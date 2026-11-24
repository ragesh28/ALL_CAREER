import json
import hashlib
import os
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import Mock, patch

from scripts.publish_company_catalog import merge_json, merge_job_lists, publish, MISSING
from scripts.company_github_publication import GitHubPublication
from scripts.company_job_store import india_today


def job(n):return {'title':'Engineer','company':'Example','location':'Chennai','apply_url':f'https://example.test/job/{n}','job_id':str(n),'first_seen':india_today().isoformat()}


class MergeTests(unittest.TestCase):
    def test_concurrent_lists_preserve_both_new_jobs(self):
        result=merge_job_lists([job(1)],[job(1),job(2)],[job(1),job(3)])
        self.assertEqual({j['job_id'] for j in result},{'1','2','3'})

    def test_first_seen_does_not_reset_during_concurrent_enrichment(self):
        old={**job(1),'first_seen':'2026-11-10'}
        result=merge_job_lists([old],[{**job(1),'salary':'INR 5 LPA'}],[{**old,'experience':'2 years'}])
        self.assertEqual(result[0]['first_seen'],'2026-11-10')
        self.assertEqual(result[0]['experience'],'2 years')
        self.assertEqual(result[0]['salary'],'INR 5 LPA')

    def test_updated_concurrent_record_is_not_deleted_by_stale_retention(self):
        old=job(1);updated={**old,'last_seen':'2026-11-25'}
        self.assertEqual(merge_job_lists([old],[],[updated]),[updated])

    def test_ai_call_counts_merge_deltas_not_duplicate_base_counts(self):
        def state(calls):return {'date':'2026-11-24','accounts':{'profile':{'provider':'cloudflare','calls':calls,'successes':calls,'checked_at':'2026-11-24'}}}
        merged=merge_json(state(10),state(12),state(13),'data/company_scraper2/ai_status.json')
        self.assertEqual(merged['accounts']['profile']['calls'],15)

    def test_local_execution_cannot_publish_accidentally(self):
        with patch.dict(os.environ,{'GITHUB_ACTIONS':'false'}):
            with self.assertRaises(RuntimeError):publish()

    def test_real_git_publication_keeps_concurrent_source_and_jobs(self):
        def git(cwd,*args):
            # Local file remotes need no host credential-helper environment.
            # Windows mock-environment restoration cannot retain empty values.
            env={k:v for k,v in os.environ.items() if not k.startswith('GIT_CONFIG_')}
            result=subprocess.run(['git','-C',str(cwd),*args],capture_output=True,env=env)
            if result.returncode:raise RuntimeError(result.stderr.decode(errors='replace'))
            return result.stdout
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);remote=root/'remote.git';remote.mkdir();git(remote,'init','--bare')
            a=root/'a';a.mkdir();git(a,'init','-b','main');git(a,'config','user.name','test');git(a,'config','user.email','test@example.test');git(a,'remote','add','origin',str(remote))
            (a/'workday_scraper').mkdir();path='workday_scraper/big_company_jobs.json';(a/path).write_text(json.dumps([job(1)]));(a/'source.py').write_text('version = 1\n');git(a,'add','.');git(a,'commit','-m','base');git(a,'push','-u','origin','main')
            b=root/'b';git(root,'clone','--branch','main',str(remote),str(b));git(b,'config','user.name','test');git(b,'config','user.email','test@example.test')
            (a/path).write_text(json.dumps([job(1),job(2)]));git(a,'add',path)
            (b/path).write_text(json.dumps([job(1),job(3)]));(b/'source.py').write_text('version = 2\n');git(b,'add','.');git(b,'commit','-m','concurrent');git(b,'push','origin','main')
            with patch.dict(os.environ,{'GITHUB_ACTIONS':'true','GIT_CONFIG_COUNT':'0'}):publish(a,runner_temp=temp)
            git(b,'pull','--ff-only','origin','main')
            self.assertEqual({j['job_id'] for j in json.loads((b/path).read_text())},{'1','2','3'})
            self.assertEqual((b/'source.py').read_text(),'version = 2\n')
            self.assertEqual((a/'source.py').read_text(),'version = 1\n')

    def test_api_publication_retries_race_without_fetching_or_repacking_git(self):
        import scripts.publish_company_catalog as publisher
        def git(root,*args):
            result=subprocess.run(['git','-C',str(root),*args],capture_output=True)
            if result.returncode:raise RuntimeError(result.stderr.decode(errors='replace'))
            return result.stdout
        class Remote:
            def __init__(self):self.attempts=0;self.saved=None
            def snapshot(self,paths,base,hashes,missing):
                self.attempts+=1
                rows=[job(1),job(3)] + ([job(4)] if self.attempts>1 else [])
                return 'latest','tree',{path:rows for path in paths}
            def commit(self,parent,tree,merged,remote,missing):
                self.saved=merged
                return self.attempts>1
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);git(root,'init','-b','main');git(root,'config','user.name','test');git(root,'config','user.email','test@example.test')
            path='workday_scraper/big_company_jobs.json';(root/'workday_scraper').mkdir()
            (root/path).write_text(json.dumps([job(1)]));(root/'source.py').write_text('original\n')
            git(root,'add','.');git(root,'commit','-m','base')
            (root/path).write_text(json.dumps([job(1),job(2)]));git(root,'add',path)
            remote=Remote()
            with patch.dict(os.environ,{'GITHUB_ACTIONS':'true'}),patch.object(publisher,'git',wraps=publisher.git) as calls:
                publish(root,api_client=remote)
            self.assertEqual({j['job_id'] for j in remote.saved[path]},{'1','2','3','4'})
            self.assertEqual(remote.attempts,2)
            self.assertEqual((root/'source.py').read_text(),'original\n')
            self.assertFalse(any(call.args[1] in ('fetch','push','worktree','read-tree') for call in calls.call_args_list))


def api_response(payload=None,status=200,headers=None):
    result=Mock(status_code=status,ok=200<=status<300,headers=headers or {})
    result.json.return_value=payload or {}
    return result


class GitHubPublicationTests(unittest.TestCase):
    def test_unchanged_remote_blob_reuses_baseline_without_downloading_catalog(self):
        session=Mock();session.request.side_effect=[
            api_response({'object':{'sha':'parent'}}),api_response({'tree':{'sha':'root'}}),
            api_response({'tree':[{'path':'data','sha':'data-tree'}]}),
            api_response({'tree':[{'path':'big_company_jobs.json','sha':'catalog'}]})]
        client=GitHubPublication('owner/repo','test-token',session)
        path='data/big_company_jobs.json';base={path:[job(1)]}
        parent,tree,values=client.snapshot([path],base,{path:'catalog'},MISSING)
        self.assertIs(values[path],base[path])
        self.assertFalse(any('/git/blobs/' in call.args[1] for call in session.request.call_args_list))

    def test_identical_large_catalog_mirrors_upload_one_blob_and_use_nonforced_update(self):
        value={'data':'x'*210000};data=json.dumps(value,ensure_ascii=False,separators=(',',':')).encode()
        sha=hashlib.sha1(b'blob '+str(len(data)).encode()+b'\0'+data).hexdigest()
        session=Mock();session.request.side_effect=[api_response({'sha':sha}),api_response({'sha':'new-tree'}),api_response({'sha':'new-commit'}),api_response({'object':{'sha':'new-commit'}})]
        client=GitHubPublication('owner/repo','test-token',session)
        merged={'data/big_company_jobs.json':value,'workday_scraper/big_company_jobs.json':value}
        self.assertTrue(client.commit('parent','tree',merged,{p:{} for p in merged},MISSING))
        calls=session.request.call_args_list
        self.assertEqual(sum(call.args[1].endswith('/git/blobs') for call in calls),1)
        self.assertEqual(calls[-1].kwargs['json'],{'sha':'new-commit','force':False})

    def test_branch_race_returns_false_for_three_way_retry(self):
        session=Mock();session.request.side_effect=[api_response({'sha':'tree'}),api_response({'sha':'commit'}),api_response(status=422)]
        client=GitHubPublication('owner/repo','test-token',session)
        self.assertFalse(client.commit('parent','tree',{'data/big_company_jobs.json':[]},{},MISSING))

    def test_provider_retry_time_beyond_save_budget_fails_without_bypassing_limit(self):
        session=Mock();session.request.return_value=api_response(status=429,headers={'Retry-After':'900'})
        client=GitHubPublication('owner/repo','test-token',session,max_seconds=60)
        with patch('scripts.company_github_publication.time.sleep') as wait:
            with self.assertRaisesRegex(RuntimeError,'rate limit'):
                client.request('GET','/git/ref/heads/main')
            wait.assert_not_called()
        self.assertEqual(session.request.call_count,1)

    def test_truncated_tree_cannot_be_mistaken_for_a_missing_file(self):
        session=Mock();session.request.return_value=api_response({'truncated':True,'tree':[]})
        client=GitHubPublication('owner/repo','test-token',session)
        with self.assertRaisesRegex(RuntimeError,'Incomplete'):
            client.entry('tree','data/big_company_jobs.json')

    def test_secondary_limit_without_retry_header_waits_one_minute(self):
        session=Mock();session.request.side_effect=[api_response({'message':'Secondary rate limit'},status=403),api_response({'ok':True})]
        client=GitHubPublication('owner/repo','test-token',session,max_seconds=180)
        with patch('scripts.company_github_publication.time.sleep') as wait:
            self.assertEqual(client.request('GET','/git/ref/heads/main'),{'ok':True})
            wait.assert_called_once_with(60)


if __name__=='__main__':unittest.main()

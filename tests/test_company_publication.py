import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

from scripts.publish_company_catalog import merge_json, merge_job_lists, publish
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


if __name__=='__main__':unittest.main()

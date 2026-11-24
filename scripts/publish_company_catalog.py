"""Publish generated JSON onto the latest main tree without overwriting concurrent data.

The source checkout is never reset. An isolated, index-only worktree starts from
the latest remote tree; only approved generated JSON paths are staged there.
"""
import json
import os
from pathlib import Path
import subprocess
import tempfile
from collections import Counter

from scripts.company_ai import atomic_json
from scripts.company_job_store import canonical_url, identity, posted_day, without_descriptions, india_today
from datetime import datetime, timezone

ALLOWED = ('data/company_job_history/', 'data/company_scraper2/', 'data/job_archives/', 'jobs_by_role/')
FILES = {'workday_scraper/big_company_jobs.json','data/big_company_jobs.json','scrape_progress.json',
         'scrape_checkpoint.json','seen_job_ids.json','scraped_jobs_output.json','role_index.json'}
MISSING = object()


def git(repo, *args, check=True):
    return subprocess.run(['git','-C',str(repo),*args],check=check,capture_output=True).stdout


def at(repo, revision, path):
    data = git(repo,'show',revision+':'+path,check=False)
    return json.loads(data) if data else MISSING


def merge_rows(base, ours, theirs):
    result = dict(theirs)
    for key,value in ours.items():
        if value not in ('',None):result[key]=value
    for key in ('first_seen','fetched_at','date_posted'):
        values=[r.get(key) for r in (base,ours,theirs) if r.get(key)]
        if values:result[key]=min(values)
    if ours.get('last_seen') or theirs.get('last_seen'):
        result['last_seen']=max(ours.get('last_seen',''),theirs.get('last_seen',''))
    if 'expired' in ours or 'expired' in theirs:result['expired']=bool(ours.get('expired') or theirs.get('expired'))
    if 'missing_scans' in ours or 'missing_scans' in theirs:result['missing_scans']=max(ours.get('missing_scans',0),theirs.get('missing_scans',0))
    return without_descriptions(result)


def merge_job_lists(base, ours, theirs):
    result={identity(j):j for j in theirs if isinstance(j,dict) and identity(j)}
    base_by_key={identity(j):j for j in base if isinstance(j,dict) and identity(j)}
    ours_keys={identity(j) for j in ours if isinstance(j,dict) and identity(j)}
    # Respect retention deletions only if the concurrent record wasn't updated.
    for key,old in base_by_key.items():
        if key not in ours_keys and result.get(key)==old:result.pop(key,None)
    by_url={canonical_url(j.get('apply_url') or j.get('url') or ''):k for k,j in result.items()}
    for row in ours:
        if not isinstance(row,dict):continue
        key=identity(row)
        if not key:continue
        link=canonical_url(row.get('apply_url') or row.get('url') or '')
        alias=by_url.get(link)
        if alias and alias!=key:
            other=result[alias]
            if not row.get('job_id') or not other.get('job_id') or row.get('job_id')==other.get('job_id'):
                row=merge_rows({},row,other);result.pop(alias);key=identity(row)
        result[key]=merge_rows(base_by_key.get(key,{}),row,result.get(key,{}))
        by_url[link]=key
    return list(result.values())


def merge_json(base, ours, theirs, path=''):
    if ours is MISSING:
        return MISSING if theirs==base else theirs
    if theirs is MISSING or theirs==base:return without_descriptions(ours)
    if ours==base:return without_descriptions(theirs)
    if isinstance(ours,list) and isinstance(theirs,list):
        if any(isinstance(j,dict) and (j.get('apply_url') or j.get('url')) for j in ours+theirs):
            return merge_job_lists(base if isinstance(base,list) else [],ours,theirs)
        unique={json.dumps(x,sort_keys=True):x for x in theirs+ours}
        return list(unique.values())
    if isinstance(ours,dict) and isinstance(theirs,dict):
        base=base if isinstance(base,dict) else {}
        if 'first_seen' in ours and 'last_seen' in ours:return merge_rows(base,ours,theirs)
        if path.endswith('ai_status.json'):
            if ours.get('date','') < theirs.get('date',''):return theirs
            if ours.get('date') != theirs.get('date'):return ours
            merged={**theirs,**ours,'accounts':{},'provider_pauses':{}}
            for key in set(ours.get('accounts',{}))|set(theirs.get('accounts',{})):
                a=ours.get('accounts',{}).get(key,{});b=theirs.get('accounts',{}).get(key,{});previous=base.get('accounts',{}).get(key,{})
                current=dict(max((a,b),key=lambda r:r.get('checked_at','')))
                for metric in ('calls','successes'):current[metric]=b.get(metric,0)+max(0,a.get(metric,0)-previous.get(metric,0))
                merged['accounts'][key]=current
            for provider in set(ours.get('provider_pauses',{}))|set(theirs.get('provider_pauses',{})):
                merged['provider_pauses'][provider]=max(ours.get('provider_pauses',{}).get(provider,''),theirs.get('provider_pauses',{}).get(provider,''))
            return merged
        merged={}
        for key in set(base)|set(ours)|set(theirs):
            value=merge_json(base.get(key,MISSING),ours.get(key,MISSING),theirs.get(key,MISSING),path+'/'+key)
            if value is not MISSING:merged[key]=value
        return merged
    return without_descriptions(ours)


def publish(repo='.', runner_temp=None, api_client=None):
    if os.environ.get('GITHUB_ACTIONS')!='true':
        raise RuntimeError('Publishing runs only inside a GitHub Actions checkout')
    repo=Path(repo).resolve()
    paths=git(repo,'diff','--cached','--name-only','-z').decode().split('\0')
    paths=[p for p in paths if p]
    if not paths:
        print('No generated data changes to publish');return
    if any(not p.endswith('.json') or not (p in FILES or p.startswith(ALLOWED)) for p in paths):
        raise RuntimeError('Only approved generated JSON may be published')
    base={p:at(repo,'HEAD',p) for p in paths}
    ours={p:json.loads((repo/p).read_text(encoding='utf-8')) if (repo/p).exists() else MISSING for p in paths}
    if api_client is None and os.environ.get('COMPANY_PUBLISH_GITHUB_API')=='1':
        from scripts.company_github_publication import GitHubPublication
        api_client=GitHubPublication.from_environment()
    baseline_hashes={}
    if api_client:
        for row in git(repo,'ls-tree','-r','HEAD','--',*paths).decode().splitlines():
            metadata,path=row.split('\t',1)
            baseline_hashes[path]=metadata.split()[2]
    for attempt in range(3):
        print(f'Reading current main for generated-data publication (attempt {attempt+1})',flush=True)
        if api_client:
            latest,tree,remote=api_client.snapshot(paths,base,baseline_hashes,MISSING)
        else:
            git(repo,'fetch','origin','main')
            latest=git(repo,'rev-parse','origin/main').decode().strip()
            remote={p:at(repo,latest,p) for p in paths}
        merged={p:merge_json(base[p],ours[p],remote[p],p) for p in paths}
        for p in ('data/big_company_jobs.json','workday_scraper/big_company_jobs.json'):
            rows=merged.get(p)
            if isinstance(rows,list):
                today=india_today()
                def recent(row):
                    published=posted_day(row.get('date_posted') or row.get('posted'),today)
                    first=posted_day(row.get('first_seen') or row.get('fetched_at'),today)
                    return (today-min(published or today,first or today)).days < 30
                merged[p]=sorted([j for j in rows if recent(j)],key=lambda j:j.get('first_seen') or j.get('fetched_at') or '',reverse=True)
        catalog='workday_scraper/big_company_jobs.json'
        if isinstance(ours.get(catalog),list):
            def index(snapshot):
                keys=set();urls={}
                for row in snapshot if isinstance(snapshot,list) else []:
                    keys.add(identity(row));urls.setdefault(canonical_url(row.get('apply_url','')),[]).append(row)
                return keys,urls
            base_index,remote_index,merged_index=map(index,(base.get(catalog),remote.get(catalog),merged.get(catalog)))
            def known(row, snapshot):
                keys,urls=snapshot
                return identity(row) in keys or any(not row.get('job_id') or not other.get('job_id') or row.get('job_id')==other.get('job_id') for other in urls.get(canonical_url(row.get('apply_url','')),[]))
            actual_new=[j for j in ours[catalog] if not known(j,base_index) and not known(j,remote_index) and known(j,merged_index)]
            by_company=Counter(j.get('company') for j in actual_new)
            for path,report in merged.items():
                if path.startswith('data/company_scraper2/') and isinstance(report,dict) and str(report.get('workflow_run_id',''))==os.environ.get('GITHUB_RUN_ID',''):
                    report.update(new_jobs=len(actual_new),locations=dict(Counter(j.get('location','Unknown') for j in actual_new)),catalog_total=len(merged[catalog]),walkins=sum(bool(j.get('is_walkin')) for j in actual_new))
                    for entry in report.get('companies',[]):
                        own=[j for j in actual_new if j.get('company')==entry.get('company')]
                        entry.update(new_jobs=by_company[entry.get('company')],locations=dict(Counter(j.get('location','Unknown') for j in own)))
        if api_client:
            if api_client.commit(latest,tree,merged,remote,MISSING):
                for p,value in merged.items():
                    if p.startswith('data/company_scraper2/') and value is not MISSING:atomic_json(repo/p,value)
                print('Published company JSON through GitHub API without repacking repository history',flush=True)
                return
            continue
        destination=Path(tempfile.mkdtemp(prefix='company-publish-',dir=runner_temp or os.environ.get('RUNNER_TEMP'))).resolve()
        git(repo,'worktree','add','--no-checkout','--detach',str(destination),latest)
        git(destination,'read-tree',latest)
        for p,value in merged.items():
            if value is MISSING:
                git(destination,'update-index','--force-remove','--',p)
            else:
                atomic_json(destination/p,value)
                git(destination,'add','--sparse','--',p)
        if subprocess.run(['git','-C',str(destination),'diff','--cached','--quiet']).returncode==0:
            print('Concurrent publication already contains these changes');return
        git(destination,'-c','user.name=github-actions[bot]','-c','user.email=github-actions[bot]@users.noreply.github.com','commit','-m','chore(jobs): merge company catalog and checkpoints [skip ci]')
        pushed=subprocess.run(['git','-C',str(destination),'push','origin','HEAD:main'],capture_output=True)
        if pushed.returncode==0:
            for p,value in merged.items():
                if p.startswith('data/company_scraper2/') and value is not MISSING:atomic_json(repo/p,value)
            print('Published company data onto latest main without resetting the source checkout')
            return
    raise RuntimeError('Publication conflicted three times; sanitized artifacts preserve the checkpoint')


if __name__=='__main__':publish()

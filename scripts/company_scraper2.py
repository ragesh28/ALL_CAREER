"""Daily official-board scraper. Restartable without persisting descriptions."""
import argparse
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from dataclasses import asdict
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import signal
import time

import requests

from scripts.company_ai import JobAI, atomic_json, load_json
from scripts.company_boards import scrape_board, posting_details
from scripts.company_job_details import details_from_record, confirmed_india_location
from scripts.company_job_store import CompanyJobStore, identity, posted_day, india_today

ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / 'scripts/company_scraper2_sources.json'
STOP = False


def stop_requested(*_):
    global STOP
    STOP = True


def closed_posting(url, deadline=None):
    remaining = min(10, deadline-time.monotonic()) if deadline is not None else 10
    if remaining < 1:
        return False
    try:
        return requests.get(url, timeout=(min(5,remaining), remaining), headers={'User-Agent':'Mozilla/5.0'}).status_code in (404, 410)
    except requests.RequestException:
        return False


def audit(configs, output, browser=False):
    def check(config):
        started = time.monotonic()
        result = scrape_board(config, max_pages=1, budget=50, browser=browser)
        description_checked = False
        if result.jobs:
            for job in result.jobs[:2]:
                posting_details(job, config, allow_browser=browser)
                if len(job.get('description','')) >= 150:
                    description_checked = True
                    result.jobs.sort(key=lambda j:len(j.get('description','')),reverse=True)
                    break
        return {'company':config['company'], 'board_id':config['board_id'], 'group':config['group'],
                'status':result.status, 'http_status':result.http_status, 'returned_records':result.returned,
                'india_samples':len(result.jobs), 'rejected_locations':result.rejected_locations,
                'description_checked':description_checked, 'sample':{k:v for k,v in (result.jobs[0] if result.jobs else {}).items() if k in ('title','location','apply_url','job_id')},
                'duration_seconds':round(time.monotonic()-started,2), 'note':result.note}
    results = []
    with ThreadPoolExecutor(max_workers=4) as pool:
        for result in pool.map(check, configs):
            results.append(result)
            atomic_json(output, {'checked_at':datetime.now(timezone.utc).isoformat(), 'companies':results})
            print(f"{result['company']}: {result['status']}; India samples={result['india_samples']}; description={result['description_checked']}", flush=True)
    return results


def run(configs, root, max_seconds=20700, browser=True, max_jobs=None):
    global STOP
    root = Path(root)
    directory = root / 'data/company_scraper2'
    checkpoint_path = directory / 'checkpoint.json'
    checkpoint = load_json(checkpoint_path,{})
    today = india_today().isoformat()
    if not checkpoint or checkpoint.get('completed'):
        checkpoint = {'cycle':today, 'completed_boards':[], 'processed_ids':[], 'active_board':None, 'completed':False, 'continuation':0}
    started = time.monotonic()
    store = CompanyJobStore(root)
    ai = JobAI(directory / 'ai_status.json')
    ai.deadline = started + max_seconds - 30
    report = {'workflow_run_id':os.environ.get('GITHUB_RUN_ID','local'), 'cycle':checkpoint['cycle'], 'started_at':datetime.now(timezone.utc).isoformat(), 'companies':[], 'locations':{}, 'new_jobs':0, 'walkins':0, 'status':'running'}
    report_path = directory / 'latest.json'
    pending = [c for c in configs if c['board_id'] not in checkpoint['completed_boards']]

    def save():
        store.save()
        ai.flush()
        checkpoint['updated_at'] = datetime.now(timezone.utc).isoformat()
        atomic_json(checkpoint_path,checkpoint)
        report['updated_at'] = checkpoint['updated_at']
        report['catalog_total'] = len(store.jobs)
        report['new_jobs'] = store.new_count
        atomic_json(report_path,report)
        atomic_json(directory / 'runs' / (report['workflow_run_id']+'.json'),report)

    for config in pending:
        if STOP or time.monotonic()-started >= max_seconds-60:
            break
        board_id = config['board_id']
        if checkpoint['active_board'] != board_id:
            checkpoint.update(active_board=board_id,processed_ids=[])
        processed = set(checkpoint['processed_ids'])
        result = scrape_board(config,budget=min(180,max(1,max_seconds-(time.monotonic()-started)-30)),browser=browser)
        entry = {'company':config['company'], 'board_id':board_id, 'status':result.status,
                 'http_status':result.http_status, 'returned_records':result.returned, 'india_jobs':len(result.jobs),
                 'complete_snapshot':result.complete, 'new_jobs':0,'existing_jobs':0,'old_jobs':0,
                 'descriptions_read':0,'ai_enriched':0,'locations':{},'walkins':0,'note':result.note}
        report['companies'].append(entry)
        completed_board = True
        present = set()
        for job in result.jobs:
            job['company'] = config['company']
            key = identity(job)
            present.add(key)
            if key in processed:
                continue
            if STOP or time.monotonic()-started >= max_seconds-45 or (max_jobs and len(processed) >= max_jobs):
                completed_board = False
                break
            original = posted_day(job.get('date_posted') or job.get('posted'))
            # Already known jobs retain metadata and their original discovery date.
            previous = store.jobs.get(key, {})
            history_entry = store.history(config['company'])['entries'].get(key,{})
            first_day = posted_day(history_entry.get('first_seen'))
            expired = (original and (india_today()-original).days >= 30) or (first_day and (india_today()-first_day).days >= 30)
            if (not store.is_known(job) or (not previous.get('metadata_checked_at') and ai.available())) and not expired:
                posting_details(job,config,allow_browser=browser)
                if job.get('description'):
                    entry['descriptions_read'] += 1
                    job.update({k:v for k,v in details_from_record(job).items() if v})
                    before = sum(s['successes'] for s in ai.state['accounts'].values())
                    facts = ai.extract(job['description'])
                    if sum(s['successes'] for s in ai.state['accounts'].values()) > before:
                        job['metadata_checked_at'] = datetime.now(timezone.utc).isoformat()
                    if facts:
                        entry['ai_enriched'] += 1
                    for k,v in facts.items():
                        if not job.get(k):job[k]=v
            outcome = store.upsert(job)
            if outcome=='new':
                entry['new_jobs'] += 1
                loc = job.get('location','Unknown')
                entry['locations'][loc] = entry['locations'].get(loc,0)+1
                report['locations'][loc] = report['locations'].get(loc,0)+1
                if job.get('is_walkin'):
                    entry['walkins'] += 1;report['walkins'] += 1
            elif outcome=='existing':entry['existing_jobs'] += 1
            elif outcome=='old':entry['old_jobs'] += 1
            # Drop full descriptions before checkpointing or reporting anything.
            job.pop('description',None)
            processed.add(key)
            checkpoint['processed_ids'] = sorted(processed)
            if len(processed)%20==0:save()
        if completed_board:
            # Zero/partial/broken extraction cannot retire history. Two full absence
            # checks plus a confirmed 404/410 are required before deleting an ID.
            if result.complete and result.status in ('ok','empty_confirmed'):
                deadline = started + max_seconds - 30
                entry['retired_ids'] = store.reconcile(config['company'],present,complete=True,
                    verify_closed=lambda url: closed_posting(url,deadline),deadline=deadline)
            checkpoint['completed_boards'].append(board_id)
            checkpoint.update(active_board=None,processed_ids=[])
        save()
        print(f"{config['company']}: {result.status}; India={len(result.jobs)}; new={entry['new_jobs']}; descriptions={entry['descriptions_read']}",flush=True)
        if not completed_board:break
    checkpoint['completed'] = all(c['board_id'] in checkpoint['completed_boards'] for c in configs)
    report['status'] = 'completed' if checkpoint['completed'] else 'checkpointed'
    report['ai_status'] = {k:{'provider':v['provider'],'status':v['status'],'calls':v['calls'],'successes':v['successes'],'model':v.get('model'),'retry_at':v.get('retry_at')} for k,v in ai.state['accounts'].items()}
    save()
    for old in (directory / 'runs').glob('*.json'):
        try:
            timestamp = load_json(old,{}).get('started_at','')
            if timestamp and (datetime.now(timezone.utc)-datetime.fromisoformat(timestamp)).days > 30:
                old.unlink()
        except (OSError,ValueError,TypeError):
            pass
    if os.environ.get('GITHUB_OUTPUT'):
        with open(os.environ['GITHUB_OUTPUT'],'a',encoding='utf-8') as fh:
            fh.write('needs_resume='+str(not checkpoint['completed']).lower()+'\n')
    if os.environ.get('GITHUB_STEP_SUMMARY'):
        with open(os.environ['GITHUB_STEP_SUMMARY'],'a',encoding='utf-8') as fh:
            fh.write(f"## Big Company Scraper 2\n\nNew jobs: {store.new_count}. Status: {report['status']}. Full descriptions are not persisted.\n\n|Company|India records|New|Descriptions read|Status|\n|---|---:|---:|---:|---|\n")
            for e in report['companies']:fh.write(f"|{e['company']}|{e['india_jobs']}|{e['new_jobs']}|{e['descriptions_read']}|{e['status']}|\n")
    return report


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--audit',action='store_true')
    parser.add_argument('--companies',default='')
    parser.add_argument('--output',default='company_scraper2_audit.json')
    parser.add_argument('--root',default=str(ROOT))
    parser.add_argument('--max-seconds',type=int,default=20700)
    parser.add_argument('--browser',action='store_true')
    parser.add_argument('--check-ai',action='store_true')
    args=parser.parse_args()
    if args.check_ai:
        ai=JobAI(Path(args.root)/'data/company_scraper2/ai_status.json')
        # One tiny factual request verifies the same extraction contract used for jobs.
        ai.probe()
        ai.flush()
        print(json.dumps({'configured_accounts':len(ai.accounts),'statuses':[{k:v for k,v in s.items() if k in ('provider','slot','status','http_status','model','models')} for s in ai.state['accounts'].values()]}))
        return
    configs=load_json(CONFIG,[])
    if args.companies:
        wanted={s.strip().casefold() for s in args.companies.split(',')}
        configs=[c for c in configs if c['company'].casefold() in wanted or c['board_id'] in wanted]
        if not configs:parser.error('No matching companies')
    for sig in (signal.SIGINT,signal.SIGTERM):signal.signal(sig,stop_requested)
    if args.audit:audit(configs,args.output,args.browser)
    else:run(configs,args.root,args.max_seconds,args.browser)


if __name__=='__main__':
    main()

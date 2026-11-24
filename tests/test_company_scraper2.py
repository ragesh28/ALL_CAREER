import json
import os
from copy import deepcopy
from datetime import date
from pathlib import Path
import tempfile
import time
import unittest
from unittest.mock import Mock, patch

from scripts.company_ai import JobAI, validate_facts, load_json
from scripts.company_boards import BoardResult, parse_payload, next_request
from scripts.company_job_store import CompanyJobStore, canonical_url, identity, posted_day
from scripts.company_scraper2 import run


def job(**changes):
    return {'title':'Software Engineer','company':'Example','location':'Chennai, India','apply_url':'https://example.test/job/1','job_id':'req-1',**changes}


def response(status=200, payload=None, text='', headers=None):
    r=Mock(status_code=status,headers=headers or {},text=text)
    r.json.return_value=payload
    return r


class ExtractionTests(unittest.TestCase):
    def test_no_model_request_starts_after_checkpoint_deadline(self):
        with tempfile.TemporaryDirectory() as d:
            session=Mock()
            ai=JobAI(Path(d)/'status.json',{'GROQ_API_KEYS':'test-key'},session)
            ai.deadline=time.monotonic()-1
            self.assertEqual(ai.extract('Requires 2 years of experience'),{})
            session.post.assert_not_called()
    def test_candidate_age_is_not_work_experience(self):
        self.assertEqual(validate_facts({'experience':{'value':'28 years','evidence':'Age: 28 years'}},'Age: 28 years'),{})
    def test_requires_verbatim_evidence_and_rejects_experience_as_posting_date(self):
        desc='Required experience: at least 2 years of work experience. Salary: INR 5 LPA.'
        facts={'experience':{'value':'2 years','evidence':'at least 2 years of work experience'},
               'salary':{'value':'INR 50 LPA','evidence':'Salary: INR 5 LPA'},
               'date_posted':{'value':'2026-11-02','evidence':'at least 2 years of work experience'},
               'walkin_date':{'value':'2026-11-02','evidence':'missing evidence'}}
        self.assertEqual(validate_facts(facts,desc),{'experience':'2 years'})

    def test_unsupported_model_falls_back_without_leaking_keys(self):
        with tempfile.TemporaryDirectory() as d:
            secret='test-token-never-publish'
            env={'CLOUDFLARE_WORKERS_AI_ACCOUNTS':json.dumps([{'account_id':'a'*32,'api_token':secret}])}
            session=Mock()
            session.post.side_effect=[response(404),response(payload={'success':True,'result':{'response':json.dumps({'experience':{'value':'2 years','evidence':'2 years of experience'}})}})]
            ai=JobAI(Path(d)/'status.json',env,session)
            self.assertEqual(ai.extract('Requires 2 years of experience'),{'experience':'2 years'})
            self.assertEqual(session.post.call_count,2)
            self.assertNotIn(secret,(Path(d)/'status.json').read_text())
            self.assertNotIn('a'*32,(Path(d)/'status.json').read_text())

    def test_daily_quota_pauses_provider_instead_of_rotating_cloudflare_accounts(self):
        with tempfile.TemporaryDirectory() as d:
            env={'CLOUDFLARE_WORKERS_AI_ACCOUNTS':json.dumps([{'account_id':n*32,'api_token':n+'-token'} for n in ['a','b']]),'GROQ_API_KEYS':'groq-token'}
            session=Mock()
            session.post.side_effect=[response(429,text='Daily neuron quota exceeded'),response(payload={'choices':[{'message':{'content':'{}'}}]})]
            ai=JobAI(Path(d)/'status.json',env,session)
            ai.extract('2 years of experience')
            urls=[call.args[0] for call in session.post.call_args_list]
            self.assertEqual(len(urls),2)
            self.assertIn('api.groq.com',urls[-1])
            self.assertEqual(list(ai.state['accounts'].values())[0]['status'],'daily_quota_exhausted')
            self.assertEqual(list(ai.state['accounts'].values())[1]['calls'],0)

    def test_http_200_error_and_non_json_do_not_count_as_model_success(self):
        with tempfile.TemporaryDirectory() as d:
            env={'CLOUDFLARE_WORKERS_AI_ACCOUNTS':json.dumps([{'account_id':'a'*32,'api_token':'token'}])}
            session=Mock()
            session.post.side_effect=[response(payload={'success':False,'errors':[{'message':'failed'}]}),response(payload={'success':True,'result':{'response':'not JSON'}})]
            ai=JobAI(Path(d)/'status.json',env,session)
            self.assertEqual(ai.extract('2 years experience'),{})
            self.assertEqual(sum(x['successes'] for x in ai.state['accounts'].values()),0)


class IdentityTests(unittest.TestCase):
    def test_publication_timestamp_is_converted_to_india_calendar_day(self):
        self.assertEqual(posted_day('2026-11-23T22:00:00Z',date(2026,11,24)),date(2026,11,24))
    def test_keeps_id_query_but_discards_tracking(self):
        self.assertEqual(canonical_url('https://ex.test/job?id=42&utm_source=x'),'https://ex.test/job?id=42')
        self.assertNotEqual(identity(job(job_id='',apply_url='https://ex.test/job?id=1')),identity(job(job_id='',apply_url='https://ex.test/job?id=2')))

    def test_modal_board_records_keep_distinct_native_ids(self):
        self.assertNotEqual(identity(job(job_id='one')),identity(job(job_id='two')))

    def test_expired_listing_cannot_return_as_new_after_thirty_days(self):
        with tempfile.TemporaryDirectory() as d:
            store=CompanyJobStore(d,date(2026,10,1));self.assertEqual(store.upsert(job()),'new');store.save()
            store=CompanyJobStore(d,date(2026,11,1));self.assertEqual(len(store.jobs),0)
            self.assertEqual(store.upsert(job()),'old');store.save()
            self.assertEqual(load_json(Path(d)/'data/big_company_jobs.json',[]),[])
            self.assertEqual(len(store.history('Example')['entries']),1)

    def test_original_old_posting_is_remembered_but_not_displayed_as_new(self):
        with tempfile.TemporaryDirectory() as d:
            store=CompanyJobStore(d,date(2026,11,24))
            self.assertEqual(store.upsert(job(date_posted='2026-09-15')),'old')
            self.assertEqual(store.jobs,{})
            self.assertEqual(store.upsert(job(job_id='older',apply_url='https://example.test/job/older',date_posted='Posted 30+ Days Ago')),'old')

    def test_old_publication_cannot_resurrect_if_source_later_omits_the_date(self):
        with tempfile.TemporaryDirectory() as d:
            store=CompanyJobStore(d,date(2026,11,24));store.upsert(job(date_posted='2026-09-15'));store.save()
            store=CompanyJobStore(d,date(2026,11,25))
            self.assertEqual(store.upsert(job()),'old')
            self.assertEqual(store.jobs,{})

    def test_native_id_survives_apply_url_change_without_duplicate(self):
        with tempfile.TemporaryDirectory() as d:
            store=CompanyJobStore(d,date(2026,11,24));store.upsert(job())
            self.assertEqual(store.upsert(job(apply_url='https://example.test/new-url/1')),'existing')
            self.assertEqual(len(store.jobs),1)
            self.assertEqual(store.new_count,1)

    def test_history_first_interruption_can_restore_recent_catalog_record(self):
        with tempfile.TemporaryDirectory() as d:
            store=CompanyJobStore(d,date(2026,11,24));store.upsert(job());store.save()
            Path(d,'workday_scraper/big_company_jobs.json').write_text('[]')
            store=CompanyJobStore(d,date(2026,11,25));self.assertEqual(store.upsert(job()),'existing')
            self.assertEqual(next(iter(store.jobs.values()))['first_seen'],'2026-11-24')

    def test_partial_or_failed_snapshot_cannot_delete_ids(self):
        with tempfile.TemporaryDirectory() as d:
            store=CompanyJobStore(d,date(2026,11,24));store.upsert(job())
            verify=Mock(return_value=True)
            for _ in range(3):self.assertEqual(store.reconcile('Example',set(),complete=False,verify_closed=verify),0)
            verify.assert_not_called()
            self.assertEqual(store.reconcile('Example',set(),complete=True,verify_closed=verify),0)
            self.assertEqual(store.reconcile('Example',set(),complete=True,verify_closed=verify),1)

    def test_descriptions_are_not_saved_to_catalog_or_history(self):
        with tempfile.TemporaryDirectory() as d:
            store=CompanyJobStore(d,date(2026,11,24));store.upsert(job(description='Private original full description',salary='INR 5 LPA'));store.save()
            for f in Path(d).rglob('*.json'):self.assertNotIn('Private original full description',f.read_text())
            self.assertEqual(next(iter(store.jobs.values()))['salary'],'INR 5 LPA')


class AdapterTests(unittest.TestCase):
    def test_greenhouse_offices_are_kept_but_updated_at_is_not_publication(self):
        cfg={'ats':'greenhouse','company':'Cloudflare','endpoint':'https://boards-api.greenhouse.io/v1/boards/cloudflare/jobs'}
        payload={'jobs':[{'id':1,'title':'Engineer','absolute_url':'https://boards.greenhouse.io/cloudflare/jobs/1','location':{'name':'Hybrid'},'offices':[{'name':'Bengaluru','location':'Bengaluru, India'}],'updated_at':'2026-11-24'}]}
        rows=parse_payload(payload,cfg)
        self.assertIn('India',rows[0]['location'])
        self.assertNotIn('date_posted',rows[0])

    def test_eightfold_relative_detail_link_is_absolute(self):
        cfg={'ats':'eightfold','company':'Micron','endpoint':'https://micron.eightfold.ai/api/pcsx/search'}
        rows=parse_payload({'data':{'positions':[{'id':12,'name':'Engineer','positionUrl':'/careers/job/12','locations':['Hyderabad, India']}]}},cfg)
        self.assertEqual(rows[0]['apply_url'],'https://micron.eightfold.ai/careers/job/12')

    def test_workday_pagination_uses_raw_page_count(self):
        config={'ats':'workday'};body={'offset':0,'limit':20}
        self.assertEqual(next_request(config,'https://example.test',body,{'total':40},20)[1]['offset'],20)
        self.assertIsNone(next_request(config,'https://example.test',{'offset':20,'limit':20},{'total':40},20))

    def test_config_has_new_and_recovered_boards_without_salary_estimates(self):
        rows=json.loads((Path(__file__).resolve().parents[1]/'scripts/company_scraper2_sources.json').read_text())
        self.assertEqual(len([r for r in rows if r['group']=='new_35']),36)
        self.assertEqual(len([r for r in rows if r['group']=='recovered']),19)
        self.assertEqual(len({r['board_id'] for r in rows}),55)
        self.assertNotIn('avg_india_salary_lpa',str(rows))


class ResumeTests(unittest.TestCase):
    def test_resume_mid_company_has_no_duplicate_and_no_raw_description_checkpoint(self):
        configs=[{'company':'Example','board_id':'example'}]
        source=[job(apply_url=f'https://example.test/job/{i}',job_id=str(i),description='Private original full description') for i in range(3)]
        def scrape(*args,**kwargs):return BoardResult(jobs=deepcopy(source),status='ok',complete=False,returned=3)
        with tempfile.TemporaryDirectory() as d,patch('scripts.company_scraper2.scrape_board',side_effect=scrape),patch.dict(os.environ,{'COMPANY_AI_DISABLED':'1'}):
            first=run(configs,d,max_jobs=1)
            self.assertEqual(first['status'],'checkpointed')
            second=run(configs,d)
            self.assertEqual(second['status'],'completed')
            rows=load_json(Path(d)/'data/big_company_jobs.json',[])
            self.assertEqual(len(rows),3)
            self.assertEqual(len({r['apply_url'] for r in rows}),3)
            for f in Path(d).rglob('*.json'):self.assertNotIn('Private original full description',f.read_text())


if __name__=='__main__':unittest.main()

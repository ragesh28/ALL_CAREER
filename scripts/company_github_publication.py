"""Publish generated JSON through GitHub without repacking the large repository."""
import base64
import hashlib
import json
import os
import re
import time

import requests


class GitHubPublication:
    def __init__(self, repository, token, session=None, max_seconds=480):
        if not re.fullmatch(r'[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+', repository or '') or not token:
            raise RuntimeError('GitHub publication needs GITHUB_REPOSITORY and GH_TOKEN')
        self.base = 'https://api.github.com/repos/' + repository
        self.session = session or requests.Session()
        self.session.headers.update({'Authorization':'Bearer '+token,
            'Accept':'application/vnd.github+json','X-GitHub-Api-Version':'2022-11-28'})
        self.deadline = time.monotonic()+max_seconds
        self.trees = {}
        self.blobs = {}

    @classmethod
    def from_environment(cls):
        return cls(os.environ.get('GITHUB_REPOSITORY',''), os.environ.get('GH_TOKEN',''))

    def request(self, method, path, body=None, conflict=False):
        for attempt in range(4):
            remaining = self.deadline-time.monotonic()
            if remaining < 2:
                raise RuntimeError('Publication deadline reached; recovery artifact retains saved data')
            try:
                response = self.session.request(method,self.base+path,json=body,
                    timeout=(min(5,remaining),min(60,remaining)))
            except requests.RequestException:
                if attempt == 3:
                    raise RuntimeError('GitHub publication network failure') from None
                continue
            if response.status_code == 422 and conflict:
                return None
            limited = response.status_code == 429 or (response.status_code == 403 and
                (response.headers.get('Retry-After') or response.headers.get('X-RateLimit-Remaining') == '0'))
            if limited:
                retry = response.headers.get('Retry-After','')
                if retry.isdigit():
                    delay = max(1,int(retry))
                else:
                    try:
                        delay = max(1,int(response.headers.get('X-RateLimit-Reset','0'))-time.time())
                    except ValueError:
                        delay = 60
                if time.monotonic()+delay+2 >= self.deadline:
                    raise RuntimeError('GitHub rate limit exceeds publication budget; data remains recoverable')
                time.sleep(delay)
                continue
            if response.status_code >= 500 and attempt < 3:
                continue
            if not response.ok:
                raise RuntimeError(f'GitHub publication {method} returned HTTP {response.status_code}')
            return response.json()
        raise RuntimeError('GitHub publication retry budget exhausted')

    def entry(self, tree, path):
        current = tree
        for part in path.split('/'):
            if current not in self.trees:
                payload = self.request('GET','/git/trees/'+current)
                if payload.get('truncated'):
                    raise RuntimeError('Incomplete GitHub tree cannot establish safe publication paths')
                self.trees[current] = {item['path']:item for item in payload['tree']}
            item = self.trees[current].get(part)
            if item is None:
                return None
            current = item['sha']
        return current

    def snapshot(self, paths, baseline, baseline_hashes, missing):
        parent = self.request('GET','/git/ref/heads/main')['object']['sha']
        tree = self.request('GET','/git/commits/'+parent)['tree']['sha']
        values = {}
        for path in paths:
            sha = self.entry(tree,path)
            if sha is None:
                values[path] = missing
            elif sha == baseline_hashes.get(path):
                values[path] = baseline[path]
            else:
                if sha not in self.blobs:
                    blob = self.request('GET','/git/blobs/'+sha)
                    if blob.get('encoding') != 'base64':
                        raise RuntimeError('Unsupported GitHub JSON blob encoding')
                    self.blobs[sha] = json.loads(base64.b64decode(blob['content']))
                values[path] = self.blobs[sha]
        return parent,tree,values

    def commit(self, parent, tree, merged, remote, missing):
        entries = []
        uploaded = {}
        inline_bytes = 0
        for path,value in merged.items():
            if value is remote.get(path) or value == remote.get(path):
                continue
            entry = {'path':path,'mode':'100644','type':'blob'}
            if value is missing:
                entry['sha'] = None
            else:
                content = json.dumps(value,ensure_ascii=False,separators=(',',':'))
                data = content.encode('utf-8')
                if len(data) > 95_000_000:
                    raise RuntimeError('Generated JSON exceeds the safe single-file publication size')
                if len(data) < 200_000 and inline_bytes+len(data) <= 4_000_000:
                    entry['content'] = content
                    inline_bytes += len(data)
                else:
                    sha = hashlib.sha1(b'blob '+str(len(data)).encode()+b'\0'+data).hexdigest()
                    if sha not in uploaded:
                        uploaded[sha] = self.request('POST','/git/blobs',
                            {'content':base64.b64encode(data).decode(),'encoding':'base64'})['sha']
                        if uploaded[sha] != sha:
                            raise RuntimeError('Published JSON blob hash mismatch')
                    entry['sha'] = uploaded[sha]
            entries.append(entry)
        if not entries:
            print('Concurrent publication already contains these changes',flush=True)
            return True
        print(f'Publishing {len(entries)} generated JSON paths through GitHub API',flush=True)
        created_tree = self.request('POST','/git/trees',{'base_tree':tree,'tree':entries})['sha']
        created = self.request('POST','/git/commits',{
            'message':'chore(jobs): merge company catalog and checkpoints [skip ci]',
            'author':{'name':'github-actions[bot]','email':'github-actions[bot]@users.noreply.github.com'},
            'committer':{'name':'github-actions[bot]','email':'github-actions[bot]@users.noreply.github.com'},
            'tree':created_tree,'parents':[parent]})['sha']
        return self.request('PATCH','/git/refs/heads/main',{'sha':created,'force':False},conflict=True) is not None

'use strict';
const test=require('node:test');
const assert=require('node:assert/strict');
const {deployPages}=require('../scripts/deploy_pages.cjs');
const revision='a'.repeat(40);
function fixture(handler) {
  const calls=[],logs=[],outputs={};
  return {calls,logs,outputs,github:{request:async(route,args)=>{calls.push({route,args});return {data:await handler(route,args)};}},
    context:{repo:{owner:'owner',repo:'repo'}},core:{getIDToken:async()=> 'private-oidc',setSecret:()=>{},
      info:message=>logs.push(message),setOutput:(key,value)=>{outputs[key]=value;}},
    artifactId:'123',buildVersion:revision,wait:async()=>{}};
}
test('uses the exact upload ID, masks OIDC and verifies success without artifact discovery',async()=>{
  const f=fixture(route=>route.startsWith('POST')?{id:'deployment',page_url:'https://example.test/'}:{status:'succeed'});
  await deployPages(f);
  assert.equal(f.calls[0].args.artifact_id,123);
  assert.equal(f.calls[0].args.oidc_token,'private-oidc');
  assert.equal(f.outputs.page_url,'https://example.test/');
  assert.equal(f.outputs.status,'succeed');
  assert.ok(f.calls.every(call=>!call.route.endsWith('/artifacts')));
  assert.ok(!f.logs.join(' ').includes('private-oidc'));
});
test('can recover the unique uploaded package from this main-branch Pages workflow',async()=>{
  const f=fixture(route=>{
    if(route.endsWith('/actions/runs/{run_id}')) return {head_branch:'main',path:'.github/workflows/deploy-public-pages.yml',head_sha:revision};
    if(route.endsWith('/artifacts'))return {total_count:1,artifacts:[{id:456,name:'github-pages',expired:false}]};
    return route.startsWith('POST')?{id:'deployment'}:{status:'succeed'};
  });
  await deployPages({...f,artifactId:'',recoverRunId:'789'});
  assert.equal(f.calls.find(call=>call.route.endsWith('/pages/deployments')).args.artifact_id,456);
});
test('rejects recovery from a different workflow before any deployment',async()=>{
  const f=fixture(()=>({head_branch:'main',path:'.github/workflows/unrelated.yml',head_sha:revision}));
  await assert.rejects(deployPages({...f,recoverRunId:'789'}),/Only this repository/);
  assert.ok(f.calls.every(call=>call.route.startsWith('GET')));
});
test('rejects an expired or ambiguous recovery package',async()=>{
  const f=fixture(route=>route.endsWith('/artifacts')?{total_count:1,artifacts:[{id:456,name:'github-pages',expired:true}]}:
    {head_branch:'main',path:'.github/workflows/deploy-public-pages.yml',head_sha:revision});
  await assert.rejects(deployPages({...f,recoverRunId:'789'}),/exactly one/);
});
test('failed Pages content cannot be reported as deployed',async()=>{
  const f=fixture(route=>route.startsWith('POST')?{id:'deployment'}:{status:'deployment_content_failed'});
  await assert.rejects(deployPages(f),/deployment_content_failed/);
  assert.ok(f.calls.some(call=>call.route.endsWith('/cancel')));
  assert.equal(f.outputs.status,undefined);
});
test('bounded polling cancels rather than falsely completing a stuck deployment',async()=>{
  let tick=0;
  const f=fixture(route=>route.startsWith('POST')?{id:'deployment'}:{status:'deployment_in_progress'});
  await assert.rejects(deployPages({...f,timeoutMs:20,now:()=>tick,wait:async()=>{tick+=10;}}),/timed out/);
  assert.ok(f.calls.some(call=>call.route.endsWith('/cancel')));
});

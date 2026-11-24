'use strict';

// Use the exact uploaded artifact ID. Artifact-service discovery can return an
// empty list even after the public Actions API confirms the completed upload.
async function deployPages({github, context, core, artifactId, recoverRunId, buildVersion,
  timeoutMs=540000, now=Date.now, wait=ms=>new Promise(resolve=>setTimeout(resolve,ms))}) {
  const repo=context.repo;
  if (recoverRunId) {
    if (!/^\d+$/.test(String(recoverRunId))) throw new Error('Invalid recovery workflow run');
    const {data:run}=await github.request('GET /repos/{owner}/{repo}/actions/runs/{run_id}',
      {...repo,run_id:Number(recoverRunId)});
    if (run.head_branch!=='main' || (run.path||'').split('@')[0]!=='.github/workflows/deploy-public-pages.yml') {
      throw new Error('Only this repository main-branch Pages packages can be recovered');
    }
    const {data:list}=await github.request('GET /repos/{owner}/{repo}/actions/runs/{run_id}/artifacts',
      {...repo,run_id:Number(recoverRunId),per_page:100});
    if (list.total_count>list.artifacts.length) throw new Error('Artifact metadata is incomplete');
    const matches=list.artifacts.filter(item=>item.name==='github-pages'&&!item.expired);
    if (matches.length!==1) throw new Error('Recovery requires exactly one unexpired Pages package');
    artifactId=matches[0].id;
    buildVersion=run.head_sha;
  }
  if (!/^\d+$/.test(String(artifactId||'')) || !/^[a-f0-9]{40}$/.test(buildVersion||'')) {
    throw new Error('Missing uploaded Pages artifact ID or build revision');
  }
  const oidc=await core.getIDToken();
  core.setSecret(oidc);
  const {data:deployment}=await github.request('POST /repos/{owner}/{repo}/pages/deployments',
    {...repo,artifact_id:Number(artifactId),pages_build_version:buildVersion,oidc_token:oidc,
      request:{timeout:30000}});
  const deploymentId=deployment.id||deployment.status_url?.split('/').pop()||buildVersion;
  core.info(`Deploying Pages package ${artifactId}`);
  const started=now();
  const finalFailures=new Set(['deployment_failed','deployment_content_failed','deployment_cancelled','deployment_lost']);
  let errors=0;
  try {
    while (now()-started<timeoutMs) {
      let status;
      try {
        const response=await github.request('GET /repos/{owner}/{repo}/pages/deployments/{deployment_id}',
          {...repo,deployment_id:deploymentId,request:{timeout:30000}});
        status=response.data.status;
        errors=0;
      } catch {
        if (++errors>=10) throw new Error('Pages deployment status could not be verified');
        core.info('Retrying temporary Pages status failure');
        await wait(10000);
        continue;
      }
      if (status==='succeed') {
        core.setOutput('page_url',deployment.page_url||`https://${repo.owner}.github.io/${repo.repo}/`);
        core.setOutput('status','succeed');
        core.info('Pages deployment verified');
        return;
      }
      if (finalFailures.has(status)) throw new Error(`Pages deployment ended with ${status}`);
      core.info(`Pages deployment status: ${status||'pending'}`);
      await wait(10000);
    }
    throw new Error('Pages deployment verification timed out');
  } catch (error) {
    try {
      await github.request('POST /repos/{owner}/{repo}/pages/deployments/{deployment_id}/cancel',
        {...repo,deployment_id:deploymentId,request:{timeout:30000}});
    } catch { core.info('Pages cancellation could not be confirmed'); }
    throw error;
  }
}

module.exports={deployPages};

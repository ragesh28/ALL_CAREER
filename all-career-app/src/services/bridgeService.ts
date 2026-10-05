import { Job } from '../types/jobs';

export class ExtensionBridgeService {
  startBatchAutoApply(jobs: Job[]) {
    if (typeof window === 'undefined') return;
    
    const validJobs = jobs.filter(j => j.url && j.url.startsWith('http'));
    if (validJobs.length === 0) {
      alert('No valid application links found in current selection.');
      return;
    }

    // Send postMessage to Chrome extension content script
    window.postMessage({
      type: 'START_BATCH_AUTO_APPLY',
      source: 'ALL_CAREER_WEB',
      jobs: validJobs.map(j => ({
        id: j.id,
        title: j.title,
        company: j.company,
        url: j.url,
        location: j.location
      }))
    }, '*');

    console.log(`[All Career Bridge] Dispatched ${validJobs.length} jobs to Auto-Fill extension.`);
  }

  sendBatchJobsToExtension(urls: string[]) {
    if (typeof window === 'undefined') return;
    window.postMessage({
      type: 'START_BATCH_AUTO_APPLY',
      source: 'ALL_CAREER_WEB',
      jobs: urls.map((url, i) => ({ id: i + 1, url }))
    }, '*');
    console.log(`[All Career Bridge] Dispatched ${urls.length} urls to Auto-Fill extension.`);
  }
}

export const bridgeService = new ExtensionBridgeService();

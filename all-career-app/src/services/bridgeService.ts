import { Job } from '../types/jobs';

export interface BatchProgressJob {
  id?: string | number;
  title?: string;
  company?: string;
  url?: string;
  apply_url?: string;
  location?: string;
  source?: string;
  portal?: string;
  [key: string]: any;
}

export interface BatchState {
  running: boolean;
  paused: boolean;
  cancelled: boolean;
  total: number;
  currentIndex: number;
  appliedCount: number;
  failedCount: number;
  currentJob: BatchProgressJob | null;
  latestItem: any | null;
  isExtensionInstalled: boolean | null;
  showHelperModal: boolean;
  showHistoryModal: boolean;
  history: any[];
}

export type BatchStateSubscriber = (state: BatchState) => void;

export class ExtensionBridgeService {
  private state: BatchState = {
    running: false,
    paused: false,
    cancelled: false,
    total: 0,
    currentIndex: 0,
    appliedCount: 0,
    failedCount: 0,
    currentJob: null,
    latestItem: null,
    isExtensionInstalled: null,
    showHelperModal: false,
    showHistoryModal: false,
    history: []
  };

  private subscribers: Set<BatchStateSubscriber> = new Set();
  private pingPromise: Promise<boolean> | null = null;
  private isInitialized = false;

  constructor() {
    if (typeof window !== 'undefined') {
      this.init();
    }
  }

  private init() {
    if (this.isInitialized) return;
    this.isInitialized = true;

    // Load cached history from localStorage
    try {
      const cached = localStorage.getItem('all_career_apply_history');
      if (cached) {
        this.state.history = JSON.parse(cached);
      }
    } catch (_) {}

    // Listen to messages from content.js / extension bridge
    window.addEventListener('message', (event) => {
      if (!event.data || typeof event.data !== 'object') return;
      const { type, data } = event.data;

      if (type === 'ALL_CAREER_PONG') {
        this.state.isExtensionInstalled = event.data.alive === true;
        this.notify();
      } else if (type === 'ALL_CAREER_BATCH_PROGRESS') {
        if (data) {
          this.state.running = data.running ?? this.state.running;
          this.state.paused = data.paused ?? false;
          this.state.total = data.total ?? this.state.total;
          this.state.currentIndex = data.currentIndex ?? this.state.currentIndex;
          this.state.appliedCount = data.appliedCount ?? this.state.appliedCount;
          this.state.failedCount = data.failedCount ?? this.state.failedCount;
          this.state.currentJob = data.currentJob ?? this.state.currentJob;
          this.state.latestItem = data.latestItem ?? this.state.latestItem;
          if (data.running === false) {
            this.state.running = false;
          }
          this.notify();
        }
      } else if (type === 'ALL_CAREER_START_BATCH_RESPONSE') {
        if (!event.data.success) {
          console.warn('[ExtensionBridge] Batch start error:', event.data.error);
          this.state.running = false;
          this.notify();
        }
      } else if (type === 'ALL_CAREER_STOP_BATCH_RESPONSE' || type === 'ALL_CAREER_STOP_BATCH') {
        this.state.running = false;
        this.state.cancelled = true;
        this.notify();
      } else if (type === 'ALL_CAREER_HISTORY_RESPONSE') {
        if (Array.isArray(event.data.history)) {
          this.state.history = event.data.history;
          try {
            localStorage.setItem('all_career_apply_history', JSON.stringify(this.state.history));
          } catch (_) {}
          this.notify();
        }
      } else if (type === 'ALL_CAREER_CLEAR_HISTORY_RESPONSE') {
        this.state.history = [];
        try {
          localStorage.removeItem('all_career_apply_history');
        } catch (_) {}
        this.notify();
      }
    });

    // Run background ping check
    this.pingExtension().catch(() => {});
  }

  public subscribe(subscriber: BatchStateSubscriber): () => void {
    this.subscribers.add(subscriber);
    subscriber(this.state);
    return () => {
      this.subscribers.delete(subscriber);
    };
  }

  public getState(): BatchState {
    return { ...this.state };
  }

  private notify() {
    const snapshot = { ...this.state };
    this.subscribers.forEach((fn) => {
      try {
        fn(snapshot);
      } catch (err) {
        console.error('[ExtensionBridge] Subscriber error:', err);
      }
    });
  }

  /**
   * Pings the Auto-Fill-V5 extension to verify if it is active
   */
  public pingExtension(timeoutMs = 900): Promise<boolean> {
    if (typeof window === 'undefined') return Promise.resolve(false);

    return new Promise((resolve) => {
      let resolved = false;

      const handler = (event: MessageEvent) => {
        if (event.data?.type === 'ALL_CAREER_PONG') {
          resolved = true;
          window.removeEventListener('message', handler);
          this.state.isExtensionInstalled = event.data.alive === true;
          this.notify();
          resolve(event.data.alive === true);
        }
      };

      window.addEventListener('message', handler);
      window.postMessage({ type: 'ALL_CAREER_PING_EXTENSION' }, '*');

      setTimeout(() => {
        if (!resolved) {
          window.removeEventListener('message', handler);
          this.state.isExtensionInstalled = false;
          this.notify();
          resolve(false);
        }
      }, timeoutMs);
    });
  }

  /**
   * Dispatches a batch of jobs to the Auto-Fill-V5 Extension
   */
  public async startBatchAutoApply(jobs: (Job | any)[]): Promise<void> {
    if (typeof window === 'undefined') return;

    // Toggle to STOP if already running
    if (this.state.running) {
      this.stopBatchAutoApply();
      return;
    }

    // Filter valid application targets
    const validJobs = jobs
      .map((j, idx) => {
        const rawUrl = (j.apply_url || j.url || j.link || j.telegram_url || '').trim();
        return {
          id: j.id || `job_${idx + 1}`,
          title: (j.title || j.role || 'Job Opening').trim(),
          company: (j.company || 'Enterprise Company').trim(),
          url: rawUrl,
          apply_url: rawUrl,
          location: j.location || 'India',
          source: j.source || j.portal || this.detectPortal(j),
          portal: j.source || j.portal || this.detectPortal(j),
          experience: j.experience || ''
        };
      })
      .filter((j) => j.url && (j.url.startsWith('http://') || j.url.startsWith('https://')));

    if (validJobs.length === 0) {
      alert('No valid web application links found in current selection.');
      return;
    }

    // Ping extension to verify presence
    const isReady = await this.pingExtension(750);
    if (!isReady) {
      this.state.showHelperModal = true;
      this.notify();
      return;
    }

    // Initialize local running state
    this.state.running = true;
    this.state.cancelled = false;
    this.state.paused = false;
    this.state.total = validJobs.length;
    this.state.currentIndex = 0;
    this.state.appliedCount = 0;
    this.state.failedCount = 0;
    this.state.currentJob = validJobs[0] || null;
    this.state.latestItem = null;
    this.notify();

    // 1. Post native Auto-Fill-V5 format
    window.postMessage(
      {
        type: 'ALL_CAREER_START_BATCH',
        data: { jobs: validJobs }
      },
      '*'
    );

    // 2. Also post legacy compatible payload
    window.postMessage(
      {
        type: 'START_BATCH_AUTO_APPLY',
        source: 'ALL_CAREER_WEB',
        jobs: validJobs
      },
      '*'
    );

    console.log(`[All Career Bridge] Successfully dispatched ${validJobs.length} jobs to Auto-Fill-V5.`);
  }

  public sendBatchJobsToExtension(urls: string[]): void {
    const jobs = urls.map((url, i) => ({
      id: `url_${i + 1}`,
      title: 'Job Opening',
      company: 'Company',
      url: url,
      apply_url: url
    }));
    this.startBatchAutoApply(jobs);
  }

  public stopBatchAutoApply(): void {
    if (typeof window === 'undefined') return;

    this.state.running = false;
    this.state.cancelled = true;
    this.notify();

    window.postMessage({ type: 'ALL_CAREER_STOP_BATCH' }, '*');
    window.postMessage({ type: 'STOP_BATCH_AUTO_APPLY' }, '*');
    console.log('[All Career Bridge] Dispatched STOP signal to Auto-Fill-V5.');
  }

  public openHistory(): void {
    this.state.showHistoryModal = true;
    this.notify();
    this.requestHistory();
  }

  public closeHistory(): void {
    this.state.showHistoryModal = false;
    this.notify();
  }

  public closeHelperModal(): void {
    this.state.showHelperModal = false;
    this.notify();
  }

  public requestHistory(): void {
    if (typeof window === 'undefined') return;
    window.postMessage({ type: 'ALL_CAREER_GET_HISTORY' }, '*');
  }

  public clearHistory(): void {
    if (typeof window === 'undefined') return;
    this.state.history = [];
    try {
      localStorage.removeItem('all_career_apply_history');
    } catch (_) {}
    this.notify();
    window.postMessage({ type: 'ALL_CAREER_CLEAR_HISTORY' }, '*');
  }

  public detectPortal(job: any): string {
    const text = `${job.url || ''} ${job.source || ''} ${job.company || ''} ${job.title || ''}`.toLowerCase();
    if (text.includes('naukri')) return 'Naukri';
    if (text.includes('linkedin')) return 'LinkedIn';
    if (text.includes('indeed')) return 'Indeed';
    if (text.includes('internshala')) return 'Internshala';
    if (text.includes('unstop')) return 'Unstop';
    if (text.includes('foundit') || text.includes('monster')) return 'Foundit';
    if (text.includes('greenhouse')) return 'Greenhouse ATS';
    if (text.includes('lever.co')) return 'Lever ATS';
    if (text.includes('myworkdayjobs') || text.includes('workday')) return 'Workday';
    if (text.includes('smartrecruiters')) return 'SmartRecruiters';
    return 'Company Portal';
  }
}

export const bridgeService = new ExtensionBridgeService();

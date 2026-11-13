import { env, createExecutionContext, SELF } from 'cloudflare:test';
import { describe, it, expect } from 'vitest';
import worker from '../src/index';

describe('LeetCode worker', () => {
  it('returns 404 for unknown routes', async () => {
    const response = await worker.fetch(new Request('http://example.com/unknown'), env, createExecutionContext());
    expect(response.status).toBe(404);
    expect(await response.text()).toBe('Not Found');
  });

  it('requires a company name', async () => {
    const response = await SELF.fetch('https://example.com/api/company');
    expect(response.status).toBe(400);
    expect(await response.json()).toEqual({ error: 'Missing company name parameter' });
  });
});

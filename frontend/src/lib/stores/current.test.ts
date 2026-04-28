import { get } from 'svelte/store';
import { describe, expect, it, beforeEach } from 'vitest';

import { current, openMemo, reset } from './current';

describe('current store', () => {
  beforeEach(() => {
    reset();
  });

  it('initial state is idle screen with no job', () => {
    const state = get(current);
    expect(state.screen).toBe('idle');
    expect(state.jobId).toBeNull();
    expect(state.job).toBeNull();
    expect(state.initialTime).toBeUndefined();
  });

  it('reset() returns store to initial state from any state', () => {
    current.set({
      screen: 'ready',
      jobId: 'abc',
      job: null,
      progress: 1,
      stageMessage: 'hi',
      errorMessage: null,
      initialTime: 42,
    });
    reset();
    const state = get(current);
    expect(state.screen).toBe('idle');
    expect(state.jobId).toBeNull();
    expect(state.initialTime).toBeUndefined();
  });

  it('openMemo() switches to ready screen and seeds initialTime', () => {
    openMemo('job-xyz', 123.5);
    const state = get(current);
    expect(state.screen).toBe('ready');
    expect(state.jobId).toBe('job-xyz');
    expect(state.initialTime).toBe(123.5);
  });

  it('openMemo() then reset() clears initialTime', () => {
    openMemo('job-xyz', 123.5);
    reset();
    const state = get(current);
    expect(state.initialTime).toBeUndefined();
  });
});

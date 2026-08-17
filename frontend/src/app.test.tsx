// @vitest-environment jsdom
import axios from 'axios';
import { beforeEach, describe, expect, it, vi } from 'vitest';

vi.mock('./api/client', () => ({
  apiClient: {
    get: vi.fn(),
    post: vi.fn(),
    patch: vi.fn(),
  },
}));

import { apiClient } from './api/client';
import { handleApiError } from './api/errors';
import { completeTask, registerForTask } from './api/volunteer';

const mockedPost = vi.mocked(apiClient.post);

describe('FastAPI contracts', () => {
  beforeEach(() => vi.clearAllMocks());

  it('registers a volunteer with the backend user_id contract', async () => {
    mockedPost.mockResolvedValueOnce({ data: { status: 'registered' } });
    await registerForTask(7, 'volunteer-1');
    expect(mockedPost).toHaveBeenCalledWith('/api/volunteer/tasks/7/register', { user_id: 'volunteer-1' });
  });

  it('completes a task with dispatcher_id and never invents evidence_url', async () => {
    mockedPost.mockResolvedValueOnce({ data: { status: 'completed' } });
    await completeTask(7, 'volunteer-1', 'dispatcher-1');
    expect(mockedPost).toHaveBeenCalledWith('/api/volunteer/tasks/7/complete', {
      user_id: 'volunteer-1',
      dispatcher_id: 'dispatcher-1',
    });
  });
});

describe('API error normalization', () => {
  it('does not mark a 409 conflict as retryable', () => {
    const error = new axios.AxiosError('Conflict', 'ERR_BAD_REQUEST', undefined, undefined, {
      status: 409,
      statusText: 'Conflict',
      headers: {},
      config: { headers: new axios.AxiosHeaders() },
      data: { detail: 'User is already registered for this task' },
    });
    const normalized = handleApiError(error);
    expect(normalized.retryable).toBe(false);
    expect(normalized.message).toContain('already registered');
  });
});

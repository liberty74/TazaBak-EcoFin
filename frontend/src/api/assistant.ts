import { apiClient } from './client';
import type { AIChatRequest, AIChatResponse } from './types';

export const chatWithAssistant = async (message: string, userId?: string | number): Promise<AIChatResponse> => {
  const payload: AIChatRequest = { message };
  if (userId !== undefined) {
    payload.user_id = userId.toString();
  }
  const response = await apiClient.post<AIChatResponse>('/api/ai/chat', payload);
  return response.data;
};

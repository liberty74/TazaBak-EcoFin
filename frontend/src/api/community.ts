import { apiClient } from './client';
import { ForumMessage } from './types';

export const fetchCommunityChat = async (limit: number = 50): Promise<ForumMessage[]> => {
  const response = await apiClient.get('/api/community/chat', { params: { limit } });
  return response.data;
};

export const postCommunityMessage = async (username: string, text: string) => {
  const response = await apiClient.post('/api/community/chat', { username, text });
  return response.data;
};

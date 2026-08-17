import { apiClient } from './client';
import { Container } from './types';

export const fetchContainers = async (activeOnly: boolean = true): Promise<Container[]> => {
  const response = await apiClient.get('/api/containers', { params: { active_only: activeOnly } });
  return response.data;
};

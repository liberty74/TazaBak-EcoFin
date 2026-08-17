import { apiClient } from './client';
import type { VolunteerCompleteResponse, VolunteerRegisterResponse, VolunteerTask } from './types';

export const fetchVolunteerTasks = async (includeCompleted: boolean = false): Promise<VolunteerTask[]> => {
  const response = await apiClient.get('/api/volunteer/tasks', { params: { include_completed: includeCompleted } });
  return response.data;
};

export const registerForTask = async (taskId: number, userId: string | number): Promise<VolunteerRegisterResponse> => {
  const response = await apiClient.post<VolunteerRegisterResponse>(`/api/volunteer/tasks/${taskId}/register`, {
    user_id: userId.toString(),
  });
  return response.data;
};

export const completeTask = async (
  taskId: number,
  userId: string | number,
  dispatcherId: string | number,
): Promise<VolunteerCompleteResponse> => {
  const response = await apiClient.post<VolunteerCompleteResponse>(`/api/volunteer/tasks/${taskId}/complete`, {
    user_id: userId.toString(),
    dispatcher_id: dispatcherId.toString(),
  });
  return response.data;
};

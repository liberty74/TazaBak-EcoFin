import { apiClient } from './client';
import { BioResponse } from './types';

export const analyzeBio = async (
  file: File,
  userId: string | number,
  deviceId: string,
  idempotencyKey: string
): Promise<BioResponse> => {
  const formData = new FormData();
  formData.append('file', file);
  formData.append('user_id', userId.toString());
  formData.append('device_id', deviceId);
  formData.append('idempotency_key', idempotencyKey);

  const response = await apiClient.post('/api/bio/analyze', formData, {
    // Axios handles multipart/form-data boundary automatically when passing FormData
  });
  return response.data;
};

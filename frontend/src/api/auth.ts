import { apiClient } from './client';
import type { LoginRequest, RegisterRequest, UserProfile } from './types';

export async function login(payload: LoginRequest): Promise<UserProfile> {
  const response = await apiClient.post<UserProfile>('/api/auth/login', payload);
  return response.data;
}

export async function register(payload: RegisterRequest): Promise<UserProfile> {
  const response = await apiClient.post<UserProfile>('/api/auth/register', payload);
  return response.data;
}

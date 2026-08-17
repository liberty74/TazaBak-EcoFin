import { apiClient } from './client';
import { UserProfile, Dashboard, PointTransaction, EcoNFT } from './types';

export const fetchUserProfile = async (userId: string | number): Promise<UserProfile> => {
  const response = await apiClient.get(`/api/users/${userId}`);
  return response.data;
};

export const fetchUserDashboard = async (userId: string | number): Promise<Dashboard> => {
  const response = await apiClient.get(`/api/users/${userId}/dashboard`);
  return response.data;
};

export const fetchUserTransactions = async (userId: string | number, limit = 10, beforeId?: number): Promise<PointTransaction[]> => {
  const params = new URLSearchParams();
  params.append('limit', limit.toString());
  if (beforeId !== undefined) {
    params.append('before_id', beforeId.toString());
  }
  const response = await apiClient.get(`/api/users/${userId}/transactions`, { params });
  return response.data;
};

export const fetchUserNfts = async (userId: string | number): Promise<EcoNFT[]> => {
  const response = await apiClient.get(`/api/users/${userId}/nfts`);
  return response.data;
};

export const fetchLeaderboard = async (limit = 10): Promise<UserProfile[]> => {
  const response = await apiClient.get(`/api/leaderboard`, { params: { limit } });
  return response.data;
};

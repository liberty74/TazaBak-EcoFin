import { apiClient } from './client';
import type { CameraAnalysis, CameraStreamUpdate, DispatchSummary, DispatchBriefing, DeviceCommandResponse, DeviceTelemetryStatus, ResolveAlertResponse } from './types';

export const fetchDispatchSummary = async (): Promise<DispatchSummary> => {
  const response = await apiClient.get('/api/dispatch/summary');
  return response.data;
};

export const fetchDispatchBriefing = async (): Promise<DispatchBriefing> => {
  const response = await apiClient.get('/api/dispatch/briefing');
  return response.data;
};

export const resolveAlert = async (alertId: number): Promise<ResolveAlertResponse> => {
  const response = await apiClient.patch<ResolveAlertResponse>(`/api/alerts/${alertId}/resolve`);
  return response.data;
};

export const sendDeviceCommand = async (
  deviceId: string,
  dispatcherId: string | number,
  action: 'OPEN_LID' | 'CLOSE_LID',
  idempotencyKey: string
): Promise<DeviceCommandResponse> => {
  const response = await apiClient.post(`/api/dispatcher/devices/${deviceId}/command`, {
    dispatcher_id: dispatcherId.toString(),
    action,
    idempotency_key: idempotencyKey,
  });
  return response.data;
};

export const fetchCommands = async (deviceId?: string, status?: string, limit = 50): Promise<DeviceCommandResponse[]> => {
  const params = new URLSearchParams();
  params.append('limit', limit.toString());
  if (deviceId) params.append('device_id', deviceId);
  if (status) params.append('status', status);
  
  const response = await apiClient.get('/api/dispatcher/commands', { params });
  return response.data;
};

export const fetchDeviceStatuses = async (): Promise<DeviceTelemetryStatus[]> => {
  const response = await apiClient.get<DeviceTelemetryStatus[]>('/api/dispatcher/devices/status');
  return response.data;
};

export const updateCameraStream = async (deviceId: string, streamUrl: string): Promise<DeviceTelemetryStatus> => {
  const payload: CameraStreamUpdate = { stream_url: streamUrl };
  const response = await apiClient.put<DeviceTelemetryStatus>(`/api/dispatcher/devices/${deviceId}/camera`, payload);
  return response.data;
};

export const fetchLatestCameraAnalysis = async (deviceId: string): Promise<CameraAnalysis> => {
  const response = await apiClient.get<CameraAnalysis>(`/api/dispatcher/devices/${deviceId}/camera/analysis`);
  return response.data;
};

export const analyzeCameraNow = async (deviceId: string): Promise<CameraAnalysis> => {
  const response = await apiClient.post<CameraAnalysis>(`/api/dispatcher/devices/${deviceId}/camera/analyze`);
  return response.data;
};

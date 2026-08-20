import { apiClient } from './client';
import type {
  BusinessForecast,
  ContainerForecast,
  EcoCostProfile,
  EcoRecommendations,
  RevenueModel,
  RoutePlan,
  SavingsReport,
  WriteOffCreate,
  WriteOffRecord,
} from './types';

/** Отчёт об экономии за период. Публичный: только агрегированные данные. */
export const fetchSavings = async (days = 30): Promise<SavingsReport> => {
  const response = await apiClient.get<SavingsReport>('/api/eco/savings', {
    params: { days },
  });
  return response.data;
};

export const fetchForecast = async (): Promise<ContainerForecast[]> => {
  const response = await apiClient.get<ContainerForecast[]>('/api/eco/forecast');
  return response.data;
};

export const fetchRoutePlan = async (horizonHours = 24): Promise<RoutePlan> => {
  const response = await apiClient.get<RoutePlan>('/api/eco/route', {
    params: { horizon_hours: horizonHours },
  });
  return response.data;
};

export const fetchRecommendations = async (days = 30): Promise<EcoRecommendations> => {
  const response = await apiClient.get<EcoRecommendations>('/api/eco/recommendations', {
    params: { days },
  });
  return response.data;
};

export const fetchBusinessForecast = async (
  target?: string,
  weeks = 4,
): Promise<BusinessForecast> => {
  const params: Record<string, string | number> = { weeks };
  if (target) params.target = target;
  const response = await apiClient.get<BusinessForecast>('/api/eco/business/forecast', {
    params,
  });
  return response.data;
};

export const fetchEcoProfile = async (): Promise<EcoCostProfile> => {
  const response = await apiClient.get<EcoCostProfile>('/api/eco/profile');
  return response.data;
};

export const fetchWriteOffs = async (limit = 60): Promise<WriteOffRecord[]> => {
  const response = await apiClient.get<WriteOffRecord[]>('/api/eco/write-offs', {
    params: { limit },
  });
  return response.data;
};

/** Один день и один продукт — одна запись: повторная отправка исправляет
 *  цифры, а не удваивает их. */
export const saveWriteOff = async (payload: WriteOffCreate): Promise<WriteOffRecord> => {
  const response = await apiClient.put<WriteOffRecord>('/api/eco/write-offs', payload);
  return response.data;
};

/** Модель доходов. Публичная: бизнес-модель — аргумент, а не секрет.
 *  Проекция приходит, только если запросили масштаб. */
export const fetchRevenue = async (
  days = 30,
  projectionContainers?: number,
): Promise<RevenueModel> => {
  const params: Record<string, number> = { days };
  if (projectionContainers) params.projection_containers = projectionContainers;
  const response = await apiClient.get<RevenueModel>('/api/eco/revenue', { params });
  return response.data;
};

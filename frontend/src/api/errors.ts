import axios from 'axios';
import type { FastAPIValidationError } from './types';

export interface NormalizedError {
  status?: number;
  title: string;
  message: string;
  fieldErrors?: Record<string, string>;
  retryable: boolean;
}

function isValidationError(value: unknown): value is FastAPIValidationError {
  if (typeof value !== 'object' || value === null) return false;
  const candidate = value as Record<string, unknown>;
  return Array.isArray(candidate.loc) && typeof candidate.msg === 'string';
}

function extractDetail(data: unknown): unknown {
  return typeof data === 'object' && data !== null ? (data as Record<string, unknown>).detail : undefined;
}

export function handleApiError(error: unknown): NormalizedError {
  if (axios.isAxiosError(error)) {
    const status = error.response?.status;
    let detail: unknown = extractDetail(error.response?.data);
    let fieldErrors: Record<string, string> | undefined;

    if (Array.isArray(detail)) {
      fieldErrors = {};
      detail.filter(isValidationError).forEach((err) => {
        fieldErrors![err.loc.join('.')] = err.msg;
      });
      detail = 'Validation error';
    } else if (typeof detail === 'object' && detail !== null) {
      detail = JSON.stringify(detail);
    }

    const message = typeof detail === 'string' && detail ? detail : undefined;

    if (!status) {
      return {
        title: 'Ошибка сети',
        message: 'Не удалось подключиться к FastAPI. Проверьте, запущен ли backend на http://127.0.0.1:8000',
        retryable: true,
      };
    }

    switch (status) {
      case 400:
        return { status, title: 'Некорректный запрос', message: message || 'Проверьте введённые данные', retryable: false };
      case 403:
        return { status, title: 'Доступ запрещён', message: message || 'Недостаточно прав или неверный ключ диспетчера', retryable: false };
      case 404:
        return { status, title: 'Не найдено', message: message || 'Ресурс не найден', retryable: false };
      case 409:
        return { status, title: 'Конфликт', message: message || 'Операция уже выполнена или состояние изменилось', retryable: false };
      case 413:
        return { status, title: 'Payload Too Large', message: 'Файл слишком большой', retryable: false };
      case 415:
        return { status, title: 'Unsupported Media Type', message: 'Неподдерживаемый формат изображения', retryable: false };
      case 422:
        return { status, title: 'Unprocessable Entity', message: 'Ошибка валидации данных', fieldErrors, retryable: false };
      case 500:
        return { status, title: 'Internal Server Error', message: 'Внутренняя ошибка сервера', retryable: true };
      case 503:
        return { status, title: 'Service Unavailable', message: 'AI-анализ временно недоступен', retryable: true };
      default:
        return { status, title: 'Ошибка', message: message || error.message, retryable: status >= 500 };
    }
  }

  return {
    title: 'Unknown Error',
    message: error instanceof Error ? error.message : 'Произошла неизвестная ошибка',
    retryable: false,
  };
}

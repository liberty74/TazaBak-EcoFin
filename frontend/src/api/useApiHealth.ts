import { useEffect, useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { fetchHealth } from './health';

export type HealthStatus = 'checking' | 'connected' | 'db_error' | 'disconnected';

export function useApiHealth() {
  const [isTabActive, setIsTabActive] = useState(!document.hidden);

  useEffect(() => {
    const handleVisibilityChange = () => {
      setIsTabActive(!document.hidden);
    };
    document.addEventListener('visibilitychange', handleVisibilityChange);
    return () => document.removeEventListener('visibilitychange', handleVisibilityChange);
  }, []);

  const { data, isPending, isError, error } = useQuery({
    queryKey: ['api-health'],
    queryFn: fetchHealth,
    refetchInterval: isTabActive ? 25000 : false,
    retry: 1, // Avoid aggressive retries
    retryDelay: 3000,
  });

  let status: HealthStatus = 'checking';
  if (isPending) {
    status = 'checking';
  } else if (isError) {
    status = 'disconnected';
  } else if (data) {
    if (data.status === 'ok' && data.database === 'reachable') {
      status = 'connected';
    } else {
      status = 'db_error';
    }
  }

  return { status, data, isError, error };
}

import React, { useState, useEffect } from 'react';
import { useAuth } from '../../store/AuthContext';
import DispatcherKeyDialog from '../common/DispatcherKeyDialog';

export default function DispatcherKeyGate({ children }: { children: React.ReactNode }) {
  const { user, logout } = useAuth();
  const [hasKey, setHasKey] = useState(!!sessionStorage.getItem('dispatcherKey'));

  useEffect(() => {
    const handleAuthFailed = () => {
      sessionStorage.removeItem('dispatcherKey');
      setHasKey(false);
    };

    window.addEventListener('dispatcher-auth-failed', handleAuthFailed);
    return () => {
      window.removeEventListener('dispatcher-auth-failed', handleAuthFailed);
    };
  }, []);

  // Sync state if sessionStorage is updated
  useEffect(() => {
    const checkKey = () => {
      const key = sessionStorage.getItem('dispatcherKey');
      setHasKey(!!key);
    };
    
    // Check key occasionally
    const interval = setInterval(checkKey, 1000);
    return () => clearInterval(interval);
  }, []);

  if (!user || user.role !== 'dispatcher') {
    return <>{children}</>;
  }

  const handleSuccess = (key: string) => {
    sessionStorage.setItem('dispatcherKey', key.trim());
    setHasKey(true);
  };

  if (!hasKey) {
    return (
      <div className="min-h-screen bg-background flex flex-col items-center justify-center p-4">
        <div className="bg-card border border-border rounded-3xl p-8 max-w-md w-full text-center shadow-xl space-y-6">
          <div className="w-16 h-16 rounded-full bg-critical/10 text-critical flex items-center justify-center mx-auto">
            <svg className="w-8 h-8" fill="none" stroke="currentColor" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z"></path>
            </svg>
          </div>
          <div>
            <h2 className="text-2xl font-bold text-foreground">Требуется Ключ Диспетчера</h2>
            <p className="text-sm text-foreground/50 mt-2">Пожалуйста, введите X-Dispatcher-Key для доступа к панели.</p>
          </div>
          <div className="flex flex-col gap-3">
            <button 
              onClick={logout}
              className="w-full py-3 bg-muted text-foreground hover:bg-muted/80 rounded-xl text-sm font-bold transition-all cursor-pointer min-h-[44px]"
            >
              Выйти из сессии
            </button>
          </div>
        </div>

        <DispatcherKeyDialog 
          isOpen={true}
          onClose={() => {}} 
          onSuccess={handleSuccess}
          username={user.username}
        />
      </div>
    );
  }

  return <>{children}</>;
}

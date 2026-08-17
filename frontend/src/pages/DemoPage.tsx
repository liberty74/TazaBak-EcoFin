import React, { useState, useEffect, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../store/AuthContext';
import { useLocaleTheme } from '../store/LocaleThemeContext';
import { User, HeartHandshake, ShieldAlert, Leaf, Loader2 } from 'lucide-react';
import { login } from '../api/auth';
import { handleApiError } from '../api/errors';
import DispatcherKeyDialog from '../components/common/DispatcherKeyDialog';
import AuthDialog from '../components/common/AuthDialog';
import type { UserProfile } from '../api/types';

export default function DemoPage() {
  const { setRole } = useAuth();
  const { t } = useLocaleTheme();
  const navigate = useNavigate();
  const [loading, setLoading] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  // Dispatcher Key Modal States
  const [showKeyModal, setShowKeyModal] = useState(false);
  const [pendingUsername, setPendingUsername] = useState('');
  const [showAuthModal, setShowAuthModal] = useState(false);
  const [authMode, setAuthMode] = useState<'login' | 'register'>('login');
  const [authUsername, setAuthUsername] = useState('');
  const dispatcherButtonRef = useRef<HTMLButtonElement>(null);

  const handleCloseModal = () => {
    setShowKeyModal(false);
  };

  const handleAuthenticated = (profile: UserProfile) => {
    setShowAuthModal(false);
    if (profile.role === 'dispatcher') {
      setPendingUsername(profile.username);
      setShowKeyModal(true);
      return;
    }
    setRole(profile.role, profile.username);
    navigate('/home');
  };

  const openAuth = (mode: 'login' | 'register', username = '') => {
    setAuthMode(mode);
    setAuthUsername(username);
    setShowAuthModal(true);
  };

  const handleDemoLogin = async (role: 'user' | 'volunteer' | 'dispatcher', username: string) => {
    setLoading(role);
    setError(null);
    try {
      const profile = await login({ username, password: '123' });
      handleAuthenticated(profile);
    } catch (e: unknown) {
      const normErr = handleApiError(e);
      setError(`Ошибка авторизации (${normErr.status || 'Network'}): ${normErr.message}`);
    } finally {
      setLoading(null);
    }
  };

  return (
    <div className="min-h-screen bg-background flex flex-col items-center justify-center p-4 relative overflow-hidden">
      {/* Decorative background pattern */}
      <div className="absolute inset-0 opacity-[0.03] pointer-events-none" style={{ backgroundImage: 'radial-gradient(var(--color-primary) 2px, transparent 2px)', backgroundSize: '32px 32px' }} />
      
      <div className="z-10 w-full max-w-4xl flex flex-col items-center">
        <div className="mb-12 text-center">
          <div className="flex items-center justify-center gap-4 mb-8">
            <img src="/logo.svg" alt="TazaBAK" className="h-16 object-contain" />
          </div>
          <div className="inline-flex items-center gap-2 bg-white dark:bg-card px-4 py-2 rounded-full text-primary font-semibold shadow-sm mb-6 border border-sand dark:border-border">
            <Leaf className="w-5 h-5" />
            <span>TazaBAK Hackathon</span>
          </div>
          <h1 className="text-4xl md:text-5xl font-extrabold text-primary mb-4 tracking-tight">{t('welcomeTitle')}</h1>
          <p className="text-xl text-graphite/80 dark:text-foreground/80">{t('welcomeSub')}</p>
          <div className="mt-6 inline-block bg-accent/20 border border-accent/40 text-primary-light font-bold px-4 py-2 rounded-lg">
            «Хлеб не отход. Хлеб — помощь.»
          </div>
        </div>

        {error && (
          <div className="mb-6 w-full max-w-xl bg-critical/10 border border-critical/30 text-critical px-6 py-4 rounded-xl text-center font-medium shadow-sm">
            {error}
          </div>
        )}

        <div className="mb-6 flex flex-wrap justify-center gap-3">
          <button onClick={() => openAuth('login')} className="rounded-xl border border-primary/30 bg-white px-5 py-3 font-bold text-primary shadow-sm transition-colors hover:bg-primary/5">Войти</button>
          <button onClick={() => openAuth('register')} className="rounded-xl bg-primary px-5 py-3 font-bold text-white shadow-sm transition-colors hover:bg-primary/90">Создать аккаунт</button>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-6 w-full">
          {/* User Card */}
          <button 
            onClick={() => handleDemoLogin('user', '123')}
            disabled={loading !== null}
            className="group flex flex-col items-center text-center bg-white dark:bg-card p-8 rounded-3xl shadow-sm border border-sand dark:border-border hover:shadow-xl hover:-translate-y-1 transition-all duration-300 relative overflow-hidden cursor-pointer"
          >
            <div className="absolute top-0 left-0 w-full h-1 bg-primary scale-x-0 group-hover:scale-x-100 transition-transform origin-left duration-300" />
            <div className="w-16 h-16 rounded-2xl bg-cream dark:bg-muted flex items-center justify-center text-primary group-hover:bg-primary group-hover:text-white transition-colors mb-6">
              <User className="w-8 h-8" />
            </div>
            <h2 className="text-2xl font-bold mb-2 dark:text-white">Житель</h2>
            <p className="text-sm text-graphite/60 dark:text-foreground/60 font-mono mb-4 bg-cream dark:bg-muted px-2 py-1 rounded">Account: 123</p>
            <p className="text-graphite dark:text-foreground/70 flex-1">Сдавайте хлеб, копите баллы, создавайте NFT и участвуйте в жизни города.</p>
            <div className="mt-8 w-full py-3 bg-primary text-white rounded-xl font-semibold opacity-100 lg:opacity-0 lg:group-hover:opacity-100 transition-opacity flex items-center justify-center gap-2">
              {loading === 'user' ? <Loader2 className="w-5 h-5 animate-spin" /> : 'Войти как Житель'}
            </div>
          </button>

          {/* Volunteer Card */}
          <button 
            onClick={() => handleDemoLogin('volunteer', 'volunteer-1')}
            disabled={loading !== null}
            className="group flex flex-col items-center text-center bg-white dark:bg-card p-8 rounded-3xl shadow-sm border border-sand dark:border-border hover:shadow-xl hover:-translate-y-1 transition-all duration-300 relative overflow-hidden cursor-pointer"
          >
            <div className="absolute top-0 left-0 w-full h-1 bg-bread scale-x-0 group-hover:scale-x-100 transition-transform origin-left duration-300" />
            <div className="w-16 h-16 rounded-2xl bg-cream dark:bg-muted flex items-center justify-center text-bread group-hover:bg-bread group-hover:text-white transition-colors mb-6">
              <HeartHandshake className="w-8 h-8" />
            </div>
            <h2 className="text-2xl font-bold mb-2 dark:text-white">Волонтёр</h2>
            <p className="text-sm text-graphite/60 dark:text-foreground/60 font-mono mb-4 bg-cream dark:bg-muted px-2 py-1 rounded">Account: volunteer-1</p>
            <p className="text-graphite dark:text-foreground/70 flex-1">Помогайте приютам, выполняйте задания по сбору и участвуйте в спасении животных.</p>
            <div className="mt-8 w-full py-3 bg-bread text-white rounded-xl font-semibold opacity-100 lg:opacity-0 lg:group-hover:opacity-100 transition-opacity flex items-center justify-center gap-2">
              {loading === 'volunteer' ? <Loader2 className="w-5 h-5 animate-spin" /> : 'Войти как Волонтёр'}
            </div>
          </button>

          {/* Dispatcher Card */}
          <button 
            ref={dispatcherButtonRef}
            onClick={() => handleDemoLogin('dispatcher', 'dispatcher-1')}
            disabled={loading !== null}
            className="group flex flex-col items-center text-center bg-white dark:bg-card p-8 rounded-3xl shadow-sm border border-sand dark:border-border hover:shadow-xl hover:-translate-y-1 transition-all duration-300 relative overflow-hidden cursor-pointer"
          >
            <div className="absolute top-0 left-0 w-full h-1 bg-critical scale-x-0 group-hover:scale-x-100 transition-transform origin-left duration-300" />
            <div className="w-16 h-16 rounded-2xl bg-cream dark:bg-muted flex items-center justify-center text-critical group-hover:bg-critical group-hover:text-white transition-colors mb-6">
              <ShieldAlert className="w-8 h-8" />
            </div>
            <h2 className="text-2xl font-bold mb-2 dark:text-white">Диспетчер</h2>
            <p className="text-sm text-graphite/60 dark:text-foreground/60 font-mono mb-4 bg-cream dark:bg-muted px-2 py-1 rounded">Account: dispatcher-1</p>
            <p className="text-graphite dark:text-foreground/70 flex-1">Контролируйте состояние контейнеров, обрабатывайте алерты и управляйте IoT-устройствами.</p>
            <div className="mt-8 w-full py-3 bg-critical text-white rounded-xl font-semibold opacity-100 lg:opacity-0 lg:group-hover:opacity-100 transition-opacity flex items-center justify-center gap-2">
              {loading === 'dispatcher' ? <Loader2 className="w-5 h-5 animate-spin" /> : 'Войти как Диспетчер'}
            </div>
          </button>
        </div>

        <div className="mt-12 text-graphite/50 text-sm flex items-center gap-2">
          <span></span>
        </div>
      </div>

      <DispatcherKeyDialog 
        isOpen={showKeyModal} 
        onClose={handleCloseModal} 
        onSuccess={(key) => { 
          setRole('dispatcher', pendingUsername); 
          setShowKeyModal(false); 
          navigate('/dispatcher'); 
        }} 
        username={pendingUsername} 
        returnFocusRef={dispatcherButtonRef}
      />
      <AuthDialog
        isOpen={showAuthModal}
        mode={authMode}
        initialUsername={authUsername}
        onClose={() => setShowAuthModal(false)}
        onAuthenticated={handleAuthenticated}
      />
    </div>
  );
}

import { useEffect, useState } from 'react';
import { Loader2, LogIn, UserPlus, X } from 'lucide-react';
import { handleApiError, login, register } from '../../api';
import type { UserProfile } from '../../api/types';

type AuthMode = 'login' | 'register';

interface AuthDialogProps {
  isOpen: boolean;
  mode: AuthMode;
  initialUsername?: string;
  onClose: () => void;
  onAuthenticated: (profile: UserProfile) => void;
}

export default function AuthDialog({
  isOpen,
  mode: initialMode,
  initialUsername = '',
  onClose,
  onAuthenticated,
}: AuthDialogProps) {
  const [mode, setMode] = useState<AuthMode>(initialMode);
  const [username, setUsername] = useState(initialUsername);
  const [password, setPassword] = useState('');
  const [role, setRole] = useState<'user' | 'volunteer'>('user');
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!isOpen) return;
    setMode(initialMode);
    setUsername(initialUsername);
    setPassword('');
    setRole('user');
    setError(null);
  }, [isOpen, initialMode, initialUsername]);

  if (!isOpen) return null;

  const submit = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setSubmitting(true);
    setError(null);
    try {
      const profile = mode === 'login'
        ? await login({ username, password })
        : await register({ username, password, role });
      onAuthenticated(profile);
    } catch (exception: unknown) {
      const normalized = handleApiError(exception);
      setError(normalized.message);
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4" role="dialog" aria-modal="true" aria-labelledby="auth-dialog-title">
      <div className="relative w-full max-w-md rounded-3xl border border-sand bg-white p-6 shadow-2xl dark:border-border dark:bg-card">
        <button onClick={onClose} disabled={submitting} className="absolute right-4 top-4 rounded-full p-2 text-graphite/50 hover:bg-cream hover:text-graphite" aria-label="Закрыть">
          <X className="h-5 w-5" />
        </button>
        <div className="mb-6 pr-8">
          <h2 id="auth-dialog-title" className="text-2xl font-bold text-graphite dark:text-white">
            {mode === 'login' ? 'Вход в Миску добра' : 'Создать аккаунт'}
          </h2>
          <p className="mt-1 text-sm text-graphite/60">{mode === 'login' ? 'Введите данные своего аккаунта.' : 'Присоединяйтесь к экосообществу Кокшетау.'}</p>
        </div>

        <div className="mb-5 grid grid-cols-2 rounded-xl bg-cream p-1 text-sm font-bold dark:bg-muted">
          <button type="button" onClick={() => { setMode('login'); setError(null); }} className={`rounded-lg py-2 ${mode === 'login' ? 'bg-white text-primary shadow-sm dark:bg-card' : 'text-graphite/60'}`}>Войти</button>
          <button type="button" onClick={() => { setMode('register'); setError(null); }} className={`rounded-lg py-2 ${mode === 'register' ? 'bg-white text-primary shadow-sm dark:bg-card' : 'text-graphite/60'}`}>Регистрация</button>
        </div>

        <form onSubmit={submit} className="space-y-4">
          <label className="block text-sm font-semibold text-graphite">
            Логин
            <input value={username} onChange={(event) => setUsername(event.target.value)} required minLength={mode === 'register' ? 3 : 1} maxLength={64} autoComplete="username" className="mt-1 w-full rounded-xl border border-sand bg-background px-3 py-2.5 outline-none focus:ring-2 focus:ring-primary/30" placeholder="например, aigerim" />
          </label>
          <label className="block text-sm font-semibold text-graphite">
            Пароль
            <input value={password} onChange={(event) => setPassword(event.target.value)} required minLength={mode === 'register' ? 6 : 1} maxLength={128} type="password" autoComplete={mode === 'login' ? 'current-password' : 'new-password'} className="mt-1 w-full rounded-xl border border-sand bg-background px-3 py-2.5 outline-none focus:ring-2 focus:ring-primary/30" placeholder={mode === 'register' ? 'минимум 6 символов' : 'Ваш пароль'} />
          </label>
          {mode === 'register' && (
            <label className="block text-sm font-semibold text-graphite">
              Роль
              <select value={role} onChange={(event) => setRole(event.target.value as 'user' | 'volunteer')} className="mt-1 w-full rounded-xl border border-sand bg-background px-3 py-2.5 outline-none focus:ring-2 focus:ring-primary/30">
                <option value="user">Житель</option>
                <option value="volunteer">Волонтёр</option>
              </select>
            </label>
          )}
          {error && <p role="alert" className="rounded-xl bg-critical/10 px-3 py-2 text-sm font-medium text-critical">{error}</p>}
          <button disabled={submitting} className="flex w-full items-center justify-center gap-2 rounded-xl bg-primary py-3 font-bold text-white transition-colors hover:bg-primary/90 disabled:opacity-50">
            {submitting ? <Loader2 className="h-5 w-5 animate-spin" /> : mode === 'login' ? <LogIn className="h-5 w-5" /> : <UserPlus className="h-5 w-5" />}
            {mode === 'login' ? 'Войти' : 'Зарегистрироваться'}
          </button>
        </form>
        {mode === 'login' && <p className="mt-4 text-center text-xs text-graphite/50">Демо-аккаунты: логин и пароль <code>123</code>.</p>}
      </div>
    </div>
  );
}

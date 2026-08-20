import React, { useEffect, useRef, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Loader2, X } from 'lucide-react';
import { handleApiError, login, register } from '../../api';
import { apiClient } from '../../api/client';
import { useAuth } from '../../store/AuthContext';
import type { UserProfile } from '../../api/types';

type Mode = 'login' | 'register';

/**
 * Демо-роли. Пароль у всех одинаковый и указан открыто: это витрина
 * хакатонного прототипа, а не боевой контур, и жюри должно входить
 * без переписки с командой.
 */
const DEMO_ACCOUNTS = [
  { username: '123', label: 'Житель', hint: 'сдаёт хлеб, копит баллы' },
  { username: 'volunteer-1', label: 'Волонтёр', hint: 'берёт задачи на уборку' },
  { username: 'dispatcher-1', label: 'Диспетчер', hint: 'экономика и маршруты' },
] as const;

const DEMO_PASSWORD = '123';

interface ShowcaseAuthProps {
  isOpen: boolean;
  initialMode: Mode;
  onClose: () => void;
}

/**
 * Вход и регистрация прямо с витрины.
 *
 * Диспетчеру после проверки логина нужен ещё и ключ панели, поэтому окно
 * умеет переключаться на второй шаг вместо того, чтобы отправлять человека
 * на отдельный экран и терять контекст.
 */
export default function ShowcaseAuth({ isOpen, initialMode, onClose }: ShowcaseAuthProps) {
  const { setRole } = useAuth();
  const navigate = useNavigate();

  const [mode, setMode] = useState<Mode>(initialMode);
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [role, setRole_] = useState<'user' | 'volunteer'>('user');
  const [submitting, setSubmitting] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  // Второй шаг: логин диспетчера принят, но панель просит ключ.
  const [keyStage, setKeyStage] = useState<string | null>(null);
  const [dispatcherKey, setDispatcherKey] = useState('');

  const firstFieldRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    if (!isOpen) return;
    setMode(initialMode);
    setUsername('');
    setPassword('');
    setRole_('user');
    setError(null);
    setKeyStage(null);
    setDispatcherKey('');
    document.body.style.overflow = 'hidden';
    const timer = setTimeout(() => firstFieldRef.current?.focus(), 60);
    return () => {
      document.body.style.overflow = '';
      clearTimeout(timer);
    };
  }, [isOpen, initialMode]);

  useEffect(() => {
    if (!isOpen) return;
    const onKey = (event: KeyboardEvent) => {
      if (event.key === 'Escape') onClose();
    };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [isOpen, onClose]);

  if (!isOpen) return null;

  const finish = (profile: UserProfile) => {
    if (profile.role === 'dispatcher') {
      setKeyStage(profile.username);
      return;
    }
    setRole(profile.role, profile.username);
    onClose();
    navigate('/home');
  };

  const submitCredentials = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setSubmitting('form');
    setError(null);
    try {
      const profile =
        mode === 'login'
          ? await login({ username, password })
          : await register({ username, password, role });
      finish(profile);
    } catch (exception: unknown) {
      setError(handleApiError(exception).message);
    } finally {
      setSubmitting(null);
    }
  };

  const enterAsDemo = async (demoUsername: string) => {
    setSubmitting(demoUsername);
    setError(null);
    try {
      finish(await login({ username: demoUsername, password: DEMO_PASSWORD }));
    } catch (exception: unknown) {
      setError(handleApiError(exception).message);
    } finally {
      setSubmitting(null);
    }
  };

  const submitDispatcherKey = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (!keyStage) return;
    const trimmed = dispatcherKey.trim();
    setSubmitting('key');
    setError(null);
    try {
      // Ключ проверяем настоящим защищённым запросом, а не сравнением на
      // клиенте: иначе панель откроется и упадёт на первом же экране.
      await apiClient.get('/api/eco/profile', { headers: { 'X-Dispatcher-Key': trimmed } });
      sessionStorage.setItem('dispatcherKey', trimmed);
      setRole('dispatcher', keyStage);
      onClose();
      navigate('/dispatcher');
    } catch (exception: unknown) {
      const normalized = handleApiError(exception);
      setError(
        normalized.status === 401 || normalized.status === 403
          ? 'Ключ не подошёл. В демо-конфигурации это 123.'
          : normalized.message,
      );
    } finally {
      setSubmitting(null);
    }
  };

  const fieldClass =
    'mt-2 w-full rounded-lg border border-ink/12 bg-band px-3.5 py-3 text-ink ' +
    'placeholder:text-faint outline-none transition-colors focus:border-verdant/70 ' +
    'focus:ring-2 focus:ring-verdant/25';

  return (
    <div
      className="fixed inset-0 z-[60] flex items-center justify-center bg-black/75 p-4 backdrop-blur-sm"
      role="dialog"
      aria-modal="true"
      aria-labelledby="showcase-auth-title"
      onMouseDown={(event) => {
        if (event.target === event.currentTarget) onClose();
      }}
    >
      <div className="showcase relative max-h-[92vh] w-full max-w-md overflow-y-auto rounded-2xl border border-ink/10 bg-paper p-7">
        <button
          type="button"
          onClick={onClose}
          className="absolute right-4 top-4 rounded-lg p-2 text-faint transition-colors hover:bg-ink/5 hover:text-ink"
          aria-label="Закрыть"
        >
          <X className="h-4 w-4" />
        </button>

        {keyStage ? (
          <>
            <p className="mono-label text-verdant">Шаг 2 из 2</p>
            <h2 id="showcase-auth-title" className="display-type mt-3 text-3xl text-ink">
              Ключ панели
            </h2>
            <p className="mt-3 text-sm leading-relaxed text-body">
              Вход как <span className="mono-data text-ink">{keyStage}</span> принят.
              Диспетчерские операции защищены отдельным ключом, потому что они
              меняют тарифы и отправляют команды на железо.
            </p>

            <form onSubmit={submitDispatcherKey} className="mt-6 space-y-4">
              <label className="block text-sm font-medium text-ink">
                Ключ диспетчера
                <input
                  ref={firstFieldRef}
                  value={dispatcherKey}
                  onChange={(event) => setDispatcherKey(event.target.value)}
                  required
                  type="password"
                  autoComplete="off"
                  placeholder="в демо это 123"
                  className={fieldClass}
                />
              </label>

              {error && (
                <p role="alert" className="rounded-lg bg-critical/12 px-3 py-2.5 text-sm text-critical">
                  {error}
                </p>
              )}

              <button
                type="submit"
                disabled={submitting !== null}
                className="flex w-full items-center justify-center gap-2 rounded-lg bg-ink py-3 text-sm font-medium text-white transition-opacity hover:opacity-90 disabled:opacity-50"
              >
                {submitting === 'key' && <Loader2 className="h-4 w-4 animate-spin" />}
                Открыть панель
              </button>
            </form>
          </>
        ) : (
          <>
            <p className="mono-label text-verdant">Доступ к платформе</p>
            <h2 id="showcase-auth-title" className="display-type mt-3 text-3xl text-ink">
              {mode === 'login' ? 'С возвращением' : 'Создать аккаунт'}
            </h2>

            <div className="mt-6 grid grid-cols-2 gap-1 rounded-lg border border-ink/10 p-1">
              {(['login', 'register'] as const).map((value) => (
                <button
                  key={value}
                  type="button"
                  onClick={() => {
                    setMode(value);
                    setError(null);
                  }}
                  aria-pressed={mode === value}
                  className={
                    'rounded-md py-2 text-sm font-medium transition-colors ' +
                    (mode === value ? 'bg-ink/8 text-ink' : 'text-body hover:text-ink')
                  }
                >
                  {value === 'login' ? 'Войти' : 'Регистрация'}
                </button>
              ))}
            </div>

            <form onSubmit={submitCredentials} className="mt-5 space-y-4">
              <label className="block text-sm font-medium text-ink">
                Логин
                <input
                  ref={firstFieldRef}
                  value={username}
                  onChange={(event) => setUsername(event.target.value)}
                  required
                  minLength={mode === 'register' ? 3 : 1}
                  maxLength={64}
                  autoComplete="username"
                  placeholder="например, aigerim"
                  className={fieldClass}
                />
              </label>

              <label className="block text-sm font-medium text-ink">
                Пароль
                <input
                  value={password}
                  onChange={(event) => setPassword(event.target.value)}
                  required
                  minLength={mode === 'register' ? 6 : 1}
                  maxLength={128}
                  type="password"
                  autoComplete={mode === 'login' ? 'current-password' : 'new-password'}
                  placeholder={mode === 'register' ? 'минимум 6 символов' : ''}
                  className={fieldClass}
                />
              </label>

              {mode === 'register' && (
                <label className="block text-sm font-medium text-ink">
                  Роль
                  <select
                    value={role}
                    onChange={(event) => setRole_(event.target.value as 'user' | 'volunteer')}
                    className={fieldClass}
                  >
                    <option value="user">Житель</option>
                    <option value="volunteer">Волонтёр</option>
                  </select>
                  <span className="mt-2 block text-xs text-faint">
                    Диспетчер не регистрируется самостоятельно — эту роль выдаёт
                    коммунальная служба вместе с ключом панели.
                  </span>
                </label>
              )}

              {error && (
                <p role="alert" className="rounded-lg bg-critical/12 px-3 py-2.5 text-sm text-critical">
                  {error}
                </p>
              )}

              <button
                type="submit"
                disabled={submitting !== null}
                className="flex w-full items-center justify-center gap-2 rounded-lg bg-ink py-3 text-sm font-medium text-white transition-opacity hover:opacity-90 disabled:opacity-50"
              >
                {submitting === 'form' && <Loader2 className="h-4 w-4 animate-spin" />}
                {mode === 'login' ? 'Войти' : 'Зарегистрироваться'}
              </button>
            </form>

            <div className="mt-7 border-t border-ink/10 pt-5">
              <p className="mono-label text-faint">Или войдите демо-ролью</p>
              <div className="mt-3 space-y-2">
                {DEMO_ACCOUNTS.map((account) => (
                  <button
                    key={account.username}
                    type="button"
                    onClick={() => enterAsDemo(account.username)}
                    disabled={submitting !== null}
                    className="flex w-full items-center justify-between gap-3 rounded-lg border border-ink/10 px-4 py-3 text-left transition-colors hover:border-verdant/50 hover:bg-ink/4 disabled:opacity-50"
                  >
                    <span className="min-w-0">
                      <span className="block text-sm font-medium text-ink">{account.label}</span>
                      <span className="block text-xs text-faint">{account.hint}</span>
                    </span>
                    {submitting === account.username ? (
                      <Loader2 className="h-4 w-4 shrink-0 animate-spin text-verdant" />
                    ) : (
                      <span className="mono-data shrink-0 text-xs text-faint">
                        {account.username}
                      </span>
                    )}
                  </button>
                ))}
              </div>
            </div>
          </>
        )}
      </div>
    </div>
  );
}

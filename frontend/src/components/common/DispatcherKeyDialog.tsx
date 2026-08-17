import React, { useState, useEffect, useRef } from 'react';
import { X, Lock, Loader2 } from 'lucide-react';
import { useLocaleTheme } from '../../store/LocaleThemeContext';
import { handleApiError, apiClient } from '../../api';

interface DispatcherKeyDialogProps {
  isOpen: boolean;
  onClose: () => void;
  onSuccess: (key: string) => void;
  username: string;
  returnFocusRef?: React.RefObject<HTMLElement | null>;
}

export default function DispatcherKeyDialog({
  isOpen,
  onClose,
  onSuccess,
  username,
  returnFocusRef,
}: DispatcherKeyDialogProps) {
  const { t } = useLocaleTheme();
  const [dispatcherKey, setDispatcherKey] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const modalRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    if (isOpen) {
      document.body.style.overflow = 'hidden';
      // Store current focus to return it if returnFocusRef is not provided
      const previousActive = document.activeElement as HTMLElement;
      
      const timer = setTimeout(() => {
        inputRef.current?.focus();
      }, 80);

      return () => {
        document.body.style.overflow = '';
        clearTimeout(timer);
        if (returnFocusRef?.current) {
          returnFocusRef.current.focus();
        } else if (previousActive && typeof previousActive.focus === 'function') {
          previousActive.focus();
        }
      };
    }
  }, [isOpen, returnFocusRef]);

  if (!isOpen) return null;

  const getFocusableElements = (container: HTMLElement) => {
    return container.querySelectorAll<HTMLElement>(
      'a[href], area[href], input:not([disabled]), select:not([disabled]), textarea:not([disabled]), button:not([disabled]), [tabindex="0"]'
    );
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLDivElement>) => {
    if (e.key === 'Tab' && modalRef.current) {
      const focusables = Array.from(getFocusableElements(modalRef.current));
      if (focusables.length === 0) return;
      const first = focusables[0]!;
      const last = focusables[focusables.length - 1]!;
      if (e.shiftKey) {
        if (document.activeElement === first) {
          last.focus();
          e.preventDefault();
        }
      } else {
        if (document.activeElement === last) {
          first.focus();
          e.preventDefault();
        }
      }
    } else if (e.key === 'Escape') {
      onClose();
      e.preventDefault();
    }
  };

  const handleOverlayClick = (e: React.MouseEvent<HTMLDivElement>) => {
    if (e.target === e.currentTarget) {
      onClose();
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    const trimmedKey = dispatcherKey.trim();
    if (!trimmedKey) {
      setError(t('dispatcherKeyModalErrorEmpty') || 'Пожалуйста, введите ключ.');
      return;
    }

    setSubmitting(true);
    setError(null);

    try {
      // Temporarily store the key in sessionStorage so that validation request can use it
      sessionStorage.setItem('dispatcherKey', trimmedKey);

      // Verify the key by hitting the protected summary endpoint
      await apiClient.get('/api/dispatch/summary');

      // Key verified successfully!
      onSuccess(trimmedKey);
      setDispatcherKey('');
    } catch (err: unknown) {
      // Clear key on failure
      sessionStorage.removeItem('dispatcherKey');
      const normErr = handleApiError(err);
      if (!normErr.status) {
        // Network error vs invalid key distinction
        setError(t('dispatcherKeyModalErrorNetwork') || 'Ошибка сети. Сервер недоступен. Проверьте запуск backend.');
      } else if (normErr.status === 403) {
        setError(t('dispatcherKeyModalErrorInvalid') || 'Неверный X-Dispatcher-Key. Доступ отклонен.');
      } else {
        setError(normErr.message);
      }
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div 
      className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-xs transition-opacity duration-300"
      role="dialog"
      aria-modal="true"
      aria-labelledby="dispatcher-dialog-title"
      aria-describedby="dispatcher-dialog-desc"
      onClick={handleOverlayClick}
      onKeyDown={handleKeyDown}
    >
      <div 
        ref={modalRef}
        className="bg-card border border-border rounded-3xl p-6 md:p-8 max-w-md w-full shadow-2xl relative overflow-hidden transform transition-all duration-300 scale-100 space-y-6"
      >
        <button 
          onClick={onClose}
          disabled={submitting}
          className="absolute top-4 right-4 p-2 text-foreground/50 hover:text-foreground hover:bg-muted rounded-full transition-colors cursor-pointer min-h-[44px] min-w-[44px] flex items-center justify-center"
          aria-label={t('close') || "Закрыть"}
        >
          <X className="w-5 h-5" />
        </button>

        <div className="flex items-center gap-3">
          <div className="p-3 rounded-2xl bg-critical/10 text-critical flex items-center justify-center">
            <Lock className="w-6 h-6" />
          </div>
          <div>
            <h3 id="dispatcher-dialog-title" className="text-xl font-bold text-foreground">
              {t('dispatcherKeyModalTitle')}
            </h3>
            <p className="text-xs text-foreground/50">Вход для {username}</p>
          </div>
        </div>

        <p id="dispatcher-dialog-desc" className="text-sm text-foreground/70 leading-relaxed">
          {t('dispatcherKeyModalDesc')}
        </p>

        <form onSubmit={handleSubmit} className="space-y-4">
          <div className="space-y-1">
            <label htmlFor="dispatcher-key-dialog-input" className="text-xs font-bold text-foreground/80 block">
              {t('dispatcherKeyModalLabel')}
            </label>
            <input 
              id="dispatcher-key-dialog-input"
              ref={inputRef}
              type="password"
              value={dispatcherKey}
              onChange={(e) => setDispatcherKey(e.target.value)}
              placeholder="X-Dispatcher-Key"
              disabled={submitting}
              className="w-full bg-muted border border-border rounded-xl px-4 py-3 text-foreground font-mono placeholder:text-foreground/30 focus:outline-none focus:ring-2 focus:ring-critical/30 h-11"
            />
          </div>

          <div aria-live="polite" className="space-y-2">
            {error && (
              <div className="text-xs text-critical bg-critical/10 border border-critical/20 px-3 py-2 rounded-lg font-medium">
                {error}
              </div>
            )}
          </div>

          <p className="text-[10px] text-foreground/40 leading-tight">
            {t('dispatcherKeyModalNote')}
          </p>

          <div className="flex gap-3 pt-2">
            <button 
              type="button"
              onClick={onClose}
              disabled={submitting}
              className="flex-1 h-11 border border-border text-foreground hover:bg-muted rounded-xl text-sm font-bold transition-colors cursor-pointer min-h-[44px] flex items-center justify-center"
            >
              {t('cancel') || "Отмена"}
            </button>
            <button 
              type="submit"
              disabled={submitting || !dispatcherKey.trim()}
              className="flex-1 h-11 bg-critical hover:bg-critical/95 text-white rounded-xl text-sm font-bold shadow-sm transition-all flex items-center justify-center gap-2 cursor-pointer disabled:opacity-50 disabled:cursor-not-allowed min-h-[44px]"
            >
              {submitting ? <Loader2 className="w-4 h-4 animate-spin" /> : t('dispatcherKeyModalSubmit')}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

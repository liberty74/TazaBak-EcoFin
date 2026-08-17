import React from 'react';
import { useLocaleTheme } from '../store/LocaleThemeContext';
import { Globe, Moon, Sun, Check } from 'lucide-react';

export default function SettingsPage() {
  const { theme, setTheme, locale, setLocale, t } = useLocaleTheme();

  return (
    <div className="p-4 md:p-8 max-w-2xl mx-auto w-full pt-8 pb-24 lg:pb-8 space-y-6">
      <div>
        <h1 className="text-3xl font-extrabold text-primary tracking-tight">{t('settingsTitle')}</h1>
        <p className="text-graphite/60 text-sm">{t('settingsSub')}</p>
      </div>

      <div className="bg-white dark:bg-card border border-sand dark:border-border rounded-3xl p-6 shadow-sm space-y-6 text-foreground">
        {/* Language Selection */}
        <div className="space-y-3">
          <label className="font-bold text-graphite dark:text-foreground flex items-center gap-2">
            <Globe className="w-5 h-5 text-primary" />
            <span>{t('langLabel')}</span>
          </label>
          <div className="grid grid-cols-2 gap-4">
            <button 
              onClick={() => setLocale('RU')}
              className={`py-3 px-4 rounded-xl font-bold text-sm border transition-all flex items-center justify-center gap-2 cursor-pointer ${locale === 'RU' ? 'bg-primary border-primary text-white shadow-sm' : 'bg-cream dark:bg-muted border-sand dark:border-border text-graphite/70 dark:text-foreground/70 hover:bg-sand/30 dark:hover:bg-accent/20'}`}
            >
              <span>🇷🇺 Русский (RU)</span>
              {locale === 'RU' && <Check className="w-4 h-4" />}
            </button>
            <button 
              onClick={() => setLocale('KZ')}
              className={`py-3 px-4 rounded-xl font-bold text-sm border transition-all flex items-center justify-center gap-2 cursor-pointer ${locale === 'KZ' ? 'bg-primary border-primary text-white shadow-sm' : 'bg-cream dark:bg-muted border-sand dark:border-border text-graphite/70 dark:text-foreground/70 hover:bg-sand/30 dark:hover:bg-accent/20'}`}
            >
              <span>🇰🇿 Қазақша (KZ)</span>
              {locale === 'KZ' && <Check className="w-4 h-4" />}
            </button>
          </div>
        </div>

        {/* Theme Selection */}
        <div className="space-y-3 pt-4 border-t border-sand dark:border-border">
          <label className="font-bold text-graphite dark:text-foreground flex items-center gap-2">
            <Moon className="w-5 h-5 text-primary" />
            <span>{t('themeLabel')}</span>
          </label>
          <div className="grid grid-cols-2 gap-4">
            <button 
              onClick={() => setTheme('light')}
              className={`py-3 px-4 rounded-xl font-bold text-sm border transition-all flex items-center justify-center gap-2 cursor-pointer ${theme === 'light' ? 'bg-primary border-primary text-white shadow-sm' : 'bg-cream dark:bg-muted border-sand dark:border-border text-graphite/70 dark:text-foreground/70 hover:bg-sand/30 dark:hover:bg-accent/20'}`}
            >
              <Sun className="w-4 h-4" />
              <span>{t('themeLight')}</span>
            </button>
            <button 
              onClick={() => setTheme('dark')}
              className={`py-3 px-4 rounded-xl font-bold text-sm border transition-all flex items-center justify-center gap-2 cursor-pointer ${theme === 'dark' ? 'bg-primary border-primary text-white shadow-sm' : 'bg-cream dark:bg-muted border-sand dark:border-border text-graphite/70 dark:text-foreground/70 hover:bg-sand/30 dark:hover:bg-accent/20'}`}
            >
              <Moon className="w-4 h-4" />
              <span>{t('themeDark')}</span>
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
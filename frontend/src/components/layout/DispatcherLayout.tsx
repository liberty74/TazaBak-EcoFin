import React from 'react';
import { Outlet, NavLink, useNavigate, useLocation } from 'react-router-dom';
import { LayoutDashboard, Map as MapIcon, AlertTriangle, RadioReceiver, LogOut, Settings, Globe, Users, Menu, X, Wifi, WifiOff } from 'lucide-react';
import { useAuth } from '../../store/AuthContext';
import { useLocaleTheme } from '../../store/LocaleThemeContext';
import { cn } from '../../lib/utils';
import { useApiHealth } from '../../api/useApiHealth';

export default function DispatcherLayout() {
  const { user, logout } = useAuth();
  const { t, locale, toggleLocale } = useLocaleTheme();
  const navigate = useNavigate();
  const location = useLocation();
  const { status: healthStatus } = useApiHealth();
  const [mobileMenuOpen, setMobileMenuOpen] = React.useState(false);

  React.useEffect(() => {
    setMobileMenuOpen(false);
  }, [location.pathname]);

  const handleLogout = () => {
    logout();
    navigate('/demo');
  };

  const renderHealthIndicator = () => {
    switch (healthStatus) {
      case 'checking':
        return (
          <div className="flex items-center gap-2">
            <span className="w-2.5 h-2.5 rounded-full bg-amber-500 animate-pulse"></span>
            <span className="text-sm text-foreground/70">Проверка API...</span>
          </div>
        );
      case 'connected':
        return (
          <div className="flex items-center gap-2">
            <span className="w-2.5 h-2.5 rounded-full bg-emerald-500 animate-pulse"></span>
            <span className="text-sm text-foreground/70">{t('apiConnected')}</span>
          </div>
        );
      case 'db_error':
        return (
          <div className="flex items-center gap-2">
            <span className="w-2.5 h-2.5 rounded-full bg-amber-500 animate-pulse"></span>
            <span className="text-sm text-amber-500 font-semibold">БД отключена</span>
          </div>
        );
      case 'disconnected':
      default:
        return (
          <div className="flex items-center gap-2">
            <span className="w-2.5 h-2.5 rounded-full bg-rose-500"></span>
            <span className="text-sm text-rose-500 font-semibold">{t('apiDisconnected')}</span>
          </div>
        );
    }
  };

  return (
    <div className="flex h-[100dvh] bg-background overflow-hidden font-sans text-foreground">
      {/* Sidebar - respects global theme styling */}
      <aside className="hidden lg:flex flex-col w-64 bg-card border-r border-border shrink-0 z-20">
        <div className="p-6 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <img src="/logo.svg" alt="TazaBAK" className="h-10 object-contain" />
            <div>
              <h1 className="font-bold text-xl text-primary leading-none">TazaBAK</h1>
              <span className="text-xs text-foreground/60">Dispatcher Center</span>
            </div>
          </div>
        </div>

        <nav className="flex-1 px-4 py-4 space-y-2 overflow-y-auto">
          <NavLink
            to="/dispatcher"
            end
            className={({ isActive }) => cn(
              "flex items-center gap-3 px-4 py-3 rounded-lg font-medium transition-colors",
              isActive 
                ? "bg-primary text-white" 
                : "text-foreground/70 hover:bg-muted hover:text-foreground"
            )}
          >
            <LayoutDashboard className="w-5 h-5" />
            <span>{t('dispatchSummary')}</span>
          </NavLink>
          
          <NavLink
            to="/dispatcher/map"
            className={({ isActive }) => cn(
              "flex items-center gap-3 px-4 py-3 rounded-lg font-medium transition-colors",
              isActive 
                ? "bg-primary text-white" 
                : "text-foreground/70 hover:bg-muted hover:text-foreground"
            )}
          >
            <MapIcon className="w-5 h-5" />
            <span>{t('navMap')}</span>
          </NavLink>

          <NavLink
            to="/dispatcher/alerts"
            className={({ isActive }) => cn(
              "flex items-center gap-3 px-4 py-3 rounded-lg font-medium transition-colors",
              isActive 
                ? "bg-primary text-white" 
                : "text-foreground/70 hover:bg-muted hover:text-foreground"
            )}
          >
            <AlertTriangle className="w-5 h-5" />
            <span>{t('alertsTitle')}</span>
          </NavLink>

          <NavLink
            to="/dispatcher/devices"
            className={({ isActive }) => cn(
              "flex items-center gap-3 px-4 py-3 rounded-lg font-medium transition-colors",
              isActive 
                ? "bg-primary text-white" 
                : "text-foreground/70 hover:bg-muted hover:text-foreground"
            )}
          >
            <RadioReceiver className="w-5 h-5" />
            <span>{t('deviceCommandTitle')}</span>
          </NavLink>
          <NavLink
            to="/dispatcher/volunteer"
            className={({ isActive }) => cn(
              "flex items-center gap-3 px-4 py-3 rounded-lg font-medium transition-colors",
              isActive ? "bg-primary text-white" : "text-foreground/70 hover:bg-muted hover:text-foreground"
            )}
          >
            <Users className="w-5 h-5" />
            <span>Волонтёры</span>
          </NavLink>
        </nav>

        {/* Toolbar row with lang switch */}
        <div className="px-6 py-2 border-t border-border flex justify-between items-center">
          <button 
            onClick={toggleLocale}
            className="p-2 hover:bg-muted rounded-xl transition-colors text-xs font-bold text-primary flex items-center gap-1.5 cursor-pointer"
            title="Switch Language"
          >
            <Globe className="w-4 h-4" />
            <span>{locale}</span>
          </button>
          
          <button 
            onClick={() => navigate('/dispatcher/settings')}
            className="p-2 hover:bg-muted rounded-xl transition-colors text-foreground/50 hover:text-primary cursor-pointer"
            title={t('navSettings')}
          >
            <Settings className="w-4 h-4" />
          </button>
        </div>

        <div className="p-4 border-t border-border">
          <div className="flex items-center gap-3 px-4 py-3 mb-2">
            <div className="w-10 h-10 rounded-full bg-primary/10 text-primary flex items-center justify-center font-bold">
              {user?.username.charAt(0).toUpperCase()}
            </div>
            <div className="flex-1 overflow-hidden">
              <p className="text-sm font-bold truncate text-foreground">{user?.username}</p>
              <p className="text-xs text-foreground/50 capitalize">Dispatcher</p>
            </div>
          </div>
          <button 
            onClick={handleLogout}
            className="w-full flex items-center gap-3 px-4 py-3 text-critical hover:bg-critical/10 rounded-lg transition-colors font-medium cursor-pointer"
          >
            <LogOut className="w-5 h-5" />
            <span>{t('logout')}</span>
          </button>
        </div>
      </aside>

      {/* Main Content Area */}
      <div className="flex-1 flex flex-col h-full relative overflow-hidden bg-background">
        {/* Mobile Header */}
        <header className="lg:hidden flex items-center justify-between px-4 h-16 bg-card border-b border-border z-30 shrink-0">
          <div className="flex items-center gap-2">
            <img src="/logo.svg" alt="TazaBAK" className="h-8 object-contain" />
            <span className="font-bold text-lg text-primary">Dispatcher</span>
          </div>
          <div className="flex items-center gap-0.5">
            <button aria-label="Сменить язык" title="Сменить язык" onClick={toggleLocale} className="p-2 text-xs font-bold hover:bg-muted rounded-full transition-colors flex items-center gap-1 cursor-pointer">
              <Globe className="w-4 h-4" />
              <span>{locale}</span>
            </button>
            <button aria-label={t('navSettings')} onClick={() => navigate('/dispatcher/settings')} className="p-2 text-foreground/50 hover:text-primary hover:bg-muted rounded-full transition-colors cursor-pointer" title={t('navSettings')}>
              <Settings className="w-5 h-5" />
            </button>
            <button aria-label="Выйти" title="Выйти" onClick={handleLogout} className="p-2 text-critical cursor-pointer"><LogOut className="w-5 h-5"/></button>
          </div>
        </header>

        {/* Top Bar for Desktop */}
        <header className="hidden lg:flex items-center justify-between px-8 h-16 bg-background border-b border-border shrink-0">
          <div className="flex items-center gap-4">
            {renderHealthIndicator()}
          </div>
          <div className="text-sm font-mono text-foreground/50">
            {new Date().toLocaleDateString(locale === 'RU' ? 'ru-RU' : 'kk-KZ', { weekday: 'long', year: 'numeric', month: 'long', day: 'numeric' })}
          </div>
        </header>

        {/* Scrollable Content */}
        <main className="flex-1 overflow-y-auto overscroll-contain p-4 pb-[calc(5rem+env(safe-area-inset-bottom))] md:p-8 lg:pb-8">
          <Outlet />
        </main>

        {mobileMenuOpen && (
          <div className="lg:hidden absolute inset-0 z-40" role="dialog" aria-modal="true" aria-label="Меню диспетчера">
            <button className="absolute inset-0 bg-black/45 backdrop-blur-[2px]" aria-label="Закрыть меню" onClick={() => setMobileMenuOpen(false)} />
            <section className="absolute inset-x-0 bottom-[calc(4rem+env(safe-area-inset-bottom))] rounded-t-3xl border-t border-border bg-card p-4 pb-6 shadow-2xl">
              <div className="mb-4 flex items-center justify-between">
                <div>
                  <p className="font-extrabold">Меню диспетчера</p>
                  <div className="mt-1 flex items-center gap-1.5 text-xs text-muted-foreground">
                    {healthStatus === 'connected' ? <Wifi className="h-3.5 w-3.5 text-primary" /> : <WifiOff className="h-3.5 w-3.5 text-critical" />}
                    <span>{healthStatus === 'connected' ? 'FastAPI подключён' : 'Нет связи с FastAPI'}</span>
                  </div>
                </div>
                <button aria-label="Закрыть меню" onClick={() => setMobileMenuOpen(false)} className="rounded-full bg-muted p-2"><X className="h-5 w-5" /></button>
              </div>
              <div className="grid grid-cols-2 gap-2">
                <NavLink to="/dispatcher/volunteer" className={({ isActive }) => cn("rounded-2xl border p-4", isActive ? "border-primary bg-primary/10 text-primary" : "border-border bg-background")}>
                  <Users className="mb-2 h-5 w-5" /><p className="font-bold">Задачи</p><p className="mt-1 text-xs text-muted-foreground">Работа волонтёров</p>
                </NavLink>
                <NavLink to="/dispatcher/settings" className={({ isActive }) => cn("rounded-2xl border p-4", isActive ? "border-primary bg-primary/10 text-primary" : "border-border bg-background")}>
                  <Settings className="mb-2 h-5 w-5" /><p className="font-bold">Настройки</p><p className="mt-1 text-xs text-muted-foreground">Язык и интерфейс</p>
                </NavLink>
              </div>
              <div className="mt-3 rounded-2xl border border-border bg-background p-3">
                <p className="text-xs text-muted-foreground">Текущая сессия</p>
                <p className="font-bold">{user?.username || 'dispatcher'} · Dispatcher</p>
              </div>
              <button onClick={handleLogout} className="mt-3 flex w-full items-center justify-center gap-2 rounded-2xl border border-critical/20 bg-critical/10 px-4 py-3 font-bold text-critical"><LogOut className="h-5 w-5" />Выйти</button>
            </section>
          </div>
        )}

        {/* Mobile Bottom Navigation */}
        <nav className="lg:hidden absolute bottom-0 w-full h-[calc(4rem+env(safe-area-inset-bottom))] pb-[env(safe-area-inset-bottom)] bg-card/95 backdrop-blur-md border-t border-border flex justify-around items-center px-1 z-50">
          <NavLink
            to="/dispatcher"
            end
            className={({ isActive }) => cn(
              "flex flex-col items-center justify-center min-w-0 flex-1 h-16 transition-colors",
              isActive ? "text-primary" : "text-foreground/50"
            )}
          >
            <LayoutDashboard className="w-5 h-5 mb-1" />
            <span className="text-[9px] font-semibold">Сводка</span>
          </NavLink>
          <NavLink
            to="/dispatcher/map"
            className={({ isActive }) => cn(
              "flex flex-col items-center justify-center min-w-0 flex-1 h-16 transition-colors",
              isActive ? "text-primary" : "text-foreground/50"
            )}
          >
            <MapIcon className="w-5 h-5 mb-1" />
            <span className="text-[10px] font-semibold">{t('navMap')}</span>
          </NavLink>
          <NavLink
            to="/dispatcher/alerts"
            className={({ isActive }) => cn(
              "flex flex-col items-center justify-center min-w-0 flex-1 h-16 transition-colors",
              isActive ? "text-primary" : "text-foreground/50"
            )}
          >
            <AlertTriangle className="w-5 h-5 mb-1" />
            <span className="text-[10px] font-semibold">Алерты</span>
          </NavLink>
          <NavLink
            to="/dispatcher/devices"
            className={({ isActive }) => cn(
              "flex flex-col items-center justify-center min-w-0 flex-1 h-16 transition-colors",
              isActive ? "text-primary" : "text-foreground/50"
            )}
          >
            <RadioReceiver className="w-5 h-5 mb-1" />
            <span className="text-[10px] font-semibold">Баки</span>
          </NavLink>
          <button onClick={() => setMobileMenuOpen((open) => !open)} aria-expanded={mobileMenuOpen} aria-label="Открыть меню диспетчера" className={cn("flex h-16 min-w-0 flex-1 flex-col items-center justify-center transition-colors", mobileMenuOpen || location.pathname === '/dispatcher/volunteer' || location.pathname === '/dispatcher/settings' ? "text-primary" : "text-foreground/50")}>
            <Menu className="mb-1 h-5 w-5" />
            <span className="text-[10px] font-semibold">Меню</span>
          </button>
        </nav>
      </div>
    </div>
  );
}

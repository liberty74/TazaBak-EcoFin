import React from 'react';
import { Outlet, NavLink, useNavigate, useLocation, Link } from 'react-router-dom';
import { Home, Map as MapIcon, HandHeart, ShoppingCart, MessageSquare, Bot, LogOut, UserCircle, Globe, Moon, Sun, Settings, Trophy, Award, Camera, Menu, X } from 'lucide-react';
import { useAuth } from '../../store/AuthContext';
import { useLocaleTheme } from '../../store/LocaleThemeContext';
import { cn } from '../../lib/utils';
import { motion } from 'motion/react';

export default function AppLayout() {
  const { user, logout } = useAuth();
  const { t, locale, toggleLocale, theme, toggleTheme } = useLocaleTheme();
  const navigate = useNavigate();
  const location = useLocation();
  const [mobileMenuOpen, setMobileMenuOpen] = React.useState(false);

  React.useEffect(() => {
    setMobileMenuOpen(false);
  }, [location.pathname]);

  const handleLogout = () => {
    logout();
    navigate('/demo');
  };

  const navItems = [
    { to: '/home', icon: Home, label: t('navHome') },
    { to: '/scan', icon: Camera, label: 'Сдать хлеб' },
    { to: '/map', icon: MapIcon, label: t('navMap') },
    { to: '/volunteer', icon: HandHeart, label: t('navVolunteer') },
    { to: '/shop', icon: ShoppingCart, label: t('navShop') },
    { to: '/community', icon: MessageSquare, label: t('navCommunity') },
    { to: '/leaderboard', icon: Trophy, label: t('navLeaderboard') },
    { to: '/collection', icon: Award, label: t('navCollection') },
  ];

  const assistantItem = { to: '/assistant', icon: Bot, label: t('navAssistant') };
  const mobilePrimaryItems = [
    { to: '/home', icon: Home, label: t('navHome') },
    { to: '/map', icon: MapIcon, label: t('navMap') },
    { to: '/scan', icon: Camera, label: 'Сдать' },
    { to: '/volunteer', icon: HandHeart, label: t('navVolunteer') },
  ];
  const mobileMoreItems = [
    { to: '/shop', icon: ShoppingCart, label: t('navShop'), description: 'Баллы и Eco-NFT' },
    { to: '/collection', icon: Award, label: t('navCollection'), description: 'Ваши созданные NFT' },
    { to: '/leaderboard', icon: Trophy, label: t('navLeaderboard'), description: 'Топ эко-активистов' },
    { to: '/community', icon: MessageSquare, label: t('navCommunity'), description: 'Чат сообщества' },
    { to: '/assistant', icon: Bot, label: t('navAssistant'), description: 'Советы от Баки' },
    { to: '/profile', icon: UserCircle, label: 'Профиль', description: 'Баланс и история' },
    { to: '/settings', icon: Settings, label: t('navSettings'), description: 'Язык и тема' },
  ];
  const isMoreRouteActive = mobileMoreItems.some((item) => location.pathname === item.to);

  return (
    <div className={cn("flex h-[100dvh] bg-background overflow-hidden font-sans", theme === 'dark' ? 'dark text-white' : 'text-graphite')}>
      {/* Desktop Sidebar */}
      <aside className="hidden lg:flex flex-col w-64 bg-white dark:bg-zinc-900 border-r border-sand dark:border-zinc-800 shrink-0 relative z-20">
        <div className="p-6 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <img src="/logo.svg" alt="TazaBAK" className="h-10 object-contain" />
            <div>
              <h1 className="font-bold text-xl text-primary leading-none">TazaBAK</h1>
              <span className="text-xs text-graphite/60 dark:text-zinc-400">{t('city')}</span>
            </div>
          </div>
        </div>

        <nav className="flex-1 px-4 py-2 space-y-1 overflow-y-auto hide-scrollbar">
          {navItems.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              className={({ isActive }) => cn(
                "flex items-center gap-3 px-4 py-3 rounded-xl font-medium transition-all duration-200",
                isActive 
                  ? "bg-primary text-white shadow-md shadow-primary/20" 
                  : "text-graphite/70 dark:text-zinc-300 hover:bg-cream dark:hover:bg-zinc-800 hover:text-primary dark:hover:text-primary-light"
              )}
            >
              <item.icon className="w-5 h-5" />
              <span>{item.label}</span>
            </NavLink>
          ))}
          <NavLink
            to={assistantItem.to}
            className={({ isActive }) => cn(
              "flex items-center gap-3 px-4 py-3 rounded-xl font-medium transition-all duration-200 border border-primary/20 bg-primary/5",
              isActive 
                ? "bg-primary text-white shadow-md shadow-primary/20" 
                : "text-primary dark:text-primary-light hover:bg-primary/10"
            )}
          >
            <assistantItem.icon className="w-5 h-5" />
            <span>{assistantItem.label}</span>
          </NavLink>
        </nav>

        {/* Toolbar Row */}
        <div className="px-6 py-2 flex items-center justify-around border-t border-sand dark:border-zinc-800 bg-cream/30 dark:bg-zinc-800/30 gap-1">
          <button 
            onClick={toggleLocale}
            className="p-2 hover:bg-cream dark:hover:bg-zinc-800 rounded-xl transition-colors text-xs font-bold text-primary flex items-center gap-1"
            title="Switch Language"
          >
            <Globe className="w-4 h-4" />
            <span>{locale}</span>
          </button>
          
          <button 
            onClick={toggleTheme}
            className="p-2 hover:bg-cream dark:hover:bg-zinc-800 rounded-xl transition-colors text-graphite/60 dark:text-zinc-400 hover:text-primary"
            title="Toggle Theme"
          >
            {theme === 'dark' ? <Sun className="w-4.5 h-4.5" /> : <Moon className="w-4.5 h-4.5" />}
          </button>

          <button 
            onClick={() => navigate('/settings')}
            className={cn("p-2 hover:bg-cream dark:hover:bg-zinc-800 rounded-xl transition-colors", 
              location.pathname === '/settings' ? 'text-primary' : 'text-graphite/60 dark:text-zinc-400'
            )}
            title={t('navSettings')}
          >
            <Settings className="w-4.5 h-4.5" />
          </button>
        </div>

        <div className="p-4 border-t border-sand dark:border-zinc-800">
          <Link to="/profile" className="flex items-center gap-3 px-4 py-3 mb-2 hover:bg-cream dark:hover:bg-zinc-800 rounded-xl transition-colors">
            <div className="w-10 h-10 rounded-full bg-cream dark:bg-zinc-800 border-2 border-primary-light flex items-center justify-center font-bold text-primary shrink-0">
              {user?.username.charAt(0).toUpperCase()}
            </div>
            <div className="flex-1 overflow-hidden">
              <p className="text-sm font-bold truncate text-graphite dark:text-white">{user?.username}</p>
              <p className="text-xs text-graphite/60 dark:text-zinc-400 capitalize">{user?.role}</p>
            </div>
          </Link>
          <button 
            onClick={handleLogout}
            className="w-full flex items-center gap-3 px-4 py-3 text-critical hover:bg-critical/10 rounded-xl transition-colors font-medium"
          >
            <LogOut className="w-5 h-5" />
            <span>{t('logout')}</span>
          </button>
        </div>
      </aside>

      {/* Main Content Area */}
      <div className="flex-1 flex flex-col h-full relative overflow-hidden bg-background dark:bg-zinc-950">
        {/* Mobile Header */}
        <header className="lg:hidden flex items-center justify-between px-3 h-16 bg-white/90 dark:bg-zinc-900/90 backdrop-blur-md border-b border-sand dark:border-zinc-800 z-30 shrink-0">
          <div className="flex items-center gap-2">
            <img src="/logo.svg" alt="TazaBAK" className="h-8 object-contain" />
            <span className="font-bold text-lg text-primary">TazaBAK</span>
          </div>
          <div className="flex items-center gap-0.5 text-primary">
            <button aria-label="Сменить язык" title="Сменить язык" onClick={toggleLocale} className="p-2 text-xs font-bold hover:bg-cream dark:hover:bg-zinc-800 rounded-full transition-colors flex items-center gap-1">
              <Globe className="w-4 h-4" />
              <span>{locale}</span>
            </button>
            <button aria-label="Сменить тему" title="Сменить тему" onClick={toggleTheme} className="p-2 hover:bg-cream dark:hover:bg-zinc-800 rounded-full transition-colors">
              {theme === 'dark' ? <Sun className="w-5 h-5" /> : <Moon className="w-5 h-5" />}
            </button>
            <button aria-label={t('navSettings')} title={t('navSettings')} onClick={() => navigate('/settings')} className="hidden min-[360px]:flex p-2 hover:bg-cream dark:hover:bg-zinc-800 rounded-full transition-colors">
              <Settings className="w-5 h-5" />
            </button>
            <button aria-label="Открыть профиль" title="Открыть профиль" onClick={() => navigate("/profile")} className="p-2 hover:bg-cream dark:hover:bg-zinc-800 rounded-full transition-colors"><UserCircle className="w-5 h-5" /></button>
          </div>
        </header>

        {/* Scrollable Content */}
        <main className="flex-1 overflow-y-auto bg-background dark:bg-zinc-950 pb-[calc(5rem+env(safe-area-inset-bottom))] lg:pb-0 relative overscroll-contain">
          <Outlet />
        </main>

        {/* Floating AI Assistant Button (Mobile Only) */}
        {location.pathname !== '/assistant' && (
          <motion.button
            whileHover={{ scale: 1.05 }}
            whileTap={{ scale: 0.95 }}
            onClick={() => navigate('/assistant')}
            aria-label="Открыть AI Баки"
            className="lg:hidden absolute bottom-[calc(5rem+env(safe-area-inset-bottom))] right-4 z-30 w-12 h-12 bg-primary text-white rounded-full shadow-lg flex items-center justify-center focus:outline-none focus:ring-4 focus:ring-primary/30"
          >
            <Bot className="w-6 h-6" />
          </motion.button>
        )}

        {mobileMenuOpen && (
          <div className="lg:hidden absolute inset-0 z-40" role="dialog" aria-modal="true" aria-label="Все разделы">
            <button className="absolute inset-0 bg-black/45 backdrop-blur-[2px]" aria-label="Закрыть меню" onClick={() => setMobileMenuOpen(false)} />
            <section className="absolute inset-x-0 bottom-[calc(4rem+env(safe-area-inset-bottom))] max-h-[72dvh] overflow-y-auto rounded-t-3xl border-t border-border bg-card p-4 pb-6 shadow-2xl">
              <div className="mb-4 flex items-center justify-between">
                <div>
                  <p className="font-extrabold text-foreground">Все разделы</p>
                  <p className="text-xs text-muted-foreground">{user?.username} · {user?.role}</p>
                </div>
                <button aria-label="Закрыть меню" onClick={() => setMobileMenuOpen(false)} className="rounded-full bg-muted p-2 text-foreground"><X className="h-5 w-5" /></button>
              </div>
              <div className="grid grid-cols-2 gap-2">
                {mobileMoreItems.map((item) => (
                  <NavLink key={item.to} to={item.to} className={({ isActive }) => cn("rounded-2xl border p-3 transition-colors", isActive ? "border-primary bg-primary/10 text-primary" : "border-border bg-background text-foreground")}>
                    <item.icon className="mb-2 h-5 w-5" />
                    <p className="text-sm font-bold leading-tight">{item.label}</p>
                    <p className="mt-1 text-[11px] leading-tight text-muted-foreground">{item.description}</p>
                  </NavLink>
                ))}
              </div>
              <button onClick={handleLogout} className="mt-3 flex w-full items-center justify-center gap-2 rounded-2xl border border-critical/20 bg-critical/10 px-4 py-3 font-bold text-critical">
                <LogOut className="h-5 w-5" />{t('logout')}
              </button>
            </section>
          </div>
        )}

        {/* Mobile Bottom Navigation */}
        <nav className="lg:hidden absolute bottom-0 w-full h-[calc(4rem+env(safe-area-inset-bottom))] pb-[env(safe-area-inset-bottom)] bg-white/95 dark:bg-zinc-900/95 backdrop-blur-md border-t border-sand dark:border-zinc-800 flex justify-around items-center px-1 z-50">
          {mobilePrimaryItems.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              className={({ isActive }) => cn(
                "flex flex-col items-center justify-center min-w-0 flex-1 h-16 transition-colors",
                isActive ? "text-primary" : "text-graphite/50 dark:text-zinc-400 hover:text-primary/70"
              )}
            >
              {({ isActive }) => (
                <>
                  <item.icon className={cn("w-5 h-5 mb-0.5", isActive && "fill-current/20")} />
                  <span className="max-w-full truncate px-1 text-[9px] font-semibold tracking-tight">{item.label}</span>
                </>
              )}
            </NavLink>
          ))}
          <button onClick={() => setMobileMenuOpen((open) => !open)} aria-expanded={mobileMenuOpen} aria-label="Открыть все разделы" className={cn("flex h-16 min-w-0 flex-1 flex-col items-center justify-center transition-colors", mobileMenuOpen || isMoreRouteActive ? "text-primary" : "text-graphite/50 dark:text-zinc-400")}>
            <Menu className="mb-0.5 h-5 w-5" />
            <span className="text-[9px] font-semibold">Ещё</span>
          </button>
        </nav>
      </div>
    </div>
  );
}

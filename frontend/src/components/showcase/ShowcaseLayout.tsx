import React, { createContext, useContext, useEffect, useState } from 'react';
import { Link, NavLink, Outlet, useLocation } from 'react-router-dom';
import { Menu, X } from 'lucide-react';
import ShowcaseAuth from './ShowcaseAuth';
import { SHOWCASE_NAV } from './content';

type Mode = 'login' | 'register';

interface ShowcaseAuthControl {
  openAuth: (mode: Mode) => void;
}

const AuthControlContext = createContext<ShowcaseAuthControl | null>(null);

/**
 * Доступ к окну входа из любой страницы витрины.
 *
 * Диалог живёт в каркасе, а не в каждой странице: иначе при переходе между
 * разделами открытое окно исчезало бы вместе со страницей.
 */
export function useShowcaseAuth(): ShowcaseAuthControl {
  const control = useContext(AuthControlContext);
  if (!control) {
    throw new Error('useShowcaseAuth доступен только внутри ShowcaseLayout');
  }
  return control;
}

/** Знак проекта: кольцо с точкой внутри — бак и его содержимое. */
function Mark({ light = false }: { light?: boolean }) {
  return (
    <span className="flex items-center gap-2.5">
      <span
        className={`grid h-6 w-6 shrink-0 place-items-center rounded-full border ${
          light ? 'border-white/60' : 'border-verdant/60'
        }`}
      >
        <span className={`h-2 w-2 rounded-full ${light ? 'bg-white' : 'bg-verdant'}`} />
      </span>
      <span
        className={`mono-label !text-[12px] !tracking-[0.22em] ${
          light ? 'text-white' : 'text-ink'
        }`}
      >
        TazaBAK
      </span>
    </span>
  );
}

export default function ShowcaseLayout() {
  const [authOpen, setAuthOpen] = useState(false);
  const [authMode, setAuthMode] = useState<Mode>('login');
  const [menuOpen, setMenuOpen] = useState(false);
  // На первом экране лендинга под шапкой идёт тёмное видео, и светлое
  // стекло смотрелось бы приклеенной полосой. Пока герой не ушёл вверх,
  // шапка прозрачная и белая; дальше возвращается обычное стекло.
  const [atTop, setAtTop] = useState(true);
  const location = useLocation();
  const overHero = location.pathname === '/' && atTop;

  const openAuth = (mode: Mode) => {
    setAuthMode(mode);
    setAuthOpen(true);
    setMenuOpen(false);
  };

  // Переход между разделами закрывает меню и поднимает страницу наверх:
  // без этого новый раздел открывается с середины предыдущего.
  useEffect(() => {
    setMenuOpen(false);
    window.scrollTo(0, 0);
    setAtTop(true);
  }, [location.pathname]);

  useEffect(() => {
    const onScroll = () => setAtTop(window.scrollY < 80);
    onScroll();
    window.addEventListener('scroll', onScroll, { passive: true });
    return () => window.removeEventListener('scroll', onScroll);
  }, []);

  const linkClass = ({ isActive }: { isActive: boolean }) =>
    `text-sm transition-colors ${
      overHero
        ? isActive
          ? 'text-white'
          : 'text-white/70 hover:text-white'
        : isActive
          ? 'text-ink'
          : 'text-body hover:text-ink'
    }`;

  return (
    <div className="showcase flex min-h-screen flex-col">
      <AuthControlContext.Provider value={{ openAuth }}>
        <ShowcaseAuth
          isOpen={authOpen}
          initialMode={authMode}
          onClose={() => setAuthOpen(false)}
        />

        <header
          className={`sticky top-0 z-50 border-b transition-colors duration-300 ${
            overHero ? 'border-white/15 bg-transparent' : 'glass-bar border-ink/8'
          }`}
        >
          <div className="mx-auto flex h-16 max-w-6xl items-center justify-between gap-4 px-5">
            <Link to="/" aria-label="На главную">
              <Mark light={overHero} />
            </Link>

            <nav className="hidden items-center gap-8 md:flex">
              {SHOWCASE_NAV.map((item) => (
                <NavLink key={item.to} to={item.to} className={linkClass}>
                  {item.label}
                </NavLink>
              ))}
            </nav>

            <div className="flex items-center gap-2">
              <button
                type="button"
                onClick={() => openAuth('login')}
                className={`rounded-lg px-4 py-2 text-sm font-medium transition-colors ${
                  overHero ? 'bg-white text-ink hover:bg-white/90' : 'bg-ink text-white hover:opacity-90'
                }`}
              >
                Войти
              </button>
              <button
                type="button"
                onClick={() => setMenuOpen((value) => !value)}
                aria-expanded={menuOpen}
                aria-label="Меню разделов"
                className="rounded-lg border border-ink/12 p-2 text-ink transition-colors hover:bg-ink/5 md:hidden"
              >
                {menuOpen ? <X className="h-4 w-4" /> : <Menu className="h-4 w-4" />}
              </button>
            </div>
          </div>

          {/* Разделы на телефоне: без этого меню витрина на телефоне
              превращается в одну длинную ленту без навигации. */}
          {menuOpen && (
            <nav className="border-t border-ink/8 px-5 py-3 md:hidden">
              {SHOWCASE_NAV.map((item) => (
                <NavLink
                  key={item.to}
                  to={item.to}
                  className={({ isActive }) =>
                    `block border-b border-ink/8 py-3 text-sm last:border-0 ${
                      isActive ? 'text-ink' : 'text-body'
                    }`
                  }
                >
                  {item.label}
                </NavLink>
              ))}
            </nav>
          )}
        </header>

        <main className="flex-1">
          <Outlet />
        </main>

        <footer className="border-t border-ink/8 bg-band">
          <div className="mx-auto max-w-6xl px-5 py-14">
            <div className="flex flex-wrap items-center justify-between gap-6">
              <Mark />
              <nav className="flex flex-wrap gap-x-7 gap-y-3">
                {SHOWCASE_NAV.map((item) => (
                  <Link
                    key={item.to}
                    to={item.to}
                    className="text-sm text-body transition-colors hover:text-ink"
                  >
                    {item.label}
                  </Link>
                ))}
                <Link to="/demo" className="text-sm text-body transition-colors hover:text-ink">
                  Быстрый вход
                </Link>
              </nav>
            </div>

            <p className="mt-10 max-w-3xl text-xs leading-relaxed text-faint">
              Прототип для Future Minds Hackathon 2026, трек EcoFin. Экономические
              параметры пилота — оценки, которые уточняются при монтаже и меняются из
              панели без переразвёртывания. Отчёт об экономии содержит только
              агрегированные городские данные без персональных.
            </p>
            <p className="mt-4 text-xs text-faint">© 2026 TazaBAK EcoFin · Кокшетау</p>
          </div>
        </footer>
      </AuthControlContext.Provider>
    </div>
  );
}

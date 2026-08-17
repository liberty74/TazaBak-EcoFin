import React from 'react';
import { useQuery } from '@tanstack/react-query';
import { Camera, Map as MapIcon, ChevronRight, Leaf, Star, Info, HeartHandshake, Award } from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../store/AuthContext';
import { useLocaleTheme } from '../store/LocaleThemeContext';
import { fetchUserDashboard } from '../api/users';
import { queryKeys } from '../api/queryKeys';

export default function HomePage() {
  const { user } = useAuth();
  const navigate = useNavigate();
  const { t, locale } = useLocaleTheme();

  const { data: dashboard, isLoading } = useQuery({
    queryKey: queryKeys.user.dashboard(user?.id),
    queryFn: () => fetchUserDashboard(user?.id || ''),
    enabled: !!user?.id,
  });

  const profile = dashboard?.profile;
  const recentTransactions = dashboard?.transactions?.slice(0, 3) || [];

  return (
    <div className="p-4 md:p-8 max-w-5xl mx-auto w-full space-y-6 pt-6 pb-24 lg:pb-8">
      {/* Header Profile Section */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 bg-white dark:bg-zinc-900 p-6 rounded-3xl border border-sand dark:border-zinc-800 shadow-sm">
        <div>
          <h2 className="text-2xl font-bold text-graphite dark:text-white mb-1">
            {t('greeting').replace('{name}', profile?.username || user?.username || '')} 👋
          </h2>
          <p className="text-graphite/60 dark:text-zinc-400">{t('subGreeting')}</p>
        </div>
        <div className="flex items-center gap-4">
          <button onClick={() => navigate('/profile')} className="bg-cream dark:bg-zinc-800 px-4 py-3 rounded-2xl flex items-center gap-3 hover:bg-sand/50 dark:hover:bg-zinc-700/50 transition-colors text-left">
            <div className="bg-primary/10 p-2 rounded-full text-primary">
              <Leaf className="w-5 h-5" />
            </div>
            <div>
              <p className="text-xs text-graphite/50 dark:text-zinc-400 font-medium">{t('points')}</p>
              <p className="font-bold text-lg leading-none text-graphite dark:text-white">{isLoading ? '...' : profile?.points}</p>
            </div>
          </button>
          <div className="bg-cream dark:bg-zinc-800 px-4 py-3 rounded-2xl flex items-center gap-3">
            <div className="bg-warning/10 p-2 rounded-full text-warning">
              <Star className="w-5 h-5" />
            </div>
            <div>
              <p className="text-xs text-graphite/50 dark:text-zinc-400 font-medium">{t('status')}</p>
              <p className="font-bold text-lg leading-none capitalize text-graphite dark:text-white">{isLoading ? '...' : profile?.status_tier}</p>
            </div>
          </div>
        </div>
      </div>

      {/* Main Actions */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <button 
          onClick={() => navigate('/scan')}
          className="group relative overflow-hidden bg-primary text-white p-6 rounded-3xl shadow-sm text-left hover:shadow-lg transition-all duration-300 min-h-[160px] flex flex-col justify-between"
        >
          <div className="absolute -right-4 -bottom-4 opacity-10 group-hover:scale-110 transition-transform duration-500">
            <Camera className="w-48 h-48" />
          </div>
          <div className="bg-white/20 w-12 h-12 rounded-2xl flex items-center justify-center mb-4 backdrop-blur-sm">
            <Camera className="w-6 h-6" />
          </div>
          <div>
            <h3 className="text-xl font-bold mb-1">{t('scanBread')}</h3>
            <p className="text-white/80 text-sm">Отсканируйте хлеб на содержание плесени и откройте смарт-бак</p>
          </div>
        </button>
        
        <button 
          onClick={() => navigate('/map')}
          className="group relative overflow-hidden bg-white dark:bg-zinc-900 text-graphite dark:text-white p-6 rounded-3xl shadow-sm border border-sand dark:border-zinc-800 text-left hover:shadow-md transition-all duration-300 min-h-[160px] flex flex-col justify-between"
        >
          <div className="absolute -right-4 -bottom-4 opacity-[0.03] group-hover:scale-110 transition-transform duration-500">
            <MapIcon className="w-48 h-48" />
          </div>
          <div className="bg-cream dark:bg-zinc-800 w-12 h-12 rounded-2xl flex items-center justify-center mb-4 text-primary">
            <MapIcon className="w-6 h-6" />
          </div>
          <div className="flex items-end justify-between">
            <div>
              <h3 className="text-xl font-bold mb-1">{t('findBin')}</h3>
              <p className="text-graphite/60 dark:text-zinc-400 text-sm">Интерактивная карта смарт-баков TazaBAK</p>
            </div>
            <ChevronRight className="w-6 h-6 text-graphite/30 group-hover:text-primary transition-colors" />
          </div>
        </button>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <button 
          onClick={() => navigate('/volunteer')}
          className="group bg-white dark:bg-zinc-900 border border-sand dark:border-zinc-800 p-5 rounded-3xl flex items-center justify-between hover:border-bread transition-colors text-left shadow-sm"
        >
          <div className="flex items-center gap-4">
            <div className="w-12 h-12 bg-bread/10 text-bread rounded-2xl flex items-center justify-center">
              <HeartHandshake className="w-6 h-6" />
            </div>
            <div>
              <h4 className="font-bold text-graphite dark:text-white">{t('navVolunteer')}</h4>
              <p className="text-sm text-graphite/60 dark:text-zinc-400">Помощь приютам для бездомных животных</p>
            </div>
          </div>
          <ChevronRight className="w-5 h-5 text-graphite/30 group-hover:text-bread transition-colors" />
        </button>

        <button 
          onClick={() => navigate('/leaderboard')}
          className="group bg-white dark:bg-zinc-900 border border-sand dark:border-zinc-800 p-5 rounded-3xl flex items-center justify-between hover:border-warning transition-colors text-left shadow-sm"
        >
          <div className="flex items-center gap-4">
            <div className="w-12 h-12 bg-warning/10 text-warning rounded-2xl flex items-center justify-center">
              <Award className="w-6 h-6" />
            </div>
            <div>
              <h4 className="font-bold text-graphite dark:text-white">{t('navLeaderboard')}</h4>
              <p className="text-sm text-graphite/60 dark:text-zinc-400">Лидеры экологического движения Көкшетау</p>
            </div>
          </div>
          <ChevronRight className="w-5 h-5 text-graphite/30 group-hover:text-warning transition-colors" />
        </button>
      </div>

      {/* Recent Activity or News */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <div>
          <div className="flex items-center justify-between mb-4 px-2">
            <h3 className="font-bold text-lg text-graphite dark:text-white">{t('recentOps')}</h3>
            <button onClick={() => navigate('/profile')} className="text-primary text-sm font-medium hover:underline">Профиль</button>
          </div>
          <div className="space-y-3">
            {isLoading ? (
              <div className="animate-pulse bg-white dark:bg-zinc-900 p-4 rounded-2xl border border-sand dark:border-zinc-800 h-[72px]" />
            ) : recentTransactions.length > 0 ? (
              recentTransactions.map((tx) => (
                <div key={tx.id} className="bg-white dark:bg-zinc-900 p-4 rounded-2xl border border-sand dark:border-zinc-800 flex items-center justify-between">
                  <div>
                    <h4 className="font-bold text-sm text-graphite dark:text-white">{tx.description}</h4>
                    <span className="text-[10px] text-graphite/40 dark:text-zinc-500 block">
                      {new Date(tx.created_at).toLocaleString(locale === 'RU' ? 'ru-RU' : 'kk-KZ')}
                    </span>
                  </div>
                  <div className={`font-bold ${tx.amount > 0 ? 'text-primary' : 'text-graphite dark:text-zinc-300'}`}>
                    {tx.amount > 0 ? '+' : ''}{tx.amount}
                  </div>
                </div>
              ))
            ) : (
              <div className="bg-white dark:bg-zinc-900 p-4 rounded-2xl border border-sand dark:border-zinc-800 text-center text-sm text-graphite/50 dark:text-zinc-500">
                {t('noOps')}
              </div>
            )}
          </div>
        </div>

        <div>
          <div className="flex items-center justify-between mb-4 px-2">
            <h3 className="font-bold text-lg text-graphite dark:text-white">{t('newsTitle')}</h3>
          </div>
          <div className="space-y-3">
            <div className="bg-white dark:bg-zinc-900 p-4 rounded-2xl border border-sand dark:border-zinc-800 flex gap-4 items-start">
              <div className="bg-cream dark:bg-zinc-800 p-3 rounded-xl text-primary shrink-0">
                <Info className="w-6 h-6" />
              </div>
              <div>
                <h4 className="font-bold text-sm mb-1 text-graphite dark:text-white">Новый бак в микрорайоне Сарыарка!</h4>
                <p className="text-xs text-graphite/60 dark:text-zinc-400 leading-relaxed">{t('newsDesc')}</p>
                <span className="text-[10px] text-graphite/40 dark:text-zinc-500 mt-2 block">Презентационный контент</span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

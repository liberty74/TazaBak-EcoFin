import React from 'react';
import { useQuery } from '@tanstack/react-query';
import { Award, Trophy, ChevronRight, ArrowUpRight, Shield, Leaf } from 'lucide-react';
import { fetchLeaderboard } from '../api/users';
import { queryKeys } from '../api/queryKeys';
import { useAuth } from '../store/AuthContext';
import { useLocaleTheme } from '../store/LocaleThemeContext';
import { motion } from 'motion/react';
import { useNavigate } from 'react-router-dom';

export default function LeaderboardPage() {
  const { user } = useAuth();
  const { t } = useLocaleTheme();
  const navigate = useNavigate();

  const { data: activists = [], isLoading, isError } = useQuery({
    queryKey: queryKeys.leaderboard,
    queryFn: () => fetchLeaderboard(15),
  });

  const top3 = activists.slice(0, 3);
  const remaining = activists.slice(3);

  // Find current user's placement if available
  const userRankIndex = activists.findIndex(a => a.username === user?.username);
  const userRank = userRankIndex !== -1 ? userRankIndex + 1 : null;
  const userProfile = userRankIndex !== -1 ? activists[userRankIndex] : null;

  const podiumColors = [
    { bg: 'bg-yellow-500/10 border-yellow-500/30', text: 'text-yellow-600', trophy: 'text-yellow-500', fill: 'from-yellow-400 to-yellow-600' }, // Gold
    { bg: 'bg-slate-400/10 border-slate-400/30', text: 'text-slate-600', trophy: 'text-slate-400', fill: 'from-slate-300 to-slate-500' }, // Silver
    { bg: 'bg-amber-600/10 border-amber-600/30', text: 'text-amber-700', trophy: 'text-amber-600', fill: 'from-amber-500 to-amber-700' }, // Bronze
  ];

  return (
    <div className="p-4 md:p-8 max-w-4xl mx-auto w-full pt-8 pb-24 lg:pb-8 space-y-6">
      {/* Title */}
      <div className="flex justify-between items-center mb-2">
        <div>
          <h1 className="text-3xl font-extrabold text-primary tracking-tight">{t('navLeaderboard')}</h1>
          <p className="text-graphite/60 text-sm">Каждый вклад важен • {t('city')}</p>
        </div>
        <button 
          onClick={() => navigate('/scan')}
          className="bg-primary hover:bg-primary/95 text-white font-bold text-sm px-4 py-2.5 rounded-xl flex items-center gap-1.5 transition-colors shadow-sm"
        >
          <span>Получить баллы</span>
          <ArrowUpRight className="w-4 h-4" />
        </button>
      </div>

      {isLoading ? (
        <div className="space-y-4">
          <div className="grid grid-cols-3 gap-4 h-48 bg-white rounded-3xl border border-sand animate-pulse" />
          <div className="h-64 bg-white rounded-3xl border border-sand animate-pulse" />
        </div>
      ) : isError ? (
        <div className="bg-critical/10 border border-critical/20 rounded-2xl p-6 text-center text-critical font-medium">
          Не удалось загрузить таблицу лидеров. Пожалуйста, проверьте бэкенд.
        </div>
      ) : (
        <>
          {/* Podium for top 3 */}
          {top3.length > 0 && (
            <div className="grid grid-cols-3 gap-2 md:gap-4 items-end pt-6 pb-2">
              {/* 2nd place */}
              {top3[1] && (
                <motion.div 
                  initial={{ opacity: 0, y: 20 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: 0.1 }}
                  className="flex flex-col items-center bg-white border border-sand p-4 rounded-3xl text-center shadow-sm relative h-[180px] md:h-[210px] justify-end"
                >
                  <div className="absolute top-4 w-12 h-12 rounded-full bg-slate-100 flex items-center justify-center font-bold text-slate-500 border-2 border-slate-300 shadow-inner">
                    {top3[1].username.charAt(0).toUpperCase()}
                  </div>
                  <Trophy className="w-6 h-6 text-slate-400 mb-2" />
                  <p className="font-bold text-sm text-graphite truncate w-full px-1">{top3[1].username}</p>
                  <span className="text-xs text-graphite/50 mb-3">{top3[1].status_tier}</span>
                  <div className="bg-slate-400 text-white font-bold px-3 py-1 rounded-full text-xs min-w-[50px] shadow-sm">
                    {top3[1].points}
                  </div>
                  <div className="absolute -top-3 bg-slate-500 text-white text-[10px] font-bold px-2 py-0.5 rounded-full">
                    2 Место
                  </div>
                </motion.div>
              )}

              {/* 1st place */}
              {top3[0] && (
                <motion.div 
                  initial={{ opacity: 0, y: 25 }}
                  animate={{ opacity: 1, y: 0 }}
                  className="flex flex-col items-center bg-white border-2 border-primary-light/50 p-4 rounded-3xl text-center shadow-md relative h-[210px] md:h-[240px] justify-end scale-105"
                >
                  <div className="absolute top-4 w-14 h-14 rounded-full bg-yellow-50 flex items-center justify-center font-bold text-yellow-600 border-4 border-yellow-400 shadow-inner">
                    {top3[0].username.charAt(0).toUpperCase()}
                  </div>
                  <Trophy className="w-8 h-8 text-yellow-500 mb-2 animate-bounce" />
                  <p className="font-extrabold text-base text-graphite truncate w-full px-1">{top3[0].username}</p>
                  <span className="text-xs text-primary font-semibold mb-3 flex items-center gap-0.5 justify-center">
                    <Leaf className="w-3.5 h-3.5" />
                    {top3[0].status_tier}
                  </span>
                  <div className="bg-primary text-white font-extrabold px-4 py-1.5 rounded-full text-xs min-w-[60px] shadow-md">
                    {top3[0].points}
                  </div>
                  <div className="absolute -top-3 bg-yellow-500 text-white text-xs font-bold px-2.5 py-1 rounded-full shadow-sm">
                    👑 1 Место
                  </div>
                </motion.div>
              )}

              {/* 3rd place */}
              {top3[2] && (
                <motion.div 
                  initial={{ opacity: 0, y: 20 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: 0.2 }}
                  className="flex flex-col items-center bg-white border border-sand p-4 rounded-3xl text-center shadow-sm relative h-[160px] md:h-[190px] justify-end"
                >
                  <div className="absolute top-4 w-12 h-12 rounded-full bg-amber-50 flex items-center justify-center font-bold text-amber-700 border-2 border-amber-500 shadow-inner">
                    {top3[2].username.charAt(0).toUpperCase()}
                  </div>
                  <Trophy className="w-5 h-5 text-amber-600 mb-2" />
                  <p className="font-bold text-sm text-graphite truncate w-full px-1">{top3[2].username}</p>
                  <span className="text-xs text-graphite/50 mb-3">{top3[2].status_tier}</span>
                  <div className="bg-amber-600 text-white font-bold px-3 py-1 rounded-full text-xs min-w-[50px] shadow-sm">
                    {top3[2].points}
                  </div>
                  <div className="absolute -top-3 bg-amber-600 text-white text-[10px] font-bold px-2 py-0.5 rounded-full">
                    3 Место
                  </div>
                </motion.div>
              )}
            </div>
          )}

          {/* User's own score alert badge */}
          {userRank && userProfile && (
            <div className="bg-primary/10 border border-primary/20 p-4 rounded-2xl flex items-center justify-between shadow-sm">
              <div className="flex items-center gap-3">
                <div className="bg-primary text-white font-extrabold w-10 h-10 rounded-xl flex items-center justify-center">
                  #{userRank}
                </div>
                <div>
                  <p className="font-bold text-graphite">Ваша позиция в рейтинге</p>
                  <p className="text-xs text-graphite/60 capitalize">{userProfile.status_tier} • {userProfile.role}</p>
                </div>
              </div>
              <div className="font-bold text-primary text-lg">
                {userProfile.points} 🐾
              </div>
            </div>
          )}

          {/* Rest of the list */}
          <div className="bg-white border border-sand rounded-3xl p-4 md:p-6 shadow-sm">
            <h3 className="font-bold text-lg mb-4 text-graphite">Рейтинг эко-активистов</h3>
            <div className="divide-y divide-sand">
              {remaining.length > 0 ? (
                remaining.map((activist, index) => {
                  const rank = index + 4;
                  const isSelf = activist.username === user?.username;
                  return (
                    <div 
                      key={activist.id} 
                      className={`flex items-center justify-between py-3 px-2 rounded-xl transition-colors ${
                        isSelf ? 'bg-primary/5 border border-primary/20' : 'hover:bg-cream/50'
                      }`}
                    >
                      <div className="flex items-center gap-4">
                        <span className="font-mono font-bold text-graphite/40 w-6 text-center">#{rank}</span>
                        <div className="w-10 h-10 rounded-full bg-cream flex items-center justify-center font-bold text-primary border border-sand">
                          {activist.username.charAt(0).toUpperCase()}
                        </div>
                        <div>
                          <p className={`font-bold text-sm ${isSelf ? 'text-primary' : 'text-graphite'}`}>
                            {activist.username} {isSelf && <span className="text-xs text-primary-light font-medium ml-1">(Вы)</span>}
                          </p>
                          <span className="text-xs text-graphite/50 capitalize">{activist.status_tier}</span>
                        </div>
                      </div>
                      <div className="font-bold text-sm text-graphite">
                        {activist.points} 🐾
                      </div>
                    </div>
                  );
                })
              ) : (
                <div className="text-center py-6 text-graphite/40 text-sm">
                  Дополнительные участники появятся при обновлении рейтинга
                </div>
              )}
            </div>
          </div>
        </>
      )}
    </div>
  );
}

import React, { useEffect, useState } from 'react';
import { Battery, Activity, AlertTriangle, MessageSquare, Bot } from 'lucide-react';
import { useQuery } from '@tanstack/react-query';
import { fetchDispatchSummary, fetchDispatchBriefing } from '../../api/dispatcher';
import { queryKeys } from '../../api/queryKeys';
import { useApiHealth } from '../../api/useApiHealth';
import { cn } from '../../lib/utils';

export default function DashboardPage() {
  const [isTabActive, setIsTabActive] = useState(!document.hidden);

  useEffect(() => {
    const handleVisibilityChange = () => {
      setIsTabActive(!document.hidden);
    };
    document.addEventListener("visibilitychange", handleVisibilityChange);
    return () => document.removeEventListener("visibilitychange", handleVisibilityChange);
  }, []);

  const { data: summary, isLoading: isSummaryLoading } = useQuery({
    queryKey: queryKeys.dispatcher.summary,
    queryFn: fetchDispatchSummary,
    refetchInterval: isTabActive ? 10000 : false,
  });

  const { data: briefing, isLoading: isBriefingLoading } = useQuery({
    queryKey: queryKeys.dispatcher.briefing,
    queryFn: fetchDispatchBriefing,
    refetchInterval: isTabActive ? 30000 : false,
  });

  const { status: healthStatus } = useApiHealth();

  const getHealthText = () => {
    switch (healthStatus) {
      case 'checking': return 'Проверка...';
      case 'connected': return 'АКТИВНА';
      case 'db_error': return 'БАЗА ОШИБКА';
      case 'disconnected':
      default: return 'ОТКЛЮЧЕНА';
    }
  };

  const getHealthClass = () => {
    switch (healthStatus) {
      case 'checking': return 'text-amber-500';
      case 'connected': return 'text-primary';
      case 'db_error': return 'text-amber-500';
      case 'disconnected':
      default: return 'text-critical';
    }
  };

  const getAlertIcon = (type: string) => {
    const t = type.toUpperCase();
    if (t.includes('FIRE_RISK') || t.includes('BIO_SCAN_SABOTAGE')) return 'bg-critical/20 text-critical';
    return 'bg-warning/20 text-warning';
  };

  return (
    <div className="space-y-6 max-w-7xl mx-auto pb-24 lg:pb-8 text-foreground">
      <div className="flex items-center justify-between mb-4">
        <h1 className="text-2xl font-bold">Обзор системы</h1>
        {isSummaryLoading && <div className="text-xs text-foreground/50 animate-pulse">Обновление...</div>}
      </div>

      <div className="grid grid-cols-2 lg:grid-cols-4 gap-3 md:gap-4">
        {/* Stat Cards */}
        <div className="bg-card border border-border p-4 md:p-6 rounded-2xl md:rounded-3xl shadow-sm flex flex-col min-w-0">
          <div className="flex justify-between items-start mb-4">
            <div className="p-3 bg-primary/10 text-primary rounded-xl">
              <Battery className="w-6 h-6" />
            </div>
          </div>
          <div>
            <h3 className="text-foreground/60 text-sm font-medium">Связь с баками</h3>
            <p className={cn("text-xl md:text-2xl font-black mt-1 tracking-tight break-words", getHealthClass())}>
              {getHealthText()}
            </p>
          </div>
        </div>
        
        <div className="bg-card border border-border p-4 md:p-6 rounded-2xl md:rounded-3xl shadow-sm flex flex-col min-w-0">
          <div className="flex justify-between items-start mb-4">
            <div className="p-3 bg-critical/10 text-critical rounded-xl">
              <AlertTriangle className="w-6 h-6" />
            </div>
          </div>
          <div>
            <h3 className="text-foreground/60 text-sm font-medium">Активных инцидентов</h3>
            <p className="text-3xl font-black mt-1 tracking-tight">
              {isSummaryLoading ? '...' : summary?.total_unresolved || 0}
            </p>
          </div>
        </div>

        <div className="bg-card border border-border p-4 md:p-6 rounded-2xl md:rounded-3xl shadow-sm flex flex-col min-w-0">
          <div className="flex justify-between items-start mb-4">
            <div className="p-3 bg-warning/10 text-warning rounded-xl">
              <Activity className="w-6 h-6" />
            </div>
          </div>
          <div>
            <h3 className="text-foreground/60 text-sm font-medium">Алерты переполнения</h3>
            <p className="text-3xl font-black mt-1 tracking-tight">
              {isSummaryLoading ? '...' : (summary?.counts_by_type['FULL_BIN'] || 0)}
            </p>
          </div>
        </div>

        <div className="bg-card border border-border p-4 md:p-6 rounded-2xl md:rounded-3xl shadow-sm flex flex-col min-w-0">
          <div className="flex justify-between items-start mb-4">
            <div className="p-3 bg-info/10 text-info rounded-xl">
              <Activity className="w-6 h-6" />
            </div>
          </div>
          <div>
            <h3 className="text-foreground/60 text-sm font-medium">Ошибки сканера</h3>
            <p className="text-3xl font-black mt-1 tracking-tight">
               {isSummaryLoading ? '...' : (summary?.counts_by_type['BIO_SCAN_SABOTAGE'] || 0)}
            </p>
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* AI Briefing */}
        <div className="lg:col-span-2 bg-gradient-to-br from-primary to-primary-light border border-primary-light p-6 rounded-3xl shadow-sm text-white">
          <div className="flex items-center gap-3 mb-6">
            <div className="w-10 h-10 bg-white/20 rounded-full flex items-center justify-center">
              <Bot className="w-5 h-5 text-white" />
            </div>
            <div>
              <h3 className="font-bold text-lg leading-none">AI-Сводка</h3>
              <p className="text-xs text-white/70 mt-1">Gemini анализирует обстановку</p>
            </div>
          </div>
          <div className="bg-black/20 rounded-2xl p-5 backdrop-blur-sm min-h-[180px] max-h-72 overflow-y-auto overscroll-contain">
             {isBriefingLoading ? (
                <div className="animate-pulse space-y-3">
                  <div className="h-4 bg-white/20 rounded w-full"></div>
                  <div className="h-4 bg-white/20 rounded w-5/6"></div>
                  <div className="h-4 bg-white/20 rounded w-4/6"></div>
                </div>
             ) : (
                <p className="text-white/90 leading-relaxed whitespace-pre-wrap">
                  {briefing?.text || "Нет данных для формирования сводки."}
                </p>
             )}
          </div>
        </div>

        {/* Live Feed */}
        <div className="bg-card border border-border p-6 rounded-3xl shadow-sm flex flex-col h-[400px]">
          <h3 className="font-bold text-lg mb-4 flex items-center gap-2">
            <MessageSquare className="w-5 h-5 text-primary" /> Живая лента алертов
          </h3>
          <div className="flex-1 overflow-y-auto space-y-4 pr-2">
            {isSummaryLoading ? (
               Array.from({ length: 4 }).map((_, i) => (
                 <div key={i} className="animate-pulse flex gap-3 pb-3">
                   <div className="w-10 h-10 bg-muted rounded-xl shrink-0"></div>
                   <div className="flex-1 space-y-2">
                     <div className="h-3 bg-muted rounded w-full"></div>
                     <div className="h-3 bg-muted rounded w-1/2"></div>
                   </div>
                 </div>
               ))
            ) : summary?.tasks && summary.tasks.length > 0 ? (
              summary.tasks.slice(0, 10).map((task) => (
                <div key={task.id} className="flex gap-3 border-b border-border pb-3 last:border-0 items-start">
                  <div className={`p-2 rounded-xl mt-1 shrink-0 ${getAlertIcon(task.type)}`}>
                     {task.type.includes('SABOTAGE') || task.type.includes('FIRE_RISK') ? <AlertTriangle className="w-4 h-4" /> : <Activity className="w-4 h-4" />}
                  </div>
                  <div>
                    <p className="text-sm font-bold">
                      {task.message}
                    </p>
                    <div className="flex items-center gap-2 mt-1">
                      <span className="text-[10px] bg-muted px-2 py-0.5 rounded-md text-foreground/60 font-mono">
                        {task.device_id || 'SYSTEM'}
                      </span>
                      <span className="text-[10px] text-foreground/40 font-mono">
                        {new Date(task.created_at).toLocaleTimeString('ru-RU')}
                      </span>
                    </div>
                  </div>
                </div>
              ))
            ) : (
              <div className="text-center text-foreground/50 text-sm py-10">Нет недавних событий</div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

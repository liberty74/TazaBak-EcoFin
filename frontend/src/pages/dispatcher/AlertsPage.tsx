import React, { useState } from 'react';
import { AlertTriangle, CheckCircle, Clock, Search, Filter, Loader2, Eye, ExternalLink } from 'lucide-react';
import { motion, AnimatePresence } from 'motion/react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { fetchDispatchSummary, resolveAlert } from '../../api/dispatcher';
import { queryKeys, handleApiError, resolveMediaUrl } from '../../api';
import { toast } from 'sonner';

export default function AlertsPage() {
  const [filter, setFilter] = useState<'all' | 'critical' | 'warning'>('all');
  const [searchQuery, setSearchQuery] = useState('');
  const [resolvingId, setResolvingId] = useState<number | null>(null);
  const [mobileVisibleCount, setMobileVisibleCount] = useState(10);
  const queryClient = useQueryClient();

  const { data: summary, isLoading, isError, refetch } = useQuery({
    queryKey: queryKeys.dispatcher.summary,
    queryFn: fetchDispatchSummary,
    refetchInterval: 5_000,
  });

  const resolveMutation = useMutation({
    mutationFn: resolveAlert,
    onSuccess: () => {
      toast.success('Алерт успешно решён');
      queryClient.invalidateQueries({ queryKey: queryKeys.dispatcher.summary });
    },
    onError: (e) => {
      const normErr = handleApiError(e);
      toast.error(normErr.message);
    }
  });

  const getAlertStatus = (type: string, backendStatus?: string) => {
    if (backendStatus?.toUpperCase() === 'CRITICAL') return 'critical';
    const t = type.toUpperCase();
    if (t.includes('FIRE_RISK') || t.includes('BIO_SCAN_SABOTAGE')) {
      return 'critical';
    }
    return 'warning';
  };

  const tasks = summary?.tasks || [];
  
  // Only process active (unresolved) alerts as they should disappear upon resolution
  const activeAlerts = tasks.filter(task => task.status !== 'RESOLVED');

  const filteredAlerts = activeAlerts.filter(alert => {
    // Filter by severity tab
    if (filter === 'critical' && getAlertStatus(alert.type, alert.status) !== 'critical') return false;
    if (filter === 'warning' && getAlertStatus(alert.type, alert.status) !== 'warning') return false;

    // Live search on device_id or message
    if (searchQuery.trim() !== '') {
      const query = searchQuery.toLowerCase();
      return [String(alert.id), alert.device_id ?? '', alert.type, alert.message]
        .some((value) => value.toLowerCase().includes(query));
    }

    return true;
  });

  React.useEffect(() => {
    setMobileVisibleCount(10);
  }, [filter, searchQuery]);

  const mobileAlerts = filteredAlerts.slice(0, mobileVisibleCount);

  const handleResolve = async (id: number) => {
    if (!window.confirm(`Подтвердите обработку инцидента №${id}.`)) return;
    setResolvingId(id);
    try {
      await resolveMutation.mutateAsync(id);
    } catch (e) {
      // Handled by mutation onError
    } finally {
      setResolvingId(null);
    }
  };

  return (
    <div className="space-y-6 max-w-7xl mx-auto pb-24 lg:pb-8">
      <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4">
        <div>
          <h1 className="text-2xl font-bold mb-1 text-graphite">Алерты системы</h1>
          <p className="text-graphite/50 text-sm">Управление инцидентами от смарт-баков в режиме реального времени</p>
        </div>
        
        <div className="flex gap-2 w-full sm:w-auto">
          <div className="relative flex-1 sm:w-64">
            <Search className="w-4 h-4 absolute left-3 top-1/2 -translate-y-1/2 text-graphite/40" />
            <input 
              type="text" 
              placeholder="Поиск по ID бака или сообщению..." 
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-full bg-white border border-sand rounded-xl pl-9 pr-4 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary/20 text-graphite"
            />
          </div>
        </div>
      </div>

      {/* Action Filters without the Resolved tab */}
      <div className="flex gap-2 overflow-x-auto pb-2 hide-scrollbar">
        <button 
          onClick={() => setFilter('all')}
          className={`px-4 py-1.5 rounded-full text-sm font-medium transition-colors shrink-0 cursor-pointer ${filter === 'all' ? 'bg-primary text-white font-bold' : 'bg-white border border-sand text-graphite/60 hover:text-graphite'}`}
        >
          Активные ({activeAlerts.length})
        </button>
        <button 
          onClick={() => setFilter('critical')}
          className={`px-4 py-1.5 rounded-full text-sm font-medium transition-colors shrink-0 cursor-pointer ${filter === 'critical' ? 'bg-critical text-white font-bold' : 'bg-white border border-sand text-graphite/60 hover:text-critical'}`}
        >
          Критические ({activeAlerts.filter(t => getAlertStatus(t.type, t.status) === 'critical').length})
        </button>
        <button 
          onClick={() => setFilter('warning')}
          className={`px-4 py-1.5 rounded-full text-sm font-medium transition-colors shrink-0 cursor-pointer ${filter === 'warning' ? 'bg-warning text-white font-bold' : 'bg-white border border-sand text-graphite/60 hover:text-warning'}`}
        >
          Предупреждения ({activeAlerts.filter(t => getAlertStatus(t.type, t.status) === 'warning').length})
        </button>
      </div>

      <div className="space-y-3 md:hidden">
        {isLoading && (
          <div className="flex items-center justify-center gap-2 rounded-2xl border border-border bg-card px-4 py-10 text-muted-foreground">
            <Loader2 className="h-5 w-5 animate-spin text-primary" />Загрузка данных алертов...
          </div>
        )}
        {isError && (
          <div className="rounded-2xl border border-critical/20 bg-card p-5 text-center">
            <p className="mb-3 font-bold text-critical">Не удалось загрузить алерты.</p>
            <button onClick={() => refetch()} className="rounded-xl bg-primary px-4 py-2 text-white">Повторить</button>
          </div>
        )}
        {!isLoading && !isError && mobileAlerts.map((alert) => {
          const status = getAlertStatus(alert.type, alert.status);
          return (
            <article key={alert.id} className="rounded-2xl border border-border bg-card p-4 shadow-sm">
              <div className="flex items-start justify-between gap-3">
                <span className={`inline-flex items-center gap-1.5 rounded-full border px-2.5 py-1 text-[11px] font-bold ${status === 'critical' ? 'border-critical/20 bg-critical/10 text-critical' : 'border-warning/20 bg-warning/10 text-warning'}`}>
                  <AlertTriangle className="h-3.5 w-3.5" />{status === 'critical' ? 'Критический' : 'Предупреждение'}
                </span>
                <span className="font-mono text-xs text-muted-foreground">#{alert.id}</span>
              </div>
              <p className="mt-3 break-all font-mono text-sm font-bold text-foreground">{alert.device_id || 'SYSTEM'}</p>
              <p className="mt-2 text-sm font-semibold leading-relaxed text-foreground">{alert.message}</p>
              {alert.evidence_url && (
                <a href={resolveMediaUrl(alert.evidence_url) || '#'} target="_blank" rel="noreferrer" className="mt-3 flex items-center gap-3 rounded-xl border border-border bg-background p-2">
                  <img src={resolveMediaUrl(alert.evidence_url) || ''} alt="Фото инцидента" className="h-16 w-16 rounded-lg object-cover" />
                  <span className="flex items-center gap-1 text-xs font-bold text-primary">Открыть фото <ExternalLink className="h-3.5 w-3.5" /></span>
                </a>
              )}
              {alert.details && Object.keys(alert.details).length > 0 && (
                <details className="mt-3 rounded-xl border border-border bg-background p-3 text-xs">
                  <summary className="cursor-pointer font-bold text-foreground">Телеметрия инцидента</summary>
                  <pre className="mt-2 max-h-36 overflow-auto whitespace-pre-wrap break-words font-mono text-[10px] text-muted-foreground">{JSON.stringify(alert.details, null, 2)}</pre>
                </details>
              )}
              <div className="mt-3 flex items-center gap-1.5 text-xs text-muted-foreground">
                <Clock className="h-3.5 w-3.5" />{new Date(alert.created_at).toLocaleString('ru-RU')}
              </div>
              <button onClick={() => handleResolve(alert.id)} disabled={resolvingId === alert.id} className="mt-4 flex w-full items-center justify-center gap-2 rounded-xl bg-primary px-4 py-3 text-sm font-bold text-white disabled:opacity-50">
                {resolvingId === alert.id ? <Loader2 className="h-4 w-4 animate-spin" /> : <CheckCircle className="h-4 w-4" />}Решить
              </button>
            </article>
          );
        })}
        {!isLoading && !isError && filteredAlerts.length === 0 && (
          <div className="rounded-2xl border border-border bg-card px-5 py-10 text-center text-muted-foreground"><p className="font-bold text-foreground">Все чисто!</p><p className="mt-1 text-xs">Нет активных инцидентов по выбранным критериям.</p></div>
        )}
        {!isLoading && !isError && mobileVisibleCount < filteredAlerts.length && (
          <button onClick={() => setMobileVisibleCount((count) => count + 10)} className="w-full rounded-2xl border border-border bg-card px-4 py-3 text-sm font-bold text-primary shadow-sm">Показать ещё ({filteredAlerts.length - mobileVisibleCount})</button>
        )}
      </div>

      <div className="hidden bg-white border border-sand rounded-3xl overflow-hidden shadow-sm md:block">
        <div className="overflow-x-auto">
          <table className="w-full text-left text-sm">
            <thead className="bg-sand/30 border-b border-sand">
              <tr>
                <th className="px-6 py-4 font-bold text-graphite/60 w-1/5">Степень важности</th>
                <th className="px-6 py-4 font-bold text-graphite/60 w-1/5">Устройство</th>
                <th className="px-6 py-4 font-bold text-graphite/60 w-2/5">Сообщение & Улики</th>
                <th className="px-6 py-4 font-bold text-graphite/60 w-1/5">Время возникновения</th>
                <th className="px-6 py-4 font-bold text-graphite/60 text-right">Действия</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-sand text-graphite">
              {isLoading ? (
                <tr>
                  <td colSpan={5} className="px-6 py-12 text-center text-graphite/40">
                    <div className="flex items-center justify-center gap-2">
                      <Loader2 className="w-5 h-5 animate-spin text-primary" />
                      <span>Загрузка данных алертов...</span>
                    </div>
                  </td>
                </tr>
              ) : isError ? (
                <tr><td colSpan={5} className="px-6 py-12 text-center"><p className="text-critical font-bold mb-3">Не удалось загрузить алерты.</p><button onClick={() => refetch()} className="bg-primary text-white px-4 py-2 rounded-xl">Повторить</button></td></tr>
              ) : (
                <AnimatePresence mode="popLayout">
                  {filteredAlerts.map((alert) => {
                    const status = getAlertStatus(alert.type, alert.status);
                    return (
                      <motion.tr 
                        key={alert.id}
                        layout
                        initial={{ opacity: 0, y: 8 }}
                        animate={{ opacity: 1, y: 0 }}
                        exit={{ opacity: 0, scale: 0.95 }}
                        transition={{ duration: 0.2 }}
                        className="hover:bg-sand/10 transition-colors group"
                      >
                        <td className="px-6 py-4 align-top">
                          {status === 'critical' ? (
                            <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-bold bg-critical/10 text-critical border border-critical/20">
                              <AlertTriangle className="w-3.5 h-3.5" /> Критический
                            </span>
                          ) : (
                            <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-bold bg-warning/10 text-warning border border-warning/20">
                              <AlertTriangle className="w-3.5 h-3.5" /> Предупреждение
                            </span>
                          )}
                        </td>
                        <td className="px-6 py-4 align-top">
                          <p className="font-mono font-bold text-graphite text-sm">{alert.device_id || 'SYSTEM'}</p>
                          <p className="text-xs text-graphite/40 font-mono mt-0.5">ID инцидента: {alert.id}</p>
                        </td>
                        <td className="px-6 py-4 align-top space-y-3">
                          <p className="font-semibold text-graphite">{alert.message}</p>
                          
                          {/* Evidence / Proof rendering */}
                          {alert.evidence_url && (
                            <div className="mt-2">
                              <p className="text-[10px] text-graphite/40 font-extrabold uppercase tracking-wider mb-1">Улики (фотофиксация):</p>
                              <a 
                                href={resolveMediaUrl(alert.evidence_url) || '#'} 
                                target="_blank" 
                                rel="noreferrer"
                                className="inline-flex items-center gap-1 group/link mt-1"
                              >
                                <div className="relative overflow-hidden rounded-2xl border border-sand">
                                  <img 
                                    src={resolveMediaUrl(alert.evidence_url) || ''} 
                                    alt="Evidence artifact" 
                                    className="w-28 h-28 object-cover hover:scale-105 transition-transform duration-200"
                                  />
                                  <div className="absolute inset-0 bg-black/40 opacity-0 group-hover/link:opacity-100 transition-opacity flex items-center justify-center text-white">
                                    <ExternalLink className="w-4 h-4" />
                                  </div>
                                </div>
                              </a>
                            </div>
                          )}

                          {/* Details Metadata rendering */}
                          {alert.details && Object.keys(alert.details).length > 0 && (
                            <div className="bg-cream/40 p-3 rounded-2xl border border-sand text-xs max-w-md mt-2 space-y-1">
                              <p className="text-[10px] text-graphite/40 font-extrabold uppercase tracking-wider">Подробные телеметрические данные:</p>
                              <pre className="font-mono text-[10px] whitespace-pre-wrap overflow-x-auto text-graphite/70">
                                {JSON.stringify(alert.details, null, 2)}
                              </pre>
                            </div>
                          )}
                        </td>
                        <td className="px-6 py-4 align-top">
                          <div className="flex items-center gap-1.5 text-graphite/60 text-xs mt-1">
                            <Clock className="w-3.5 h-3.5 text-graphite/40" />
                            {new Date(alert.created_at).toLocaleString('ru-RU')}
                          </div>
                        </td>
                        <td className="px-6 py-4 align-top text-right">
                          <button 
                            onClick={() => handleResolve(alert.id)}
                            disabled={resolvingId === alert.id}
                            className="bg-primary/10 text-primary hover:bg-primary hover:text-white px-4 py-2 rounded-xl text-xs font-bold transition-all disabled:opacity-50 flex items-center gap-1.5 ml-auto cursor-pointer shadow-sm"
                          >
                            {resolvingId === alert.id ? (
                              <Loader2 className="w-3.5 h-3.5 animate-spin" />
                            ) : (
                              <CheckCircle className="w-3.5 h-3.5" />
                            )}
                            <span>Решить</span>
                          </button>
                        </td>
                      </motion.tr>
                    );
                  })}
                </AnimatePresence>
              )}
              {!isLoading && !isError && filteredAlerts.length === 0 && (
                <tr>
                  <td colSpan={5} className="px-6 py-16 text-center text-graphite/40">
                    <p className="font-medium text-base mb-1">Все чисто!</p>
                    <p className="text-xs">Нет активных инцидентов, соответствующих выбранным критериям поиска.</p>
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}

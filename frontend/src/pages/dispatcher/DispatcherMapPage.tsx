import React, { useState } from 'react';
import { MapContainer, TileLayer, Marker, Popup } from 'react-leaflet';
import 'leaflet/dist/leaflet.css';
import L from 'leaflet';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { fetchContainers, queryKeys, sendDeviceCommand, fetchDispatchSummary, handleApiError } from '../../api';
import { useAuth } from '../../store/AuthContext';
import { useLocaleTheme } from '../../store/LocaleThemeContext';
import { Container } from '../../api/types';
import { MapPin, Battery, Activity, Flame, Unlock, Lock, Loader2, Radio, AlertTriangle } from 'lucide-react';
import { toast } from 'sonner';
import { createRequestId } from '../../lib/utils';

export default function DispatcherMapPage() {
  const kokshetauCenter = [53.2846, 69.3833] as [number, number];
  const { user } = useAuth();
  const { t } = useLocaleTheme();
  const queryClient = useQueryClient();
  const [pendingCommand, setPendingCommand] = useState<string | null>(null);

  const { data: containers = [], isLoading: isContainersLoading } = useQuery({
    queryKey: queryKeys.containers(false),
    queryFn: () => fetchContainers(false),
  });

  const { data: summary } = useQuery({
    queryKey: queryKeys.dispatcher.summary,
    queryFn: fetchDispatchSummary,
  });

  const commandMutation = useMutation({
    mutationFn: (args: { deviceId: string, action: 'OPEN_LID' | 'CLOSE_LID' }) => 
      sendDeviceCommand(args.deviceId, user?.id || 0, args.action, createRequestId()),
    onSuccess: (data) => {
      toast.success(`Команда ${data.action} отправлена (ID: ${data.id})`);
      queryClient.invalidateQueries({ queryKey: queryKeys.containers(false) });
    },
    onError: (e) => {
      const normErr = handleApiError(e);
      toast.error(`Ошибка: ${normErr.message}`);
    }
  });

  // Determine container statuses/alerts
  const getContainerAlert = (deviceId: string) => {
    if (!summary?.tasks) return null;
    return summary.tasks.find(t => t.device_id === deviceId && t.status !== 'RESOLVED');
  };

  const getAlertStatus = (type: string) => {
    const t = type.toUpperCase();
    if (t.includes('FIRE_RISK') || t.includes('BIO_SCAN_SABOTAGE')) {
      return 'critical';
    }
    return 'warning';
  };

  const getMarkerIcon = (container: Container) => {
    const activeAlert = getContainerAlert(container.device_id);
    let color = '#39A96B'; // green
    let pulseClass = '';

    if (!container.is_active) {
      color = '#718096'; // gray
    } else if (activeAlert) {
      const severity = getAlertStatus(activeAlert.type);
      if (severity === 'critical') {
        color = '#D64545'; // red
        pulseClass = 'animate-ping duration-1000';
      } else {
        color = '#F59E42'; // orange
      }
    } else if (container.fill_percent >= 80) {
      color = '#D64545'; // red fill alert
    } else if (container.fill_percent >= 50) {
      color = '#F59E42'; // orange fill alert
    }

    const htmlStr = `
      <div class="relative flex items-center justify-center">
        ${pulseClass ? `<span class="absolute inline-flex h-8 w-8 rounded-full bg-red-400 opacity-75 ${pulseClass}"></span>` : ''}
        <div style="background-color: ${color}; width: 28px; height: 28px; border-radius: 50%; border: 3px solid #fff; box-shadow: 0 4px 10px rgba(0,0,0,0.4); display: flex; align-items: center; justify-content: center;" class="relative z-10">
          ${activeAlert?.type === 'FIRE_RISK' ? '🔥' : activeAlert?.type === 'BIO_SCAN_SABOTAGE' ? '⚠️' : ''}
        </div>
      </div>
    `;

    return L.divIcon({
      className: 'custom-dispatcher-icon',
      html: htmlStr,
      iconSize: [32, 32],
      iconAnchor: [16, 16],
    });
  };

  const handleCommand = async (deviceId: string, action: 'OPEN_LID' | 'CLOSE_LID') => {
    if (action === 'OPEN_LID' && getContainerAlert(deviceId)?.type === 'FIRE_RISK') {
      toast.error('Открытие заблокировано из-за активного пожарного риска.');
      return;
    }
    const key = `${deviceId}:${action}`;
    setPendingCommand(key);
    try {
      await commandMutation.mutateAsync({ deviceId, action });
    } catch {
      // The mutation onError handler presents the normalized error.
    } finally {
      setPendingCommand(null);
    }
  };

  return (
    <div className="h-[calc(100vh-8rem)] w-full relative rounded-3xl overflow-hidden border border-border shadow-lg flex flex-col lg:flex-row">
      {/* Sidebar for Map overview */}
      <div className="w-full lg:w-80 bg-card border-b lg:border-b-0 lg:border-r border-border p-4 overflow-y-auto space-y-4 flex flex-col h-1/3 lg:h-full z-10">
        <div>
          <h2 className="font-bold text-lg text-white flex items-center gap-2">
            <Radio className="w-5 h-5 text-primary-light" />
            <span>Контроль Баков</span>
          </h2>
          <p className="text-xs text-foreground/50">Интерактивный IoT Мониторинг</p>
        </div>

        <div className="space-y-2 flex-1 overflow-y-auto pr-1">
          {containers.map((container) => {
            const alert = getContainerAlert(container.device_id);
            return (
              <div 
                key={container.id} 
                className={`p-3 rounded-2xl bg-white/5 border border-white/10 hover:border-white/20 transition-all text-xs space-y-2 relative ${
                  alert && getAlertStatus(alert.type) === 'critical' ? 'border-red-500/40 bg-red-500/5' : ''
                }`}
              >
                <div className="flex justify-between items-center">
                  <span className="font-mono font-bold text-white text-sm">{container.device_id}</span>
                  <span className={`px-2 py-0.5 rounded text-[10px] font-bold ${
                    container.is_active ? 'bg-primary/20 text-primary-light' : 'bg-white/10 text-white/50'
                  }`}>
                    {container.is_active ? 'Активен' : 'Отключён'}
                  </span>
                </div>
                <p className="text-foreground/70 truncate">{container.address}</p>

                <div className="flex items-center justify-between">
                  <span>Заполненность</span>
                  <span className="font-bold text-white">{container.fill_percent}%</span>
                </div>

                <div className="w-full bg-white/10 rounded-full h-1">
                  <div 
                    className="h-1 rounded-full transition-all" 
                    style={{ 
                      width: `${container.fill_percent}%`,
                      backgroundColor: container.fill_percent >= 80 ? '#D64545' : container.fill_percent >= 50 ? '#F59E42' : '#39A96B'
                    }}
                  />
                </div>

                {alert && (
                  <div className={`p-2 rounded-xl flex items-center gap-1.5 font-bold ${
                    getAlertStatus(alert.type) === 'critical' ? 'bg-critical/20 text-red-400 animate-pulse' : 'bg-warning/20 text-orange-400'
                  }`}>
                    {getAlertStatus(alert.type) === 'critical' ? (
                      <Flame className="w-3.5 h-3.5 shrink-0 text-red-400 animate-pulse" />
                    ) : (
                      <AlertTriangle className="w-3.5 h-3.5 shrink-0 text-orange-400" />
                    )}
                    <span className="truncate">{alert.message}</span>
                  </div>
                )}
              </div>
            );
          })}
        </div>
      </div>

      {/* Main Map */}
      <div className="flex-1 h-2/3 lg:h-full relative z-0">
        <MapContainer 
          center={kokshetauCenter} 
          zoom={14} 
          className="w-full h-full"
          zoomControl={true}
        >
          <TileLayer
            attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'
            url="https://{s}.basemaps.cartocdn.com/rastertiles/dark_all/{z}/{x}/{y}{r}.png"
          />

          {containers.map((container) => {
            const alert = getContainerAlert(container.device_id);
            return (
              <Marker 
                key={container.id} 
                position={[container.latitude, container.longitude]}
                icon={getMarkerIcon(container)}
              >
                <Popup className="dispatcher-popup">
                  <div className="p-3 min-w-[240px] text-graphite space-y-3">
                    <div className="flex justify-between items-start">
                      <div>
                        <h3 className="font-extrabold text-sm font-mono text-graphite">{container.device_id}</h3>
                        <p className="text-[10px] text-graphite/60 mt-0.5">{container.address}</p>
                      </div>
                      <span className={`px-2 py-0.5 rounded text-[9px] font-bold ${
                        container.is_active ? 'bg-emerald-100 text-emerald-800' : 'bg-gray-100 text-gray-800'
                      }`}>
                        {container.is_active ? 'Онлайн' : 'Офлайн'}
                      </span>
                    </div>

                    <div className="space-y-1">
                      <div className="flex justify-between text-xs">
                        <span className="text-graphite/60">Заполненность</span>
                        <span className="font-bold text-graphite">{container.fill_percent}%</span>
                      </div>
                      <div className="w-full bg-gray-200 rounded-full h-1.5">
                        <div 
                          className="h-1.5 rounded-full" 
                          style={{ 
                            width: `${container.fill_percent}%`,
                            backgroundColor: container.fill_percent >= 80 ? '#D64545' : container.fill_percent >= 50 ? '#F59E42' : '#39A96B'
                          }}
                        />
                      </div>
                    </div>

                    {alert && (
                      <div className={`border p-2 rounded-xl text-xs font-bold flex items-center gap-1.5 ${
                        getAlertStatus(alert.type) === 'critical' ? 'bg-red-50 border-red-200 text-red-700' : 'bg-orange-50 border-orange-200 text-orange-700'
                      }`}>
                        {getAlertStatus(alert.type) === 'critical' ? (
                          <Flame className="w-4 h-4 shrink-0 text-red-500 animate-pulse" />
                        ) : (
                          <AlertTriangle className="w-4 h-4 shrink-0 text-orange-500" />
                        )}
                        <span>{alert.message}</span>
                      </div>
                    )}

                    <div className="pt-2 border-t border-gray-100 grid grid-cols-2 gap-2">
                      <button 
                        onClick={() => handleCommand(container.device_id, 'OPEN_LID')}
                        disabled={pendingCommand === `${container.device_id}:OPEN_LID` || alert?.type === 'FIRE_RISK'}
                        className="bg-emerald-100 hover:bg-emerald-200 text-emerald-800 font-bold text-[11px] py-1.5 px-2 rounded-xl flex items-center justify-center gap-1 transition-colors disabled:opacity-50 cursor-pointer"
                      >
                        {pendingCommand === `${container.device_id}:OPEN_LID` ? <Loader2 className="w-3 h-3 animate-spin" /> : <Unlock className="w-3 h-3" />}
                        <span>Открыть</span>
                      </button>
                      <button 
                        onClick={() => handleCommand(container.device_id, 'CLOSE_LID')}
                        disabled={pendingCommand === `${container.device_id}:CLOSE_LID`}
                        className="bg-red-100 hover:bg-red-200 text-red-800 font-bold text-[11px] py-1.5 px-2 rounded-xl flex items-center justify-center gap-1 transition-colors disabled:opacity-50 cursor-pointer"
                      >
                        {pendingCommand === `${container.device_id}:CLOSE_LID` ? <Loader2 className="w-3 h-3 animate-spin" /> : <Lock className="w-3 h-3" />}
                        <span>Закрыть</span>
                      </button>
                    </div>
                  </div>
                </Popup>
              </Marker>
            );
          })}
        </MapContainer>
      </div>
    </div>
  );
}

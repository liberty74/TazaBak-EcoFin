import { type ReactNode, useMemo, useState } from 'react';
import { AlertTriangle, Camera, Flame, Loader2, Lock, MapPin, RadioReceiver, ScanLine, Search, ShieldCheck, Thermometer, Unlock, X } from 'lucide-react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { analyzeCameraNow, fetchContainers, fetchDeviceStatuses, fetchLatestCameraAnalysis, getApiBaseUrl, queryKeys, resolveMediaUrl, sendDeviceCommand, updateCameraStream } from '../../api';
import type { CameraAnalysis, Container, DeviceTelemetryStatus } from '../../api/types';
import { useAuth } from '../../store/AuthContext';
import { handleApiError } from '../../api/errors';
import { toast } from 'sonner';
import { createRequestId } from '../../lib/utils';

const lidIsClosed = (status: string) => status.startsWith('CLOSE') || status === 'CLOSED';
const temperatureStyle = (temperature: number | null | undefined) => {
  if (temperature == null) return 'text-foreground/45';
  if (temperature > 50) return 'text-critical animate-pulse';
  return 'text-primary';
};

export default function DevicesPage() {
  const { user } = useAuth();
  const queryClient = useQueryClient();
  const [search, setSearch] = useState('');
  const [selectedDevice, setSelectedDevice] = useState<Container | null>(null);
  const [cameraInput, setCameraInput] = useState('');
  const [cameraBroken, setCameraBroken] = useState(false);

  const containersQuery = useQuery({ queryKey: queryKeys.containers(false), queryFn: () => fetchContainers(false), refetchInterval: 10_000 });
  const statusesQuery = useQuery({ queryKey: queryKeys.dispatcher.deviceStatuses, queryFn: fetchDeviceStatuses, refetchInterval: 5_000 });
  const statusByDevice = useMemo(() => new Map((statusesQuery.data ?? []).map((status) => [status.device_id, status])), [statusesQuery.data]);
  const activeStatus = selectedDevice ? statusByDevice.get(selectedDevice.device_id) : undefined;
  const analysisQuery = useQuery({
    queryKey: queryKeys.dispatcher.cameraAnalysis(selectedDevice?.device_id),
    queryFn: () => fetchLatestCameraAnalysis(selectedDevice!.device_id),
    enabled: Boolean(selectedDevice && activeStatus?.camera_stream_url),
    refetchInterval: 5_000,
    retry: false,
  });

  const commandMutation = useMutation({
    mutationFn: ({ deviceId, action }: { deviceId: string; action: 'OPEN_LID' | 'CLOSE_LID' }) =>
      sendDeviceCommand(deviceId, user?.id ?? 'dispatcher-1', action, createRequestId()),
    onSuccess: (command) => {
      toast.success(`Команда ${command.action === 'OPEN_LID' ? 'открытия' : 'закрытия'} отправлена: ${command.status}`);
      queryClient.invalidateQueries({ queryKey: queryKeys.dispatcher.deviceStatuses });
      queryClient.invalidateQueries({ queryKey: queryKeys.dispatcher.commands() });
    },
    onError: (error: unknown) => toast.error(handleApiError(error).message),
  });

  const cameraMutation = useMutation({
    mutationFn: ({ deviceId, url }: { deviceId: string; url: string }) => updateCameraStream(deviceId, url),
    onSuccess: () => {
      toast.success('Адрес ESP32-CAM сохранён');
      setCameraBroken(false);
      queryClient.invalidateQueries({ queryKey: queryKeys.dispatcher.deviceStatuses });
    },
    onError: (error: unknown) => toast.error(handleApiError(error).message),
  });

  const analyzeMutation = useMutation({
    mutationFn: (deviceId: string) => analyzeCameraNow(deviceId),
    onSuccess: (analysis) => {
      queryClient.setQueryData(queryKeys.dispatcher.cameraAnalysis(analysis.device_id), analysis);
      queryClient.invalidateQueries({ queryKey: queryKeys.dispatcher.summary });
      if (analysis.detected) {
        toast.warning('YOLOv8 обнаружил возможный навал мусора — создан алерт');
      } else {
        toast.success('YOLOv8: территория возле бака чистая');
      }
    },
    onError: (error: unknown) => toast.error(handleApiError(error).message),
  });

  const devices = (containersQuery.data ?? []).filter((device) => `${device.device_id} ${device.name} ${device.address}`.toLowerCase().includes(search.toLowerCase()));

  const openDetails = (device: Container) => {
    setSelectedDevice(device);
    setCameraInput('');
    setCameraBroken(false);
  };

  return (
    <div className="mx-auto max-w-7xl space-y-6 pb-24 text-foreground lg:pb-8">
      <div>
        <h1 className="flex items-center gap-2 text-2xl font-bold"><RadioReceiver className="h-6 w-6 text-primary" />IoT управление</h1>
        <p className="mt-1 text-sm text-foreground/55">Телеметрия ESP32, температура DS18B20, заслонка SG90 и камера ESP32-CAM.</p>
      </div>

      <div className="relative max-w-xl">
        <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-foreground/40" />
        <input value={search} onChange={(event) => setSearch(event.target.value)} placeholder="Поиск по ID, названию или адресу" className="w-full rounded-xl border border-border bg-card py-2.5 pl-9 pr-4 text-sm outline-none focus:ring-2 focus:ring-primary/30" />
      </div>

      <div className="grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-3">
        {containersQuery.isLoading ? Array.from({ length: 6 }).map((_, index) => <div key={index} className="h-64 animate-pulse rounded-3xl border border-border bg-card" />) : devices.map((device) => {
          const status = statusByDevice.get(device.device_id);
          const isClosed = lidIsClosed(status?.lid_status ?? 'OPEN');
          const temperature = status?.temperature_in_c;
          const commandPending = commandMutation.isPending && commandMutation.variables?.deviceId === device.device_id;
          return (
            <article key={device.id} className="rounded-3xl border border-border bg-card p-5 shadow-sm">
              <div className="flex items-start justify-between gap-3">
                <div>
                  <p className="font-mono text-sm font-bold">{device.device_id}</p>
                  <h2 className="mt-1 font-bold">{device.name}</h2>
                </div>
                <span className={`rounded-full px-2.5 py-1 text-xs font-bold ${device.is_active ? 'bg-primary/10 text-primary' : 'bg-muted text-foreground/50'}`}>{device.is_active ? 'Активен' : 'Отключён'}</span>
              </div>
              <p className="mt-3 flex gap-2 text-xs text-foreground/60"><MapPin className="h-4 w-4 shrink-0" />{device.address}</p>

              <div className="mt-5 grid grid-cols-2 gap-3">
                <Metric icon={<Thermometer className="h-4 w-4" />} label="DS18B20" value={temperature == null ? 'Нет данных' : `${temperature.toFixed(1)} °C`} valueClass={temperatureStyle(temperature)} />
                <Metric icon={isClosed ? <Lock className="h-4 w-4" /> : <Unlock className="h-4 w-4" />} label="Заслонка" value={isClosed ? 'Заблокирована' : 'Доступна'} valueClass={isClosed ? 'text-critical' : 'text-primary'} />
              </div>
              {temperature != null && temperature > 50 && <p className="mt-3 flex items-center gap-1.5 rounded-xl bg-critical/10 p-2 text-xs font-bold text-critical"><Flame className="h-4 w-4 animate-pulse" />Пожарный порог &gt; 50°C: заслонка закрывается автоматически</p>}

              <div className="mt-5">
                <div className="mb-1 flex justify-between text-xs text-foreground/60"><span>Заполненность</span><b>{device.fill_percent.toFixed(0)}%</b></div>
                <div className="h-2 overflow-hidden rounded-full bg-muted"><div className="h-full rounded-full bg-primary transition-all" style={{ width: `${device.fill_percent}%` }} /></div>
              </div>
              <div className="mt-5 grid grid-cols-3 gap-2">
                <button onClick={() => commandMutation.mutate({ deviceId: device.device_id, action: 'OPEN_LID' })} disabled={commandPending} className="flex items-center justify-center gap-1 rounded-xl bg-primary/10 py-2 text-xs font-bold text-primary disabled:opacity-50"><Unlock className="h-4 w-4" />Открыть</button>
                <button onClick={() => commandMutation.mutate({ deviceId: device.device_id, action: 'CLOSE_LID' })} disabled={commandPending} className="flex items-center justify-center gap-1 rounded-xl bg-critical/10 py-2 text-xs font-bold text-critical disabled:opacity-50">{commandPending ? <Loader2 className="h-4 w-4 animate-spin" /> : <Lock className="h-4 w-4" />}Закрыть</button>
                <button onClick={() => openDetails(device)} className="flex items-center justify-center gap-1 rounded-xl bg-muted py-2 text-xs font-bold text-foreground"><Camera className="h-4 w-4" />Камера</button>
              </div>
            </article>
          );
        })}
      </div>

      {selectedDevice && <DeviceDetails
        device={selectedDevice}
        status={activeStatus}
        cameraInput={cameraInput}
        cameraBroken={cameraBroken}
        cameraSaving={cameraMutation.isPending}
        analysis={analysisQuery.data}
        analyzing={analyzeMutation.isPending}
        onCameraInput={setCameraInput}
        onSaveCamera={() => cameraMutation.mutate({ deviceId: selectedDevice.device_id, url: cameraInput })}
        onAnalyze={() => analyzeMutation.mutate(selectedDevice.device_id)}
        onImageError={() => setCameraBroken(true)}
        onClose={() => setSelectedDevice(null)}
      />}
    </div>
  );
}

function Metric({ icon, label, value, valueClass }: { icon: ReactNode; label: string; value: string; valueClass: string }) {
  return <div className="rounded-2xl bg-muted/60 p-3"><div className="flex items-center gap-1 text-xs text-foreground/55">{icon}{label}</div><p className={`mt-1 text-sm font-bold ${valueClass}`}>{value}</p></div>;
}

function DeviceDetails({ device, status, cameraInput, cameraBroken, cameraSaving, analysis, analyzing, onCameraInput, onSaveCamera, onAnalyze, onImageError, onClose }: {
  device: Container; status?: DeviceTelemetryStatus; cameraInput: string; cameraBroken: boolean; cameraSaving: boolean; analysis?: CameraAnalysis; analyzing: boolean; onCameraInput: (value: string) => void; onSaveCamera: () => void; onAnalyze: () => void; onImageError: () => void; onClose: () => void;
}) {
  const streamUrl = status?.camera_stream_url ? `${getApiBaseUrl()}${status.camera_stream_url}` : null;
  const analysisImageUrl = analysis ? `${resolveMediaUrl(analysis.image_url)}?frame=${analysis.frame_id}` : null;
  return <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4"><section className="max-h-[90vh] w-full max-w-3xl overflow-y-auto rounded-3xl bg-card p-6 shadow-2xl"><div className="flex items-start justify-between gap-4"><div><p className="font-mono text-sm text-foreground/50">{device.device_id}</p><h2 className="text-xl font-bold">Камера ИИ и датчики</h2></div><button onClick={onClose} className="rounded-full p-2 hover:bg-muted" aria-label="Закрыть"><X className="h-5 w-5" /></button></div>
    <div className="mt-5 overflow-hidden rounded-2xl bg-black"><div className="relative aspect-video"><span className="absolute left-3 top-3 z-10 rounded-full bg-black/70 px-2 py-1 text-xs font-bold text-white">LIVE · ESP32-CAM</span>{streamUrl && !cameraBroken ? <img src={streamUrl} onError={onImageError} className="h-full w-full object-contain" alt={`Live stream ${device.device_id}`} /> : <div className="flex h-full flex-col items-center justify-center gap-2 p-6 text-center text-white/70"><Camera className="h-10 w-10" /><p className="font-bold">{cameraBroken ? 'Поток недоступен' : 'Подключите ESP32-CAM'}</p><p className="text-xs">Укажите MJPEG URL, например http://192.168.1.50:81/stream</p></div>}</div></div>
    <p className="mt-2 text-xs text-foreground/50">FastAPI автоматически получает снимок камеры каждые 5 секунд, запускает YOLOv8 и сохраняет доказательство с рамками.</p>
    <div className={`mt-5 rounded-2xl border p-4 ${analysis?.detected ? 'border-critical/30 bg-critical/5' : 'border-primary/20 bg-primary/5'}`}>
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="flex items-center gap-2">
          {analysis?.detected ? <AlertTriangle className="h-5 w-5 text-critical" /> : <ShieldCheck className="h-5 w-5 text-primary" />}
          <div><p className="text-sm font-bold">Последний кадр YOLOv8</p><p className="text-xs text-foreground/55">{analysis ? `${analysis.detected ? 'Обнаружен возможный навал' : 'Территория чистая'} · ${new Date(analysis.created_at).toLocaleTimeString('ru-RU')}` : 'Ожидание первого анализа'}</p></div>
        </div>
        <button onClick={onAnalyze} disabled={!streamUrl || analyzing} className="flex items-center gap-2 rounded-xl bg-primary px-3 py-2 text-xs font-bold text-white disabled:opacity-50">{analyzing ? <Loader2 className="h-4 w-4 animate-spin" /> : <ScanLine className="h-4 w-4" />}Анализировать сейчас</button>
      </div>
      {analysisImageUrl && <img src={analysisImageUrl} className="mt-3 aspect-video w-full rounded-xl bg-black object-contain" alt="Кадр с рамками YOLOv8" />}
      {analysis && analysis.detected_objects.length > 0 && <div className="mt-3 flex flex-wrap gap-2">{analysis.detected_objects.map((item, index) => <span key={`${item.label}-${index}`} className="rounded-full bg-background px-2.5 py-1 text-xs font-semibold">{item.label} {(item.confidence * 100).toFixed(0)}%</span>)}</div>}
      {analysis?.alert_id && <p className="mt-3 text-xs font-bold text-critical">Создан или обновлён алерт ILLEGAL_DUMP #{analysis.alert_id}</p>}
    </div>
    <div className="mt-5 grid gap-3 sm:grid-cols-3"><Metric icon={<Thermometer className="h-4 w-4" />} label="DS18B20 внутри" value={status?.temperature_in_c == null ? 'Нет данных' : `${status.temperature_in_c.toFixed(1)} °C`} valueClass={temperatureStyle(status?.temperature_in_c)} /><Metric icon={<Flame className="h-4 w-4" />} label="Порог пожара" value="> 50 °C" valueClass="text-critical" /><Metric icon={lidIsClosed(status?.lid_status ?? 'OPEN') ? <Lock className="h-4 w-4" /> : <Unlock className="h-4 w-4" />} label="Замок SG90" value={status?.lid_status ?? 'Нет данных'} valueClass={lidIsClosed(status?.lid_status ?? 'OPEN') ? 'text-critical' : 'text-primary'} /></div>
    <div className="mt-5 rounded-2xl border border-border p-4"><label className="text-sm font-bold">MJPEG URL камеры</label><div className="mt-2 flex flex-col gap-2 sm:flex-row"><input value={cameraInput} onChange={(event) => onCameraInput(event.target.value)} placeholder="http://192.168.1.50:81/stream" className="min-w-0 flex-1 rounded-xl border border-border bg-background px-3 py-2 text-sm outline-none focus:ring-2 focus:ring-primary/30" /><button onClick={onSaveCamera} disabled={!cameraInput.trim() || cameraSaving} className="rounded-xl bg-primary px-4 py-2 text-sm font-bold text-white disabled:opacity-50">{cameraSaving ? 'Сохраняем…' : 'Сохранить'}</button></div></div>
  </section></div>;
}

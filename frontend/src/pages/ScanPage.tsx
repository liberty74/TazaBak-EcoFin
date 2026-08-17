import React, { useState, useRef, useEffect } from 'react';
import { Camera, Upload, X, CheckCircle, Loader2, AlertTriangle, RefreshCw, ArrowLeft } from 'lucide-react';
import { motion, AnimatePresence } from 'motion/react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../store/AuthContext';
import { analyzeBio, BioResponse } from '../api';
import { useQueryClient } from '@tanstack/react-query';
import { queryKeys, handleApiError } from '../api';
import { QRCodeSVG } from 'qrcode.react';
import { createRequestId } from '../lib/utils';

const RESULT_QR_CODES: Record<BioResponse['status'], string> = {
  approve: 'good123',
  reject: 'bad456',
  invalid: 'none000',
};

export default function ScanPage() {
  const [image, setImage] = useState<File | null>(null);
  const [previewUrl, setPreviewUrl] = useState<string | null>(null);
  const [isScanning, setIsScanning] = useState(false);
  const [result, setResult] = useState<BioResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [idempotencyKey, setIdempotencyKey] = useState<string>(createRequestId);
  
  const fileInputRef = useRef<HTMLInputElement>(null);
  const navigate = useNavigate();
  const { user } = useAuth();
  const queryClient = useQueryClient();

  // Automatically revoke the object URL whenever the previewUrl changes or when the component unmounts
  useEffect(() => {
    return () => {
      if (previewUrl) {
        URL.revokeObjectURL(previewUrl);
      }
    };
  }, [previewUrl]);

  const resetState = () => {
    setImage(null);
    setPreviewUrl(null);
    setResult(null);
    setError(null);
    setIdempotencyKey(createRequestId());
    if (fileInputRef.current) fileInputRef.current.value = '';
  };

  const handleImageCapture = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) {
      if (file.size > 5 * 1024 * 1024) {
        setError('Файл слишком большой. Максимальный размер 5 МБ.');
        return;
      }
      if (!['image/jpeg', 'image/png', 'image/webp'].includes(file.type)) {
        setError('Неподдерживаемый формат. Используйте JPEG, PNG или WebP.');
        return;
      }
      setImage(file);
      setPreviewUrl(URL.createObjectURL(file));
      setError(null);
    }
  };

  const processImage = async () => {
    if (!image || !user?.id) return;
    setIsScanning(true);
    setError(null);
    
    try {
      // By default use device_id "bio-central-park-001" as specified
      const response = await analyzeBio(image, user.id, "bio-central-park-001", idempotencyKey);
      setResult(response);
      
      if (response.status === 'approve') {
        queryClient.invalidateQueries({ queryKey: queryKeys.user.profile(user.id) });
        queryClient.invalidateQueries({ queryKey: queryKeys.user.dashboard(user.id) });
        queryClient.invalidateQueries({ queryKey: queryKeys.user.transactions(user.id) });
        queryClient.invalidateQueries({ queryKey: queryKeys.leaderboard });
      }
    } catch (e: unknown) {
      const normErr = handleApiError(e);
      setError(`${normErr.title}: ${normErr.message}`);
    } finally {
      setIsScanning(false);
    }
  };

  return (
    <div className="mx-auto flex min-h-full w-full max-w-2xl flex-col p-4 pb-8 pt-5 text-foreground md:p-8">
      {/* Header */}
      <div className="mb-5 flex items-center gap-3">
        <button aria-label="Назад" onClick={() => navigate('/home')} className="flex h-10 w-10 shrink-0 items-center justify-center rounded-full border border-border bg-card text-foreground shadow-sm transition-colors hover:text-primary">
          <ArrowLeft className="h-5 w-5" />
        </button>
        <div>
          <h1 className="mb-1 text-2xl font-bold text-foreground">Сдать хлеб</h1>
          <p className="text-sm text-muted-foreground">Сделайте фото хлеба для умного бака</p>
        </div>
      </div>

      {error && (
        <div className="mb-4 bg-critical/10 border border-critical/30 text-critical px-4 py-3 rounded-xl flex items-start gap-2">
          <AlertTriangle className="w-5 h-5 shrink-0 mt-0.5" />
          <p className="text-sm font-medium">{error}</p>
        </div>
      )}

      {/* Main Content Area */}
      <div className="flex min-h-[360px] flex-1 flex-col items-center justify-center">
        <AnimatePresence mode="wait">
          {!image && !result && (
            <motion.div
              key="upload"
              initial={{ opacity: 0, scale: 0.9 }}
              animate={{ opacity: 1, scale: 1 }}
              exit={{ opacity: 0, scale: 0.9 }}
              className="flex w-full flex-col gap-4"
            >
              <button
                onClick={() => fileInputRef.current?.click()}
                className="flex min-h-[340px] w-full cursor-pointer flex-col items-center justify-center gap-4 rounded-3xl border-2 border-dashed border-primary/40 bg-card px-5 text-primary shadow-sm transition-colors hover:bg-primary/5 md:aspect-video md:min-h-0"
              >
                <div className="flex h-16 w-16 items-center justify-center rounded-full bg-primary/10 shadow-sm ring-1 ring-primary/10">
                  <Camera className="w-8 h-8" />
                </div>
                <div className="text-center px-4">
                  <p className="text-lg font-bold">Сделать фото или выбрать из галереи</p>
                  <p className="mt-1 text-sm text-muted-foreground">На iPhone откроется выбор камеры или медиатеки</p>
                  <p className="mt-2 text-xs text-muted-foreground">JPEG, PNG или WebP · до 5 МБ</p>
                </div>
              </button>
              <input
                type="file"
                ref={fileInputRef}
                onChange={handleImageCapture}
                accept="image/jpeg,image/png,image/webp"
                className="hidden"
              />
            </motion.div>
          )}

          {previewUrl && !result && (
            <motion.div
              key="preview"
              initial={{ opacity: 0, scale: 0.9 }}
              animate={{ opacity: 1, scale: 1 }}
              exit={{ opacity: 0, scale: 0.9 }}
              className="relative w-full overflow-hidden rounded-3xl border border-border bg-card shadow-lg"
            >
              <img src={previewUrl} alt="Preview" className="w-full h-auto object-cover max-h-[60vh]" />
              
              <button
                onClick={resetState}
                disabled={isScanning}
                className="absolute top-4 right-4 w-10 h-10 bg-black/50 backdrop-blur-md text-white rounded-full flex items-center justify-center hover:bg-black/70 transition-colors z-10"
              >
                <X className="w-5 h-5" />
              </button>

              <div className="absolute bottom-0 left-0 w-full p-4 bg-gradient-to-t from-black/80 to-transparent">
                <button
                  onClick={processImage}
                  disabled={isScanning}
                  className="w-full bg-primary text-white py-4 rounded-xl font-bold flex items-center justify-center gap-2 hover:bg-primary/90 transition-colors disabled:opacity-50"
                >
                  {isScanning ? (
                    <>
                      <Loader2 className="w-6 h-6 animate-spin" />
                      Анализируем через AI...
                    </>
                  ) : (
                    <>
                      <Upload className="w-6 h-6" />
                      Отправить на проверку
                    </>
                  )}
                </button>
              </div>
            </motion.div>
          )}

          {result && (
            <motion.div
              key="result"
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              className="w-full"
            >
              {result.status === 'approve' && (
                <div className="bg-primary/10 border border-primary/20 rounded-3xl p-6 text-center">
                  <div className="w-20 h-20 mx-auto bg-primary text-white rounded-full flex items-center justify-center mb-4">
                    <CheckCircle className="w-10 h-10" />
                  </div>
                  <h2 className="text-2xl font-bold text-primary mb-2">Хлеб распознан!</h2>
                  <p className="mb-6 text-foreground/80">
                    Покажите этот QR-код сканеру на баке, чтобы открыть крышку.
                  </p>
                  
                  <div className="mb-6 flex items-center justify-between rounded-xl border border-border bg-card p-4 shadow-sm">
                    <span className="font-medium text-muted-foreground">Начислено:</span>
                    <span className="text-xl font-bold text-primary">+{result.points_awarded} 🐾</span>
                  </div>
                  
                  {result.command_sent ? (
                    <p className="text-sm font-bold text-primary mb-6 flex items-center justify-center gap-2">
                      <CheckCircle className="w-4 h-4" />
                      Команда открытия отправлена
                    </p>
                  ) : (
                    <p className="mb-6 text-sm text-muted-foreground">
                      Контейнер сейчас offline, команда сохранена для доставки.
                    </p>
                  )}

                  <div className="space-y-3">
                    <button onClick={() => navigate('/home')} className="w-full bg-primary text-white py-3 rounded-xl font-bold">
                      Вернуться на главную
                    </button>
                    <button onClick={resetState} className="flex w-full items-center justify-center gap-2 rounded-xl border border-primary/20 bg-card py-3 font-bold text-primary">
                      <RefreshCw className="w-4 h-4" />
                      Сдать ещё
                    </button>
                  </div>
                </div>
              )}

              {result.status === 'reject' && (
                <div className="bg-critical/10 border border-critical/20 rounded-3xl p-6 text-center">
                  <div className="w-20 h-20 mx-auto bg-critical text-white rounded-full flex items-center justify-center mb-4">
                    <X className="w-10 h-10" />
                  </div>
                  <h2 className="text-2xl font-bold text-critical mb-2">Отклонено</h2>
                  <p className="text-critical/80 mb-6 font-medium">
                    {result.reason === 'mold_detected' ? 'Обнаружена плесень. Плесневелый хлеб нельзя отдавать животным — это опасно для их здоровья.' : 'Несоответствие правилам приёма.'}
                  </p>
                  <button onClick={resetState} className="w-full bg-critical text-white py-3 rounded-xl font-bold flex items-center justify-center gap-2">
                    <RefreshCw className="w-4 h-4" />
                    Попробовать другое фото
                  </button>
                </div>
              )}

              {result.status === 'invalid' && (
                <div className="bg-warning/10 border border-warning/20 rounded-3xl p-6 text-center">
                  <div className="w-20 h-20 mx-auto bg-warning text-white rounded-full flex items-center justify-center mb-4">
                    <AlertTriangle className="w-10 h-10" />
                  </div>
                  <h2 className="text-2xl font-bold text-warning mb-2">Не удалось распознать</h2>
                  <p className="text-warning/80 mb-6 font-medium">
                    {result.reason === 'not_bread' ? 'На фото не найден хлеб. Убедитесь, что хлеб хорошо видно и он без пакета.' : 'Объект не найден в кадре. Сделайте фото при хорошем освещении.'}
                  </p>
                  <button onClick={resetState} className="w-full bg-warning text-white py-3 rounded-xl font-bold flex items-center justify-center gap-2">
                    <Camera className="w-4 h-4" />
                    Переснять
                  </button>
                </div>
              )}

              <div className="mt-4 rounded-3xl border border-border bg-card p-5 text-center shadow-sm">
                <p className="mb-3 text-sm font-bold text-foreground/70">QR-код результата</p>
                <div className="mx-auto inline-flex rounded-2xl bg-white p-3 ring-1 ring-black/5" style={{ backgroundColor: '#ffffff' }}>
                  <QRCodeSVG
                    value={RESULT_QR_CODES[result.status]}
                    size={200}
                    level="M"
                    marginSize={2}
                    title={`QR-код ${RESULT_QR_CODES[result.status]}`}
                  />
                </div>
                <p className="mt-3 font-mono text-lg font-bold tracking-widest text-foreground">
                  {RESULT_QR_CODES[result.status]}
                </p>
              </div>
              
              {/* Optional: Collapsible debug info */}
              {result.detected_objects && result.detected_objects.length > 0 && (
                <div className="mt-4 rounded-xl bg-muted p-4 text-left">
                  <p className="mb-2 text-xs font-bold uppercase text-muted-foreground">AI-детали:</p>
                  {result.detected_objects.map((obj, i) => (
                    <div key={i} className="flex justify-between text-xs text-foreground/80">
                      <span>{obj.label}</span>
                      <span>{(obj.confidence * 100).toFixed(1)}%</span>
                    </div>
                  ))}
                </div>
              )}
            </motion.div>
          )}
        </AnimatePresence>
      </div>
    </div>
  );
}

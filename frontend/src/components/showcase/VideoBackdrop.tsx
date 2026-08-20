import React, { useEffect, useRef } from 'react';

/**
 * Полноэкранное видео за содержимым секции.
 *
 * Референс держит атмосферу фотографией неба; у нас это ролик. Правила те
 * же: изображение не спорит с текстом, а даёт ему глубину — поверх всегда
 * лежит затемняющая вуаль, и контраст считается уже к ней.
 *
 * Звука нет и быть не может: витрина открывается сама, а видео, которое
 * заговорило без спроса, закрывают вместе со вкладкой.
 */
export default function VideoBackdrop({
  src,
  className = '',
  /** Затемнение поверх кадра. Чем выше, тем читаемее белый текст. */
  scrim = 'from-ink/75 via-ink/55 to-ink/75',
}: {
  src: string;
  className?: string;
  scrim?: string;
}) {
  const videoRef = useRef<HTMLVideoElement>(null);

  useEffect(() => {
    const video = videoRef.current;
    if (!video) return;

    // Кто просил убрать движение — получает первый кадр вместо цикла.
    if (window.matchMedia('(prefers-reduced-motion: reduce)').matches) {
      video.pause();
      return;
    }

    // Autoplay может быть отклонён политикой браузера. Это не ошибка:
    // остаётся статичный кадр, и секция продолжает читаться.
    void video.play().catch(() => undefined);
  }, []);

  return (
    <div aria-hidden className={`pointer-events-none absolute inset-0 overflow-hidden ${className}`}>
      <video
        ref={videoRef}
        className="h-full w-full object-cover"
        src={src}
        autoPlay
        muted
        loop
        playsInline
        preload="auto"
      />
      <div className={`absolute inset-0 bg-gradient-to-b ${scrim}`} />
    </div>
  );
}

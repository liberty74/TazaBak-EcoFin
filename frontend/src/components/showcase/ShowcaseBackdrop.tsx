import React, { useEffect, useRef } from 'react';

/**
 * Живой фон витрины: сеть площадок города.
 *
 * Это не абстрактные частицы, а метафора самого продукта. Каждая точка —
 * контейнерная площадка, её свечение растёт по мере наполнения. Дойдя до
 * порога, площадка вспыхивает и гаснет: приехал мусоровоз. Между соседями
 * тянутся нити маршрута, по которым изредка пробегает импульс.
 *
 * Абстрактный шум смотрелся бы одинаково на любом сайте; здесь фон
 * рассказывает то же, что и текст рядом с ним.
 */

interface Node {
  x: number;
  y: number;
  /** Заполненность 0..1 — она же яркость точки. */
  fill: number;
  /** Своя скорость наполнения: площадки не должны пульсировать в такт. */
  rate: number;
  /** Порог вывоза у каждой свой, иначе вспышки идут волной. */
  threshold: number;
  /** Затухающая вспышка после вывоза. */
  flash: number;
  radius: number;
}

interface Edge {
  /* Ссылки на сами площадки, а не индексы: с индексами каждое обращение
     требовало бы проверки на выход за границы массива. */
  from: Node;
  to: Node;
  /** Позиция бегущего импульса, -1 — импульса нет. */
  pulse: number;
  pulseDelay: number;
}

const NODE_COUNT = 46;
const LINK_DISTANCE = 0.19;
// Тёмная зелень для светлого полотна. Поверх видео вызывающая сторона
// передаёт светлый акцент — на кадре тёмный просто утонет.
const DEFAULT_ACCENT: readonly [number, number, number] = [27, 122, 78];

export default function ShowcaseBackdrop({
  className = '',
  accent = DEFAULT_ACCENT,
}: {
  className?: string;
  accent?: readonly [number, number, number];
}) {
  const canvasRef = useRef<HTMLCanvasElement>(null);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const context = canvas.getContext('2d');
    if (!context) return;

    const reduceMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;

    let width = 0;
    let height = 0;
    let nodes: Node[] = [];
    let edges: Edge[] = [];
    let frame = 0;
    let last = performance.now();

    /* Координаты держим в долях от 0 до 1, чтобы пересчёт при изменении
       размера окна не рождал новую случайную картину. */
    const seedNodes = () => {
      nodes = Array.from({ length: NODE_COUNT }, () => ({
        x: Math.random(),
        y: Math.random(),
        fill: Math.random(),
        rate: 0.012 + Math.random() * 0.03,
        threshold: 0.75 + Math.random() * 0.25,
        flash: 0,
        radius: 1.1 + Math.random() * 1.9,
      }));

      edges = [];
      nodes.forEach((from, index) => {
        nodes.slice(index + 1).forEach((to) => {
          if (Math.hypot(from.x - to.x, from.y - to.y) < LINK_DISTANCE) {
            edges.push({ from, to, pulse: -1, pulseDelay: Math.random() * 14 });
          }
        });
      });
    };

    const resize = () => {
      const parent = canvas.parentElement;
      if (!parent) return;
      const ratio = Math.min(window.devicePixelRatio || 1, 2);
      width = parent.clientWidth;
      height = parent.clientHeight;
      canvas.width = Math.max(1, Math.floor(width * ratio));
      canvas.height = Math.max(1, Math.floor(height * ratio));
      canvas.style.width = `${width}px`;
      canvas.style.height = `${height}px`;
      context.setTransform(ratio, 0, 0, ratio, 0, 0);
    };

    const draw = (delta: number) => {
      context.clearRect(0, 0, width, height);
      const [r, g, b] = accent;

      // Нити маршрута идут первыми: точки должны лежать поверх них.
      for (const edge of edges) {
        const x1 = edge.from.x * width;
        const y1 = edge.from.y * height;
        const x2 = edge.to.x * width;
        const y2 = edge.to.y * height;

        context.strokeStyle = `rgba(${r}, ${g}, ${b}, 0.08)`;
        context.lineWidth = 1;
        context.beginPath();
        context.moveTo(x1, y1);
        context.lineTo(x2, y2);
        context.stroke();

        if (!reduceMotion) {
          if (edge.pulse < 0) {
            edge.pulseDelay -= delta;
            if (edge.pulseDelay <= 0) {
              edge.pulse = 0;
              edge.pulseDelay = 8 + Math.random() * 22;
            }
          } else {
            edge.pulse += delta * 0.6;
            if (edge.pulse > 1) {
              edge.pulse = -1;
            } else {
              const px = x1 + (x2 - x1) * edge.pulse;
              const py = y1 + (y2 - y1) * edge.pulse;
              // Импульс ярче в середине пути и гаснет к концам.
              const strength = Math.sin(edge.pulse * Math.PI);
              context.fillStyle = `rgba(${r}, ${g}, ${b}, ${0.55 * strength})`;
              context.beginPath();
              context.arc(px, py, 1.6, 0, Math.PI * 2);
              context.fill();
            }
          }
        }
      }

      for (const node of nodes) {
        if (!reduceMotion) {
          node.fill += node.rate * delta;
          if (node.fill >= node.threshold) {
            node.fill = 0;
            node.flash = 1;
          }
          if (node.flash > 0) node.flash = Math.max(0, node.flash - delta * 1.5);
        }

        const x = node.x * width;
        const y = node.y * height;
        const level = node.fill / node.threshold;

        // Ореол растёт вместе с заполненностью — площадка «набухает».
        const halo = node.radius * (3 + level * 5 + node.flash * 9);
        const gradient = context.createRadialGradient(x, y, 0, x, y, halo);
        gradient.addColorStop(0, `rgba(${r}, ${g}, ${b}, ${0.13 * level + node.flash * 0.3})`);
        gradient.addColorStop(1, `rgba(${r}, ${g}, ${b}, 0)`);
        context.fillStyle = gradient;
        context.beginPath();
        context.arc(x, y, halo, 0, Math.PI * 2);
        context.fill();

        context.fillStyle = `rgba(${r}, ${g}, ${b}, ${0.3 + level * 0.45 + node.flash * 0.25})`;
        context.beginPath();
        context.arc(x, y, node.radius, 0, Math.PI * 2);
        context.fill();
      }
    };

    const tick = (now: number) => {
      // Секунды, а не кадры: картина идёт одинаково на 60 и 144 Гц.
      const delta = Math.min((now - last) / 1000, 0.05);
      last = now;
      draw(delta);
      frame = requestAnimationFrame(tick);
    };

    const observer =
      typeof ResizeObserver !== 'undefined' ? new ResizeObserver(resize) : null;
    if (observer && canvas.parentElement) observer.observe(canvas.parentElement);
    window.addEventListener('resize', resize);

    seedNodes();
    resize();

    if (reduceMotion) {
      // Один кадр вместо анимации: фон остаётся, движения нет.
      draw(0);
    } else {
      frame = requestAnimationFrame(tick);
    }

    // Во вкладке в фоне рисовать незачем — это чистый расход батареи.
    const onVisibility = () => {
      if (reduceMotion) return;
      if (document.hidden) {
        cancelAnimationFrame(frame);
      } else {
        last = performance.now();
        frame = requestAnimationFrame(tick);
      }
    };
    document.addEventListener('visibilitychange', onVisibility);

    return () => {
      cancelAnimationFrame(frame);
      window.removeEventListener('resize', resize);
      document.removeEventListener('visibilitychange', onVisibility);
      observer?.disconnect();
    };
  }, [accent]);

  return (
    <canvas
      ref={canvasRef}
      aria-hidden
      className={`pointer-events-none absolute inset-0 h-full w-full ${className}`}
    />
  );
}

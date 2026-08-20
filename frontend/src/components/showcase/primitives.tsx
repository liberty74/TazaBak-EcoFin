import React, { useEffect, useRef, useState } from 'react';

/**
 * Показ секции при первом появлении в кадре.
 *
 * IntersectionObserver здесь не годится: переход по якорю или по ссылке
 * может перепрыгнуть промежуточные секции, они ни разу не пересекут кадр и
 * останутся скрытыми навсегда. Поэтому условие шире — секция считается
 * показанной, как только её верх поднялся выше нижней границы окна, что
 * верно и для «пролетели мимо».
 */
export function useRevealOnScroll<T extends HTMLElement>() {
  const ref = useRef<T>(null);
  const [shown, setShown] = useState(false);

  useEffect(() => {
    if (shown) return;
    let frame = 0;

    const check = () => {
      frame = 0;
      const node = ref.current;
      if (!node) return;
      if (node.getBoundingClientRect().top < window.innerHeight * 0.9) setShown(true);
    };

    const schedule = () => {
      if (frame) return;
      frame = requestAnimationFrame(check);
    };

    check();
    window.addEventListener('scroll', schedule, { passive: true });
    window.addEventListener('resize', schedule);
    return () => {
      if (frame) cancelAnimationFrame(frame);
      window.removeEventListener('scroll', schedule);
      window.removeEventListener('resize', schedule);
    };
  }, [shown]);

  return { ref, shown };
}

export function Section({
  children,
  className = '',
  id,
}: {
  children: React.ReactNode;
  className?: string;
  id?: string;
}) {
  const { ref, shown } = useRevealOnScroll<HTMLElement>();
  return (
    <section id={id} ref={ref} className={`${shown ? 'showcase-rise' : 'opacity-0'} ${className}`}>
      {children}
    </section>
  );
}

/**
 * Микрозаголовок над секцией.
 *
 * Классы перечислены целиком, а не собраны шаблоном: Tailwind находит их
 * статическим сканированием исходников, и `text-${tone}` в сборку не попал бы.
 */
const EYEBROW_TONE = {
  /** Подпись бренда. */
  verdant: 'text-verdant',
  /** Данные и модели — свой акцент, чтобы не сливаться с брендом. */
  signal: 'text-signal',
  faint: 'text-faint',
} as const;

export function Eyebrow({
  children,
  tone = 'verdant',
}: {
  children: React.ReactNode;
  tone?: keyof typeof EYEBROW_TONE;
}) {
  return <p className={`mono-label ${EYEBROW_TONE[tone]}`}>{children}</p>;
}

/** Шапка раздела: один и тот же ритм на всех страницах витрины. */
export function PageHeader({
  eyebrow,
  title,
  lead,
  tone,
}: {
  eyebrow: string;
  title: React.ReactNode;
  lead?: React.ReactNode;
  tone?: keyof typeof EYEBROW_TONE;
}) {
  return (
    <header className="border-b border-ink/8">
      <div className="mx-auto max-w-6xl px-5 pb-16 pt-20 md:pt-28">
        <Eyebrow tone={tone}>{eyebrow}</Eyebrow>
        <h1 className="display-type mt-7 max-w-3xl text-[clamp(2.25rem,5.5vw,4rem)] text-ink">
          {title}
        </h1>
        {lead && (
          <p className="mt-8 max-w-2xl text-base leading-relaxed text-body md:text-lg">{lead}</p>
        )}
      </div>
    </header>
  );
}

/** Числовая плитка. Единицу измерения держим рядом со значением. */
export function StatCell({
  value,
  unit,
  caption,
}: {
  value: string;
  unit: string;
  caption: string;
}) {
  return (
    <div className="bg-canvas p-7">
      <p className="display-type text-4xl text-ink md:text-5xl">
        {value}
        <span className="ml-2 font-sans text-base font-normal text-verdant">{unit}</span>
      </p>
      <p className="mt-4 text-sm leading-relaxed text-body">{caption}</p>
    </div>
  );
}

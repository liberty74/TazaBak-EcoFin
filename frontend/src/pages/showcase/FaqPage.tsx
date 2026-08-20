import React, { useState } from 'react';
import { Minus, Plus } from 'lucide-react';
import { PageHeader, Section } from '../../components/showcase/primitives';
import { FAQ, type FaqEntry } from '../../components/showcase/content';
import { useShowcaseAuth } from '../../components/showcase/ShowcaseLayout';

function FaqItem({ item, index }: { item: FaqEntry; index: number }) {
  const [open, setOpen] = useState(false);
  return (
    <div className="border-b border-ink/10">
      <button
        type="button"
        onClick={() => setOpen((value) => !value)}
        aria-expanded={open}
        className="flex w-full items-start gap-5 py-6 text-left"
      >
        <span className="mono-data mt-1 shrink-0 text-xs text-faint">
          {String(index + 1).padStart(2, '0')}.
        </span>
        <span className="flex-1 text-base font-medium text-ink md:text-lg">{item.q}</span>
        <span className="mt-0.5 shrink-0 text-body">
          {open ? <Minus className="h-4 w-4" /> : <Plus className="h-4 w-4" />}
        </span>
      </button>
      {open && (
        <p className="max-w-3xl pb-6 pl-11 text-sm leading-relaxed text-body md:text-base">
          {item.a}
        </p>
      )}
    </div>
  );
}

export default function FaqPage() {
  const { openAuth } = useShowcaseAuth();

  return (
    <>
      <PageHeader
        eyebrow="Вопросы"
        tone="faint"
        title={
          <>
            Частые вопросы <span className="italic">и честные ответы</span>
          </>
        }
        lead={
          <>
            Включая неудобные. Если система чего-то не умеет или цифра держится на
            допущении, это написано здесь, а не выясняется на защите.
          </>
        }
      />

      <Section className="mx-auto max-w-4xl px-5 py-20">
        {FAQ.map((item, index) => (
          <FaqItem key={item.q} item={item} index={index} />
        ))}
      </Section>

      <Section className="border-t border-ink/8 bg-band">
        <div className="mx-auto max-w-4xl px-5 py-20 text-center">
          <h2 className="display-type text-[clamp(1.75rem,3.5vw,2.75rem)] text-ink">
            Остались вопросы — посмотрите сами.
          </h2>
          <p className="mx-auto mt-6 max-w-xl text-base leading-relaxed text-body">
            Демо-роли открывают те же экраны, что видит коммунальная служба: экономию с
            раскрытой формулой, прогноз по каждой площадке и кабинет пекарни.
          </p>
          <button
            type="button"
            onClick={() => openAuth('login')}
            className="mt-10 rounded-lg bg-ink px-6 py-3 text-sm font-medium text-white transition-opacity hover:opacity-90"
          >
            Войти в демо
          </button>
        </div>
      </Section>
    </>
  );
}

import React from 'react';
import { PageHeader, Section } from '../../components/showcase/primitives';
import { MODULES } from '../../components/showcase/content';

export default function ModulesPage() {
  return (
    <>
      <PageHeader
        eyebrow="Модули"
        title={<>Одна платформа для города и малого бизнеса.</>}
        lead={
          <>
            У коммунальной службы, водителя, пекарни и волонтёра разные вопросы к
            системе. Модули собраны так, чтобы у каждого был свой экран, а не общий
            дашборд, из которого каждый выуживает нужное.
          </>
        }
      />

      <Section className="mx-auto max-w-6xl px-5 py-20">
        <div className="space-y-4">
          {MODULES.map((module) => (
            <article
              key={module.key}
              className="grid gap-8 rounded-3xl border border-ink/10 bg-paper p-7 md:grid-cols-[minmax(0,20rem)_1fr] md:p-9"
            >
              {/* Цвет плитки — единственный различитель категории. Текст на
                  пастельных плитках чернильный (11–12:1), на глубокой
                  зелёной — светлый (9.4:1). */}
              <div className={`${module.surface} flex flex-col justify-between rounded-2xl p-7`}>
                <h2
                  className={`display-type text-3xl ${
                    module.invertText ? 'text-white' : 'text-ink'
                  }`}
                >
                  {module.title}
                </h2>
                <p
                  className={`mt-8 text-xs uppercase tracking-wider ${
                    module.invertText ? 'text-mint' : 'text-ink/70'
                  }`}
                >
                  {module.audience}
                </p>
              </div>

              <div className="flex flex-col justify-center">
                <p className="text-base font-medium text-ink">{module.short}</p>
                <p className="mt-5 text-sm leading-relaxed text-body md:text-base">{module.body}</p>
              </div>
            </article>
          ))}
        </div>
      </Section>

      <Section className="border-t border-ink/8 bg-band">
        <div className="mx-auto max-w-6xl px-5 py-20">
          <h2 className="display-type max-w-2xl text-[clamp(1.75rem,3.5vw,2.75rem)] text-ink">
            Модули не живут по отдельности.
          </h2>
          <p className="mt-8 max-w-2xl text-base leading-relaxed text-body">
            Прогноз питает маршрут, маршрут порождает фактические заезды, заезды дают
            экономию, экономия задаёт тариф. Сдача хлеба жителем попадает в ту же
            сводку, что и списания пекарни. Поэтому цифра на любом экране
            прослеживается до исходного замера.
          </p>

          <ol className="mt-12 grid gap-px overflow-hidden rounded-2xl border border-ink/10 bg-ink/8 md:grid-cols-4">
            {[
              ['Замер', 'Датчик отдаёт расстояние и температуру каждые несколько минут.'],
              ['Прогноз', 'Регрессия по циклу даёт срок до порога вывоза.'],
              ['Маршрут', 'В план смены попадают только те площадки, которым пора.'],
              ['Экономия', 'Несделанный заезд превращается в литры, тенге и CO₂.'],
            ].map(([title, body], index) => (
              <li key={title} className="bg-canvas p-7">
                <span className="mono-data text-xs text-verdant">
                  {String(index + 1).padStart(2, '0')}
                </span>
                <h3 className="mt-4 text-lg font-medium text-ink">{title}</h3>
                <p className="mt-3 text-sm leading-relaxed text-body">{body}</p>
              </li>
            ))}
          </ol>
        </div>
      </Section>
    </>
  );
}

import React from 'react';
import { Eyebrow, PageHeader, Section } from '../../components/showcase/primitives';
import { MODELS } from '../../components/showcase/content';
import VideoBackdrop from '../../components/showcase/VideoBackdrop';

export default function TechnologyPage() {
  return (
    <>
      <PageHeader
        eyebrow="Технология"
        tone="signal"
        title={<>Каждая модель делает то, для чего она подходит.</>}
        lead={
          <>
            Одна сеть на все задачи выглядит внушительнее на слайде и хуже работает в
            деле. Мы развели модели по областям, где у каждой есть основание стоять, и
            готовы объяснить это основание для каждой.
          </>
        }
      />

      <Section className="mx-auto max-w-6xl px-5 py-20">
        <div className="space-y-4">
          {MODELS.map((model) => (
            <article
              key={model.name}
              className="grid gap-8 rounded-2xl border border-ink/10 bg-paper p-7 md:grid-cols-[minmax(0,16rem)_1fr] md:p-9"
            >
              <div>
                <p className="mono-label text-verdant">{model.role}</p>
                <h2 className="mt-4 text-2xl font-medium text-ink">{model.name}</h2>
              </div>
              <div>
                <p className="text-base leading-relaxed text-ink">{model.body}</p>
                <p className="mt-5 text-sm leading-relaxed text-body">{model.detail}</p>
              </div>
            </article>
          ))}
        </div>
      </Section>

      {/* ---------------------------------------------------------------
          Формула CLIP — то, что просят объяснить на техзащите.
          --------------------------------------------------------------- */}
      <Section className="border-y border-ink/8 bg-band">
        <div className="mx-auto max-w-6xl px-5 py-20">
          <Eyebrow tone="signal">Как получается процент уверенности</Eyebrow>
          <h2 className="display-type mt-7 max-w-2xl text-[clamp(1.75rem,3.5vw,2.75rem)] text-ink">
            Три строки арифметики, которые можно воспроизвести на доске.
          </h2>

          <div className="mt-12 grid gap-4 lg:grid-cols-2">
            <div className="rounded-2xl border border-ink/10 bg-paper p-7">
              <p className="mono-label text-faint">Качество хлеба · CLIP</p>
              <pre className="mono-data mt-6 overflow-x-auto text-xs leading-relaxed text-body md:text-sm">
{`сходство = вектор(фото) · вектор(описание)
логиты   = сходство × масштаб модели
проценты = softmax(логиты)`}
              </pre>
              <p className="mt-6 text-sm leading-relaxed text-body">
                Фотография и три описания — «свежий хлеб», «хлеб с плесенью», «на фото
                нет хлеба» — переводятся в векторы одного пространства. Чем ближе
                векторы, тем выше доля класса. Ниже порога уверенности снимок не
                оценивается: система просит фото получше вместо того, чтобы гадать.
              </p>
            </div>

            <div className="rounded-2xl border border-ink/10 bg-paper p-7">
              <p className="mono-label text-faint">Прогноз заполнения · регрессия</p>
              <pre className="mono-data mt-6 overflow-x-auto text-xs leading-relaxed text-body md:text-sm">
{`b   = Σ(t−t̄)(y−ȳ) / Σ(t−t̄)²
a   = ȳ − b·t̄
R²  = 1 − Σ(y−(a+b·t))² / Σ(y−ȳ)²
ETA = (порог − уровень) / b`}
              </pre>
              <p className="mt-6 text-sm leading-relaxed text-body">
                Метод наименьших квадратов, написанный вручную, без внешних библиотек.
                R² показывает, насколько прямая объясняет замеры, и выводится рядом со
                сроком: по нему видно, доверять прогнозу или площадкой пользуются рывками.
              </p>
            </div>
          </div>
        </div>
      </Section>

      {/* ---------------------------------------------------------------
          Проверяемость — единственная тёмная панель на витрине.
          --------------------------------------------------------------- */}
      <Section className="mx-auto max-w-6xl px-5 py-20">
        {/* Единственная тёмная панель на всей витрине: она ломает светлый
            ритм и притягивает взгляд к главному обещанию. Второй такой на
            странице быть не должно — приём перестанет работать. */}
        <div className="rounded-3xl bg-inverted p-8 md:p-12">
          <p className="mono-label text-mint">Проверяемость</p>
          <h2 className="display-type mt-5 max-w-2xl text-[clamp(1.75rem,3vw,2.5rem)] text-white">
            Число, которое нельзя проверить, на защите не стоит ничего.
          </h2>
          <p className="mt-6 max-w-2xl text-sm leading-relaxed text-white/80 md:text-base">
            Поэтому у каждой суммы на экране есть основание вида «10 баков × 1 000 ₸»,
            неполная неделя на графике помечена отдельно, а проекция на город никогда
            не показывается как измеренный факт. Там, где данных не хватает, система
            говорит об этом вместо того, чтобы подставить правдоподобную цифру.
          </p>

          <div className="mt-10 grid gap-6 md:grid-cols-3">
            {[
              [
                'Сверка чисел',
                'Каждое число из ответа языковой модели ищется среди переданных фактов. Не нашлось — рекомендация отбрасывается целиком.',
              ],
              [
                'Отказ вместо догадки',
                'Меньше трёх замеров или уровень не растёт — срок не выдаётся. Площадка объясняет причину молчания.',
              ],
              [
                'Разделённые кошельки',
                'Спасённый хлеб не складывается с деньгами от рейсов, а разовая маржа — с регулярной выручкой.',
              ],
            ].map(([title, body]) => (
              <div key={title}>
                <h3 className="text-base font-medium text-white">{title}</h3>
                <p className="mt-3 text-sm leading-relaxed text-white/75">{body}</p>
              </div>
            ))}
          </div>
        </div>
      </Section>

      {/* ---------------------------------------------------------------
          Переход к железу: кадр вместо очередной карточки, чтобы страница
          дышала между двумя плотными блоками.
          --------------------------------------------------------------- */}
      <Section className="relative overflow-hidden bg-ink">
        <VideoBackdrop src="/media/paper.mp4" scrim="from-ink/80 via-ink/60 to-ink/85" />
        <div className="relative mx-auto max-w-4xl px-5 py-24 text-center md:py-32">
          <p className="mono-label text-white/70">От модели к железу</p>
          <p className="display-type mt-7 text-[clamp(1.75rem,4vw,2.75rem)] text-white">
            <span className="display-lead">Алгоритм</span> ничего не стоит,
            <br />
            пока его не подключили к баку.
          </p>
        </div>
      </Section>

      {/* ---------------------------------------------------------------
          Железо.
          --------------------------------------------------------------- */}
      <Section className="border-t border-ink/8 bg-band">
        <div className="mx-auto max-w-6xl px-5 py-20">
          <Eyebrow>Физический контур</Eyebrow>
          <h2 className="display-type mt-7 max-w-2xl text-[clamp(1.75rem,3.5vw,2.75rem)] text-ink">
            Прототип собран, а не нарисован.
          </h2>

          <div className="mt-12 grid gap-4 md:grid-cols-2 lg:grid-cols-4">
            {[
              ['ESP32 + HC-SR04', 'Расстояние до мусора: 25 см — пустой бак, 7 см — полный.'],
              ['DS18B20', 'Температура внутри. Выше 50 °C — критическая тревога о возгорании.'],
              ['ESP32-CAM', 'Поток кадров площадки, по которым работает распознавание навала.'],
              ['Привод SG90', 'Команда закрытия заслонки приходит по WebSocket при переполнении.'],
            ].map(([title, body]) => (
              <article key={title} className="rounded-2xl border border-ink/10 bg-paper p-7">
                <h3 className="mono-data text-sm text-verdant">{title}</h3>
                <p className="mt-4 text-sm leading-relaxed text-body">{body}</p>
              </article>
            ))}
          </div>

          <p className="mt-8 max-w-3xl text-sm leading-relaxed text-faint">
            Веса моделей запекаются в Docker-образ на этапе сборки, поэтому контейнер
            не уходит в сеть за ними при первом запросе и работает офлайн. В интернет
            система выходит только за ответом языковой модели — и только если ключ задан.
          </p>
        </div>
      </Section>
    </>
  );
}

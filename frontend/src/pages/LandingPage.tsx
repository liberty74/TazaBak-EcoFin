import React from 'react';
import { Link } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { ArrowRight, ArrowUpRight, ChevronDown } from 'lucide-react';
import { fetchRevenue, fetchSavings } from '../api/eco';
import { queryKeys } from '../api/queryKeys';
import ShowcaseBackdrop from '../components/showcase/ShowcaseBackdrop';
import VideoBackdrop from '../components/showcase/VideoBackdrop';
import { useShowcaseAuth } from '../components/showcase/ShowcaseLayout';
import { Eyebrow, Section, StatCell } from '../components/showcase/primitives';
import { MODULES } from '../components/showcase/content';

const NUMBER = new Intl.NumberFormat('ru-RU', { maximumFractionDigits: 0 });
const DECIMAL = new Intl.NumberFormat('ru-RU', { maximumFractionDigits: 1 });
const DASH = '—';

/** Карточка перехода в раздел: заголовок, обещание и стрелка. */
function SectionLink({
  to,
  eyebrow,
  title,
  body,
}: {
  to: string;
  eyebrow: string;
  title: string;
  body: string;
}) {
  return (
    <Link
      to={to}
      className="group flex flex-col justify-between rounded-2xl border border-ink/10 bg-paper p-7 transition-colors hover:border-verdant/45 hover:bg-band"
    >
      <div>
        <p className="mono-label text-verdant">{eyebrow}</p>
        <h3 className="display-type mt-4 text-2xl text-ink">{title}</h3>
        <p className="mt-4 text-sm leading-relaxed text-body">{body}</p>
      </div>
      <span className="mt-7 inline-flex items-center gap-2 text-sm text-ink">
        Открыть раздел
        <ArrowUpRight className="h-4 w-4 transition-transform group-hover:translate-x-0.5 group-hover:-translate-y-0.5" />
      </span>
    </Link>
  );
}

export default function LandingPage() {
  const { openAuth } = useShowcaseAuth();

  // Цифры на витрине — не копирайтинг, а тот же публичный отчёт, который
  // видит диспетчер. Если backend не поднят, стоят прочерки, а не
  // заготовленные красивые числа.
  const { data: savings } = useQuery({
    queryKey: queryKeys.eco.savings(30),
    queryFn: () => fetchSavings(30),
    retry: false,
  });

  const { data: revenue } = useQuery({
    queryKey: queryKeys.eco.revenue(30, 1200),
    queryFn: () => fetchRevenue(30, 1200),
    retry: false,
  });

  const stats = [
    {
      value: savings ? NUMBER.format(savings.trips.saved) : DASH,
      unit: 'рейсов',
      caption: `не понадобилось за 30 дней из ${
        savings ? NUMBER.format(savings.trips.baseline) : DASH
      } по графику`,
    },
    {
      value: savings ? NUMBER.format(savings.money.total_kzt) : DASH,
      unit: '₸',
      caption: 'топливо и время бригады по расчётной модели пилота',
    },
    {
      value: savings ? DECIMAL.format(savings.resources.co2_kg_saved) : DASH,
      unit: 'кг CO₂',
      caption: `и ${
        savings ? DECIMAL.format(savings.resources.liters_saved) : DASH
      } л дизеля не сожжено`,
    },
    {
      value:
        savings?.payback.payback_months != null
          ? DECIMAL.format(savings.payback.payback_months)
          : DASH,
      unit: 'мес',
      caption: 'окупаемость десяти баков при тарифе 1 000 ₸',
    },
  ];

  const scenario = revenue?.projection ?? revenue?.pilot;

  return (
    <>
      {/* ---------------------------------------------------------------
          Первый экран. Атмосферу держит видео неба, поверх него —
          сеть площадок города и затемняющая вуаль под текстом.
          --------------------------------------------------------------- */}
      {/* -mt-16 задвигает первый экран под липкую шапку высотой h-16. Без
          этого видео начинается ниже неё, шапка показывает фон страницы, и
          белые надписи на нём становятся нечитаемыми. */}
      <div className="relative -mt-16 overflow-hidden bg-ink">
        <VideoBackdrop src="/media/clouds.mp4" scrim="from-ink/70 via-ink/45 to-ink/85" />

        {/* Живая сеть поверх кадра: точки — площадки, они наполняются и
            вспыхивают при вывозе. На видео она читается только светлой. */}
        <ShowcaseBackdrop accent={[255, 255, 255]} className="opacity-50" />

        {/* Верхние 4rem экрана заняты шапкой, поэтому отступ сверху на неё
            больше — иначе содержимое кажется съехавшим вверх. */}
        <div className="relative mx-auto flex min-h-[92vh] max-w-4xl flex-col items-center justify-center px-5 pb-24 pt-40 text-center">
          <p className="mono-label rounded-full border border-white/25 bg-white/10 px-5 py-2 text-white/90 backdrop-blur-sm">
            EcoFin · Кокшетау · Пилот на десяти баках
          </p>

          <h1 className="display-type mt-9 text-[clamp(2.75rem,8.5vw,6rem)] text-white drop-shadow-sm">
            <span className="display-lead">Считает</span> рейсы.
            <br />
            <span className="display-lead">Показывает</span> деньги.
          </h1>

          <p className="mt-8 max-w-xl text-base leading-relaxed text-white/85 md:text-lg">
            Датчики в баках, вывоз по фактической заполненности и экономический
            слой, который переводит несделанный заезд в литры, тенге и килограммы
            CO₂ — с формулой, раскрываемой на экране.
          </p>

          <div className="mt-11 flex flex-wrap items-center justify-center gap-3">
            <button
              type="button"
              onClick={() => openAuth('login')}
              className="inline-flex items-center gap-2 rounded-lg bg-white px-6 py-3 text-sm font-medium text-ink transition-opacity hover:opacity-90"
            >
              Открыть панель
              <ArrowRight className="h-4 w-4" />
            </button>
            <button
              type="button"
              onClick={() => openAuth('register')}
              className="rounded-lg border border-white/35 px-6 py-3 text-sm font-medium text-white transition-colors hover:bg-white/10"
            >
              Создать аккаунт
            </button>
          </div>

          <a
            href="#numbers"
            aria-label="К цифрам пилота"
            className="mt-20 text-white/60 transition-colors hover:text-white"
          >
            <ChevronDown className="h-5 w-5 animate-bounce" />
          </a>
        </div>
      </div>

      {/* ---------------------------------------------------------------
          Живые цифры.
          --------------------------------------------------------------- */}
      <Section id="numbers" className="border-y border-ink/8 bg-band">
        <div className="mx-auto max-w-6xl px-5 py-20">
          <div className="flex flex-wrap items-end justify-between gap-4">
            <Eyebrow>Отчёт за последние 30 дней</Eyebrow>
            <p className="mono-data text-xs text-faint">
              {savings ? 'данные получены из API' : 'backend недоступен'}
            </p>
          </div>

          <div className="mt-10 grid grid-cols-1 gap-px overflow-hidden rounded-2xl border border-ink/10 bg-ink/8 sm:grid-cols-2 lg:grid-cols-4">
            {stats.map((stat) => (
              <StatCell key={stat.unit} {...stat} />
            ))}
          </div>

          <p className="mt-6 max-w-2xl text-sm leading-relaxed text-faint">
            Это не пример из презентации: те же числа отдаёт публичный эндпоинт
            <span className="mono-data text-body"> /api/eco/savings</span>, и на экране
            диспетчера каждое из них раскрывается до исходной формулы.
          </p>
        </div>
      </Section>

      {/* ---------------------------------------------------------------
          График против факта.
          --------------------------------------------------------------- */}
      <Section className="mx-auto max-w-6xl px-5 py-24">
        <div className="grid gap-14 lg:grid-cols-2 lg:items-center">
          <div>
            <h2 className="display-type text-[clamp(2rem,4vw,3.25rem)] text-ink">
              График говорит 150.
              <br />
              Факт говорит 92.
            </h2>
            <p className="mt-7 max-w-lg text-base leading-relaxed text-body">
              Мусоровоз ходит по расписанию и вывозит баки, заполненные на четверть.
              Мы вывозим по факту — и разница в заездах становится измеримой
              экономией, а не лозунгом об экологии.
            </p>
            <Link
              to="/economics"
              className="mt-8 inline-flex items-center gap-2 text-sm text-ink underline-offset-4 hover:underline"
            >
              Как считается экономия
              <ArrowUpRight className="h-4 w-4" />
            </Link>
          </div>

          <div className="rounded-2xl border border-ink/10 bg-paper p-7">
            <div className="grid grid-cols-2 gap-px overflow-hidden rounded-xl bg-ink/8">
              <div className="bg-paper p-5">
                <p className="mono-label text-faint">По графику</p>
                <p className="mono-data mt-3 text-3xl text-body">
                  {savings ? NUMBER.format(savings.trips.baseline) : DASH}
                </p>
                <p className="mt-1 text-xs text-faint">заездов за 30 дней</p>
              </div>
              <div className="bg-paper p-5">
                <p className="mono-label text-verdant">По факту</p>
                <p className="mono-data mt-3 text-3xl text-ink">
                  {savings ? NUMBER.format(savings.trips.actual) : DASH}
                </p>
                <p className="mt-1 text-xs text-faint">заездов за 30 дней</p>
              </div>
            </div>

            <div className="mt-6 rounded-xl border border-verdant/25 bg-mint/8 p-5">
              <p className="text-sm text-body">Один пропущенный заезд стоит оператору</p>
              <p className="mono-data mt-2 text-2xl text-verdant">379 ₸</p>
              <p className="mt-3 text-xs leading-relaxed text-faint">
                0,39 л дизеля — 129 ₸ · шесть минут бригады — 250 ₸
              </p>
            </div>

            <p className="mt-6 text-xs leading-relaxed text-faint">
              Средняя заполненность в момент вывоза при этом{' '}
              <span className="mono-data text-body">
                {savings?.trips.average_fill_at_collection_percent != null
                  ? `${DECIMAL.format(savings.trips.average_fill_at_collection_percent)}%`
                  : DASH}
              </span>{' '}
              — баки едут полными, а не наполовину пустыми.
            </p>
          </div>
        </div>
      </Section>

      {/* ---------------------------------------------------------------
          Модули коротко, подробности — на своей странице.
          --------------------------------------------------------------- */}
      <Section className="border-y border-ink/8 bg-band">
        <div className="mx-auto max-w-6xl px-5 py-24">
          <div className="flex flex-wrap items-end justify-between gap-6">
            <div>
              <Eyebrow>Пять модулей</Eyebrow>
              <h2 className="display-type mt-7 max-w-2xl text-[clamp(2rem,4vw,3.25rem)] text-ink">
                Одна платформа для города и малого бизнеса.
              </h2>
            </div>
            <Link
              to="/modules"
              className="inline-flex items-center gap-2 text-sm text-ink underline-offset-4 hover:underline"
            >
              Все модули подробно
              <ArrowUpRight className="h-4 w-4" />
            </Link>
          </div>

          <div className="mt-14 grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {MODULES.map((module) => (
              <article key={module.key} className={`${module.surface} rounded-3xl p-7`}>
                <h3
                  className={`display-type text-3xl ${
                    module.invertText ? 'text-white' : 'text-ink'
                  }`}
                >
                  {module.title}
                </h3>
                <p
                  className={`mt-4 text-sm leading-relaxed ${
                    module.invertText ? 'text-mint' : 'text-ink/80'
                  }`}
                >
                  {module.short}
                </p>
              </article>
            ))}
          </div>
        </div>
      </Section>

      {/* ---------------------------------------------------------------
          Переходы в разделы.
          --------------------------------------------------------------- */}
      <Section className="mx-auto max-w-6xl px-5 py-24">
        <Eyebrow tone="signal">Дальше</Eyebrow>
        <h2 className="display-type mt-7 max-w-2xl text-[clamp(2rem,4vw,3.25rem)] text-ink">
          Каждый вопрос разобран отдельно.
        </h2>

        <div className="mt-14 grid gap-4 md:grid-cols-3">
          <SectionLink
            to="/economics"
            eyebrow="Экономика"
            title="Откуда берётся цифра"
            body="Формулы, тариф, разложенный по комплектующим, и пять источников дохода вместо одного."
          />
          <SectionLink
            to="/technology"
            eyebrow="Технология"
            title="Три модели, три задачи"
            body="Где стоит YOLO, где CLIP и почему языковая модель не может выдумать число."
          />
          <SectionLink
            to="/faq"
            eyebrow="Вопросы"
            title="Честные ответы"
            body="Включая неудобные: что система делает, когда данных не хватает, и что с персональными."
          />
        </div>
      </Section>

      {/* ---------------------------------------------------------------
          Полоса-передышка перед разговором о деньгах: одна фраза на
          движущемся кадре, без данных и кнопок.
          --------------------------------------------------------------- */}
      <Section className="relative overflow-hidden bg-ink">
        <VideoBackdrop src="/media/texture.mp4" scrim="from-ink/80 via-ink/65 to-ink/80" />
        <div className="relative mx-auto max-w-4xl px-5 py-28 text-center md:py-36">
          <p className="mono-label text-white/70">Зачем это городу</p>
          <p className="display-type mt-7 text-[clamp(1.75rem,4vw,3rem)] text-white">
            <span className="display-lead">Мусор</span> вывозят по расписанию.
            <br />
            <span className="display-lead">Деньги</span> уезжают вместе с ним.
          </p>
        </div>
      </Section>

      {/* ---------------------------------------------------------------
          Бизнес-модель коротко.
          --------------------------------------------------------------- */}
      <Section className="border-t border-ink/8 bg-band">
        <div className="mx-auto max-w-6xl px-5 py-24">
          <div className="grid gap-14 lg:grid-cols-2 lg:items-end">
            <div>
              <Eyebrow>На чём это зарабатывает</Eyebrow>
              <h2 className="display-type mt-7 text-[clamp(2rem,4vw,3.25rem)] text-ink">
                Пять источников вместо одного.
              </h2>
              <p className="mt-7 max-w-lg text-base leading-relaxed text-body">
                Экономия на маршрутах не окупает платформу в одиночку: бак приносит
                около 2 200 ₸ экономии в месяц, и подписка, удерживаемая ниже этой
                цифры, всегда будет долей небольшой суммы. Это не изъян тарифа, а
                причина, по которой модель стоит на нескольких ногах.
              </p>
              <Link
                to="/economics"
                className="mt-8 inline-flex items-center gap-2 text-sm text-ink underline-offset-4 hover:underline"
              >
                Разбор бизнес-модели
                <ArrowUpRight className="h-4 w-4" />
              </Link>
            </div>

            <div className="rounded-2xl border border-ink/10 bg-paper p-7">
              <p className="mono-label text-faint">
                {revenue?.projection ? 'Проекция на 1 200 баков' : 'Пилот, расчёт по тарифу'}
              </p>
              <p className="display-type mt-4 text-5xl text-ink">
                {scenario ? NUMBER.format(scenario.monthly_recurring_kzt) : DASH}
                <span className="ml-2 font-sans text-lg font-normal text-verdant">₸ / мес</span>
              </p>
              <p className="mt-2 text-xs text-faint">
                {revenue?.projection
                  ? 'расчёт по масштабу города, а не измерение'
                  : 'сколько принёс бы тариф на десяти баках — плательщиков ещё нет'}
              </p>

              <ul className="mt-7 space-y-3">
                {scenario ? (
                  scenario.streams
                    .filter((stream) => stream.is_recurring)
                    .map((stream) => (
                      <li
                        key={stream.key}
                        className="flex items-baseline justify-between gap-4 border-b border-ink/8 pb-3 last:border-0"
                      >
                        <span className="text-sm text-body">{stream.title}</span>
                        <span className="mono-data shrink-0 text-sm text-ink">
                          {NUMBER.format(stream.monthly_kzt)}
                        </span>
                      </li>
                    ))
                ) : (
                  <li className="text-sm text-faint">Backend недоступен</li>
                )}
              </ul>
            </div>
          </div>
        </div>
      </Section>
    </>
  );
}

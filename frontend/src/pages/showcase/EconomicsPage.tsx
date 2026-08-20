import React from 'react';
import { useQuery } from '@tanstack/react-query';
import { fetchRevenue, fetchSavings } from '../../api/eco';
import { queryKeys } from '../../api/queryKeys';
import { Eyebrow, PageHeader, Section, StatCell } from '../../components/showcase/primitives';

const NUMBER = new Intl.NumberFormat('ru-RU', { maximumFractionDigits: 0 });
const DECIMAL = new Intl.NumberFormat('ru-RU', { maximumFractionDigits: 1 });
const DASH = '—';

/** Себестоимость комплекта: то, что жюри вправе проверить построчно. */
const BOM = [
  ['ESP32 DevKit', 2_500],
  ['Ультразвуковой датчик HC-SR04', 800],
  ['Датчик температуры DS18B20', 1_000],
  ['Привод заслонки SG90', 1_200],
  ['Корпус, крепёж, проводка', 3_000],
  ['Питание: аккумулятор и солнечная панель', 8_000],
  ['Монтаж и пусконаладка', 5_000],
] as const;

const BOM_TOTAL = BOM.reduce((sum, [, price]) => sum + price, 0);
const INSTALL_PRICE = 28_000;

export default function EconomicsPage() {
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

  const payback = savings?.payback;

  return (
    <>
      <PageHeader
        eyebrow="Экономика"
        title={<>Каждая цифра раскрывается до формулы.</>}
        lead={
          <>
            Трек EcoFin спрашивает, сколько денег и ресурсов сэкономлено. Ниже — как
            именно это считается, откуда взялся тариф и почему платформа не может
            жить на одной только экономии маршрутов.
          </>
        }
      />

      {/* ---------------------------------------------------------------
          Стоимость одного заезда.
          --------------------------------------------------------------- */}
      <Section className="mx-auto max-w-6xl px-5 py-20">
        <Eyebrow>Единица расчёта</Eyebrow>
        <h2 className="display-type mt-7 max-w-2xl text-[clamp(1.75rem,3.5vw,2.75rem)] text-ink">
          Один заезд на площадку — 379 ₸.
        </h2>

        <div className="mt-12 grid gap-4 md:grid-cols-3">
          {[
            {
              title: 'Топливо',
              value: '129 ₸',
              body: '1,5 км до следующей точки при расходе 26 л на 100 км — это 0,39 л дизеля по 331 ₸.',
            },
            {
              title: 'Бригада',
              value: '250 ₸',
              body: 'Шесть минут на обслуживание площадки при ставке 2 500 ₸ в час.',
            },
            {
              title: 'Выбросы',
              value: '1,05 кг CO₂',
              body: 'Те же 0,39 л дизеля при коэффициенте сжигания 2,68 кг на литр.',
            },
          ].map((item) => (
            <article key={item.title} className="rounded-2xl border border-ink/10 bg-paper p-7">
              <p className="mono-label text-faint">{item.title}</p>
              <p className="mono-data mt-4 text-2xl text-verdant">{item.value}</p>
              <p className="mt-4 text-sm leading-relaxed text-body">{item.body}</p>
            </article>
          ))}
        </div>

        <div className="mt-4 rounded-2xl border border-ink/10 bg-paper p-7 md:p-9">
          <h3 className="text-lg font-medium text-ink">Почему модель маржинальная</h3>
          <p className="mt-4 max-w-3xl text-sm leading-relaxed text-body md:text-base">
            Мусоровоз объезжает много площадок за один рейс. Пропущенная площадка
            сберегает плечо до следующей точки и время бригады на ней — а не рейс от
            автобазы и обратно. Если считать целый рейс на контейнер, цифра вырастет в
            разы, и первый же вопрос жюри её сломает. Заниженная, но защищаемая оценка
            здесь полезнее красивой.
          </p>
        </div>
      </Section>

      {/* ---------------------------------------------------------------
          Что это дало на пилоте.
          --------------------------------------------------------------- */}
      <Section className="border-y border-ink/8 bg-band">
        <div className="mx-auto max-w-6xl px-5 py-20">
          <div className="flex flex-wrap items-end justify-between gap-4">
            <Eyebrow>Пилот, последние 30 дней</Eyebrow>
            <p className="mono-data text-xs text-faint">
              {savings ? 'данные получены из API' : 'backend недоступен'}
            </p>
          </div>

          <div className="mt-10 grid grid-cols-1 gap-px overflow-hidden rounded-2xl border border-ink/10 bg-ink/8 sm:grid-cols-2 lg:grid-cols-4">
            <StatCell
              value={savings ? NUMBER.format(savings.trips.saved) : DASH}
              unit="рейсов"
              caption={`из ${savings ? NUMBER.format(savings.trips.baseline) : DASH} по графику не понадобилось`}
            />
            <StatCell
              value={savings ? DECIMAL.format(savings.resources.km_saved) : DASH}
              unit="км"
              caption="не проехано по городу"
            />
            <StatCell
              value={savings ? DECIMAL.format(savings.resources.liters_saved) : DASH}
              unit="л"
              caption="дизеля осталось в баке"
            />
            <StatCell
              value={savings ? NUMBER.format(savings.money.total_kzt) : DASH}
              unit="₸"
              caption="топливо и время бригады вместе"
            />
          </div>
        </div>
      </Section>

      {/* ---------------------------------------------------------------
          Тариф и окупаемость.
          --------------------------------------------------------------- */}
      <Section className="mx-auto max-w-6xl px-5 py-20">
        <Eyebrow>Тариф</Eyebrow>
        <h2 className="display-type mt-7 max-w-2xl text-[clamp(1.75rem,3.5vw,2.75rem)] text-ink">
          Подписка не может стоить дороже экономии, которую создаёт.
        </h2>
        <p className="mt-8 max-w-2xl text-base leading-relaxed text-body">
          Один бак приносит около 2 200 ₸ экономии в месяц. Подписка держится на
          1 000 ₸ — это 45% созданной пользы, остальное остаётся клиенту. Раньше в
          проекте стояли 5 000 ₸: вдвое больше всей экономии, оператор уходил в минус,
          и срок окупаемости не определялся вовсе. Это была ошибка назначения цены, а
          не расчёта.
        </p>

        <div className="mt-12 grid gap-4 lg:grid-cols-2">
          <div className="rounded-2xl border border-ink/10 bg-paper p-7">
            <p className="mono-label text-faint">Себестоимость комплекта на один бак</p>
            <ul className="mt-6 space-y-3">
              {BOM.map(([name, price]) => (
                <li
                  key={name}
                  className="flex items-baseline justify-between gap-4 border-b border-ink/8 pb-3 text-sm"
                >
                  <span className="text-body">{name}</span>
                  <span className="mono-data shrink-0 text-ink">{NUMBER.format(price)}</span>
                </li>
              ))}
              <li className="flex items-baseline justify-between gap-4 border-b border-ink/8 pb-3 text-sm">
                <span className="text-ink">Итого себестоимость</span>
                <span className="mono-data shrink-0 text-ink">{NUMBER.format(BOM_TOTAL)}</span>
              </li>
              <li className="flex items-baseline justify-between gap-4 pt-1 text-sm">
                <span className="text-ink">Цена для клиента</span>
                <span className="mono-data shrink-0 text-verdant">
                  {NUMBER.format(INSTALL_PRICE)}
                </span>
              </li>
            </ul>
            <p className="mt-6 text-xs leading-relaxed text-faint">
              Разница в {NUMBER.format(INSTALL_PRICE - BOM_TOTAL)} ₸ — гарантия и запас
              на брак. Она показана отдельной строкой, а не спрятана внутри цены.
            </p>
          </div>

          <div className="rounded-2xl border border-ink/10 bg-paper p-7">
            <p className="mono-label text-faint">Окупаемость пилота из десяти баков</p>
            <p className="display-type mt-4 text-5xl text-ink">
              {payback?.payback_months != null ? DECIMAL.format(payback.payback_months) : DASH}
              <span className="ml-2 font-sans text-lg font-normal text-verdant">месяцев</span>
            </p>

            <ul className="mt-8 space-y-3 text-sm">
              {[
                ['Экономия в месяц', payback?.monthly_savings_kzt],
                ['Минус подписка', payback?.monthly_subscription_kzt],
                ['Чистая экономия', payback?.net_monthly_kzt],
                ['Установка всего', payback?.install_total_kzt],
              ].map(([label, value]) => (
                <li
                  key={String(label)}
                  className="flex items-baseline justify-between gap-4 border-b border-ink/8 pb-3 last:border-0"
                >
                  <span className="text-body">{label}</span>
                  <span className="mono-data shrink-0 text-ink">
                    {typeof value === 'number' ? `${NUMBER.format(value)} ₸` : DASH}
                  </span>
                </li>
              ))}
            </ul>

            <p className="mt-6 text-xs leading-relaxed text-faint">
              Если чистая экономия не положительна, срок не выдаётся как «бесконечность»
              — поле честно остаётся пустым.
            </p>
          </div>
        </div>
      </Section>

      {/* ---------------------------------------------------------------
          Источники дохода.
          --------------------------------------------------------------- */}
      <Section className="border-t border-ink/8 bg-band">
        <div className="mx-auto max-w-6xl px-5 py-20">
          <Eyebrow>Бизнес-модель</Eyebrow>
          <h2 className="display-type mt-7 max-w-2xl text-[clamp(1.75rem,3.5vw,2.75rem)] text-ink">
            Пять источников вместо одного.
          </h2>
          <p className="mt-8 max-w-2xl text-base leading-relaxed text-body">
            Экономия на маршрутах не окупает платформу в одиночку — и это не изъян
            тарифа, а причина, по которой модель стоит на нескольких ногах. Каждый
            источник считается из того, что уже лежит в базе, а не из круглого числа
            для слайда.
          </p>

          <div className="mt-12 overflow-x-auto rounded-2xl border border-ink/10">
            <table className="w-full min-w-[640px] text-sm">
              <thead>
                <tr className="border-b border-ink/10 text-left">
                  <th className="mono-label px-6 py-4 font-normal text-faint">Источник</th>
                  <th className="mono-label px-6 py-4 text-right font-normal text-faint">
                    Пилот, ₸/мес
                  </th>
                  <th className="mono-label px-6 py-4 text-right font-normal text-faint">
                    Город, ₸/мес
                  </th>
                  <th className="mono-label px-6 py-4 font-normal text-faint">Основание</th>
                </tr>
              </thead>
              <tbody>
                {revenue?.pilot.streams.map((stream, index) => {
                  const scaled = revenue.projection?.streams[index];
                  return (
                    <tr key={stream.key} className="border-b border-ink/8 last:border-0">
                      <td className="px-6 py-4 text-ink">
                        {stream.title}
                        {!stream.is_recurring && (
                          <span className="ml-2 rounded-full bg-ink/8 px-2 py-0.5 text-[10px] uppercase tracking-wide text-faint">
                            разово
                          </span>
                        )}
                      </td>
                      <td className="mono-data px-6 py-4 text-right text-ink">
                        {NUMBER.format(stream.monthly_kzt)}
                      </td>
                      <td className="mono-data px-6 py-4 text-right text-body">
                        {scaled ? NUMBER.format(scaled.monthly_kzt) : DASH}
                      </td>
                      <td className="mono-data px-6 py-4 text-xs text-faint">{stream.basis}</td>
                    </tr>
                  );
                }) ?? (
                  <tr>
                    <td className="px-6 py-6 text-faint" colSpan={4}>
                      Backend недоступен
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>

          <p className="mt-6 max-w-3xl text-sm leading-relaxed text-faint">
            Колонка «Город» — расчёт на 1 200 баков, а не измерение. Организации и
            жители в ней масштабируются пропорционально бакам: это допущение, и оно
            названо допущением. Разовая маржа на оборудовании не складывается с
            регулярной выручкой — иначе доход был бы посчитан дважды.
          </p>
        </div>
      </Section>
    </>
  );
}

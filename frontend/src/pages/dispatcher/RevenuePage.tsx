import React, { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import {
  Bar,
  BarChart,
  LabelList,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts';
import { Info, Table as TableIcon, Wrench } from 'lucide-react';
import { fetchRevenue } from '../../api/eco';
import { queryKeys } from '../../api/queryKeys';
import { useLocaleTheme } from '../../store/LocaleThemeContext';
import { cn } from '../../lib/utils';
import { MAX_BAR_WIDTH, chartTokens, formatNumber } from '../../lib/chartTheme';
import type { RevenueScenario, RevenueStream } from '../../api/types';

/** Масштабы. Пилот считается по установленным бакам, остальное — проекция. */
const SCALES = [
  { containers: undefined, label: 'Пилот' },
  { containers: 300, label: '300 баков' },
  { containers: 1200, label: 'Кокшетау' },
  { containers: 5000, label: 'Область' },
];

/**
 * Короткая подпись для оси.
 *
 * Полные названия потоков не помещаются в категориальную ось, а обрезка
 * многоточием превращает подписи в загадку. Поэтому у каждого потока есть
 * своя короткая форма, а полное название остаётся в карточках ниже.
 */
const SHORT_TITLE: Record<string, string> = {
  operator_saas: 'Оператор',
  business_saas: 'Бизнес',
  sponsored_rewards: 'Спонсоры',
  carbon_credits: 'CO₂',
  hardware_margin: 'Оборудование',
};

function ScenarioTotals({
  scenario,
  isProjection,
}: {
  scenario: RevenueScenario;
  isProjection: boolean;
}) {
  return (
    <div
      className={cn(
        'rounded-3xl p-6 md:p-8 shadow-sm border',
        isProjection
          ? 'bg-card border-dashed border-muted-foreground/40'
          : 'bg-gradient-to-br from-primary to-primary-light border-primary-light text-white',
      )}
    >
      <div className="flex items-center gap-2">
        <p
          className={cn(
            'text-sm font-medium',
            isProjection ? 'text-muted-foreground' : 'text-white/80',
          )}
        >
          {scenario.title}
        </p>
        {isProjection && (
          <span className="text-[11px] font-bold uppercase tracking-wide px-2 py-0.5 rounded-full bg-warning/15 text-warning">
            расчёт, не факт
          </span>
        )}
      </div>

      <p className="text-5xl md:text-6xl font-black tracking-tight mt-2">
        {formatNumber(scenario.monthly_recurring_kzt)}
        <span className="text-2xl md:text-3xl font-bold ml-2">₸</span>
      </p>
      <p
        className={cn(
          'mt-1 text-base font-semibold',
          isProjection ? 'text-muted-foreground' : 'text-white/90',
        )}
      >
        потенциальной регулярной выручки в месяц · {formatNumber(scenario.annual_recurring_kzt)} ₸ в год
      </p>

      {/* Разовая маржа держится отдельно от регулярной: сложить их — значит
          посчитать выручку дважды. */}
      <p
        className={cn(
          'mt-4 text-sm',
          isProjection ? 'text-muted-foreground' : 'text-white/80',
        )}
      >
        Плюс {formatNumber(scenario.one_time_kzt)} ₸ разово при монтаже
        {' '}{scenario.containers} баков — в сумму выше не входит.
      </p>

      {/* Ни одна цифра на экране не является полученными деньгами. Пилот
          показывает, что дал бы тариф на уже установленных баках; платящих
          клиентов пока нет. Назвать это выручкой значило бы соврать жюри. */}
      {!isProjection && (
        <p className="mt-4 text-xs text-white/70">
          Это не полученные деньги: столько принёс бы тариф на установленных
          баках. Договоров с плательщиками пока нет — считаем юнит-экономику,
          а не выручку.
        </p>
      )}
    </div>
  );
}

function StreamCard({ stream }: { stream: RevenueStream }) {
  return (
    <div className="bg-card border border-border rounded-2xl p-5 flex flex-col gap-2 min-w-0">
      <div className="flex items-start justify-between gap-3">
        <h3 className="font-bold text-base">{stream.title}</h3>
        {!stream.is_recurring && (
          <span className="shrink-0 text-[11px] font-bold uppercase tracking-wide px-2 py-0.5 rounded-full bg-muted text-muted-foreground">
            разово
          </span>
        )}
      </div>
      <p className="text-2xl font-black tracking-tight">
        {formatNumber(stream.monthly_kzt)}
        <span className="text-sm font-semibold text-muted-foreground ml-1.5">
          ₸{stream.is_recurring ? ' / мес' : ''}
        </span>
      </p>
      {/* Основание — то, что превращает число в проверяемое утверждение. */}
      <p className="text-sm font-mono text-muted-foreground break-words">{stream.basis}</p>
      <p className="text-sm text-muted-foreground leading-relaxed">{stream.note}</p>
    </div>
  );
}

export default function RevenuePage() {
  const { theme } = useLocaleTheme();
  const tokens = chartTokens(theme);
  const [scale, setScale] = useState<number | undefined>(undefined);
  const [showTable, setShowTable] = useState(false);

  const { data, isLoading, isError } = useQuery({
    queryKey: queryKeys.eco.revenue(30, scale),
    queryFn: () => fetchRevenue(30, scale),
  });

  if (isError) {
    return (
      <div className="max-w-7xl mx-auto">
        <div className="bg-critical/10 border border-critical/20 rounded-2xl p-6 text-critical font-medium">
          Не удалось загрузить модель доходов. Проверьте, что backend запущен.
        </div>
      </div>
    );
  }

  const scenario = data ? (data.projection ?? data.pilot) : null;
  const isProjection = Boolean(data?.projection);
  const streams = scenario?.streams ?? [];
  const recurring = streams.filter((stream) => stream.is_recurring);
  const oneTime = streams.filter((stream) => !stream.is_recurring);

  // Столбцы сортируются по величине: глаз сравнивает длины, а не ищет их.
  const chartData = [...recurring]
    .sort((a, b) => b.monthly_kzt - a.monthly_kzt)
    .map((stream) => ({
      name: SHORT_TITLE[stream.key] ?? stream.title,
      value: stream.monthly_kzt,
      key: stream.key,
    }));

  return (
    <div className="space-y-6 max-w-7xl mx-auto pb-24 lg:pb-8 text-foreground">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="text-2xl font-bold">Источники дохода</h1>
          <p className="text-sm text-muted-foreground">
            На чём платформа будет зарабатывать и при каком масштабе это окупается
          </p>
        </div>
        <div className="flex gap-1 bg-muted p-1 rounded-xl" role="group" aria-label="Масштаб">
          {SCALES.map((option) => (
            <button
              key={option.label}
              onClick={() => setScale(option.containers)}
              aria-pressed={scale === option.containers}
              className={cn(
                'px-3 py-1.5 rounded-lg text-sm font-semibold transition-colors min-h-[36px]',
                scale === option.containers
                  ? 'bg-card text-primary shadow-sm'
                  : 'text-muted-foreground hover:text-foreground',
              )}
            >
              {option.label}
            </button>
          ))}
        </div>
      </div>

      {isLoading || !scenario ? (
        <div className="h-48 rounded-3xl bg-muted animate-pulse" />
      ) : (
        <ScenarioTotals scenario={scenario} isProjection={isProjection} />
      )}

      {/* Состав регулярной выручки. Одна серия — легенда не нужна,
          заголовок её называет. */}
      <div className="bg-card border border-border rounded-3xl p-5 md:p-6">
        <div className="flex flex-wrap items-center justify-between gap-3 mb-4">
          <div>
            <h2 className="font-bold text-lg">Из чего складывается выручка</h2>
            <p className="text-sm text-muted-foreground">
              Тенге в месяц, только регулярные источники
            </p>
          </div>
          <button
            onClick={() => setShowTable((value) => !value)}
            aria-pressed={showTable}
            className="flex items-center gap-1.5 text-sm font-semibold text-muted-foreground hover:text-foreground px-3 py-1.5 rounded-lg border border-border min-h-[36px]"
          >
            <TableIcon size={15} />
            {showTable ? 'График' : 'Таблица'}
          </button>
        </div>

        {showTable ? (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="text-left text-muted-foreground border-b border-border">
                  <th className="py-2 pr-4 font-semibold">Источник</th>
                  <th className="py-2 pr-4 font-semibold text-right">₸ в месяц</th>
                  <th className="py-2 font-semibold">Основание</th>
                </tr>
              </thead>
              <tbody>
                {recurring.map((stream) => (
                  <tr key={stream.key} className="border-b border-border/50">
                    <td className="py-2 pr-4 font-medium">{stream.title}</td>
                    <td className="py-2 pr-4 text-right tabular-nums">
                      {formatNumber(stream.monthly_kzt)}
                    </td>
                    <td className="py-2 text-muted-foreground font-mono text-xs">
                      {stream.basis}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <div className="h-72 -ml-2">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart
                data={chartData}
                layout="vertical"
                margin={{ top: 4, right: 72, bottom: 4, left: 8 }}
              >
                {/* Сетки нет намеренно: ось скрыта, и линии указывали бы
                    в пустоту. Значения подписаны прямо на столбцах. */}
                <XAxis type="number" hide />
                <YAxis
                  type="category"
                  dataKey="name"
                  width={104}
                  tickLine={false}
                  axisLine={false}
                  tick={{ fill: tokens.axis, fontSize: 13 }}
                />
                <Tooltip
                  cursor={{ fill: tokens.grid, fillOpacity: 0.4 }}
                  contentStyle={{
                    background: tokens.surface,
                    border: `1px solid ${tokens.grid}`,
                    borderRadius: 12,
                    color: tokens.axis,
                  }}
                  formatter={(value) => [`${formatNumber(Number(value ?? 0))} ₸`, 'В месяц']}
                />
                {/* Один цвет на всю серию. Подсветка «крупнейший ярче»
                    здесь врала: 10 000 и 9 000 почти равны, а разный цвет
                    читался как разный класс источника. */}
                <Bar
                  dataKey="value"
                  barSize={MAX_BAR_WIDTH}
                  radius={[0, 4, 4, 0]}
                  fill={tokens.mark}
                >
                  <LabelList
                    dataKey="value"
                    position="right"
                    fill={tokens.axis}
                    fontSize={12}
                    formatter={(value: unknown) => formatNumber(Number(value ?? 0))}
                  />
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>
        )}
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {recurring.map((stream) => (
          <StreamCard key={stream.key} stream={stream} />
        ))}
      </div>

      {oneTime.length > 0 && (
        <div>
          <h2 className="font-bold text-lg mb-3 flex items-center gap-2">
            <Wrench size={18} className="text-muted-foreground" />
            Разовый доход
          </h2>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {oneTime.map((stream) => (
              <StreamCard key={stream.key} stream={stream} />
            ))}
          </div>
        </div>
      )}

      {/* Допущения стоят рядом с цифрами, а не в сноске под экраном. */}
      {data && (
        <div className="bg-muted/50 border border-border rounded-2xl p-5">
          <h2 className="font-bold text-base flex items-center gap-2 mb-3">
            <Info size={17} className="text-muted-foreground" />
            На чём держится расчёт
          </h2>
          <ul className="space-y-2">
            {data.assumptions.map((assumption) => (
              <li key={assumption} className="text-sm text-muted-foreground flex gap-2">
                <span className="text-primary mt-0.5 shrink-0">•</span>
                <span className="leading-relaxed">{assumption}</span>
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}

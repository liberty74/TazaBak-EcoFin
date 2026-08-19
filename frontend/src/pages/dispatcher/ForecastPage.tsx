import React, { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import {
  Bar,
  BarChart,
  LabelList,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts';
import { AlertTriangle, Clock, HelpCircle, Table as TableIcon } from 'lucide-react';
import { fetchForecast } from '../../api/eco';
import { queryKeys } from '../../api/queryKeys';
import { useLocaleTheme } from '../../store/LocaleThemeContext';
import { cn } from '../../lib/utils';
import { MAX_BAR_WIDTH, chartTokens, formatDecimal } from '../../lib/chartTheme';
import type { ContainerForecast } from '../../api/types';

/** Горизонт планирования смены. Всё, что раньше него, попадёт в маршрут. */
const PLANNING_HORIZON_HOURS = 24;

const REASON_TEXT: Record<string, string> = {
  not_enough_measurements:
    'Меньше трёх замеров в текущем цикле. Через две точки прямая проходит идеально, и шум выглядел бы уверенным трендом.',
  not_filling:
    'Уровень не растёт, поэтому срока нет. Приписать его — значит выдумать вывоз.',
};

/** «11.8 ч» читается хуже, чем «11 ч 48 мин». */
const formatEta = (hours: number): string => {
  if (hours < 1) return `${Math.round(hours * 60)} мин`;
  const whole = Math.floor(hours);
  const minutes = Math.round((hours - whole) * 60);
  if (whole >= 24) {
    const days = Math.floor(whole / 24);
    const rest = whole % 24;
    return rest ? `${days} сут ${rest} ч` : `${days} сут`;
  }
  return minutes ? `${whole} ч ${minutes} мин` : `${whole} ч`;
};

/** Короткое имя площадки для оси: «Площадка Абая, 12» → «Абая, 12». */
const shortName = (name: string): string => name.replace(/^Площадка\s+/i, '');

function StatTile({
  icon,
  label,
  value,
  tone,
}: {
  icon: React.ReactNode;
  label: string;
  value: number;
  tone: 'critical' | 'warning' | 'muted';
}) {
  return (
    <div className="bg-card border border-border p-4 md:p-5 rounded-2xl flex flex-col min-w-0">
      <div
        className={cn(
          'p-2.5 rounded-xl w-fit mb-3',
          tone === 'critical' && 'bg-critical/10 text-critical',
          tone === 'warning' && 'bg-warning/10 text-warning',
          tone === 'muted' && 'bg-muted text-muted-foreground',
        )}
      >
        {icon}
      </div>
      <h3 className="text-muted-foreground text-sm font-medium">{label}</h3>
      <p className="text-3xl font-black mt-1 tracking-tight">{value}</p>
    </div>
  );
}

function ContainerRow({ item }: { item: ContainerForecast }) {
  return (
    <div className="flex flex-wrap items-baseline justify-between gap-x-4 gap-y-1 py-3 border-b border-border/50 last:border-0">
      <div className="min-w-0">
        <p className="font-semibold truncate">{item.name}</p>
        <p className="text-xs text-muted-foreground font-mono">{item.device_id}</p>
      </div>
      <div className="text-right shrink-0">
        <p className="font-bold tabular-nums">
          {formatDecimal(item.fill_percent)}%
        </p>
        <p className="text-xs text-muted-foreground">
          порог {formatDecimal(item.threshold_percent)}%
        </p>
      </div>
    </div>
  );
}

export default function ForecastPage() {
  const { theme } = useLocaleTheme();
  const tokens = chartTokens(theme);
  const [showTable, setShowTable] = useState(false);

  const { data, isLoading, isError } = useQuery({
    queryKey: queryKeys.eco.forecast,
    queryFn: fetchForecast,
  });

  if (isError) {
    return (
      <div className="max-w-7xl mx-auto">
        <div className="bg-critical/10 border border-critical/20 rounded-2xl p-6 text-critical font-medium">
          Не удалось загрузить прогноз. Проверьте, что backend запущен.
        </div>
      </div>
    );
  }

  const items = data ?? [];
  const dueNow = items.filter((item) => item.status === 'due_now');
  const forecast = items.filter((item) => item.status === 'forecast');
  const unavailable = items.filter((item) => item.status === 'unavailable');
  const withinHorizon = forecast.filter(
    (item) => (item.eta_hours ?? Infinity) <= PLANNING_HORIZON_HOURS,
  );

  // На шкале часов остаются только те, у кого срок действительно посчитан.
  // «Уже пора» — это ноль, а «прогноза нет» — не число: смешивать их с
  // остальными на одной оси значило бы врать формой.
  const chartData = [...forecast]
    .sort((a, b) => (a.eta_hours ?? 0) - (b.eta_hours ?? 0))
    .map((item) => ({
      name: shortName(item.name),
      hours: item.eta_hours ?? 0,
      label: formatEta(item.eta_hours ?? 0),
    }));

  return (
    <div className="space-y-6 max-w-7xl mx-auto pb-24 lg:pb-8 text-foreground">
      <div>
        <h1 className="text-2xl font-bold">Прогноз заполнения</h1>
        <p className="text-sm text-muted-foreground">
          Когда каждая площадка дойдёт до порога вывоза
        </p>
      </div>

      <div className="grid grid-cols-2 lg:grid-cols-3 gap-3 md:gap-4">
        <StatTile
          icon={<AlertTriangle size={20} />}
          label="Пора вывозить сейчас"
          value={dueNow.length}
          tone="critical"
        />
        <StatTile
          icon={<Clock size={20} />}
          label={`Дойдут за ${PLANNING_HORIZON_HOURS} ч`}
          value={withinHorizon.length}
          tone="warning"
        />
        <StatTile
          icon={<HelpCircle size={20} />}
          label="Срок не определён"
          value={unavailable.length}
          tone="muted"
        />
      </div>

      {dueNow.length > 0 && (
        <div className="bg-critical/5 border border-critical/20 rounded-2xl p-5">
          <h2 className="font-bold text-base flex items-center gap-2 mb-2 text-critical">
            <AlertTriangle size={18} />
            Порог уже пройден
          </h2>
          <div>
            {dueNow.map((item) => (
              <ContainerRow key={item.container_id} item={item} />
            ))}
          </div>
        </div>
      )}

      <div className="bg-card border border-border rounded-3xl p-5 md:p-6">
        <div className="flex flex-wrap items-center justify-between gap-3 mb-4">
          <div>
            <h2 className="font-bold text-lg">Сколько осталось до порога</h2>
            <p className="text-sm text-muted-foreground">
              Часы по линейной регрессии текущего цикла наполнения. Пунктир —
              горизонт смены: всё левее него попадает в сегодняшний маршрут.
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

        {isLoading ? (
          <div className="h-72 rounded-2xl bg-muted animate-pulse" />
        ) : showTable ? (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="text-left text-muted-foreground border-b border-border">
                  <th className="py-2 pr-4 font-semibold">Площадка</th>
                  <th className="py-2 pr-4 font-semibold text-right">Заполнено</th>
                  <th className="py-2 pr-4 font-semibold text-right">Скорость, %/ч</th>
                  <th className="py-2 pr-4 font-semibold text-right">До порога</th>
                  <th className="py-2 font-semibold text-right">R²</th>
                </tr>
              </thead>
              <tbody>
                {forecast
                  .slice()
                  .sort((a, b) => (a.eta_hours ?? 0) - (b.eta_hours ?? 0))
                  .map((item) => (
                    <tr key={item.container_id} className="border-b border-border/50">
                      <td className="py-2 pr-4 font-medium">{item.name}</td>
                      <td className="py-2 pr-4 text-right tabular-nums">
                        {formatDecimal(item.fill_percent)}%
                      </td>
                      <td className="py-2 pr-4 text-right tabular-nums">
                        {item.rate_percent_per_hour === null
                          ? '—'
                          : formatDecimal(item.rate_percent_per_hour)}
                      </td>
                      <td className="py-2 pr-4 text-right tabular-nums">
                        {formatEta(item.eta_hours ?? 0)}
                      </td>
                      <td className="py-2 text-right tabular-nums">
                        {item.r_squared === null ? '—' : item.r_squared.toFixed(2)}
                      </td>
                    </tr>
                  ))}
              </tbody>
            </table>
          </div>
        ) : (
          <div className="h-80 -ml-2">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart
                data={chartData}
                layout="vertical"
                margin={{ top: 22, right: 84, bottom: 4, left: 8 }}
              >
                <XAxis type="number" hide />
                <YAxis
                  type="category"
                  dataKey="name"
                  width={132}
                  tickLine={false}
                  axisLine={false}
                  tick={{ fill: tokens.axis, fontSize: 12 }}
                />
                <Tooltip
                  cursor={{ fill: tokens.grid, fillOpacity: 0.4 }}
                  contentStyle={{
                    background: tokens.surface,
                    border: `1px solid ${tokens.grid}`,
                    borderRadius: 12,
                    color: tokens.axis,
                  }}
                  formatter={(value) => [formatEta(Number(value ?? 0)), 'До порога']}
                />
                {/* Граница смены: всё левее неё едет сегодня. */}
                <ReferenceLine
                  x={PLANNING_HORIZON_HOURS}
                  stroke={tokens.axis}
                  strokeDasharray="4 4"
                  label={{
                    value: `граница смены · ${PLANNING_HORIZON_HOURS} ч`,
                    position: 'top',
                    fill: tokens.axis,
                    fontSize: 11,
                  }}
                />
                <Bar
                  dataKey="hours"
                  barSize={MAX_BAR_WIDTH}
                  radius={[0, 4, 4, 0]}
                  fill={tokens.mark}
                >
                  <LabelList
                    dataKey="label"
                    position="right"
                    fill={tokens.axis}
                    fontSize={12}
                  />
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>
        )}
      </div>

      {unavailable.length > 0 && (
        <div className="bg-card border border-border rounded-2xl p-5">
          <h2 className="font-bold text-base mb-1">Срок не определён</h2>
          <p className="text-sm text-muted-foreground mb-3">
            Прогноз не выдаётся, когда данных не хватает. Это честнее, чем
            показать цифру, которой нечем подтвердиться.
          </p>
          {unavailable.map((item) => (
            <div
              key={item.container_id}
              className="py-3 border-b border-border/50 last:border-0"
            >
              <p className="font-semibold">{item.name}</p>
              <p className="text-sm text-muted-foreground mt-0.5">
                {item.reason ? REASON_TEXT[item.reason] : 'Причина не указана'}
              </p>
              <p className="text-xs text-muted-foreground mt-1">
                замеров в цикле: {item.samples}
              </p>
            </div>
          ))}
        </div>
      )}

      <p className="text-sm text-muted-foreground">
        R² показывает, насколько прямая объясняет замеры. Значение рядом с
        единицей означает ровное наполнение, низкое — что площадкой пользуются
        рывками и сроку доверять не стоит.
      </p>
    </div>
  );
}

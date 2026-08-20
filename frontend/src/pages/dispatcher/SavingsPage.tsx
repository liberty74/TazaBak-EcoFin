import React, { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import {
  Area,
  AreaChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts';
import {
  Bot,
  ChevronDown,
  Coins,
  Droplets,
  Leaf,
  Route as RouteIcon,
  Sparkles,
  Table as TableIcon,
  Truck,
  Wheat,
} from 'lucide-react';
import { fetchRecommendations, fetchRoutePlan, fetchSavings } from '../../api/eco';
import { queryKeys } from '../../api/queryKeys';
import { useLocaleTheme } from '../../store/LocaleThemeContext';
import { cn } from '../../lib/utils';
import {
  AREA_FILL_OPACITY,
  LINE_WIDTH,
  chartTokens,
  formatDecimal,
  formatNumber,
  formatWeek,
} from '../../lib/chartTheme';

const PERIODS = [
  { days: 7, label: '7 дней' },
  { days: 30, label: '30 дней' },
  { days: 90, label: '90 дней' },
];

/** Плитка показателя: подпись, значение, единица. */
function StatTile({
  icon,
  label,
  value,
  unit,
  tone = 'primary',
}: {
  icon: React.ReactNode;
  label: string;
  value: string;
  unit: string;
  tone?: 'primary' | 'bread';
}) {
  return (
    <div className="bg-card border border-border p-4 md:p-5 rounded-2xl md:rounded-3xl shadow-sm flex flex-col min-w-0">
      <div
        className={cn(
          'p-2.5 rounded-xl w-fit mb-3',
          tone === 'bread' ? 'bg-bread/10 text-bread' : 'bg-primary/10 text-primary',
        )}
      >
        {icon}
      </div>
      <h3 className="text-muted-foreground text-sm font-medium">{label}</h3>
      <p className="text-2xl md:text-3xl font-black mt-1 tracking-tight break-words">
        {value}
        <span className="text-sm font-semibold text-muted-foreground ml-1.5">{unit}</span>
      </p>
    </div>
  );
}

export default function SavingsPage() {
  const { theme } = useLocaleTheme();
  const tokens = chartTokens(theme);
  const [days, setDays] = useState(30);
  const [showFormula, setShowFormula] = useState(false);
  const [showTable, setShowTable] = useState(false);

  const { data: report, isLoading, isError } = useQuery({
    queryKey: queryKeys.eco.savings(days),
    queryFn: () => fetchSavings(days),
  });

  const { data: route } = useQuery({
    queryKey: queryKeys.eco.route(24),
    queryFn: () => fetchRoutePlan(24),
  });

  const { data: advice, isLoading: isAdviceLoading } = useQuery({
    queryKey: queryKeys.eco.recommendations(days),
    queryFn: () => fetchRecommendations(days),
  });

  if (isError) {
    return (
      <div className="max-w-7xl mx-auto">
        <div className="bg-critical/10 border border-critical/20 rounded-2xl p-6 text-critical font-medium">
          Не удалось загрузить отчёт об экономии. Проверьте, что backend запущен.
        </div>
      </div>
    );
  }

  const weekly = report?.weekly ?? [];
  const hasPartialWeek = weekly.some((point) => point.is_partial);

  return (
    <div className="space-y-6 max-w-7xl mx-auto pb-24 lg:pb-8 text-foreground">
      {/* Строка фильтра — одна на весь экран, а не внутри карточек */}
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="text-2xl font-bold">Экономия</h1>
          <p className="text-sm text-muted-foreground">
            {report ? `${report.org_name} · ${report.city}` : 'Загрузка отчёта...'}
          </p>
        </div>
        <div className="flex gap-1 bg-muted p-1 rounded-xl" role="group" aria-label="Период отчёта">
          {PERIODS.map((period) => (
            <button
              key={period.days}
              onClick={() => setDays(period.days)}
              aria-pressed={days === period.days}
              className={cn(
                'px-3 py-1.5 rounded-lg text-sm font-semibold transition-colors min-h-[36px]',
                days === period.days
                  ? 'bg-card text-primary shadow-sm'
                  : 'text-muted-foreground hover:text-foreground',
              )}
            >
              {period.label}
            </button>
          ))}
        </div>
      </div>

      {/* Главное число экрана. Жюри трека ищет деньги — показываем их сразу. */}
      <div className="bg-gradient-to-br from-primary to-primary-light border border-primary-light rounded-3xl p-6 md:p-8 text-white shadow-sm">
        <p className="text-white/80 text-sm font-medium">
          Расчётная экономия за {days} дней при вывозе по факту заполненности
        </p>
        <p className="text-5xl md:text-6xl font-black tracking-tight mt-2">
          {isLoading ? '—' : formatNumber(report?.money.total_kzt ?? 0)}
          <span className="text-2xl md:text-3xl font-bold ml-2">₸</span>
        </p>
        <p className="text-white/90 mt-3 text-base md:text-lg font-semibold">
          и {isLoading ? '—' : formatDecimal(report?.resources.co2_kg_saved ?? 0)} кг CO₂ не
          выброшено в воздух
        </p>
        {report && (
          <p className="text-white/70 text-sm mt-3">
            {formatDecimal(report.trips.saved)} рейсов не понадобилось из{' '}
            {formatDecimal(report.trips.baseline)} по графику · {report.containers} площадок
          </p>
        )}
      </div>

      {/* Ресурсы в одном порядке везде: рейсы → топливо → деньги → CO2 */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-3 md:gap-4">
        <StatTile
          icon={<Truck className="w-5 h-5" />}
          label="Рейсов не сделано"
          value={isLoading ? '—' : formatDecimal(report?.trips.saved ?? 0)}
          unit="шт"
        />
        <StatTile
          icon={<Droplets className="w-5 h-5" />}
          label="Топлива сэкономлено"
          value={isLoading ? '—' : formatDecimal(report?.resources.liters_saved ?? 0)}
          unit="л"
        />
        <StatTile
          icon={<Coins className="w-5 h-5" />}
          label="Экономия по расчёту"
          value={isLoading ? '—' : formatNumber(report?.money.total_kzt ?? 0)}
          unit="₸"
        />
        <StatTile
          icon={<Leaf className="w-5 h-5" />}
          label="CO₂ не выброшено"
          value={isLoading ? '—' : formatDecimal(report?.resources.co2_kg_saved ?? 0)}
          unit="кг"
        />
      </div>

      {/* График по неделям. Одна серия — легенда не нужна, заголовок её называет */}
      <section className="bg-card border border-border rounded-3xl p-5 md:p-6 shadow-sm">
        <div className="flex flex-wrap items-start justify-between gap-3 mb-5">
          <div>
            <h2 className="font-bold text-lg">Расчётная экономия по неделям</h2>
            <p className="text-sm text-muted-foreground">
              Тенге, не потраченные на топливо и работу бригады
            </p>
          </div>
          <button
            onClick={() => setShowTable((open) => !open)}
            aria-pressed={showTable}
            className="flex items-center gap-1.5 text-sm font-semibold text-primary hover:bg-muted px-3 py-2 rounded-lg transition-colors min-h-[40px]"
          >
            <TableIcon className="w-4 h-4" />
            {showTable ? 'График' : 'Таблица'}
          </button>
        </div>

        {showTable ? (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="text-left text-muted-foreground border-b border-border">
                  <th className="py-2 pr-4 font-semibold">Неделя с</th>
                  <th className="py-2 pr-4 font-semibold text-right">Рейсов</th>
                  <th className="py-2 pr-4 font-semibold text-right">Тенге</th>
                  <th className="py-2 font-semibold text-right">CO₂, кг</th>
                </tr>
              </thead>
              <tbody className="tabular-nums">
                {weekly.map((point) => (
                  <tr key={point.week_start} className="border-b border-border last:border-0">
                    <td className="py-2 pr-4">
                      {formatWeek(point.week_start)}
                      {point.is_partial && (
                        <span className="ml-2 text-xs text-muted-foreground">(идёт)</span>
                      )}
                    </td>
                    <td className="py-2 pr-4 text-right">{formatDecimal(point.trips_saved)}</td>
                    <td className="py-2 pr-4 text-right">{formatNumber(point.kzt_saved)}</td>
                    <td className="py-2 text-right">{formatDecimal(point.co2_kg_saved)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <div className="h-[260px] w-full">
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={weekly} margin={{ top: 8, right: 8, left: 0, bottom: 0 }}>
                <defs>
                  <linearGradient id="savingsFill" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="0%" stopColor={tokens.mark} stopOpacity={AREA_FILL_OPACITY * 2} />
                    <stop offset="100%" stopColor={tokens.mark} stopOpacity={0} />
                  </linearGradient>
                </defs>
                <CartesianGrid
                  stroke={tokens.grid}
                  strokeWidth={1}
                  vertical={false}
                />
                <XAxis
                  dataKey="week_start"
                  tickFormatter={formatWeek}
                  tick={{ fill: tokens.axis, fontSize: 12 }}
                  tickLine={false}
                  axisLine={{ stroke: tokens.grid }}
                />
                <YAxis
                  tickFormatter={formatNumber}
                  tick={{ fill: tokens.axis, fontSize: 12 }}
                  tickLine={false}
                  axisLine={false}
                  width={64}
                />
                <Tooltip
                  cursor={{ stroke: tokens.muted, strokeWidth: 1 }}
                  contentStyle={{
                    background: tokens.surface,
                    border: `1px solid ${tokens.grid}`,
                    borderRadius: 12,
                    fontSize: 13,
                  }}
                  labelFormatter={(value) => `Неделя с ${formatWeek(String(value))}`}
                  formatter={(value) => [`${formatNumber(Number(value ?? 0))} ₸`, 'Экономия']}
                />
                <Area
                  type="monotone"
                  dataKey="kzt_saved"
                  stroke={tokens.mark}
                  strokeWidth={LINE_WIDTH}
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  fill="url(#savingsFill)"
                  {...{
                    // Точка ставится только на незакрытой неделе — она одна
                    // здесь нуждается в оговорке, а не каждая.
                    dot: (props: { cx?: number; cy?: number; index?: number }) => {
                      const point = weekly[props.index ?? -1];
                      if (!point?.is_partial) {
                        return <g key={`empty-${props.index}`} />;
                      }
                      return (
                        <circle
                          key={`partial-${props.index}`}
                          cx={props.cx}
                          cy={props.cy}
                          r={4}
                          fill={tokens.surface}
                          stroke={tokens.mark}
                          strokeWidth={2}
                        />
                      );
                    },
                  }}
                  activeDot={{ r: 4, fill: tokens.mark, stroke: tokens.surface, strokeWidth: 2 }}
                />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        )}

        {hasPartialWeek && (
          <p className="text-xs text-muted-foreground mt-3">
            Последняя неделя ещё идёт, поэтому она набрала меньше остальных —
            это не падение экономии. Точка на графике отмечена полым кружком.
          </p>
        )}
      </section>

      {/* items-start: карточки живут своей высотой, а не тянутся под соседа */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4 md:gap-6 items-start">
        {/* Маршрут: два числа рядом — в этом и продукт */}
        <section className="bg-card border border-border rounded-3xl p-5 md:p-6 shadow-sm">
          <div className="flex items-center gap-2 mb-5">
            <RouteIcon className="w-5 h-5 text-primary" />
            <h2 className="font-bold text-lg">Маршрут на завтра</h2>
          </div>

          {route ? (
            <>
              <div className="grid grid-cols-2 gap-3">
                <div className="rounded-2xl border border-border p-4">
                  <p className="text-xs font-semibold text-muted-foreground uppercase">
                    Объехать все
                  </p>
                  <p className="text-2xl font-black mt-1">
                    {formatDecimal(route.baseline.distance_km)}
                    <span className="text-sm font-semibold text-muted-foreground ml-1">км</span>
                  </p>
                  <p className="text-sm text-muted-foreground mt-1">
                    {route.baseline.stops} площадок · {formatNumber(route.baseline.kzt)} ₸
                  </p>
                </div>
                <div className="rounded-2xl border-2 border-primary/30 bg-primary/5 p-4">
                  <p className="text-xs font-semibold text-primary uppercase">По плану</p>
                  <p className="text-2xl font-black mt-1 text-primary">
                    {formatDecimal(route.planned.distance_km)}
                    <span className="text-sm font-semibold ml-1">км</span>
                  </p>
                  <p className="text-sm text-muted-foreground mt-1">
                    {route.planned.stops} площадок · {formatNumber(route.planned.kzt)} ₸
                  </p>
                </div>
              </div>

              {/* Мера: сколько от полного объезда занимает план */}
              <div className="mt-4">
                <div className="h-2 w-full rounded-full bg-muted overflow-hidden">
                  <div
                    className="h-full rounded-full bg-primary"
                    style={{
                      width: `${Math.min(
                        100,
                        route.baseline.distance_km > 0
                          ? (route.planned.distance_km / route.baseline.distance_km) * 100
                          : 0,
                      )}%`,
                    }}
                  />
                </div>
                <p className="text-sm font-semibold mt-3">
                  Экономия: {formatDecimal(route.distance_saved_km)} км ·{' '}
                  {formatNumber(route.kzt_saved)} ₸ · {formatDecimal(route.co2_kg_saved)} кг CO₂
                </p>
              </div>

              {route.skipped.length > 0 && (
                <p className="text-sm text-muted-foreground mt-3">
                  Пропускаем сегодня: {route.skipped.slice(0, 4).join(', ')}
                  {route.skipped.length > 4 && ` и ещё ${route.skipped.length - 4}`}
                </p>
              )}
            </>
          ) : (
            <p className="text-sm text-muted-foreground">Загрузка маршрута...</p>
          )}
        </section>

        {/* Рекомендации Баки */}
        <section className="bg-card border border-border rounded-3xl p-5 md:p-6 shadow-sm">
          <div className="flex items-center justify-between gap-2 mb-5">
            <div className="flex items-center gap-2">
              <Bot className="w-5 h-5 text-primary" />
              <h2 className="font-bold text-lg">Рекомендации Баки</h2>
            </div>
            {advice && (
              <span
                className="text-[10px] font-bold uppercase px-2 py-1 rounded-md bg-muted text-muted-foreground"
                title={
                  advice.provider === 'google-gemini'
                    ? `Ответ модели ${advice.model}, сверен с посчитанными числами`
                    : 'Правила по тем же посчитанным числам, без обращения к модели'
                }
              >
                {advice.provider === 'google-gemini' ? 'Gemini' : 'Локальные правила'}
              </span>
            )}
          </div>

          {isAdviceLoading ? (
            <div className="space-y-3 animate-pulse">
              <div className="h-16 bg-muted rounded-2xl" />
              <div className="h-16 bg-muted rounded-2xl" />
            </div>
          ) : (
            <ol className="space-y-3">
              {advice?.recommendations.map((item, index) => (
                <li key={index} className="rounded-2xl border border-border p-4">
                  <div className="flex gap-3">
                    <span className="shrink-0 w-6 h-6 rounded-lg bg-primary/10 text-primary font-bold text-sm flex items-center justify-center">
                      {index + 1}
                    </span>
                    <div className="min-w-0">
                      <p className="font-bold text-sm">{item.title}</p>
                      <p className="text-sm text-muted-foreground mt-1">{item.detail}</p>
                    </div>
                  </div>
                </li>
              ))}
            </ol>
          )}
          <p className="text-xs text-muted-foreground mt-4 flex items-start gap-1.5">
            <Sparkles className="w-3.5 h-3.5 shrink-0 mt-0.5" />
            Модель не считает сама: она получает готовые числа, и каждое число в
            ответе сверяется с ними.
          </p>
        </section>
      </div>

      {/* Спасённый хлеб — отдельно от денег оператора и никогда к ним не прибавляется */}
      {report && report.bread.kg_total > 0 && (
        <section className="bg-card border border-border rounded-3xl p-5 md:p-6 shadow-sm">
          <div className="flex items-center gap-2 mb-4">
            <Wheat className="w-5 h-5 text-bread" />
            <h2 className="font-bold text-lg">Спасённый хлеб</h2>
          </div>
          <div className="grid grid-cols-2 md:grid-cols-3 gap-3">
            <div>
              <p className="text-sm text-muted-foreground">От жителей</p>
              <p className="text-xl font-black mt-0.5">
                {formatDecimal(report.bread.kg_from_citizens)} кг
              </p>
            </div>
            <div>
              <p className="text-sm text-muted-foreground">От бизнеса</p>
              <p className="text-xl font-black mt-0.5">
                {formatDecimal(report.bread.kg_from_business)} кг
              </p>
            </div>
            <div>
              <p className="text-sm text-muted-foreground">Стоимость продукта</p>
              <p className="text-xl font-black mt-0.5 text-bread">
                {formatNumber(report.bread.rescued_value_kzt)} ₸
              </p>
            </div>
          </div>
          <p className="text-xs text-muted-foreground mt-4">
            Это стоимость продукта, ушедшего в приют вместо полигона. Пекарня эти
            деньги не вернёт, поэтому сумма лежит отдельно и к экономии на рейсах
            не прибавляется.
          </p>
        </section>
      )}

      {/* Окупаемость — как есть, включая случай, когда она не сходится */}
      {report && (
        <section className="bg-card border border-border rounded-3xl p-5 md:p-6 shadow-sm">
          <h2 className="font-bold text-lg mb-4">Окупаемость для клиента</h2>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3 tabular-nums">
            <div>
              <p className="text-sm text-muted-foreground">Экономия в месяц</p>
              <p className="text-lg font-black mt-0.5">
                {formatNumber(report.payback.monthly_savings_kzt)} ₸
              </p>
            </div>
            <div>
              <p className="text-sm text-muted-foreground">Подписка в месяц</p>
              <p className="text-lg font-black mt-0.5">
                {formatNumber(report.payback.monthly_subscription_kzt)} ₸
              </p>
            </div>
            <div>
              <p className="text-sm text-muted-foreground">Чистая экономия</p>
              <p
                className={cn(
                  'text-lg font-black mt-0.5',
                  report.payback.net_monthly_kzt > 0 ? 'text-primary' : 'text-critical',
                )}
              >
                {formatNumber(report.payback.net_monthly_kzt)} ₸
              </p>
            </div>
            <div>
              <p className="text-sm text-muted-foreground">Срок окупаемости</p>
              <p className="text-lg font-black mt-0.5">
                {report.payback.payback_months !== null
                  ? `${formatDecimal(report.payback.payback_months)} мес`
                  : 'не определён'}
              </p>
            </div>
          </div>
          {report.payback.payback_months === null && (
            <p className="text-sm text-muted-foreground mt-4">
              При текущем тарифе подписка обходится дороже, чем экономия на рейсах,
              поэтому срок окупаемости не определён — формула возвращает пустое
              значение, а не бесконечность. Тариф меняется через{' '}
              <code className="text-xs bg-muted px-1.5 py-0.5 rounded">PUT /api/eco/profile</code>{' '}
              без переразвёртывания.
            </p>
          )}
        </section>
      )}

      {/* Откуда цифра — раскрытие всех входных значений расчёта */}
      {report && (
        <section className="bg-card border border-border rounded-3xl shadow-sm overflow-hidden">
          <button
            onClick={() => setShowFormula((open) => !open)}
            aria-expanded={showFormula}
            className="w-full flex items-center justify-between gap-3 p-5 md:p-6 text-left hover:bg-muted/50 transition-colors min-h-[56px]"
          >
            <span className="font-bold text-lg">Откуда цифра</span>
            <ChevronDown
              className={cn('w-5 h-5 shrink-0 transition-transform', showFormula && 'rotate-180')}
            />
          </button>

          {showFormula && (
            <div className="px-5 md:px-6 pb-6 space-y-4">
              <pre className="text-xs md:text-sm bg-muted rounded-2xl p-4 overflow-x-auto leading-relaxed">
{`Стоимость одного обслуживания площадки:
  литры  = ${report.formula.km_per_stop} / 100 × ${report.formula.fuel_consumption_l_per_100km} = ${formatDecimal(report.formula.liters_per_saved_stop)} л
  ₸_топл = ${formatDecimal(report.formula.liters_per_saved_stop)} × ${report.formula.fuel_price_kzt_per_liter} ₸/л
  ₸_бриг = ${report.formula.minutes_per_stop} / 60 × ${report.formula.crew_cost_kzt_per_hour} ₸/час
  итого  = ${formatDecimal(report.formula.kzt_per_saved_stop)} ₸ за одну площадку

Экономия за период:
  N_график = ${formatDecimal(report.formula.days)} / 7 × ${report.formula.baseline_trips_per_week} × ${report.formula.containers} = ${formatDecimal(report.trips.baseline)}
  N_факт   = ${report.trips.actual}
  ΔN       = max(0, ${formatDecimal(report.trips.baseline)} − ${report.trips.actual}) = ${formatDecimal(report.trips.saved)}

  км    = ${formatDecimal(report.trips.saved)} × ${report.formula.km_per_stop} = ${formatDecimal(report.resources.km_saved)} км
  литры = ${formatDecimal(report.resources.liters_saved)} л
  ₸     = ${formatDecimal(report.trips.saved)} × ${formatDecimal(report.formula.kzt_per_saved_stop)} = ${formatNumber(report.money.total_kzt)} ₸
  CO₂   = ${formatDecimal(report.resources.liters_saved)} × ${report.formula.co2_kg_per_liter} = ${formatDecimal(report.resources.co2_kg_saved)} кг`}
              </pre>
              <p className="text-sm text-muted-foreground">
                Модель маржинальная: мусоровоз объезжает много площадок за один
                маршрут, поэтому пропущенная площадка экономит плечо до следующей
                точки и время бригады на ней, а не рейс от автобазы.
              </p>
              {report.trips.average_fill_at_collection_percent !== null && (
                <p className="text-sm text-muted-foreground">
                  Средняя заполненность бака в момент вывоза:{' '}
                  <span className="font-bold text-foreground">
                    {formatDecimal(report.trips.average_fill_at_collection_percent)}%
                  </span>{' '}
                  — против 24–45% при вывозе по графику.
                </p>
              )}
            </div>
          )}
        </section>
      )}
    </div>
  );
}

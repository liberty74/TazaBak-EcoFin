import React, { useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  LabelList,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts';
import { toast } from 'sonner';
import { CalendarDays, HeartHandshake, Table as TableIcon, Wheat } from 'lucide-react';
import { fetchBusinessForecast, fetchWriteOffs, saveWriteOff } from '../../api/eco';
import { queryKeys } from '../../api/queryKeys';
import { handleApiError } from '../../api/errors';
import { useLocaleTheme } from '../../store/LocaleThemeContext';
import { cn } from '../../lib/utils';
import {
  MAX_BAR_WIDTH,
  chartTokens,
  formatDecimal,
  formatLongDate,
  formatNumber,
} from '../../lib/chartTheme';

const today = () => new Date().toISOString().slice(0, 10);

/** Общепринятые сокращения: резать название по два символа нельзя —
 *  получаются «Че» и «Во» вместо «Чт» и «Вс». */
const WEEKDAY_SHORT: Record<string, string> = {
  Понедельник: 'Пн',
  Вторник: 'Вт',
  Среда: 'Ср',
  Четверг: 'Чт',
  Пятница: 'Пт',
  Суббота: 'Сб',
  Воскресенье: 'Вс',
};

const emptyForm = () => ({
  occurred_on: today(),
  product: '',
  kg_written_off: '',
  kg_donated: '',
  cost_kzt_per_kg: '',
});

export default function BakeryPage() {
  const { theme } = useLocaleTheme();
  const tokens = chartTokens(theme);
  const queryClient = useQueryClient();
  const [form, setForm] = useState(emptyForm);
  const [showWeekdayTable, setShowWeekdayTable] = useState(false);

  const { data: forecast, isLoading } = useQuery({
    queryKey: queryKeys.eco.businessForecast(undefined, 4),
    queryFn: () => fetchBusinessForecast(undefined, 4),
  });

  const { data: records = [] } = useQuery({
    queryKey: queryKeys.eco.writeOffs(14),
    queryFn: () => fetchWriteOffs(14),
  });

  const mutation = useMutation({
    mutationFn: saveWriteOff,
    onSuccess: (record) => {
      toast.success(`Списание сохранено: ${record.product}, ${record.kg_written_off} кг`);
      setForm(emptyForm());
      queryClient.invalidateQueries({ queryKey: ['ecoWriteOffs'] });
      queryClient.invalidateQueries({ queryKey: ['ecoBusinessForecast'] });
      queryClient.invalidateQueries({ queryKey: ['ecoSavings'] });
    },
    onError: (error) => {
      const normalized = handleApiError(error);
      toast.error(`${normalized.title}: ${normalized.message}`);
    },
  });

  const handleSubmit = (event: React.FormEvent) => {
    event.preventDefault();
    const written = Number(form.kg_written_off);
    const donated = Number(form.kg_donated || 0);
    if (!form.product.trim()) {
      toast.error('Укажите название продукта');
      return;
    }
    if (donated > written) {
      toast.error('Передано в приют не может быть больше, чем списано');
      return;
    }
    mutation.mutate({
      occurred_on: form.occurred_on,
      product: form.product.trim(),
      kg_written_off: written,
      kg_donated: donated,
      cost_kzt_per_kg: Number(form.cost_kzt_per_kg),
    });
  };

  const expectedTotal =
    forecast?.products.reduce((sum, item) => sum + item.expected_kg, 0) ?? 0;

  // Подпись значения кладётся в отдельное поле и заполняется только у того
  // дня, ради которого график и построен: число над каждым столбцом никто
  // не читает, а над одним — читают.
  const weekdayData = (forecast?.weekday_profile ?? []).map((day) => ({
    ...day,
    highlighted: day.name === forecast?.target_weekday,
    label_kg: day.name === forecast?.target_weekday ? formatDecimal(day.average_kg) : '',
  }));

  return (
    <div className="space-y-6 max-w-7xl mx-auto pb-24 lg:pb-8 text-foreground">
      <div>
        <h1 className="text-2xl font-bold">Кабинет пекарни</h1>
        <p className="text-sm text-muted-foreground">
          {forecast ? forecast.org_name : 'Загрузка...'} · списания и прогноз остатков
        </p>
      </div>

      {/* Прогноз на завтра */}
      <div className="bg-gradient-to-br from-bread to-warning border border-warning rounded-3xl p-6 md:p-8 text-white shadow-sm">
        <p className="text-white/80 text-sm font-medium flex items-center gap-2">
          <CalendarDays className="w-4 h-4" />
          Прогноз остатков на{' '}
          {forecast
            ? `${forecast.target_weekday.toLowerCase()}, ${formatLongDate(forecast.target_date)}`
            : '—'}
        </p>
        <p className="text-5xl md:text-6xl font-black tracking-tight mt-2">
          {isLoading ? '—' : formatDecimal(expectedTotal)}
          <span className="text-2xl md:text-3xl font-bold ml-2">кг</span>
        </p>
        <p className="text-white/90 mt-3 text-sm">
          Среднее по тому же дню недели за последние {forecast?.lookback_weeks ?? 4} недели.
          Вторник похож на прошлый вторник сильнее, чем на вчера.
        </p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4 md:gap-6">
        {/* Прогноз по продуктам — таблица, потому что у каждого три величины */}
        <section className="bg-card border border-border rounded-3xl p-5 md:p-6 shadow-sm">
          <div className="flex items-center gap-2 mb-4">
            <Wheat className="w-5 h-5 text-bread" />
            <h2 className="font-bold text-lg">Что останется завтра</h2>
          </div>
          {forecast && forecast.products.length > 0 ? (
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="text-left text-muted-foreground border-b border-border">
                    <th className="py-2 pr-3 font-semibold">Продукт</th>
                    <th className="py-2 pr-3 font-semibold text-right">Ожидаем</th>
                    <th className="py-2 pr-3 font-semibold text-right">Среднее</th>
                    <th className="py-2 font-semibold text-right">Отклонение</th>
                  </tr>
                </thead>
                <tbody className="tabular-nums">
                  {forecast.products.map((item) => (
                    <tr key={item.product} className="border-b border-border last:border-0">
                      <td className="py-2.5 pr-3">
                        <span className="font-medium">{item.product}</span>
                        {item.basis === 'all_days' && (
                          <span
                            className="ml-2 text-[10px] font-bold uppercase px-1.5 py-0.5 rounded bg-muted text-muted-foreground"
                            title="По этому дню недели истории ещё нет — усреднили по всем дням"
                          >
                            все дни
                          </span>
                        )}
                      </td>
                      <td className="py-2.5 pr-3 text-right font-bold">
                        {formatDecimal(item.expected_kg)} кг
                      </td>
                      <td className="py-2.5 pr-3 text-right text-muted-foreground">
                        {formatDecimal(item.average_kg)} кг
                      </td>
                      <td
                        className={cn(
                          'py-2.5 text-right font-semibold',
                          item.deviation_percent > 0 ? 'text-critical' : 'text-primary',
                        )}
                      >
                        {item.deviation_percent > 0 ? '+' : ''}
                        {formatDecimal(item.deviation_percent)}%
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : (
            <p className="text-sm text-muted-foreground">
              Истории списаний пока нет. Внесите несколько дней — прогноз появится.
            </p>
          )}
        </section>

        {/* Итоги периода */}
        <section className="bg-card border border-border rounded-3xl p-5 md:p-6 shadow-sm">
          <div className="flex items-center gap-2 mb-4">
            <HeartHandshake className="w-5 h-5 text-primary" />
            <h2 className="font-bold text-lg">Сколько ушло в приют</h2>
          </div>
          {forecast && (
            <>
              <div className="grid grid-cols-2 gap-3">
                <div className="rounded-2xl border border-border p-4">
                  <p className="text-sm text-muted-foreground">Списано всего</p>
                  <p className="text-2xl font-black mt-1">
                    {formatDecimal(forecast.total_written_off_kg)}
                    <span className="text-sm font-semibold text-muted-foreground ml-1">кг</span>
                  </p>
                </div>
                <div className="rounded-2xl border-2 border-primary/30 bg-primary/5 p-4">
                  <p className="text-sm text-primary">Передано в приют</p>
                  <p className="text-2xl font-black mt-1 text-primary">
                    {formatDecimal(forecast.total_donated_kg)}
                    <span className="text-sm font-semibold ml-1">кг</span>
                  </p>
                </div>
              </div>
              <div className="mt-4">
                <div className="h-2 w-full rounded-full bg-muted overflow-hidden">
                  <div
                    className="h-full rounded-full bg-primary"
                    style={{ width: `${Math.min(100, forecast.donation_rate_percent)}%` }}
                  />
                </div>
                <p className="text-sm font-semibold mt-3">
                  {formatDecimal(forecast.donation_rate_percent)}% списаний спасено ·{' '}
                  {formatNumber(forecast.rescued_value_kzt)} ₸ стоимости продукта
                </p>
              </div>
              <p className="text-xs text-muted-foreground mt-3">
                Это не вернувшиеся деньги: продукт уже списан. Цифра показывает
                стоимость того, что ушло животным вместо полигона.
              </p>
            </>
          )}
        </section>
      </div>

      {/* Профиль по дням недели: выделен завтрашний, остальные — контекст */}
      <section className="bg-card border border-border rounded-3xl p-5 md:p-6 shadow-sm">
        <div className="flex flex-wrap items-start justify-between gap-3 mb-5">
          <div>
            <h2 className="font-bold text-lg">Сколько остаётся по дням недели</h2>
            <p className="text-sm text-muted-foreground">
              Среднее списание, кг · выделен день, на который считаем прогноз
            </p>
          </div>
          <button
            onClick={() => setShowWeekdayTable((open) => !open)}
            aria-pressed={showWeekdayTable}
            className="flex items-center gap-1.5 text-sm font-semibold text-primary hover:bg-muted px-3 py-2 rounded-lg transition-colors min-h-[40px]"
          >
            <TableIcon className="w-4 h-4" />
            {showWeekdayTable ? 'График' : 'Таблица'}
          </button>
        </div>

        {showWeekdayTable ? (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="text-left text-muted-foreground border-b border-border">
                  <th className="py-2 pr-4 font-semibold">День недели</th>
                  <th className="py-2 pr-4 font-semibold text-right">Среднее, кг</th>
                  <th className="py-2 font-semibold text-right">Замеров</th>
                </tr>
              </thead>
              <tbody className="tabular-nums">
                {weekdayData.map((day) => (
                  <tr key={day.weekday} className="border-b border-border last:border-0">
                    <td className="py-2 pr-4">{day.name}</td>
                    <td className="py-2 pr-4 text-right">{formatDecimal(day.average_kg)}</td>
                    <td className="py-2 text-right">{day.samples}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <div className="h-[240px] w-full">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={weekdayData} margin={{ top: 20, right: 8, left: 0, bottom: 0 }}>
                <CartesianGrid stroke={tokens.grid} strokeWidth={1} vertical={false} />
                <XAxis
                  dataKey="name"
                  tickFormatter={(value: string) => WEEKDAY_SHORT[value] ?? value}
                  tick={{ fill: tokens.axis, fontSize: 12 }}
                  tickLine={false}
                  axisLine={{ stroke: tokens.grid }}
                />
                <YAxis
                  tick={{ fill: tokens.axis, fontSize: 12 }}
                  tickLine={false}
                  axisLine={false}
                  width={40}
                />
                <Tooltip
                  cursor={{ fill: tokens.grid, fillOpacity: 0.4 }}
                  contentStyle={{
                    background: tokens.surface,
                    border: `1px solid ${tokens.grid}`,
                    borderRadius: 12,
                    fontSize: 13,
                  }}
                  formatter={(value) => [`${formatDecimal(Number(value ?? 0))} кг`, 'Среднее списание']}
                />
                <Bar dataKey="average_kg" maxBarSize={MAX_BAR_WIDTH} radius={[4, 4, 0, 0]}>
                  {weekdayData.map((day) => (
                    <Cell key={day.weekday} fill={day.highlighted ? tokens.bread : tokens.muted} />
                  ))}
                  {/* Подписан только выделенный день, а не каждый столбец */}
                  <LabelList dataKey="label_kg" position="top" fill={tokens.axis} fontSize={12} />
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>
        )}
      </section>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4 md:gap-6">
        {/* Ввод списаний */}
        <section className="bg-card border border-border rounded-3xl p-5 md:p-6 shadow-sm">
          <h2 className="font-bold text-lg mb-1">Внести вечерние списания</h2>
          <p className="text-sm text-muted-foreground mb-5">
            Один продукт за один день — одна запись. Повторная отправка исправит
            цифры, а не удвоит их.
          </p>
          <form onSubmit={handleSubmit} className="space-y-3">
            <div className="grid grid-cols-2 gap-3">
              <label className="block">
                <span className="text-sm font-medium text-muted-foreground">Дата</span>
                <input
                  type="date"
                  required
                  value={form.occurred_on}
                  onChange={(e) => setForm({ ...form, occurred_on: e.target.value })}
                  className="mt-1 w-full rounded-xl border border-border bg-background px-3 py-2.5 text-sm min-h-[44px]"
                />
              </label>
              <label className="block">
                <span className="text-sm font-medium text-muted-foreground">Продукт</span>
                <input
                  type="text"
                  required
                  maxLength={64}
                  placeholder="Хлеб пшеничный"
                  value={form.product}
                  onChange={(e) => setForm({ ...form, product: e.target.value })}
                  className="mt-1 w-full rounded-xl border border-border bg-background px-3 py-2.5 text-sm min-h-[44px]"
                />
              </label>
            </div>
            <div className="grid grid-cols-3 gap-3">
              <label className="block">
                <span className="text-sm font-medium text-muted-foreground">Списано, кг</span>
                <input
                  type="number"
                  required
                  min={0}
                  step="0.01"
                  value={form.kg_written_off}
                  onChange={(e) => setForm({ ...form, kg_written_off: e.target.value })}
                  className="mt-1 w-full rounded-xl border border-border bg-background px-3 py-2.5 text-sm min-h-[44px]"
                />
              </label>
              <label className="block">
                <span className="text-sm font-medium text-muted-foreground">В приют, кг</span>
                <input
                  type="number"
                  min={0}
                  step="0.01"
                  value={form.kg_donated}
                  onChange={(e) => setForm({ ...form, kg_donated: e.target.value })}
                  className="mt-1 w-full rounded-xl border border-border bg-background px-3 py-2.5 text-sm min-h-[44px]"
                />
              </label>
              <label className="block">
                <span className="text-sm font-medium text-muted-foreground">₸ за кг</span>
                <input
                  type="number"
                  required
                  min={0}
                  step="1"
                  value={form.cost_kzt_per_kg}
                  onChange={(e) => setForm({ ...form, cost_kzt_per_kg: e.target.value })}
                  className="mt-1 w-full rounded-xl border border-border bg-background px-3 py-2.5 text-sm min-h-[44px]"
                />
              </label>
            </div>
            <button
              type="submit"
              disabled={mutation.isPending}
              className="w-full bg-primary text-white font-bold py-3 rounded-xl transition-colors hover:bg-primary/90 disabled:opacity-50 min-h-[48px]"
            >
              {mutation.isPending ? 'Сохраняем...' : 'Сохранить списание'}
            </button>
          </form>
        </section>

        {/* Журнал */}
        <section className="bg-card border border-border rounded-3xl p-5 md:p-6 shadow-sm">
          <h2 className="font-bold text-lg mb-4">Последние записи</h2>
          {records.length > 0 ? (
            <div className="overflow-x-auto max-h-[340px] overflow-y-auto">
              <table className="w-full text-sm">
                <thead className="sticky top-0 bg-card">
                  <tr className="text-left text-muted-foreground border-b border-border">
                    <th className="py-2 pr-3 font-semibold">Дата</th>
                    <th className="py-2 pr-3 font-semibold">Продукт</th>
                    <th className="py-2 pr-3 font-semibold text-right">Списано</th>
                    <th className="py-2 font-semibold text-right">В приют</th>
                  </tr>
                </thead>
                <tbody className="tabular-nums">
                  {records.map((record) => (
                    <tr key={record.id} className="border-b border-border last:border-0">
                      <td className="py-2 pr-3">{formatLongDate(record.occurred_on)}</td>
                      <td className="py-2 pr-3">{record.product}</td>
                      <td className="py-2 pr-3 text-right">
                        {formatDecimal(record.kg_written_off)} кг
                      </td>
                      <td className="py-2 text-right text-primary font-semibold">
                        {formatDecimal(record.kg_donated)} кг
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : (
            <p className="text-sm text-muted-foreground">Записей пока нет.</p>
          )}
        </section>
      </div>
    </div>
  );
}

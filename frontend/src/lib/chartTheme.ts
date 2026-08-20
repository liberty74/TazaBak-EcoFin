import type { Theme } from '../store/LocaleThemeContext';

/**
 * Токены графиков EcoFin.
 *
 * Значения не подбирались на глаз: каждый цвет марки проверен на контраст
 * не ниже 3:1 к своей поверхности, иначе на светлой теме зелёный уходил в
 * невидимку (#39A96B даёт к белому всего 2.97:1 и годится только для тёмной).
 *
 *   светлая тема, поверхность #FFFFFF   mark 6.47:1 · muted 3.60:1
 *   тёмная тема,  поверхность #1B211E   mark 6.47:1 · muted 4.51:1
 *
 * Поверхность и сетка держатся ровно теми же значениями, что и карточка
 * приложения: иначе фон подсказки над графиком отличается от карточки,
 * на которой он лежит.
 *
 * Сетка намеренно на шаг от поверхности — она не данные и не должна спорить
 * с ними за внимание.
 */
export interface ChartTokens {
  /** Основная серия. Единственный цвет данных на графике. */
  mark: string;
  /** Приглушённый контекст в приёме «выделить одно, остальное серым». */
  muted: string;
  /** Хлеб и остатки пекарни — другой домен, другой оттенок. */
  bread: string;
  /** Волосяная линия сетки, сплошная и рецессивная. */
  grid: string;
  /** Цвет поверхности: зазоры и кольца делаются им, а не обводкой. */
  surface: string;
  /** Подписи осей — текстовым токеном, никогда цветом данных. */
  axis: string;
}

const LIGHT: ChartTokens = {
  mark: '#176B4D',
  muted: '#7C8A84',
  bread: '#B87333',
  grid: '#ECE6DA',
  surface: '#FFFFFF',
  axis: '#66736D',
};

const DARK: ChartTokens = {
  mark: '#35B87C',
  muted: '#7A8A83',
  bread: '#D89A52',
  grid: '#2E3833',
  surface: '#1B211E',
  axis: '#9BA39E',
};

export const chartTokens = (theme: Theme): ChartTokens =>
  theme === 'dark' ? DARK : LIGHT;

/** Заливка площади — тот же оттенок серии лёгкой размывкой, не плашкой. */
export const AREA_FILL_OPACITY = 0.1;

/** Толщина линии и столбца: данные тонкие, кричать им не нужно. */
export const LINE_WIDTH = 2;
export const MAX_BAR_WIDTH = 24;

const NUMBER_FORMAT = new Intl.NumberFormat('ru-RU', { maximumFractionDigits: 0 });
const DECIMAL_FORMAT = new Intl.NumberFormat('ru-RU', { maximumFractionDigits: 1 });

export const formatNumber = (value: number): string => NUMBER_FORMAT.format(value);
export const formatDecimal = (value: number): string => DECIMAL_FORMAT.format(value);

/** Дата недели для оси: «4 авг» вместо ISO-строки. */
export const formatWeek = (iso: string): string =>
  new Date(iso).toLocaleDateString('ru-RU', { day: 'numeric', month: 'short' });

/** Дата для человека: «18 августа» вместо 2026-08-18. */
export const formatLongDate = (iso: string): string =>
  new Date(iso).toLocaleDateString('ru-RU', { day: 'numeric', month: 'long' });

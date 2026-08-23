import { describe, expect, it } from 'vitest';

import { LINK_SILENCE_MS, linkState } from './deviceLink';

// Фиксированный «сейчас»: иначе тест зависел бы от времени прогона.
const NOW = new Date('2026-08-20T12:00:00Z').getTime();
const agoMs = (ms: number) => new Date(NOW - ms).toISOString();

describe('состояние связи с платой', () => {
  it('считает плату живой, пока молчание короче порога', () => {
    expect(linkState(agoMs(LINK_SILENCE_MS - 1000), NOW)).toEqual({
      online: true,
      label: 'на связи',
    });
  });

  it('считает связь потерянной ровно на пороге', () => {
    // Граница принадлежит «молчит»: двенадцать пропущенных отправок подряд —
    // это уже не помеха.
    expect(linkState(agoMs(LINK_SILENCE_MS), NOW).online).toBe(false);
  });

  it('называет длительность молчания в удобных единицах', () => {
    expect(linkState(agoMs(7 * 60_000), NOW).label).toBe('молчит 7 мин');
    expect(linkState(agoMs(3 * 3_600_000), NOW).label).toBe('молчит 3 ч');
    expect(linkState(agoMs(2 * 86_400_000), NOW).label).toBe('молчит 2 сут');
  });

  it('не рисует связь там, где замеров ещё не было', () => {
    expect(linkState(null, NOW)).toEqual({
      online: false,
      label: 'замеров ещё не было',
    });
    expect(linkState(undefined, NOW).online).toBe(false);
  });

  it('нечитаемую дату считает отсутствием связи, а не жизнью', () => {
    // Раньше NaN в арифметике давал бы silentMs = NaN, сравнение — false, и
    // плата с испорченной датой выглядела бы как молчащая. Проверка ловит
    // обратный случай: она не должна оказаться «на связи».
    expect(linkState('не дата', NOW).online).toBe(false);
  });
});

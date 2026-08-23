/** Состояние связи с платой, выведенное из свежести последнего замера. */

// Плата шлёт замер раз в 15 секунд. Молчание дольше трёх минут — это двенадцать
// пропущенных подряд, и списать их на помехи уже нельзя: связь потеряна.
// Порог намеренно щедрый — мигающая плашка на каждый одиночный сбой приучает
// не обращать на неё внимания.
export const LINK_SILENCE_MS = 3 * 60 * 1000;

export interface LinkState {
  online: boolean;
  label: string;
}

export function linkState(
  measuredAt: string | null | undefined,
  now: number = Date.now(),
): LinkState {
  if (!measuredAt) return { online: false, label: 'замеров ещё не было' };

  const measured = new Date(measuredAt).getTime();
  // Нечитаемая дата — не повод рисовать зелёную точку: неизвестно не равно живо.
  if (Number.isNaN(measured)) return { online: false, label: 'замеров ещё не было' };

  const silentMs = now - measured;
  if (silentMs < LINK_SILENCE_MS) return { online: true, label: 'на связи' };

  const minutes = Math.round(silentMs / 60000);
  if (minutes < 60) return { online: false, label: `молчит ${minutes} мин` };
  const hours = Math.round(minutes / 60);
  if (hours < 24) return { online: false, label: `молчит ${hours} ч` };
  return { online: false, label: `молчит ${Math.round(hours / 24)} сут` };
}

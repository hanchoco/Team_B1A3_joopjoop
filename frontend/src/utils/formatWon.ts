const MAN_WON = 10000

/** Format an amount in won: below 만원 shows the raw 원 value, 만원 and above
 * auto-converts to 만원 units. */
export function formatWon(amount: number | string): string {
  const numeric = Number(amount)
  if (!Number.isFinite(numeric)) return '0원'
  const abs = Math.abs(numeric)
  if (abs < MAN_WON) {
    return `${numeric.toLocaleString()}원`
  }
  const manWon = numeric / MAN_WON
  const rounded = Math.round(manWon * 100) / 100
  return `${rounded.toLocaleString()}만 원`
}

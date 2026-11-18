// Presentation only: the values themselves are never rounded or changed.
const fourDecimals = new Intl.NumberFormat("es", { minimumFractionDigits: 4, maximumFractionDigits: 4 });

/** A value for display, with four decimals (Spanish decimal comma). */
export function formatValue(value: number): string {
  return fourDecimals.format(value);
}

/** The full value, exactly as received (JavaScript's shortest round-trip representation of the double). */
export function exactValue(value: number): string {
  return String(value);
}

const SCALE = 10 ** 4;

/** The displayed value as an integer number of ten-thousandths ("0,1815" -> 1815), read from the text the user sees. */
function displayedUnits(value: number): number {
  const text = formatValue(value);
  const units = Number(text.replace(/[^\d]/g, ""));
  return text.startsWith("-") ? -units : units;
}

/**
 * `high - low` computed on the values as they are displayed, so that what the user reads always subtracts correctly:
 * 0,3495 - 0,1815 = 0,1680. It is not the exact difference rounded (which can end in 0,1679); the exact difference is
 * never changed or discarded, it is simply not what this presentation value is.
 */
export function formatDisplayedDifference(high: number, low: number): string {
  return formatValue((displayedUnits(high) - displayedUnits(low)) / SCALE);
}

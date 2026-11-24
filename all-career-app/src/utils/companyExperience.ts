/** Match only a stated requirement; titles and seniority never supply a range. */
export function matchesCompanyExperience(requirement: string | undefined, years: number): boolean {
  const value = (requirement || '').toLowerCase();
  const numbers = (value.match(/\d+(?:\.\d+)?/g) || []).map(Number);
  if (!numbers.length) {
    if (/fresher|entry.level|fresh graduate/.test(value)) return years === 0;
    if (/intern|trainee/.test(value)) return years >= 0 && years <= 1;
    return false;
  }
  const divisor = /month/.test(value) && !/year|yr/.test(value) ? 12 : 1;
  let minimum = numbers[0] / divisor;
  let maximum = minimum;
  if (numbers.length > 1) {
    minimum = Math.min(numbers[0], numbers[1]) / divisor;
    maximum = Math.max(numbers[0], numbers[1]) / divisor;
  } else if (/\+|minimum|at least|above|more than/.test(value)) maximum = Infinity;
  else if (/up to|maximum|less than/.test(value)) minimum = 0;
  return years >= minimum && years <= maximum;
}

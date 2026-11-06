/** Resolve our CSS color tokens before handing options to ECharts' canvas parser.
 * Numeric observations, missing values and formatter functions are unchanged.
 */
export function resolveChartTokens<T>(option: T, styles: Pick<CSSStyleDeclaration, 'getPropertyValue'>): T {
  const resolve = (value: unknown): unknown => {
    if (typeof value === 'string' && /^var\(--[a-z0-9-]+\)$/.test(value)) return styles.getPropertyValue(value.slice(4, -1)).trim() || value
    if (Array.isArray(value)) return value.map(resolve)
    if (value && typeof value === 'object' && Object.getPrototypeOf(value) === Object.prototype) return Object.fromEntries(Object.entries(value).map(([key, entry]) => [key, resolve(entry)]))
    return value
  }
  return resolve(option) as T
}

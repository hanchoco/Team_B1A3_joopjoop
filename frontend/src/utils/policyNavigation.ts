export const POLICY_LIST_PATH = '/policies'

export const POSSIBILITY_FILTERS = [
  { value: 'ELIGIBLE', label: '가능성 높음' },
  { value: 'NEEDS_REVIEW', label: '추가 확인 필요' },
  { value: 'ALL', label: '전체' },
] as const

export type PossibilityFilter = (typeof POSSIBILITY_FILTERS)[number]['value']

export interface PolicyListNavigationState {
  fromPolicyList: true
}

const POLICY_LIST_SCROLL_STORAGE_PREFIX = 'joopjoop:policy-list-scroll:'

export function resolvePossibilityFilter(value: string | null): PossibilityFilter {
  return POSSIBILITY_FILTERS.find((filter) => filter.value === value)?.value ?? 'ELIGIBLE'
}

export function resolvePolicyListFilter(searchParams: URLSearchParams): PossibilityFilter {
  const requestedFilter = searchParams.get('filter')
  if (requestedFilter) return resolvePossibilityFilter(requestedFilter)

  return searchParams.get('search')?.trim() ? 'ALL' : 'ELIGIBLE'
}

export function buildPolicyDetailPath(policyId: number, searchParams: URLSearchParams): string {
  const listParams = new URLSearchParams(searchParams)
  listParams.set('filter', resolvePolicyListFilter(listParams))
  const listPath = `${POLICY_LIST_PATH}?${listParams.toString()}`
  const detailParams = new URLSearchParams({ returnTo: listPath })
  return `${POLICY_LIST_PATH}/${policyId}?${detailParams.toString()}`
}

export function resolvePolicyListReturnPath(value: string | null, origin: string): string {
  if (!value) return POLICY_LIST_PATH

  try {
    const url = new URL(value, origin)
    if (url.origin !== origin || url.pathname !== POLICY_LIST_PATH) {
      return POLICY_LIST_PATH
    }
    return `${url.pathname}${url.search}`
  } catch {
    return POLICY_LIST_PATH
  }
}

export function isPolicyListNavigationState(value: unknown): value is PolicyListNavigationState {
  return (
    typeof value === 'object' &&
    value !== null &&
    'fromPolicyList' in value &&
    value.fromPolicyList === true
  )
}

export function rememberPolicyListScrollPosition(locationKey: string, scrollY: number): void {
  if (!locationKey || !Number.isFinite(scrollY) || scrollY < 0) return

  try {
    window.sessionStorage.setItem(
      `${POLICY_LIST_SCROLL_STORAGE_PREFIX}${locationKey}`,
      String(scrollY),
    )
  } catch {
    // Scroll restoration is best-effort when session storage is unavailable.
  }
}

export function readPolicyListScrollPosition(locationKey: string): number | null {
  if (!locationKey) return null

  try {
    const storedValue = window.sessionStorage.getItem(
      `${POLICY_LIST_SCROLL_STORAGE_PREFIX}${locationKey}`,
    )
    if (storedValue === null) return null

    const value = Number(storedValue)
    return Number.isFinite(value) && value >= 0 ? value : null
  } catch {
    return null
  }
}

export function clearPolicyListScrollPosition(locationKey: string): void {
  if (!locationKey) return

  try {
    window.sessionStorage.removeItem(`${POLICY_LIST_SCROLL_STORAGE_PREFIX}${locationKey}`)
  } catch {
    // Scroll restoration is best-effort when session storage is unavailable.
  }
}

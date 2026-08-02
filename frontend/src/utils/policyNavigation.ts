export const POLICY_LIST_PATH = '/policies'

export const POSSIBILITY_FILTERS = [
  { value: 'ELIGIBLE', label: '가능성 높음' },
  { value: 'NEEDS_REVIEW', label: '추가 확인 필요' },
  { value: 'ALL', label: '전체' },
] as const

export type PossibilityFilter = (typeof POSSIBILITY_FILTERS)[number]['value']

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

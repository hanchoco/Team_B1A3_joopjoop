export type ChecklistEntryPoint = 'mypage' | 'my-policies' | 'policy-detail'

export type ChecklistNavigationState =
  | {
      from: 'mypage'
      myPageReturnTo: string
    }
  | {
      from: 'my-policies'
      myPoliciesReturnTo: string
    }
  | {
      from: 'policy-detail'
      policyDetailReturnTo: string
      policyDetailState: unknown
    }

function isSafeLocalPath(value: unknown): value is string {
  return typeof value === 'string' && value.startsWith('/') && !value.startsWith('//')
}

export function isChecklistNavigationState(value: unknown): value is ChecklistNavigationState {
  if (typeof value !== 'object' || value === null || !('from' in value)) {
    return false
  }

  if (value.from === 'mypage') {
    return 'myPageReturnTo' in value && isSafeLocalPath(value.myPageReturnTo)
  }
  if (value.from === 'my-policies') {
    return 'myPoliciesReturnTo' in value && isSafeLocalPath(value.myPoliciesReturnTo)
  }
  return (
    value.from === 'policy-detail' &&
    'policyDetailReturnTo' in value &&
    isSafeLocalPath(value.policyDetailReturnTo) &&
    'policyDetailState' in value
  )
}

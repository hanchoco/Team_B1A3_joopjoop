import type { PolicySummaryResponse } from '../types/api'
import { normalizePolicyDisplayText } from './policyContent'

export interface PolicyCardPreview {
  summary: string
  hasMoreContent: boolean
}

const MAX_PREVIEW_LENGTH = 180
const LIST_PREFIX = /^(?:(?:[○◯·•※★]|[-–—](?=\s))\s*|\d{1,2}[.)]\s*)+/
const METADATA_PREFIX =
  /^(?:\d{1,2}[.)]\s*)?(?:모집\s*기간|모집\s*대상|모집\s*인원|모집\s*분야|접수\s*기간|신청\s*방법|지원\s*자격|선정\s*인원|선정\s*발표|활동\s*내용|문\s*의\s*처|문의처)\s*[:：]/
const NOTICE_PREFIX = /^[※★]/
const WRAPPING_QUOTES: ReadonlyArray<readonly [string, string]> = [
  ['"', '"'],
  ["'", "'"],
  ['“', '”'],
  ['‘', '’'],
]

function stripWrappingQuotes(value: string): string {
  const pair = WRAPPING_QUOTES.find(
    ([opening, closing]) => value.startsWith(opening) && value.endsWith(closing),
  )
  return pair ? value.slice(pair[0].length, -pair[1].length).trim() : value
}

function cleanPreviewLine(value: string): string {
  return stripWrappingQuotes(
    value
      .replace(LIST_PREFIX, '')
      .replace(/\s+\|\s+/g, ' · ')
      .replace(/[ \t]+/g, ' ')
      .trim(),
  )
}

function truncatePreview(value: string): string {
  if (value.length <= MAX_PREVIEW_LENGTH) return value

  const candidate = value.slice(0, MAX_PREVIEW_LENGTH).trimEnd()
  const lastSpaceIndex = candidate.lastIndexOf(' ')
  const boundary = lastSpaceIndex >= MAX_PREVIEW_LENGTH * 0.6 ? lastSpaceIndex : candidate.length
  return `${candidate.slice(0, boundary).trimEnd()}…`
}

export function buildPolicyCardPreview(
  policy: Pick<PolicySummaryResponse, 'summary'>,
): PolicyCardPreview {
  if (!policy.summary?.trim()) {
    return { summary: '', hasMoreContent: false }
  }

  const normalized = normalizePolicyDisplayText(policy.summary).replace(/\r\n?/g, '\n')
  const sourceLines = normalized.split('\n').map((line) => line.trim())
  const previewLines: string[] = []
  let omittedMetadata = false

  for (const line of sourceLines) {
    if (!line) continue
    if (previewLines.length > 0 && (METADATA_PREFIX.test(line) || NOTICE_PREFIX.test(line))) {
      omittedMetadata = true
      break
    }

    const cleaned = cleanPreviewLine(line)
    if (cleaned) previewLines.push(cleaned)
  }

  const fullPreview = previewLines.join(' ')
  const summary = truncatePreview(fullPreview)

  return {
    summary,
    hasMoreContent: omittedMetadata || fullPreview.length > MAX_PREVIEW_LENGTH,
  }
}

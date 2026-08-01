export type PolicyContentItemType = 'notice' | 'primary' | 'secondary' | 'plain' | 'process'

export interface ParsedPolicyContentItem {
  type: PolicyContentItemType
  text: string
}

interface ParsePolicyContentOptions {
  mode?: 'default' | 'support' | 'application'
  unmarkedType?: PolicyContentItemType
}

const HTML_ENTITIES: Record<string, string> = {
  '&gt;': '>',
  '&lt;': '<',
  '&amp;': '&',
  '&quot;': '"',
  '&#39;': "'",
  '&nbsp;': ' ',
}

const HTML_ENTITY_PATTERN = /&(?:gt|lt|amp|quot|nbsp|#39);/g
const URL_PATTERN = /(https?:\/\/[^\s]+)/g
const NOTICE_PREFIX = /^[★※]\s*/
const PRIMARY_PREFIX = /^[○◯]\s*/
const SECONDARY_PREFIX = /^[-·•]\s*/
const PROCESS_SEPARATOR = /\s+-\s+/
const PIPE_SEPARATOR = /\s+\|\s+/

function normalizeArrowTokens(value: string): string {
  return value
    .split(URL_PATTERN)
    .map((part) => (/^https?:\/\//.test(part) ? part : part.replace(/[ \t]*->[ \t]*/g, ' → ')))
    .join('')
}

export function normalizePolicyDisplayText(value: string): string {
  const decoded = value.replace(HTML_ENTITY_PATTERN, (entity) => HTML_ENTITIES[entity])
  return normalizeArrowTokens(decoded)
}

function parseNormalizedPolicyContentItem(
  text: string,
  unmarkedType: PolicyContentItemType = 'plain',
): ParsedPolicyContentItem {
  if (NOTICE_PREFIX.test(text)) {
    return { type: 'notice', text: text.replace(NOTICE_PREFIX, '').trim() }
  }
  if (PRIMARY_PREFIX.test(text)) {
    return { type: 'primary', text: text.replace(PRIMARY_PREFIX, '').trim() }
  }
  if (SECONDARY_PREFIX.test(text)) {
    return { type: 'secondary', text: text.replace(SECONDARY_PREFIX, '').trim() }
  }
  return { type: unmarkedType, text }
}

export function parsePolicyContentItem(
  value: string,
  unmarkedType: PolicyContentItemType = 'plain',
): ParsedPolicyContentItem {
  return parseNormalizedPolicyContentItem(normalizePolicyDisplayText(value).trim(), unmarkedType)
}

function parsePolicyContentLine(
  value: string,
  { mode = 'default', unmarkedType = 'plain' }: ParsePolicyContentOptions,
): ParsedPolicyContentItem[] {
  const normalized = normalizePolicyDisplayText(value).trim()
  if (!normalized) return []

  const initialItem = parseNormalizedPolicyContentItem(normalized, unmarkedType)
  if (initialItem.type === 'notice') return [initialItem]

  if (mode === 'application') {
    const steps = normalized.split(PROCESS_SEPARATOR).map((step) => step.trim())
    if (steps.length > 1) {
      return steps
        .map((step) => ({
          type: 'process' as const,
          text: parseNormalizedPolicyContentItem(step).text,
        }))
        .filter((item) => item.text.length > 0)
    }
  }

  if (mode === 'support') {
    const parts = normalized.split(PIPE_SEPARATOR).map((part) => part.trim())
    if (parts.length > 1) {
      return parts
        .map((part) => {
          const item = parseNormalizedPolicyContentItem(part, unmarkedType)
          return item.type === 'plain' ? { ...item, type: 'secondary' as const } : item
        })
        .filter((item) => item.text.length > 0)
    }
  }

  return initialItem.text ? [initialItem] : []
}

export function parsePolicyContent(
  value: string | null | undefined,
  options: ParsePolicyContentOptions = {},
): ParsedPolicyContentItem[] {
  if (!value) return []

  return value
    .replace(/\r\n?/g, '\n')
    .split('\n')
    .flatMap((line) => parsePolicyContentLine(line, options))
}

export function parsePolicyContentLines(
  values: string[],
  options: ParsePolicyContentOptions = {},
): ParsedPolicyContentItem[] {
  return values.flatMap((value) => parsePolicyContent(value, options))
}

export function parsePolicySummary(value: string | null | undefined): ParsedPolicyContentItem[] {
  if (!value) return []

  return normalizePolicyDisplayText(value)
    .replace(/\r\n?/g, '\n')
    .split(/(?=[○◯])/)
    .flatMap((segment) => segment.split('\n'))
    .map((segment) => {
      const text = segment.trim()
      if (PRIMARY_PREFIX.test(text)) {
        return {
          type: 'secondary' as const,
          text: text.replace(PRIMARY_PREFIX, '').trim(),
        }
      }
      return parseNormalizedPolicyContentItem(text)
    })
    .filter((item) => item.text.length > 0)
}

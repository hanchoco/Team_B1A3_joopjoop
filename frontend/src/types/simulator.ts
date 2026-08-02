export type SimulatorInputValue = number

export interface SimulatorFormProps {
  /** Read-only values the policy already knows (calculation_rule_json). */
  rule: Record<string, unknown>
  /** User-entered personal variables only. `undefined` means the field is empty. */
  values: Record<string, SimulatorInputValue | undefined>
  /** `undefined` clears the field so native `required` validation sees it as empty. */
  onChange: (name: string, value: SimulatorInputValue | undefined) => void
}

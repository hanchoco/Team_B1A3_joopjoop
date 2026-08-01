export type SimulatorInputValue = number

export interface SimulatorFormProps {
  /** Read-only values the policy already knows (calculation_rule_json). */
  rule: Record<string, unknown>
  /** User-entered personal variables only. */
  values: Record<string, SimulatorInputValue>
  onChange: (name: string, value: SimulatorInputValue) => void
}

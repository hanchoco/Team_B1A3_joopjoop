export type SimulatorInputValue = string | number

export interface SimulatorFormProps {
  values: Record<string, SimulatorInputValue>
  onChange: (name: string, value: SimulatorInputValue) => void
}

import type { PolicyStatus } from '../types'
import { getPolicyStatusDisplay } from '../lib/policyStatus'

interface Props {
  status: PolicyStatus
}

export default function StatusBadge({ status }: Props) {
  const { label, className } = getPolicyStatusDisplay(status)
  return <span className={className}>{label}</span>
}

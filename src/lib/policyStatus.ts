import type { PolicyStatus } from '../types'

export const policyStatusOptions: { value: PolicyStatus; label: string; className: string }[] = [
  { value: 'active', label: '现行有效', className: 'status-active' },
  { value: 'repealed', label: '已废止', className: 'status-repealed' },
  { value: 'draft', label: '征求意见稿', className: 'status-draft' },
  { value: 'unknown', label: '未知', className: 'status-draft' },
]

export function getPolicyStatusDisplay(status: PolicyStatus) {
  return policyStatusOptions.find(option => option.value === status) ?? policyStatusOptions[3]
}

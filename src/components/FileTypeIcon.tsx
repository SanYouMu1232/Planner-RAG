import { FileText, FileImage, File, Scan, Presentation, Table2 } from 'lucide-react'
import type { FileType } from '../types'

const iconMap: Record<FileType, { Icon: typeof FileText; color: string }> = {
  pdf: { Icon: FileText, color: 'text-red-500' },
  word: { Icon: FileText, color: 'text-blue-500' },
  ppt: { Icon: Presentation, color: 'text-orange-500' },
  excel: { Icon: Table2, color: 'text-emerald-600' },
  image: { Icon: FileImage, color: 'text-purple-500' },
  scan: { Icon: Scan, color: 'text-amber-500' },
  web: { Icon: File, color: 'text-green-500' },
  txt: { Icon: FileText, color: 'text-slate-500' },
  md: { Icon: FileText, color: 'text-slate-500' },
  other: { Icon: File, color: 'text-foreground-muted' },
}
interface Props { type: FileType; size?: number }
export default function FileTypeIcon({ type, size = 18 }: Props) { const {Icon,color}=iconMap[type] ?? iconMap.other; return <Icon size={size} className={color}/> }

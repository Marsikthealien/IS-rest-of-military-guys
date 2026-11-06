import { LeaveStatus } from '../constants'
import { Badge } from '@/components/ui/badge'

const VARIANT = {
  SCHEDULED: 'default',
  APPROVED: 'default',
  REJECTED: 'destructive',
  CANCELLED: 'outline',
  COMPLETED: 'outline',
}

export default function StatusBadge({ status }) {
  return <Badge variant={VARIANT[status] || 'secondary'} className="whitespace-normal">{LeaveStatus[status]}</Badge>
}

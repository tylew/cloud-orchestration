import { cn } from '@/lib/utils'

type StatusDotProps = {
  status: 'success' | 'warning' | 'error' | 'pending' | 'info'
  className?: string
}

const statusColors: Record<StatusDotProps['status'], string> = {
  success: 'bg-green-500',
  warning: 'bg-amber-500',
  error: 'bg-destructive',
  pending: 'bg-muted-foreground',
  info: 'bg-muted-foreground',
}

export function StatusDot({ status, className }: StatusDotProps) {
  return (
    <span
      className={cn('inline-block h-2 w-2 rounded-full', statusColors[status], className)}
      aria-label={status}
    />
  )
}

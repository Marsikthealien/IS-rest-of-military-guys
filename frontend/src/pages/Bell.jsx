import { useEffect, useState } from 'react'
import { Bell as BellIcon } from 'lucide-react'
import { api } from '../api'
import { Badge } from '@/components/ui/badge'
import { buttonVariants } from '@/components/ui/button'
import { Popover, PopoverContent, PopoverTrigger } from '@/components/ui/popover'

export default function Bell({ userId, tick }) {
  const [items, setItems] = useState([])
  const load = () => api.notifications(userId).then(setItems).catch(() => {})

  useEffect(() => {
    load()
    const t = setInterval(load, 10000) // опитування раз на 10 с
    return () => clearInterval(t)
  }, [userId, tick])

  // при відкритті позначаємо прочитаними; підсвітка лишається до закриття
  const toggle = (open) => { if (open) api.notifications(userId, true); else load() }
  const unread = items.filter((n) => !n.isRead).length

  return (
    <Popover onOpenChange={toggle}>
      {/* без asChild: Button не передає ref у React 18, і Popover лишався б поза екраном */}
      <PopoverTrigger className={buttonVariants({ variant: 'outline', size: 'sm' })} aria-label={`Сповіщення, непрочитаних: ${unread}`}>
        <BellIcon />
        {unread > 0 && <Badge className="px-1.5">{unread}</Badge>}
      </PopoverTrigger>
      <PopoverContent align="end" className="max-h-96 w-80 overflow-auto p-0">
        {items.length === 0 && <p className="p-4 text-sm text-muted-foreground">Сповіщень немає</p>}
        {items.map((n) => (
          <div key={n.id} className={`border-b p-3 text-sm last:border-0 ${n.isRead ? '' : 'bg-muted'}`}>
            {n.text}
            <div className="mt-1 text-xs text-muted-foreground">{new Date(n.createdAt).toLocaleString('uk-UA')}</div>
          </div>
        ))}
      </PopoverContent>
    </Popover>
  )
}

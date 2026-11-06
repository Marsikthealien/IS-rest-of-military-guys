import { useState } from 'react'
import { format, parseISO } from 'date-fns'
import { uk } from 'date-fns/locale'
import { CalendarIcon } from 'lucide-react'
import { buttonVariants } from '@/components/ui/button'
import { Calendar } from '@/components/ui/calendar'
import { Popover, PopoverContent, PopoverTrigger } from '@/components/ui/popover'
import { cn } from '@/lib/utils'

// value і onChange працюють із рядком YYYY-MM-DD, як і API.
// Минулі дати не вимикаємо: їх відхиляє перевірка V4 зі своїм текстом помилки.
export default function DatePicker({ id, value, onChange, invalid }) {
  const [open, setOpen] = useState(false)
  const selected = value ? parseISO(value) : undefined

  const select = (date) => {
    onChange(date ? format(date, 'yyyy-MM-dd') : '')
    setOpen(false)
  }

  return (
    <Popover open={open} onOpenChange={setOpen}>
      <PopoverTrigger
        id={id}
        aria-invalid={invalid}
        className={cn(buttonVariants({ variant: 'outline' }), 'w-full justify-between font-normal', !selected && 'text-muted-foreground')}
      >
        {selected ? format(selected, 'dd.MM.yyyy') : 'Оберіть дату'}
        <CalendarIcon className="text-muted-foreground" />
      </PopoverTrigger>
      <PopoverContent align="start" className="w-auto p-0">
        <Calendar mode="single" locale={uk} selected={selected} defaultMonth={selected} onSelect={select} autoFocus />
      </PopoverContent>
    </Popover>
  )
}

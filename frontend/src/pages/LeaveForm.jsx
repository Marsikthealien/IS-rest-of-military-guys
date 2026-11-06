import { useEffect, useState } from 'react'
import { api } from '../api'
import { LeaveType } from '../constants'
import DatePicker from '@/components/DatePicker.jsx'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'

const today = () => new Date().toISOString().slice(0, 10)

// клієнтська автоперевірка V1-V5 (лише підказка, рішення за сервером)
function validate(f) {
  const e = {}
  if (!f.type) e.type = 'Не вказано тип відпустки'
  if (!f.dateFrom) e.dateFrom = 'Вкажіть дату початку'
  else if (f.dateFrom < today()) e.dateFrom = 'Дата початку не може бути в минулому'
  if (!f.dateTo) e.dateTo = 'Вкажіть дату кінця'
  else if (f.dateFrom && f.dateTo < f.dateFrom) e.dateTo = 'Дата кінця раніша за дату початку'
  return e
}

const duration = (a, b) => Math.round((new Date(b) - new Date(a)) / 86400000) + 1

function Field({ id, label, error, children }) {
  return (
    <div className="grid gap-2">
      <Label htmlFor={id}>{label}</Label>
      {children}
      {error && <p className="text-sm text-destructive">{error}</p>}
    </div>
  )
}

export default function LeaveForm({ userId, onSubmitted, tick }) {
  const [f, setF] = useState({ type: '', dateFrom: '', dateTo: '', comment: '' })
  const [balances, setBalances] = useState([])
  const [serverErr, setServerErr] = useState({})
  const [done, setDone] = useState('')

  useEffect(() => { api.balance(userId).then(setBalances) }, [userId, tick])

  const setValue = (k, v) => { setF({ ...f, [k]: v }); setServerErr({}); setDone('') }
  const set = (k) => (e) => setValue(k, e.target.value)
  const clientErr = validate(f)
  const pristine = !f.type && !f.dateFrom && !f.dateTo // порожня форма ще без помилок, як на wireframe
  const errors = pristine ? serverErr : { ...clientErr, ...serverErr }
  const days = f.dateFrom && f.dateTo && !clientErr.dateTo ? duration(f.dateFrom, f.dateTo) : null
  const bal = balances.find((b) => b.type === f.type)
  const after = bal && bal.remainingDays != null && days != null ? bal.remainingDays - days : null
  const exceeded = after != null && after < 0

  const submit = async () => {
    try {
      const r = await api.submit(userId, { ...f, type: f.type || null, dateFrom: f.dateFrom || null, dateTo: f.dateTo || null })
      setDone(`Заявку №${r.id} подано`)
      setF({ type: '', dateFrom: '', dateTo: '', comment: '' })
      onSubmitted()
    } catch (e) { setServerErr(e.errors || { dateTo: e.detail }) }
  }

  const blocked = Object.keys(clientErr).length > 0 || exceeded

  return (
    <Card>
      <CardHeader>
        <CardTitle>Нова заявка на відпустку</CardTitle>
        <CardDescription>Система перевірить повноту заявки й залишок днів ще до подання.</CardDescription>
      </CardHeader>
      <CardContent className="grid gap-5">
        <Field id="type" label="Тип відпустки *" error={errors.type}>
          <Select value={f.type} onValueChange={(v) => setValue('type', v)}>
            <SelectTrigger id="type" className="w-full" aria-invalid={!!errors.type}><SelectValue placeholder="Оберіть тип" /></SelectTrigger>
            <SelectContent>
              {Object.entries(LeaveType).map(([k, v]) => <SelectItem key={k} value={k}>{v}</SelectItem>)}
            </SelectContent>
          </Select>
        </Field>
        <div className="grid gap-5 sm:grid-cols-2">
          <Field id="dateFrom" label="Дата початку *" error={errors.dateFrom}>
            <DatePicker id="dateFrom" value={f.dateFrom} onChange={(v) => setValue('dateFrom', v)} invalid={!!errors.dateFrom} />
          </Field>
          <Field id="dateTo" label="Дата кінця *" error={errors.dateTo}>
            <DatePicker id="dateTo" value={f.dateTo} onChange={(v) => setValue('dateTo', v)} invalid={!!errors.dateTo} />
          </Field>
        </div>
        <p className="text-sm text-muted-foreground">
          Тривалість: <span className="font-medium text-foreground">{days != null ? `${days} календарних днів` : '-'}</span>
        </p>
        <Field id="comment" label="Коментар">
          <Input id="comment" value={f.comment} onChange={set('comment')} />
        </Field>

        {bal && (
          <Alert variant={exceeded ? 'destructive' : 'default'}>
            <AlertDescription>
              <span>
                Залишок ({LeaveType[bal.type]}, 2026):{' '}
                {bal.remainingDays == null ? 'без ліміту' : (
                  <>{bal.remainingDays} дн.{after != null && <> → після заявки <b>{after} дн.</b></>}</>
                )}
                {exceeded && <> Перевищено залишок на {-after} дн.</>}
              </span>
            </AlertDescription>
          </Alert>
        )}
        <div className="flex items-center gap-3">
          <Button onClick={submit} disabled={blocked}>Подати</Button>
          {done && <span role="status" className="text-sm text-muted-foreground">{done}</span>}
        </div>
      </CardContent>
    </Card>
  )
}

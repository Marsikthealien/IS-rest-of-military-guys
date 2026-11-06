import { useEffect, useState } from 'react'
import { api } from '../api'
import { LeaveType } from '../constants'
import ScheduleCard from './ScheduleCard.jsx'
import StatusBadge from './StatusBadge.jsx'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table'

export default function CommanderCabinet({ userId, tick, onChanged }) {
  const [rows, setRows] = useState([])
  const [overlaps, setOverlaps] = useState({})
  const [reasons, setReasons] = useState({})
  const [comments, setComments] = useState({})
  const [error, setError] = useState('')

  useEffect(() => { api.requests(userId).then(setRows) }, [userId, tick])

  const run = async (fn) => {
    try { setError(''); await fn(); onChanged() } catch (e) {
      setError(e.errors ? Object.values(e.errors).join('; ') : e.detail || 'Помилка')
    }
  }
  const open = (id) => run(async () => {
    const r = await api.open(userId, id)
    setOverlaps((o) => ({ ...o, [id]: r.overlaps }))
  })

  return (
    <>
    <Card>
      <CardHeader><CardTitle>Заявки на розгляд</CardTitle></CardHeader>
      <CardContent className="grid gap-4">
        {error && <Alert variant="destructive"><AlertDescription>{error}</AlertDescription></Alert>}
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>№</TableHead><TableHead>Військовослужбовець</TableHead><TableHead>Тип</TableHead>
              <TableHead>Дати</TableHead><TableHead>Статус</TableHead><TableHead className="w-72">Дії</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {rows.map((r) => (
              <TableRow key={r.id} className="align-top">
                <TableCell>{r.id}</TableCell>
                <TableCell className="whitespace-normal">{r.memberName}</TableCell>
                <TableCell className="whitespace-normal">{LeaveType[r.type]}</TableCell>
                <TableCell className="whitespace-normal">{r.dateFrom} - {r.dateTo}<div className="text-xs text-muted-foreground">{r.durationDays} дн.</div></TableCell>
                <TableCell className="whitespace-normal">
                  <StatusBadge status={r.status} />
                </TableCell>
                <TableCell className="whitespace-normal">
                  <div className="grid gap-2">
                    {r.status === 'SUBMITTED' && <Button size="sm" onClick={() => open(r.id)}>Відкрити</Button>}
                    {overlaps[r.id]?.length > 0 && (
                      <Alert><AlertDescription>Перетини: {overlaps[r.id].map((o) => `${o.memberName} ${o.dateFrom} - ${o.dateTo}`).join('; ')}</AlertDescription></Alert>
                    )}
                    {r.status === 'UNDER_REVIEW' && (
                      <>
                        <Input aria-label="Коментар" placeholder="Коментар" value={comments[r.id] || ''} onChange={(e) => setComments({ ...comments, [r.id]: e.target.value })} />
                        <Button size="sm" onClick={() => run(() => api.approve(userId, r.id, comments[r.id]))}>Погодити</Button>
                        <Input aria-label="Причина відхилення" placeholder="Причина відхилення *" value={reasons[r.id] || ''} onChange={(e) => setReasons({ ...reasons, [r.id]: e.target.value })} />
                        <Button size="sm" variant="destructive" disabled={!(reasons[r.id] || '').trim()} onClick={() => run(() => api.reject(userId, r.id, reasons[r.id]))}>Відхилити</Button>
                      </>
                    )}
                  </div>
                </TableCell>
              </TableRow>
            ))}
            {rows.length === 0 && <TableRow><TableCell colSpan={6} className="py-6 text-center text-muted-foreground">Заявок на розгляд немає</TableCell></TableRow>}
          </TableBody>
        </Table>
      </CardContent>
    </Card>
    <ScheduleCard userId={userId} tick={tick} />
    </>
  )
}

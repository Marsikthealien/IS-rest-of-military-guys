import { useEffect, useState } from 'react'
import { api } from '../api'
import { LeaveType } from '../constants'
import StatusBadge from './StatusBadge.jsx'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table'

export default function MyRequests({ userId, tick, onChanged }) {
  const [rows, setRows] = useState([])
  useEffect(() => { api.requests(userId).then(setRows) }, [userId, tick])

  const cancel = async (id) => { await api.cancel(userId, id); onChanged() }

  return (
    <Card>
      <CardHeader><CardTitle>Мої заявки</CardTitle></CardHeader>
      <CardContent>
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>№</TableHead><TableHead>Тип</TableHead><TableHead>Дати</TableHead><TableHead>Дн.</TableHead>
              <TableHead>Статус</TableHead><TableHead>Причина</TableHead><TableHead />
            </TableRow>
          </TableHeader>
          <TableBody>
            {rows.map((r) => (
              <TableRow key={r.id}>
                <TableCell>{r.id}</TableCell>
                <TableCell>{LeaveType[r.type]}</TableCell>
                <TableCell>{r.dateFrom} - {r.dateTo}</TableCell>
                <TableCell>{r.durationDays}</TableCell>
                <TableCell><StatusBadge status={r.status} /></TableCell>
                <TableCell className="whitespace-normal">
                                    {r.decisions.filter((d) => d.reason).map((d, i) => <div key={i} className="text-destructive">Причина: {d.reason}</div>)}
                </TableCell>
                <TableCell className="text-right">
                  {r.status === 'SUBMITTED' && <Button variant="outline" size="sm" onClick={() => cancel(r.id)}>Скасувати</Button>}
                </TableCell>
              </TableRow>
            ))}
            {rows.length === 0 && <TableRow><TableCell colSpan={7} className="py-6 text-center text-muted-foreground">Заявок ще немає</TableCell></TableRow>}
          </TableBody>
        </Table>
      </CardContent>
    </Card>
  )
}

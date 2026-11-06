import { useEffect, useState } from 'react'
import { api } from '../api'
import { LeaveStatus, LeaveType } from '../constants'
import ScheduleCard from './ScheduleCard.jsx'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table'

function History({ userId, tick }) {
  const [rows, setRows] = useState([])
  useEffect(() => { api.history(userId).then(setRows) }, [userId, tick])

  return (
    <Card>
      <CardHeader><CardTitle>Історія підрозділу</CardTitle></CardHeader>
      <CardContent>
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Заявка</TableHead><TableHead>Військовослужбовець</TableHead><TableHead>Зі статусу</TableHead>
              <TableHead>У статус</TableHead><TableHead>Причина або коментар</TableHead><TableHead>Хто</TableHead><TableHead>Коли</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {rows.map((d, i) => (
              <TableRow key={i} className="align-top">
                <TableCell>№{d.requestId}</TableCell>
                <TableCell className="whitespace-normal">{d.memberName}</TableCell>
                <TableCell className="whitespace-normal">{LeaveStatus[d.fromStatus]}</TableCell>
                <TableCell className="whitespace-normal">{LeaveStatus[d.toStatus]}</TableCell>
                <TableCell className="whitespace-normal">{d.reason || d.comment || '-'}</TableCell>
                <TableCell className="whitespace-normal">{d.changedBy}</TableCell>
                <TableCell className="whitespace-normal">{new Date(d.decidedAt).toLocaleString('uk-UA')}</TableCell>
              </TableRow>
            ))}
            {rows.length === 0 && <TableRow><TableCell colSpan={7} className="py-6 text-center text-muted-foreground">Історія порожня</TableCell></TableRow>}
          </TableBody>
        </Table>
      </CardContent>
    </Card>
  )
}

function Norms({ userId }) {
  const [rows, setRows] = useState([])
  const [edit, setEdit] = useState({})
  const [msg, setMsg] = useState({ error: '', ok: '' })
  useEffect(() => { api.norms(userId).then(setRows) }, [userId])

  const save = async (type) => {
    try {
      const n = await api.saveNorm(userId, type, Number(edit[type]))
      setRows((rs) => rs.map((r) => (r.type === type ? n : r)))
      setEdit(({ [type]: _, ...rest }) => rest)
      setMsg({ error: '', ok: `Норму збережено: ${LeaveType[type]}` })
    } catch (e) {
      setMsg({ error: e.errors ? Object.values(e.errors).join('; ') : e.detail || 'Помилка', ok: '' })
    }
  }

  return (
    <Card>
      <CardHeader><CardTitle>Довідник норм</CardTitle></CardHeader>
      <CardContent className="grid gap-4">
        {msg.error && <Alert variant="destructive"><AlertDescription>{msg.error}</AlertDescription></Alert>}
        {msg.ok && <p role="status" className="text-sm text-muted-foreground">{msg.ok}</p>}
        <Table>
          <TableHeader>
            <TableRow><TableHead>Тип</TableHead><TableHead className="w-40">Днів на рік</TableHead><TableHead className="w-32" /></TableRow>
          </TableHeader>
          <TableBody>
            {rows.map((n) => (
              <TableRow key={n.type}>
                <TableCell>{LeaveType[n.type]}</TableCell>
                <TableCell>
                  <Input type="number" min="0" aria-label={`Днів на рік: ${LeaveType[n.type]}`}
                    value={edit[n.type] ?? n.daysPerYear}
                    onChange={(e) => setEdit({ ...edit, [n.type]: e.target.value })} />
                </TableCell>
                <TableCell className="text-right">
                  <Button size="sm" disabled={edit[n.type] === undefined || edit[n.type] === ''} onClick={() => save(n.type)}>Зберегти</Button>
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </CardContent>
    </Card>
  )
}

export default function HRCabinet({ userId, tick }) {
  return (
    <>
      <ScheduleCard userId={userId} tick={tick} />
      <History userId={userId} tick={tick} />
      <Norms userId={userId} />
    </>
  )
}

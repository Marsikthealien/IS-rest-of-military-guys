import { useEffect, useState } from 'react'
import { api } from '../api'
import { LeaveType } from '../constants'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table'

// Графік відпусток: командир бачить свій підрозділ, відповідальний за кадровий облік - усі (визначає сервер)
export default function ScheduleCard({ userId, tick }) {
  const [rows, setRows] = useState([])
  useEffect(() => { api.schedule(userId).then(setRows) }, [userId, tick])

  return (
    <Card>
      <CardHeader><CardTitle>Графік відпусток</CardTitle></CardHeader>
      <CardContent>
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Підрозділ</TableHead><TableHead>Військовослужбовець</TableHead><TableHead>Тип</TableHead>
              <TableHead>З</TableHead><TableHead>По</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {rows.map((e) => (
              <TableRow key={e.id}>
                <TableCell>{e.unitName}</TableCell>
                <TableCell>{e.rank} {e.memberName}</TableCell>
                <TableCell>{LeaveType[e.type]}</TableCell>
                <TableCell>{e.dateFrom}</TableCell>
                <TableCell>{e.dateTo}</TableCell>
              </TableRow>
            ))}
            {rows.length === 0 && <TableRow><TableCell colSpan={5} className="py-6 text-center text-muted-foreground">Графік порожній</TableCell></TableRow>}
          </TableBody>
        </Table>
      </CardContent>
    </Card>
  )
}

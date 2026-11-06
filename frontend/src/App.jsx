import { useEffect, useState } from 'react'
import { api } from './api'
import { Roles } from './constants'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Alert, AlertDescription } from '@/components/ui/alert'
import LeaveForm from './pages/LeaveForm.jsx'
import MyRequests from './pages/MyRequests.jsx'
import CommanderCabinet from './pages/CommanderCabinet.jsx'
import HRCabinet from './pages/HRCabinet.jsx'
import Bell from './pages/Bell.jsx'

export default function App() {
  const [users, setUsers] = useState([])
  const [role, setRole] = useState('SERVICE_MEMBER')
  const [userId, setUserId] = useState(null)
  const [tick, setTick] = useState(0) // лічильник для оновлення списків після дій
  const refresh = () => setTick((t) => t + 1)

  const [error, setError] = useState('')

  useEffect(() => { api.users().then(setUsers) }, [])
  const ofRole = users.filter((u) => u.role === role)
  // вибір користувача = вхід через POST /login; кабінет відкривається лише після успіху
  const signIn = async (u) => {
    setUserId(null)
    if (!u) return
    try { setError(''); await api.login(u.login); setUserId(u.id) } catch (e) { setError(e.detail || 'Помилка входу') }
  }
  useEffect(() => { signIn(ofRole[0]) }, [users])
  // роль і користувач змінюються разом, щоб кабінет не смикав API від імені попереднього користувача
  const changeRole = (r) => { setRole(r); signIn(users.find((u) => u.role === r)) }

  return (
    <div className="min-h-screen bg-background text-foreground">
      <header className="sticky top-0 z-10 border-b bg-background/95 backdrop-blur">
        <div className="mx-auto flex max-w-5xl flex-wrap items-center gap-3 px-4 py-3">
          <span className="mr-2 font-semibold tracking-tight">ІС «Відпустка»</span>
          <Select value={role} onValueChange={changeRole}>
            <SelectTrigger className="w-80 max-w-full" aria-label="Роль"><SelectValue /></SelectTrigger>
            <SelectContent>
              {Object.entries(Roles).map(([k, v]) => <SelectItem key={k} value={k}>{v}</SelectItem>)}
            </SelectContent>
          </Select>
          <Select value={userId ? String(userId) : ''} onValueChange={(v) => signIn(users.find((u) => u.id === Number(v)))}>
            <SelectTrigger className="w-80 max-w-full" aria-label="Користувач"><SelectValue placeholder="Користувач" /></SelectTrigger>
            <SelectContent>
              {ofRole.map((u) => <SelectItem key={u.id} value={String(u.id)}>{u.rank} {u.fullName}</SelectItem>)}
            </SelectContent>
          </Select>
          <div className="ml-auto">{userId && <Bell userId={userId} tick={tick} />}</div>
        </div>
      </header>
      <main className="mx-auto flex max-w-5xl flex-col gap-6 px-4 py-6">
        {error && <Alert variant="destructive"><AlertDescription>{error}</AlertDescription></Alert>}
        {userId && role === 'SERVICE_MEMBER' && (
          <>
            <LeaveForm key={userId} userId={userId} onSubmitted={refresh} tick={tick} />
            <MyRequests userId={userId} tick={tick} onChanged={refresh} />
          </>
        )}
        {userId && role === 'COMMANDER' && <CommanderCabinet userId={userId} tick={tick} onChanged={refresh} />}
        {userId && role === 'HR_CLERK' && <HRCabinet userId={userId} tick={tick} />}
      </main>
    </div>
  )
}

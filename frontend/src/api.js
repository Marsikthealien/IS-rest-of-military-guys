// Тонка обгортка над fetch; роль передається заголовком X-User-Id
const BASE = '/api'
const PASSWORD = 'demo' // пароль усіх тестових користувачів (seed)

async function call(userId, method, path, body) {
  const res = await fetch(BASE + path, {
    method,
    headers: { 'Content-Type': 'application/json', 'X-User-Id': String(userId) },
    body: body ? JSON.stringify(body) : undefined,
  })
  const data = await res.json().catch(() => ({}))
  if (!res.ok) throw { status: res.status, ...data }
  return data
}

export const api = {
  users: () => fetch(BASE + '/dev/users').then((r) => r.json()),
  login: (login) => call(0, 'POST', '/login', { login, password: PASSWORD }),
  balance: (u, year = 2026) => call(u, 'GET', `/balance?year=${year}`),
  submit: (u, body) => call(u, 'POST', '/requests', body),
  requests: (u) => call(u, 'GET', '/requests'),
  open: (u, id) => call(u, 'POST', `/requests/${id}/open`),
  approve: (u, id, comment) => call(u, 'POST', `/requests/${id}/approve`, { comment }),
  reject: (u, id, reason) => call(u, 'POST', `/requests/${id}/reject`, { reason }),
  cancel: (u, id) => call(u, 'POST', `/requests/${id}/cancel`),
  schedule: (u) => call(u, 'GET', '/schedule'),
  history: (u) => call(u, 'GET', '/history'),
  norms: (u) => call(u, 'GET', '/norms'),
  saveNorm: (u, type, daysPerYear) => call(u, 'PUT', `/norms/${type}`, { daysPerYear }),
  notifications: (u, markRead = false) => call(u, 'GET', `/notifications?mark_read=${markRead}`),
}

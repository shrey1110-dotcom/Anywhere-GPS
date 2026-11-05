async function call(path, opts = {}) {
  const r = await fetch(path, { headers: { 'Content-Type': 'application/json' }, ...opts })
  const body = await r.json().catch(() => ({}))
  if (!r.ok) throw Object.assign(new Error(body.message || `HTTP ${r.status}`), { hint: body.hint, code: body.code })
  return body
}
const post = (p, b) => call(p, { method: 'POST', body: JSON.stringify(b || {}) })
export const api = {
  health: () => call('/api/health'),
  devices: () => call('/api/devices'),
  readiness: (u) => call(`/api/devices/${encodeURIComponent(u)}/readiness`),
  mountImage: (u) => post(`/api/devices/${encodeURIComponent(u)}/developer-image/mount`),
  session: (u) => call('/api/session' + (u ? `?udid=${encodeURIComponent(u)}` : '')),
  setLocation: (udid, latitude, longitude) => post('/api/location', { udid, latitude, longitude }),
  restore: (udid) => post('/api/location/clear', { udid }),
  favorites: () => call('/api/favorites'),
  addFavorite: (name, latitude, longitude) => post('/api/favorites', { name, latitude, longitude }),
  delFavorite: (id) => call(`/api/favorites/${id}`, { method: 'DELETE' }),
  geocode: (q) => call(`/api/geocode?q=${encodeURIComponent(q)}`),
}

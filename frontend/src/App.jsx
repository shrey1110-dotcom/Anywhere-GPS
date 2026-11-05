import React, { useCallback, useEffect, useRef, useState } from 'react'
import L from 'leaflet'
import { api } from './api.js'

const PIN = L.divIcon({ className: 'pin', html: '<div></div>', iconSize: [22, 22], iconAnchor: [11, 22] })
const fmt = (n) => (n == null ? '' : Number(n).toFixed(6))

function MapView({ selected, active, onPick }) {
  const el = useRef(null), map = useRef(null), sel = useRef(null), act = useRef(null)
  useEffect(() => {
    map.current = L.map(el.current, { zoomControl: true }).setView([20, 0], 2)
    L.tileLayer('https://tile.openstreetmap.org/{z}/{x}/{y}.png', { maxZoom: 19, attribution: '© OpenStreetMap contributors' }).addTo(map.current)
    map.current.on('click', (e) => onPick(e.latlng.lat, e.latlng.lng))
    return () => map.current.remove()
  }, [])
  useEffect(() => {
    if (!map.current) return
    sel.current?.remove()
    if (selected) { sel.current = L.marker([selected.lat, selected.lon], { icon: PIN }).addTo(map.current); map.current.setView([selected.lat, selected.lon], Math.max(map.current.getZoom(), 12)) }
  }, [selected])
  useEffect(() => {
    act.current?.remove()
    if (active && map.current) act.current = L.circle([active.latitude, active.longitude], { radius: 120, color: '#16a34a', fillOpacity: 0.25 }).addTo(map.current)
  }, [active])
  return <div ref={el} className="map" />
}

export default function App() {
  const [health, setHealth] = useState(null)
  const [devices, setDevices] = useState([])
  const [udid, setUdid] = useState('')
  const [ready, setReady] = useState(null)
  const [session, setSession] = useState(null)
  const [sel, setSel] = useState(null)
  const [lat, setLat] = useState(''), [lon, setLon] = useState('')
  const [q, setQ] = useState(''), [results, setResults] = useState([])
  const [favs, setFavs] = useState([])
  const [err, setErr] = useState(null)
  const [busy, setBusy] = useState(false)
  const [backendDown, setBackendDown] = useState(false)

  const guard = async (fn) => { setBusy(true); setErr(null); try { return await fn() } catch (e) { setErr({ message: e.message, hint: e.hint }) } finally { setBusy(false) } }

  const poll = useCallback(async () => {
    try {
      const h = await api.health(); setHealth(h); setBackendDown(false)
      const d = (await api.devices()).devices; setDevices(d)
      const target = udid && d.some((x) => x.udid === udid) ? udid : d.length === 1 ? d[0].udid : ''
      if (target !== udid) setUdid(target)
      if (target) { setSession(await api.session(target)); setReady(await api.readiness(target)) } else { setSession(null); setReady(null) }
    } catch (e) { setBackendDown(true) }
  }, [udid])
  useEffect(() => { poll(); const t = setInterval(poll, 2500); return () => clearInterval(t) }, [poll])
  useEffect(() => { api.favorites().then(setFavs).catch(() => {}) }, [])

  const pick = (la, lo) => { setSel({ lat: la, lon: lo }); setLat(fmt(la)); setLon(fmt(lo)) }
  const manual = () => { const a = parseFloat(lat), b = parseFloat(lon); if (Number.isFinite(a) && Number.isFinite(b)) setSel({ lat: a, lon: b }) }
  const search = () => guard(async () => setResults(await api.geocode(q)))
  const apply = () => guard(async () => { setSession(await api.setLocation(udid || null, sel.lat, sel.lon)) })
  const restore = () => guard(async () => { setSession(await api.restore(udid || null)) })
  const [favName, setFavName] = useState('')
  const saveFav = () => guard(async () => { await api.addFavorite(favName || `${fmt(sel.lat)}, ${fmt(sel.lon)}`, sel.lat, sel.lon); setFavName(''); setFavs(await api.favorites()) })

  const active = session?.simulation_active
  const connLabel = backendDown ? 'Backend not running' : devices.length === 0 ? 'No iPhone connected' : devices.length > 1 && !udid ? 'Choose an iPhone' : ready?.ready ? 'iPhone ready' : 'iPhone needs setup'
  const connClass = backendDown || devices.length === 0 ? 'bad' : ready?.ready ? 'good' : 'warn'
  const dev = devices.find((d) => d.udid === udid)

  return (
    <div className="app">
      {health?.mock && <div className="mockbar">MOCK BACKEND — no real iPhone is being controlled</div>}
      <aside>
        <h1>Anywhere GPS</h1>
        <section>
          <div className={`status ${connClass}`}><span className="dot" />{connLabel}</div>
          {devices.length > 1 && (<select value={udid} onChange={(e) => setUdid(e.target.value)}><option value="">Select iPhone…</option>{devices.map((d) => <option key={d.udid} value={d.udid}>{d.name || d.udid}</option>)}</select>)}
          {dev && <div className="muted">{dev.name} · iOS {dev.ios_version || '?'}</div>}
          {ready && !ready.ready && ready.problems.map((p) => (<div className="problem" key={p.code}><b>{p.message}</b><div>{p.hint}</div>
            {p.code === 'developer_image_missing' && <button onClick={() => guard(() => api.mountImage(udid))} disabled={busy}>Mount developer image</button>}</div>))}
        </section>

        <section>
          <label>Search a place</label>
          <div className="row"><input value={q} placeholder="City or address" onChange={(e) => setQ(e.target.value)} onKeyDown={(e) => e.key === 'Enter' && search()} /><button onClick={search} disabled={busy}>Search</button></div>
          {results.map((r, i) => <div key={i} className="result" onClick={() => { pick(r.latitude, r.longitude); setResults([]) }}>{r.name}</div>)}
          <label>Coordinates</label>
          <div className="row"><input value={lat} placeholder="Latitude" onChange={(e) => setLat(e.target.value)} onBlur={manual} /><input value={lon} placeholder="Longitude" onChange={(e) => setLon(e.target.value)} onBlur={manual} /></div>
          <div className="muted">…or click anywhere on the map.</div>
        </section>

        <section>
          <button className="primary" disabled={!sel || busy || backendDown || !ready?.ready} onClick={apply}>Set Location</button>
          <button className="restore" disabled={busy || backendDown || !udid} onClick={restore}>Restore Real GPS</button>
          <div className="row"><input value={favName} placeholder="Favorite name (optional)" onChange={(e) => setFavName(e.target.value)} /><button className="ghost" disabled={!sel} onClick={saveFav}>★ Save</button></div>
        </section>

        <section>
          <label>Session</label>
          <div className={`state ${session?.state || 'idle'}`}>{session ? session.state.toUpperCase() : '—'}</div>
          {active && <div>Simulating <b>{fmt(session.target.latitude)}, {fmt(session.target.longitude)}</b></div>}
          {session?.state === 'lost' && <div className="problem"><b>Simulation is no longer active.</b> {session.error?.message}<div>{session.error?.hint}</div></div>}
          {session?.last_restore && session.state === 'idle' && <div className="note">{session.last_restore.message}{!session.last_restore.verified && ' (not yet verified)'}</div>}
          {err && <div className="problem"><b>{err.message}</b>{err.hint && <div>{err.hint}</div>}</div>}
        </section>

        {favs.length > 0 && <section><label>Favorites</label>{favs.map((f) => (<div className="fav" key={f.id}><span onClick={() => pick(f.latitude, f.longitude)}>{f.name}</span><button className="x" onClick={() => api.delFavorite(f.id).then(() => api.favorites().then(setFavs))}>×</button></div>))}</section>}
      </aside>
      <MapView selected={sel} active={active ? session.target : null} onPick={pick} />
    </div>
  )
}

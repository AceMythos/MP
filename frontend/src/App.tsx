import { useEffect, useMemo, useState, type FormEvent } from 'react'

type TabKey = 'dashboard' | 'upload' | 'alerts' | 'events' | 'users' | 'audit'

type DashboardOverview = {
  total_events: number
  total_alerts: number
  total_accounts: number
  high_alerts: number
  critical_alerts: number
  severity_breakdown: Record<string, number>
}

type AlertRow = {
  id: number
  rule_name: string
  severity: 'low' | 'medium' | 'high' | 'critical'
  risk_score: number
  created_at: string
  reason_codes: string[]
  event: { account: string | null; source_ip: string | null; url: string | null; occurred_at: string | null }
}

type EventRow = {
  id: number
  account: string | null
  group_name: string | null
  source_ip: string | null
  url: string | null
  port: number | null
  vlan: string | null
  switch_ip: string | null
  occurred_at: string | null
}

type UserRisk = {
  account: string
  event_count: number
  alert_count: number
  max_risk_score: number
  max_severity: string
  last_seen_at: string | null
}

type AuditLogRow = {
  id: number
  admin_username: string
  action: string
  details: string | null
  created_at: string
}

const API_BASE = 'http://127.0.0.1:8000'
const TABS: Array<{ key: TabKey; label: string }> = [
  { key: 'dashboard', label: 'Dashboard' },
  { key: 'upload', label: 'Upload' },
  { key: 'alerts', label: 'Alerts' },
  { key: 'events', label: 'Events' },
  { key: 'users', label: 'Users' },
  { key: 'audit', label: 'Audit' },
]

function App() {
  const [token, setToken] = useState<string | null>(null)
  const [username, setUsername] = useState('admin')
  const [password, setPassword] = useState('')
  const [loginError, setLoginError] = useState('')
  const [activeTab, setActiveTab] = useState<TabKey>('dashboard')
  const [health, setHealth] = useState<'loading' | 'ok' | 'down'>('loading')
  const [overview, setOverview] = useState<DashboardOverview | null>(null)
  const [alerts, setAlerts] = useState<AlertRow[]>([])
  const [events, setEvents] = useState<EventRow[]>([])
  const [users, setUsers] = useState<UserRisk[]>([])
  const [auditLogs, setAuditLogs] = useState<AuditLogRow[]>([])
  const [uploadStatus, setUploadStatus] = useState<string>('No file uploaded yet.')
  const [syntheticCount, setSyntheticCount] = useState(300)
  const [syntheticSeed, setSyntheticSeed] = useState('')
  const [uploading, setUploading] = useState(false)
  const [selectedAlert, setSelectedAlert] = useState<AlertRow | null>(null)
  const [alertSeverityFilter, setAlertSeverityFilter] = useState<'all' | AlertRow['severity']>('all')
  const [alertQuery, setAlertQuery] = useState('')
  const [eventQuery, setEventQuery] = useState('')

  useEffect(() => {
    void fetchHealth()
    if (token) {
      void refreshData(token)
    }
  }, [token])

  function getAuthHeaders(accessToken: string): Record<string, string> {
    return { Authorization: `Bearer ${accessToken}` }
  }

  async function fetchHealth() {
    try {
      const res = await fetch(`${API_BASE}/health`)
      setHealth(res.ok ? 'ok' : 'down')
    } catch {
      setHealth('down')
    }
  }

  async function refreshData(accessToken: string) {
    try {
      const headers = getAuthHeaders(accessToken)
      const [overviewRes, alertsRes, eventsRes, usersRes, auditRes] = await Promise.all([
        fetch(`${API_BASE}/dashboard/overview`, { headers }),
        fetch(`${API_BASE}/alerts?limit=20`, { headers }),
        fetch(`${API_BASE}/events?limit=20`, { headers }),
        fetch(`${API_BASE}/risk/users?limit=20`, { headers }),
        fetch(`${API_BASE}/admin/audit-logs?limit=30`, { headers }),
      ])
      if ([overviewRes, alertsRes, eventsRes, usersRes, auditRes].some((res) => res.status === 401)) {
        setToken(null)
        setLoginError('Session expired. Please log in again.')
        return
      }
      if (overviewRes.ok) setOverview((await overviewRes.json()) as DashboardOverview)
      if (alertsRes.ok) setAlerts((await alertsRes.json()) as AlertRow[])
      if (eventsRes.ok) setEvents((await eventsRes.json()) as EventRow[])
      if (usersRes.ok) setUsers((await usersRes.json()) as UserRisk[])
      if (auditRes.ok) setAuditLogs((await auditRes.json()) as AuditLogRow[])
    } catch {
      // keep current state
    }
  }

  async function onUpload(file: File) {
    if (!token) {
      setUploadStatus('Upload failed: not authenticated.')
      return
    }
    setUploading(true)
    setUploadStatus(`Uploading ${file.name}...`)
    try {
      const formData = new FormData()
      formData.append('file', file)
      const res = await fetch(`${API_BASE}/ingestions/csv`, {
        method: 'POST',
        body: formData,
        headers: getAuthHeaders(token),
      })
      const body = await res.json()
      if (!res.ok) {
        setUploadStatus(`Upload failed: ${body.detail || 'Unknown error'}`)
      } else {
        setUploadStatus(`Ingestion completed. Records: ${body.records_total}`)
        await refreshData(token)
      }
    } catch {
      setUploadStatus('Upload failed: backend unavailable.')
    } finally {
      setUploading(false)
    }
  }

  async function onGenerateSynthetic() {
    if (!token) {
      setUploadStatus('Synthetic generation failed: not authenticated.')
      return
    }
    setUploading(true)
    setUploadStatus(`Generating ${syntheticCount} synthetic events...`)
    try {
      const query = new URLSearchParams({ count: String(syntheticCount) })
      if (syntheticSeed.trim()) query.set('seed', syntheticSeed.trim())
      const res = await fetch(`${API_BASE}/ingestions/synthetic?${query.toString()}`, {
        method: 'POST',
        headers: getAuthHeaders(token),
      })
      const body = await res.json()
      if (!res.ok) {
        setUploadStatus(`Synthetic generation failed: ${body.detail || 'Unknown error'}`)
      } else {
        setUploadStatus(`Synthetic ingestion completed. Records: ${body.records_total}`)
        await refreshData(token)
      }
    } catch {
      setUploadStatus('Synthetic generation failed: backend unavailable.')
    } finally {
      setUploading(false)
    }
  }

  const topUsers = useMemo(() => users.slice(0, 5), [users])
  const recentAlerts = useMemo(() => alerts.slice(0, 6), [alerts])
  const severity = overview?.severity_breakdown ?? { low: 0, medium: 0, high: 0, critical: 0 }
  const filteredAlerts = useMemo(() => {
    return alerts
      .filter((a) => (alertSeverityFilter === 'all' ? true : a.severity === alertSeverityFilter))
      .filter((a) => {
        if (!alertQuery.trim()) return true
        const q = alertQuery.toLowerCase()
        return (
          a.rule_name.toLowerCase().includes(q) ||
          (a.event.account ?? '').toLowerCase().includes(q) ||
          (a.event.source_ip ?? '').toLowerCase().includes(q) ||
          a.reason_codes.join(' ').toLowerCase().includes(q)
        )
      })
  }, [alerts, alertSeverityFilter, alertQuery])

  const filteredEvents = useMemo(() => {
    return events.filter((e) => {
      if (!eventQuery.trim()) return true
      const q = eventQuery.toLowerCase()
      return (
        (e.account ?? '').toLowerCase().includes(q) ||
        (e.group_name ?? '').toLowerCase().includes(q) ||
        (e.source_ip ?? '').toLowerCase().includes(q) ||
        (e.url ?? '').toLowerCase().includes(q) ||
        (e.vlan ?? '').toLowerCase().includes(q)
      )
    })
  }, [events, eventQuery])

  async function onLoginSubmit(e: FormEvent) {
    e.preventDefault()
    setLoginError('')
    try {
      const response = await fetch(`${API_BASE}/auth/login`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ username, password }),
      })
      const body = await response.json()
      if (!response.ok) {
        setLoginError(body.detail || 'Invalid local admin credentials.')
        return
      }
      setToken(body.access_token as string)
      setPassword('')
    } catch {
      setLoginError('Backend unavailable.')
    }
  }

  if (!token) {
    return (
      <div className="login-page">
        <div className="login-card reveal">
          <p className="hero-kicker">AEGIS SOC ACCESS</p>
          <h1>Secure Operator Portal</h1>
          <p className="login-hint">Local admin mode for v1. Use your backend admin credentials.</p>
          <form onSubmit={onLoginSubmit}>
            <label>
              Username
              <input value={username} onChange={(e) => setUsername(e.target.value)} />
            </label>
            <label>
              Password
              <input type="password" value={password} onChange={(e) => setPassword(e.target.value)} />
            </label>
            {loginError && <div className="login-error">{loginError}</div>}
            <button className="login-btn" type="submit">Enter Command Center</button>
          </form>
        </div>
      </div>
    )
  }

  return (
    <div className="app-shell">
      <header className="globalbar">
        <div className="global-brand">AEGIS SOC</div>
        <nav className="global-nav">
          <button className="global-link">Search</button>
          <button className="global-link">Analytics</button>
          <button className="global-link">Reports</button>
          <button className="global-link">Alerts</button>
          <button className="global-link">Dashboards</button>
        </nav>
        <div className="global-tools">
          <button className="ghost-btn" onClick={() => token && void refreshData(token)}>Refresh</button>
          <button
            className="ghost-btn"
            onClick={() => {
              setToken(null)
              setAlerts([])
              setEvents([])
              setUsers([])
              setAuditLogs([])
              setOverview(null)
            }}
          >
            Logout
          </button>
          <div className={health === 'ok' ? 'health ok' : health === 'down' ? 'health down' : 'health'}>
            {health === 'ok' ? 'Backend Online' : health === 'down' ? 'Backend Offline' : 'Checking...'}
          </div>
        </div>
      </header>

      <main className="workspace">
        <div className="ambient-orb ambient-orb-a"></div>
        <div className="ambient-orb ambient-orb-b"></div>
        <header className="topbar reveal">
          <div>
            <h1>Sentinel Threat Command</h1>
            <p>Identity and network anomaly monitoring</p>
          </div>
          <div className="topbar-actions"></div>
        </header>
        <nav className="section-tabs reveal">
          {TABS.map((tab) => (
            <button key={tab.key} className={activeTab === tab.key ? 'nav-btn active' : 'nav-btn'} onClick={() => setActiveTab(tab.key)}>
              {tab.label}
            </button>
          ))}
        </nav>

        {activeTab === 'dashboard' && (
          <section className="panel-grid reveal">
            <div className="hero-rail">
              <div>
                <p className="hero-kicker">SOC LIVE GRID</p>
                <h2 className="hero-title">Operational Threat Posture</h2>
              </div>
              <div className="hero-meta">
                <span>Rules + Isolation Forest</span>
                <span>Local Mode</span>
              </div>
            </div>
            <div className="kpi"><span>Total Events</span><strong>{overview?.total_events ?? 0}</strong></div>
            <div className="kpi"><span>Total Alerts</span><strong>{overview?.total_alerts ?? 0}</strong></div>
            <div className="kpi high"><span>High Alerts</span><strong>{overview?.high_alerts ?? 0}</strong></div>
            <div className="kpi critical"><span>Critical Alerts</span><strong>{overview?.critical_alerts ?? 0}</strong></div>
            <div className="card wide">
              <h2>Severity Distribution</h2>
              <div className="severity-bars">
                <div><label>Low</label><progress max={Math.max(1, overview?.total_alerts ?? 1)} value={severity.low}></progress><span>{severity.low}</span></div>
                <div><label>Medium</label><progress max={Math.max(1, overview?.total_alerts ?? 1)} value={severity.medium}></progress><span>{severity.medium}</span></div>
                <div><label>High</label><progress max={Math.max(1, overview?.total_alerts ?? 1)} value={severity.high}></progress><span>{severity.high}</span></div>
                <div><label>Critical</label><progress max={Math.max(1, overview?.total_alerts ?? 1)} value={severity.critical}></progress><span>{severity.critical}</span></div>
              </div>
            </div>
            <div className="card">
              <h2>Top Risky Users</h2>
              {topUsers.map((u) => (
                <div key={u.account} className="row"><span>{u.account}</span><strong>{u.max_risk_score}</strong></div>
              ))}
            </div>
            <div className="card">
              <h2>Recent Alerts</h2>
              {recentAlerts.map((a) => (
                <div key={a.id} className="row"><span>{a.event.account ?? 'unknown'}</span><strong>{a.severity}</strong></div>
              ))}
            </div>
          </section>
        )}

        {activeTab === 'upload' && (
          <section className="card full reveal">
            <h2>CSV Ingestion</h2>
            <label className="upload-zone">
              <input type="file" accept=".csv" onChange={(e) => e.target.files?.[0] && void onUpload(e.target.files[0])} />
              <span>{uploading ? 'Processing...' : 'Drop CSV or click to upload'}</span>
              <small>Required columns: id, account, group, IP, url, port, vlan, switchIP, time</small>
            </label>
            <p className="status">{uploadStatus}</p>
            <hr />
            <h2>Synthetic UEBA Generation</h2>
            <div className="toolbar synthetic-controls">
              <input
                type="number"
                min={1}
                max={5000}
                value={syntheticCount}
                onChange={(e) => setSyntheticCount(Number(e.target.value) || 1)}
                className="search-input"
                placeholder="Event count"
              />
              <input
                value={syntheticSeed}
                onChange={(e) => setSyntheticSeed(e.target.value)}
                className="search-input"
                placeholder="Seed (optional)"
              />
              <button className="login-btn" disabled={uploading} onClick={() => void onGenerateSynthetic()}>
                {uploading ? 'Processing...' : 'Generate Synthetic Events'}
              </button>
            </div>
          </section>
        )}

        {activeTab === 'alerts' && (
          <section className="card full reveal">
            <div className="section-head">
              <h2>Alerts Triage</h2>
              <div className="chip-group">
                {(['all', 'critical', 'high', 'medium', 'low'] as const).map((opt) => (
                  <button
                    key={opt}
                    className={alertSeverityFilter === opt ? 'chip active' : 'chip'}
                    onClick={() => setAlertSeverityFilter(opt)}
                  >
                    {opt}
                  </button>
                ))}
              </div>
            </div>
            <div className="toolbar">
              <input
                className="search-input"
                placeholder="Search account, IP, rule, reason..."
                value={alertQuery}
                onChange={(e) => setAlertQuery(e.target.value)}
              />
            </div>
            <table>
              <thead><tr><th>Severity</th><th>Risk</th><th>Rule</th><th>Account</th><th>IP</th><th>Time</th></tr></thead>
              <tbody>
                {filteredAlerts.map((a) => (
                  <tr key={a.id} onClick={() => setSelectedAlert(a)}>
                    <td><span className={`badge ${a.severity}`}>{a.severity}</span></td>
                    <td>{a.risk_score}</td>
                    <td>{a.rule_name}</td>
                    <td>{a.event.account ?? 'unknown'}</td>
                    <td className="mono">{a.event.source_ip ?? '-'}</td>
                    <td>{new Date(a.created_at).toLocaleString()}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </section>
        )}

        {activeTab === 'events' && (
          <section className="card full reveal">
            <h2>Raw Event Explorer</h2>
            <div className="toolbar">
              <input
                className="search-input"
                placeholder="Search account, group, IP, URL, VLAN..."
                value={eventQuery}
                onChange={(e) => setEventQuery(e.target.value)}
              />
            </div>
            <table>
              <thead><tr><th>Account</th><th>Group</th><th>IP</th><th>URL</th><th>Port</th><th>VLAN</th></tr></thead>
              <tbody>
                {filteredEvents.map((e) => (
                  <tr key={e.id}>
                    <td>{e.account ?? 'unknown'}</td><td>{e.group_name ?? '-'}</td><td className="mono">{e.source_ip ?? '-'}</td><td>{e.url ?? '-'}</td><td className="mono">{e.port ?? '-'}</td><td className="mono">{e.vlan ?? '-'}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </section>
        )}

        {activeTab === 'users' && (
          <section className="card full reveal">
            <h2>User Risk Ranking</h2>
            <table>
              <thead><tr><th>Account</th><th>Events</th><th>Alerts</th><th>Max Risk</th><th>Severity</th></tr></thead>
              <tbody>
                {users.map((u) => (
                  <tr key={u.account}>
                    <td>{u.account}</td><td className="mono">{u.event_count}</td><td className="mono">{u.alert_count}</td><td className="mono">{u.max_risk_score}</td><td><span className={`badge ${u.max_severity}`}>{u.max_severity}</span></td>
                  </tr>
                ))}
              </tbody>
            </table>
          </section>
        )}

        {activeTab === 'audit' && (
          <section className="card full reveal">
            <h2>Admin Audit Log</h2>
            <table>
              <thead><tr><th>Time</th><th>Admin</th><th>Action</th><th>Details</th></tr></thead>
              <tbody>
                {auditLogs.map((log) => (
                  <tr key={log.id}>
                    <td>{new Date(log.created_at).toLocaleString()}</td>
                    <td>{log.admin_username}</td>
                    <td>{log.action}</td>
                    <td className="mono">{log.details ?? '-'}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </section>
        )}
      </main>

      {selectedAlert && (
        <aside className="drawer reveal">
          <button className="close" onClick={() => setSelectedAlert(null)}>Close</button>
          <h3>Alert #{selectedAlert.id}</h3>
          <p><strong>Rule:</strong> {selectedAlert.rule_name}</p>
          <p><strong>Risk:</strong> {selectedAlert.risk_score}</p>
          <p><strong>Reasons:</strong> {selectedAlert.reason_codes.join(', ')}</p>
          <p><strong>URL:</strong> {selectedAlert.event.url ?? '-'}</p>
        </aside>
      )}
    </div>
  )
}

export default App

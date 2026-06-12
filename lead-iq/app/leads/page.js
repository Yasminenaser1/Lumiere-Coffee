'use client';

import { useState, useEffect, useCallback } from 'react';

/* ── helpers ── */
function scoreColor(s) {
  if (s >= 8) return '#22c55e';
  if (s >= 5) return '#f59e0b';
  if (s > 0)  return '#ef4444';
  return '#404060';
}

function statusStyle(status) {
  const map = {
    New:       { bg: '#1e1e38', color: '#a0a0cc', border: '#3a3a5c' },
    Contacted: { bg: '#1a2a44', color: '#60a5fa', border: '#2a4a7a' },
    Qualified: { bg: '#0f2d1f', color: '#4ade80', border: '#1a5a35' },
    Closed:    { bg: '#2d1a1a', color: '#f87171', border: '#5a2a2a' },
  };
  return map[status] || map.New;
}

const STATUSES = ['New', 'Contacted', 'Qualified', 'Closed'];
const SIZES    = ['1–5', '6–20', '21–50', '51–200', '200+'];

/* ── Add Lead Modal ── */
function AddLeadModal({ onClose, onAdded }) {
  const [form, setForm] = useState({
    company: '', contact_name: '', email: '', title: '', company_size: '', notes: '',
  });
  const [saving, setSaving] = useState(false);
  const [err, setErr] = useState('');

  async function submit(e) {
    e.preventDefault();
    if (!form.company.trim() || !form.contact_name.trim()) {
      setErr('Company and Contact name are required.');
      return;
    }
    setSaving(true);
    const res = await fetch('/api/leads', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(form),
    });
    const data = await res.json();
    setSaving(false);
    if (!res.ok) { setErr(data.error || 'Save failed'); return; }
    onAdded(data);
    onClose();
  }

  const field = (label, key, type = 'text', placeholder = '') => (
    <label style={st.label}>
      <span style={st.labelText}>{label}</span>
      <input
        type={type}
        value={form[key]}
        onChange={e => setForm(f => ({ ...f, [key]: e.target.value }))}
        placeholder={placeholder}
        style={st.input}
      />
    </label>
  );

  return (
    <div style={st.overlay} onClick={onClose}>
      <div style={st.modal} onClick={e => e.stopPropagation()}>
        <div style={st.modalHeader}>
          <h2 style={st.modalTitle}>Add New Lead</h2>
          <button style={st.closeBtn} onClick={onClose}>✕</button>
        </div>

        <form onSubmit={submit} style={st.form}>
          <div style={st.row2}>
            {field('Company *', 'company', 'text', 'Blue Bottle Coffee')}
            {field('Contact Name *', 'contact_name', 'text', 'Jane Smith')}
          </div>
          <div style={st.row2}>
            {field('Email', 'email', 'email', 'jane@example.com')}
            {field('Title', 'title', 'text', 'Founder / Head of Ops')}
          </div>

          <label style={st.label}>
            <span style={st.labelText}>Company Size</span>
            <select
              value={form.company_size}
              onChange={e => setForm(f => ({ ...f, company_size: e.target.value }))}
              style={st.input}
            >
              <option value="">Select…</option>
              {SIZES.map(s => <option key={s} value={s}>{s} employees</option>)}
            </select>
          </label>

          <label style={st.label}>
            <span style={st.labelText}>Notes</span>
            <textarea
              value={form.notes}
              onChange={e => setForm(f => ({ ...f, notes: e.target.value }))}
              placeholder="Any context about this lead…"
              rows={3}
              style={{ ...st.input, resize: 'vertical' }}
            />
          </label>

          {err && <p style={{ color: '#ef4444', fontSize: 12 }}>{err}</p>}

          <div style={st.modalFooter}>
            <button type="button" style={st.cancelBtn} onClick={onClose}>Cancel</button>
            <button type="submit" style={st.saveBtn} disabled={saving}>
              {saving ? 'Saving…' : 'Add Lead'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

/* ── Score Badge ── */
function ScoreBadge({ score }) {
  const color = scoreColor(score);
  if (!score) return <span style={{ color: '#404060', fontSize: 12 }}>—</span>;
  return (
    <span style={{
      display: 'inline-flex', alignItems: 'center', justifyContent: 'center',
      width: 36, height: 36, borderRadius: '50%',
      background: color + '22', border: `2px solid ${color}`,
      color, fontWeight: 700, fontSize: 13,
    }}>{score}</span>
  );
}

/* ── Main Page ── */
export default function LeadsPage() {
  const [leads, setLeads]       = useState([]);
  const [loading, setLoading]   = useState(true);
  const [showAdd, setShowAdd]   = useState(false);
  const [filter, setFilter]     = useState('All');
  const [scoring, setScoring]   = useState(null); // id being scored
  const [tooltip, setTooltip]   = useState(null); // { id, reason }

  const load = useCallback(async () => {
    setLoading(true);
    const res  = await fetch('/api/leads');
    const data = await res.json();
    setLeads(data);
    setLoading(false);
  }, []);

  useEffect(() => { load(); }, [load]);

  async function analyze(lead) {
    setScoring(lead.id);
    const res  = await fetch('/api/leads/score', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ leadId: lead.id }),
    });
    const data = await res.json();
    if (data.lead) {
      setLeads(prev => prev.map(l => l.id === lead.id ? data.lead : l));
    }
    setScoring(null);
    if (data.reason) setTooltip({ id: lead.id, reason: data.reason });
  }

  async function changeStatus(lead, status) {
    const res  = await fetch(`/api/leads/${lead.id}`, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ status }),
    });
    const data = await res.json();
    setLeads(prev => prev.map(l => l.id === lead.id ? data : l));
  }

  async function deleteLead(id) {
    if (!confirm('Delete this lead?')) return;
    await fetch(`/api/leads/${id}`, { method: 'DELETE' });
    setLeads(prev => prev.filter(l => l.id !== id));
  }

  const visible  = filter === 'All' ? leads : leads.filter(l => l.status === filter);
  const totals   = {
    all:       leads.length,
    newL:      leads.filter(l => l.status === 'New').length,
    qualified: leads.filter(l => l.status === 'Qualified').length,
    avgScore:  leads.filter(l => l.score > 0).length
      ? (leads.filter(l => l.score > 0).reduce((a, l) => a + l.score, 0) /
         leads.filter(l => l.score > 0).length).toFixed(1)
      : '—',
  };

  return (
    <div style={st.page}>
      {/* ── Header ── */}
      <header style={st.header}>
        <div style={st.headerLeft}>
          <div style={st.logo}>
            <span style={st.logoIcon}>⚡</span>
            <span style={st.logoText}>LEAD IQ</span>
          </div>
          <span style={st.logoSub}>Coffee Shop Pipeline</span>
        </div>
        <button style={st.addBtn} onClick={() => setShowAdd(true)}>+ Add Lead</button>
      </header>

      {/* ── Stat bar ── */}
      <div style={st.statBar}>
        {[
          { label: 'Total Leads',  val: totals.all },
          { label: 'New',          val: totals.newL },
          { label: 'Qualified',    val: totals.qualified },
          { label: 'Avg AI Score', val: totals.avgScore },
        ].map(s => (
          <div key={s.label} style={st.statCard}>
            <div style={st.statVal}>{s.val}</div>
            <div style={st.statLabel}>{s.label}</div>
          </div>
        ))}
      </div>

      {/* ── Filter tabs ── */}
      <div style={st.tabs}>
        {['All', ...STATUSES].map(t => (
          <button
            key={t}
            style={{ ...st.tab, ...(filter === t ? st.tabActive : {}) }}
            onClick={() => setFilter(t)}
          >
            {t}
            {t !== 'All' && (
              <span style={st.tabCount}>
                {leads.filter(l => l.status === t).length}
              </span>
            )}
          </button>
        ))}
      </div>

      {/* ── Table ── */}
      <div style={st.tableWrap}>
        {loading ? (
          <div style={st.empty}>Loading…</div>
        ) : visible.length === 0 ? (
          <div style={st.empty}>
            {leads.length === 0
              ? 'No leads yet — click "+ Add Lead" to get started.'
              : `No leads with status "${filter}".`}
          </div>
        ) : (
          <table style={st.table}>
            <thead>
              <tr>
                {['Company', 'Contact', 'Size', 'Score', 'Status', 'Actions'].map(h => (
                  <th key={h} style={st.th}>{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {visible.map(lead => {
                const ss = statusStyle(lead.status);
                return (
                  <tr key={lead.id} style={st.tr}>
                    <td style={st.td}>
                      <div style={st.company}>{lead.company}</div>
                      {lead.notes && (
                        <div style={st.notes}>{lead.notes.slice(0, 60)}{lead.notes.length > 60 ? '…' : ''}</div>
                      )}
                    </td>
                    <td style={st.td}>
                      <div style={st.contactName}>{lead.contact_name}</div>
                      {lead.title && <div style={st.contactSub}>{lead.title}</div>}
                      {lead.email && <div style={st.contactSub}>{lead.email}</div>}
                    </td>
                    <td style={{ ...st.td, textAlign: 'center', color: '#8080a0' }}>
                      {lead.company_size || '—'}
                    </td>
                    <td style={{ ...st.td, textAlign: 'center' }}>
                      <div style={{ position: 'relative', display: 'inline-block' }}>
                        <div
                          onMouseEnter={() => lead.score_reason && setTooltip({ id: lead.id, reason: lead.score_reason })}
                          onMouseLeave={() => setTooltip(null)}
                        >
                          <ScoreBadge score={lead.score} />
                        </div>
                        {tooltip?.id === lead.id && (
                          <div style={st.scoreTooltip}>{tooltip.reason}</div>
                        )}
                      </div>
                    </td>
                    <td style={st.td}>
                      <select
                        value={lead.status}
                        onChange={e => changeStatus(lead, e.target.value)}
                        style={{
                          background: ss.bg,
                          color: ss.color,
                          border: `1px solid ${ss.border}`,
                          padding: '4px 8px',
                          borderRadius: 6,
                          fontSize: 12,
                          fontWeight: 600,
                          cursor: 'pointer',
                        }}
                      >
                        {STATUSES.map(s => <option key={s} value={s}>{s}</option>)}
                      </select>
                    </td>
                    <td style={{ ...st.td, whiteSpace: 'nowrap' }}>
                      <button
                        style={st.analyzeBtn}
                        onClick={() => analyze(lead)}
                        disabled={scoring === lead.id}
                      >
                        {scoring === lead.id ? '…' : '⚡ Analyze'}
                      </button>
                      <button
                        style={st.deleteBtn}
                        onClick={() => deleteLead(lead.id)}
                      >
                        ✕
                      </button>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        )}
      </div>

      {showAdd && (
        <AddLeadModal
          onClose={() => setShowAdd(false)}
          onAdded={lead => setLeads(prev => [lead, ...prev])}
        />
      )}
    </div>
  );
}

/* ── Styles ── */
const st = {
  page: {
    minHeight: '100vh',
    background: '#0b0b14',
    color: '#e8e8f0',
    padding: '0 0 60px',
  },
  header: {
    display: 'flex', alignItems: 'center', justifyContent: 'space-between',
    padding: '20px 32px',
    borderBottom: '1px solid #1e1e30',
    background: '#0d0d1a',
  },
  headerLeft: { display: 'flex', alignItems: 'center', gap: 16 },
  logo: { display: 'flex', alignItems: 'center', gap: 8 },
  logoIcon: { fontSize: 22 },
  logoText: {
    fontSize: 20, fontWeight: 800, letterSpacing: '0.08em',
    background: 'linear-gradient(135deg, #a78bfa, #60a5fa)',
    WebkitBackgroundClip: 'text', WebkitTextFillColor: 'transparent',
  },
  logoSub: { color: '#5050708', fontSize: 13, color: '#505070', marginTop: 2 },
  addBtn: {
    background: 'linear-gradient(135deg, #7c6cff, #5b8ff0)',
    color: '#fff', fontWeight: 600, padding: '9px 18px',
    borderRadius: 8, fontSize: 13,
  },

  statBar: {
    display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)',
    gap: 16, padding: '20px 32px',
    borderBottom: '1px solid #1e1e30',
  },
  statCard: {
    background: '#13131f', border: '1px solid #2a2a40',
    borderRadius: 10, padding: '14px 20px',
  },
  statVal:   { fontSize: 26, fontWeight: 700, color: '#e8e8f0' },
  statLabel: { fontSize: 12, color: '#6060808', color: '#606080', marginTop: 2 },

  tabs: {
    display: 'flex', gap: 4, padding: '16px 32px 0',
    borderBottom: '1px solid #1e1e30',
  },
  tab: {
    background: 'none', color: '#8080a0',
    padding: '8px 14px', borderRadius: '6px 6px 0 0',
    fontWeight: 500, display: 'flex', alignItems: 'center', gap: 6,
    border: '1px solid transparent', borderBottom: 'none',
    marginBottom: -1,
  },
  tabActive: {
    background: '#13131f', color: '#e8e8f0',
    borderColor: '#2a2a40',
  },
  tabCount: {
    background: '#2a2a40', color: '#8080a0',
    fontSize: 11, fontWeight: 600, borderRadius: 10,
    padding: '1px 6px',
  },

  tableWrap: {
    margin: '0 32px',
    background: '#13131f',
    border: '1px solid #2a2a40',
    borderRadius: '0 8px 8px 8px',
    overflow: 'auto',
  },
  empty: {
    padding: '60px 0', textAlign: 'center',
    color: '#606080', fontSize: 14,
  },
  table: {
    width: '100%', borderCollapse: 'collapse',
  },
  th: {
    textAlign: 'left', padding: '12px 16px',
    fontSize: 11, fontWeight: 600, color: '#606080',
    letterSpacing: '0.06em', textTransform: 'uppercase',
    borderBottom: '1px solid #2a2a40',
    background: '#0f0f1e',
  },
  tr: {
    borderBottom: '1px solid #1a1a2e',
    transition: 'background 0.1s',
  },
  td: {
    padding: '14px 16px', verticalAlign: 'middle',
  },
  company:    { fontWeight: 600, fontSize: 14, color: '#d0d0e8' },
  notes:      { fontSize: 11, color: '#606080', marginTop: 3 },
  contactName:{ fontSize: 13, fontWeight: 500 },
  contactSub: { fontSize: 11, color: '#606080', marginTop: 2 },

  scoreTooltip: {
    position: 'absolute', bottom: '110%', left: '50%',
    transform: 'translateX(-50%)',
    background: '#1c1c2e', border: '1px solid #3a3a5a',
    borderRadius: 6, padding: '6px 10px',
    fontSize: 11, color: '#c0c0e0',
    whiteSpace: 'nowrap', maxWidth: 260, whiteSpace: 'normal',
    zIndex: 100, pointerEvents: 'none',
    boxShadow: '0 4px 12px rgba(0,0,0,0.5)',
  },

  analyzeBtn: {
    background: '#1c1c38', color: '#a0a0ff',
    border: '1px solid #3a3a60',
    padding: '5px 12px', borderRadius: 6,
    fontSize: 12, fontWeight: 600,
    marginRight: 6,
  },
  deleteBtn: {
    background: 'none', color: '#404060',
    border: '1px solid #2a2a40',
    padding: '5px 10px', borderRadius: 6,
    fontSize: 12,
  },

  /* Modal */
  overlay: {
    position: 'fixed', inset: 0,
    background: 'rgba(0,0,0,0.7)', backdropFilter: 'blur(4px)',
    display: 'flex', alignItems: 'center', justifyContent: 'center',
    zIndex: 1000,
  },
  modal: {
    background: '#13131f', border: '1px solid #2a2a40',
    borderRadius: 12, width: 540, maxWidth: '95vw',
    boxShadow: '0 20px 60px rgba(0,0,0,0.6)',
  },
  modalHeader: {
    display: 'flex', alignItems: 'center', justifyContent: 'space-between',
    padding: '20px 24px 0',
  },
  modalTitle: { fontSize: 16, fontWeight: 700 },
  closeBtn: {
    background: 'none', color: '#606080',
    fontSize: 16, padding: '4px 8px', borderRadius: 6,
  },
  form: { padding: '16px 24px 24px', display: 'flex', flexDirection: 'column', gap: 12 },
  row2: { display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12 },
  label: { display: 'flex', flexDirection: 'column', gap: 4 },
  labelText: { fontSize: 12, fontWeight: 500, color: '#8080a0' },
  input: { width: '100%' },
  modalFooter: { display: 'flex', justifyContent: 'flex-end', gap: 8, marginTop: 4 },
  cancelBtn: {
    background: 'none', color: '#8080a0',
    border: '1px solid #2a2a40', padding: '8px 16px', borderRadius: 6,
  },
  saveBtn: {
    background: 'linear-gradient(135deg, #7c6cff, #5b8ff0)',
    color: '#fff', fontWeight: 600, padding: '8px 20px', borderRadius: 6,
  },
};

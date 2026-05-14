import { useState, useEffect } from 'react';
import EDADatasetView from './EDADatasetView';
import EDAOverview from './EDAOverview';

export default function EDATab({ datasets }) {
  const [active, setActive] = useState(datasets[0]?.id || 'overview');
  const [reports, setReports] = useState({});
  const [loading, setLoading] = useState(false);
  const [err, setErr] = useState('');

  useEffect(() => {
    const allIds = [...datasets.map(d => d.id), 'overview'];
    if (!allIds.includes(active)) setActive(datasets[0]?.id || 'overview');
  }, [datasets]);

  useEffect(() => {
    if (!datasets.length) return;
    setLoading(true);
    setErr('');
    fetch(`/api/eda?datasets=${encodeURIComponent(datasets.map(d => d.id).join(','))}`)
      .then(r => r.ok ? r.json() : Promise.reject(new Error(`HTTP ${r.status}`)))
      .then(setReports)
      .catch(e => setErr(e.message))
      .finally(() => setLoading(false));
  }, [datasets]);

  const tabs = [...datasets, { id: 'overview', name: 'Обзор ▾' }];

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100%', overflow: 'hidden' }}>
      <div style={{ flexShrink: 0, background: 'var(--surf)', borderBottom: '1px solid var(--border)', padding: '0 24px', display: 'flex', gap: 0, overflowX: 'auto' }}>
        {tabs.map(t => (
          <div
            key={t.id}
            onClick={() => setActive(t.id)}
            style={{
              padding: '9px 16px', cursor: 'pointer', fontSize: 11, fontWeight: 600, whiteSpace: 'nowrap',
              borderBottom: `2px solid ${active === t.id ? 'var(--accent)' : 'transparent'}`,
              color: active === t.id ? 'var(--accent)' : 'var(--text2)',
              transition: 'all .15s',
            }}
          >
            {t.name}
          </div>
        ))}
      </div>
      <div style={{ flex: 1, overflow: 'hidden' }}>
        {loading && <div style={{ padding: 24, color: 'var(--muted)', fontFamily: 'IBM Plex Mono', fontSize: 12 }}>EDA считается…</div>}
        {err && <div style={{ padding: 24, color: 'var(--red)', fontFamily: 'IBM Plex Mono', fontSize: 12 }}>{err}</div>}
        {!loading && !err && (active === 'overview'
          ? <EDAOverview datasets={datasets} reports={reports} />
          : <EDADatasetView key={active} datasetId={active} report={reports[active]} />
        )}
      </div>
    </div>
  );
}

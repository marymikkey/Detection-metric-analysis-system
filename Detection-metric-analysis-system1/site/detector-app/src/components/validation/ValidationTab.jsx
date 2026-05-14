import { useState, useMemo } from 'react';
import Card from '../ui/Card';
import MonoLabel from '../ui/MonoLabel';

export default function ValidationTab({ datasets, models, valCfg, onComplete }) {
  const jobs = useMemo(() => datasets.flatMap(d => models.map(m => ({
    id: `${m.id}__${d.id}`, modelId: m.id, datasetId: d.id, modelName: m.name, datasetName: d.name,
  }))), []);

  const [statuses, setStatuses] = useState(() =>
    Object.fromEntries(jobs.map(j => [j.id, { phase: -1, pct: 0, phaseLabel: '' }]))
  );
  const [currentIdx, setCurrentIdx] = useState(-1);
  const [done, setDone] = useState(false);
  const [started, setStarted] = useState(false);
  const [log, setLog] = useState('');
  const [err, setErr] = useState('');

  function updateJob(id, upd) {
    setStatuses(prev => ({ ...prev, [id]: { ...prev[id], ...upd } }));
  }

  async function runValidation() {
    setStarted(true);
    setCurrentIdx(0);
    jobs.forEach(j => updateJob(j.id, { phase: 2, pct: 25, phaseLabel: 'Запуск eval_all_coco.py' }));
    try {
      const r = await fetch('/api/validation', { method: 'POST' });
      const data = await r.json();
      setLog((data.stdout || '') + (data.stderr ? `\n${data.stderr}` : ''));
      if (!data.ok) throw new Error(data.stderr || data.stdout || 'validation failed');
      const rr = await fetch('/api/results');
      const rd = await rr.json();
      const out = {};
      const selectedJobIds = new Set(jobs.map(j => j.id));
      (rd.rows || []).forEach(row => {
        const id = `${row.modelId}__${row.datasetId}`;
        if (selectedJobIds.has(id)) out[id] = row;
      });
      jobs.forEach(j => updateJob(j.id, { phase: 4, pct: 100, phaseLabel: 'Готово', metrics: out[`${j.modelId}__${j.datasetId}`]?.metrics }));
      setDone(true);
      setTimeout(() => onComplete(out), 700);
    } catch (e) {
      setErr(e.message);
      jobs.forEach(j => updateJob(j.id, { phase: 0, pct: 0, phaseLabel: 'Ошибка' }));
    }
  }

  const completedCount = jobs.filter(j => statuses[j.id].phase >= 4).length;
  const overallPct = jobs.length ? Math.round(completedCount / jobs.length * 100) : 0;

  return (
    <div style={{ padding: '18px 24px 40px', overflowY: 'auto', height: '100%' }}>
      {!started && (
        <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', height: '65%', gap: 24, animation: 'fadeIn .3s ease' }}>
          <div style={{ textAlign: 'center' }}>
            <div style={{ fontFamily: 'Syne', fontSize: 26, fontWeight: 800, marginBottom: 10 }}>Готово к валидации</div>
            <div style={{ color: 'var(--text2)', fontSize: 13, lineHeight: 2 }}>
              <span style={{ color: 'var(--accent)' }}>{models.length} мод.</span>{' × '}
              <span style={{ color: 'var(--green)' }}>{datasets.length} датас.</span>{' = '}
              <span style={{ color: 'var(--amber)', fontFamily: 'Syne', fontWeight: 800, fontSize: 18 }}>{jobs.length}</span>{' заданий'}
            </div>
            <div style={{ display: 'flex', justifyContent: 'center', gap: 6, marginTop: 12, flexWrap: 'wrap' }}>
              {models.map(m => <span key={m.id} style={{ fontFamily: 'IBM Plex Mono', fontSize: 10, padding: '3px 10px', background: 'var(--accent-dim)', color: 'var(--accent)', borderRadius: 20 }}>{m.name}</span>)}
              {datasets.map(d => <span key={d.id} style={{ fontFamily: 'IBM Plex Mono', fontSize: 10, padding: '3px 10px', background: 'rgba(74,222,128,.08)', color: 'var(--green)', borderRadius: 20 }}>{d.name}</span>)}
            </div>
          </div>
          <button
            onClick={runValidation}
            style={{ padding: '13px 42px', background: 'var(--accent)', color: '#fff', border: 'none', borderRadius: 8, fontFamily: 'Syne', fontSize: 15, fontWeight: 800, letterSpacing: '.05em', cursor: 'pointer', boxShadow: '0 0 32px var(--accent-glow)' }}
          >
            ▶ ЗАПУСТИТЬ ВАЛИДАЦИЮ
          </button>
        </div>
      )}

      {started && (
        <div style={{ animation: 'fadeIn .3s ease', maxWidth: 920, margin: '0 auto' }}>
          <Card style={{ padding: '18px 22px', marginBottom: 16 }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 14, marginBottom: 12 }}>
              <div style={{ fontFamily: 'Syne', fontWeight: 800, fontSize: 24 }}>{completedCount}/{jobs.length}</div>
              <div style={{ fontSize: 12, color: 'var(--text2)' }}>заданий завершено</div>
              <div style={{ marginLeft: 'auto' }}>
                <span style={{ fontFamily: 'IBM Plex Mono', fontSize: 14, color: 'var(--accent)', fontWeight: 600 }}>{overallPct}%</span>
              </div>
            </div>
            <div style={{ height: 6, background: 'var(--surf2)', borderRadius: 3, overflow: 'hidden' }}>
              <div style={{ height: '100%', width: `${overallPct}%`, background: 'linear-gradient(90deg,var(--accent),var(--green))', borderRadius: 3, transition: 'width .4s', boxShadow: '0 0 12px var(--accent-glow)' }} />
            </div>
            {done && <div style={{ marginTop: 10, fontFamily: 'IBM Plex Mono', fontSize: 11, color: 'var(--green)' }}>✓ Все задания завершены — переход к результатам…</div>}
            {err && <div style={{ marginTop: 10, fontFamily: 'IBM Plex Mono', fontSize: 11, color: 'var(--red)', whiteSpace: 'pre-wrap' }}>{err}</div>}
            {log && <pre style={{ marginTop: 10, maxHeight: 220, overflow: 'auto', fontSize: 9, color: 'var(--muted)', whiteSpace: 'pre-wrap' }}>{log}</pre>}
          </Card>

          <Card style={{ padding: '16px 22px' }}>
            <MonoLabel style={{ marginBottom: 14 }}>Прогресс по заданиям</MonoLabel>
            <div style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
              {jobs.map((j, i) => {
                const st = statuses[j.id];
                const isDone = st.phase >= 4, isRun = currentIdx === i && !isDone, isPend = st.phase < 0;
                const barClr = isDone ? 'var(--green)' : isRun ? 'var(--accent)' : 'var(--border2)';
                return (
                  <div key={j.id}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 6 }}>
                      <div style={{ width: 8, height: 8, borderRadius: '50%', background: isDone ? 'var(--green)' : isRun ? 'var(--accent)' : 'var(--dim)', animation: isRun ? 'pulse 1s infinite' : 'none', flexShrink: 0 }} />
                      <span style={{ fontFamily: 'Syne', fontWeight: 700, fontSize: 12, color: isDone ? 'var(--green)' : isRun ? 'var(--accent)' : 'var(--text)' }}>{j.modelName}</span>
                      <span style={{ fontFamily: 'IBM Plex Mono', fontSize: 10, color: 'var(--muted)' }}>×</span>
                      <span style={{ fontFamily: 'IBM Plex Mono', fontSize: 11, color: 'var(--text2)' }}>{j.datasetName}</span>
                      <div style={{ marginLeft: 'auto', display: 'flex', alignItems: 'center', gap: 8 }}>
                        {isPend && <span style={{ fontSize: 10, color: 'var(--dim)', fontFamily: 'IBM Plex Mono' }}>ожидание</span>}
                        {isRun && <span style={{ fontSize: 10, color: 'var(--accent)', fontFamily: 'IBM Plex Mono', animation: 'pulse 1s infinite' }}>{st.phaseLabel}…</span>}
                        {isDone && <span style={{ fontSize: 10, color: 'var(--green)', fontFamily: 'IBM Plex Mono' }}>✓ Готово</span>}
                        <span style={{ fontFamily: 'IBM Plex Mono', fontSize: 11, color: isDone ? 'var(--green)' : isRun ? 'var(--accent)' : 'var(--muted)', minWidth: 38, textAlign: 'right' }}>{st.pct || 0}%</span>
                      </div>
                    </div>
                    <div style={{ height: 5, background: 'var(--surf2)', borderRadius: 2, overflow: 'hidden' }}>
                      <div style={{ height: '100%', width: `${st.pct || 0}%`, background: barClr, borderRadius: 2, transition: 'width .35s', boxShadow: isRun ? '0 0 8px var(--accent-glow)' : 'none' }} />
                    </div>
                  </div>
                );
              })}
            </div>
          </Card>
        </div>
      )}
    </div>
  );
}

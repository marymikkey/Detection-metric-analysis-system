import { useEffect, useState } from 'react';
import { CLRS } from '../../data/constants';
import Card from '../ui/Card';
import MonoLabel from '../ui/MonoLabel';

const METRICS_LABELS = { map50: 'mAP@50', map5095: 'mAP@50:95' };

function heatColor(val) {
  const v = Math.max(0, Math.min(1, val));
  if (v >= .95) return { bg: 'rgba(74,222,128,.18)',   text: '#4ade80' };
  if (v >= .90) return { bg: 'rgba(129,140,248,.18)',  text: '#818cf8' };
  if (v >= .80) return { bg: 'rgba(251,191,36,.12)',   text: '#fbbf24' };
  return             { bg: 'rgba(248,113,113,.12)',   text: '#f87171' };
}

export default function ResultsTab({ datasets, models, results }) {
  const [metric, setMetric] = useState('map50');
  const [apiRows, setApiRows] = useState([]);
  useEffect(() => {
    if (Object.keys(results || {}).length) return;
    fetch('/api/results').then(r => r.json()).then(d => setApiRows(d.rows || [])).catch(() => {});
  }, [results]);
  const jobs = Object.values(results || {});
  const selectedDatasetIds = new Set(datasets.map(d => d.id));
  const selectedModelIds = new Set(models.map(m => m.id));
  const rows = (jobs.length ? jobs : apiRows).filter(row =>
    selectedDatasetIds.has(row.datasetId) && selectedModelIds.has(row.modelId)
  );

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100%', overflow: 'hidden' }}>
      <div style={{ flex: 1, overflowY: 'auto', padding: '18px 24px 40px' }}>
        <div className="fade">
          <div style={{ marginBottom: 14, display: 'flex', gap: 8, alignItems: 'center' }}>
            <MonoLabel>Сравнительная матрица метрик</MonoLabel>
            <div style={{ marginLeft: 'auto', display: 'flex', gap: 6 }}>
              {Object.entries(METRICS_LABELS).map(([k, v]) => (
                <div key={k} onClick={() => setMetric(k)} style={{ padding: '4px 11px', borderRadius: 4, cursor: 'pointer', fontSize: 10, fontFamily: 'IBM Plex Mono', border: `1px solid ${metric === k ? 'var(--accent)' : 'var(--border)'}`, color: metric === k ? 'var(--accent)' : 'var(--muted)', background: metric === k ? 'var(--accent-dim)' : 'transparent' }}>
                  {v}
                </div>
              ))}
            </div>
          </div>
          <Card style={{ padding: 0, overflow: 'hidden' }}>
            <table style={{ width: '100%', borderCollapse: 'collapse' }}>
              <thead>
                <tr style={{ borderBottom: '1px solid var(--border)' }}>
                  {['Модель', 'Датасет', 'mAP@50', 'mAP@50:95'].map((h, i) => (
                    <th key={h} style={{ padding: '12px 18px', textAlign: i >= 2 ? 'right' : 'left', fontFamily: 'IBM Plex Mono', fontSize: 9, color: (i === 2 && metric === 'map50') || (i === 3 && metric === 'map5095') ? 'var(--accent)' : 'var(--muted)', fontWeight: 400, letterSpacing: '.08em', textTransform: 'uppercase' }}>{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {rows.map((j, mi) => {
                  const v = j.metrics || {};
                  const c50 = heatColor(v.map50), c95 = heatColor(v.map5095);
                  return (
                    <tr key={`${j.modelId}__${j.datasetId}`} style={{ borderBottom: '1px solid var(--border)' }}>
                      <td style={{ padding: '12px 18px' }}>
                        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                          <div style={{ width: 8, height: 8, borderRadius: '50%', background: CLRS[mi % CLRS.length] }} />
                          <span style={{ fontFamily: 'Syne', fontWeight: 700, fontSize: 13 }}>{j.modelName}</span>
                          <span style={{ fontFamily: 'IBM Plex Mono', fontSize: 9, color: 'var(--muted)' }}>DB</span>
                        </div>
                      </td>
                      <td style={{ padding: '12px 18px', fontFamily: 'IBM Plex Mono', fontSize: 11, color: 'var(--text2)' }}>{j.datasetName}</td>
                      <td style={{ padding: '12px 18px', textAlign: 'right' }}>
                        <div style={{ padding: '5px 12px', borderRadius: 5, background: c50.bg, display: 'inline-block', minWidth: 72 }}>
                          <span style={{ fontFamily: 'Syne', fontWeight: 800, fontSize: 14, color: c50.text }}>{(v.map50 * 100).toFixed(2)}%</span>
                        </div>
                      </td>
                      <td style={{ padding: '12px 18px', textAlign: 'right' }}>
                        <div style={{ padding: '5px 12px', borderRadius: 5, background: c95.bg, display: 'inline-block', minWidth: 72 }}>
                          <span style={{ fontFamily: 'Syne', fontWeight: 800, fontSize: 14, color: c95.text }}>{(v.map5095 * 100).toFixed(2)}%</span>
                        </div>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </Card>
        </div>
      </div>
    </div>
  );
}

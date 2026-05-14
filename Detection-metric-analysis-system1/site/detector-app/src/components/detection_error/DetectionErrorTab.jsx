import { useEffect, useState } from 'react';
import KpiCard from '../ui/KpiCard';

const CATS = {
  ground_truth: { label: 'Ground Truth', short: 'GT', color: '#ffffff', labelBg: '#16a34a', labelColor: '#ffffff', bg: 'rgba(34,197,94,.10)', border: 'rgba(34,197,94,.28)', dashed: true },
  false_positive: { label: 'False Positive', short: 'FP', color: '#f87171', bg: 'rgba(248,113,113,.10)', border: 'rgba(248,113,113,.28)' },
  false_negative: { label: 'False Negative', short: 'FN', color: '#fbbf24', bg: 'rgba(251,191,36,.10)', border: 'rgba(251,191,36,.28)' },
  low_conf: { label: 'Low Confidence', short: 'LC', color: '#38bdf8', bg: 'rgba(56,189,248,.10)', border: 'rgba(56,189,248,.28)' },
  low_iou: { label: 'Low IoU', short: 'IoU', color: '#4ade80', bg: 'rgba(74,222,128,.10)', border: 'rgba(74,222,128,.28)' },
  duplicate: { label: 'Duplicate', short: 'DUP', color: '#e879f9', bg: 'rgba(232,121,249,.10)', border: 'rgba(232,121,249,.28)' },
};

const CAT_ORDER = ['false_positive', 'false_negative', 'low_conf', 'low_iou', 'duplicate'];

function catMeta(key) {
  return CATS[key] || { label: key, short: key.slice(0, 3).toUpperCase(), color: 'var(--accent)', bg: 'var(--accent-dim)', border: 'var(--accent)33' };
}

function boxLabel(e, m) {
  const parts = [m.short];
  if (e.iou != null) parts.push(e.type === 'low_iou' ? e.iou.toFixed(2) : `iou=${e.iou.toFixed(2)}`);
  if (e.score != null) parts.push(`s=${e.score.toFixed(2)}`);
  return parts.join(' ');
}

function BoxLayer({ item, thick = 2 }) {
  const rawBoxes = item.overlays || item.errors;
  const boxes = [...rawBoxes.filter(e => e.type !== 'ground_truth'), ...rawBoxes.filter(e => e.type === 'ground_truth')];
  return boxes.map((e, i) => {
    const m = catMeta(e.type);
    const zIndex = e.type === 'ground_truth' ? boxes.length * 3 : i + 1;
    return (
      <div
        key={i}
        title={`${m.label}${e.score != null ? ` score=${e.score.toFixed(3)}` : ''}${e.iou != null ? ` iou=${e.iou.toFixed(3)}` : ''}`}
        style={{
          position: 'absolute',
          left: `${e.bbox[0] / item.width * 100}%`,
          top: `${e.bbox[1] / item.height * 100}%`,
          width: `${e.bbox[2] / item.width * 100}%`,
          height: `${e.bbox[3] / item.height * 100}%`,
          border: `${thick}px ${m.dashed ? 'dashed' : 'solid'} ${m.color}`,
          boxSizing: 'border-box',
          boxShadow: '0 0 0 1px rgba(0,0,0,.55)',
          zIndex,
        }}
      >
        <span
          style={{
            position: 'absolute',
            left: 0,
            bottom: '100%',
            padding: '1px 4px',
            borderRadius: 3,
            background: m.labelBg || 'rgba(0,0,0,.72)',
            border: `1px solid ${m.color}`,
            color: m.labelColor || m.color,
            fontFamily: 'IBM Plex Mono',
            fontSize: thick > 2 ? 11 : 8,
            lineHeight: 1.25,
            whiteSpace: 'nowrap',
            textShadow: '0 1px 2px rgba(0,0,0,.9)',
            pointerEvents: 'none',
            zIndex: zIndex + boxes.length,
          }}
        >
          {boxLabel(e, m)}
        </span>
      </div>
    );
  });
}

function ImageCard({ item, onOpen }) {
  const first = item.errors[0]?.type || 'unknown';
  const meta = catMeta(first);
  return (
    <div onClick={() => onOpen(item)} style={{ borderRadius: 8, overflow: 'hidden', cursor: 'pointer', border: '1px solid var(--border)', background: 'var(--surf)' }}>
      <div style={{ position: 'relative', width: '100%', paddingTop: '62%', background: 'var(--surf2)', overflow: 'hidden' }}>
        <img src={item.image_url} alt={item.file_name} style={{ position: 'absolute', inset: 0, width: '100%', height: '100%', objectFit: 'cover' }} />
        <BoxLayer item={item} />
      </div>
      <div style={{ padding: '6px 8px', display: 'flex', alignItems: 'center', gap: 6 }}>
        <div style={{ width: 6, height: 6, borderRadius: '50%', background: meta.color }} />
        <span style={{ fontFamily: 'IBM Plex Mono', fontSize: 9, color: 'var(--text2)', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap', flex: 1 }}>{item.file_name}</span>
        <span style={{ fontFamily: 'IBM Plex Mono', fontSize: 9, color: 'var(--muted)' }}>{item.errors.length}</span>
      </div>
    </div>
  );
}

export default function DetectionErrorTab() {
  const [payload, setPayload] = useState(null);
  const [loadErr, setLoadErr] = useState(null);
  const [filterCat, setFilterCat] = useState('all');
  const [lightbox, setLightbox] = useState(null);

  useEffect(() => {
    fetch('/api/detection-errors')
      .then(r => r.ok ? r.json() : Promise.reject(new Error(`HTTP ${r.status}`)))
      .then(setPayload)
      .catch(e => setLoadErr(e.message));
  }, []);

  if (loadErr) {
    return (
      <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', height: '100%', gap: 12, color: 'var(--muted)' }}>
        <div style={{ fontFamily: 'IBM Plex Mono', fontSize: 13, color: 'var(--red)' }}>Не удалось загрузить ошибки</div>
        <div style={{ fontFamily: 'IBM Plex Mono', fontSize: 10 }}>{loadErr}</div>
      </div>
    );
  }

  if (!payload) {
    return (
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', height: '100%', gap: 12, color: 'var(--muted)' }}>
        <div style={{ width: 24, height: 24, border: '2px solid var(--border)', borderTopColor: 'var(--accent)', borderRadius: '50%', animation: 'spin .7s linear infinite' }} />
        <span style={{ fontFamily: 'IBM Plex Mono', fontSize: 12 }}>Загрузка…</span>
      </div>
    );
  }

  const items = payload.items || [];
  const summary = payload.summary || {};
  const presentCats = CAT_ORDER.filter(c => (summary[c] || 0) > 0);
  const shown = filterCat === 'all' ? items : items.filter(item => item.errors.some(e => e.type === filterCat));

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100%', overflow: 'hidden' }}>
      <div style={{ flexShrink: 0, padding: '10px 20px', borderBottom: '1px solid var(--border)', display: 'flex', gap: 8 }}>
        <div style={{ flex: 1 }}><KpiCard label="Images" value={payload.totalImages || items.length} color="var(--text2)" /></div>
        {presentCats.map(c => {
          const meta = catMeta(c);
          return <div key={c} style={{ flex: 1 }}><KpiCard label={meta.label} value={summary[c] || 0} color={meta.color} warn /></div>;
        })}
      </div>

      <div style={{ flexShrink: 0, padding: '8px 20px', borderBottom: '1px solid var(--border)', display: 'flex', gap: 6, background: 'var(--surf)' }}>
        <button onClick={() => setFilterCat('all')} style={{ padding: '5px 12px', borderRadius: 5, border: `1px solid ${filterCat === 'all' ? 'var(--accent)' : 'var(--border)'}`, background: filterCat === 'all' ? 'var(--accent-dim)' : 'transparent', color: filterCat === 'all' ? 'var(--accent)' : 'var(--text2)', cursor: 'pointer', fontSize: 10, fontFamily: 'IBM Plex Mono' }}>ALL</button>
        {presentCats.map(c => {
          const meta = catMeta(c);
          return <button key={c} onClick={() => setFilterCat(c)} style={{ padding: '5px 12px', borderRadius: 5, border: `1px solid ${filterCat === c ? meta.color : 'var(--border)'}`, background: filterCat === c ? meta.bg : 'transparent', color: filterCat === c ? meta.color : 'var(--text2)', cursor: 'pointer', fontSize: 10, fontFamily: 'IBM Plex Mono' }}>{meta.short}</button>;
        })}
      </div>

      <div style={{ flex: 1, overflowY: 'auto', padding: '16px 20px 40px' }}>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(220px, 1fr))', gap: 12 }}>
          {shown.map(item => <ImageCard key={item.image_id} item={item} onOpen={setLightbox} />)}
        </div>
      </div>

      {lightbox && (
        <div onClick={() => setLightbox(null)} style={{ position: 'fixed', inset: 0, background: 'rgba(0,0,0,.9)', zIndex: 1000, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
          <div onClick={e => e.stopPropagation()} style={{ position: 'relative', maxWidth: '90vw', maxHeight: '86vh' }}>
            <img src={lightbox.image_url} alt={lightbox.file_name} style={{ maxWidth: '90vw', maxHeight: '86vh', display: 'block' }} />
            <BoxLayer item={lightbox} thick={3} />
          </div>
        </div>
      )}
    </div>
  );
}

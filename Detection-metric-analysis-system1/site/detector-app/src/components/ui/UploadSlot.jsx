import { useState, useRef } from 'react';

export default function UploadSlot({ label, accept, hint, file, onFile }) {
  const [drag, setDrag] = useState(false);
  const ref = useRef(null);
  return (
    <div
      onDragOver={e => { e.preventDefault(); setDrag(true); }}
      onDragLeave={() => setDrag(false)}
      onDrop={e => { e.preventDefault(); setDrag(false); const f = e.dataTransfer.files[0]; if (f) onFile(f); }}
      onClick={() => ref.current?.click()}
      style={{
        padding: '11px 14px', borderRadius: 7, cursor: 'pointer', transition: 'all .18s',
        border: `1.5px dashed ${drag ? 'var(--accent)' : file ? 'rgba(74,222,128,.5)' : 'var(--border2)'}`,
        background: drag ? 'var(--accent-dim)' : file ? 'rgba(74,222,128,.04)' : 'var(--bg)',
        display: 'flex', alignItems: 'center', gap: 10,
      }}
    >
      <input ref={ref} type="file" accept={accept} style={{ display: 'none' }} onChange={e => e.target.files[0] && onFile(e.target.files[0])} />
      <div style={{ width: 30, height: 30, borderRadius: 5, flexShrink: 0, display: 'flex', alignItems: 'center', justifyContent: 'center', background: file ? 'rgba(74,222,128,.12)' : 'var(--surf2)', border: `1px solid ${file ? 'rgba(74,222,128,.25)' : 'var(--border)'}`, fontSize: 13, color: file ? 'var(--green)' : 'var(--muted)' }}>
        {file ? '✓' : hint}
      </div>
      <div style={{ minWidth: 0 }}>
        <div style={{ fontSize: 11, fontWeight: 600, color: file ? 'var(--green)' : 'var(--text2)', marginBottom: 2 }}>{label}</div>
        <div style={{ fontFamily: 'IBM Plex Mono', fontSize: 9, color: 'var(--muted)', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{file ? file.name : accept}</div>
      </div>
    </div>
  );
}

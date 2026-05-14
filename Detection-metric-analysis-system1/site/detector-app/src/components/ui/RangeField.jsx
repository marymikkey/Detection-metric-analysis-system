export default function RangeField({ label, value, onChange, min, max, step }) {
  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 7 }}>
        <span style={{ fontSize: 11, color: 'var(--text2)' }}>{label}</span>
        <span style={{ fontFamily: 'IBM Plex Mono', fontSize: 11, color: 'var(--accent)' }}>{value}</span>
      </div>
      <input type="range" min={min} max={max} step={step} value={value} onChange={e => onChange(+e.target.value)} style={{ width: '100%' }} />
    </div>
  );
}

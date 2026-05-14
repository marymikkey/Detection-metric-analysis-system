export default function KpiCard({ label, value, color = 'var(--accent)', warn = false, sub, hint }) {
  return (
    <div style={{ padding: '10px 14px', background: 'var(--surf2)', border: `1px solid ${warn ? color + '55' : 'var(--border)'}`, borderRadius: 8, position: 'relative', overflow: 'hidden' }}>
      {warn && <div style={{ position: 'absolute', top: 0, left: 0, right: 0, height: 2, background: color }} />}
      <div style={{ fontFamily: 'IBM Plex Mono', fontSize: 15, fontWeight: 500, color, marginBottom: 3 }}>{value}</div>
      <div style={{ fontSize: 9, color: 'var(--muted)', letterSpacing: '.08em', textTransform: 'uppercase' }}>
        {label}
        {hint && <span title={hint} style={{ cursor: 'help', marginLeft: 4, color: 'var(--dim)', fontStyle: 'normal' }}> (?)</span>}
      </div>
      {sub && <div style={{ fontFamily: 'IBM Plex Mono', fontSize: 9, color: 'var(--dim)', marginTop: 2 }}>{sub}</div>}
    </div>
  );
}

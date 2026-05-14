export default function SectionHeader({ n, label }) {
  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 12 }}>
      <span style={{ fontFamily: 'IBM Plex Mono', fontSize: 10, color: 'var(--muted)', letterSpacing: '.1em' }}>{n}</span>
      <div style={{ height: 1, width: 14, background: 'var(--border)' }} />
      <span style={{ fontFamily: 'IBM Plex Mono', fontSize: 10, color: 'var(--text2)', letterSpacing: '.1em', textTransform: 'uppercase' }}>{label}</span>
    </div>
  );
}

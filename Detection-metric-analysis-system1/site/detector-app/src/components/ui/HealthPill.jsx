export default function HealthPill({ label, ok, onClick, clickable }) {
  return (
    <div
      onClick={onClick}
      style={{
        display: 'flex', alignItems: 'center', gap: 5,
        padding: '4px 10px', borderRadius: 20,
        cursor: clickable ? 'pointer' : 'default',
        border: `1px solid ${ok ? 'rgba(74,222,128,.3)' : 'rgba(248,113,113,.3)'}`,
        background: ok ? 'rgba(74,222,128,.05)' : 'rgba(248,113,113,.05)',
        transition: 'all .2s',
      }}
    >
      <span style={{ width: 6, height: 6, borderRadius: '50%', background: ok ? 'var(--green)' : 'var(--red)', display: 'inline-block' }} />
      <span style={{ fontSize: 10, color: 'var(--text2)' }}>{label}</span>
      <span style={{ fontSize: 10, fontFamily: 'IBM Plex Mono', color: ok ? 'var(--green)' : 'var(--red)', fontWeight: 500 }}>{ok ? '✓' : '✗'}</span>
    </div>
  );
}

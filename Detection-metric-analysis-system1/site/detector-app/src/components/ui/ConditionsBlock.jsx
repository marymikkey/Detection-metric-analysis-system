export default function ConditionsBlock({ data, total }) {
  if (!data.length) return <div style={{ fontSize: 11, color: 'var(--muted)', padding: '6px 0' }}>No data</div>;
  const max = Math.max(...data.map(([, v]) => v), 1);
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
      {data.map(([tag, count]) => (
        <div key={tag} style={{ display: 'grid', gridTemplateColumns: '90px 1fr 60px 48px', alignItems: 'center', gap: 8 }}>
          <span style={{ fontSize: 11, fontFamily: 'IBM Plex Mono', color: 'var(--text2)' }}>{tag}</span>
          <div style={{ height: 7, background: 'var(--border)', borderRadius: 2, overflow: 'hidden' }}>
            <div style={{ height: '100%', width: `${count / max * 100}%`, background: 'var(--accent)', opacity: .75 }} />
          </div>
          <span style={{ fontFamily: 'IBM Plex Mono', fontSize: 10, textAlign: 'right' }}>{count.toLocaleString()}</span>
          <span style={{ fontFamily: 'IBM Plex Mono', fontSize: 10, color: 'var(--muted)', textAlign: 'right' }}>
            {total ? (count / total * 100).toFixed(1) + '%' : '—'}
          </span>
        </div>
      ))}
    </div>
  );
}

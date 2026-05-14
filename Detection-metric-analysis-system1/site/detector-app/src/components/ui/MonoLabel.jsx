export default function MonoLabel({ children, style: s = {} }) {
  return (
    <div style={{ fontFamily: 'IBM Plex Mono', fontSize: 10, color: 'var(--muted)', letterSpacing: '.14em', textTransform: 'uppercase', ...s }}>
      {children}
    </div>
  );
}

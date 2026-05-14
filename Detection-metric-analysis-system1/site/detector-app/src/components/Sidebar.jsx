const TABS = [
  { id: 0, icon: '◎', label: 'Setup',           sub: 'Конфигурация' },
  { id: 1, icon: '◈', label: 'EDA',             sub: 'Анализ данных' },
  { id: 2, icon: '◉', label: 'Validation',      sub: 'Валидация' },
  { id: 3, icon: '◆', label: 'Results',         sub: 'Результаты' },
  { id: 4, icon: '◇', label: 'Detection Error', sub: 'Ошибки детекции' },
];

export default function Sidebar({ step, setStep, locks }) {
  return (
    <div style={{ width: 192, flexShrink: 0, background: 'var(--surf)', borderRight: '1px solid var(--border)', display: 'flex', flexDirection: 'column', paddingTop: 8 }}>
      {TABS.map(t => {
        const locked = locks[t.id], active = step === t.id;
        return (
          <div
            key={t.id}
            onClick={() => !locked && setStep(t.id)}
            style={{ padding: '12px 17px', cursor: locked ? 'not-allowed' : 'pointer', borderLeft: `2px solid ${active ? 'var(--accent)' : 'transparent'}`, background: active ? 'var(--accent-dim)' : 'transparent', opacity: locked ? .3 : 1, transition: 'all .15s' }}
          >
            <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 3 }}>
              <span style={{ color: active ? 'var(--accent)' : 'var(--muted)', fontSize: 11 }}>{t.icon}</span>
              <span style={{ fontFamily: 'Syne', fontWeight: 700, fontSize: 12, letterSpacing: '.04em', color: active ? 'var(--accent)' : 'var(--text)' }}>{t.label}</span>
            </div>
            <div style={{ fontSize: 10, color: 'var(--muted)', marginLeft: 20 }}>{t.sub}</div>
          </div>
        );
      })}
      <div style={{ flexGrow: 1 }} />
      <div style={{ padding: '12px 17px', borderTop: '1px solid var(--border)' }}>
        <div style={{ fontSize: 9, color: 'var(--muted)', lineHeight: 2, letterSpacing: '.08em' }}>
          <div>DETECTOR v2.0</div>
          <div style={{ color: 'var(--dim)' }}>© 2026</div>
        </div>
      </div>
    </div>
  );
}

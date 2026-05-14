import { useState, useEffect } from 'react';
import Sidebar from './components/Sidebar';
import SetupTab from './components/setup/SetupTab';
import EDATab from './components/eda/EDATab';
import ValidationTab from './components/validation/ValidationTab';
import ResultsTab from './components/results/ResultsTab';
import DetectionErrorTab from './components/detection_error/DetectionErrorTab';
import MonoLabel from './components/ui/MonoLabel';

const TWEAK_DEFAULTS = { accentColor: '#818cf8' };
const TITLES = ['Конфигурация', 'Анализ данных — EDA', 'Валидация', 'Результаты', 'Detection Error'];

export default function App() {
  const [step, setStep] = useState(0);
  const [cfg, setCfg] = useState({ datasets: [], models: [], valCfg: null });
  const [edaReady, setEdaReady] = useState(false);
  const [valDone, setValDone] = useState(false);
  const [valResults, setValResults] = useState({});
  const [tweaks, setTweaks] = useState(TWEAK_DEFAULTS);
  const [showTweaks, setShowTweaks] = useState(false);

  useEffect(() => {
    const h = e => {
      if (e.data?.type === '__activate_edit_mode') setShowTweaks(true);
      if (e.data?.type === '__deactivate_edit_mode') setShowTweaks(false);
    };
    window.addEventListener('message', h);
    window.parent.postMessage({ type: '__edit_mode_available' }, '*');
    return () => window.removeEventListener('message', h);
  }, []);

  useEffect(() => {
    document.documentElement.style.setProperty('--accent', tweaks.accentColor);
    const r = parseInt(tweaks.accentColor.slice(1, 3), 16);
    const g = parseInt(tweaks.accentColor.slice(3, 5), 16);
    const b = parseInt(tweaks.accentColor.slice(5, 7), 16);
    document.documentElement.style.setProperty('--accent-dim',  `rgba(${r},${g},${b},0.09)`);
    document.documentElement.style.setProperty('--accent-glow', `rgba(${r},${g},${b},0.22)`);
  }, [tweaks.accentColor]);

  const setTweak = (k, v) => {
    const next = { ...tweaks, [k]: v };
    setTweaks(next);
    window.parent.postMessage({ type: '__edit_mode_set_keys', edits: next }, '*');
  };

  const locks = { 0: false, 1: !edaReady, 2: !edaReady, 3: !valDone, 4: !valDone };

  const handleStart = (datasets, models, valCfg) => {
    setCfg({ datasets, models, valCfg });
    setEdaReady(true);
    setStep(1);
  };
  const handleValComplete = results => {
    setValResults(results);
    setValDone(true);
    setStep(3);
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100vh', overflow: 'hidden' }}>
      {/* Header */}
      <div style={{ height: 48, background: 'var(--surf)', borderBottom: '1px solid var(--border)', display: 'flex', alignItems: 'center', padding: '0 20px', gap: 16, flexShrink: 0 }}>
        <div style={{ fontFamily: 'Syne', fontWeight: 800, fontSize: 16, letterSpacing: '.14em', color: 'var(--accent)' }}>DETECTOR</div>
        <div style={{ width: 1, height: 16, background: 'var(--border)' }} />
        <div style={{ fontFamily: 'IBM Plex Mono', fontSize: 10, color: 'var(--text2)', display: 'flex', gap: 10, alignItems: 'center', flexWrap: 'wrap' }}>
          {cfg.datasets.length > 0 && <span style={{ color: 'var(--green)' }}>{cfg.datasets.length} датас.</span>}
          {cfg.models.length > 0 && <><span style={{ color: 'var(--muted)' }}>·</span><span style={{ color: 'var(--accent)' }}>{cfg.models.length} мод.</span></>}
          {cfg.datasets.length > 0 && cfg.models.length > 0 && <><span style={{ color: 'var(--muted)' }}>·</span><span>{cfg.datasets.length * cfg.models.length} заданий</span></>}
          {valDone && <><span style={{ color: 'var(--muted)' }}>·</span><span style={{ color: 'var(--green)' }}>✓ Завершено</span></>}
        </div>
        <div style={{ flexGrow: 1 }} />
        <div style={{ display: 'flex', gap: 5, alignItems: 'center' }}>
          {[0, 1, 2, 3, 4].map(i => (
            <div key={i} style={{ height: 3, width: i === step ? 18 : 3, borderRadius: 2, transition: 'all .3s', background: i === step ? 'var(--accent)' : locks[i] ? 'var(--border)' : 'var(--border2)' }} />
          ))}
        </div>
      </div>

      <div style={{ display: 'flex', flex: 1, overflow: 'hidden' }}>
        <Sidebar step={step} setStep={setStep} locks={locks} />
        <div style={{ flex: 1, overflow: 'hidden', display: 'flex', flexDirection: 'column' }}>
          <div style={{ padding: '18px 24px 0', flexShrink: 0 }}>
            <div style={{ fontFamily: 'Syne', fontWeight: 800, fontSize: 20, letterSpacing: '-.01em' }}>{TITLES[step]}</div>
          </div>
          <div style={{ flex: 1, overflow: 'hidden' }}>
            {step === 0 && <SetupTab onStart={handleStart} />}
            {step === 1 && <EDATab datasets={cfg.datasets} />}
            {step === 2 && <ValidationTab key={JSON.stringify(cfg)} datasets={cfg.datasets} models={cfg.models} valCfg={cfg.valCfg} onComplete={handleValComplete} />}
            {step === 3 && <ResultsTab datasets={cfg.datasets} models={cfg.models} results={valResults} />}
            {step === 4 && <DetectionErrorTab />}
          </div>
        </div>
      </div>

      {/* Tweaks panel */}
      {showTweaks && (
        <div style={{ position: 'fixed', bottom: 16, right: 16, background: 'var(--surf2)', border: '1px solid var(--border2)', borderRadius: 12, padding: 18, width: 220, zIndex: 200, boxShadow: '0 10px 50px rgba(0,0,0,.6)' }}>
          <div style={{ fontFamily: 'Syne', fontWeight: 700, fontSize: 13, marginBottom: 14 }}>Tweaks</div>
          <MonoLabel style={{ marginBottom: 9 }}>Цвет акцента</MonoLabel>
          <div style={{ display: 'flex', gap: 7, marginBottom: 4 }}>
            {['#818cf8', '#4ade80', '#f87171', '#fbbf24', '#38bdf8', '#e879f9'].map(c => (
              <div key={c} onClick={() => setTweak('accentColor', c)} style={{ width: 22, height: 22, borderRadius: 5, background: c, cursor: 'pointer', border: tweaks.accentColor === c ? '2px solid #fff' : '2px solid transparent', transition: 'all .15s' }} />
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

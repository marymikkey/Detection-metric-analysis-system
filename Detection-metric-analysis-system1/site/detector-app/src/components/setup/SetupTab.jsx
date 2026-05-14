import { useEffect, useState } from 'react';
import Card from '../ui/Card';
import MonoLabel from '../ui/MonoLabel';
import SectionHeader from '../ui/SectionHeader';
import RangeField from '../ui/RangeField';
import SelectField from '../ui/SelectField';
import UploadSlot from '../ui/UploadSlot';

export default function SetupTab({ onStart }) {
  const [selDs, setSelDs] = useState([]);
  const [selMs, setSelMs] = useState([]);
  const [dbDs, setDbDs] = useState([]);
  const [dbMs, setDbMs] = useState([]);
  const [loadErr, setLoadErr] = useState('');
  const [customDs, setCustomDs] = useState([]);
  const [customMs, setCustomMs] = useState([]);
  const [addingDs, setAddingDs] = useState(false);
  const [addingMs, setAddingMs] = useState(false);
  const [newDsName, setNewDsName] = useState('');
  const [newDsYaml, setNewDsYaml] = useState(null);
  const [newMsName, setNewMsName] = useState('');
  const [newMsWeights, setNewMsWeights] = useState(null);
  const [newMsScript, setNewMsScript] = useState(null);
  const [batchSize, setBatchSize] = useState(16);
  const [confThresh, setConfThresh] = useState(0.25);
  const [valSplit, setValSplit] = useState('val');

  useEffect(() => {
    fetch('/api/setup')
      .then(r => r.ok ? r.json() : Promise.reject(new Error(`HTTP ${r.status}`)))
      .then(data => {
        setDbDs(data.datasets || []);
        setDbMs(data.models || []);
        setSelDs((data.datasets || []).map(d => d.id));
        setSelMs((data.models || []).map(m => m.id));
      })
      .catch(e => setLoadErr(e.message));
  }, []);

  const toggleDs = id => setSelDs(prev => prev.includes(id) ? prev.filter(x => x !== id) : [...prev, id]);
  const toggleMs = id => setSelMs(prev => prev.includes(id) ? prev.filter(x => x !== id) : [...prev, id]);

  const allDs = [...dbDs, ...customDs];
  const allMs = [...dbMs, ...customMs];
  const totalJobs = selDs.length * selMs.length;
  const canStart = selDs.length > 0 && selMs.length > 0;

  function addCustomDs() {
    if (!newDsName.trim()) return;
    const d = { id: 'custom_' + Date.now(), name: newDsName.trim(), classes: '?', images: '?', desc: 'Custom dataset', size: '?', custom: true };
    setCustomDs(prev => [...prev, d]); setSelDs(prev => [...prev, d.id]);
    setNewDsName(''); setNewDsYaml(null); setAddingDs(false);
  }

  function addCustomMs() {
    if (!newMsName.trim() || !newMsWeights || !newMsScript) return;
    const m = { id: 'custom_' + Date.now(), name: newMsName.trim(), params: '?', gflops: '?', speed: '?', type: 'Custom', custom: true, weightsFile: newMsWeights, scriptFile: newMsScript };
    setCustomMs(prev => [...prev, m]); setSelMs(prev => [...prev, m.id]);
    setNewMsName(''); setNewMsWeights(null); setNewMsScript(null); setAddingMs(false);
  }

  const dsCfg = selDs.map(id => allDs.find(d => d.id === id)).filter(Boolean);
  const msCfg = selMs.map(id => allMs.find(m => m.id === id)).filter(Boolean);

  return (
    <div style={{ padding: '22px 40px 40px', overflowY: 'auto', height: '100%' }}>
      <div style={{ maxWidth: 960, animation: 'fadeIn .3s ease' }}>
        <p style={{ color: 'var(--text2)', fontSize: 13, lineHeight: 1.7, marginBottom: 28, maxWidth: 640 }}>
          Выберите один или несколько датасетов и моделей. Платформа проведёт EDA по каждому датасету и запустит валидацию всех комбинаций.
        </p>
        {loadErr && <div style={{ marginBottom: 16, color: 'var(--red)', fontFamily: 'IBM Plex Mono', fontSize: 11 }}>DB/API: {loadErr}</div>}

        {/* Datasets */}
        <SectionHeader n="01" label={`Датасеты ${selDs.length > 0 ? `(${selDs.length} выбрано)` : ''}`} />
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4,1fr)', gap: 9, marginBottom: 10 }}>
          {allDs.map(d => {
            const on = selDs.includes(d.id);
            return (
              <div key={d.id} onClick={() => toggleDs(d.id)} style={{ padding: 14, borderRadius: 10, cursor: 'pointer', transition: 'all .18s', border: `1px solid ${on ? 'var(--accent)' : 'var(--border)'}`, background: on ? 'var(--accent-dim)' : 'var(--surf)', position: 'relative' }}>
                {on && <div style={{ position: 'absolute', top: 8, right: 8, width: 18, height: 18, borderRadius: '50%', background: 'var(--accent)', display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: 10, color: '#fff', fontWeight: 700 }}>✓</div>}
                <div style={{ fontFamily: 'Syne', fontWeight: 700, fontSize: 12, color: on ? 'var(--accent)' : 'var(--text)', marginBottom: 7 }}>{d.name}</div>
                <div style={{ fontSize: 10, color: 'var(--text2)', lineHeight: 1.9 }}>
                  <div style={{ color: 'var(--muted)' }}>{d.desc}</div>
                  <div>{d.classes ?? '?'} кл.</div>
                  <div style={{ color: 'var(--muted)', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{d.imagePath || d.path}</div>
                </div>
              </div>
            );
          })}
        </div>

        {!addingDs
          ? <button onClick={() => setAddingDs(true)} style={{ fontSize: 11, color: 'var(--muted)', background: 'transparent', border: '1px dashed var(--border2)', borderRadius: 7, padding: '7px 14px', cursor: 'pointer', marginBottom: 24, fontFamily: 'IBM Plex Mono' }}>＋ Добавить свой датасет</button>
          : <div style={{ marginBottom: 24, padding: '14px 18px', background: 'var(--surf)', border: '1px solid var(--border)', borderRadius: 10, display: 'flex', flexDirection: 'column', gap: 10 }}>
              <MonoLabel style={{ marginBottom: 4 }}>Новый датасет</MonoLabel>
              <input value={newDsName} onChange={e => setNewDsName(e.target.value)} placeholder="Название датасета" style={{ padding: '7px 11px', background: 'var(--surf2)', border: '1px solid var(--border)', borderRadius: 6, color: 'var(--text)', fontSize: 12, fontFamily: 'Plus Jakarta Sans' }} />
              <UploadSlot label="YAML конфиг" accept=".yaml,.yml,.json" hint="⚙" file={newDsYaml} onFile={setNewDsYaml} />
              <div style={{ display: 'flex', gap: 8 }}>
                <button onClick={addCustomDs} disabled={!newDsName.trim()} style={{ padding: '7px 18px', background: newDsName.trim() ? 'var(--accent)' : 'var(--border)', color: newDsName.trim() ? '#fff' : 'var(--muted)', border: 'none', borderRadius: 6, cursor: newDsName.trim() ? 'pointer' : 'not-allowed', fontFamily: 'Syne', fontSize: 12, fontWeight: 700 }}>Добавить</button>
                <button onClick={() => { setAddingDs(false); setNewDsName(''); setNewDsYaml(null); }} style={{ padding: '7px 14px', background: 'transparent', color: 'var(--muted)', border: '1px solid var(--border)', borderRadius: 6, cursor: 'pointer', fontSize: 12 }}>Отмена</button>
              </div>
            </div>
        }

        {/* Models */}
        <SectionHeader n="02" label={`Модели ${selMs.length > 0 ? `(${selMs.length} выбрано)` : ''}`} />
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4,1fr)', gap: 9, marginBottom: 10 }}>
          {allMs.map(m => {
            const on = selMs.includes(m.id);
            return (
              <div key={m.id} onClick={() => toggleMs(m.id)} style={{ padding: 14, borderRadius: 10, cursor: 'pointer', transition: 'all .18s', border: `1px solid ${on ? 'var(--accent)' : 'var(--border)'}`, background: on ? 'var(--accent-dim)' : 'var(--surf)', position: 'relative' }}>
                {on && <div style={{ position: 'absolute', top: 8, right: 8, width: 18, height: 18, borderRadius: '50%', background: 'var(--accent)', display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: 10, color: '#fff', fontWeight: 700 }}>✓</div>}
                <div style={{ fontFamily: 'Syne', fontWeight: 800, fontSize: 14, color: on ? 'var(--accent)' : 'var(--text)', marginBottom: 3 }}>{m.name}</div>
                <div style={{ fontFamily: 'IBM Plex Mono', fontSize: 9, color: 'var(--muted)', marginBottom: 8 }}>{String(m.type || 'custom').toUpperCase()}</div>
                <div style={{ fontSize: 10, color: 'var(--text2)', lineHeight: 1.9 }}>
                  <div style={{ color: 'var(--muted)', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{m.weightsPath || 'custom weights'}</div>
                  <div style={{ color: 'var(--muted)', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{m.scriptPath || ''}</div>
                </div>
              </div>
            );
          })}
        </div>

        {!addingMs
          ? <button onClick={() => setAddingMs(true)} style={{ fontSize: 11, color: 'var(--muted)', background: 'transparent', border: '1px dashed var(--border2)', borderRadius: 7, padding: '7px 14px', cursor: 'pointer', marginBottom: 24, fontFamily: 'IBM Plex Mono' }}>＋ Добавить свою модель (.pth + .py)</button>
          : <div style={{ marginBottom: 24, padding: '14px 18px', background: 'var(--surf)', border: '1px solid var(--border)', borderRadius: 10, display: 'flex', flexDirection: 'column', gap: 10 }}>
              <MonoLabel style={{ marginBottom: 4 }}>Новая модель</MonoLabel>
              <input value={newMsName} onChange={e => setNewMsName(e.target.value)} placeholder="Название модели" style={{ padding: '7px 11px', background: 'var(--surf2)', border: '1px solid var(--border)', borderRadius: 6, color: 'var(--text)', fontSize: 12, fontFamily: 'Plus Jakarta Sans' }} />
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 10 }}>
                <UploadSlot label="Веса (.pth/.pt)" accept=".pth,.pt,.bin,.safetensors" hint="⚖" file={newMsWeights} onFile={setNewMsWeights} />
                <UploadSlot label="Скрипт (.py)" accept=".py" hint="⚙" file={newMsScript} onFile={setNewMsScript} />
              </div>
              {newMsWeights && newMsScript && newMsName.trim() && (
                <div style={{ padding: '7px 12px', background: 'rgba(74,222,128,.06)', border: '1px solid rgba(74,222,128,.2)', borderRadius: 6, fontSize: 10, color: 'var(--green)', fontFamily: 'IBM Plex Mono' }}>✓ Готово к добавлению</div>
              )}
              <div style={{ display: 'flex', gap: 8 }}>
                <button onClick={addCustomMs} disabled={!newMsName.trim() || !newMsWeights || !newMsScript} style={{ padding: '7px 18px', background: newMsName.trim() && newMsWeights && newMsScript ? 'var(--accent)' : 'var(--border)', color: newMsName.trim() && newMsWeights && newMsScript ? '#fff' : 'var(--muted)', border: 'none', borderRadius: 6, cursor: 'pointer', fontFamily: 'Syne', fontSize: 12, fontWeight: 700 }}>Добавить</button>
                <button onClick={() => { setAddingMs(false); setNewMsName(''); setNewMsWeights(null); setNewMsScript(null); }} style={{ padding: '7px 14px', background: 'transparent', color: 'var(--muted)', border: '1px solid var(--border)', borderRadius: 6, cursor: 'pointer', fontSize: 12 }}>Отмена</button>
              </div>
            </div>
        }

        {/* Validation params */}
        <SectionHeader n="03" label="Параметры валидации" />
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: 16, marginBottom: 32 }}>
          <SelectField label="Сплит" value={valSplit} onChange={setValSplit} options={['val', 'test', 'train']} strOpts />
          <SelectField label="Batch Size" value={batchSize} onChange={setBatchSize} options={[1, 4, 8, 16, 32, 64]} />
          <RangeField label="Conf threshold" value={confThresh} onChange={setConfThresh} min={0.05} max={0.95} step={0.05} />
        </div>

        {canStart && (
          <div style={{ marginBottom: 20, padding: '12px 16px', background: 'var(--surf)', border: '1px solid var(--border)', borderRadius: 10, display: 'flex', alignItems: 'center', gap: 12, flexWrap: 'wrap' }}>
            <div style={{ fontSize: 11, color: 'var(--text2)' }}>Будет запущено заданий:</div>
            <span style={{ fontFamily: 'Syne', fontWeight: 800, fontSize: 22, color: 'var(--accent)' }}>{totalJobs}</span>
            <span style={{ fontFamily: 'IBM Plex Mono', fontSize: 10, color: 'var(--muted)' }}>{selMs.length} мод. × {selDs.length} датас.</span>
            <div style={{ marginLeft: 'auto', display: 'flex', gap: 8, flexWrap: 'wrap' }}>
              {msCfg.map(m => <span key={m.id} style={{ fontFamily: 'IBM Plex Mono', fontSize: 9, padding: '2px 8px', background: 'var(--accent-dim)', color: 'var(--accent)', borderRadius: 4 }}>{m.name}</span>)}
              {dsCfg.map(d => <span key={d.id} style={{ fontFamily: 'IBM Plex Mono', fontSize: 9, padding: '2px 8px', background: 'rgba(74,222,128,.08)', color: 'var(--green)', borderRadius: 4 }}>{d.name}</span>)}
            </div>
          </div>
        )}
        <button
          onClick={() => canStart && onStart(dsCfg, msCfg, { batchSize, confThresh, valSplit })}
          disabled={!canStart}
          style={{ padding: '13px 36px', background: canStart ? 'var(--accent)' : 'var(--border)', color: canStart ? '#fff' : 'var(--muted)', border: 'none', borderRadius: 8, fontFamily: 'Syne', fontSize: 14, fontWeight: 700, letterSpacing: '.06em', cursor: canStart ? 'pointer' : 'not-allowed', transition: 'all .2s', boxShadow: canStart ? '0 0 28px var(--accent-glow)' : 'none' }}
        >
          {canStart ? `ЗАПУСТИТЬ ВАЛИДАЦИЮ (${totalJobs} заданий) →` : 'Выберите датасеты и модели'}
        </button>
      </div>
    </div>
  );
}

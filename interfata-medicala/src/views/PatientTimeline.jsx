import { useState, useEffect } from 'react';
import { fetchConsultatii } from '../models/api';

function formatDate(dateStr) {
  if (!dateStr) return '—';
  const d = new Date(dateStr);
  return d.toLocaleDateString('ro-RO', { day: '2-digit', month: 'long', year: 'numeric' });
}

function formatTime(dateStr) {
  if (!dateStr) return '';
  const d = new Date(dateStr);
  return d.toLocaleTimeString('ro-RO', { hour: '2-digit', minute: '2-digit' });
}

function TranscriptViewer({ transcript }) {
  const linii = transcript ? transcript.split('\n').filter(l => l.trim()) : [];
  return (
    <div style={styles.transcript.container}>
      <p style={styles.transcript.label}>Transcriere consultație</p>
      {linii.length === 0 ? (
        <p style={styles.transcript.empty}>Nicio transcriere disponibilă.</p>
      ) : (
        linii.map((linie, i) => {
          const eDoctor = linie.startsWith('SPEAKER_00');
          return (
            <div key={i} style={{ ...styles.transcript.linie, justifyContent: eDoctor ? 'flex-start' : 'flex-end' }}>
              <div style={{ ...styles.transcript.bubble, ...(eDoctor ? styles.transcript.bubbleDoctor : styles.transcript.bubblePacient) }}>
                <span style={styles.transcript.speaker}>{eDoctor ? 'Medic' : 'Pacient'}</span>
                <span style={styles.transcript.text}>{linie.replace(/^SPEAKER_\d+:\s*/, '')}</span>
              </div>
            </div>
          );
        })
      )}
    </div>
  );
}

function DiagnosticViewer({ diagnostic, corectie }) {
  const [tab, setTab] = useState(corectie ? 'corectie' : 'ai');
  return (
    <div>
      {corectie && (
        <div style={styles.tabs.container}>
          <button onClick={() => setTab('corectie')} style={{ ...styles.tabs.btn, ...(tab === 'corectie' ? styles.tabs.active : {}) }}>
            Corectura medic
          </button>
          <button onClick={() => setTab('ai')} style={{ ...styles.tabs.btn, ...(tab === 'ai' ? styles.tabs.activeAlt : {}) }}>
            Raport AI inițial
          </button>
        </div>
      )}
      <div style={styles.diagnostic.container}>
        <p style={styles.diagnostic.label}>
          {tab === 'corectie' ? 'Raport corectat de medic' : 'Raport generat de AI'}
        </p>
        <pre style={styles.diagnostic.text}>
          {(tab === 'corectie' ? corectie : diagnostic) || 'Nu există raport.'}
        </pre>
      </div>
    </div>
  );
}

function ConsultatieCard({ c, index, total }) {
  const [expanded, setExpanded] = useState(false);
  const [viewMode, setViewMode] = useState('diagnostic');
  const isLast = index === total - 1;

  return (
    <div style={styles.card.wrapper}>
      <div style={styles.timeline.col}>
        <div style={styles.timeline.dot} />
        {!isLast && <div style={styles.timeline.line} />}
      </div>
      <div style={{ flex: 1, paddingBottom: isLast ? 0 : 32 }}>
        <button onClick={() => setExpanded(e => !e)} style={styles.card.header}>
          <div style={styles.card.dateRow}>
            <span style={styles.card.date}>{formatDate(c.data_consultatiei)}</span>
            <span style={styles.card.time}>{formatTime(c.data_consultatiei)}</span>
          </div>
          <span style={{ ...styles.card.chevron, transform: expanded ? 'rotate(180deg)' : 'rotate(0deg)' }}>▾</span>
        </button>

        {c.rezumat_scurt && <p style={styles.card.rezumat}>{c.rezumat_scurt}</p>}

        {expanded && (
          <div style={styles.card.expanded}>
            <div style={styles.viewSwitch.container}>
              <button onClick={() => setViewMode('diagnostic')} style={{ ...styles.viewSwitch.btn, ...(viewMode === 'diagnostic' ? styles.viewSwitch.active : {}) }}>
                Diagnostic
              </button>
              <button onClick={() => setViewMode('transcript')} style={{ ...styles.viewSwitch.btn, ...(viewMode === 'transcript' ? styles.viewSwitch.active : {}) }}>
                Transcriere
              </button>
            </div>
            {viewMode === 'diagnostic'
              ? <DiagnosticViewer diagnostic={c.diagnostic_complet} corectie={c.corectie_medic} />
              : <TranscriptViewer transcript={c.transcript} />
            }
            <div style={styles.card.footer}>
              <span style={styles.card.footerItem}>ID consultație #{c.id}</span>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

export default function PatientTimeline({ pacientId, onClose }) {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    if (!pacientId) return;
    setLoading(true);
    setError('');
    fetchConsultatii(pacientId)
      .then(d => { setData(d); setLoading(false); })
      .catch(e => { setError(e.message); setLoading(false); });
  }, [pacientId]);

  return (
    <div style={styles.modal.overlay}>
      <div style={styles.modal.container}>
        <div style={styles.modal.header}>
          <div>
            <h2 style={styles.modal.title}>
              {data ? data.pacient.nume_complet : 'Istoric consultații'}
            </h2>
            {data && (
              <p style={styles.modal.subtitle}>
                {data.pacient.varsta} ani
                {data.pacient.cnp_masked ? ` · CNP: ${data.pacient.cnp_masked}` : ''}
                {' · '}
                <strong>{data.total}</strong> {data.total === 1 ? 'consultație' : 'consultații'}
              </p>
            )}
          </div>
          <button onClick={onClose} style={styles.modal.closeBtn}>✕</button>
        </div>

        {data?.pacient.istoric_medical && (
          <div style={styles.istoricMedical.container}>
            <p style={styles.istoricMedical.label}>Istoric medical cunoscut</p>
            <p style={styles.istoricMedical.text}>{data.pacient.istoric_medical}</p>
          </div>
        )}

        {data && data.total > 0 && (
          <div style={styles.stats.container}>
            <div style={styles.stats.item}>
              <span style={styles.stats.number}>{data.total}</span>
              <span style={styles.stats.label}>{data.total === 1 ? 'Consultație' : 'Consultații'}</span>
            </div>
          </div>
        )}

        <div style={styles.modal.body}>
          {loading && (
            <div style={styles.state.center}>
              <div style={styles.state.spinner} />
              <p style={styles.state.text}>Se încarcă istoricul...</p>
            </div>
          )}
          {error && <div style={styles.state.error}><p>Eroare la încărcare: {error}</p></div>}
          {data && data.total === 0 && (
            <div style={styles.state.center}>
              <p style={styles.state.empty}>Nicio consultație înregistrată.</p>
            </div>
          )}
          {data && data.total > 0 && (
            <div style={{ paddingTop: 8 }}>
              {data.consultatii.map((c, i) => (
                <ConsultatieCard key={c.id} c={c} index={i} total={data.total} />
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

const styles = {
  modal: {
    overlay: { position: 'fixed', inset: 0, background: 'rgba(15,23,42,0.55)', backdropFilter: 'blur(4px)', zIndex: 1000, display: 'flex', alignItems: 'flex-start', justifyContent: 'center', padding: '32px 16px', overflowY: 'auto' },
    container: { background: '#fff', borderRadius: 16, width: '100%', maxWidth: 720, boxShadow: '0 24px 64px rgba(0,0,0,0.18)', overflow: 'hidden' },
    header: { display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', padding: '24px 28px 20px', borderBottom: '1px solid #e2e8f0', background: '#f8fafc' },
    title: { margin: 0, fontSize: 20, fontWeight: 700, color: '#0f172a' },
    subtitle: { margin: '4px 0 0', fontSize: 13, color: '#64748b', fontWeight: 400 },
    closeBtn: { background: 'none', border: 'none', fontSize: 18, color: '#94a3b8', cursor: 'pointer', padding: '4px 8px', borderRadius: 6 },
    body: { padding: '20px 28px 28px', maxHeight: '65vh', overflowY: 'auto' },
  },
  istoricMedical: {
    container: { margin: '16px 28px 0', padding: '12px 16px', background: '#fefce8', borderLeft: '3px solid #eab308', borderRadius: '0 8px 8px 0' },
    label: { margin: '0 0 4px', fontSize: 11, fontWeight: 600, color: '#a16207', textTransform: 'uppercase', letterSpacing: '0.05em' },
    text: { margin: 0, fontSize: 13, color: '#713f12', lineHeight: 1.5 },
  },
  stats: {
    container: { display: 'flex', alignItems: 'center', padding: '16px 28px', borderBottom: '1px solid #e2e8f0' },
    item: { display: 'flex', flexDirection: 'column', alignItems: 'flex-start', flex: 1 },
    number: { fontSize: 22, fontWeight: 700, color: '#1e40af', lineHeight: 1 },
    label: { fontSize: 11, color: '#94a3b8', marginTop: 2, textTransform: 'uppercase', letterSpacing: '0.05em' },
  },
  card: {
    wrapper: { display: 'flex', gap: 0 },
    header: { display: 'flex', justifyContent: 'space-between', alignItems: 'center', width: '100%', background: 'none', border: 'none', cursor: 'pointer', padding: '4px 0 8px', textAlign: 'left' },
    dateRow: { display: 'flex', alignItems: 'center', gap: 8, marginBottom: 6 },
    date: { fontSize: 15, fontWeight: 600, color: '#0f172a' },
    time: { fontSize: 12, color: '#94a3b8', background: '#f1f5f9', padding: '2px 6px', borderRadius: 4 },
    chevron: { fontSize: 18, color: '#94a3b8', transition: 'transform 0.2s', display: 'block' },
    rezumat: { margin: '0 0 4px', fontSize: 13, color: '#475569', lineHeight: 1.6, paddingRight: 16 },
    expanded: { marginTop: 12, background: '#f8fafc', borderRadius: 12, padding: 16, border: '1px solid #e2e8f0' },
    footer: { display: 'flex', justifyContent: 'flex-start', alignItems: 'center', marginTop: 12, paddingTop: 12, borderTop: '1px solid #e2e8f0' },
    footerItem: { fontSize: 11, color: '#94a3b8' },
  },
  timeline: {
    col: { display: 'flex', flexDirection: 'column', alignItems: 'center', marginRight: 16, paddingTop: 6, width: 16, flexShrink: 0 },
    dot: { width: 12, height: 12, borderRadius: '50%', flexShrink: 0, background: '#2563eb', boxShadow: '0 0 0 3px #fff, 0 0 0 4px #e2e8f0' },
    line: { width: 2, flex: 1, background: '#e2e8f0', marginTop: 6 },
  },
  tabs: {
    container: { display: 'flex', gap: 4, marginBottom: 12 },
    btn: { padding: '5px 12px', fontSize: 12, borderRadius: 6, border: 'none', cursor: 'pointer', fontWeight: 500, background: '#e2e8f0', color: '#64748b' },
    active: { background: '#0f172a', color: '#fff' },
    activeAlt: { background: '#64748b', color: '#fff' },
  },
  viewSwitch: {
    container: { display: 'flex', gap: 4, marginBottom: 12 },
    btn: { flex: 1, padding: '7px 0', fontSize: 12, borderRadius: 8, border: '1px solid #e2e8f0', cursor: 'pointer', fontWeight: 500, background: '#fff', color: '#64748b' },
    active: { background: '#0f172a', color: '#fff', borderColor: '#0f172a' },
  },
  diagnostic: {
    container: { background: '#fff', borderRadius: 8, padding: 14, border: '1px solid #e2e8f0' },
    label: { margin: '0 0 8px', fontSize: 11, fontWeight: 600, color: '#94a3b8', textTransform: 'uppercase', letterSpacing: '0.05em' },
    text: { margin: 0, fontSize: 12.5, color: '#334155', lineHeight: 1.7, whiteSpace: 'pre-wrap', fontFamily: 'inherit', maxHeight: 320, overflowY: 'auto' },
  },
  transcript: {
    container: { display: 'flex', flexDirection: 'column', gap: 8 },
    label: { margin: '0 0 4px', fontSize: 11, fontWeight: 600, color: '#94a3b8', textTransform: 'uppercase', letterSpacing: '0.05em' },
    empty: { margin: 0, fontSize: 13, color: '#94a3b8' },
    linie: { display: 'flex' },
    bubble: { maxWidth: '75%', padding: '8px 12px', borderRadius: 12, display: 'flex', flexDirection: 'column', gap: 2 },
    bubbleDoctor: { background: '#eff6ff', borderBottomLeftRadius: 4 },
    bubblePacient: { background: '#f0fdf4', borderBottomRightRadius: 4 },
    speaker: { fontSize: 10, fontWeight: 600, color: '#94a3b8', textTransform: 'uppercase', letterSpacing: '0.05em' },
    text: { fontSize: 13, color: '#1e293b', lineHeight: 1.5 },
  },
  state: {
    center: { display: 'flex', flexDirection: 'column', alignItems: 'center', padding: '40px 0', gap: 12 },
    spinner: { width: 32, height: 32, border: '3px solid #e2e8f0', borderTopColor: '#2563eb', borderRadius: '50%', animation: 'spin 0.8s linear infinite' },
    text: { margin: 0, color: '#64748b', fontSize: 14 },
    empty: { margin: 0, color: '#94a3b8', fontSize: 14 },
    error: { padding: 16, background: '#fef2f2', borderRadius: 8, color: '#991b1b', fontSize: 13 },
  },
};

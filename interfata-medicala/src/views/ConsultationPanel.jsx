export default function ConsultationPanel({ status, transcript, processingMsg, canStart, onStart, onStop }) {
  return (
    <>
      <section style={{ textAlign: 'center' }}>
        {status === 'idle' || status === 'completed' ? (
          <button
            onClick={onStart}
            disabled={!canStart}
            style={{
              padding: '15px 40px', fontSize: '20px',
              backgroundColor: canStart ? '#2ecc71' : '#bdc3c7',
              color: 'white', border: 'none', borderRadius: '50px',
              cursor: canStart ? 'pointer' : 'not-allowed', fontWeight: 'bold',
            }}
          >
            Începe Înregistrarea
          </button>
        ) : status === 'recording' ? (
          <div style={{ animation: 'pulse 1.5s infinite', display: 'inline-block' }}>
            <button
              onClick={onStop}
              style={{
                padding: '15px 40px', fontSize: '20px',
                backgroundColor: '#e74c3c', color: 'white',
                border: 'none', borderRadius: '50px', cursor: 'pointer', fontWeight: 'bold',
              }}
            >
              Oprește și Generează Diagnostic
            </button>
          </div>
        ) : (
          <div style={{ padding: '20px', color: '#2980b9', fontWeight: 'bold' }}>
            <div style={{ fontSize: '24px', marginBottom: '8px' }}>⏳</div>
            {processingMsg || 'Se inițializează procesarea...'}
            <div style={{ marginTop: '12px', height: '4px', backgroundColor: '#dce9f5', borderRadius: '2px', overflow: 'hidden' }}>
              <div style={{
                height: '100%', width: '40%', backgroundColor: '#2980b9',
                borderRadius: '2px', animation: 'progressBar 1.8s ease-in-out infinite alternate',
              }} />
            </div>
          </div>
        )}
      </section>

      {status === 'recording' && (
        <div style={{ marginTop: '30px', padding: '20px', borderLeft: '5px solid #e74c3c', backgroundColor: '#fff5f5' }}>
          <h4>🎙️ Transcriere în timp real:</h4>
          {transcript.length > 0
            ? transcript.map((t, i) => <p key={i} style={{ margin: '5px 0' }}>{t}</p>)
            : <p>Vă rugăm vorbiți...</p>
          }
        </div>
      )}
    </>
  );
}

import { useState, useRef } from 'react';

function App() {
  const [status, setStatus] = useState('idle');
  const [sessionId, setSessionId] = useState(null);
  const [transcript, setTranscript] = useState([]);
  const [report, setReport] = useState(null);

  const wsRef = useRef(null);

  const API_BASE_URL = 'http://localhost:8000';
  const WS_BASE_URL = 'ws://localhost:8000';

  // Poll /result until diarization + LLM finish (can take a few minutes on CPU)
  const pollForResult = async (sid) => {
    for (let i = 0; i < 72; i++) {          // up to ~6 minutes
      await new Promise(r => setTimeout(r, 5000));
      try {
        const res = await fetch(`${API_BASE_URL}/sessions/${sid}/result`);
        const data = await res.json();
        if (data.status === 'completed') return data;
        console.log(`Still processing… attempt ${i + 1}`);
      } catch (e) {
        console.error('Poll error:', e);
      }
    }
    return null;
  };

  const startConsultation = async () => {
    setStatus('recording');
    setTranscript([]);
    setReport(null);

    // 1. Create session on the server
    const res = await fetch(`${API_BASE_URL}/sessions`, { method: 'POST' });
    const data = await res.json();
    const sid = data.session_id;
    setSessionId(sid);

    // 2. Open WebSocket — server starts sounddevice recording immediately
    const ws = new WebSocket(`${WS_BASE_URL}/sessions/${sid}/stream`);
    wsRef.current = ws;

    ws.onopen = () => console.log('🟢 WS open — server is recording via sounddevice');
    ws.onmessage = (event) => {
      const msg = JSON.parse(event.data);
      if (msg.type === 'partial_transcript') {
        setTranscript(prev => [...prev, msg.text]);
      }
    };
    ws.onerror = (e) => console.error('WS error:', e);
  };

  const stopConsultation = async () => {
    setStatus('processing');

    // Close WebSocket (signals server to stop recording thread)
    if (wsRef.current) wsRef.current.close();

    // Tell server to run diarization + LLM
    await fetch(`${API_BASE_URL}/sessions/${sessionId}/stop`, { method: 'POST' });

    // Poll until the report is ready
    const finalData = await pollForResult(sessionId);
    if (finalData?.status === 'completed') {
      setReport(finalData.data);
      setStatus('completed');
    } else {
      alert('Processing timed out — check the server console.');
      setStatus('idle');
    }
  };

  return (
    <div style={{ fontFamily: 'system-ui', maxWidth: '800px', margin: '0 auto', padding: '20px' }}>
      <header style={{ textAlign: 'center', marginBottom: '40px' }}>
        <h1 style={{ color: '#2c3e50' }}>🩺 AI Medical Assistant</h1>
        <p style={{ color: '#7f8c8d', fontSize: '14px' }}>
          Audio captured directly by the server (same as app_cabinet.py)
        </p>
      </header>

      {/* Control button */}
      <div style={{ display: 'flex', justifyContent: 'center', marginBottom: '30px' }}>
        {status === 'idle' || status === 'completed' ? (
          <button onClick={startConsultation} style={btnStyle('#27ae60')}>
            ▶ Start Consultation
          </button>
        ) : status === 'recording' ? (
          <button onClick={stopConsultation} style={btnStyle('#e74c3c')}>
            ⏹ Stop &amp; Generate Report
          </button>
        ) : (
          <button disabled style={btnStyle('#95a5a6')}>
            ⏳ AI Processing… (diarization + report)
          </button>
        )}
      </div>

      {status === 'recording' && (
        <p style={{ textAlign: 'center', color: '#e74c3c' }}>
          🔴 Recording live via server microphone…
        </p>
      )}

      {/* Live transcript */}
      {(status === 'recording' || transcript.length > 0) && (
        <div style={panelStyle}>
          <h3 style={{ marginTop: 0 }}>🗣️ Live Transcript</h3>
          {transcript.length === 0
            ? <p style={{ color: '#bdc3c7' }}>Waiting for speech…</p>
            : transcript.map((line, i) => <p key={i} style={{ margin: '4px 0' }}>{line}</p>)
          }
        </div>
      )}

      {/* Final report */}
      {status === 'completed' && report && (
        <div style={{ ...panelStyle, backgroundColor: '#e8f8ff', marginTop: '20px' }}>
          <h2 style={{ color: '#0984e3', marginTop: 0 }}>🏥 Medical Report</h2>
          <p style={{ whiteSpace: 'pre-wrap' }}>{report.summary}</p>
          {report.disclaimer && (
            <p style={{ color: '#95a5a6', fontSize: '13px' }}>{report.disclaimer}</p>
          )}
        </div>
      )}
    </div>
  );
}

const btnStyle = (bg) => ({
  padding: '15px 30px', fontSize: '18px',
  backgroundColor: bg, color: 'white',
  border: 'none', borderRadius: '8px', cursor: 'pointer',
});

const panelStyle = {
  backgroundColor: '#f9fbfd', padding: '20px',
  borderRadius: '8px', border: '1px solid #dcdde1', minHeight: '120px',
};

export default App;
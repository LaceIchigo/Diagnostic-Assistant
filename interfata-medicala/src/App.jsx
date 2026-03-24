import { useState, useRef } from 'react';
import './App.css'; // Dacă vrei să adaugi stiluri mai târziu

function App() {
  const [status, setStatus] = useState('idle'); // idle, recording, processing, completed
  const [sessionId, setSessionId] = useState(null);
  const [transcript, setTranscript] = useState([]);
  const [report, setReport] = useState(null);

  // Referințe pentru a păstra conexiunea activă fără a re-randa pagina
  const wsRef = useRef(null);
  const mediaRecorderRef = useRef(null);

  // URL-ul backend-ului tău (FastAPI)
  const API_BASE_URL = 'http://localhost:8000';
  const WS_BASE_URL = 'ws://localhost:8000';

  // ==========================================
  // 1. START CONSULTAȚIE
  // ==========================================
  const startConsultation = async () => {
    try {
      setStatus('recording');
      setTranscript([]);
      setReport(null);

      // A. Creăm sesiunea nouă
      const res = await fetch(`${API_BASE_URL}/sessions`, { method: 'POST' });
      const data = await res.json();
      const newSessionId = data.session_id;
      setSessionId(newSessionId);

      // B. Ne conectăm la WebSocket
      const ws = new WebSocket(`${WS_BASE_URL}/sessions/${newSessionId}/stream`);
      wsRef.current = ws;

      ws.onopen = () => console.log('🟢 WebSocket Conectat');

      ws.onmessage = (event) => {
        const msg = JSON.parse(event.data);
        if (msg.type === 'partial_transcript') {
          // Adăugăm noul text la lista de transcript
          setTranscript((prev) => [...prev, msg.text]);
        }
      };

      // C. Pornim microfonul browserului
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const mediaRecorder = new MediaRecorder(stream, { mimeType: 'audio/webm' });
      mediaRecorderRef.current = mediaRecorder;

      // Când browserul adună o bucată de sunet, o trimite pe WebSocket
      mediaRecorder.ondataavailable = async (event) => {
        if (event.data.size > 0 && ws.readyState === WebSocket.OPEN) {
          // Transformăm fisierul .webm (Blob) într-un buffer binar curat
          const buffer = await event.data.arrayBuffer();
          // Trimitem pachetul binar către serverul Python
          ws.send(buffer);
        }
      };

      // Trimitem pachete audio la fiecare 1 secundă (1000 ms)
      mediaRecorder.start(1000);

    } catch (error) {
      console.error('Eroare la pornire:', error);
      alert('Nu am putut accesa microfonul sau serverul este oprit.');
      setStatus('idle');
    }
  };

  // ==========================================
  // 2. STOP CONSULTAȚIE
  // ==========================================
  const stopConsultation = async () => {
    setStatus('processing');

    // A. Oprim microfonul
    if (mediaRecorderRef.current) {
      mediaRecorderRef.current.stop();
      mediaRecorderRef.current.stream.getTracks().forEach(track => track.stop());
    }

    // B. Închidem WebSocket-ul
    if (wsRef.current) {
      wsRef.current.close();
    }

    // C. Anunțăm serverul că am terminat și așteptăm procesarea
    try {
      await fetch(`${API_BASE_URL}/sessions/${sessionId}/stop`, { method: 'POST' });

      // D. Cerem rezultatul final (după ce Ollama termină)
      const res = await fetch(`${API_BASE_URL}/sessions/${sessionId}/result`);
      const finalData = await res.json();

      if (finalData.status === 'completed') {
        setReport(finalData.data);
        setStatus('completed');
      }
    } catch (error) {
      console.error('Eroare la oprire:', error);
      setStatus('idle');
    }
  };

  // ==========================================
  // INTERFAȚA VIZUALĂ
  // ==========================================
  return (
    <div style={{ fontFamily: 'system-ui, sans-serif', maxWidth: '800px', margin: '0 auto', padding: '20px' }}>

      {/* HEADER */}
      <header style={{ textAlign: 'center', marginBottom: '40px' }}>
        <h1 style={{ color: '#2c3e50' }}>🩺 Asistent Medical AI</h1>
        <p style={{ color: '#7f8c8d' }}>Sistem de analiză și transcriere în timp real</p>
      </header>

      {/* ZONA DE BUTOANE */}
      <div style={{ display: 'flex', justifyContent: 'center', marginBottom: '30px' }}>
        {status === 'idle' || status === 'completed' ? (
          <button
            onClick={startConsultation}
            style={{ padding: '15px 30px', fontSize: '18px', backgroundColor: '#27ae60', color: 'white', border: 'none', borderRadius: '8px', cursor: 'pointer', fontWeight: 'bold' }}>
            ▶ Începe Consultația
          </button>
        ) : status === 'recording' ? (
          <button
            onClick={stopConsultation}
            style={{ padding: '15px 30px', fontSize: '18px', backgroundColor: '#e74c3c', color: 'white', border: 'none', borderRadius: '8px', cursor: 'pointer', fontWeight: 'bold', animation: 'pulse 2s infinite' }}>
            ⏹ Oprește și Generează Raport
          </button>
        ) : (
          <button disabled style={{ padding: '15px 30px', fontSize: '18px', backgroundColor: '#95a5a6', color: 'white', border: 'none', borderRadius: '8px' }}>
            ⏳ Procesare AI în curs...
          </button>
        )}
      </div>

      {/* STATUS */}
      {status === 'recording' && (
        <div style={{ textAlign: 'center', color: '#e74c3c', fontWeight: 'bold', marginBottom: '20px' }}>
          🔴 Înregistrare live... (ID Sesiune: {sessionId && sessionId.substring(0, 8)}...)
        </div>
      )}

      <hr style={{ border: '1px solid #ecf0f1', marginBottom: '30px' }} />

      {/* ZONA DE TRANSCRIPT LIVE */}
      {(status === 'recording' || transcript.length > 0) && (
        <div style={{ backgroundColor: '#f9fbfd', padding: '20px', borderRadius: '8px', border: '1px solid #dcdde1', minHeight: '150px' }}>
          <h3 style={{ marginTop: 0, color: '#34495e' }}>🗣️ Transcript Live:</h3>
          {transcript.map((line, index) => (
            <p key={index} style={{ margin: '5px 0', fontSize: '16px' }}>{line}</p>
          ))}
          {transcript.length === 0 && <p style={{ color: '#bdc3c7', fontStyle: 'italic' }}>Aștept voce...</p>}
        </div>
      )}

      {/* ZONA DE RAPORT MEDICAL FINAL */}
      {status === 'completed' && report && (
        <div style={{ backgroundColor: '#e8fbff', padding: '20px', borderRadius: '8px', border: '1px solid #bce6fb', marginTop: '20px' }}>
          <h2 style={{ marginTop: 0, color: '#0984e3' }}>🏥 Raport Medical Final</h2>

          <h4>Rezumat:</h4>
          <p>{report.summary}</p>

          <h4>Sugestii Diagnostic:</h4>
          <ul>
            {report.suggestions.map((sug, idx) => <li key={idx}>{sug}</li>)}
          </ul>

          <p style={{ fontSize: '12px', color: '#7f8c8d', marginTop: '20px' }}>⚠️ {report.disclaimer}</p>
        </div>
      )}

    </div>
  );
}

export default App;
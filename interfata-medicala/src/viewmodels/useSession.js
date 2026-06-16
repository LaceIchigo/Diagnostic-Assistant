import { useState } from 'react';
import * as api from '../models/api';

export function useSession() {
  const [status, setStatus] = useState('idle');
  const [sessionId, setSessionId] = useState(null);
  const [activePacientId, setActivePacientId] = useState(null);
  const [transcript, setTranscript] = useState([]);
  const [report, setReport] = useState(null);
  const [editedReport, setEditedReport] = useState('');
  const [processingMsg, setProcessingMsg] = useState('');

  const pollResult = async (sid) => {
    const start = Date.now();
    const timeoutMs = 120000;
    const steps = [
      { after: 0,     msg: 'Diarizare voci in curs...' },
      { after: 15000, msg: 'LLM genereaza raportul medical...' },
      { after: 60000, msg: 'Model complex, aproape gata...' },
    ];

    while (Date.now() - start < timeoutMs) {
      const elapsed = Date.now() - start;
      const step = [...steps].reverse().find(s => elapsed >= s.after);
      if (step) setProcessingMsg(step.msg);

      await new Promise(r => setTimeout(r, 2000));

      const data = await api.getSessionResult(sid);
      if (data.status === 'completed') return data;
      if (data.status === 'error') throw new Error(data.message || 'Eroare server');
    }
    throw new Error('Timeout: procesarea a durat mai mult de 2 minute');
  };

  const start = async (pacientId) => {
    if (!pacientId) { alert('Va rugam selectati un pacient mai intai!'); return; }
    try {
      setStatus('recording');
      setTranscript([]);
      setReport(null);
      setEditedReport('');
      setProcessingMsg('');
      setActivePacientId(pacientId);

      const data = await api.createSession();
      setSessionId(data.session_id);

      const ws = api.createSessionSocket(data.session_id);
      ws.onmessage = (event) => {
        const msg = JSON.parse(event.data);
        if (msg.type === 'partial_transcript') {
          setTranscript(prev => [...prev, msg.text]);
        }
      };
    } catch {
      setStatus('idle');
      alert('Eroare la pornirea serverului.');
    }
  };

  const stop = async () => {
    setStatus('processing');
    setProcessingMsg('Se opreste inregistrarea...');
    try {
      await api.stopSession(sessionId, activePacientId);
      const finalData = await pollResult(sessionId);
      setReport(finalData.data);
      setEditedReport(finalData.data.summary);
      setStatus('completed');
      setProcessingMsg('');
    } catch (error) {
      console.error('Eroare stop:', error);
      alert(error.message);
      setStatus('idle');
      setProcessingMsg('');
    }
  };

  const saveCorectie = async (consultatieId) => {
    try {
      await api.saveCorectie(consultatieId, editedReport);
      alert('Corectura salvata pentru Federated Learning!');
    } catch {
      alert('Eroare la salvarea corecturii.');
    }
  };

  return {
    status,
    transcript,
    report,
    editedReport,
    setEditedReport,
    processingMsg,
    start,
    stop,
    saveCorectie,
  };
}

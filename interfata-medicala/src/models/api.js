const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';
const WS_BASE_URL  = import.meta.env.VITE_WS_URL  || 'ws://localhost:8000';

async function request(url, options = {}) {
  const res = await fetch(url, options);
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  return res.json();
}

export const fetchPacienti = () =>
  request(`${API_BASE_URL}/pacienti`);

export const addPacient = (data) =>
  request(`${API_BASE_URL}/pacienti`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  });

export const createSession = () =>
  request(`${API_BASE_URL}/sessions`, { method: 'POST' });

export const createSessionSocket = (sessionId) =>
  new WebSocket(`${WS_BASE_URL}/sessions/${sessionId}/stream`);

export const stopSession = (sessionId, pacientId) =>
  request(`${API_BASE_URL}/sessions/${sessionId}/stop?pacient_id=${pacientId}`, { method: 'POST' });

export const getSessionResult = (sessionId) =>
  request(`${API_BASE_URL}/sessions/${sessionId}/result`);

export const saveCorectie = (consultatieId, text) =>
  request(`${API_BASE_URL}/consultatii/${consultatieId}/corectie`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ text_corectat: text }),
  });

export const fetchConsultatii = (pacientId) =>
  request(`${API_BASE_URL}/pacienti/${pacientId}/consultatii`);

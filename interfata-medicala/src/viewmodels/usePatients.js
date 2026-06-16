import { useState, useEffect } from 'react';
import * as api from '../models/api';

export function usePatients() {
  const [pacienti, setPacienti] = useState([]);
  const [selectedPacientId, setSelectedPacientId] = useState('');
  const [showAddForm, setShowAddForm] = useState(false);
  const [newPacient, setNewPacient] = useState({
    nume_complet: '', cnp: '', varsta: '', istoric_medical: '',
  });

  useEffect(() => { loadPacienti(); }, []);

  const loadPacienti = async () => {
    try {
      const data = await api.fetchPacienti();
      setPacienti(data);
    } catch (e) {
      console.error('Nu pot incarca pacientii', e);
    }
  };

  const submitNewPacient = async (e) => {
    e.preventDefault();
    try {
      await api.addPacient(newPacient);
      setNewPacient({ nume_complet: '', cnp: '', varsta: '', istoric_medical: '' });
      setShowAddForm(false);
      await loadPacienti();
    } catch {
      alert('Eroare la salvarea pacientului');
    }
  };

  return {
    pacienti,
    selectedPacientId,
    setSelectedPacientId,
    showAddForm,
    setShowAddForm,
    newPacient,
    setNewPacient,
    submitNewPacient,
  };
}

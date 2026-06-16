import { useState } from 'react';
import './App.css';

import { usePatients } from './viewmodels/usePatients';
import { useSession } from './viewmodels/useSession';

import PatientSelector from './views/PatientSelector';
import ConsultationPanel from './views/ConsultationPanel';
import ReportEditor from './views/ReportEditor';
import PatientTimeline from './views/PatientTimeline';

function App() {
  const patients = usePatients();
  const session = useSession();
  const [showTimeline, setShowTimeline] = useState(false);

  return (
    <div className="container" style={{ maxWidth: '900px', margin: '0 auto', padding: '20px', fontFamily: 'sans-serif' }}>
      <header style={{ textAlign: 'center', borderBottom: '1px solid rgba(255,255,255,0.1)', marginBottom: '30px', paddingBottom: '16px' }}>
        <h1 style={{ color: '#ecf0f1', margin: '0 0 8px 0', lineHeight: 1.2, fontSize: '1.9rem' }}>
          🩺 Smart Medical Assistant v2.0
        </h1>
        <p style={{ color: '#9aa7b0', margin: 0, fontSize: '0.95rem' }}>
          Sistem AI cu integrare Bază de Date Pacienți
        </p>
      </header>
      <PatientSelector
        pacienti={patients.pacienti}
        selectedPacientId={patients.selectedPacientId}
        setSelectedPacientId={patients.setSelectedPacientId}
        showAddForm={patients.showAddForm}
        setShowAddForm={patients.setShowAddForm}
        newPacient={patients.newPacient}
        setNewPacient={patients.setNewPacient}
        submitNewPacient={patients.submitNewPacient}
        onShowTimeline={() => setShowTimeline(true)}
      />

      <ConsultationPanel
        status={session.status}
        transcript={session.transcript}
        processingMsg={session.processingMsg}
        canStart={!!patients.selectedPacientId}
        onStart={() => session.start(patients.selectedPacientId)}
        onStop={session.stop}
      />

      {session.status === 'completed' && session.report && (
        <ReportEditor
          report={session.report}
          editedReport={session.editedReport}
          onChange={session.setEditedReport}
          onSave={() => session.saveCorectie(session.report.consultatie_id)}
        />
      )}

      {showTimeline && (
        <PatientTimeline
          pacientId={patients.selectedPacientId}
          onClose={() => setShowTimeline(false)}
        />
      )}

      <style>{`
        @keyframes progressBar {
          from { transform: translateX(-100%); }
          to   { transform: translateX(250%); }
        }
        @keyframes pulse {
          0%, 100% { opacity: 1; }
          50%       { opacity: 0.7; }
        }
        @keyframes spin {
          to { transform: rotate(360deg); }
        }
      `}</style>
    </div>
  );
}

export default App;

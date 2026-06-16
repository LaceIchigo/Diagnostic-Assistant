export default function ReportEditor({ report, editedReport, onChange, onSave }) {
  return (
    <div style={{
      marginTop: '40px', padding: '30px',
      backgroundColor: '#e3f2fd', borderRadius: '15px', border: '1px solid #bbdefb',
    }}>
      <h2 style={{ color: '#1565c0', borderBottom: '2px solid #1565c0', paddingBottom: '10px' }}>
        🏥 Diagnostic (Mod Editare)
      </h2>

      <p style={{ color: '#e67e22', fontWeight: 'bold', fontSize: '14px' }}>
        ℹ Modificați textul de mai jos dacă AI-ul a greșit. Datele vor fi folosite anonimizat
        pentru a antrena și îmbunătăți modelul (Federated Learning).
      </p>

      <textarea
        value={editedReport}
        onChange={e => onChange(e.target.value)}
        style={{
          width: '100%', minHeight: '200px', padding: '15px',
          fontSize: '16px', borderRadius: '8px', border: '1px solid #90caf9',
          marginTop: '10px', fontFamily: 'inherit', lineHeight: '1.5',
          boxSizing: 'border-box',
        }}
      />

      <div style={{ marginTop: '20px', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <span style={{ fontSize: '12px', color: '#546e7a' }}>⏱️ {report.disclaimer}</span>
        <button
          onClick={onSave}
          style={{
            padding: '12px 25px', backgroundColor: '#8e44ad',
            color: 'white', border: 'none', borderRadius: '8px',
            cursor: 'pointer', fontWeight: 'bold',
          }}
        >
          Salvează & Contribuie la Modelul AI
        </button>
      </div>
    </div>
  );
}

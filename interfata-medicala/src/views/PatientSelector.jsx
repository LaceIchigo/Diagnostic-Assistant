export default function PatientSelector({
  pacienti,
  selectedPacientId,
  setSelectedPacientId,
  showAddForm,
  setShowAddForm,
  newPacient,
  setNewPacient,
  submitNewPacient,
  onShowTimeline,
}) {
  return (
    <section style={{ backgroundColor: '#f8f9fa', padding: '20px', borderRadius: '12px', marginBottom: '30px' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <h3>👤 Selectare Pacient</h3>
        <button
          onClick={() => setShowAddForm(!showAddForm)}
          style={{ backgroundColor: '#3498db', color: 'white', border: 'none', padding: '8px 15px', borderRadius: '5px', cursor: 'pointer' }}
        >
          {showAddForm ? '✖ Închide' : '➕ Pacient Nou'}
        </button>
      </div>

      {!showAddForm ? (
        <div style={{ marginTop: '15px' }}>
          <select
            value={selectedPacientId}
            onChange={e => setSelectedPacientId(e.target.value)}
            style={{ width: '100%', padding: '12px', fontSize: '16px', borderRadius: '8px', border: '1px solid #ccc' }}
          >
            <option value="">-- Alegeți Pacientul din Listă --</option>
            {pacienti.map(p => (
              <option key={p.id} value={p.id}>
                {p.nume_complet} (CNP: {p.cnp_masked || '***'})
              </option>
            ))}
          </select>
          {selectedPacientId && (
            <button
              onClick={onShowTimeline}
              style={{
                marginTop: '10px', width: '100%', padding: '10px',
                backgroundColor: '#1565c0', color: 'white', border: 'none',
                borderRadius: '8px', cursor: 'pointer', fontWeight: 'bold', fontSize: '14px',
              }}
            >
              📋 Vezi Istoricul Consultațiilor
            </button>
          )}
        </div>
      ) : (
        <form onSubmit={submitNewPacient} style={{ display: 'grid', gap: '10px', marginTop: '15px' }}>
          <input
            type="text" placeholder="Nume Complet" required
            value={newPacient.nume_complet}
            onChange={e => setNewPacient({ ...newPacient, nume_complet: e.target.value })}
            style={{ padding: '10px' }}
          />
          <input
            type="text" placeholder="CNP" required
            value={newPacient.cnp}
            onChange={e => setNewPacient({ ...newPacient, cnp: e.target.value })}
            style={{ padding: '10px' }}
          />
          <input
            type="number" placeholder="Vârstă" required
            value={newPacient.varsta}
            onChange={e => setNewPacient({ ...newPacient, varsta: e.target.value })}
            style={{ padding: '10px' }}
          />
          <textarea
            placeholder="Istoric Medical (opțional)"
            value={newPacient.istoric_medical}
            onChange={e => setNewPacient({ ...newPacient, istoric_medical: e.target.value })}
            style={{ padding: '10px' }}
          />
          <button
            type="submit"
            style={{ backgroundColor: '#27ae60', color: 'white', padding: '10px', border: 'none', borderRadius: '5px', fontWeight: 'bold' }}
          >
            Salvează Pacientul
          </button>
        </form>
      )}
    </section>
  );
}

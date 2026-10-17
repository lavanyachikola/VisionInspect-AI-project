import React, { useState, useEffect } from 'react'
import CameraCapture from './CameraCapture'


function App() {
  const [email, setEmail] = useState('engineer@gmail.com')
  const [password, setPassword] = useState('password123')
  const [message, setMessage] = useState('')
  const [loading, setLoading] = useState(false)
  const [loggedIn, setLoggedIn] = useState(false)
  const [user, setUser] = useState(null)
  const [currentPage, setCurrentPage] = useState('dashboard')
  const [inspections, setInspections] = useState([])
  const [stats, setStats] = useState({ total: 0, defective: 0, passed: 0, reworked: 0, rejected: 0, defect_rate: 0, pass_rate: 0, by_severity: {} })
  const [analytics, setAnalytics] = useState(null)
  const [modelPerf, setModelPerf] = useState(null)
  const [products, setProducts] = useState([])
  const [selectedProduct, setSelectedProduct] = useState('')
  const [selectedFile, setSelectedFile] = useState(null)
  const [preview, setPreview] = useState(null)
  const [result, setResult] = useState(null)
  const [categories, setCategories] = useState([])
  const [selectedCategory, setSelectedCategory] = useState(null)
  const [categoryImages, setCategoryImages] = useState([])
  const [selectedInspection, setSelectedInspection] = useState(null)
  const [showCamera, setShowCamera] = useState(false)
  
  
  
  const [filterDecision, setFilterDecision] = useState('all')
  const [filterProduct, setFilterProduct] = useState('all')

  useEffect(() => {
    const savedUser = localStorage.getItem('user')
    if (savedUser) {
      try {
        setUser(JSON.parse(savedUser))
        setLoggedIn(true)
        fetchInspections(); fetchStats(); fetchProducts(); fetchCategories()
      } catch (e) {}
    }
  }, [])

  const fetchInspections = async () => {
    try {
      const t = localStorage.getItem('token')
      const r = await fetch('http://127.0.0.1:8000/inspections/', { headers: { 'Authorization': `Bearer ${t}` } })
      if (r.ok) setInspections(await r.json())
    } catch (e) {}
  }

  const fetchStats = async () => {
    try {
      const t = localStorage.getItem('token')
      const r = await fetch('http://127.0.0.1:8000/inspections/stats', { headers: { 'Authorization': `Bearer ${t}` } })
      if (r.ok) setStats(await r.json())
    } catch (e) {}
  }

  const fetchAnalytics = async () => {
    try {
      const t = localStorage.getItem('token')
      const r = await fetch('http://127.0.0.1:8000/inspections/analytics/summary', { headers: { 'Authorization': `Bearer ${t}` } })
      if (r.ok) setAnalytics(await r.json())
    } catch (e) {}
  }

  const fetchModelPerf = async () => {
    try {
      const t = localStorage.getItem('token')
      const r = await fetch('http://127.0.0.1:8000/inspections/model-performance', { headers: { 'Authorization': `Bearer ${t}` } })
      if (r.ok) setModelPerf(await r.json())
    } catch (e) {}
  }

  const fetchProducts = async () => {
    try {
      const t = localStorage.getItem('token')
      const r = await fetch('http://127.0.0.1:8000/auth/products', { headers: { 'Authorization': `Bearer ${t}` } })
      if (r.ok) setProducts(await r.json())
    } catch (e) {
      setProducts([
        { id: 'MC-001', product_name: 'Metal Component', product_code: 'MC-001' },
        { id: 'PP-001', product_name: 'Plastic Part', product_code: 'PP-001' },
        { id: 'EB-001', product_name: 'Electronic Board', product_code: 'EB-001' }
      ])
    }
  }

  const fetchCategories = async () => {
    try {
      const t = localStorage.getItem('token')
      const r = await fetch('http://127.0.0.1:8000/dataset/categories', { headers: { 'Authorization': `Bearer ${t}` } })
      if (r.ok) {
        const d = await r.json()
        setCategories(d.categories || [])
      }
    } catch (e) {}
  }

  const fetchCategoryImages = async (cat) => {
    try {
      const t = localStorage.getItem('token')
      const r = await fetch(`http://127.0.0.1:8000/dataset/category/${cat}`, { headers: { 'Authorization': `Bearer ${t}` } })
      if (r.ok) {
        const d = await r.json()
        setCategoryImages(d.images || [])
      }
    } catch (e) {}
  }

  const handleLogin = async (e) => {
    e.preventDefault()
    setLoading(true); setMessage('')
    try {
      const fd = new URLSearchParams()
      fd.append('email', email); fd.append('password', password)
      const r = await fetch('http://127.0.0.1:8000/auth/login', {
        method: 'POST',
        headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
        body: fd
      })
      const d = await r.json()
      if (r.ok) {
        setLoggedIn(true); setUser(d.user); setMessage('Login successful!')
        localStorage.setItem('token', d.access_token)
        localStorage.setItem('user', JSON.stringify(d.user))
        fetchInspections(); fetchStats(); fetchProducts(); fetchCategories()
      } else setMessage('Login failed')
    } catch (e) { setMessage('Cannot connect to server') }
    finally { setLoading(false) }
  }

  const handleLogout = () => {
    setLoggedIn(false); setUser(null); setMessage(''); setCurrentPage('dashboard')
    localStorage.removeItem('token'); localStorage.removeItem('user')
  }


  
  const handleFileChange = (e) => {
    const f = e.target.files[0]
    if (f) { setSelectedFile(f); setPreview(URL.createObjectURL(f)); setResult(null) }
  }

  const handleInspect = async (e) => {
    e.preventDefault()
    if (!selectedProduct || !selectedFile) {
      setResult({ type: 'error', message: 'Please select product and image' })
      return
    }
    setLoading(true); setResult(null)
    try {
      const fd = new FormData()
      fd.append('product_id', selectedProduct)
      fd.append('image', selectedFile)
      const t = localStorage.getItem('token')
      const r = await fetch('http://127.0.0.1:8000/inspections/upload', {
        method: 'POST',
        headers: { 'Authorization': `Bearer ${t}` },
        body: fd
      })
      const d = await r.json()
      if (r.ok) {
        setResult({ type: 'success', data: d })
        fetchInspections(); fetchStats()
        setSelectedProduct(''); setSelectedFile(null)
        const fi = document.getElementById('fileInput')
        if (fi) fi.value = ''
      } else setResult({ type: 'error', message: d.detail || 'Failed' })
    } catch (e) { setResult({ type: 'error', message: 'Error: ' + e.message }) }
    finally { setLoading(false) }
  }

  const getBadge = (v) => {
    const c = {
      PASS: 'badge-passed', REWORK: 'badge-pending', REJECT: 'badge-failed',
      Critical: 'badge-failed', High: 'badge-pending', Medium: 'badge-processing', Low: 'badge-passed'
    }
    return <span className={c[v] || 'badge-pending'}>{v}</span>
  }

  const Navbar = () => (
    <nav className="nav">
      <div className="nav-left">
        <div className="logo">V</div>
        <div>
          <h1 className="nav-title">VisionInspect <span style={{color:'#3b82f6'}}>AI</span></h1>
          
        </div>
      </div>
      <div className="nav-right">
        <span className="nav-user">{user?.name}</span>
        <span className="nav-role">{user?.role?.replace('_', ' ')}</span>
        <button onClick={handleLogout} className="btn-logout">Logout</button>
      </div>
    </nav>
  )

  const Sidebar = () => {
    const isSup = user?.role === 'supervisor'
    const items = [
      { id: 'dashboard', label: 'Dashboard', icon: '📊' },
      ...(isSup ? [] : [{ id: 'inspect', label: 'AI Inspect', icon: '🔍' }]),
      { id: 'inspections', label: 'History', icon: '📋' },
      { id: 'analytics', label: 'Analytics', icon: '📈' },
      { id: 'model', label: 'Model Performance', icon: '🎯' },
      { id: 'dataset', label: 'Dataset', icon: '🗄️' }
    ]
    return (
      <div className="sidebar">
        {items.map(i => (
          <button key={i.id} className={`side-item ${currentPage === i.id ? 'active' : ''}`}
            onClick={() => {
              setCurrentPage(i.id)
              if (i.id === 'dashboard') { fetchStats(); fetchInspections() }
              if (i.id === 'analytics') fetchAnalytics()
              if (i.id === 'model') fetchModelPerf()
              if (i.id === 'dataset') fetchCategories()
              if (i.id === 'inspect') fetchProducts()
              if (i.id === 'inspections') fetchInspections()
            }}>
            <span className="side-icon">{i.icon}</span>{i.label}
          </button>
        ))}
      </div>
    )
  }

  const DashboardPage = () => {
    const isSup = user?.role === 'supervisor'
    return (
      <div className="page">
        <div className="page-header">
          <h2>{isSup ? 'Production Overview' : 'Dashboard'}</h2>
          <p>AI-powered defect detection analytics</p>
        </div>
        <div className="stat-grid">
          <div className="stat-card" style={{borderColor:'#3b82f633'}}>
            <div className="stat-label">Total</div>
            <div className="stat-value" style={{color:'#3b82f6'}}>{stats.total}</div>
          </div>
          <div className="stat-card" style={{borderColor:'#34d39933'}}>
            <div className="stat-label">Passed</div>
            <div className="stat-value" style={{color:'#34d399'}}>{stats.passed}</div>
          </div>
          <div className="stat-card" style={{borderColor:'#fbbf2433'}}>
            <div className="stat-label">Rework</div>
            <div className="stat-value" style={{color:'#fbbf24'}}>{stats.reworked}</div>
          </div>
          <div className="stat-card" style={{borderColor:'#f8717133'}}>
            <div className="stat-label">Rejected</div>
            <div className="stat-value" style={{color:'#f87171'}}>{stats.rejected}</div>
          </div>
        </div>
        <div className="rate-grid">
          <div className="rate-card">
            <div className="rate-label">Defect Rate</div>
            <div className="rate-value" style={{color:'#f87171'}}>{stats.defect_rate}%</div>
          </div>
          <div className="rate-card">
            <div className="rate-label">Pass Rate</div>
            <div className="rate-value" style={{color:'#34d399'}}>{stats.pass_rate}%</div>
          </div>
        </div>
        {stats.by_severity && (
          <div className="section">
            <h3 className="section-title">Severity Distribution</h3>
            <div className="severity-grid">
              {['Critical', 'High', 'Medium', 'Low'].map(s => (
                <div key={s} className="sev-card">
                  <div className="sev-label">{s}</div>
                  <div className="sev-count">{stats.by_severity[s] || 0}</div>
                </div>
              ))}
            </div>
          </div>
        )}
        {!isSup && (
          <div className="section">
            <h3 className="section-title">Quick Actions</h3>
            <div className="btn-row">
              <button className="btn-primary" onClick={() => { setCurrentPage('inspect'); setResult(null) }}>Start Inspection</button>
              <button className="btn-secondary" onClick={() => { setCurrentPage('inspections'); fetchInspections() }}>History</button>
              <button className="btn-secondary" onClick={() => { setCurrentPage('analytics'); fetchAnalytics() }}>Analytics</button>
              <button className="btn-secondary" onClick={() => { setCurrentPage('model'); fetchModelPerf() }}>Model Performance</button>
            </div>
          </div>
        )}
      </div>
    )
  }

  const InspectPage = () => (
    <div className="page">
      <div className="page-header">
        <h2>AI Inspection</h2>
        <p>Upload image for AI-powered defect detection</p>
      </div>
      <div className="inspect-wrapper">
        <form onSubmit={handleInspect} className="form-card">
          <div className="form-group">
            <label className="form-label">Select Product</label>
            <select className="form-select" value={selectedProduct} onChange={e => setSelectedProduct(e.target.value)} required>
              <option value="">Choose product...</option>
              {products.map(p => <option key={p.id} value={p.id}>{p.product_name} ({p.product_code})</option>)}
            </select>
          </div>
          <div className="form-group">
            <label className="form-label">Upload Image</label>
            <div className="dropzone">
              {preview ? (
                <div>
                  <img src={preview} alt="preview" className="preview-img" />
                  <p className="file-name">{selectedFile?.name}</p>
                  <button type="button" className="btn-remove" onClick={() => { setPreview(null); setSelectedFile(null); setResult(null) }}>Remove</button>
                </div>
              ) : (
                <div>
                  <p className="drop-text">Drop image here or click</p>
                  <p className="drop-sub">JPG, PNG, BMP, TIFF</p>
                  <input id="fileInput" type="file" onChange={(e) => {
                  const files = Array.from(e.target.files)
                  if (files.length > 1) {
                    setBatchFiles(files)
                  } else if (files.length === 1) {
                    handleFileChange(e)
                  }
                }} accept="image/*" multiple className="file-input" />
                </div>
              )}
            </div>
          </div>

          


          <div style={{ marginTop: '12px', textAlign: 'center' }}>
            <button
              type="button"
              onClick={() => setShowCamera(true)}
              className="btn-secondary"
              style={{ padding: '12px 24px', fontSize: '15px' }}
            >
              📷 Or Capture from Camera
            </button>
          </div>

          <button type="submit" disabled={loading} className="btn-primary btn-full">
            {loading ? 'AI Analyzing...' : 'Run AI Inspection'}
          </button>
        </form>
        
        
          

          

{result?.type === 'success' && <ResultDisplay data={result.data} previewUrl={preview} />}
        {result?.type === 'error' && <div className="error-box"><p>{result.message}</p></div>}
      </div>
    </div>
  )

  const ResultDisplay = ({ data, previewUrl }) => {
    const ai = data.ai_detection || {}
    const qa = data.quality_analysis || {}
    const detected = ai.defect_detected
    return (
      <div className="result-wrapper">
        <div className="result-header" style={{
          background: detected ? 'rgba(239,68,68,0.08)' : 'rgba(34,197,94,0.08)',
          borderColor: detected ? 'rgba(239,68,68,0.3)' : 'rgba(34,197,94,0.3)'
        }}>
          <div className="result-icon">{detected ? 'X' : '✓'}</div>
          <h2 className="result-title" style={{ color: detected ? '#f87171' : '#34d399' }}>
            {ai.decision === 'REJECT' ? 'REJECTED' : ai.decision === 'REWORK' ? 'REWORK REQUIRED' : 'PASSED'}
          </h2>
          <p className="result-id">Inspection #{String(data.inspection?.id || '').slice(-4)}</p>
        </div>
        <div className="section">
          <h3 className="section-title">Image Comparison</h3>
          <div className="image-compare">
            <div className="img-box">
              <p className="img-label">Original</p>
              <img src={previewUrl || ''} alt="original" className="compare-img" />
            </div>
            <div className="img-arrow">→</div>
            <div className="img-box">
              <p className="img-label">AI Detection</p>
              <img src={data.result_image_url} alt="result" className="compare-img"
                onError={e => e.target.src = previewUrl || ''} />
              {detected && ai.location && (
                <div className="loc-info">
                  <p>X: {ai.location.x} | Y: {ai.location.y}</p>
                  <p>W: {ai.location.width} | H: {ai.location.height}</p>
                </div>
              )}
            </div>
          </div>
        </div>
        <div className="section">
          <h3 className="section-title">Image Preprocessing</h3>
          <div className="steps-grid">
            {(data.preprocessing?.steps || []).map((s, i) => (
              <div key={i} className="step-item">
                <span className="step-check">✓</span>
                <span>{s}</span>
              </div>
            ))}
          </div>
          <div className="preprocess-info">
            <span>Original: {data.preprocessing?.original_size}</span>
            <span>→</span>
            <span>Processed: {data.preprocessing?.processed_size}</span>
          </div>
        </div>
        <div className="section">
          <h3 className="section-title">Image Quality</h3>
          <div className="qa-grid">
            <QACard label="Resolution" value={`${qa.resolution?.width}x${qa.resolution?.height}`} status={qa.resolution?.status} />
            <QACard label="Brightness" value={qa.brightness?.value} status={qa.brightness?.status} />
            <QACard label="Sharpness" value={qa.sharpness?.value} status={qa.sharpness?.status} />
            <QACard label="Noise" value={qa.noise?.value} status={qa.noise?.status} />
          </div>
          <div className="qa-overall">
            <div className="qa-score">Overall: {qa.overall?.score}%</div>
            <div className="qa-status">{qa.overall?.status}</div>
          </div>
        </div>
        {detected && (
          <div className="section">
            <h3 className="section-title">AI Detection Results</h3>
            <div className="ai-grid">
              <InfoBox label="Defect Type" value={ai.defect_type} color="#f87171" />
              <InfoBox label="Confidence" value={`${Math.round((ai.confidence || 0) * 100)}%`} color="white" />
              <InfoBox label="Severity Score" value={`${ai.severity_score}/100`} color="#fbbf24" />
              <InfoBox label="Severity Level" value={ai.severity_level} color="#f87171" />
            </div>
          </div>
        )}
        {ai.timing && (
          <div className="section">
            <h3 className="section-title">Processing Performance</h3>
            <div className="timing-grid">
              <div className="timing-box">
                <p className="timing-label">Preprocessing</p>
                <p className="timing-value">{ai.timing.preprocessing_ms} ms</p>
              </div>
              <div className="timing-box">
                <p className="timing-label">AI Inference</p>
                <p className="timing-value">{ai.timing.inference_ms} ms</p>
              </div>
              <div className="timing-box">
                <p className="timing-label">Total</p>
                <p className="timing-value" style={{color:'#60a5fa'}}>{ai.timing.total_ms} ms</p>
              </div>
            </div>
          </div>
        )}
        <div className={`decision-box ${
          ai.decision === 'REJECT' ? 'decision-fail' :
          ai.decision === 'REWORK' ? 'decision-rework' : 'decision-pass'
        }`}>
          <h3 className="decision-title">FINAL QUALITY DECISION</h3>
          <div className="decision-result" style={{
            color: ai.decision === 'REJECT' ? '#f87171' :
                   ai.decision === 'REWORK' ? '#fbbf24' : '#34d399'
          }}>
            {ai.decision === 'REJECT' ? 'X REJECT' :
             ai.decision === 'REWORK' ? '! REWORK' : '✓ PASS'}
          </div>
          <p className="decision-reason">{ai.recommendation}</p>
        </div>
        <button className="btn-secondary" onClick={() => { setCurrentPage('inspections'); fetchInspections() }}>
          View All Inspections
        </button>
      </div>
    )
  }

  const QACard = ({ label, value, status }) => {
    const good = status === 'Good' || status === 'Low' || status === 'Suitable'
    return (
      <div className="qa-card">
        <p className="qa-label">{label}</p>
        <p className="qa-value">{value}</p>
        <p className="qa-status-txt" style={{ color: good ? '#34d399' : '#fbbf24' }}>
          {good ? 'OK' : '!'} {status}
        </p>
      </div>
    )
  }

  const InfoBox = ({ label, value, color }) => (
    <div className="info-box">
      <p className="info-label">{label}</p>
      <p className="info-value" style={{ color }}>{value || '-'}</p>
    </div>
  )

  const InspectionsPage = () => {
    const filtered = inspections.filter(i => {
      if (filterDecision !== 'all' && i.decision !== filterDecision) return false
      if (filterProduct !== 'all' && i.product_name !== filterProduct) return false
      return true
    })
    const uniqueProducts = [...new Set(inspections.map(i => i.product_name).filter(Boolean))]

    const exportCSV = async () => {
      const t = localStorage.getItem('token')
      const r = await fetch('http://127.0.0.1:8000/inspections/export/csv', {
        headers: { 'Authorization': `Bearer ${t}` }
      })
      if (r.ok) {
        const blob = await r.blob()
        const url = URL.createObjectURL(blob)
        const a = document.createElement('a')
        a.href = url
        a.download = 'inspections.csv'
        a.click()
        URL.revokeObjectURL(url)
      }
    }

    return (
      <div className="page">
        <div className="page-header" style={{display:'flex', justifyContent:'space-between', alignItems:'center'}}>
          <div>
            <h2>Inspection History</h2>
            <p>All AI inspection records</p>
          </div>
          <button className="btn-primary" onClick={exportCSV}>Export CSV</button>
        </div>
        <div className="filter-row">
          <select className="form-select filter-select" value={filterDecision} onChange={e => setFilterDecision(e.target.value)}>
            <option value="all">All Decisions</option>
            <option value="PASS">PASS</option>
            <option value="REWORK">REWORK</option>
            <option value="REJECT">REJECT</option>
          </select>
          <select className="form-select filter-select" value={filterProduct} onChange={e => setFilterProduct(e.target.value)}>
            <option value="all">All Products</option>
            {uniqueProducts.map(p => <option key={p} value={p}>{p}</option>)}
          </select>
          <div className="filter-count">Showing {filtered.length} of {inspections.length}</div>
        </div>
        <div className="section">
          {filtered.length === 0 ? (
            <p className="empty">No inspections match your filters.</p>
          ) : (
            <table className="table">
              <thead>
                <tr>
                  <th>ID</th><th>Image</th><th>Product</th><th>Defect</th>
                  <th>Confidence</th><th>Severity</th><th>Decision</th><th>Date</th>
                </tr>
              </thead>
              <tbody>
                {filtered.map(i => (
                  <tr key={i.id} onClick={() => setSelectedInspection(i)}>
                    <td className="td-id">#{String(i.id).slice(-4)}</td>
                    <td>{i.image_filename}</td>
                    <td>{i.product_name || '-'}</td>
                    <td>{i.defect_detected ? <span style={{color:'#f87171', fontWeight:600}}>{i.defect_type}</span> : <span style={{color:'#34d399'}}>None</span>}</td>
                    <td>{i.confidence ? `${Math.round(i.confidence * 100)}%` : '-'}</td>
                    <td>{i.severity_level && i.severity_level !== 'None' ? getBadge(i.severity_level) : '-'}</td>
                    <td>{i.decision ? getBadge(i.decision) : '-'}</td>
                    <td className="td-date">{new Date(i.created_at).toLocaleDateString()}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
        {selectedInspection && (
          <div className="modal-overlay" onClick={() => setSelectedInspection(null)}>
            <div className="modal" onClick={e => e.stopPropagation()}>
              <div className="modal-header">
                <h3>Inspection Report #{String(selectedInspection.id).slice(-4)}</h3>
                <button className="btn-close" onClick={() => setSelectedInspection(null)}>X</button>
              </div>
              <div className="modal-body">
                <div className={`report-status ${
                  selectedInspection.decision === 'REJECT' ? 'report-fail' :
                  selectedInspection.decision === 'REWORK' ? 'report-rework' : 'report-pass'
                }`}>
                  <p style={{ fontSize: '24px', fontWeight: 700,
                    color: selectedInspection.decision === 'REJECT' ? '#f87171' :
                           selectedInspection.decision === 'REWORK' ? '#fbbf24' : '#34d399'
                  }}>
                    {selectedInspection.decision}
                  </p>
                </div>
                <div className="report-section">
                  <h4 className="report-h4">Product Information</h4>
                  <div className="report-grid">
                    <div><span className="report-label">Product:</span> <span className="report-value">{selectedInspection.product_name}</span></div>
                    <div><span className="report-label">Code:</span> <span className="report-value">{selectedInspection.product_code}</span></div>
                    <div><span className="report-label">Image:</span> <span className="report-value">{selectedInspection.image_filename}</span></div>
                    <div><span className="report-label">Date:</span> <span className="report-value">{new Date(selectedInspection.created_at).toLocaleString()}</span></div>
                  </div>
                </div>
                {selectedInspection.defect_detected && (
                  <div className="report-section">
                    <h4 className="report-h4">Defect Information</h4>
                    <div className="report-grid">
                      <div><span className="report-label">Type:</span> <span className="report-value" style={{color:'#f87171'}}>{selectedInspection.defect_type}</span></div>
                      <div><span className="report-label">Confidence:</span> <span className="report-value">{Math.round((selectedInspection.confidence || 0) * 100)}%</span></div>
                      <div><span className="report-label">Severity:</span> <span className="report-value" style={{color:'#fbbf24'}}>{selectedInspection.severity_score}/100 ({selectedInspection.severity_level})</span></div>
                    </div>
                  </div>
                )}
                <div className="report-section">
                  <h4 className="report-h4">Recommendation</h4>
                  <p style={{ color: '#94a3b8', fontSize: '14px' }}>{selectedInspection.recommendation}</p>
                </div>

                <div className="report-section">
                  <h4 className="report-h4">Actions</h4>
                  <button
                    className="btn-primary"
                    style={{ marginTop: '8px' }}
                    onClick={async () => {
                      const token = localStorage.getItem('token')
                      const r = await fetch(`http://127.0.0.1:8000/inspections/${selectedInspection.id}/pdf`, {
                        headers: { 'Authorization': `Bearer ${token}` }
                      })
                      if (r.ok) {
                        const blob = await r.blob()
                        const url = URL.createObjectURL(blob)
                        const a = document.createElement('a')
                        a.href = url
                        a.download = `inspection_${String(selectedInspection.id).slice(-8)}.pdf`
                        a.click()
                        URL.revokeObjectURL(url)
                      } else {
                        alert('Failed to download PDF')
                      }
                    }}
                  >
                    📄 Download PDF Report
                  </button>
                </div>

              </div>
            </div>
          </div>
        )}
      </div>
    )
  }

  const AnalyticsPage = () => {
    if (!analytics) return <div className="page"><div className="page-header"><h2>Analytics</h2><p>Loading...</p></div></div>
    const maxTrend = Math.max(...analytics.daily_trend.map(d => d.total), 1)
    const maxDefect = Math.max(...Object.values(analytics.defect_distribution), 1)
    const maxSeverity = Math.max(...Object.values(analytics.severity_distribution), 1)
    return (
      <div className="page">
        <div className="page-header">
          <h2>Analytics Dashboard</h2>
          <p>Production quality insights</p>
        </div>
        <div className="stat-grid">
          <div className="stat-card" style={{borderColor:'#3b82f633'}}>
            <div className="stat-label">Total</div>
            <div className="stat-value" style={{color:'#3b82f6'}}>{analytics.total}</div>
          </div>
          <div className="stat-card" style={{borderColor:'#34d39933'}}>
            <div className="stat-label">Passed</div>
            <div className="stat-value" style={{color:'#34d399'}}>{analytics.passed}</div>
          </div>
          <div className="stat-card" style={{borderColor:'#fbbf2433'}}>
            <div className="stat-label">Rework</div>
            <div className="stat-value" style={{color:'#fbbf24'}}>{analytics.reworked}</div>
          </div>
          <div className="stat-card" style={{borderColor:'#f8717133'}}>
            <div className="stat-label">Rejected</div>
            <div className="stat-value" style={{color:'#f87171'}}>{analytics.rejected}</div>
          </div>
        </div>
        <div className="rate-grid">
          <div className="rate-card">
            <div className="rate-label">Defect Rate</div>
            <div className="rate-value" style={{color:'#f87171'}}>{analytics.defect_rate}%</div>
          </div>
          <div className="rate-card">
            <div className="rate-label">Pass Rate</div>
            <div className="rate-value" style={{color:'#34d399'}}>{analytics.pass_rate}%</div>
          </div>
        </div>
        <div className="section">
          <h3 className="section-title">Defect Type Distribution</h3>
          <div className="bar-chart">
            {Object.entries(analytics.defect_distribution).map(([t, c]) => (
              <div key={t} className="bar-row">
                <div className="bar-label">{t}</div>
                <div className="bar-track">
                  <div className="bar-fill" style={{width: `${(c/maxDefect)*100}%`, background: 'linear-gradient(90deg, #f87171, #fbbf24)'}}></div>
                </div>
                <div className="bar-value">{c}</div>
              </div>
            ))}
          </div>
        </div>
        <div className="section">
          <h3 className="section-title">Severity Distribution</h3>
          <div className="bar-chart">
            {Object.entries(analytics.severity_distribution).map(([l, c]) => {
              const colors = {Critical: '#f87171', High: '#fb923c', Medium: '#fbbf24', Low: '#34d399'}
              return (
                <div key={l} className="bar-row">
                  <div className="bar-label">{l}</div>
                  <div className="bar-track">
                    <div className="bar-fill" style={{width: `${(c/maxSeverity)*100}%`, background: colors[l]}}></div>
                  </div>
                  <div className="bar-value">{c}</div>
                </div>
              )
            })}
          </div>
        </div>
        <div className="section">
          <h3 className="section-title">7-Day Trend</h3>
          <div className="trend-chart">
            {analytics.daily_trend.map((d, i) => (
              <div key={i} className="trend-column">
                <div className="trend-bars">
                  <div className="trend-bar" style={{height: `${(d.total/maxTrend)*100}%`, background: '#3b82f6'}}></div>
                  <div className="trend-bar" style={{height: `${(d.defective/maxTrend)*100}%`, background: '#f87171'}}></div>
                </div>
                <div className="trend-label">{d.date}</div>
              </div>
            ))}
          </div>
          <div className="trend-legend">
            <span><span className="legend-dot" style={{background:'#3b82f6'}}></span> Total</span>
            <span><span className="legend-dot" style={{background:'#f87171'}}></span> Defective</span>
          </div>
        </div>
        {analytics.product_stats && analytics.product_stats.length > 0 && (
          <div className="section">
            <h3 className="section-title">Product Quality Analysis</h3>
            <div className="bar-chart">
              {analytics.product_stats.map((p, i) => (
                <div key={i} className="bar-row">
                  <div className="bar-label">{p.product}</div>
                  <div className="bar-track">
                    <div className="bar-fill" style={{width: `${p.pass_rate}%`, background: p.pass_rate > 80 ? 'linear-gradient(90deg, #34d399, #60a5fa)' : p.pass_rate > 60 ? 'linear-gradient(90deg, #fbbf24, #fb923c)' : 'linear-gradient(90deg, #f87171, #ef4444)'}}></div>
                  </div>
                  <div className="bar-value">{p.pass_rate}%</div>
                </div>
              ))}
            </div>
          </div>
        )}
        <div className="section">
          <h3 className="section-title">Summary Metrics</h3>
          <div className="qa-grid">
            <div className="qa-card">
              <p className="qa-label">Avg Confidence</p>
              <p className="qa-value">{analytics.avg_confidence}%</p>
            </div>
            <div className="qa-card">
              <p className="qa-label">Avg Severity</p>
              <p className="qa-value">{analytics.avg_severity}</p>
            </div>
            <div className="qa-card">
              <p className="qa-label">Defective</p>
              <p className="qa-value" style={{color:'#f87171'}}>{analytics.defective}</p>
            </div>
            <div className="qa-card">
              <p className="qa-label">Passed</p>
              <p className="qa-value" style={{color:'#34d399'}}>{analytics.passed}</p>
            </div>
          </div>
        </div>
      </div>
    )
  }

  const ModelPerformancePage = () => {
    if (!modelPerf) return <div className="page"><div className="page-header"><h2>Model Performance</h2><p>Loading...</p></div></div>
    return (
      <div className="page">
        <div className="page-header">
          <h2>Model Performance Metrics</h2>
          <p>Real evaluation metrics calculated from stored inspections</p>
        </div>
        <div className="stat-grid">
          <div className="stat-card" style={{borderColor:'#3b82f633'}}>
            <div className="stat-label">Accuracy</div>
            <div className="stat-value" style={{color:'#3b82f6'}}>{modelPerf.accuracy}%</div>
          </div>
          <div className="stat-card" style={{borderColor:'#8b5cf633'}}>
            <div className="stat-label">Precision</div>
            <div className="stat-value" style={{color:'#8b5cf6'}}>{modelPerf.precision}%</div>
          </div>
          <div className="stat-card" style={{borderColor:'#34d39933'}}>
            <div className="stat-label">Recall</div>
            <div className="stat-value" style={{color:'#34d399'}}>{modelPerf.recall}%</div>
          </div>
          <div className="stat-card" style={{borderColor:'#fbbf2433'}}>
            <div className="stat-label">F1 Score</div>
            <div className="stat-value" style={{color:'#fbbf24'}}>{modelPerf.f1_score}%</div>
          </div>
        </div>
        <div className="section">
          <h3 className="section-title">Confusion Matrix</h3>
          <div className="qa-grid">
            <div className="qa-card">
              <p className="qa-label">True Positives</p>
              <p className="qa-value" style={{color:'#34d399'}}>{modelPerf.true_positives}</p>
            </div>
            <div className="qa-card">
              <p className="qa-label">True Negatives</p>
              <p className="qa-value" style={{color:'#34d399'}}>{modelPerf.true_negatives}</p>
            </div>
            <div className="qa-card">
              <p className="qa-label">False Positives</p>
              <p className="qa-value" style={{color:'#f87171'}}>{modelPerf.false_positives}</p>
            </div>
            <div className="qa-card">
              <p className="qa-label">False Negatives</p>
              <p className="qa-value" style={{color:'#f87171'}}>{modelPerf.false_negatives}</p>
            </div>
          </div>
        </div>
        <div className="section">
          <h3 className="section-title">Test Summary</h3>
          <div className="report-grid">
            <div><span className="report-label">Total Tested:</span> <span className="report-value">{modelPerf.total_tested}</span></div>
            <div><span className="report-label">Defective Found:</span> <span className="report-value">{modelPerf.defective_found}</span></div>
            <div><span className="report-label">Passed:</span> <span className="report-value">{modelPerf.passed}</span></div>
          </div>
        </div>
      </div>
    )
  }

  const DatasetPage = () => (
    <div className="page">
      <div className="page-header">
        <h2>MVTec AD Dataset</h2>
        <p>Browse industrial anomaly detection dataset</p>
      </div>
      <div className="dataset-layout">
        <div className="dataset-sidebar">
          <h4 className="dataset-heading">Categories</h4>
          {categories.map(c => (
            <button key={c} className={`cat-btn ${selectedCategory === c ? 'active' : ''}`}
              onClick={() => { setSelectedCategory(c); fetchCategoryImages(c) }}>
              {c.replace('_', ' ')}
            </button>
          ))}
        </div>
        <div className="dataset-main">
          {selectedCategory ? (
            <>
              <h4 className="dataset-title">{selectedCategory.replace('_', ' ')}</h4>
              {categoryImages.length === 0 ? (
                <p className="empty">No images found</p>
              ) : (
                <>
                  <p className="dataset-count">{categoryImages.length} images</p>
                  <div className="img-grid">
                    {categoryImages.slice(0, 20).map((img, idx) => (
                      <div key={idx} className="img-cell">
                        <img src={`http://127.0.0.1:8000/dataset/image/${selectedCategory}/${img}`}
                          alt={img} className="grid-img"
                          onError={e => { e.target.style.display='none'; e.target.parentElement.innerHTML=`<div class="no-img">${img}</div>` }} />
                      </div>
                    ))}
                  </div>
                </>
              )}
            </>
          ) : (
            <p className="empty">Select a category to view images</p>
          )}
        </div>
      </div>
    </div>
  )

  if (loggedIn && user) {
    return (
      <div className="app">
        <Navbar />
        <div className="app-body">
          <Sidebar />
          <div className="app-content">
            {currentPage === 'dashboard' && <DashboardPage />}
            {currentPage === 'inspect' && <InspectPage />}
            {currentPage === 'inspections' && <InspectionsPage />}
            {currentPage === 'analytics' && <AnalyticsPage />}
            {currentPage === 'model' && <ModelPerformancePage />}
            {currentPage === 'dataset' && <DatasetPage />}
          </div>
        </div>
      </div>
    )
  }

  return (
    <div className="login-page">
      <div className="login-card">
        <div className="login-logo">V</div>
        <h1 className="login-title">VisionInspect <span style={{color:'#3b82f6'}}>AI</span></h1>
        <p className="login-sub">Manufacturing Quality Control</p>
        
        <form onSubmit={handleLogin} className="login-form">
          <div className="form-group">
            <label className="form-label">Email</label>
            <input type="email" className="form-input" value={email} onChange={e => setEmail(e.target.value)} required />
          </div>
          <div className="form-group">
            <label className="form-label">Password</label>
            <input type="password" className="form-input" value={password} onChange={e => setPassword(e.target.value)} required />
          </div>

          


          <div style={{ marginTop: '12px', textAlign: 'center' }}>
            <button
              type="button"
              onClick={() => setShowCamera(true)}
              className="btn-secondary"
              style={{ padding: '12px 24px', fontSize: '15px' }}
            >
              📷 Or Capture from Camera
            </button>
          </div>

          <button type="submit" disabled={loading} className="btn-primary btn-full">
            {loading ? 'Signing in...' : 'Sign In'}
          </button>
        </form>
        {message && <div className="login-msg">{message}</div>}
        <div className="login-demo">
          <p>engineer@gmail.com / password123</p>
          <p>supervisor@gmail.com / password123</p>
        </div>
      </div>
    </div>
  )
}

export default App

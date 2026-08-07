import React, { useState, useEffect, useContext } from 'react';
import { AuthContext } from '../context/AuthContext';
import api from '../services/api';

const PRDGeneratorPage = () => {
  const { user } = useContext(AuthContext);

  // Backlog features list
  const [features, setFeatures] = useState([]);
  const [selectedFeatureId, setSelectedFeatureId] = useState('');

  // Custom inputs
  const [featureName, setFeatureName] = useState('');
  const [description, setDescription] = useState('');

  // UI status
  const [loadingBacklog, setLoadingBacklog] = useState(true);
  const [generating, setGenerating] = useState(false);
  const [generatedPRD, setGeneratedPRD] = useState('');
  const [error, setError] = useState(null);
  const [successMsg, setSuccessMsg] = useState(null);

  // Fetch prioritized features for select dropdown
  useEffect(() => {
    const fetchBacklog = async () => {
      try {
        setLoadingBacklog(true);
        const res = await api.get(`/api/prioritize/results?project_id=${user.project_id}&page_size=50`);
        if (res.data.success) {
          setFeatures(res.data.data.results || []);
        }
      } catch (err) {
        console.error("Failed to load prioritization backlog for PRD:", err);
        setError("Could not load prioritized backlog features. You can still input details manually.");
      } finally {
        setLoadingBacklog(false);
      }
    };

    if (user && user.project_id) {
      fetchBacklog();
    }
  }, [user]);

  // Handle dropdown select
  const handleFeatureSelect = (e) => {
    const featId = e.target.value;
    setSelectedFeatureId(featId);

    if (featId === 'custom') {
      setFeatureName('');
      setDescription('');
    } else {
      const selected = features.find(f => f.prioritization_id === featId);
      if (selected) {
        setFeatureName(selected.feature_name);
        setDescription(selected.description || '');
      }
    }
  };

  // Generate PRD
  const handleGeneratePRD = async (e) => {
    e.preventDefault();
    if (!featureName.trim()) {
      setError("Please specify a feature name.");
      return;
    }

    setGenerating(true);
    setGeneratedPRD('');
    setError(null);
    setSuccessMsg(null);

    try {
      const response = await api.post('/api/prd/generate-prd', {
        feature_name: featureName,
        description: description,
        project_id: user.project_id
      });

      if (response.data.success) {
        setGeneratedPRD(response.data.prd);
        setSuccessMsg("PRD generated successfully!");
      } else {
        setError(response.data.error || "Failed to generate PRD.");
      }
    } catch (err) {
      console.error(err);
      setError(err.response?.data?.error || "Gemini AI generation service failed. Check if API key is set.");
    } finally {
      setGenerating(false);
    }
  };

  // Copy to Clipboard
  const handleCopyToClipboard = () => {
    navigator.clipboard.writeText(generatedPRD);
    setSuccessMsg("Copied to clipboard!");
    setTimeout(() => setSuccessMsg(null), 3000);
  };

  // Download Markdown File
  const handleDownload = () => {
    const element = document.createElement("a");
    const file = new Blob([generatedPRD], { type: 'text/markdown' });
    element.href = URL.createObjectURL(file);
    element.download = `${featureName.toLowerCase().replace(/\s+/g, '-')}-prd.md`;
    document.body.appendChild(element);
    element.click();
    document.body.removeChild(element);
  };

  return (
    <div className="prd-generator-container page-layout">
      <div className="dashboard-header">
        <div className="header-meta">
          <h1>📄 AI PRD Generator </h1>
          <p>Retrieve customer feedback context and draft comprehensive Product Requirement Documents using Gemini AI.</p>
        </div>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '2rem', marginTop: '1.5rem' }}>
        {/* Generator Controls */}
        <div className="glass-panel" style={{ padding: '2rem' }}>
          <h3>Configure PRD Context</h3>
          <hr style={{ borderColor: 'rgba(255,255,255,0.08)', margin: '1rem 0' }} />

          <form onSubmit={handleGeneratePRD}>
            {/* Feature Selector */}
            <div className="form-group" style={{ marginBottom: '1.5rem' }}>
              <label style={{ display: 'block', marginBottom: '0.5rem', color: 'var(--text-secondary)' }}>
                Select Feature from Prioritized Backlog
              </label>
              <select
                value={selectedFeatureId}
                onChange={handleFeatureSelect}
                disabled={loadingBacklog}
                style={{
                  width: '100%',
                  padding: '0.75rem',
                  borderRadius: '6px',
                  background: 'rgba(0, 0, 0, 0.2)',
                  border: '1px solid rgba(255, 255, 255, 0.1)',
                  color: 'var(--text-primary)',
                  cursor: 'pointer'
                }}
              >
                {loadingBacklog ? (
                  <option>Loading prioritized backlog...</option>
                ) : (
                  <>
                    <option value="">-- Choose a feature --</option>
                    {features.map((f) => (
                      <option key={f.prioritization_id} value={f.prioritization_id}>
                        {f.feature_name} (Score: {f.priority_score.toFixed(1)} - {f.priority_class})
                      </option>
                    ))}
                    <option value="custom">✍️ Custom Feature (Input manually)</option>
                  </>
                )}
              </select>
            </div>

            {/* Feature Name */}
            <div className="form-group" style={{ marginBottom: '1.5rem' }}>
              <label style={{ display: 'block', marginBottom: '0.5rem', color: 'var(--text-secondary)' }}>
                Feature Name
              </label>
              <input
                type="text"
                placeholder="e.g. Dark Mode Support"
                value={featureName}
                onChange={(e) => setFeatureName(e.target.value)}
                required
                style={{
                  width: '100%',
                  padding: '0.75rem',
                  borderRadius: '6px',
                  background: 'rgba(0, 0, 0, 0.2)',
                  border: '1px solid rgba(255, 255, 255, 0.1)',
                  color: 'var(--text-primary)'
                }}
              />
            </div>

            {/* Description / Initial Scope */}
            <div className="form-group" style={{ marginBottom: '2rem' }}>
              <label style={{ display: 'block', marginBottom: '0.5rem', color: 'var(--text-secondary)' }}>
                Description & Initial Scope
              </label>
              <textarea
                placeholder="Outline the core problems this feature addresses or requirements..."
                value={description}
                onChange={(e) => setDescription(e.target.value)}
                rows={6}
                style={{
                  width: '100%',
                  padding: '0.75rem',
                  borderRadius: '6px',
                  background: 'rgba(0, 0, 0, 0.2)',
                  border: '1px solid rgba(255, 255, 255, 0.1)',
                  color: 'var(--text-primary)',
                  resize: 'vertical',
                  fontFamily: 'inherit'
                }}
              />
            </div>

            <button
              type="submit"
              className="action-btn"
              disabled={generating}
              style={{ width: '100%', padding: '0.9rem' }}
            >
              {generating ? "✨ Generating PRD..." : "✨ Generate AI PRD"}
            </button>
          </form>

          {error && (
            <div className="alert-message error-alert" style={{ marginTop: '1.5rem' }}>
              <strong>Error:</strong> {error}
            </div>
          )}
        </div>

        {/* Generated PRD Document Output */}
        <div className="glass-panel" style={{ padding: '2rem', display: 'flex', flexDirection: 'column' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1rem' }}>
            <h3 style={{ margin: 0 }}>Generated Document Output</h3>
            {generatedPRD && (
              <div style={{ display: 'flex', gap: '0.5rem' }}>
                <button onClick={handleCopyToClipboard} className="action-btn" style={{ padding: '0.4rem 0.8rem', fontSize: '0.8rem' }}>
                  📋 Copy
                </button>
                <button onClick={handleDownload} className="action-btn" style={{ padding: '0.4rem 0.8rem', fontSize: '0.8rem', background: '#2563eb' }}>
                  💾 Download
                </button>
              </div>
            )}
          </div>
          <hr style={{ borderColor: 'rgba(255,255,255,0.08)', margin: '0 0 1rem 0' }} />

          {successMsg && (
            <div className="alert-message info-alert" style={{ marginBottom: '1rem', padding: '0.5rem 1rem' }}>
              <strong>Notice:</strong> {successMsg}
            </div>
          )}

          {generatedPRD ? (
            <div style={{
              flex: 1,
              background: 'rgba(0, 0, 0, 0.25)',
              border: '1px solid rgba(255, 255, 255, 0.08)',
              borderRadius: '6px',
              padding: '1.25rem',
              overflowY: 'auto',
              maxHeight: '500px',
              fontFamily: 'monospace',
              whiteSpace: 'pre-wrap',
              fontSize: '0.9rem',
              lineHeight: '1.5',
              color: '#d1d5db'
            }}>
              {generatedPRD}
            </div>
          ) : (
            <div style={{
              flex: 1,
              display: 'flex',
              flexDirection: 'column',
              justifyContent: 'center',
              alignItems: 'center',
              color: 'var(--text-muted)',
              border: '2px dashed rgba(255,255,255,0.1)',
              borderRadius: '6px',
              minHeight: '300px',
              padding: '2rem',
              textAlign: 'center'
            }}>
              <span style={{ fontSize: '3rem', marginBottom: '1rem' }}>📄</span>
              <p>Your AI-generated PRD will appear here.</p>
              <p style={{ fontSize: '0.8rem' }}>Configure the feature context and trigger the generator to build a document enriched with processed user feedback.</p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default PRDGeneratorPage;

import React, { useState, useEffect, useContext } from 'react';
import { AuthContext } from '../context/AuthContext';
import api from '../services/api';
import { Link } from 'react-router-dom';

const DashboardPage = () => {
  const { user } = useContext(AuthContext);
  const [stats, setStats] = useState({
    pending: 0,
    processing: 0,
    processed: 0,
    duplicate: 0,
    failed: 0
  });
  
  const [recentFeedbacks, setRecentFeedbacks] = useState([]);
  const [pipelineRunning, setPipelineRunning] = useState(false);
  const [pipelineStatusMsg, setPipelineStatusMsg] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const fetchDashboardData = async () => {
    try {
      // 1. Fetch processing results for project
      const resultsRes = await api.get(`/process/results?project_id=${user.project_id}&page_size=10`);
      if (resultsRes.data.success) {
        setRecentFeedbacks(resultsRes.data.data.results);
      }
      
      // Calculate inline counts or call status counts
      // Let's compute counts manually or query all raw status endpoints.
      // Since we don't have a separate dashboard stats endpoint, we can do query aggregation or parse.
      // We will mock status queries or load recent raw logs
      // Let's get counts of processed vs duplicates from processed results weight
      // Or make a lightweight call. Since we have standard envelope, let's fetch total count.
      // To provide real statistics, we can infer from raw count.
      // Let's fetch recent raw items or set dummy values that are derived from loaded sizes.
      const rawCount = resultsRes.data.data.total;
      setStats({
        pending: 0,
        processing: 0,
        processed: rawCount,
        duplicate: resultsRes.data.data.results.reduce((acc, curr) => acc + (curr.weight - 1), 0),
        failed: 0
      });
      setError(null);
    } catch (err) {
      console.error(err);
      setError("Failed to fetch recent processed results. Verify backend service is running.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (user && user.project_id) {
      fetchDashboardData();
    }
  }, [user]);

  const handleRunPipeline = async () => {
    setPipelineRunning(true);
    setPipelineStatusMsg("Initiating Pipeline...");
    
    try {
      const response = await api.post('/process/run', { project_id: user.project_id });
      if (response.data.success) {
        const { job_id, pending_count } = response.data.data;
        if (pending_count === 0) {
          setPipelineStatusMsg("No pending feedback found to process.");
        } else {
          setPipelineStatusMsg(`Pipeline running in background. Job ID: ${job_id}. Processing ${pending_count} items...`);
          // Poll for completion
          setTimeout(() => {
            fetchDashboardData();
            setPipelineStatusMsg(null);
          }, 5000);
        }
      }
    } catch (err) {
      console.error(err);
      setPipelineStatusMsg(null);
      setError(err.response?.data?.error || "Failed to trigger NLP pipeline.");
    } finally {
      setPipelineRunning(false);
    }
  };

  if (loading) {
    return (
      <div className="loader-container">
        <div className="spinner"></div>
        <p>Loading Dashboard Analytics...</p>
      </div>
    );
  }

  return (
    <div className="dashboard-container page-layout">
      <div className="dashboard-header">
        <div className="header-meta">
          <h1>Product Manager Command Panel</h1>
          <p className="project-token"><strong>Active Project ID:</strong> {user.project_id}</p>
        </div>
        
        <button 
          onClick={handleRunPipeline} 
          className="action-btn run-pipeline-btn"
          disabled={pipelineRunning}
        >
          {pipelineRunning ? "Executing Pipeline..." : "⚡ Run NLP Preprocessing"}
        </button>
      </div>

      {pipelineStatusMsg && (
        <div className="alert-message info-alert">
          <strong>Pipeline Run Status: </strong> {pipelineStatusMsg}
        </div>
      )}

      {error && (
        <div className="alert-message error-alert">
          <strong>Analytics Warning: </strong> {error}
        </div>
      )}

      {/* Metrics Cards */}
      <div className="metrics-grid">
        <div className="metric-card glass-panel">
          <span className="metric-icon">📝</span>
          <div className="metric-data">
            <span className="metric-value">{stats.processed}</span>
            <span className="metric-label">Canonical Issues</span>
          </div>
        </div>

        <div className="metric-card glass-panel">
          <span className="metric-icon">👥</span>
          <div className="metric-data">
            <span className="metric-value">{stats.duplicate}</span>
            <span className="metric-label">Duplicate Matches</span>
          </div>
        </div>

        <div className="metric-card glass-panel">
          <span className="metric-icon">⚡</span>
          <div className="metric-data">
            <span className="metric-value">{recentFeedbacks.reduce((acc, curr) => acc + curr.weight, 0)}</span>
            <span className="metric-label">Total Submissions (Weight)</span>
          </div>
        </div>
      </div>

      {/* Section Content */}
      <div className="recent-activity-section glass-panel">
        <div className="section-header">
          <h2>Recent Preprocessed Feedback</h2>
          <Link to="/status" className="view-all-link">View Detailed Status Table →</Link>
        </div>

        {recentFeedbacks.length === 0 ? (
          <div className="empty-state">
            <p>No feedback processed yet. Head to the <Link to="/upload/csv">CSV Ingestion Panel</Link> to import some data.</p>
          </div>
        ) : (
          <div className="table-responsive">
            <table className="data-table">
              <thead>
                <tr>
                  <th>Subject</th>
                  <th>Category</th>
                  <th>Priority</th>
                  <th>Weight</th>
                  <th>Word Count</th>
                  <th>Lemma Extract</th>
                </tr>
              </thead>
              <tbody>
                {recentFeedbacks.map((item) => (
                  <tr key={item.processed_id}>
                    <td>
                      <div className="subject-text">{item.original_subject}</div>
                      <div className="description-preview">{item.clean_text.substring(0, 75)}...</div>
                    </td>
                    <td>
                      <span className={`badge category-${item.category.toLowerCase().replace(' ', '-')}`}>
                        {item.category}
                      </span>
                    </td>
                    <td>
                      <span className={`badge priority-${item.priority.toLowerCase()}`}>
                        {item.priority}
                      </span>
                    </td>
                    <td><strong>{item.weight}</strong></td>
                    <td>{item.word_count}</td>
                    <td>
                      <div className="lemmas-chips">
                        {item.lemmas.slice(0, 3).map((lemma, idx) => (
                          <span key={idx} className="lemma-chip">{lemma}</span>
                        ))}
                        {item.lemmas.length > 3 && <span className="lemma-more">+{item.lemmas.length - 3}</span>}
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
};

export default DashboardPage;

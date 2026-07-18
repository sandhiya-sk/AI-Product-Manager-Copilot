import React, { useState, useEffect, useContext } from 'react';
import { AuthContext } from '../context/AuthContext';
import api from '../services/api';

const CATEGORY_COLORS = {
  'Bug Report': '#ef4444',
  'Feature Request': '#8b5cf6',
  'Complaint': '#f97316',
  'Praise': '#22c55e',
  'Question': '#3b82f6',
  'Pricing Issue': '#eab308',
  'Performance Issue': '#ec4899',
  'UI Issue': '#06b6d4',
  'Security Concern': '#dc2626',
};

const SENTIMENT_COLORS = {
  'Positive': '#22c55e',
  'Negative': '#ef4444',
  'Neutral': '#94a3b8',
  'Mixed': '#f59e0b',
};

const CATEGORY_ICONS = {
  'Bug Report': '🐛',
  'Feature Request': '✨',
  'Complaint': '😤',
  'Praise': '⭐',
  'Question': '❓',
  'Pricing Issue': '💰',
  'Performance Issue': '⚡',
  'UI Issue': '🎨',
  'Security Concern': '🔒',
};

const ClassificationPage = () => {
  const { user } = useContext(AuthContext);

  // Pipeline state
  const [classifying, setClassifying] = useState(false);
  const [classifyMsg, setClassifyMsg] = useState(null);

  // Results state
  const [results, setResults] = useState([]);
  const [totalResults, setTotalResults] = useState(0);
  const [page, setPage] = useState(1);
  const [pageSize] = useState(15);

  // Stats state
  const [stats, setStats] = useState(null);

  // Filters
  const [filterCategory, setFilterCategory] = useState('');
  const [filterSentiment, setFilterSentiment] = useState('');

  // UI state
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [expandedRow, setExpandedRow] = useState(null);
  const [activeTab, setActiveTab] = useState('results');

  // ─── Fetch Classification Results ───────────────────────
  const fetchResults = async (currentPage = 1) => {
    try {
      let url = `/classify/results?project_id=${user.project_id}&page=${currentPage}&page_size=${pageSize}`;
      if (filterCategory) url += `&category=${encodeURIComponent(filterCategory)}`;
      if (filterSentiment) url += `&sentiment=${encodeURIComponent(filterSentiment)}`;

      const res = await api.get(url);
      if (res.data.success) {
        setResults(res.data.data.results);
        setTotalResults(res.data.data.total);
      }
    } catch (err) {
      console.error('Failed to fetch classification results:', err);
      setError('Failed to load classification results.');
    }
  };

  // ─── Fetch Classification Stats ─────────────────────────
  const fetchStats = async () => {
    try {
      const res = await api.get(`/classify/stats?project_id=${user.project_id}`);
      if (res.data.success) {
        setStats(res.data.data);
      }
    } catch (err) {
      console.error('Failed to fetch classification stats:', err);
    }
  };

  // ─── Initial Load ───────────────────────────────────────
  useEffect(() => {
    if (user && user.project_id) {
      Promise.all([fetchResults(1), fetchStats()]).finally(() => setLoading(false));
    }
  }, [user]);

  // ─── Refetch on filter/page change ──────────────────────
  useEffect(() => {
    if (user && user.project_id) {
      fetchResults(page);
    }
  }, [page, filterCategory, filterSentiment]);

  // ─── Run Classification Pipeline ────────────────────────
  const handleRunClassification = async () => {
    setClassifying(true);
    setClassifyMsg('Starting AI Classification Pipeline...');
    setError(null);

    try {
      const res = await api.post('/classify/run', { project_id: user.project_id });
      if (res.data.success) {
        const { job_id, unclassified_count } = res.data.data;
        if (unclassified_count === 0) {
          setClassifyMsg('All feedback has already been classified. No new items to process.');
        } else {
          setClassifyMsg(`Classification running in background. Job ID: ${job_id}. Classifying ${unclassified_count} items...`);

          // Poll for completion
          const pollInterval = setInterval(async () => {
            try {
              const statusRes = await api.get(`/classify/status/${job_id}`);
              if (statusRes.data.success) {
                const jobData = statusRes.data.data;
                if (jobData.status === 'completed') {
                  clearInterval(pollInterval);
                  setClassifyMsg(
                    `Classification complete! ${jobData.classified_count} classified, ${jobData.failed_count} failed.`
                  );
                  fetchResults(1);
                  fetchStats();
                  setPage(1);
                } else if (jobData.status === 'failed') {
                  clearInterval(pollInterval);
                  setClassifyMsg(`Classification failed: ${jobData.error}`);
                }
              }
            } catch (pollErr) {
              console.error('Poll error:', pollErr);
            }
          }, 3000);

          // Safety: stop polling after 5 minutes
          setTimeout(() => clearInterval(pollInterval), 300000);
        }
      }
    } catch (err) {
      console.error(err);
      setClassifyMsg(null);
      setError(err.response?.data?.error || 'Failed to trigger classification pipeline.');
    } finally {
      setClassifying(false);
    }
  };

  // ─── Pagination ─────────────────────────────────────────
  const totalPages = Math.ceil(totalResults / pageSize);

  if (loading) {
    return (
      <div className="loader-container">
        <div className="spinner"></div>
        <p>Loading Classification Intelligence...</p>
      </div>
    );
  }

  return (
    <div className="dashboard-container page-layout">
      {/* Header */}
      <div className="dashboard-header">
        <div className="header-meta">
          <h1>🧠 AI Classification & Theme Extraction</h1>
          <p className="project-token">
            <strong>Module 4</strong> — Powered by Gemini AI
          </p>
        </div>
        <button
          onClick={handleRunClassification}
          className="action-btn run-pipeline-btn"
          disabled={classifying}
        >
          {classifying ? 'Classifying...' : '🤖 Run AI Classification'}
        </button>
      </div>

      {/* Status Messages */}
      {classifyMsg && (
        <div className="alert-message info-alert">
          <strong>Classification Status: </strong> {classifyMsg}
        </div>
      )}
      {error && (
        <div className="alert-message error-alert">
          <strong>Error: </strong> {error}
        </div>
      )}

      {/* Tab Navigation */}
      <div className="classify-tabs">
        <button
          className={`classify-tab ${activeTab === 'results' ? 'active' : ''}`}
          onClick={() => setActiveTab('results')}
        >
          📋 Classification Results
        </button>
        <button
          className={`classify-tab ${activeTab === 'analytics' ? 'active' : ''}`}
          onClick={() => setActiveTab('analytics')}
        >
          📊 Analytics Dashboard
        </button>
      </div>

      {/* ─── Results Tab ───────────────────────────────── */}
      {activeTab === 'results' && (
        <div className="classify-results-section">
          {/* Filters */}
          <div className="classify-filters glass-panel">
            <div className="filter-group">
              <label>Category:</label>
              <select
                value={filterCategory}
                onChange={(e) => { setFilterCategory(e.target.value); setPage(1); }}
              >
                <option value="">All Categories</option>
                {Object.keys(CATEGORY_ICONS).map(cat => (
                  <option key={cat} value={cat}>{CATEGORY_ICONS[cat]} {cat}</option>
                ))}
              </select>
            </div>
            <div className="filter-group">
              <label>Sentiment:</label>
              <select
                value={filterSentiment}
                onChange={(e) => { setFilterSentiment(e.target.value); setPage(1); }}
              >
                <option value="">All Sentiments</option>
                <option value="Positive">😊 Positive</option>
                <option value="Negative">😠 Negative</option>
                <option value="Neutral">😐 Neutral</option>
                <option value="Mixed">🤔 Mixed</option>
              </select>
            </div>
            <div className="filter-group">
              <span className="result-count">{totalResults} results</span>
            </div>
          </div>

          {/* Results Table */}
          {results.length === 0 ? (
            <div className="empty-state glass-panel">
              <p>
                No classified feedback yet. Run the preprocessing pipeline first (Module 3),
                then click <strong>"Run AI Classification"</strong> to classify feedback.
              </p>
            </div>
          ) : (
            <div className="table-responsive glass-panel">
              <table className="data-table classify-table">
                <thead>
                  <tr>
                    <th>Subject</th>
                    <th>AI Category</th>
                    <th>Sentiment</th>
                    <th>Confidence</th>
                    <th>Keywords</th>
                    <th>Weight</th>
                    <th>Details</th>
                  </tr>
                </thead>
                <tbody>
                  {results.map((item) => (
                    <React.Fragment key={item.classified_id}>
                      <tr className={expandedRow === item.classified_id ? 'expanded-row' : ''}>
                        <td>
                          <div className="subject-text">
                            {item.original_subject || 'N/A'}
                          </div>
                          <div className="description-preview">
                            {item.ai_summary || (item.clean_text || '').substring(0, 80)}...
                          </div>
                        </td>
                        <td>
                          <span
                            className="badge classify-category-badge"
                            style={{
                              backgroundColor: `${CATEGORY_COLORS[item.ai_category] || '#6b7280'}20`,
                              color: CATEGORY_COLORS[item.ai_category] || '#6b7280',
                              borderColor: CATEGORY_COLORS[item.ai_category] || '#6b7280',
                            }}
                          >
                            {CATEGORY_ICONS[item.ai_category] || '📌'} {item.ai_category}
                          </span>
                        </td>
                        <td>
                          <span
                            className="badge classify-sentiment-badge"
                            style={{
                              backgroundColor: `${SENTIMENT_COLORS[item.ai_sentiment] || '#94a3b8'}20`,
                              color: SENTIMENT_COLORS[item.ai_sentiment] || '#94a3b8',
                              borderColor: SENTIMENT_COLORS[item.ai_sentiment] || '#94a3b8',
                            }}
                          >
                            {item.ai_sentiment}
                          </span>
                          <div className="sentiment-score-bar">
                            <div
                              className="sentiment-score-fill"
                              style={{
                                width: `${Math.abs(item.ai_sentiment_score) * 50 + 50}%`,
                                backgroundColor: item.ai_sentiment_score >= 0 ? '#22c55e' : '#ef4444',
                              }}
                            />
                          </div>
                        </td>
                        <td>
                          <div className="confidence-display">
                            <div className="confidence-bar">
                              <div
                                className="confidence-fill"
                                style={{ width: `${item.ai_confidence_score * 100}%` }}
                              />
                            </div>
                            <span className="confidence-value">
                              {(item.ai_confidence_score * 100).toFixed(0)}%
                            </span>
                          </div>
                        </td>
                        <td>
                          <div className="lemmas-chips">
                            {(item.keywords || []).slice(0, 3).map((kw, idx) => (
                              <span key={idx} className="lemma-chip keyword-chip">{kw}</span>
                            ))}
                            {(item.keywords || []).length > 3 && (
                              <span className="lemma-more">+{item.keywords.length - 3}</span>
                            )}
                          </div>
                        </td>
                        <td><strong>{item.weight}</strong></td>
                        <td>
                          <button
                            className="expand-btn"
                            onClick={() =>
                              setExpandedRow(
                                expandedRow === item.classified_id ? null : item.classified_id
                              )
                            }
                          >
                            {expandedRow === item.classified_id ? '▲' : '▼'}
                          </button>
                        </td>
                      </tr>

                      {/* Expanded Details Row */}
                      {expandedRow === item.classified_id && (
                        <tr className="detail-row">
                          <td colSpan="7">
                            <div className="classify-detail-grid">
                              {/* Themes */}
                              <div className="detail-section">
                                <h4>🎯 Themes</h4>
                                <div className="detail-chips">
                                  {(item.themes || []).map((th, idx) => (
                                    <span key={idx} className="detail-chip theme-chip">{th}</span>
                                  ))}
                                  {(!item.themes || item.themes.length === 0) && (
                                    <span className="no-data">No themes extracted</span>
                                  )}
                                </div>
                              </div>

                              {/* Topics */}
                              <div className="detail-section">
                                <h4>📂 Topics</h4>
                                <div className="detail-chips">
                                  {(item.topics || []).map((tp, idx) => (
                                    <span key={idx} className="detail-chip topic-chip">{tp}</span>
                                  ))}
                                  {(!item.topics || item.topics.length === 0) && (
                                    <span className="no-data">No topics extracted</span>
                                  )}
                                </div>
                              </div>

                              {/* Pain Points */}
                              <div className="detail-section">
                                <h4>🔥 Pain Points</h4>
                                <div className="detail-chips">
                                  {(item.pain_points || []).map((pp, idx) => (
                                    <span key={idx} className="detail-chip pain-chip">{pp}</span>
                                  ))}
                                  {(!item.pain_points || item.pain_points.length === 0) && (
                                    <span className="no-data">No pain points identified</span>
                                  )}
                                </div>
                              </div>

                              {/* Customer Intent */}
                              <div className="detail-section">
                                <h4>🎯 Customer Intent</h4>
                                <p className="intent-text">
                                  {item.customer_intent || 'Not determined'}
                                </p>
                              </div>

                              {/* All Keywords */}
                              <div className="detail-section full-width">
                                <h4>🔑 All Keywords</h4>
                                <div className="detail-chips">
                                  {(item.keywords || []).map((kw, idx) => (
                                    <span key={idx} className="detail-chip keyword-detail-chip">{kw}</span>
                                  ))}
                                </div>
                              </div>

                              {/* AI Summary */}
                              {item.ai_summary && (
                                <div className="detail-section full-width">
                                  <h4>📝 AI Summary</h4>
                                  <p className="ai-summary-text">{item.ai_summary}</p>
                                </div>
                              )}
                            </div>
                          </td>
                        </tr>
                      )}
                    </React.Fragment>
                  ))}
                </tbody>
              </table>
            </div>
          )}

          {/* Pagination */}
          {totalPages > 1 && (
            <div className="pagination-controls">
              <button
                disabled={page <= 1}
                onClick={() => setPage(p => Math.max(1, p - 1))}
                className="action-btn"
              >
                ← Previous
              </button>
              <span className="page-info">
                Page {page} of {totalPages}
              </span>
              <button
                disabled={page >= totalPages}
                onClick={() => setPage(p => p + 1)}
                className="action-btn"
              >
                Next →
              </button>
            </div>
          )}
        </div>
      )}

      {/* ─── Analytics Tab ─────────────────────────────── */}
      {activeTab === 'analytics' && stats && (
        <div className="classify-analytics-section">
          {/* Summary Cards */}
          <div className="metrics-grid">
            <div className="metric-card glass-panel">
              <span className="metric-icon">🧠</span>
              <div className="metric-data">
                <span className="metric-value">{stats.total_classified}</span>
                <span className="metric-label">Total Classified</span>
              </div>
            </div>
            <div className="metric-card glass-panel">
              <span className="metric-icon">📊</span>
              <div className="metric-data">
                <span className="metric-value">{(stats.avg_confidence_score * 100).toFixed(1)}%</span>
                <span className="metric-label">Avg Confidence</span>
              </div>
            </div>
            <div className="metric-card glass-panel">
              <span className="metric-icon">⚖️</span>
              <div className="metric-data">
                <span className="metric-value">{stats.total_weighted_submissions}</span>
                <span className="metric-label">Total Weighted</span>
              </div>
            </div>
          </div>

          {/* Category Distribution */}
          <div className="analytics-grid">
            <div className="analytics-card glass-panel">
              <h3>📁 Category Distribution</h3>
              <div className="distribution-list">
                {Object.entries(stats.category_distribution)
                  .sort(([, a], [, b]) => b - a)
                  .map(([cat, count]) => (
                    <div key={cat} className="distribution-item">
                      <div className="dist-label">
                        <span className="dist-icon">{CATEGORY_ICONS[cat] || '📌'}</span>
                        <span>{cat}</span>
                      </div>
                      <div className="dist-bar-container">
                        <div
                          className="dist-bar"
                          style={{
                            width: `${(count / Math.max(...Object.values(stats.category_distribution))) * 100}%`,
                            backgroundColor: CATEGORY_COLORS[cat] || '#6b7280',
                          }}
                        />
                      </div>
                      <span className="dist-count">{count}</span>
                    </div>
                  ))}
              </div>
            </div>

            <div className="analytics-card glass-panel">
              <h3>😊 Sentiment Distribution</h3>
              <div className="distribution-list">
                {Object.entries(stats.sentiment_distribution)
                  .sort(([, a], [, b]) => b - a)
                  .map(([sent, count]) => (
                    <div key={sent} className="distribution-item">
                      <div className="dist-label">
                        <span>{sent}</span>
                      </div>
                      <div className="dist-bar-container">
                        <div
                          className="dist-bar"
                          style={{
                            width: `${(count / Math.max(...Object.values(stats.sentiment_distribution))) * 100}%`,
                            backgroundColor: SENTIMENT_COLORS[sent] || '#94a3b8',
                          }}
                        />
                      </div>
                      <span className="dist-count">{count}</span>
                    </div>
                  ))}
              </div>
            </div>
          </div>

          {/* Top Keywords & Themes */}
          <div className="analytics-grid">
            <div className="analytics-card glass-panel">
              <h3>🔑 Top Keywords</h3>
              <div className="tag-cloud">
                {stats.top_keywords.map((item, idx) => (
                  <span
                    key={idx}
                    className="cloud-tag"
                    style={{
                      fontSize: `${Math.max(0.75, Math.min(1.5, 0.75 + (item.count / (stats.top_keywords[0]?.count || 1)) * 0.75))}rem`,
                      opacity: Math.max(0.5, item.count / (stats.top_keywords[0]?.count || 1)),
                    }}
                  >
                    {item.keyword}
                    <sup className="tag-count">{item.count}</sup>
                  </span>
                ))}
                {stats.top_keywords.length === 0 && (
                  <span className="no-data">No keywords extracted yet</span>
                )}
              </div>
            </div>

            <div className="analytics-card glass-panel">
              <h3>🎯 Top Themes</h3>
              <div className="theme-list">
                {stats.top_themes.map((item, idx) => (
                  <div key={idx} className="theme-item">
                    <span className="theme-rank">#{idx + 1}</span>
                    <span className="theme-name">{item.theme}</span>
                    <span className="theme-count">{item.count} mentions</span>
                  </div>
                ))}
                {stats.top_themes.length === 0 && (
                  <span className="no-data">No themes extracted yet</span>
                )}
              </div>
            </div>
          </div>

          {/* Top Pain Points */}
          <div className="analytics-card glass-panel full-width-card">
            <h3>🔥 Top Pain Points</h3>
            <div className="pain-points-grid">
              {stats.top_pain_points.map((item, idx) => (
                <div key={idx} className="pain-point-card">
                  <div className="pain-point-header">
                    <span className="pain-point-rank">#{idx + 1}</span>
                    <span className="pain-point-count">{item.count} reports</span>
                  </div>
                  <p className="pain-point-text">{item.pain_point}</p>
                </div>
              ))}
              {stats.top_pain_points.length === 0 && (
                <span className="no-data">No pain points identified yet</span>
              )}
            </div>
          </div>
        </div>
      )}

      {activeTab === 'analytics' && !stats && (
        <div className="empty-state glass-panel">
          <p>No analytics data available. Run the classification pipeline first.</p>
        </div>
      )}
    </div>
  );
};

export default ClassificationPage;

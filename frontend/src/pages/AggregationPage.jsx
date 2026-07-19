import React, { useState, useEffect, useContext } from 'react';
import { AuthContext } from '../context/AuthContext';
import api from '../services/api';

const IMPORTANCE_COLORS = {
  'Critical': '#ef4444',
  'High': '#f97316',
  'Medium': '#eab308',
  'Low': '#22c55e',
};

const IMPORTANCE_ICONS = {
  'Critical': '🔴',
  'High': '🟠',
  'Medium': '🟡',
  'Low': '🟢',
};

const TREND_ICONS = {
  'rising': '📈',
  'stable': '➡️',
  'declining': '📉',
};

const TREND_COLORS = {
  'rising': '#22c55e',
  'stable': '#94a3b8',
  'declining': '#ef4444',
};

const SENTIMENT_COLORS = {
  'Positive': '#22c55e',
  'Negative': '#ef4444',
  'Neutral': '#94a3b8',
  'Mixed': '#f59e0b',
};

const AggregationPage = () => {
  const { user } = useContext(AuthContext);

  // Pipeline state
  const [aggregating, setAggregating] = useState(false);
  const [aggregateMsg, setAggregateMsg] = useState(null);

  // Clusters state
  const [clusters, setClusters] = useState([]);
  const [totalClusters, setTotalClusters] = useState(0);
  const [page, setPage] = useState(1);
  const [pageSize] = useState(15);

  // Stats state
  const [stats, setStats] = useState(null);

  // Filters
  const [filterImportance, setFilterImportance] = useState('');
  const [filterTrend, setFilterTrend] = useState('');
  const [sortBy, setSortBy] = useState('frequency');

  // UI state
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [expandedRow, setExpandedRow] = useState(null);
  const [activeTab, setActiveTab] = useState('clusters');
  const [expandedDetail, setExpandedDetail] = useState(null);

  // ─── Fetch Clusters ─────────────────────────────────────
  const fetchClusters = async (currentPage = 1) => {
    try {
      let url = `/aggregate/clusters?project_id=${user.project_id}&page=${currentPage}&page_size=${pageSize}&sort_by=${sortBy}`;
      if (filterImportance) url += `&importance=${encodeURIComponent(filterImportance)}`;
      if (filterTrend) url += `&trend=${encodeURIComponent(filterTrend)}`;

      const res = await api.get(url);
      if (res.data.success) {
        setClusters(res.data.data.clusters);
        setTotalClusters(res.data.data.total);
      }
    } catch (err) {
      console.error('Failed to fetch clusters:', err);
      setError('Failed to load feature clusters.');
    }
  };

  // ─── Fetch Stats ────────────────────────────────────────
  const fetchStats = async () => {
    try {
      const res = await api.get(`/aggregate/stats?project_id=${user.project_id}`);
      if (res.data.success) {
        setStats(res.data.data);
      }
    } catch (err) {
      console.error('Failed to fetch aggregation stats:', err);
    }
  };

  // ─── Fetch Cluster Detail ──────────────────────────────
  const fetchClusterDetail = async (aggregateId) => {
    try {
      const res = await api.get(`/aggregate/clusters/${aggregateId}`);
      if (res.data.success) {
        setExpandedDetail(res.data.data);
      }
    } catch (err) {
      console.error('Failed to fetch cluster detail:', err);
    }
  };

  // ─── Initial Load ───────────────────────────────────────
  useEffect(() => {
    if (user && user.project_id) {
      Promise.all([fetchClusters(1), fetchStats()]).finally(() => setLoading(false));
    }
  }, [user]);

  // ─── Refetch on filter/page/sort change ─────────────────
  useEffect(() => {
    if (user && user.project_id) {
      fetchClusters(page);
    }
  }, [page, filterImportance, filterTrend, sortBy]);

  // ─── Run Aggregation Pipeline ───────────────────────────
  const handleRunAggregation = async () => {
    setAggregating(true);
    setAggregateMsg('Starting Feature Request Aggregation...');
    setError(null);

    try {
      const res = await api.post('/aggregate/run', { project_id: user.project_id });
      if (res.data.success) {
        const { job_id, feature_request_count } = res.data.data;
        if (feature_request_count === 0) {
          setAggregateMsg('No classified feature requests found. Run AI Classification first (Module 4).');
        } else {
          setAggregateMsg(`Aggregation running in background. Analyzing ${feature_request_count} feature requests...`);

          // Poll for completion
          const pollInterval = setInterval(async () => {
            try {
              const statusRes = await api.get(`/aggregate/status/${job_id}`);
              if (statusRes.data.success) {
                const jobData = statusRes.data.data;
                if (jobData.status === 'completed') {
                  clearInterval(pollInterval);
                  setAggregateMsg(
                    `Aggregation complete! ${jobData.clusters_created} clusters formed from ${jobData.total_requests} requests.`
                  );
                  fetchClusters(1);
                  fetchStats();
                  setPage(1);
                } else if (jobData.status === 'failed') {
                  clearInterval(pollInterval);
                  setAggregateMsg(`Aggregation failed: ${jobData.error}`);
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
      setAggregateMsg(null);
      setError(err.response?.data?.error || 'Failed to trigger aggregation pipeline.');
    } finally {
      setAggregating(false);
    }
  };

  // ─── Handle Row Expand ──────────────────────────────────
  const handleExpandRow = (aggregateId) => {
    if (expandedRow === aggregateId) {
      setExpandedRow(null);
      setExpandedDetail(null);
    } else {
      setExpandedRow(aggregateId);
      fetchClusterDetail(aggregateId);
    }
  };

  // ─── Pagination ─────────────────────────────────────────
  const totalPages = Math.ceil(totalClusters / pageSize);

  if (loading) {
    return (
      <div className="loader-container">
        <div className="spinner"></div>
        <p>Loading Feature Aggregation Intelligence...</p>
      </div>
    );
  }

  return (
    <div className="dashboard-container page-layout">
      {/* Header */}
      <div className="dashboard-header">
        <div className="header-meta">
          <h1>🔗 Feature Request Aggregation</h1>
          <p className="project-token">
            AI-powered semantic clustering of customer feature requests
          </p>
        </div>
        <button
          onClick={handleRunAggregation}
          className="action-btn run-pipeline-btn"
          disabled={aggregating}
          id="run-aggregation-btn"
        >
          {aggregating ? 'Aggregating...' : '🧬 Run Feature Aggregation'}
        </button>
      </div>

      {/* Status Messages */}
      {aggregateMsg && (
        <div className="alert-message info-alert">
          <strong>Aggregation Status: </strong> {aggregateMsg}
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
          className={`classify-tab ${activeTab === 'clusters' ? 'active' : ''}`}
          onClick={() => setActiveTab('clusters')}
          id="tab-clusters"
        >
          🧬 Feature Clusters
        </button>
        <button
          className={`classify-tab ${activeTab === 'analytics' ? 'active' : ''}`}
          onClick={() => setActiveTab('analytics')}
          id="tab-analytics"
        >
          📊 Analytics Dashboard
        </button>
        <button
          className={`classify-tab ${activeTab === 'trends' ? 'active' : ''}`}
          onClick={() => setActiveTab('trends')}
          id="tab-trends"
        >
          📈 Trend Radar
        </button>
      </div>

      {/* ─── Clusters Tab ───────────────────────────────── */}
      {activeTab === 'clusters' && (
        <div className="agg-clusters-section">
          {/* Filters */}
          <div className="classify-filters glass-panel">
            <div className="filter-group">
              <label>Importance:</label>
              <select
                value={filterImportance}
                onChange={(e) => { setFilterImportance(e.target.value); setPage(1); }}
                id="filter-importance"
              >
                <option value="">All Levels</option>
                <option value="Critical">🔴 Critical</option>
                <option value="High">🟠 High</option>
                <option value="Medium">🟡 Medium</option>
                <option value="Low">🟢 Low</option>
              </select>
            </div>
            <div className="filter-group">
              <label>Trend:</label>
              <select
                value={filterTrend}
                onChange={(e) => { setFilterTrend(e.target.value); setPage(1); }}
                id="filter-trend"
              >
                <option value="">All Trends</option>
                <option value="rising">📈 Rising</option>
                <option value="stable">➡️ Stable</option>
                <option value="declining">📉 Declining</option>
              </select>
            </div>
            <div className="filter-group">
              <label>Sort By:</label>
              <select
                value={sortBy}
                onChange={(e) => { setSortBy(e.target.value); setPage(1); }}
                id="filter-sort"
              >
                <option value="frequency">Frequency</option>
                <option value="importance">Importance</option>
                <option value="affected_users">Affected Users</option>
                <option value="trend">Trend</option>
              </select>
            </div>
            <div className="filter-group">
              <span className="result-count">{totalClusters} clusters</span>
            </div>
          </div>

          {/* Cluster Table */}
          {clusters.length === 0 ? (
            <div className="empty-state glass-panel">
              <p>
                No feature clusters yet. First run <strong>AI Classification</strong> (Module 4),
                then click <strong>"Run Feature Aggregation"</strong> to cluster feature requests.
              </p>
            </div>
          ) : (
            <div className="table-responsive glass-panel">
              <table className="data-table agg-table" id="cluster-table">
                <thead>
                  <tr>
                    <th>Feature Cluster</th>
                    <th>Frequency</th>
                    <th>Importance</th>
                    <th>Affected Users</th>
                    <th>Sentiment</th>
                    <th>Trend</th>
                    <th>Details</th>
                  </tr>
                </thead>
                <tbody>
                  {clusters.map((cluster) => (
                    <React.Fragment key={cluster.aggregate_id}>
                      <tr className={expandedRow === cluster.aggregate_id ? 'expanded-row' : ''}>
                        <td className="table-subject">
                          <div className="agg-cluster-label">
                            {cluster.cluster_label}
                          </div>
                          <div className="description-preview">
                            {cluster.cluster_description || ''}
                          </div>
                        </td>
                        <td>
                          <div className="agg-frequency-cell">
                            <div className="agg-frequency-bar-container">
                              <div
                                className="agg-frequency-bar"
                                style={{
                                  width: `${Math.min(100, (cluster.frequency / (clusters[0]?.frequency || 1)) * 100)}%`,
                                }}
                              />
                            </div>
                            <span className="agg-frequency-value">{cluster.frequency}</span>
                          </div>
                        </td>
                        <td>
                          <span
                            className="badge agg-importance-badge"
                            style={{
                              backgroundColor: `${IMPORTANCE_COLORS[cluster.importance] || '#6b7280'}20`,
                              color: IMPORTANCE_COLORS[cluster.importance] || '#6b7280',
                              borderColor: IMPORTANCE_COLORS[cluster.importance] || '#6b7280',
                              border: `1px solid ${IMPORTANCE_COLORS[cluster.importance] || '#6b7280'}`,
                            }}
                          >
                            {IMPORTANCE_ICONS[cluster.importance] || '⚪'} {cluster.importance}
                          </span>
                        </td>
                        <td>
                          <div className="agg-users-cell">
                            <span className="agg-users-icon">👥</span>
                            <strong>{cluster.affected_users}</strong>
                          </div>
                        </td>
                        <td>
                          <span
                            className="badge classify-sentiment-badge"
                            style={{
                              backgroundColor: `${SENTIMENT_COLORS[cluster.dominant_sentiment] || '#94a3b8'}20`,
                              color: SENTIMENT_COLORS[cluster.dominant_sentiment] || '#94a3b8',
                              borderColor: SENTIMENT_COLORS[cluster.dominant_sentiment] || '#94a3b8',
                            }}
                          >
                            {cluster.dominant_sentiment}
                          </span>
                        </td>
                        <td>
                          <span
                            className="agg-trend-badge"
                            style={{ color: TREND_COLORS[cluster.trend_direction] || '#94a3b8' }}
                          >
                            {TREND_ICONS[cluster.trend_direction] || '➡️'}{' '}
                            <span className="agg-trend-label">{cluster.trend_direction}</span>
                          </span>
                        </td>
                        <td>
                          <button
                            className="expand-btn"
                            onClick={() => handleExpandRow(cluster.aggregate_id)}
                            aria-label="Toggle cluster details"
                          >
                            {expandedRow === cluster.aggregate_id ? '▲' : '▼'}
                          </button>
                        </td>
                      </tr>

                      {/* Expanded Details Row */}
                      {expandedRow === cluster.aggregate_id && (
                        <tr className="detail-row">
                          <td colSpan="7">
                            <div className="agg-detail-grid">
                              {/* Keywords */}
                              <div className="detail-section">
                                <h4>🔑 Representative Keywords</h4>
                                <div className="detail-chips">
                                  {(cluster.representative_keywords || []).map((kw, idx) => (
                                    <span key={idx} className="detail-chip keyword-detail-chip">{kw}</span>
                                  ))}
                                  {(!cluster.representative_keywords || cluster.representative_keywords.length === 0) && (
                                    <span className="no-data">No keywords available</span>
                                  )}
                                </div>
                              </div>

                              {/* Metrics Summary */}
                              <div className="detail-section">
                                <h4>📊 Cluster Metrics</h4>
                                <div className="agg-metrics-mini">
                                  <div className="agg-metric-item">
                                    <span className="agg-metric-label">Total Requests</span>
                                    <span className="agg-metric-value">{cluster.frequency}</span>
                                  </div>
                                  <div className="agg-metric-item">
                                    <span className="agg-metric-label">Affected Users</span>
                                    <span className="agg-metric-value">{cluster.affected_users}</span>
                                  </div>
                                  <div className="agg-metric-item">
                                    <span className="agg-metric-label">Avg Sentiment</span>
                                    <span className="agg-metric-value">
                                      {cluster.avg_sentiment_score >= 0 ? '+' : ''}
                                      {cluster.avg_sentiment_score?.toFixed(2)}
                                    </span>
                                  </div>
                                  <div className="agg-metric-item">
                                    <span className="agg-metric-label">Cluster Members</span>
                                    <span className="agg-metric-value">
                                      {(cluster.member_classified_ids || []).length}
                                    </span>
                                  </div>
                                </div>
                              </div>

                              {/* Trend Details */}
                              <div className="detail-section">
                                <h4>
                                  {TREND_ICONS[cluster.trend_direction] || '➡️'} Trend Analysis
                                </h4>
                                {cluster.trend_details && cluster.trend_details.weekly_counts ? (
                                  <div className="agg-trend-timeline">
                                    {cluster.trend_details.weekly_counts.map((wk, idx) => (
                                      <div key={idx} className="agg-trend-week">
                                        <span className="agg-week-label">{wk.week}</span>
                                        <div className="agg-week-bar-container">
                                          <div
                                            className="agg-week-bar"
                                            style={{
                                              width: `${Math.min(100, (wk.count / Math.max(...cluster.trend_details.weekly_counts.map(w => w.count))) * 100)}%`,
                                              backgroundColor: TREND_COLORS[cluster.trend_direction] || '#94a3b8',
                                            }}
                                          />
                                        </div>
                                        <span className="agg-week-count">{wk.count}</span>
                                      </div>
                                    ))}
                                    {cluster.trend_details.growth_rate !== undefined && (
                                      <div className="agg-growth-rate">
                                        Growth Rate: <strong style={{ color: TREND_COLORS[cluster.trend_direction] }}>
                                          {cluster.trend_details.growth_rate > 0 ? '+' : ''}
                                          {(cluster.trend_details.growth_rate * 100).toFixed(1)}%
                                        </strong>
                                      </div>
                                    )}
                                  </div>
                                ) : (
                                  <span className="no-data">No trend data available</span>
                                )}
                              </div>

                              {/* Sample Feedbacks */}
                              <div className="detail-section">
                                <h4>📝 Sample Feedback</h4>
                                {expandedDetail && expandedDetail.sample_feedbacks && expandedDetail.sample_feedbacks.length > 0 ? (
                                  <div className="agg-sample-list">
                                    {expandedDetail.sample_feedbacks.map((fb, idx) => (
                                      <div key={idx} className="agg-sample-card">
                                        <div className="agg-sample-subject">
                                          {fb.original_subject || 'N/A'}
                                        </div>
                                        <div className="agg-sample-summary">
                                          {fb.ai_summary || fb.original_description?.substring(0, 120) || ''}
                                        </div>
                                        <div className="agg-sample-meta">
                                          <span
                                            className="badge classify-sentiment-badge"
                                            style={{
                                              backgroundColor: `${SENTIMENT_COLORS[fb.ai_sentiment] || '#94a3b8'}20`,
                                              color: SENTIMENT_COLORS[fb.ai_sentiment] || '#94a3b8',
                                              borderColor: SENTIMENT_COLORS[fb.ai_sentiment] || '#94a3b8',
                                              fontSize: '0.7rem',
                                              padding: '0.15rem 0.4rem',
                                            }}
                                          >
                                            {fb.ai_sentiment}
                                          </span>
                                          <span className="agg-sample-weight">Weight: {fb.weight}</span>
                                        </div>
                                      </div>
                                    ))}
                                  </div>
                                ) : (
                                  <div className="agg-sample-loading">
                                    {expandedDetail ? (
                                      <span className="no-data">No sample feedback available</span>
                                    ) : (
                                      <span className="no-data">Loading details...</span>
                                    )}
                                  </div>
                                )}
                              </div>

                              {/* Description */}
                              {cluster.cluster_description && (
                                <div className="detail-section full-width">
                                  <h4>📋 Cluster Description</h4>
                                  <p className="ai-summary-text">{cluster.cluster_description}</p>
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
              <span className="metric-icon">🧬</span>
              <div className="metric-data">
                <span className="metric-value">{stats.total_clusters}</span>
                <span className="metric-label">Feature Clusters</span>
              </div>
            </div>
            <div className="metric-card glass-panel">
              <span className="metric-icon">📋</span>
              <div className="metric-data">
                <span className="metric-value">{stats.total_feature_requests}</span>
                <span className="metric-label">Total Requests</span>
              </div>
            </div>
            <div className="metric-card glass-panel">
              <span className="metric-icon">👥</span>
              <div className="metric-data">
                <span className="metric-value">{stats.total_affected_users}</span>
                <span className="metric-label">Affected Users</span>
              </div>
            </div>
          </div>

          {/* Distributions */}
          <div className="analytics-grid">
            {/* Importance Distribution */}
            <div className="analytics-card glass-panel">
              <h3>🎯 Importance Distribution</h3>
              <div className="distribution-list">
                {Object.entries(stats.importance_distribution)
                  .sort(([a], [b]) => {
                    const order = { 'Critical': 0, 'High': 1, 'Medium': 2, 'Low': 3 };
                    return (order[a] ?? 4) - (order[b] ?? 4);
                  })
                  .map(([level, count]) => (
                    <div key={level} className="distribution-item">
                      <div className="dist-label">
                        <span className="dist-icon">{IMPORTANCE_ICONS[level] || '⚪'}</span>
                        <span>{level}</span>
                      </div>
                      <div className="dist-bar-container">
                        <div
                          className="dist-bar"
                          style={{
                            width: `${(count / Math.max(...Object.values(stats.importance_distribution))) * 100}%`,
                            backgroundColor: IMPORTANCE_COLORS[level] || '#6b7280',
                          }}
                        />
                      </div>
                      <span className="dist-count">{count}</span>
                    </div>
                  ))}
              </div>
            </div>

            {/* Trend Distribution */}
            <div className="analytics-card glass-panel">
              <h3>📈 Trend Distribution</h3>
              <div className="distribution-list">
                {Object.entries(stats.trend_distribution)
                  .sort(([a], [b]) => {
                    const order = { 'rising': 0, 'stable': 1, 'declining': 2 };
                    return (order[a] ?? 3) - (order[b] ?? 3);
                  })
                  .map(([trend, count]) => (
                    <div key={trend} className="distribution-item">
                      <div className="dist-label">
                        <span className="dist-icon">{TREND_ICONS[trend] || '➡️'}</span>
                        <span style={{ textTransform: 'capitalize' }}>{trend}</span>
                      </div>
                      <div className="dist-bar-container">
                        <div
                          className="dist-bar"
                          style={{
                            width: `${(count / Math.max(...Object.values(stats.trend_distribution))) * 100}%`,
                            backgroundColor: TREND_COLORS[trend] || '#94a3b8',
                          }}
                        />
                      </div>
                      <span className="dist-count">{count}</span>
                    </div>
                  ))}
              </div>
            </div>
          </div>

          {/* Top Clusters */}
          <div className="analytics-card glass-panel full-width-card">
            <h3>🏆 Top Feature Requests by Frequency</h3>
            <div className="agg-top-clusters-list">
              {stats.top_clusters.map((cluster, idx) => (
                <div key={idx} className="agg-top-cluster-item">
                  <span className="agg-top-rank">#{idx + 1}</span>
                  <div className="agg-top-info">
                    <span className="agg-top-label">{cluster.cluster_label}</span>
                    <div className="agg-top-meta">
                      <span
                        className="badge agg-importance-badge"
                        style={{
                          backgroundColor: `${IMPORTANCE_COLORS[cluster.importance] || '#6b7280'}15`,
                          color: IMPORTANCE_COLORS[cluster.importance] || '#6b7280',
                          border: `1px solid ${IMPORTANCE_COLORS[cluster.importance] || '#6b7280'}40`,
                          fontSize: '0.7rem',
                          padding: '0.1rem 0.4rem',
                        }}
                      >
                        {cluster.importance}
                      </span>
                      <span className="agg-top-users">👥 {cluster.affected_users}</span>
                      <span style={{ color: TREND_COLORS[cluster.trend_direction] }}>
                        {TREND_ICONS[cluster.trend_direction]} {cluster.trend_direction}
                      </span>
                    </div>
                  </div>
                  <div className="agg-top-freq-bar">
                    <div
                      className="agg-top-freq-fill"
                      style={{
                        width: `${(cluster.frequency / (stats.top_clusters[0]?.frequency || 1)) * 100}%`,
                      }}
                    />
                  </div>
                  <span className="agg-top-freq-value">{cluster.frequency}</span>
                </div>
              ))}
              {stats.top_clusters.length === 0 && (
                <span className="no-data">No clusters available</span>
              )}
            </div>
          </div>

          {/* Sentiment Breakdown */}
          <div className="analytics-card glass-panel full-width-card">
            <h3>😊 Cluster Sentiment Breakdown</h3>
            <div className="distribution-list">
              {Object.entries(stats.sentiment_breakdown)
                .sort(([, a], [, b]) => b - a)
                .map(([sentiment, count]) => (
                  <div key={sentiment} className="distribution-item">
                    <div className="dist-label">
                      <span>{sentiment}</span>
                    </div>
                    <div className="dist-bar-container">
                      <div
                        className="dist-bar"
                        style={{
                          width: `${(count / Math.max(...Object.values(stats.sentiment_breakdown))) * 100}%`,
                          backgroundColor: SENTIMENT_COLORS[sentiment] || '#94a3b8',
                        }}
                      />
                    </div>
                    <span className="dist-count">{count}</span>
                  </div>
                ))}
            </div>
          </div>
        </div>
      )}

      {activeTab === 'analytics' && !stats && (
        <div className="empty-state glass-panel">
          <p>No analytics data available. Run the aggregation pipeline first.</p>
        </div>
      )}

      {/* ─── Trends Tab ────────────────────────────────── */}
      {activeTab === 'trends' && (
        <div className="agg-trends-section">
          {clusters.length === 0 ? (
            <div className="empty-state glass-panel">
              <p>No trend data available. Run the aggregation pipeline first.</p>
            </div>
          ) : (
            <>
              {/* Rising Trends */}
              <div className="agg-trend-group">
                <h2 className="agg-trend-group-title">
                  <span className="agg-trend-group-icon" style={{ color: '#22c55e' }}>📈</span>
                  Rising Trends
                </h2>
                <div className="agg-trend-cards">
                  {clusters
                    .filter(c => c.trend_direction === 'rising')
                    .sort((a, b) => b.frequency - a.frequency)
                    .map(cluster => (
                      <div key={cluster.aggregate_id} className="agg-trend-card agg-trend-rising">
                        <div className="agg-trend-card-header">
                          <span className="agg-trend-card-label">{cluster.cluster_label}</span>
                          <span className="agg-trend-card-badge" style={{ color: '#22c55e' }}>
                            📈 Rising
                          </span>
                        </div>
                        <div className="agg-trend-card-metrics">
                          <div className="agg-trend-metric">
                            <span className="agg-trend-metric-value">{cluster.frequency}</span>
                            <span className="agg-trend-metric-label">Requests</span>
                          </div>
                          <div className="agg-trend-metric">
                            <span className="agg-trend-metric-value">{cluster.affected_users}</span>
                            <span className="agg-trend-metric-label">Users</span>
                          </div>
                          <div className="agg-trend-metric">
                            <span className="agg-trend-metric-value">
                              {IMPORTANCE_ICONS[cluster.importance]} {cluster.importance}
                            </span>
                            <span className="agg-trend-metric-label">Priority</span>
                          </div>
                        </div>
                        <div className="agg-trend-card-keywords">
                          {(cluster.representative_keywords || []).slice(0, 4).map((kw, idx) => (
                            <span key={idx} className="detail-chip keyword-detail-chip">{kw}</span>
                          ))}
                        </div>
                        {cluster.trend_details?.growth_rate !== undefined && (
                          <div className="agg-trend-growth" style={{ color: '#22c55e' }}>
                            +{(cluster.trend_details.growth_rate * 100).toFixed(1)}% growth
                          </div>
                        )}
                      </div>
                    ))}
                  {clusters.filter(c => c.trend_direction === 'rising').length === 0 && (
                    <div className="agg-trend-empty">No rising trends detected</div>
                  )}
                </div>
              </div>

              {/* Stable Trends */}
              <div className="agg-trend-group">
                <h2 className="agg-trend-group-title">
                  <span className="agg-trend-group-icon" style={{ color: '#94a3b8' }}>➡️</span>
                  Stable Trends
                </h2>
                <div className="agg-trend-cards">
                  {clusters
                    .filter(c => c.trend_direction === 'stable')
                    .sort((a, b) => b.frequency - a.frequency)
                    .map(cluster => (
                      <div key={cluster.aggregate_id} className="agg-trend-card agg-trend-stable">
                        <div className="agg-trend-card-header">
                          <span className="agg-trend-card-label">{cluster.cluster_label}</span>
                          <span className="agg-trend-card-badge" style={{ color: '#94a3b8' }}>
                            ➡️ Stable
                          </span>
                        </div>
                        <div className="agg-trend-card-metrics">
                          <div className="agg-trend-metric">
                            <span className="agg-trend-metric-value">{cluster.frequency}</span>
                            <span className="agg-trend-metric-label">Requests</span>
                          </div>
                          <div className="agg-trend-metric">
                            <span className="agg-trend-metric-value">{cluster.affected_users}</span>
                            <span className="agg-trend-metric-label">Users</span>
                          </div>
                          <div className="agg-trend-metric">
                            <span className="agg-trend-metric-value">
                              {IMPORTANCE_ICONS[cluster.importance]} {cluster.importance}
                            </span>
                            <span className="agg-trend-metric-label">Priority</span>
                          </div>
                        </div>
                        <div className="agg-trend-card-keywords">
                          {(cluster.representative_keywords || []).slice(0, 4).map((kw, idx) => (
                            <span key={idx} className="detail-chip keyword-detail-chip">{kw}</span>
                          ))}
                        </div>
                      </div>
                    ))}
                  {clusters.filter(c => c.trend_direction === 'stable').length === 0 && (
                    <div className="agg-trend-empty">No stable trends detected</div>
                  )}
                </div>
              </div>

              {/* Declining Trends */}
              <div className="agg-trend-group">
                <h2 className="agg-trend-group-title">
                  <span className="agg-trend-group-icon" style={{ color: '#ef4444' }}>📉</span>
                  Declining Trends
                </h2>
                <div className="agg-trend-cards">
                  {clusters
                    .filter(c => c.trend_direction === 'declining')
                    .sort((a, b) => b.frequency - a.frequency)
                    .map(cluster => (
                      <div key={cluster.aggregate_id} className="agg-trend-card agg-trend-declining">
                        <div className="agg-trend-card-header">
                          <span className="agg-trend-card-label">{cluster.cluster_label}</span>
                          <span className="agg-trend-card-badge" style={{ color: '#ef4444' }}>
                            📉 Declining
                          </span>
                        </div>
                        <div className="agg-trend-card-metrics">
                          <div className="agg-trend-metric">
                            <span className="agg-trend-metric-value">{cluster.frequency}</span>
                            <span className="agg-trend-metric-label">Requests</span>
                          </div>
                          <div className="agg-trend-metric">
                            <span className="agg-trend-metric-value">{cluster.affected_users}</span>
                            <span className="agg-trend-metric-label">Users</span>
                          </div>
                          <div className="agg-trend-metric">
                            <span className="agg-trend-metric-value">
                              {IMPORTANCE_ICONS[cluster.importance]} {cluster.importance}
                            </span>
                            <span className="agg-trend-metric-label">Priority</span>
                          </div>
                        </div>
                        <div className="agg-trend-card-keywords">
                          {(cluster.representative_keywords || []).slice(0, 4).map((kw, idx) => (
                            <span key={idx} className="detail-chip keyword-detail-chip">{kw}</span>
                          ))}
                        </div>
                        {cluster.trend_details?.growth_rate !== undefined && (
                          <div className="agg-trend-growth" style={{ color: '#ef4444' }}>
                            {(cluster.trend_details.growth_rate * 100).toFixed(1)}% decline
                          </div>
                        )}
                      </div>
                    ))}
                  {clusters.filter(c => c.trend_direction === 'declining').length === 0 && (
                    <div className="agg-trend-empty">No declining trends detected</div>
                  )}
                </div>
              </div>
            </>
          )}
        </div>
      )}
    </div>
  );
};

export default AggregationPage;

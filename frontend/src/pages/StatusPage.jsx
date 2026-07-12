import React, { useState, useEffect, useContext } from 'react';
import { AuthContext } from '../context/AuthContext';
import api from '../services/api';
import StatusPanel from '../components/StatusPanel';

const StatusPage = () => {
  const { user } = useContext(AuthContext);
  const [records, setRecords] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(20);
  const [totalRecords, setTotalRecords] = useState(0);

  const fetchStatusRecords = async () => {
    setLoading(true);
    try {
      const response = await api.get(`/process/results?project_id=${user.project_id}&page=${page}&page_size=${pageSize}`);
      if (response.data.success) {
        setRecords(response.data.data.results);
        setTotalRecords(response.data.data.total);
      } else {
        setError(response.data.error || "Failed to load preprocessed results.");
      }
    } catch (err) {
      console.error(err);
      setError("Network error. Failed to retrieve preprocessed records.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (user && user.project_id) {
      fetchStatusRecords();
    }
  }, [user, page, pageSize]);

  const handleNextPage = () => {
    if (page * pageSize < totalRecords) {
      setPage((prev) => prev + 1);
    }
  };

  const handlePrevPage = () => {
    if (page > 1) {
      setPage((prev) => prev - 1);
    }
  };

  if (loading && records.length === 0) {
    return (
      <div className="loader-container">
        <div className="spinner"></div>
        <p>Loading processed database results...</p>
      </div>
    );
  }

  const totalPages = Math.ceil(totalRecords / pageSize) || 1;

  return (
    <div className="status-page page-layout">
      <div className="page-header flex-header">
        <div>
          <h1>Processed Database Results</h1>
          <p>Explore NLP tokens, lemmas, weights, and duplicate groupings of processed customer reviews.</p>
        </div>
        
        <button className="action-btn refresh-btn" onClick={fetchStatusRecords} disabled={loading}>
          {loading ? "Refreshing..." : "🔄 Refresh Data"}
        </button>
      </div>

      {error && (
        <div className="alert-message error-alert">
          {error}
        </div>
      )}

      <StatusPanel records={records} />

      {totalRecords > 0 && (
        <div className="pagination-bar">
          <button 
            className="pagination-btn" 
            onClick={handlePrevPage} 
            disabled={page === 1}
          >
            ◀ Previous
          </button>
          
          <span className="pagination-info">
            Page {page} of {totalPages} (Total: {totalRecords} records)
          </span>
          
          <button 
            className="pagination-btn" 
            onClick={handleNextPage} 
            disabled={page >= totalPages}
          >
            Next ▶
          </button>
        </div>
      )}
    </div>
  );
};

export default StatusPage;

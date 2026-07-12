import React, { useState, useRef, useContext } from 'react';
import api from '../services/api';
import { AuthContext } from '../context/AuthContext';

const CSVUploadPanel = () => {
  const { user } = useContext(AuthContext);
  const [file, setFile] = useState(null);
  const [dragActive, setDragActive] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [uploadResult, setUploadResult] = useState(null);
  const [error, setError] = useState(null);
  
  const fileInputRef = useRef(null);

  const handleDrag = (e) => {
    e.preventDefault();
    e.stopPropagation();
    if (e.type === "dragenter" || e.type === "dragover") {
      setDragActive(true);
    } else if (e.type === "dragleave") {
      setDragActive(false);
    }
  };

  const validateFile = (selectedFile) => {
    if (!selectedFile) return false;
    if (!selectedFile.name.endsWith('.csv')) {
      setError("Invalid file type. Please select a .csv file.");
      setFile(null);
      return false;
    }
    setError(null);
    return true;
  };

  const handleDrop = (e) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(false);
    
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      const droppedFile = e.dataTransfer.files[0];
      if (validateFile(droppedFile)) {
        setFile(droppedFile);
        setUploadResult(null);
      }
    }
  };

  const handleChange = (e) => {
    e.preventDefault();
    if (e.target.files && e.target.files[0]) {
      const selectedFile = e.target.files[0];
      if (validateFile(selectedFile)) {
        setFile(selectedFile);
        setUploadResult(null);
      }
    }
  };

  const handleButtonClick = () => {
    fileInputRef.current.click();
  };

  const handleUpload = async (e) => {
    e.preventDefault();
    if (!file) {
      setError("Please select a file first.");
      return;
    }

    setUploading(true);
    setError(null);
    setUploadResult(null);

    const formData = new FormData();
    formData.append('file', file);
    formData.append('project_id', user.project_id);

    try {
      const response = await api.post('/ingest/csv', formData, {
        headers: {
          'Content-Type': 'multipart/form-data'
        }
      });
      
      if (response.data.success) {
        setUploadResult(response.data.data);
        setFile(null); // Clear selected file after upload
      } else {
        setError(response.data.error || "Upload failed.");
      }
    } catch (err) {
      console.error(err);
      const errMsg = err.response?.data?.error || err.response?.data?.details || "Network error. Failed to upload.";
      setError(errMsg);
    } finally {
      setUploading(false);
    }
  };

  return (
    <div className="upload-panel-card glass-panel">
      <h2 className="panel-title">Upload Bulk Feedback via CSV</h2>
      <p className="panel-subtitle">Upload CSV files containing customer reviews. Ensure columns contain 'subject' and 'description'.</p>

      <form 
        className={`drag-drop-zone ${dragActive ? 'active' : ''}`}
        onDragEnter={handleDrag}
        onDragOver={handleDrag}
        onDragLeave={handleDrag}
        onDrop={handleDrop}
        onSubmit={handleUpload}
      >
        <input 
          ref={fileInputRef}
          type="file" 
          className="file-input-hidden" 
          accept=".csv"
          onChange={handleChange}
        />
        
        <div className="upload-prompt">
          <span className="upload-icon">📂</span>
          {file ? (
            <div className="selected-file-info">
              <p className="file-name">{file.name}</p>
              <p className="file-size">{(file.size / 1024).toFixed(1)} KB</p>
            </div>
          ) : (
            <p>Drag and drop your CSV file here, or <span className="browse-link" onClick={handleButtonClick}>browse files</span></p>
          )}
        </div>

        {file && (
          <button 
            type="submit" 
            className="action-btn upload-btn" 
            disabled={uploading}
          >
            {uploading ? "Uploading In Progress..." : "Ingest Feedback Data"}
          </button>
        )}
      </form>

      {error && (
        <div className="alert-message error-alert">
          <strong>Error: </strong> {typeof error === 'object' ? JSON.stringify(error) : error}
        </div>
      )}

      {uploadResult && (
        <div className="alert-message success-alert">
          <h3>Ingestion Completed Successfully</h3>
          <p><strong>Batch ID: </strong> {uploadResult.batch_id}</p>
          <p><strong>Ingested Records: </strong> {uploadResult.ingested_count}</p>
          {uploadResult.failed_rows && uploadResult.failed_rows.length > 0 && (
            <div className="failed-rows-container">
              <p className="failed-rows-title">Failed Rows ({uploadResult.failed_rows.length}):</p>
              <ul className="failed-rows-list">
                {uploadResult.failed_rows.map((row, idx) => (
                  <li key={idx} className="failed-row-item">
                    Line {row.row_number}: {row.error}
                  </li>
                ))}
              </ul>
            </div>
          )}
        </div>
      )}
    </div>
  );
};

export default CSVUploadPanel;

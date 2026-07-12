import React from 'react';
import CSVUploadPanel from '../components/CSVUploadPanel';

const UploadCSVPage = () => {
  return (
    <div className="upload-csv-page page-layout">
      <div className="page-header">
        <h1>Ingestion Command Panel</h1>
        <p>Import bulk customer feedback records from CSV files directly into the raw feedback database.</p>
      </div>

      <div className="page-content-centered">
        <CSVUploadPanel />
      </div>
    </div>
  );
};

export default UploadCSVPage;

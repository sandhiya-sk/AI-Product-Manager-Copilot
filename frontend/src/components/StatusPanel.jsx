import React from 'react';

const StatusPanel = ({ records }) => {
  if (!records || records.length === 0) {
    return (
      <div className="empty-state glass-panel">
        <p>No feedback processed yet. Trigger pipeline to process pending feedback.</p>
      </div>
    );
  }

  const formatTags = (tags) => {
    if (!tags || tags.length === 0) return '-';
    return tags.map((tag, idx) => (
      <span key={idx} className="status-tag">
        {tag}
      </span>
    ));
  };

  return (
    <div className="status-panel-container glass-panel">
      <h3 className="section-title">Processed Feedback List</h3>
      <div className="table-responsive">
        <table className="data-table">
          <thead>
            <tr>
              <th>Subject</th>
              <th>Category</th>
              <th>Priority</th>
              <th>Weight</th>
              <th>Tokens</th>
              <th>Word Count</th>
              <th>Processed Time</th>
            </tr>
          </thead>
          <tbody>
            {records.map((rec) => (
              <tr key={rec.processed_id}>
                <td className="table-subject">
                  <div className="subject-text" title={rec.original_subject}>
                    {rec.original_subject}
                  </div>
                  <div className="group-id-text" title="Duplicate Group ID">
                    Group: {rec.duplicate_group_id.substring(0, 8)}...
                  </div>
                </td>
                <td>
                  <span className={`badge category-${rec.category.toLowerCase().replace(' ', '-')}`}>
                    {rec.category}
                  </span>
                </td>
                <td>
                  <span className={`badge priority-${rec.priority.toLowerCase()}`}>
                    {rec.priority}
                  </span>
                </td>
                <td className="table-weight">
                  <strong>{rec.weight}</strong>
                </td>
                <td className="table-tokens">
                  {formatTags(rec.tokens.slice(0, 5))}
                  {rec.tokens.length > 5 && <span className="token-more-indicator">+{rec.tokens.length - 5} more</span>}
                </td>
                <td>{rec.word_count}</td>
                <td>
                  {new Date(rec.processing_timestamp).toLocaleDateString()}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
};

export default StatusPanel;

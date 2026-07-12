import React, { useState } from 'react';
import api from '../services/api';

const FeedbackForm = () => {
  const [formData, setFormData] = useState({
    subject: '',
    description: '',
    priority: 'Medium',
    category: 'General',
    tags: '',
    product_name: '',
    product_version: '',
    sentiment_self_reported: ''
  });

  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState(null);
  const [error, setError] = useState(null);

  const handleInputChange = (e) => {
    const { name, value } = e.target;
    setFormData((prev) => ({
      ...prev,
      [name]: value
    }));
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!formData.subject.strip || !formData.subject.trim()) {
      setError("Subject is required.");
      return;
    }
    if (!formData.description || formData.description.trim().length < 10) {
      setError("Description is required and must be at least 10 characters long.");
      return;
    }

    setLoading(true);
    setError(null);
    setResult(null);

    // Prepare tags as comma-separated mapping
    const payload = {
      ...formData,
      tags: formData.tags ? formData.tags.split(',').map(t => t.trim()).filter(Boolean) : [],
      sentiment_self_reported: formData.sentiment_self_reported || null
    };

    try {
      const response = await api.post('/ingest/feedback', payload);
      if (response.data.success) {
        setResult(response.data.data);
        // Clear form fields
        setFormData({
          subject: '',
          description: '',
          priority: 'Medium',
          category: 'General',
          tags: '',
          product_name: '',
          product_version: '',
          sentiment_self_reported: ''
        });
      } else {
        setError(response.data.error || "Submission failed.");
      }
    } catch (err) {
      console.error(err);
      setError(err.response?.data?.error || "Network error. Failed to submit feedback.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="feedback-form-card glass-panel">
      <h2 className="panel-title">Submit Structured Feedback</h2>
      <p className="panel-subtitle">Provide details about bugs, enhancements, feature suggestions, or general input.</p>

      <form onSubmit={handleSubmit} className="standard-form">
        <div className="form-group">
          <label htmlFor="subject">Subject *</label>
          <input 
            type="text" 
            id="subject"
            name="subject"
            value={formData.subject}
            onChange={handleInputChange}
            placeholder="Summarize the feedback briefly"
            required 
          />
        </div>

        <div className="form-group">
          <label htmlFor="description">Detailed Description *</label>
          <textarea 
            id="description"
            name="description"
            value={formData.description}
            onChange={handleInputChange}
            placeholder="Describe what occurred, steps to reproduce, or feature context (min 10 chars)"
            rows="5"
            required 
          />
        </div>

        <div className="form-grid">
          <div className="form-group">
            <label htmlFor="category">Category</label>
            <select 
              id="category"
              name="category"
              value={formData.category}
              onChange={handleInputChange}
            >
              <option value="General">General</option>
              <option value="Bug">Bug</option>
              <option value="Feature Request">Feature Request</option>
              <option value="Improvement">Improvement</option>
              <option value="Complaint">Complaint</option>
            </select>
          </div>

          <div className="form-group">
            <label htmlFor="priority">Priority</label>
            <select 
              id="priority"
              name="priority"
              value={formData.priority}
              onChange={handleInputChange}
            >
              <option value="Low">Low</option>
              <option value="Medium">Medium</option>
              <option value="High">High</option>
              <option value="Critical">Critical</option>
            </select>
          </div>
        </div>

        <div className="form-grid">
          <div className="form-group">
            <label htmlFor="product_name">Product Name (Optional)</label>
            <input 
              type="text" 
              id="product_name"
              name="product_name"
              value={formData.product_name}
              onChange={handleInputChange}
              placeholder="e.g. Android Mobile App"
            />
          </div>

          <div className="form-group">
            <label htmlFor="product_version">Product Version (Optional)</label>
            <input 
              type="text" 
              id="product_version"
              name="product_version"
              value={formData.product_version}
              onChange={handleInputChange}
              placeholder="e.g. 1.2.3"
            />
          </div>
        </div>

        <div className="form-grid">
          <div className="form-group">
            <label htmlFor="tags">Tags (comma-separated)</label>
            <input 
              type="text" 
              id="tags"
              name="tags"
              value={formData.tags}
              onChange={handleInputChange}
              placeholder="e.g. performance, android, login"
            />
          </div>

          <div className="form-group">
            <label htmlFor="sentiment_self_reported">Sentiment (Self Reported)</label>
            <select 
              id="sentiment_self_reported"
              name="sentiment_self_reported"
              value={formData.sentiment_self_reported}
              onChange={handleInputChange}
            >
              <option value="">Choose sentiment...</option>
              <option value="Positive">Positive</option>
              <option value="Neutral">Neutral</option>
              <option value="Negative">Negative</option>
            </select>
          </div>
        </div>

        <button type="submit" className="action-btn submit-btn" disabled={loading}>
          {loading ? "Submitting In Progress..." : "Submit Feedback"}
        </button>
      </form>

      {error && (
        <div className="alert-message error-alert">
          <strong>Error: </strong> {error}
        </div>
      )}

      {result && (
        <div className="alert-message success-alert">
          <strong>Success!</strong> Feedback successfully ingested.
          <p><strong>Feedback ID:</strong> {result.feedback_id}</p>
          <p><strong>Status:</strong> {result.processing_status}</p>
        </div>
      )}
    </div>
  );
};

export default FeedbackForm;

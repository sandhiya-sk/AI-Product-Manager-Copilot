import React from 'react';
import FeedbackForm from '../components/FeedbackForm';

const FeedbackFormPage = () => {
  return (
    <div className="feedback-form-page page-layout">
      <div className="page-header">
        <h1>Submit Feedback</h1>
        <p>Record a new product feedback request, bug description, or improvement proposal.</p>
      </div>

      <div className="page-content-centered">
        <FeedbackForm />
      </div>
    </div>
  );
};

export default FeedbackFormPage;

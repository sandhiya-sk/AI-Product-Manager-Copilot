import React, { useState, useEffect, useRef, useContext } from 'react';
import { useNavigate } from 'react-router-dom';
import { AuthContext } from '../context/AuthContext';
import api from '../services/api';
import {
  Send,
  Paperclip,
  Trash2,
  Bot,
  User,
  Sparkles,
  X,
  FileText,
  HelpCircle,
  ArrowRight
} from 'lucide-react';

const AssistantPage = () => {
  const { user } = useContext(AuthContext);
  const chatEndRef = useRef(null);
  const fileInputRef = useRef(null);

  // States
  const [messages, setMessages] = useState([
    {
      id: 'welcome',
      sender: 'ai',
      text: "Hello! I'm your AI Product Manager Assistant. I can help analyze customer feedback, prioritize features, estimate business impact, generate product insights, and answer product management questions.",
      timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
    }
  ]);
  const [inputText, setInputText] = useState('');
  const [isTyping, setIsTyping] = useState(false);
  const [attachedFile, setAttachedFile] = useState(null);

  // Suggested Prompts
  const suggestedPrompts = [
    "Summarize customer feedback",
    "Prioritize backlog",
    "Predict business impact",
    "Generate product roadmap",
    "Analyze feature requests"
  ];

  // Scroll to bottom on new messages
  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, isTyping]);

  // Handle Send Message
  const handleSendMessage = async (textToSend) => {
    const query = textToSend || inputText;
    if (!query.trim() && !attachedFile) return;

    // Construct User Message
    const userMsg = {
      id: `user-${Date.now()}`,
      sender: 'user',
      text: query,
      file: attachedFile ? attachedFile.name : null,
      timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
    };

    setMessages((prev) => [...prev, userMsg]);
    setInputText('');
    setAttachedFile(null);
    setIsTyping(true);

    try {
      const response = await api.post('/api/assistant/chat', {
        message: query
      });

      if (response.data.success) {
        const aiMsg = {
          id: `ai-${Date.now()}`,
          sender: 'ai',
          text: response.data.reply,
          timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
        };
        setMessages((prev) => [...prev, aiMsg]);
      } else {
        throw new Error(response.data.error || "Failed to get AI response.");
      }
    } catch (err) {
      console.error(err);
      const errorMsg = {
        id: `ai-err-${Date.now()}`,
        sender: 'ai',
        text: "Sorry, I encountered an error. Please verify the backend is running and GEMINI_API_KEY is configured.",
        isError: true,
        timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
      };
      setMessages((prev) => [...prev, errorMsg]);
    } finally {
      setIsTyping(false);
    }
  };

  // Preset User Message click handler
  const handleExampleQuery = () => {
    handleSendMessage("What are the top 3 features requested by users?");
  };

  // Attach File Action
  const handleAttachFile = (e) => {
    const file = e.target.files[0];
    if (file) {
      setAttachedFile(file);
    }
  };

  // Trigger file dialog
  const triggerFileInput = () => {
    fileInputRef.current?.click();
  };

  // Clear Chat history
  const handleClearChat = () => {
    setMessages([
      {
        id: 'welcome',
        sender: 'ai',
        text: "Hello! I'm your AI Product Manager Assistant. I can help analyze customer feedback, prioritize features, estimate business impact, generate product insights, and answer product management questions.",
        timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
      }
    ]);
  };

  // Custom Markdown & Lists Formatter
  const parseBoldAndItalic = (text) => {
    if (!text) return '';
    // Split by ** first to capture bold text
    const parts = text.split(/\*\*([^*]+)\*\*/g);
    return parts.map((part, idx) => {
      const isBold = idx % 2 !== 0;
      
      // Within each part, look for italic *text*
      const subParts = part.split(/\*([^*]+)\*/g);
      const renderedSubParts = subParts.map((subPart, subIdx) => {
        const isItalic = subIdx % 2 !== 0;
        if (isItalic) {
          return <em key={subIdx} style={{ fontStyle: 'italic', color: '#c084fc' }}>{subPart}</em>;
        }
        return subPart;
      });

      if (isBold) {
        return <strong key={idx} style={{ fontWeight: '700', color: '#ffffff' }}>{renderedSubParts}</strong>;
      }
      return <span key={idx}>{renderedSubParts}</span>;
    });
  };

  const formatMessageText = (text) => {
    if (!text) return '';
    
    const lines = text.split('\n');
    return lines.map((line, lineIdx) => {
      // Check for numbered list item like "1. **Dark Mode**..."
      const numListMatch = line.match(/^(\d+)\.\s+(.*)$/);
      if (numListMatch) {
        const num = numListMatch[1];
        const content = numListMatch[2];
        return (
          <div key={lineIdx} style={{ marginLeft: '0.75rem', marginBottom: '0.75rem', display: 'flex', gap: '0.5rem', alignItems: 'flex-start' }}>
            <span style={{ color: '#c084fc', fontWeight: '700', minWidth: '1.25rem' }}>{num}.</span>
            <span style={{ flex: 1, lineHeight: '1.6' }}>{parseBoldAndItalic(content)}</span>
          </div>
        );
      }

      // Check for bullet list item like "* *Explanation:* ..." or "- *Explanation:* ..."
      const bulletMatch = line.match(/^(\s*)([*+-])\s+(.*)$/);
      if (bulletMatch) {
        const indent = bulletMatch[1].length;
        const content = bulletMatch[3];
        return (
          <div key={lineIdx} style={{ marginLeft: `${indent * 0.5 + 1.25}rem`, marginBottom: '0.5rem', display: 'flex', gap: '0.5rem', alignItems: 'flex-start' }}>
            <span style={{ color: '#a78bfa', fontWeight: 'bold' }}>•</span>
            <span style={{ flex: 1, fontSize: '0.94rem', color: '#d1d5db', lineHeight: '1.5' }}>{parseBoldAndItalic(content)}</span>
          </div>
        );
      }

      // Default line
      return (
        <div key={lineIdx} style={{ marginBottom: '0.5rem', minHeight: '1.2em', lineHeight: '1.6' }}>
          {parseBoldAndItalic(line)}
        </div>
      );
    });
  };

  return (
    <div className="page-layout chatgpt-assistant-layout">
      <div className="chat-centered-container">
        
        {/* Header Section */}
        <header className="chat-header">
          <div className="chat-header-left">
            <h1 className="chat-main-title">AI Assistant</h1>
            <p className="chat-main-subtitle">
              Ask anything about product management, feedback analysis, feature prioritization, and business insights.
            </p>
          </div>
          <button onClick={handleClearChat} className="chat-clear-btn" title="Reset Chat History">
            <Trash2 size={16} />
            <span>Clear Chat</span>
          </button>
        </header>

        {/* Chat Feed */}
        <div className="chat-feed-box glass-panel-premium">
          <div className="chat-scroll-viewport">
            {messages.map((msg) => (
              <div
                key={msg.id}
                className={`chat-bubble-row ${msg.sender === 'user' ? 'align-right' : 'align-left'}`}
              >
                {/* Bot Icon */}
                {msg.sender === 'ai' && (
                  <div className="bubble-avatar avatar-bot">
                    <Bot size={18} color="#ffffff" />
                  </div>
                )}

                {/* Bubble Container */}
                <div className={`chat-message-bubble ${msg.sender === 'user' ? 'bubble-style-user' : 'bubble-style-ai'}`}>
                  {/* File preview inside message if uploaded */}
                  {msg.file && (
                    <div className="bubble-attachment-badge">
                      <FileText size={13} />
                      <span className="bubble-attachment-name">{msg.file}</span>
                    </div>
                  )}

                  {/* Message body */}
                  <div className="bubble-body-text">
                    {msg.sender === 'ai' ? formatMessageText(msg.text) : msg.text}
                  </div>

                  {/* Timestamp */}
                  <span className="bubble-timestamp">{msg.timestamp}</span>
                </div>

                {/* User Icon */}
                {msg.sender === 'user' && (
                  <div className="bubble-avatar avatar-user">
                    <User size={18} color="#ffffff" />
                  </div>
                )}
              </div>
            ))}

            {/* AI Response typing indicator */}
            {isTyping && (
              <div className="chat-bubble-row align-left">
                <div className="bubble-avatar avatar-bot">
                  <Bot size={18} color="#ffffff" />
                </div>
                <div className="chat-message-bubble bubble-style-ai loading-bubble">
                  <div className="typing-loader-dots">
                    <span className="loading-dot-pulse"></span>
                    <span className="loading-dot-pulse"></span>
                    <span className="loading-dot-pulse"></span>
                  </div>
                </div>
              </div>
            )}

            {/* Suggested Prompts & Example Question - Rendered right below welcome message inside the feed */}
            {messages.length === 1 && !isTyping && (
              <div className="welcome-prompt-suggestions-grid">
                
                {/* 1. Large Demo Prompt Card */}
                <div className="prompt-card highlight-card" onClick={handleExampleQuery}>
                  <div className="prompt-card-meta">
                    <HelpCircle size={16} color="#c084fc" />
                    <span className="card-badge">Demo Query</span>
                  </div>
                  <h4 className="prompt-card-title">"What are the top 3 features requested by users?"</h4>
                  <p className="prompt-card-description">Click to see the feedback aggregation results, percentages, and explanations.</p>
                  <div className="prompt-card-action">
                    <span>Ask this example</span>
                    <ArrowRight size={14} />
                  </div>
                </div>

                {/* 2. Standard Suggestion Cards */}
                {suggestedPrompts.map((prompt, idx) => (
                  <div key={idx} className="prompt-card" onClick={() => setInputText(prompt)}>
                    <div className="prompt-card-meta">
                      <Sparkles size={14} color="#a78bfa" />
                      <span className="card-badge">Suggested</span>
                    </div>
                    <h4 className="prompt-card-title">{prompt}</h4>
                    <p className="prompt-card-description">Generate insights relating to "{prompt.toLowerCase()}".</p>
                    <div className="prompt-card-action">
                      <span>Fill query box</span>
                      <ArrowRight size={14} />
                    </div>
                  </div>
                ))}

              </div>
            )}

            <div ref={chatEndRef} />
          </div>
        </div>

        {/* Input Bar Area */}
        <footer className="chat-input-sticky-panel glass-panel-premium">
          <div className="input-inner-wrapper">
            
            {/* Attachment preview capsule */}
            {attachedFile && (
              <div className="chat-input-attachment-preview">
                <div className="attachment-preview-badge">
                  <FileText size={14} color="#c084fc" />
                  <span className="attachment-file-label">{attachedFile.name}</span>
                  <button onClick={() => setAttachedFile(null)} className="remove-attachment-btn" title="Remove attachment">
                    <X size={14} />
                  </button>
                </div>
              </div>
            )}

            {/* Input Form */}
            <form
              onSubmit={(e) => {
                e.preventDefault();
                handleSendMessage();
              }}
              className="chat-input-form"
            >
              {/* Hidden file input */}
              <input
                type="file"
                ref={fileInputRef}
                onChange={handleAttachFile}
                style={{ display: 'none' }}
              />

              {/* Clip Action Button */}
              <button
                type="button"
                onClick={triggerFileInput}
                className="action-icon-btn clip-btn"
                title="Attach feedback CSV or TXT file"
              >
                <Paperclip size={20} />
              </button>

              {/* Text Input Field */}
              <input
                type="text"
                value={inputText}
                onChange={(e) => setInputText(e.target.value)}
                placeholder="Ask your AI Assistant..."
                className="chat-textarea-box"
              />

              {/* Gradient Submit Send Button */}
              <button
                type="submit"
                disabled={!inputText.trim() && !attachedFile}
                className="action-icon-btn send-btn-gradient"
                title="Send to AI Assistant"
              >
                <Send size={18} color="#ffffff" />
              </button>
            </form>
          </div>
        </footer>

      </div>

      {/* Modern Centered ChatGPT/Gemini Stylings */}
      <style>{`
        /* Page Layout and Centering */
        .chatgpt-assistant-layout {
          min-height: calc(100vh - 120px);
          display: flex;
          justify-content: center;
          width: 100%;
          animation: fadeIn 0.4s cubic-bezier(0.16, 1, 0.3, 1);
        }

        .chat-centered-container {
          width: 100%;
          max-width: 960px;
          display: flex;
          flex-direction: column;
          gap: 1.5rem;
          padding: 1rem 0.5rem;
        }

        /* Glass Panel Premium */
        .glass-panel-premium {
          background: rgba(15, 15, 26, 0.45);
          backdrop-filter: blur(20px);
          -webkit-backdrop-filter: blur(20px);
          border: 1px solid rgba(255, 255, 255, 0.06);
          border-radius: 24px;
          box-shadow: 0 8px 32px 0 rgba(0, 0, 0, 0.35);
          transition: var(--transition-smooth);
        }

        .glass-panel-premium:hover {
          border-color: rgba(124, 58, 237, 0.2);
          box-shadow: 0 12px 40px 0 rgba(124, 58, 237, 0.04);
        }

        /* Header Area */
        .chat-header {
          display: flex;
          justify-content: space-between;
          align-items: center;
          padding: 0.5rem 1rem;
        }

        .chat-main-title {
          font-size: 2.2rem;
          font-weight: 800;
          margin: 0;
          letter-spacing: -0.03em;
          background: linear-gradient(135deg, #ffffff 0%, #c084fc 100%);
          WebkitBackgroundClip: text;
          WebkitTextFillColor: transparent;
        }

        .chat-main-subtitle {
          color: var(--text-secondary);
          font-size: 0.98rem;
          margin: 0.4rem 0 0 0;
          line-height: 1.5;
        }

        .chat-clear-btn {
          display: flex;
          align-items: center;
          gap: 0.5rem;
          border-radius: 14px;
          padding: 0.65rem 1.1rem;
          background: rgba(255, 255, 255, 0.02);
          border: 1px solid rgba(255, 255, 255, 0.06);
          color: var(--text-secondary);
          font-size: 0.88rem;
          font-weight: 500;
          cursor: pointer;
          transition: var(--transition-smooth);
        }

        .chat-clear-btn:hover {
          color: #ef4444;
          border-color: rgba(239, 68, 68, 0.35);
          background: rgba(239, 68, 68, 0.05);
        }

        /* Chat Feed Box */
        .chat-feed-box {
          flex: 1;
          height: 580px;
          padding: 2rem;
          overflow: hidden;
          position: relative;
        }

        .chat-scroll-viewport {
          height: 100%;
          overflow-y: auto;
          padding-right: 0.5rem;
          display: flex;
          flex-direction: column;
          gap: 1.5rem;
        }

        /* Scrollbars */
        .chat-scroll-viewport::-webkit-scrollbar {
          width: 6px;
        }

        .chat-scroll-viewport::-webkit-scrollbar-track {
          background: transparent;
        }

        .chat-scroll-viewport::-webkit-scrollbar-thumb {
          background: rgba(255, 255, 255, 0.04);
          border-radius: 10px;
        }

        .chat-scroll-viewport::-webkit-scrollbar-thumb:hover {
          background: rgba(124, 58, 237, 0.25);
        }

        /* Chat rows */
        .chat-bubble-row {
          display: flex;
          align-items: flex-start;
          gap: 1rem;
          max-width: 88%;
          animation: messageFadeIn 0.3s cubic-bezier(0.16, 1, 0.3, 1) forwards;
        }

        @keyframes messageFadeIn {
          from { opacity: 0; transform: translateY(10px); }
          to { opacity: 1; transform: translateY(0); }
        }

        .align-left {
          align-self: flex-start;
        }

        .align-right {
          align-self: flex-end;
          flex-direction: row;
        }

        /* Avatars */
        .bubble-avatar {
          width: 36px;
          height: 36px;
          border-radius: 10px;
          display: flex;
          align-items: center;
          justify-content: center;
          flex-shrink: 0;
          box-shadow: 0 4px 10px rgba(0, 0, 0, 0.2);
        }

        .avatar-bot {
          background: linear-gradient(135deg, #7c3aed 0%, #9333ea 100%);
          border: 1px solid rgba(255, 255, 255, 0.08);
          box-shadow: 0 0 10px rgba(124, 58, 237, 0.3);
        }

        .avatar-user {
          background: rgba(255, 255, 255, 0.06);
          border: 1px solid rgba(255, 255, 255, 0.1);
        }

        /* Chat bubbles */
        .chat-message-bubble {
          border-radius: 20px;
          padding: 1.1rem 1.4rem;
          color: var(--text-primary);
          font-size: 0.98rem;
          line-height: 1.6;
          box-shadow: 0 4px 15px rgba(0,0,0,0.1);
        }

        .bubble-style-ai {
          background: rgba(255, 255, 255, 0.025);
          border: 1px solid rgba(255, 255, 255, 0.05);
          border-top-left-radius: 4px;
        }

        .bubble-style-user {
          background: linear-gradient(135deg, rgba(124, 58, 237, 0.15) 0%, rgba(147, 51, 234, 0.08) 100%);
          border: 1px solid rgba(124, 58, 237, 0.25);
          border-top-right-radius: 4px;
          box-shadow: 0 4px 15px rgba(124, 58, 237, 0.08);
        }

        .bubble-attachment-badge {
          display: inline-flex;
          align-items: center;
          gap: 0.4rem;
          background: rgba(255, 255, 255, 0.06);
          border: 1px solid rgba(255, 255, 255, 0.08);
          padding: 0.3rem 0.65rem;
          border-radius: 8px;
          font-size: 0.78rem;
          margin-bottom: 0.5rem;
          color: #f3f4f6;
        }

        .bubble-attachment-name {
          max-width: 140px;
          overflow: hidden;
          text-overflow: ellipsis;
          white-space: nowrap;
          font-weight: 500;
        }

        .bubble-timestamp {
          display: block;
          font-size: 0.72rem;
          color: rgba(255, 255, 255, 0.35);
          text-align: right;
          margin-top: 0.45rem;
        }

        .bubble-style-user .bubble-timestamp {
          color: rgba(255, 255, 255, 0.5);
        }

        /* Typing loading indicator */
        .loading-bubble {
          padding: 0.85rem 1.25rem;
        }

        .typing-loader-dots {
          display: flex;
          gap: 0.3rem;
          align-items: center;
          height: 1.2rem;
        }

        .loading-dot-pulse {
          width: 7px;
          height: 7px;
          background: #a78bfa;
          border-radius: 50%;
          animation: dotPulse 1.2s infinite ease-in-out;
        }

        .loading-dot-pulse:nth-child(2) {
          animation-delay: 0.2s;
        }

        .loading-dot-pulse:nth-child(3) {
          animation-delay: 0.4s;
        }

        @keyframes dotPulse {
          0%, 100% { transform: scale(0.8); opacity: 0.5; }
          50% { transform: scale(1.2); opacity: 1; }
        }

        /* Welcome Prompt Suggestions Grid */
        .welcome-prompt-suggestions-grid {
          display: grid;
          grid-template-columns: repeat(2, 1fr);
          gap: 1rem;
          margin-top: 1.5rem;
          animation: gridFadeIn 0.5s cubic-bezier(0.16, 1, 0.3, 1) forwards;
        }

        @keyframes gridFadeIn {
          from { opacity: 0; transform: translateY(15px); }
          to { opacity: 1; transform: translateY(0); }
        }

        .prompt-card {
          background: rgba(255, 255, 255, 0.015);
          border: 1px solid rgba(255, 255, 255, 0.05);
          border-radius: 18px;
          padding: 1.2rem;
          cursor: pointer;
          transition: var(--transition-smooth);
          display: flex;
          flex-direction: column;
          gap: 0.4rem;
          position: relative;
          overflow: hidden;
        }

        .prompt-card:hover {
          background: rgba(255, 255, 255, 0.03);
          border-color: rgba(255, 255, 255, 0.12);
          transform: translateY(-2px);
          box-shadow: 0 4px 15px rgba(0, 0, 0, 0.1);
        }

        .highlight-card {
          border-color: rgba(124, 58, 237, 0.2);
          background: linear-gradient(135deg, rgba(124, 58, 237, 0.05) 0%, rgba(147, 51, 234, 0.01) 100%);
        }

        .highlight-card:hover {
          border-color: rgba(124, 58, 237, 0.45);
          box-shadow: 0 4px 20px rgba(124, 58, 237, 0.08);
        }

        .prompt-card-meta {
          display: flex;
          align-items: center;
          gap: 0.35rem;
        }

        .card-badge {
          font-size: 0.72rem;
          text-transform: uppercase;
          letter-spacing: 0.05em;
          color: var(--text-muted);
          font-weight: 600;
        }

        .highlight-card .card-badge {
          color: #c084fc;
        }

        .prompt-card-title {
          font-size: 0.95rem;
          font-weight: 600;
          color: #ffffff;
          margin: 0;
          line-height: 1.4;
        }

        .prompt-card-description {
          font-size: 0.82rem;
          color: var(--text-secondary);
          margin: 0;
          line-height: 1.4;
          flex-grow: 1;
        }

        .prompt-card-action {
          display: flex;
          align-items: center;
          gap: 0.35rem;
          font-size: 0.78rem;
          font-weight: 600;
          color: #c084fc;
          margin-top: 0.5rem;
          transition: var(--transition-smooth);
        }

        .prompt-card:hover .prompt-card-action {
          color: #a78bfa;
          transform: translateX(4px);
        }

        /* Bottom Sticky Panel */
        .chat-input-sticky-panel {
          padding: 1.1rem 1.5rem;
        }

        .input-inner-wrapper {
          display: flex;
          flex-direction: column;
          gap: 0.6rem;
        }

        .chat-input-attachment-preview {
          display: flex;
        }

        .attachment-preview-badge {
          display: inline-flex;
          align-items: center;
          gap: 0.5rem;
          background: rgba(124, 58, 237, 0.08);
          border: 1px solid rgba(124, 58, 237, 0.25);
          padding: 0.38rem 0.8rem;
          border-radius: 12px;
          font-size: 0.82rem;
          color: #c084fc;
        }

        .attachment-file-label {
          font-weight: 500;
          max-width: 320px;
          overflow: hidden;
          text-overflow: ellipsis;
          white-space: nowrap;
        }

        .remove-attachment-btn {
          background: transparent;
          border: none;
          color: var(--text-muted);
          cursor: pointer;
          display: flex;
          align-items: center;
          padding: 0.1rem;
          border-radius: 50%;
          transition: var(--transition-smooth);
        }

        .remove-attachment-btn:hover {
          color: #ef4444;
          background: rgba(239, 68, 68, 0.1);
        }

        .chat-input-form {
          display: flex;
          align-items: center;
          gap: 0.75rem;
          position: relative;
        }

        .action-icon-btn {
          display: flex;
          align-items: center;
          justify-content: center;
          width: 46px;
          height: 46px;
          border-radius: 50%;
          background: rgba(255, 255, 255, 0.02);
          border: 1px solid rgba(255, 255, 255, 0.06);
          color: var(--text-secondary);
          cursor: pointer;
          transition: var(--transition-smooth);
          flex-shrink: 0;
        }

        .clip-btn:hover {
          background: rgba(255, 255, 255, 0.06);
          border-color: rgba(255, 255, 255, 0.15);
          color: var(--text-primary);
        }

        .chat-textarea-box {
          flex: 1;
          background: rgba(10, 10, 18, 0.45);
          border: 1px solid rgba(255, 255, 255, 0.06);
          border-radius: 28px;
          color: var(--text-primary);
          padding: 0.85rem 1.5rem;
          font-size: 0.98rem;
          outline: none;
          font-family: inherit;
          transition: var(--transition-smooth);
        }

        .chat-textarea-box:focus {
          border-color: rgba(124, 58, 237, 0.5);
          background: rgba(10, 10, 18, 0.65);
          box-shadow: 0 0 15px rgba(124, 58, 237, 0.25);
        }

        .send-btn-gradient {
          background: linear-gradient(135deg, #7c3aed 0%, #9333ea 100%);
          border: none;
          box-shadow: 0 4px 15px rgba(124, 58, 237, 0.25);
        }

        .send-btn-gradient:hover:not(:disabled) {
          transform: scale(1.05);
          box-shadow: 0 0 18px rgba(124, 58, 237, 0.55);
        }

        .send-btn-gradient:disabled {
          opacity: 0.4;
          cursor: not-allowed;
          box-shadow: none;
        }

        /* Responsive Layout adjustments */
        @media (max-width: 768px) {
          .welcome-prompt-suggestions-grid {
            grid-template-columns: 1fr;
          }
          .chat-header {
            flex-direction: column;
            align-items: flex-start;
            gap: 1rem;
          }
          .chat-clear-btn {
            width: 100%;
            justify-content: center;
          }
          .chat-feed-box {
            padding: 1.2rem;
            height: 480px;
          }
          .chat-bubble-row {
            max-width: 95%;
          }
        }
      `}</style>
    </div>
  );
};

export default AssistantPage;

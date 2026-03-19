import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter';
import { lucario } from 'react-syntax-highlighter/dist/esm/styles/prism';
import './ReportViewer.css';
import api from './api';

const ReportViewer = () => {
  const { jobId } = useParams();
  const navigate = useNavigate();
  const [activeTab, setActiveTab] = useState('markdown');
  const [reportData, setReportData] = useState(null);
  const [markdownContent, setMarkdownContent] = useState('');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    const fetchReport = async () => {
      setLoading(true);
      try {
        // 1. Fetch Job Metadata & JSON Report
        const res = await api.get(`/audit/${jobId}`);
        setReportData(res.data);

        // 2. Fetch Markdown Content
        try {
          const mdRes = await api.get(`/audit/${jobId}/report-markdown`);
          setMarkdownContent(mdRes.data);
        } catch (mdErr) {
          console.error("Markdown not available or error:", mdErr);
          setMarkdownContent('');
        }
      } catch (err) {
        setError(err.response?.data?.detail || err.message);
      } finally {
        setLoading(false);
      }
    };

    fetchReport();
  }, [jobId]);

  if (loading) return <div className="report-loading">Loading report...</div>;
  if (error) return <div className="report-error">Error: {error}</div>;

  return (
    <div className="report-viewer-container">
      <header className="report-header">
        <div className="header-left">
          <button onClick={() => navigate(-1)} className="back-btn">← Back</button>
          <h1>Audit Report: <span className="job-id-text">{jobId}</span></h1>
        </div>
        <div className="header-right">
          <div className="score-badge" style={{ backgroundColor: getScoreColor(reportData?.report?.overall_health_score) }}>
            Score: {reportData?.report?.overall_health_score || 'N/A'}
          </div>
        </div>
      </header>

      <nav className="report-tabs">
        <button 
          className={`tab-btn ${activeTab === 'markdown' ? 'active' : ''}`}
          onClick={() => setActiveTab('markdown')}
        >
          Analysis (Markdown)
        </button>
        <button 
          className={`tab-btn ${activeTab === 'json' ? 'active' : ''}`}
          onClick={() => setActiveTab('json')}
        >
          Raw Data (JSON)
        </button>
      </nav>

      <main className="report-content">
        {activeTab === 'markdown' ? (
          <div className="markdown-view">
            {markdownContent ? (
              <ReactMarkdown 
                remarkPlugins={[remarkGfm]}
                components={{
                  code({ node, inline, className, children, ...props }) {
                    const match = /language-(\w+)/.exec(className || '');
                    return !inline && match ? (
                      <SyntaxHighlighter
                        style={lucario}
                        language={match[1]}
                        PreTag="div"
                        {...props}
                      >
                        {String(children).replace(/\n$/, '')}
                      </SyntaxHighlighter>
                    ) : (
                      <code className={className} {...props}>
                        {children}
                      </code>
                    );
                  }
                }}
              >
                {markdownContent}
              </ReactMarkdown>
            ) : (
              <p>Markdown report not available.</p>
            )}
          </div>
        ) : (
          <div className="json-view">
            <SyntaxHighlighter language="json" style={lucario}>
              {JSON.stringify(reportData?.report, null, 2)}
            </SyntaxHighlighter>
          </div>
        )}
      </main>
    </div>
  );
};

const getScoreColor = (score) => {
  if (score === undefined || score === null) return 'gray';
  if (score >= 8) return '#10b981'; // green
  if (score >= 6) return '#f59e0b'; // orange
  return '#ef4444'; // red
};

export default ReportViewer;

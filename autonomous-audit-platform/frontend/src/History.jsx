import React, { useState, useEffect } from 'react';
import api from './api';
import { Clock, CheckCircle2, AlertCircle, Eye } from 'lucide-react';
import { motion } from 'framer-motion';

const History = ({ onViewReport }) => {
  const [audits, setAudits] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchHistory();
  }, []);

  const fetchHistory = async () => {
    setLoading(true);
    try {
      const resp = await api.get('/audit/');
      setAudits(resp.data.jobs || []);
    } catch (err) {
      console.error("Error fetching history:", err);
    } finally {
      setLoading(false);
    }
  };

  const formatDate = (dateString) => {
    if (!dateString) return 'N/A';
    return new Date(dateString).toLocaleString();
  };

  return (
    <motion.div 
      initial={{ opacity: 0 }} 
      animate={{ opacity: 1 }}
      style={{ animation: 'fadeIn 0.5s ease' }}
    >
      <header style={{ marginBottom: '3rem' }}>
        <h2 style={{ fontSize: '2.5rem', marginBottom: '0.5rem' }} className="gradient-text">Audit History</h2>
        <p style={{ color: 'var(--text-dim)', fontSize: '1.1rem' }}>Review past security and quality audits across your projects.</p>
      </header>

      {loading ? (
        <div className="glass-card" style={{ textAlign: 'center', padding: '4rem' }}>
          <div className="spinner" style={{ margin: '0 auto 1.5rem auto' }}></div>
          <p style={{ color: 'var(--text-dim)' }}>Loading audit records...</p>
        </div>
      ) : audits.length === 0 ? (
        <div className="glass-card" style={{ textAlign: 'center', padding: '4rem' }}>
          <Clock size={48} style={{ color: 'var(--text-muted)', marginBottom: '1.5rem' }} />
          <h3 style={{ marginBottom: '0.5rem' }}>No Audits Found</h3>
          <p style={{ color: 'var(--text-dim)' }}>Run your first audit from the Dashboard to see it here.</p>
        </div>
      ) : (
        <div className="glass-card" style={{ padding: '0', overflow: 'hidden' }}>
          <table style={{ width: '100%', borderCollapse: 'collapse', textAlign: 'left' }}>
            <thead>
              <tr style={{ background: 'rgba(255,255,255,0.03)', borderBottom: '1px solid rgba(255,255,255,0.1)' }}>
                <th style={{ padding: '1.25rem' }}>Status</th>
                <th style={{ padding: '1.25rem' }}>Repository Path</th>
                <th style={{ padding: '1.25rem' }}>Health</th>
                <th style={{ padding: '1.25rem' }}>Date</th>
                <th style={{ padding: '1.25rem', textAlign: 'right' }}>Actions</th>
              </tr>
            </thead>
            <tbody>
              {audits.map((audit) => (
                <tr key={audit.job_id} style={{ borderBottom: '1px solid rgba(255,255,255,0.05)', transition: 'background 0.2s ease' }} className="history-row">
                  <td style={{ padding: '1.25rem' }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                      {audit.status === 'completed' ? (
                        <CheckCircle2 size={16} style={{ color: 'var(--success)' }} />
                      ) : audit.status === 'failed' ? (
                        <AlertCircle size={16} style={{ color: 'var(--error)' }} />
                      ) : (
                        <div className="spinner-sm"></div>
                      )}
                      <span style={{ fontSize: '0.875rem', textTransform: 'capitalize' }}>{audit.status}</span>
                    </div>
                  </td>
                  <td style={{ padding: '1.25rem' }}>
                    <div style={{ fontSize: '0.875rem', fontWeight: 500, maxWidth: '300px', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                      {audit.repo_path || audit.repo_url}
                    </div>
                  </td>
                  <td style={{ padding: '1.25rem' }}>
                    {audit.health_score !== null ? (
                      <div style={{ 
                        fontWeight: 700, 
                        color: audit.health_score >= 8 ? 'var(--success)' : audit.health_score >= 6 ? 'var(--warning)' : 'var(--error)' 
                      }}>
                        {audit.health_score}
                      </div>
                    ) : '-'}
                  </td>
                  <td style={{ padding: '1.25rem', fontSize: '0.875rem', color: 'var(--text-dim)' }}>
                    {formatDate(audit.created_at)}
                  </td>
                  <td style={{ padding: '1.25rem', textAlign: 'right' }}>
                    <button 
                      className="btn-secondary" 
                      style={{ padding: '0.5rem 1rem', fontSize: '0.75rem', display: 'inline-flex', alignItems: 'center', gap: '0.5rem' }}
                      onClick={() => onViewReport(audit.job_id)}
                      disabled={audit.status !== 'completed'}
                    >
                      <Eye size={14} /> View Report
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </motion.div>
  );
};

export default History;

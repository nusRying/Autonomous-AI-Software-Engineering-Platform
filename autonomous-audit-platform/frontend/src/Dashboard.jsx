import React, { useState, useEffect } from 'react';
import api from './api';
import { Play, Search, AlertCircle, CheckCircle2, FileText, ExternalLink, ArrowLeft, CloudDownload, FileJson } from 'lucide-react';
import { useParams, useNavigate } from 'react-router-dom';
import { motion, AnimatePresence } from 'framer-motion';

const Dashboard = () => {
  const [repoPath, setRepoPath] = useState('');
  const [loading, setLoading] = useState(false);
  const [jobId, setJobId] = useState(null);
  const [jobStatus, setJobStatus] = useState(null);
  const [report, setReport] = useState(null);
  const { jobId: urlJobId } = useParams();
  const navigate = useNavigate();
  const user = JSON.parse(localStorage.getItem('user') || '{}');
  const canAudit = user.role === 'admin' || user.role === 'developer';

  useEffect(() => {
    if (urlJobId) {
      setJobId(urlJobId);
      loadReport(urlJobId);
    }
  }, [urlJobId]);

  const loadReport = async (id) => {
    setLoading(true);
    setReport(null);
    try {
      const resp = await api.get(`/audit/${id}`);
      setJobStatus(resp.data.status);
      if (resp.data.status === 'completed') {
        setReport(resp.data.report);
      }
    } catch (err) {
      console.error("Error loading historical report:", err);
    } finally {
      setLoading(false);
    }
  };

  const startAudit = async () => {
    if (!repoPath) return;
    setLoading(true);
    setReport(null);
    try {
      const resp = await api.post('/audit/', { repo_path: repoPath });
      setJobId(resp.data.job_id);
    } catch (err) {
      alert(err.response?.data?.detail || "Error starting audit.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    let interval;
    if (jobId && !report) {
      interval = setInterval(async () => {
        try {
          const resp = await api.get(`/audit/${jobId}`);
          setJobStatus(resp.data.status);
          if (resp.data.status === 'completed') {
            setReport(resp.data.report);
            clearInterval(interval);
          } else if (resp.data.status === 'failed') {
            clearInterval(interval);
          }
        } catch (e) {
          clearInterval(interval);
        }
      }, 2000);
    }
    return () => clearInterval(interval);
  }, [jobId, report]);

  return (
    <div style={{ animation: 'fadeIn 0.5s ease' }}>
      <header style={{ marginBottom: '3rem' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '1rem', marginBottom: '0.5rem' }}>
          {urlJobId && (
            <button 
              onClick={() => navigate('/history')}
              style={{ background: 'transparent', border: 'none', color: 'var(--text-dim)', cursor: 'pointer', display: 'flex', alignItems: 'center', padding: '0.5rem' }}
            >
              <ArrowLeft size={24} />
            </button>
          )}
          <h2 style={{ fontSize: '2.5rem' }} className="gradient-text">
            {urlJobId ? "Audit Report" : "Audit Dashboard"}
          </h2>
        </div>
        <p style={{ color: 'var(--text-dim)', fontSize: '1.1rem' }}>
          {urlJobId ? `Reviewing results for audit #${urlJobId}` : "Initiate autonomous AI security & quality audits on any Python repository."}
        </p>
      </header>

      {/* Audit Input Section */}
      {!urlJobId && (
        <section className="glass-card" style={{ marginBottom: '2rem' }}>
          <div style={{ display: 'flex', gap: '1rem', alignItems: 'center' }}>
            <div style={{ flex: 1, position: 'relative' }}>
              <Search style={{ position: 'absolute', left: '1rem', top: '50%', transform: 'translateY(-50%)', color: 'var(--text-muted)' }} size={20} />
              <input 
                className="input-glass" 
                style={{ paddingLeft: '3rem' }} 
                placeholder="Enter local repository absolute path..." 
                value={repoPath}
                onChange={(e) => setRepoPath(e.target.value)}
                disabled={!canAudit}
              />
            </div>
            <button className="btn-primary" onClick={startAudit} disabled={loading || (jobId && !report) || !canAudit}>
              {loading ? "Initializing..." : (jobId && !report ? "Audit Running..." : "Start Full Audit")}
            </button>
          </div>
          {!canAudit && <p style={{ color: 'var(--warning)', fontSize: '0.8rem', marginTop: '0.5rem' }}>Only Admins and Developers can trigger new audits.</p>}
        </section>
      )}

      {/* Progress View */}
      <AnimatePresence>
        {jobId && !report && (
          <motion.div 
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0 }}
            className="glass-card" 
            style={{ marginBottom: '2rem', display: 'flex', alignItems: 'center', gap: '1.5rem', borderColor: 'var(--primary)' }}
          >
            <div className="spinner"></div>
            <div>
              <div style={{ fontWeight: 600, fontSize: '1.1rem' }}>Audit in Progress...</div>
              <div style={{ color: 'var(--text-dim)', fontSize: '0.875rem' }}>Job ID: {jobId} | Status: {jobStatus}</div>
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Result Section */}
      {report && (
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 2fr', gap: '2rem' }}>
          {/* Summary Column */}
          <div style={{ display: 'flex', flexDirection: 'column', gap: '2rem' }}>
            <div className="glass-card" style={{ textAlign: 'center', background: 'rgba(255, 255, 255, 0.02)' }}>
              <div style={{ color: 'var(--text-dim)', fontSize: '0.9rem', marginBottom: '1rem' }}>Health Score</div>
              <HealthGauge score={report.overall_health_score} />
              <div style={{ marginTop: '1rem', fontWeight: 600, fontSize: '1.25rem' }}>
                {report.overall_health_score >= 8 ? "Excellent" : report.overall_health_score >= 6 ? "Good" : "Action Required"}
              </div>
            </div>

            <div className="glass-card">
              <h3 style={{ marginBottom: '1.5rem', fontSize: '1.1rem', fontWeight: 600, display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                <CloudDownload size={20} className="text-primary" />
                Audit Result Views
              </h3>
              <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
                <FileItem 
                  onClick={() => navigate(`/report/${jobId}`)}
                  title="Interactive Report" 
                  type="Markdown / Analysis"
                  icon={<FileText size={20} style={{ color: 'var(--primary)' }} />} 
                />
                
                <FileItem 
                  onClick={() => navigate(`/report/${jobId}`)}
                  title="Raw Audit Data" 
                  type="JSON"
                  icon={<FileJson size={20} style={{ color: 'var(--secondary)' }} />} 
                />
              </div>
              <div style={{ marginTop: '1.5rem', paddingTop: '1rem', borderTop: '1px solid var(--glass-border)', fontSize: '0.75rem', color: 'var(--text-muted)', display: 'flex', justifyContent: 'space-between' }}>
                <span>Storage: MinIO Hybrid</span>
                <span>Status: Synced</span>
              </div>
            </div>

            <div className="glass-card">
              <h3 style={{ marginBottom: '1rem', fontSize: '1rem' }}>Stats</h3>
              <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
                <StatRow label="Critical Issues" value={report.findings.filter(f => f.severity === 'CRITICAL').length} color="var(--error)" />
                <StatRow label="High Issues" value={report.findings.filter(f => f.severity === 'HIGH').length} color="var(--warning)" />
                <StatRow label="Files Scanned" value={report.total_files_scanned} color="var(--secondary)" />
              </div>
            </div>
          </div>

          {/* Findings Column */}
          <div className="glass-card">
             <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '2rem' }}>
                <h3 style={{ fontSize: '1.25rem' }}>Findings & Recommendations</h3>
                <div style={{ color: 'var(--text-dim)', fontSize: '0.8rem' }}>{report.findings.length} total issues detected</div>
             </div>
             
             <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
                {report.findings.map((finding, idx) => (
                  <FindingCard key={idx} finding={finding} />
                ))}
             </div>
          </div>
        </div>
      )}
    </div>
  );
};

const HealthGauge = ({ score }) => {
  const percentage = (score || 0) * 10;
  const color = score >= 8 ? 'var(--success)' : score >= 6 ? 'var(--warning)' : 'var(--error)';
  return (
    <div style={{ position: 'relative', width: '120px', height: '120px', margin: '0 auto' }}>
      <svg width="120" height="120" viewBox="0 0 100 100">
        <circle cx="50" cy="50" r="45" fill="none" stroke="rgba(255,255,255,0.05)" strokeWidth="8" />
        <circle 
          cx="50" cy="50" r="45" fill="none" stroke={color} strokeWidth="8" 
          strokeDasharray="283" 
          strokeDashoffset={283 - (283 * percentage) / 100}
          strokeLinecap="round"
          style={{ transition: 'stroke-dashoffset 1s ease-out', transform: 'rotate(-90deg)', transformOrigin: '50% 50%' }}
        />
      </svg>
      <div style={{ position: 'absolute', top: '50%', left: '50%', transform: 'translate(-50%, -50%)', fontSize: '2rem', fontWeight: 700 }}>
        {score}
      </div>
    </div>
  );
};

const StatRow = ({ label, value, color }) => (
  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
    <span style={{ color: 'var(--text-dim)', fontSize: '0.875rem' }}>{label}</span>
    <span style={{ color, fontWeight: 700 }}>{value}</span>
  </div>
);

const FileItem = ({ onClick, title, type, icon }) => (
  <div onClick={onClick} className="file-card" style={{ cursor: 'pointer' }}>
    <div style={{ 
      width: '40px', 
      height: '40px', 
      borderRadius: '0.75rem', 
      background: 'rgba(255,255,255,0.03)', 
      display: 'flex', 
      alignItems: 'center', 
      justifyContent: 'center' 
    }}>
      {icon}
    </div>
    <div style={{ flex: 1 }}>
      <div style={{ fontSize: '0.875rem', fontWeight: 600 }}>{title}</div>
      <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>Format: {type}</div>
    </div>
    <ExternalLink size={14} style={{ opacity: 0.4 }} />
  </div>
);

const FindingCard = ({ finding }) => (
  <div style={{ 
    padding: '1.25rem', 
    borderRadius: '1rem', 
    background: 'rgba(255,255,255,0.02)', 
    borderLeft: `4px solid ${finding.severity === 'CRITICAL' ? 'var(--error)' : finding.severity === 'HIGH' ? 'var(--warning)' : 'var(--secondary)'}`
  }}>
    <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '0.5rem' }}>
      <span style={{ fontWeight: 600 }}>{finding.title || finding.file}</span>
      <span className={`badge badge-${finding.severity?.toLowerCase() === 'critical' || finding.severity?.toLowerCase() === 'high' ? 'error' : 'warning'}`}>
        {finding.severity}
      </span>
    </div>
    <p style={{ fontSize: '0.875rem', color: 'var(--text-dim)', lineHeight: 1.5, marginBottom: '0.75rem' }}>{finding.description}</p>
    <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', display: 'flex', gap: '1rem', alignItems: 'center' }}>
      <span style={{ display: 'flex', alignItems: 'center', gap: '0.25rem' }}><CheckCircle2 size={12}/> {finding.category || 'Quality'}</span>
      {finding.remediation && <span style={{ color: 'var(--secondary)' }}>{finding.remediation}</span>}
    </div>
  </div>
);

export default Dashboard;

import React, { useState, useEffect } from 'react';
import api from './api';
import { Sparkles, Terminal, Code2, Rocket, CloudDownload, Image as ImageIcon, CheckCircle2, AlertCircle, FileJson } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';

const EngineerDashboard = () => {
  const [prompt, setPrompt] = useState('');
  const [image, setImage] = useState(null);
  const [imagePreview, setImagePreview] = useState(null);
  const [loading, setLoading] = useState(false);
  const [jobId, setJobId] = useState(null);
  const [jobData, setJobData] = useState(null);
  const user = JSON.parse(localStorage.getItem('user') || '{}');
  const canEngineer = user.role === 'admin' || user.role === 'developer';

  const handleImageChange = (e) => {
    const file = e.target.files[0];
    if (file) {
      setImage(file);
      const reader = new FileReader();
      reader.onloadend = () => setImagePreview(reader.result);
      reader.readAsDataURL(file);
    }
  };

  const startGeneration = async () => {
    if (!prompt) return;
    setLoading(true);
    setJobData(null);
    try {
      const payload = { project_prompt: prompt };
      if (imagePreview) {
        payload.image_base64 = imagePreview;
      }
      const resp = await api.post('/engineer/', payload);
      setJobId(resp.data.job_id);
    } catch (err) {
      alert(err.response?.data?.detail || "Error starting project generation.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    let interval;
    if (jobId && (!jobData || jobData.status !== 'completed')) {
      interval = setInterval(async () => {
        try {
          const resp = await api.get(`/engineer/${jobId}`);
          setJobData(resp.data);
          if (resp.data.status === 'completed' || resp.data.status === 'failed') {
            clearInterval(interval);
          }
        } catch (e) {
          clearInterval(interval);
        }
      }, 3000);
    }
    return () => clearInterval(interval);
  }, [jobId, jobData]);

  return (
    <div style={{ animation: 'fadeIn 0.5s ease' }}>
      <header style={{ marginBottom: '3rem' }}>
        <h2 style={{ fontSize: '2.5rem' }} className="gradient-text">Autonomous Engineer</h2>
        <p style={{ color: 'var(--text-dim)', fontSize: '1.1rem' }}>
          Describe your project, upload a screenshot for UI inspiration, and watch AI build it from scratch.
        </p>
      </header>

      <div style={{ display: 'grid', gridTemplateColumns: '1.5fr 1fr', gap: '2rem' }}>
        {/* Input Column */}
        <section style={{ display: 'flex', flexDirection: 'column', gap: '2rem' }}>
          <div className="glass-card">
            <h3 style={{ marginBottom: '1.5rem', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
              <Sparkles size={20} color="var(--primary)" /> Project Definition
            </h3>
            
            <div style={{ marginBottom: '1.5rem' }}>
              <label style={{ display: 'block', marginBottom: '0.5rem', color: 'var(--text-dim)', fontSize: '0.875rem' }}>Prompt</label>
              <textarea 
                className="input-glass" 
                style={{ minHeight: '120px', padding: '1rem', width: '100%', resize: 'vertical' }}
                placeholder="e.g., Build a Task Management System with a FastAPI backend and a React/Tailwind frontend. Include user auth and task categories."
                value={prompt}
                onChange={(e) => setPrompt(e.target.value)}
                disabled={!canEngineer || (jobId && jobData?.status !== 'completed' && jobData?.status !== 'failed')}
              />
            </div>

            <div style={{ marginBottom: '2rem' }}>
              <label style={{ display: 'block', marginBottom: '0.5rem', color: 'var(--text-dim)', fontSize: '0.875rem' }}>UI Inspiration (Optional Screenshot)</label>
              <div style={{ display: 'flex', gap: '1rem', alignItems: 'start' }}>
                <label className="btn-secondary" style={{ cursor: 'pointer', display: 'flex', alignItems: 'center', gap: '0.5rem', padding: '0.75rem 1.25rem' }}>
                  <ImageIcon size={18} /> {imagePreview ? "Change Image" : "Upload Screenshot"}
                  <input type="file" hidden accept="image/*" onChange={handleImageChange} disabled={!canEngineer} />
                </label>
                {imagePreview && (
                  <div style={{ position: 'relative' }}>
                    <img src={imagePreview} alt="Preview" style={{ width: '80px', height: '80px', objectFit: 'cover', borderRadius: '0.5rem', border: '1px solid rgba(255,255,255,0.1)' }} />
                    <button 
                      onClick={() => {setImage(null); setImagePreview(null);}}
                      style={{ position: 'absolute', top: '-0.5rem', right: '-0.5rem', background: 'var(--error)', color: 'white', border: 'none', borderRadius: '50%', width: '20px', height: '20px', cursor: 'pointer', fontSize: '12px' }}
                    >X</button>
                  </div>
                )}
              </div>
            </div>

            <button 
              className="btn-primary" 
              style={{ width: '100%', padding: '1rem', fontSize: '1.1rem' }} 
              onClick={startGeneration}
              disabled={loading || !prompt || !canEngineer || (jobId && jobData?.status !== 'completed' && jobData?.status !== 'failed')}
            >
              <Rocket size={20} style={{ marginRight: '0.5rem' }} />
              {loading ? "Initializing..." : "Launch Autonomous Build"}
            </button>
          </div>

          <AnimatePresence>
            {jobData && (
              <motion.div 
                initial={{ opacity: 0, scale: 0.95 }}
                animate={{ opacity: 1, scale: 1 }}
                className="glass-card" 
                style={{ borderColor: jobData.status === 'completed' ? 'var(--success)' : jobData.status === 'failed' ? 'var(--error)' : 'var(--primary)' }}
              >
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1.5rem' }}>
                   <h3 style={{ fontSize: '1.1rem' }}>Build Status</h3>
                   <span className={`badge badge-${jobData.status === 'completed' ? 'success' : jobData.status === 'failed' ? 'error' : 'primary'}`}>
                      {jobData.status.toUpperCase()}
                   </span>
                </div>
                
                <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
                   <div style={{ display: 'flex', alignItems: 'center', gap: '1rem' }}>
                      <div className={jobData.status !== 'completed' && jobData.status !== 'failed' ? 'spinner' : ''} style={{ width: '20px', height: '20px' }}>
                        {jobData.status === 'completed' && <CheckCircle2 size={20} color="var(--success)" />}
                        {jobData.status === 'failed' && <AlertCircle size={20} color="var(--error)" />}
                      </div>
                      <span style={{ fontSize: '0.9rem', color: 'var(--text-dim)' }}>
                        {jobData.status === 'pending' && "Initializing pipeline..."}
                        {jobData.status === 'planning' && "Architecting system design..."}
                        {jobData.status.startsWith('coding') && `Implementation Attempt ${jobData.status.split('_').pop()}...`}
                        {jobData.status === 'verifying' && "Running Docker stability tests & generating docs..."}
                        {jobData.status === 'completed' && "Project successfully built and verified!"}
                        {jobData.status === 'failed' && `Error: ${jobData.error}`}
                      </span>
                   </div>
                </div>

                {jobData.status === 'completed' && (
                  <div style={{ marginTop: '2rem', display: 'flex', gap: '1rem' }}>
                    <a href={jobData.repo_url} target="_blank" rel="noreferrer" className="btn-primary" style={{ flex: 1, textDecoration: 'none', display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '0.5rem' }}>
                       <CloudDownload size={18} /> Download Code
                    </a>
                  </div>
                )}
              </motion.div>
            )}
          </AnimatePresence>
        </section>

        {/* Sidebar Column (Stats & Specs) */}
        <section style={{ display: 'flex', flexDirection: 'column', gap: '2rem' }}>
          <div className="glass-card">
            <h3 style={{ marginBottom: '1rem', fontSize: '1rem', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
              <Code2 size={18} color="var(--secondary)" /> Technical Specification
            </h3>
            {jobData?.technical_spec ? (
              <div style={{ background: 'rgba(0,0,0,0.2)', padding: '1rem', borderRadius: '0.5rem', maxHeight: '400px', overflowY: 'auto' }}>
                <pre style={{ fontSize: '0.75rem', color: 'var(--secondary)', whiteSpace: 'pre-wrap' }}>
                  {JSON.stringify(jobData.technical_spec, null, 2)}
                </pre>
              </div>
            ) : (
              <p style={{ color: 'var(--text-muted)', fontSize: '0.875rem', textAlign: 'center', padding: '2rem' }}>
                Spec will be displayed here once planning starts.
              </p>
            )}
          </div>

          <div className="glass-card">
            <h3 style={{ marginBottom: '1.5rem', fontSize: '1rem' }}>Recent Builds</h3>
            <RecentBuildList jobId={jobId} />
          </div>
        </section>
      </div>
    </div>
  );
};

const RecentBuildList = ({ currentJobId }) => {
  const [builds, setBuilds] = useState([]);
  
  useEffect(() => {
    const fetchBuilds = async () => {
      try {
        const resp = await api.get('/engineer/');
        setBuilds(resp.data.jobs.slice(0, 5));
      } catch (e) {}
    };
    fetchBuilds();
  }, [currentJobId]);

  if (builds.length === 0) return <div style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>No builds yet.</div>;

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
      {builds.map(b => (
        <div key={b.job_id} style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', fontSize: '0.85rem' }}>
          <span style={{ color: 'var(--text-dim)', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap', maxWidth: '150px' }}>
            {b.project_name || "Untitled"}
          </span>
          <span className={`badge badge-${b.status === 'completed' ? 'success' : 'primary'}`} style={{ fontSize: '0.7rem' }}>
            {b.status}
          </span>
        </div>
      ))}
    </div>
  );
};

export default EngineerDashboard;

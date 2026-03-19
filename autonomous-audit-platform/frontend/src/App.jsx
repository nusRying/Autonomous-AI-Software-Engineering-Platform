import React from 'react';
import { Routes, Route, Navigate, useNavigate } from 'react-router-dom';
import Layout from './Layout.jsx';
import Dashboard from './Dashboard.jsx';
import EngineerDashboard from './EngineerDashboard.jsx';
import APIManager from './APIManager.jsx';
import History from './History.jsx';
import ReportViewer from './ReportViewer.jsx';
import WorkflowCanvas from './components/WorkflowCanvas.jsx';
import Login from './Login.jsx';
import { Activity, Terminal, ShieldAlert, Rocket } from 'lucide-react';

// Guard component to redirect unauthenticated users
const ProtectedRoute = ({ children }) => {
  const token = localStorage.getItem('token');
  if (!token) return <Navigate to="/login" replace />;
  return <Layout>{children}</Layout>;
};

const App = () => {
  const navigate = useNavigate();

  return (
    <Routes>
      <Route path="/login" element={<Login />} />
      
      {/* Protected Routes wrapped in Layout via the Guard */}
      <Route path="/" element={<ProtectedRoute><HomeOverview /></ProtectedRoute>} />
      <Route path="/audit-runner" element={<ProtectedRoute><Dashboard /></ProtectedRoute>} />
      <Route path="/audit-runner/:jobId" element={<ProtectedRoute><Dashboard /></ProtectedRoute>} />
      <Route path="/report/:jobId" element={<ProtectedRoute><ReportViewer /></ProtectedRoute>} />
      <Route path="/engineer" element={<ProtectedRoute><EngineerDashboard /></ProtectedRoute>} />
      <Route path="/history" element={<ProtectedRoute><History onViewReport={(id) => navigate(`/report/${id}`)} /></ProtectedRoute>} />
      <Route path="/api-keys" element={<ProtectedRoute><APIManager /></ProtectedRoute>} />
      
      <Route path="*" element={<Navigate to="/" />} />
    </Routes>
  );
};

const HomeOverview = () => (
  <div style={{ animation: 'fadeIn 0.5s ease' }}>
    <header style={{ marginBottom: '4rem' }}>
      <h2 style={{ fontSize: '3.5rem', fontWeight: 800, marginBottom: '1rem' }} className="gradient-text">
        Welcome to Audit AI
      </h2>
      <p style={{ fontSize: '1.25rem', color: 'var(--text-dim)', maxWidth: '700px', lineHeight: 1.6 }}>
        The state-of-the-art autonomous auditing platform. Built for security, speed, and absolute quality.
      </p>
    </header>

    <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '2rem' }}>
      <FeatureCard 
        icon={<Activity color="var(--primary)" />} 
        title="Predictive Audits" 
        desc="AI agents simulate developer workflows to catch bugs before they reach production." 
      />
      <FeatureCard 
        icon={<ShieldAlert color="var(--accent)" />} 
        title="Security Scanning" 
        desc="Real-time vulnerability detection using specialized security-focused LLM agents." 
      />
      <FeatureCard 
        icon={<Terminal color="var(--secondary)" />} 
        title="Live Feedback" 
        desc="Watch agents research, plan, and audit your code in real-time." 
      />
    </div>

    <div style={{ marginTop: '4rem' }}>
      <h3 style={{ fontSize: '1.5rem', marginBottom: '1.5rem' }}>Visual Workflow Intelligence</h3>
      <WorkflowCanvas />
    </div>

    <div className="glass-card" style={{ marginTop: '4rem', display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '3rem' }}>
      <div>
        <h3 style={{ fontSize: '1.5rem', marginBottom: '0.5rem' }}>Ready to secure your codebase?</h3>
        <p style={{ color: 'var(--text-dim)' }}>Run your first autonomous audit in seconds.</p>
      </div>
      <a href="/audit-runner" className="btn-primary" style={{ textDecoration: 'none' }}>Get Started Now</a>
    </div>
  </div>
);

const FeatureCard = ({ icon, title, desc }) => (
  <div className="glass-card">
    <div style={{ marginBottom: '1.5rem', transform: 'scale(1.2)', transformOrigin: 'left' }}>{icon}</div>
    <h3 style={{ marginBottom: '1rem' }}>{title}</h3>
    <p style={{ color: 'var(--text-dim)', fontSize: '0.9rem', lineHeight: 1.6 }}>{desc}</p>
  </div>
);

export default App;

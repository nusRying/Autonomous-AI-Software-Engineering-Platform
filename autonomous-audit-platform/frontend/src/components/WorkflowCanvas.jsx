import React from 'react';

const WorkflowCanvas = () => {
  return (
    <div className="glass-card" style={{ 
      height: '300px', 
      display: 'flex', 
      flexDirection: 'column',
      alignItems: 'center', 
      justifyContent: 'center',
      borderStyle: 'dashed',
      borderColor: 'rgba(255, 255, 255, 0.2)',
      background: 'rgba(255, 255, 255, 0.02)'
    }}>
      <div style={{ 
        padding: '1.5rem', 
        borderRadius: '50%', 
        background: 'rgba(var(--primary-rgb), 0.1)', 
        marginBottom: '1rem',
        animation: 'pulse 2s infinite'
      }}>
        <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="lucide lucide-activity">
          <path d="M22 12h-4l-3 9L9 3l-3 9H2"/>
        </svg>
      </div>
      <h4 style={{ marginBottom: '0.5rem', opacity: 0.8 }}>Visual Workflow Intelligence</h4>
      <p style={{ color: 'var(--text-dim)', fontSize: '0.9rem' }}>
        Low-Code workflow engine is initializing...
      </p>
    </div>
  );
};

export default WorkflowCanvas;

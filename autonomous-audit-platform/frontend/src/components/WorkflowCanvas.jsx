import React from 'react';

const WorkflowCanvas = () => {
  return (
    <div className="glass-card" style={{ 
      height: '500px', 
      display: 'flex', 
      flexDirection: 'column',
      padding: '0',
      overflow: 'hidden',
      border: '1px solid rgba(255, 255, 255, 0.1)',
      position: 'relative'
    }}>
      {/* Header for the Visualizer */}
      <div style={{ 
        padding: '1rem 1.5rem', 
        background: 'rgba(255, 255, 255, 0.03)', 
        borderBottom: '1px solid rgba(255, 255, 255, 0.1)',
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center'
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
          <div className="pulse-dot"></div>
          <span style={{ fontSize: '0.9rem', fontWeight: 600, color: 'var(--text-dim)' }}>
            LIVE ARCHITECTURE MAP (RADIOGRAFÍA)
          </span>
        </div>
        <div style={{ display: 'flex', gap: '1rem' }}>
          <a href="http://localhost:8082" target="_blank" rel="noreferrer" style={{ fontSize: '0.8rem', color: 'var(--primary)' }}>Open Full Visualizer</a>
          <a href="http://localhost:8081" target="_blank" rel="noreferrer" style={{ fontSize: '0.8rem', color: 'var(--secondary)' }}>Open Appsmith Panel</a>
        </div>
      </div>

      {/* Real Structurizr Iframe */}
      <iframe 
        src="http://localhost:8082" 
        style={{ 
          width: '100%', 
          height: '100%', 
          border: 'none',
          filter: 'invert(0.9) hue-rotate(180deg) brightness(1.2)' // Adjusted to match dark theme better
        }}
        title="Architecture Map"
      />

      {/* Overlay status */}
      <div style={{ 
        position: 'absolute', 
        bottom: '1rem', 
        right: '1rem', 
        padding: '0.5rem 1rem', 
        background: 'rgba(0,0,0,0.6)', 
        borderRadius: '4px',
        fontSize: '0.75rem',
        backdropFilter: 'blur(4px)',
        color: 'rgba(255,255,255,0.7)'
      }}>
        C4 Model Generator: Active
      </div>
    </div>
  );
};

export default WorkflowCanvas;

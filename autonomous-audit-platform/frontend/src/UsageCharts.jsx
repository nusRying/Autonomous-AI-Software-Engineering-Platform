import React from 'react';

const UsageCharts = ({ dailyUsage = [], providerUsage = [] }) => {
  // Line Chart Calculation
  const hasData = dailyUsage.length > 0;
  const maxTokens = hasData ? Math.max(...dailyUsage.map(d => d.tokens), 1000) : 1000;
  const chartHeight = 150;
  const chartWidth = 400;
  
  const points = hasData ? dailyUsage.map((d, i) => {
    const x = dailyUsage.length > 1 ? (i / (dailyUsage.length - 1)) * chartWidth : chartWidth / 2;
    const y = chartHeight - (d.tokens / maxTokens) * chartHeight;
    return `${x},${y}`;
  }).join(' ') : "";

  const areaPoints = hasData ? `0,${chartHeight} ${points} ${chartWidth},${chartHeight}` : `0,${chartHeight} ${chartWidth},${chartHeight}`;

  return (
    <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '2rem', marginBottom: '3rem' }}>
      {/* Daily Usage Trend */}
      <div className="glass-card">
        <h3 style={{ fontSize: '1.25rem', marginBottom: '1.5rem', color: 'var(--text-main)' }}>Daily Token Usage</h3>
        <div style={{ position: 'relative', height: chartHeight, width: '100%' }}>
          {hasData ? (
            <svg viewBox={`0 0 ${chartWidth} ${chartHeight}`} style={{ width: '100%', height: '100%', overflow: 'visible' }}>
              <defs>
                <linearGradient id="chartGradient" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="0%" stopColor="var(--primary)" stopOpacity="0.3" />
                  <stop offset="100%" stopColor="var(--primary)" stopOpacity="0" />
                </linearGradient>
              </defs>
              
              {/* Grid Lines */}
              {[0, 0.5, 1].map(p => (
                <line 
                  key={p}
                  x1="0" y1={chartHeight * p} x2={chartWidth} y2={chartHeight * p} 
                  stroke="rgba(255,255,255,0.05)" strokeWidth="1" 
                />
              ))}

              {/* Area */}
              <polyline points={areaPoints} fill="url(#chartGradient)" />
              
              {/* Line */}
              <polyline 
                points={points} 
                fill="none" 
                stroke="var(--primary)" 
                strokeWidth="3" 
                strokeLinecap="round" 
                strokeLinejoin="round" 
              />
              
              {/* Data Points */}
              {dailyUsage.map((d, i) => {
                const x = dailyUsage.length > 1 ? (i / (dailyUsage.length - 1)) * chartWidth : chartWidth / 2;
                const y = chartHeight - (d.tokens / maxTokens) * chartHeight;
                return (
                  <circle 
                    key={i} 
                    cx={x} cy={y} r="4" 
                    fill="var(--bg-color)" 
                    stroke="var(--primary)" 
                    strokeWidth="2" 
                  />
                );
              })}
            </svg>
          ) : (
            <div style={{ height: '100%', display: 'flex', alignItems: 'center', justifyContent: 'center', color: 'var(--text-muted)' }}>
              No usage data for the last 7 days.
            </div>
          )}
        </div>
        <div style={{ display: 'flex', justifyContent: 'space-between', marginTop: '1rem', color: 'var(--text-muted)', fontSize: '0.75rem' }}>
          {dailyUsage.map((d, i) => (
            <span key={i}>{new Date(d.day).toLocaleDateString(undefined, { weekday: 'short' })}</span>
          ))}
        </div>
      </div>

      {/* Provider Distribution */}
      <div className="glass-card">
        <h3 style={{ fontSize: '1.25rem', marginBottom: '1.5rem', color: 'var(--text-main)' }}>Provider Breakdown</h3>
        <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
          {providerUsage.map(p => {
            const total = providerUsage.reduce((acc, curr) => acc + curr.tokens, 0);
            const percentage = total > 0 ? (p.tokens / total) * 100 : 0;
            return (
              <div key={p.provider}>
                <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.875rem', marginBottom: '0.5rem' }}>
                  <span style={{ textTransform: 'capitalize' }}>{p.provider}</span>
                  <span style={{ color: 'var(--text-dim)' }}>{percentage.toFixed(1)}%</span>
                </div>
                <div style={{ width: '100%', height: '8px', background: 'rgba(255,255,255,0.05)', borderRadius: '4px', overflow: 'hidden' }}>
                  <div style={{ 
                    width: `${percentage}%`, 
                    height: '100%', 
                    background: p.provider === 'openai' ? 'var(--primary)' : 
                               p.provider === 'anthropic' ? 'var(--secondary)' : 'var(--accent)',
                    boxShadow: '0 0 10px rgba(255,255,255,0.1)'
                  }} />
                </div>
              </div>
            );
          })}
          {providerUsage.length === 0 && (
            <div style={{ textAlign: 'center', color: 'var(--text-muted)', padding: '2rem 0' }}>
              No provider data available.
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default UsageCharts;

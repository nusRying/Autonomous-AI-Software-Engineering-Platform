import React, { useState, useEffect } from 'react';
import api from './api';
import { Key, Plus, Trash2, CheckCircle, XCircle, AlertTriangle } from 'lucide-react';
import UsageCharts from './UsageCharts';

const APIManager = () => {
  const [keys, setKeys] = useState([]);
  const [usageStats, setUsageStats] = useState({ total_tokens: 0, daily_usage: [], provider_usage: [] });
  const [showAdd, setShowAdd] = useState(false);
  const [newKey, setNewKey] = useState({ provider: 'openai', api_key: '', label: '' });
  const user = JSON.parse(localStorage.getItem('user') || '{}');
  const isAdmin = user.role === 'admin';

  const fetchKeys = async () => {
    try {
      const resp = await api.get('/api/api_keys/');
      setKeys(Array.isArray(resp.data) ? resp.data : []);
    } catch (e) {
      console.error("Failed to fetch keys");
    }
  };

  const fetchUsage = async () => {
    try {
      const resp = await api.get('/api/analytics/usage');
      setUsageStats(resp.data);
    } catch (e) {
      console.error("Failed to fetch usage stats");
    }
  };

  useEffect(() => { 
    fetchKeys(); 
    fetchUsage();
  }, []);

  const addKey = async () => {
    try {
      await api.post('/api/api_keys/', newKey);
      setShowAdd(false);
      setNewKey({ provider: 'openai', api_key: '', label: '' });
      fetchKeys();
    } catch (e) {
      alert(e.response?.data?.detail || "Failed to add key");
    }
  };

  const deleteKey = async (id) => {
    if (!confirm("Remove this API key?")) return;
    try {
      await api.delete(`/api/api_keys/${id}`);
      fetchKeys();
    } catch (e) {
      alert(e.response?.data?.detail || "Failed to delete key");
    }
  };

  return (
    <div style={{ animation: 'fadeIn 0.5s ease' }}>
      <header style={{ marginBottom: '3rem', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <div>
          <h2 style={{ fontSize: '2.5rem', marginBottom: '0.5rem' }} className="gradient-text">API Credentials</h2>
          <p style={{ color: 'var(--text-dim)', fontSize: '1.1rem' }}>Manage LLM provider keys with auto-rotation and usage tracking.</p>
        </div>
        {isAdmin && (
          <button className="btn-primary" onClick={() => setShowAdd(true)} style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
            <Plus size={20} /> Add Provider Key
          </button>
        )}
      </header>

      <UsageCharts 
        dailyUsage={usageStats.daily_usage} 
        providerUsage={usageStats.provider_usage} 
      />

      {showAdd && (
        <div className="glass-card" style={{ marginBottom: '2rem', border: '1px solid var(--primary)' }}>
          <h3 style={{ marginBottom: '1.5rem' }}>Add New Credential</h3>
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 2fr 1fr', gap: '1rem', marginBottom: '1.5rem' }}>
            <select 
              className="input-glass" 
              value={newKey.provider} 
              onChange={e => setNewKey({...newKey, provider: e.target.value})}
              style={{ background: 'rgba(0,0,0,0.5)' }}
            >
              <option value="openai">OpenAI</option>
              <option value="anthropic">Anthropic</option>
              <option value="google">Google Gemini</option>
            </select>
            <input 
              className="input-glass" 
              placeholder="Paste API Key here..." 
              value={newKey.api_key}
              onChange={e => setNewKey({...newKey, api_key: e.target.value})}
            />
            <input 
              className="input-glass" 
              placeholder="Label (optional)" 
              value={newKey.label}
              onChange={e => setNewKey({...newKey, label: e.target.value})}
            />
          </div>
          <div style={{ display: 'flex', gap: '1rem', justifyContent: 'flex-end' }}>
            <button style={{ background: 'transparent', border: 'none', color: 'white', cursor: 'pointer' }} onClick={() => setShowAdd(false)}>Cancel</button>
            <button className="btn-primary" onClick={addKey}>Save Credential</button>
          </div>
        </div>
      )}

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(350px, 1fr))', gap: '1.5rem' }}>
        {keys.length > 0 ? keys.map((k) => (
          <KeyCard key={k.id} k={k} onDelete={() => deleteKey(k.id)} isAdmin={isAdmin} />
        )) : (
          <div className="glass-card" style={{ gridColumn: '1 / -1', textAlign: 'center', padding: '4rem', opacity: 0.6 }}>
            <Key size={48} style={{ margin: '0 auto 1.5rem', display: 'block' }} />
            <p>No API keys configured yet. {isAdmin ? "Add one to enable AI auditing." : "Contact an administrator to add keys."}</p>
          </div>
        )}
      </div>
    </div>
  );
};

const KeyCard = ({ k, onDelete, isAdmin }) => (
  <div className="glass-card" style={{ position: 'relative' }}>
    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '1.5rem' }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: '1rem' }}>
        <div style={{ padding: '0.75rem', background: 'rgba(255,255,255,0.05)', borderRadius: '0.75rem' }}>
          <Key size={24} color="var(--secondary)" />
        </div>
        <div>
          <div style={{ fontWeight: 600, fontSize: '1.1rem' }}>{k.provider.toUpperCase()}</div>
          <div style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>ID: {k.id}</div>
        </div>
      </div>
      {isAdmin && (
        <button 
          onClick={onDelete}
          style={{ 
            background: 'rgba(239, 68, 68, 0.05)', 
            border: '1px solid rgba(239, 68, 68, 0.1)', 
            color: 'var(--text-dim)', 
            cursor: 'pointer', 
            padding: '0.6rem',
            borderRadius: '0.75rem',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            transition: 'all 0.2s ease'
          }}
          onMouseOver={e => {
            e.currentTarget.style.color = 'var(--error)';
            e.currentTarget.style.background = 'rgba(239, 68, 68, 0.1)';
            e.currentTarget.style.borderColor = 'var(--error)';
            e.currentTarget.style.transform = 'scale(1.05)';
          }}
          onMouseOut={e => {
            e.currentTarget.style.color = 'var(--text-dim)';
            e.currentTarget.style.background = 'rgba(239, 68, 68, 0.05)';
            e.currentTarget.style.borderColor = 'rgba(239, 68, 68, 0.1)';
            e.currentTarget.style.transform = 'scale(1)';
          }}
          title="Delete Key"
        >
          <Trash2 size={18} />
        </button>
      )}
    </div>

    <div style={{ marginBottom: '1.5rem' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.8rem', marginBottom: '0.5rem' }}>
        <span style={{ color: 'var(--text-dim)' }}>Usage</span>
        <span>{k.tokens_used.toLocaleString()} tokens used</span>
      </div>
      <div style={{ width: '100%', height: '6px', background: 'rgba(255,255,255,0.05)', borderRadius: '3px', overflow: 'hidden' }}>
        <div style={{ 
          width: `${Math.min((k.tokens_used / (k.token_limit || 100000)) * 100, 100)}%`, 
          height: '100%', 
          background: 'linear-gradient(90deg, var(--primary), var(--secondary))' 
        }}></div>
      </div>
    </div>

    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
       <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', fontSize: '0.875rem' }}>
          {k.is_active ? <CheckCircle size={16} color="var(--success)" /> : <XCircle size={16} color="var(--error)" />}
          <span style={{ color: k.is_active ? 'var(--success)' : 'var(--error)', fontWeight: 500 }}>
            {k.is_active ? 'Active & Ready' : 'Exhausted / Inactive'}
          </span>
       </div>
       {k.label && <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>{k.label}</span>}
    </div>
  </div>
);

export default APIManager;

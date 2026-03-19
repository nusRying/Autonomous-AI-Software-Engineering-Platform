import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Shield, Lock, User, AlertCircle } from 'lucide-react';
import api from './api';

const Login = () => {
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const navigate = useNavigate();

  const handleLogin = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError('');

    try {
      const formData = new FormData();
      formData.append('username', username);
      formData.append('password', password);

      const resp = await api.post('/api/auth/login', formData);
      const { access_token } = resp.data;
      
      localStorage.setItem('token', access_token);
      
      // Fetch user info
      const userResp = await api.get('/api/auth/me');
      localStorage.setItem('user', JSON.stringify(userResp.data));
      
      navigate('/');
    } catch (err) {
      setError(err.response?.data?.detail || 'Login failed. Please check your credentials.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div style={{ minHeight: '100vh', display: 'flex', alignItems: 'center', justifyContent: 'center', background: 'var(--bg-dark)' }}>
      <div className="glass-card" style={{ width: '100%', maxWidth: '450px', padding: '3rem', border: '1px solid rgba(255, 255, 255, 0.05)' }}>
        <div style={{ textAlign: 'center', marginBottom: '3rem' }}>
          <div style={{ display: 'inline-flex', padding: '1rem', background: 'rgba(59, 130, 246, 0.1)', borderRadius: '1rem', marginBottom: '1.5rem' }}>
            <Shield size={40} color="var(--primary)" />
          </div>
          <h1 className="gradient-text" style={{ fontSize: '2.5rem', marginBottom: '0.5rem' }}>Audit Engine</h1>
          <p style={{ color: 'var(--text-dim)' }}>Sign in to access the autonomous platform.</p>
        </div>

        <form onSubmit={handleLogin} style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>
          <div style={{ position: 'relative' }}>
            <User size={18} style={{ position: 'absolute', left: '1rem', top: '50%', transform: 'translateY(-50%)', color: 'var(--text-muted)' }} />
            <input 
              className="input-glass" 
              style={{ paddingLeft: '3rem' }} 
              placeholder="Username" 
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              required
            />
          </div>
          
          <div style={{ position: 'relative' }}>
            <Lock size={18} style={{ position: 'absolute', left: '1rem', top: '50%', transform: 'translateY(-50%)', color: 'var(--text-muted)' }} />
            <input 
              className="input-glass" 
              type="password"
              style={{ paddingLeft: '3rem' }} 
              placeholder="Password" 
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
            />
          </div>

          {error && (
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', color: 'var(--error)', fontSize: '0.875rem', padding: '0.75rem', background: 'rgba(239, 68, 68, 0.1)', borderRadius: '0.5rem' }}>
              <AlertCircle size={16} />
              {error}
            </div>
          )}

          <button className="btn-primary" type="submit" disabled={loading} style={{ padding: '1rem', fontSize: '1.1rem', marginTop: '1rem' }}>
            {loading ? "Authenticating..." : "Sign In"}
          </button>
        </form>

        <div style={{ marginTop: '2rem', textAlign: 'center', fontSize: '0.875rem', color: 'var(--text-muted)' }}>
          Default Admin: <code style={{ color: 'var(--primary)' }}>admin / admin123</code>
        </div>
      </div>
    </div>
  );
};

export default Login;

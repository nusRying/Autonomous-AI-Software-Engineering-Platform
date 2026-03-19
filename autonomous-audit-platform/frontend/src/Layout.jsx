import React from 'react';
import { NavLink, useNavigate } from 'react-router-dom';
import { LayoutDashboard, Key, ShieldCheck, Activity, Terminal, Clock, LogOut, User } from 'lucide-react';

const Layout = ({ children }) => {
  const navigate = useNavigate();
  const user = JSON.parse(localStorage.getItem('user') || '{}');

  const handleLogout = () => {
    localStorage.removeItem('token');
    localStorage.removeItem('user');
    navigate('/login');
  };

  return (
    <div style={{ display: 'flex', minHeight: '100vh' }}>
      {/* Sidebar */}
      <aside className="glass-card" style={{ 
        width: '280px', 
        height: 'calc(100vh - 2rem)', 
        margin: '1rem', 
        padding: '2rem 1rem',
        display: 'flex',
        flexDirection: 'column',
        position: 'sticky',
        top: '1rem'
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', marginBottom: '3rem', padding: '0 1rem' }}>
          <ShieldCheck size={32} color="var(--secondary)" />
          <h1 className="gradient-text" style={{ fontSize: '1.25rem', fontWeight: 700 }}>AUDIT AI</h1>
        </div>

        <nav style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem', flex: 1 }}>
          <SidebarLink to="/" icon={<LayoutDashboard size={20} />} label="Overview" />
          <SidebarLink to="/audit-runner" icon={<Activity size={20} />} label="Run Audit" />
          <SidebarLink to="/engineer" icon={<Terminal size={20} />} label="Autonomous Engineer" />
          <SidebarLink to="/api-keys" icon={<Key size={20} />} label="API Keys" />
          <SidebarLink to="/history" icon={<Clock size={20} />} label="Audit History" />
        </nav>

        {/* User Profile & Logout */}
        <div style={{ marginTop: 'auto', display: 'flex', flexDirection: 'column', gap: '1rem' }}>
          <div className="glass-card" style={{ padding: '1rem', borderRadius: '1rem', display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
            <div style={{ background: 'rgba(255,255,255,0.05)', padding: '0.5rem', borderRadius: '0.5rem' }}>
              <User size={18} color="var(--primary)" />
            </div>
            <div style={{ overflow: 'hidden' }}>
              <div style={{ fontWeight: 600, fontSize: '0.875rem', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>{user.username || 'User'}</div>
              <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', textTransform: 'capitalize' }}>{user.role || 'Observer'}</div>
            </div>
          </div>

          <button 
            onClick={handleLogout}
            style={{ 
              display: 'flex', alignItems: 'center', gap: '0.75rem', padding: '0.75rem 1rem', 
              borderRadius: '0.75rem', background: 'rgba(239, 68, 68, 0.1)', border: 'none', 
              color: 'var(--error)', cursor: 'pointer', fontWeight: 600, fontSize: '0.875rem'
            }}
          >
            <LogOut size={18} /> Logout
          </button>
        </div>
      </aside>

      {/* Main Content */}
      <main style={{ flex: 1, padding: '2rem', maxWidth: '1200px', margin: '0 auto' }}>
        {children}
      </main>
    </div>
  );
};

const SidebarLink = ({ to, icon, label }) => (
  <NavLink 
    to={to} 
    style={({ isActive }) => ({
      display: 'flex',
      alignItems: 'center',
      gap: '1rem',
      padding: '0.75rem 1rem',
      borderRadius: '0.75rem',
      color: isActive ? 'white' : 'var(--text-dim)',
      background: isActive ? 'rgba(255, 255, 255, 0.05)' : 'transparent',
      textDecoration: 'none',
      fontWeight: isActive ? 600 : 400,
      transition: 'all 0.2s ease'
    })}
  >
    {icon}
    <span>{label}</span>
  </NavLink>
);

export default Layout;

import { StrictMode, useEffect, useState } from 'react';
import { createRoot } from 'react-dom/client';
import Dashboard from '../pages/Dashboard';
import Login from '../pages/Login';
import './styles.css';

function App() {
  const [token, setToken] = useState<string>(() => localStorage.getItem('plantops-token') || '');

  useEffect(() => {
    if (token) {
      localStorage.setItem('plantops-token', token);
    } else {
      localStorage.removeItem('plantops-token');
    }
  }, [token]);

  if (!token) {
    return <Login onLoggedIn={setToken} />;
  }

  return <Dashboard token={token} onLogout={() => setToken('')} />;
}

const root = document.getElementById('root');
if (!root) throw new Error('Frontend root element was not found.');

createRoot(root).render(<StrictMode><App /></StrictMode>);

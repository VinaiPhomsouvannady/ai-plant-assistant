import { StrictMode, useEffect, useState } from 'react';
import { createRoot } from 'react-dom/client';
import Dashboard from '../pages/Dashboard';
import Login from '../pages/Login';
import './styles.css';

function App() {
  const [authenticated, setAuthenticated] = useState<boolean | null>(null);

  useEffect(() => {
    fetch('/api/auth/me', { credentials: 'include' })
      .then((response) => setAuthenticated(response.ok))
      .catch(() => setAuthenticated(false));
  }, []);

  if (authenticated === null) {
    return <main className="login-shell" />;
  }

  if (!authenticated) {
    return <Login onLoggedIn={() => setAuthenticated(true)} />;
  }

  async function handleLogout() {
    await fetch('/api/auth/logout', { method: 'POST', credentials: 'include' });
    setAuthenticated(false);
  }

  return <Dashboard onLogout={handleLogout} />;
}

const root = document.getElementById('root');
if (!root) throw new Error('Frontend root element was not found.');

createRoot(root).render(<StrictMode><App /></StrictMode>);

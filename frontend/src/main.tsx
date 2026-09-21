import { StrictMode } from 'react';
import { createRoot } from 'react-dom/client';
import Dashboard from '../pages/Dashboard';
import './styles.css';

const root = document.getElementById('root');
if (!root) throw new Error('Frontend root element was not found.');

createRoot(root).render(<StrictMode><Dashboard /></StrictMode>);

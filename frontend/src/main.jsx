import { StrictMode } from 'react';
import { createRoot } from 'react-dom/client';
import App from './App';
import './styles/global.css';
import { BrowserRouter } from 'react-router-dom';
import { AuthProvider } from './context/AuthProvider';
const root = document.getElementById('root');
if (!root) {
    throw new Error('Elemen root aplikasi tidak ditemukan.');
}
createRoot(root).render(<StrictMode>
    <BrowserRouter><AuthProvider><App /></AuthProvider></BrowserRouter>
  </StrictMode>);

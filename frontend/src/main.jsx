import { StrictMode } from 'react';
import { createRoot } from 'react-dom/client';
import { BrowserRouter } from 'react-router-dom';
import { AuthProvider } from './context/AuthProvider';
<<<<<<< HEAD
=======
import { AppStateProvider } from './context/AppStateProvider';
>>>>>>> origin/develop
import App from './App';
import './styles/global.css';

createRoot(document.getElementById('root')).render(
  <StrictMode>
    <BrowserRouter>
      <AuthProvider>
<<<<<<< HEAD
        <App />
=======
        <AppStateProvider>
          <App />
        </AppStateProvider>
>>>>>>> origin/develop
      </AuthProvider>
    </BrowserRouter>
  </StrictMode>,
);

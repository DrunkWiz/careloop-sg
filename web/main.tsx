import { StrictMode } from 'react';
import { createRoot } from 'react-dom/client';
import './shared/tokens.css';
import SeniorApp from './senior/SeniorApp';
import CareApp from './care/CareApp';

const path = window.location.pathname;
const App = path.startsWith('/care') ? CareApp : SeniorApp;

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <App />
  </StrictMode>,
);

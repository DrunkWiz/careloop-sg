import { StrictMode } from 'react';
import { createRoot } from 'react-dom/client';
import './shared/tokens.css';
import SeniorApp from './senior/SeniorApp';
import CareApp from './care/CareApp';
import Welcome from './Welcome';
import { doorFor, setUpApp } from './shared/pwa';

const path = window.location.pathname;
setUpApp(doorFor(path, window.location.search));
const App = path.startsWith('/care') ? CareApp : path.startsWith('/senior') ? SeniorApp : Welcome;

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <App />
  </StrictMode>,
);

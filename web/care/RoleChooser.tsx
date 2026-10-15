// /care: which CareLoop are you? Family and centre staff get different apps, built for different jobs.
// Until login exists, the demo people are listed here (all synthetic).
import { usingMocks } from '../shared/api';

// `mock`: also in the offline mocks (the others need the API's demo, npm run dev:live).
const FAMILY = [
  { caregiver: 'cg-weiling', name: 'Wei Ling', about: "Mr Tan's daughter", mock: true },
  { caregiver: 'cg-kelvin', name: 'Kelvin', about: "Mr Tan's son, and his own mother's main carer", mock: true },
  { caregiver: 'cg-mei', name: 'Mei', about: "Mdm Wong's daughter", mock: true },
  { caregiver: 'cg-priya', name: 'Priya', about: "Mdm Kaur's daughter, in London" },
  { caregiver: 'cg-arjun', name: 'Arjun', about: "Mdm Kaur's son" },
  { caregiver: 'cg-nur', name: 'Nur', about: "Encik Rahman's daughter" },
  { caregiver: 'cg-maria', name: 'Maria', about: "Encik Rahman's helper" },
  { caregiver: 'cg-junjie', name: 'Jun Jie', about: "Mdm Chua's son (sees her weekly summary)" },
  { caregiver: 'cg-huimin', name: 'Hui Min', about: "Mdm Chua's daughter-in-law" },
];
const CENTRE = [
  { worker: 'aac-siti', name: 'Siti', about: 'Befriender, Tampines centre: 7 seniors', mock: true },
  { worker: 'aac-farid', name: 'Farid', about: 'Befriender, Ang Mo Kio centre: 2 seniors' },
];

function go(path: string, extra: Record<string, string>) {
  const q = new URLSearchParams(window.location.search);
  Object.entries(extra).forEach(([k, v]) => q.set(k, v));
  window.location.href = `${path}?${q.toString()}`;
}

export default function RoleChooser() {
  const family = FAMILY.filter((f) => !usingMocks || f.mock);
  const centre = CENTRE.filter((c) => !usingMocks || c.mock);
  return (
    <div className="chooser">
      <header className="chooser-head">
        <p className="chooser-brand">CareLoop SG</p>
        <h1>Who's looking after someone today?</h1>
        <p className="care-muted">
          CareLoop stays quiet until something is different for the person you care for, then hands it to you with the evidence.
        </p>
      </header>

      <section className="chooser-card is-family">
        <div className="chooser-card-head">
          <span className="chooser-icon" aria-hidden="true">♥</span>
          <div>
            <h2>I'm family</h2>
            <p>One person: their week, their health, things to do nearby. Quiet unless they need you.</p>
          </div>
        </div>
        <div className="chooser-people">
          {family.map((f) => (
            <button key={f.caregiver} className="chooser-person" onClick={() => go('/care/family', { caregiver: f.caregiver })}>
              <strong>{f.name}</strong>
              <span>{f.about}</span>
            </button>
          ))}
        </div>
      </section>

      <section className="chooser-card is-centre">
        <div className="chooser-card-head">
          <span className="chooser-icon" aria-hidden="true">⌂</span>
          <div>
            <h2>I work at an Active Ageing Centre</h2>
            <p>Your whole caseload, sorted by who needs a look today. For seniors with no family to call.</p>
          </div>
        </div>
        <div className="chooser-people">
          {centre.map((c) => (
            <button key={c.worker} className="chooser-person" onClick={() => go('/care/aac', { worker: c.worker })}>
              <strong>{c.name}</strong>
              <span>{c.about}</span>
            </button>
          ))}
        </div>
      </section>

      <p className="care-muted chooser-note">Demo people. All synthetic.</p>
    </div>
  );
}

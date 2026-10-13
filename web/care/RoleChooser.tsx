// /care: which CareLoop are you? Family and centre staff get different apps, built for different jobs.
// Until login exists, the demo people are listed here (all synthetic).
const FAMILY = [
  { contact: 'tan-weiling', name: 'Wei Ling', about: "Mr Tan's daughter" },
  { contact: 'tan-kelvin', name: 'Kelvin', about: "Mr Tan's son" },
  { contact: 'wong-mei', name: 'Mei', about: "Mdm Wong's daughter" },
];

function go(path: string, extra: Record<string, string>) {
  const q = new URLSearchParams(window.location.search);
  Object.entries(extra).forEach(([k, v]) => q.set(k, v));
  window.location.href = `${path}?${q.toString()}`;
}

export default function RoleChooser() {
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
          {FAMILY.map((f) => (
            <button key={f.contact} className="chooser-person" onClick={() => go('/care/family', { contact: f.contact })}>
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
          <button className="chooser-person" onClick={() => go('/care/aac', { worker: 'aac-siti' })}>
            <strong>Siti</strong>
            <span>Befriender at an Active Ageing Centre</span>
          </button>
        </div>
      </section>

      <p className="care-muted chooser-note">Demo people. All synthetic.</p>
    </div>
  );
}

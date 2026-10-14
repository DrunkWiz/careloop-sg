import Brand from './shared/Brand';
import './welcome.css';

export default function Welcome() {
  return <div className="welcome">
    <header className="welcome-nav"><Brand /><a href="/care">Open caregiver app <span aria-hidden="true">↗</span></a></header>
    <main>
      <section className="welcome-hero">
        <div className="welcome-copy">
          <span className="welcome-eyebrow"><span /> A LITTLE CLOSER, EVERY DAY</span>
          <h1>Everyday care.<br /><em>A little more<br />peace of mind.</em></h1>
          <p>Small check-ins. A clearer picture. CareLoop helps Singapore seniors and the people who care for them stay connected between doctor visits.</p>
          <a className="welcome-cta" href="#choose">Find your CareLoop <span aria-hidden="true">↓</span></a>
          <div className="welcome-languages">English <span>·</span> Singlish <span>·</span> 中文</div>
        </div>
        <div className="welcome-scene" aria-label="Daily check-ins connect a senior with their family">
          <span className="scene-orbit orbit-one" /><span className="scene-orbit orbit-two" />
          <div className="scene-caption">CONNECTED BY CARE</div>
          <div className="scene-person person-senior"><span aria-hidden="true">☀</span><strong>A moment for you.</strong><small>A simple daily check-in</small></div>
          <div className="scene-connection" aria-hidden="true">♡</div>
          <div className="scene-person person-family"><span aria-hidden="true">⌂</span><strong>A little reassurance.</strong><small>A shared picture for family</small></div>
          <div className="scene-note"><span aria-hidden="true">✓</span><div><strong>Quiet when things are as usual.</strong><small>Clear next steps when someone needs you.</small></div></div>
        </div>
      </section>
      <section id="choose" className="welcome-doors">
        <div className="welcome-section-head"><div><span className="welcome-eyebrow">YOUR CARE, YOUR WAY</span><h2>Where would you like to start?</h2></div><p>One circle of care. A space for everyone.</p></div>
        <div className="welcome-door-grid">
          <article className="welcome-door"><span className="door-number">01 / FOR SENIORS</span><h3>My daily check-in</h3><p>Record your BP, remember your pills, or tell us how you feel. One simple step at a time.</p><a href="/senior">Open my app <span aria-hidden="true">↗</span></a><a className="door-demo" href="/senior?senior=tan">Try Mr Tan’s demo →</a></article>
          <article className="welcome-door"><span className="door-number">02 / FOR FAMILY</span><h3>Someone I care for</h3><p>See how their week is going, make a care plan, and know when it’s time to lend a hand.</p><a href="/care">Open family app <span aria-hidden="true">↗</span></a><a className="door-demo" href="/care/family/health?contact=wong-mei">Try Mei’s family demo →</a></article>
          <article className="welcome-door"><span className="door-number">03 / FOR CENTRES</span><h3>Our community</h3><p>A clearer view of your caseload, shared programmes, and support for seniors without family to call.</p><a href="/care/aac?worker=aac-siti">Explore centre demo <span aria-hidden="true">↗</span></a><span className="door-demo">Built for Active Ageing Centres</span></article>
        </div>
      </section>
      <div className="welcome-principles"><span>✓ Simple daily check-ins</span><span>✓ Sharing choices stay with the senior</span><span>✓ People decide the next step</span></div>
    </main>
    <footer className="welcome-footer"><Brand /><p>Hackathon prototype · All demo people and readings are synthetic.</p><span>Made for care in Singapore.</span></footer>
  </div>;
}

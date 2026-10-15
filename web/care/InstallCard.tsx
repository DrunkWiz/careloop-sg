// "Add to home screen": CareLoop as an app on the phone, with its own icon and no browser bar.
// Android and desktop Chrome offer a prompt we can trigger; iPhone has none, so it gets the steps.
import { useEffect, useState } from 'react';
import { canPrompt, isInstalled, isIos, onInstallChange, promptInstall } from '../shared/pwa';

export default function InstallCard({ senior }: { senior: string }) {
  const [, redraw] = useState(0);
  useEffect(() => onInstallChange(() => redraw((n) => n + 1)), []);
  const seniorLink = `${window.location.origin}/senior`;

  return (
    <section className="care-card">
      <h2>CareLoop on your home screen</h2>
      {isInstalled() ? (
        <p className="care-muted">Done: you're using the app from your home screen.</p>
      ) : canPrompt() ? (
        <>
          <p className="care-muted">Opens like an app, full screen, with its own icon.</p>
          <button className="care-secondary" onClick={() => void promptInstall()}>
            Add to home screen
          </button>
        </>
      ) : isIos() ? (
        <p className="care-muted">In Safari, tap Share, then “Add to Home Screen”.</p>
      ) : (
        <p className="care-muted">In your browser's menu, choose “Install app” or “Add to Home screen”.</p>
      )}
      <p className="care-muted">
        For {senior}'s phone: open <strong>{seniorLink}</strong> on it and add it the same way. It opens their app, with big buttons.
      </p>
    </section>
  );
}

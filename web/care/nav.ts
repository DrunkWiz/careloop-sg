// Client-side navigation within /care, keeping the query string (?contact=, ?scenario=).
export function navigate(path: string) {
  window.history.pushState(null, '', path + window.location.search);
  window.dispatchEvent(new PopStateEvent('popstate'));
  window.scrollTo(0, 0);
}

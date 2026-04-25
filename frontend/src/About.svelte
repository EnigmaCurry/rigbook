<script>
  import { onMount } from "svelte";

  let version = "";

  onMount(async () => {
    try {
      const res = await fetch("/api/version");
      const data = await res.json();
      version = data.version;
    } catch {}
  });
</script>

<div class="about">
  <h2>Guidebook {version ? `v${version}` : ""} <a href="#/settings/updates" class="updates-link">Check for updates</a></h2>
  <p>A web application template.</p>
  <p>
    <a href="https://github.com/EnigmaCurry/guidebook" target="_blank" rel="noopener">
      github.com/EnigmaCurry/guidebook
    </a>
  </p>

  <h3>Keyboard Shortcuts</h3>
  <table class="shortcuts">
    <tbody>
      <tr><td class="key">1</td><td>Records</td></tr>
      <tr><td class="key">2</td><td>Query</td></tr>
      <tr><td class="key">3</td><td>Notifications</td></tr>
      <tr><td class="key">4</td><td>Settings</td></tr>
      <tr><td class="key">5</td><td>About</td></tr>
      <tr><td class="key">N</td><td>New Record</td></tr>
      <tr><td class="key">W</td><td>Toggle dual pane</td></tr>
      <tr><td class="key">?</td><td>This page</td></tr>
      <tr><td class="key">Esc</td><td>Close menu / cancel</td></tr>
    </tbody>
  </table>

  <p class="license">MIT License &copy; 2026 EnigmaCurry</p>
</div>

<style>
  .about {
    max-width: 400px;
  }

  h2 {
    color: var(--accent);
    font-size: 1.4rem;
    margin: 0 0 0.75rem 0;
  }

  h3 {
    color: var(--text-muted);
    font-size: 1rem;
    margin: 1.25rem 0 0.5rem 0;
  }

  p {
    color: var(--text-muted);
    font-size: 0.9rem;
    margin: 0 0 0.5rem 0;
  }

  a {
    color: var(--accent);
  }

  a:hover {
    color: var(--accent);
    opacity: 0.8;
  }

  .shortcuts {
    width: 100%;
    border-collapse: collapse;
    font-size: 0.85rem;
  }

  .shortcuts td {
    padding: 0.3rem 0.5rem;
    border-bottom: 1px solid var(--border);
  }

  .key {
    color: var(--accent);
    font-weight: bold;
    font-family: monospace;
    font-size: 0.9rem;
    width: 60px;
  }

  .updates-link {
    font-size: 0.55em;
    color: var(--accent);
    font-weight: normal;
  }

  .license {
    margin-top: 1.5rem;
    font-size: 0.8rem;
    color: var(--text-dimmer);
  }
</style>

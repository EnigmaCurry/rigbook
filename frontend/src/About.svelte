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
  <h2>Rigbook {version ? `v${version}` : ""}</h2>
  <p>A ham radio logbook web application.</p>
  <p>
    <a href="https://github.com/EnigmaCurry/rigbook" target="_blank" rel="noopener">
      github.com/EnigmaCurry/rigbook
    </a>
  </p>

  <h3>Keyboard Shortcuts</h3>
  <table class="shortcuts">
    <tbody>
      <tr><td class="key">/</td><td>Focus search</td></tr>
      <tr><td class="key">N</td><td>New QSO</td></tr>
      <tr><td class="key">H</td><td>Hunting (home)</td></tr>
      <tr><td class="key">L</td><td>Logbook</td></tr>
      <tr><td class="key">S</td><td>Spots</td></tr>
      <tr><td class="key">P</td><td>My Parks</td></tr>
      <tr><td class="key">T</td><td>Tune radio</td></tr>
      <tr><td class="key">M</td><td>Cycle radio mode</td></tr>
      <tr><td class="key">?</td><td>This page</td></tr>
      <tr><td class="key">PgUp</td><td>Scroll logbook up</td></tr>
      <tr><td class="key">PgDn</td><td>Scroll logbook down</td></tr>
      <tr><td class="key">Home</td><td>Scroll logbook to top</td></tr>
      <tr><td class="key">End</td><td>Scroll logbook to bottom</td></tr>
      <tr><td class="key">Shift + Scroll</td><td>Scroll logbook horizontally</td></tr>
      <tr><td class="key">Up/Down</td><td>Navigate rows (Spots, My Parks)</td></tr>
      <tr><td class="key">Enter</td><td>Log QSO (Spots) / View park (My Parks)</td></tr>
      <tr><td class="key">Esc</td><td>Close search / menu / deselect row</td></tr>
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
    color: var(--accent-vfo);
  }

  a:hover {
    color: var(--accent);
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

  .license {
    margin-top: 1.5rem;
    font-size: 0.8rem;
    color: var(--text-dimmer);
  }
</style>

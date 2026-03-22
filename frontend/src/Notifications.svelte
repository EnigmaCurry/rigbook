<script>
  import { onMount, onDestroy, createEventDispatcher } from "svelte";

  const dispatch = createEventDispatcher();

  let view = "inbox";
  let notifications = [];
  let doneNotifications = [];
  let loading = true;

  async function fetchInbox() {
    try {
      const res = await fetch("/api/notifications/");
      if (res.ok) notifications = await res.json();
    } catch {}
    loading = false;
  }

  async function fetchDone() {
    try {
      const res = await fetch("/api/notifications/done");
      if (res.ok) doneNotifications = await res.json();
    } catch {}
  }

  async function markRead(id) {
    await fetch(`/api/notifications/${id}/read`, { method: "PUT" });
    await fetchInbox();
    dispatch("countchange");
  }

  async function markDone(id) {
    await fetch(`/api/notifications/${id}/done`, { method: "PUT" });
    await fetchInbox();
    if (view === "done") await fetchDone();
    dispatch("countchange");
  }

  async function markAllRead() {
    await fetch("/api/notifications/read-all", { method: "PUT" });
    await fetchInbox();
    dispatch("countchange");
  }

  async function deleteNotification(id) {
    await fetch(`/api/notifications/${id}`, { method: "DELETE" });
    await fetchDone();
  }

  function switchView(v) {
    view = v;
    if (v === "done") fetchDone();
    else fetchInbox();
  }

  function formatTime(ts) {
    if (!ts) return "";
    return ts.replace("T", " ").replace("Z", "z");
  }

  function formatFreq(freqKhz) {
    const mhz = parseFloat(freqKhz) / 1000;
    if (isNaN(mhz)) return freqKhz;
    return mhz.toFixed(3);
  }

  function tuneToSpot(meta) {
    dispatch("tune", meta);
  }

  function addQsoFromSpot(meta) {
    dispatch("addqso", meta);
  }

  let eventSource;

  onMount(() => {
    fetchInbox();
    eventSource = new EventSource("/api/events/stream");
    eventSource.addEventListener("notification", () => {
      if (view === "inbox") fetchInbox();
    });
    eventSource.addEventListener("unread", () => {
      if (view === "inbox") fetchInbox();
    });
  });

  onDestroy(() => {
    if (eventSource) eventSource.close();
  });
</script>

<div class="notifications">
  <h2>Notifications</h2>

  <div class="tabs">
    <button class="tab" class:active={view === "inbox"} on:click={() => switchView("inbox")}>Inbox</button>
    <button class="tab" class:active={view === "done"} on:click={() => switchView("done")}>Done</button>
    {#if view === "inbox" && notifications.some(n => !n.read)}
      <button class="mark-all-btn" on:click={markAllRead}>Mark All Read</button>
    {/if}
  </div>

  {#if view === "inbox"}
    {#if loading}
      <p class="empty">Loading...</p>
    {:else if notifications.length === 0}
      <p class="empty">No notifications.</p>
    {:else}
      {#each notifications as notif (notif.id)}
        <div class="notif-card" class:unread={!notif.read}>
          <div class="notif-header">
            <span class="notif-title">{notif.title}</span>
            <span class="notif-time">{formatTime(notif.timestamp)}</span>
          </div>
          <div class="notif-text">
            {#if notif.meta?.callsign}
              <!-- svelte-ignore a11y-click-events-have-key-events -->
              <!-- svelte-ignore a11y-no-static-element-interactions -->
              <span class="clickable callsign" on:click={() => addQsoFromSpot(notif.meta)} title="Log QSO with {notif.meta.callsign}">{notif.meta.callsign}</span>
              {" on "}
              <!-- svelte-ignore a11y-click-events-have-key-events -->
              <!-- svelte-ignore a11y-no-static-element-interactions -->
              <span class="clickable freq" on:click={() => tuneToSpot(notif.meta)} title="Tune radio to {formatFreq(notif.meta.frequency)} MHz">{formatFreq(notif.meta.frequency)} MHz</span>
              {" "}{notif.meta.mode}{#if notif.text.includes(" — ")} — {notif.text.split(" — ").slice(1).join(" — ")}{/if}
            {:else}
              {notif.text}
            {/if}
          </div>
          <div class="notif-actions">
            {#if !notif.read}
              <button class="action-btn" on:click={() => markRead(notif.id)}>Mark Read</button>
            {/if}
            <button class="action-btn" on:click={() => markDone(notif.id)}>Done</button>
          </div>
        </div>
      {/each}
    {/if}
  {:else}
    {#if doneNotifications.length === 0}
      <p class="empty">No done notifications.</p>
    {:else}
      {#each doneNotifications as notif (notif.id)}
        <div class="notif-card done">
          <div class="notif-header">
            <span class="notif-title">{notif.title}</span>
            <span class="notif-time">{formatTime(notif.timestamp)}</span>
          </div>
          <div class="notif-text">
            {#if notif.meta?.callsign}
              <!-- svelte-ignore a11y-click-events-have-key-events -->
              <!-- svelte-ignore a11y-no-static-element-interactions -->
              <span class="clickable callsign" on:click={() => addQsoFromSpot(notif.meta)} title="Log QSO with {notif.meta.callsign}">{notif.meta.callsign}</span>
              {" on "}
              <!-- svelte-ignore a11y-click-events-have-key-events -->
              <!-- svelte-ignore a11y-no-static-element-interactions -->
              <span class="clickable freq" on:click={() => tuneToSpot(notif.meta)} title="Tune radio to {formatFreq(notif.meta.frequency)} MHz">{formatFreq(notif.meta.frequency)} MHz</span>
              {" "}{notif.meta.mode}{#if notif.text.includes(" — ")} — {notif.text.split(" — ").slice(1).join(" — ")}{/if}
            {:else}
              {notif.text}
            {/if}
          </div>
          <div class="notif-actions">
            <button class="action-btn delete-btn" on:click={() => deleteNotification(notif.id)}>Delete</button>
          </div>
        </div>
      {/each}
    {/if}
  {/if}
</div>

<style>
  .notifications {
    max-width: 600px;
  }

  h2 {
    color: var(--accent);
    font-size: 1.2rem;
    margin: 0 0 1rem 0;
  }

  .tabs {
    display: flex;
    gap: 0.5rem;
    margin-bottom: 1rem;
    align-items: center;
  }

  .tab {
    background: var(--bg-card);
    color: var(--text-muted);
    border: 1px solid var(--border);
    padding: 0.4rem 1rem;
    font-family: inherit;
    font-size: 0.85rem;
    border-radius: 3px;
    cursor: pointer;
  }

  .tab.active {
    color: var(--accent);
    border-color: var(--accent);
    font-weight: bold;
  }

  .tab:hover {
    background: var(--bg-input);
  }

  .mark-all-btn {
    margin-left: auto;
    background: var(--btn-secondary, #3e404a);
    color: var(--text);
    border: none;
    padding: 0.3rem 0.8rem;
    font-family: inherit;
    font-size: 0.75rem;
    border-radius: 3px;
    cursor: pointer;
  }

  .mark-all-btn:hover {
    background: var(--btn-secondary-hover, #4e505a);
  }

  .empty {
    color: var(--text-dim);
    font-size: 0.9rem;
  }

  .notif-card {
    background: var(--bg-card);
    border: 1px solid var(--border);
    border-radius: 4px;
    padding: 0.6rem 0.8rem;
    margin-bottom: 0.5rem;
  }

  .notif-card.unread {
    border-left: 3px solid var(--accent);
  }

  .notif-card.done {
    opacity: 0.7;
  }

  .notif-header {
    display: flex;
    justify-content: space-between;
    align-items: baseline;
    margin-bottom: 0.25rem;
  }

  .notif-title {
    font-weight: bold;
    font-size: 0.85rem;
    color: var(--text);
  }

  .unread .notif-title {
    color: var(--accent);
  }

  .notif-time {
    font-size: 0.7rem;
    color: var(--text-dim);
  }

  .notif-text {
    font-size: 0.8rem;
    color: var(--text-muted);
    margin-bottom: 0.4rem;
  }

  .clickable {
    cursor: pointer;
    text-decoration: underline;
    text-decoration-style: dotted;
  }

  .clickable:hover {
    text-decoration-style: solid;
  }

  .clickable.callsign {
    color: var(--accent-callsign, #ffcc00);
    font-weight: bold;
  }

  .clickable.freq {
    color: var(--accent);
  }

  .notif-actions {
    display: flex;
    gap: 0.5rem;
  }

  .action-btn {
    background: var(--btn-secondary, #3e404a);
    color: var(--text);
    border: none;
    padding: 0.2rem 0.6rem;
    font-family: inherit;
    font-size: 0.7rem;
    border-radius: 3px;
    cursor: pointer;
  }

  .action-btn:hover {
    background: var(--btn-secondary-hover, #4e505a);
  }

  .delete-btn:hover {
    background: #a03030;
  }
</style>

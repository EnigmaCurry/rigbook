<script>
  import { createEventDispatcher } from "svelte";

  export let value = "";
  export let items = [];
  export let placeholder = "";

  const dispatch = createEventDispatcher();

  let open = false;
  let highlightIndex = -1;

  function matchScore(item, query) {
    const q = query.toLowerCase();
    if (typeof item === "string") {
      if (item.toLowerCase() === q) return 3;
      if (item.toLowerCase().startsWith(q)) return 2;
      if (item.toLowerCase().includes(q)) return 1;
      return 0;
    }
    const { name = "", aliases = [] } = item;
    // Exact alias match gets highest priority
    if (aliases.some(a => a.toLowerCase() === q)) return 4;
    if (name.toLowerCase() === q) return 3;
    if (aliases.some(a => a.toLowerCase().startsWith(q))) return 3;
    if (name.toLowerCase().startsWith(q)) return 2;
    if (name.toLowerCase().includes(q)) return 1;
    if (aliases.some(a => a.toLowerCase().includes(q))) return 1;
    return 0;
  }

  function label(item) {
    return typeof item === "string" ? item : item.name;
  }

  $: filtered = value
    ? items
        .map(i => ({ item: i, score: matchScore(i, value) }))
        .filter(x => x.score > 0)
        .sort((a, b) => b.score - a.score)
        .slice(0, 20)
        .map(x => x.item)
    : items.slice(0, 20);

  function onInput() {
    open = true;
    highlightIndex = -1;
    dispatch("input");
  }

  function onFocus() {
    open = true;
  }

  function onBlur() {
    // delay so click on option registers
    setTimeout(() => { open = false; }, 150);
  }

  function pick(item) {
    value = label(item);
    open = false;
    dispatch("input");
    dispatch("pick", item);
  }

  function onKeydown(e) {
    if (!open || filtered.length === 0) return;
    if (e.key === "ArrowDown") {
      e.preventDefault();
      highlightIndex = (highlightIndex + 1) % filtered.length;
    } else if (e.key === "ArrowUp") {
      e.preventDefault();
      highlightIndex = highlightIndex <= 0 ? filtered.length - 1 : highlightIndex - 1;
    } else if (e.key === "Enter" && highlightIndex >= 0) {
      e.preventDefault();
      pick(filtered[highlightIndex]);
    } else if (e.key === "Tab" && highlightIndex >= 0) {
      pick(filtered[highlightIndex]);
    } else if (e.key === "Escape") {
      open = false;
    }
  }
</script>

<div class="autocomplete">
  <!-- svelte-ignore a11y-no-noninteractive-element-interactions -->
  <form autocomplete="off" on:submit|preventDefault on:keydown={onKeydown}>
    <input
      type="search"
      bind:value
      {placeholder}
      on:input={onInput}
      on:focus={onFocus}
      on:blur={onBlur}
      autocomplete="off"
    />
  </form>
  {#if open && filtered.length > 0}
    <ul class="dropdown">
      {#each filtered as item, i}
        <li
          class:highlighted={i === highlightIndex}
          on:mousedown|preventDefault={() => pick(item)}
        >
          {label(item)}
        </li>
      {/each}
    </ul>
  {/if}
</div>

<style>
  .autocomplete {
    position: relative;
  }

  form {
    margin: 0;
    padding: 0;
  }

  input {
    width: 100%;
    background: #5a5c6a;
    border: 1px solid #6e7080;
    color: #f0f0f0;
    padding: 0.35rem 0.5rem;
    font-family: inherit;
    font-size: 0.9rem;
    border-radius: 3px;
    -webkit-appearance: none;
    appearance: none;
  }

  input::-webkit-search-cancel-button,
  input::-webkit-search-decoration {
    display: none;
  }

  input:focus {
    outline: none;
    border-color: #00ff88;
  }

  .dropdown {
    position: absolute;
    top: 100%;
    left: 0;
    right: 0;
    max-height: 200px;
    overflow-y: auto;
    background: #4a4c5a;
    border: 1px solid #6e7080;
    border-top: none;
    border-radius: 0 0 3px 3px;
    margin: 0;
    padding: 0;
    list-style: none;
    z-index: 100;
  }

  li {
    padding: 0.3rem 0.5rem;
    cursor: pointer;
    color: #f0f0f0;
    font-size: 0.85rem;
  }

  li:hover,
  li.highlighted {
    background: #00ff88;
    color: #1a1a2e;
  }
</style>

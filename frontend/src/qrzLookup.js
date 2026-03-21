/**
 * Shared QRZ location lookup with rate limiting.
 *
 * Usage:
 *   const qrz = new QrzLookup(spots, updated => { spots = updated; });
 *   await qrz.enqueue(spots);  // call after each fetch
 *   qrz.destroy();             // call in onDestroy
 */
export class QrzLookup {
  constructor(onUpdate) {
    this._onUpdate = onUpdate; // callback to trigger Svelte reactivity
    this._queue = [];
    this._lookedUp = new Set();
    this._burstUsed = 0;
    this._dripTimer = null;
    this.pending = 0;
    this.skipped = false;
  }

  /**
   * Process a batch of spots: find missing locations, burst up to 20,
   * drip the rest at 1/s. Spots with >=100 missing skip entirely.
   */
  async enqueue(spots) {
    // Stop existing drip
    if (this._dripTimer) {
      clearInterval(this._dripTimer);
      this._dripTimer = null;
    }

    const visibleCalls = new Set(spots.map(s => s.callsign));
    const allMissing = [...new Set(
      spots.filter(s => !s.country).map(s => s.callsign)
    )];
    this.skipped = allMissing.length >= 100;

    if (this.skipped) {
      this._queue = [];
      this.pending = 0;
      return;
    }

    const newCalls = allMissing.filter(c => !this._lookedUp.has(c));
    for (const c of newCalls) this._lookedUp.add(c);

    const burstAvail = Math.max(0, 20 - this._burstUsed);
    const burstCalls = newCalls.slice(0, burstAvail);
    const dripCalls = newCalls.slice(burstAvail);
    this._burstUsed += burstCalls.length;

    // Burst
    if (burstCalls.length > 0) {
      await Promise.all(burstCalls.map(call => this._lookupOne(call, spots)));
      this._onUpdate(spots);
    }

    // Rebuild queue: new drip calls + remaining visible old queue entries
    this._queue = [
      ...dripCalls,
      ...this._queue.filter(c => visibleCalls.has(c) && !this._lookedUp.has(c))
    ];
    this.pending = this._queue.length;

    if (this._queue.length > 0) {
      this._dripTimer = setInterval(async () => {
        if (this._queue.length === 0) {
          clearInterval(this._dripTimer);
          this._dripTimer = null;
          this.pending = 0;
          this._onUpdate(spots);
          return;
        }
        const call = this._queue.shift();
        this.pending = this._queue.length;
        await this._lookupOne(call, spots);
        this._onUpdate(spots);
      }, 1000);
    }
  }

  async _lookupOne(call, spots) {
    try {
      const res = await fetch(`/api/qrz/lookup/${call}`);
      if (res.ok) {
        const data = await res.json();
        for (const s of spots) {
          if (s.callsign === call && data.country) {
            s.country = data.country || "";
            s.country_code = data.country_code || "";
            s.qrz_state = data.state || "";
          }
        }
      }
    } catch {}
  }

  destroy() {
    if (this._dripTimer) {
      clearInterval(this._dripTimer);
      this._dripTimer = null;
    }
  }
}

/** Format frequency in kHz to MHz string. */
export function formatFreq(khz, decimals = 3) {
  if (!khz) return "";
  return (khz / 1000).toFixed(decimals);
}

/** Format location from spot's qrz_state and country fields. */
export function locationStr(spot) {
  if (spot.qrz_state && spot.country) return `${spot.qrz_state}, ${spot.country}`;
  return spot.country || spot.qrz_state || "";
}

/**
 * Calculate great-circle distance in miles between two Maidenhead grid squares.
 * Returns null if either grid is invalid.
 */
export function gridDistanceMi(grid1, grid2) {
  const toLatLon = (g) => {
    if (!g || g.length < 4) return null;
    g = g.toUpperCase();
    let lon = (g.charCodeAt(0) - 65) * 20 - 180 + (g.charCodeAt(2) - 48) * 2;
    let lat = (g.charCodeAt(1) - 65) * 10 - 90 + (g.charCodeAt(3) - 48);
    if (g.length >= 6) {
      lon += (g.charCodeAt(4) - 65) * (2 / 24) + (1 / 24);
      lat += (g.charCodeAt(5) - 65) * (1 / 24) + (0.5 / 24);
    } else {
      lon += 1;
      lat += 0.5;
    }
    return [lat, lon];
  };
  const c1 = toLatLon(grid1), c2 = toLatLon(grid2);
  if (!c1 || !c2) return null;
  const R = Math.PI / 180;
  const lat1 = c1[0] * R, lon1 = c1[1] * R, lat2 = c2[0] * R, lon2 = c2[1] * R;
  const dlat = lat2 - lat1, dlon = lon2 - lon1;
  const a = Math.sin(dlat / 2) ** 2 + Math.cos(lat1) * Math.cos(lat2) * Math.sin(dlon / 2) ** 2;
  return Math.round(2 * 6371 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a)) * 0.621371);
}

/**
 * Format a timestamp as "Xm ago" / "Xh Ym ago".
 * Accepts an ISO string (e.g. "2026-03-21T18:30:00") or a Unix timestamp (seconds).
 */
export function timeAgo(value) {
  if (!value) return "";
  const then = typeof value === "number" ? new Date(value * 1000) : new Date(value + (String(value).endsWith("Z") ? "" : "Z"));
  const mins = Math.floor((Date.now() - then) / 60000);
  if (mins < 1) return "just now";
  if (mins < 60) return `${mins}m ago`;
  const h = Math.floor(mins / 60);
  const m = mins % 60;
  return m > 0 ? `${h}h ${m}m ago` : `${h}h ago`;
}

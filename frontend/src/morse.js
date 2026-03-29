/** Morse code utilities. */

const MORSE = {
  A: ".-",    B: "-...",  C: "-.-.",  D: "-..",   E: ".",
  F: "..-.",  G: "--.",   H: "....",  I: "..",     J: ".---",
  K: "-.-",   L: ".-..",  M: "--",    N: "-.",     O: "---",
  P: ".--.",  Q: "--.-",  R: ".-.",   S: "...",    T: "-",
  U: "..-",   V: "...-",  W: ".--",   X: "-..-",  Y: "-.--",
  Z: "--..",
  "0": "-----", "1": ".----", "2": "..---", "3": "...--", "4": "....-",
  "5": ".....", "6": "-....", "7": "--...", "8": "---..", "9": "----.",
  "/": "-..-.",
};

/**
 * Convert a string to an SVG dashArray encoding its Morse representation.
 * Each unit is `unit` pixels (default 4).  Dash = 3 units, dot = 1 unit,
 * intra-char gap = 1 unit, inter-char gap = 3 units, trailing word gap = 7 units.
 * Returns { dashArray: string, total: number }.
 */
export function textToDashArray(text, unit = 4) {
  if (!text) return { dashArray: "", total: 0 };
  const words = text.toUpperCase().trim().split(/\s+/);
  const parts = [];
  for (let w = 0; w < words.length; w++) {
    if (w > 0) parts.push(7 * unit); // word gap
    const chars = words[w].split("");
    for (let i = 0; i < chars.length; i++) {
      const morse = MORSE[chars[i]];
      if (!morse) continue;
      if (i > 0 && parts.length) parts.push(3 * unit); // inter-char gap
      for (let j = 0; j < morse.length; j++) {
        parts.push(morse[j] === "-" ? 3 * unit : unit);
        if (j < morse.length - 1) parts.push(unit); // intra-char gap
      }
    }
  }
  parts.push(7 * unit); // trailing gap before repeat
  const total = parts.reduce((a, b) => a + b, 0);
  return { dashArray: parts.join(" "), total };
}

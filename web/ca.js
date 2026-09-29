export function parseRule(text) {
  const match = text.trim().toUpperCase().match(/^B([0-8]*)\/S([0-8]*)$/);
  if (!match || new Set(match[1]).size !== match[1].length || new Set(match[2]).size !== match[2].length) {
    throw new Error(`Invalid rule: ${text}`);
  }
  const bits = Array(18).fill(0);
  for (const digit of match[1]) bits[Number(digit)] = 1;
  for (const digit of match[2]) bits[9 + Number(digit)] = 1;
  return bits;
}

export function formatRule(bits) {
  if (bits.length !== 18 || bits.some((value) => value !== 0 && value !== 1)) {
    throw new Error("Rule must contain 18 binary values");
  }
  const births = bits.slice(0, 9).map((on, i) => (on ? i : "")).join("");
  const survival = bits.slice(9).map((on, i) => (on ? i : "")).join("");
  return `B${births}/S${survival}`;
}

export function makeGrid(size, density = 0, random = Math.random) {
  return Uint8Array.from({ length: size * size }, () => (random() < density ? 1 : 0));
}

export function stepGrid(grid, size, bits, noise = 0, random = Math.random, boundary = "wrap") {
  if (boundary !== "wrap" && boundary !== "dead") throw new Error(`Invalid boundary: ${boundary}`);
  const next = new Uint8Array(grid.length);
  for (let row = 0; row < size; row += 1) {
    for (let col = 0; col < size; col += 1) {
      let neighbors = 0;
      for (let dr = -1; dr <= 1; dr += 1) {
        for (let dc = -1; dc <= 1; dc += 1) {
          if (dr || dc) {
            const neighborRow = row + dr;
            const neighborCol = col + dc;
            if (boundary === "dead" && (neighborRow < 0 || neighborRow >= size || neighborCol < 0 || neighborCol >= size)) continue;
            const r = (neighborRow + size) % size;
            const c = (neighborCol + size) % size;
            neighbors += grid[r * size + c];
          }
        }
      }
      const index = row * size + col;
      next[index] = grid[index] ? bits[9 + neighbors] : bits[neighbors];
      if (noise && random() < noise) next[index] ^= 1;
    }
  }
  return next;
}

import assert from "node:assert/strict";
import test from "node:test";
import { formatRule, parseRule, stepGrid } from "../ca.js";

const SIZE = 12;
const index = (row, col) => row * SIZE + col;
const evolve = (grid, times) => {
  let state = grid;
  for (let i = 0; i < times; i += 1) state = stepGrid(state, SIZE, parseRule("B3/S23"));
  return state;
};

test("rule notation round trips", () => {
  assert.equal(formatRule(parseRule("B3/S23")), "B3/S23");
  assert.equal(formatRule(parseRule("B36/S23")), "B36/S23");
});

test("Conway block is stable", () => {
  const grid = new Uint8Array(SIZE * SIZE);
  for (const [r, c] of [[4, 4], [4, 5], [5, 4], [5, 5]]) grid[index(r, c)] = 1;
  assert.deepEqual(evolve(grid, 1), grid);
});

test("Conway blinker has period two", () => {
  const grid = new Uint8Array(SIZE * SIZE);
  for (const col of [4, 5, 6]) grid[index(5, col)] = 1;
  assert.deepEqual(evolve(grid, 2), grid);
});

test("Conway glider translates after four generations", () => {
  const grid = new Uint8Array(SIZE * SIZE);
  for (const [r, c] of [[2, 3], [3, 4], [4, 2], [4, 3], [4, 4]]) grid[index(r, c)] = 1;
  const expected = new Uint8Array(SIZE * SIZE);
  for (const [r, c] of [[3, 4], [4, 5], [5, 3], [5, 4], [5, 5]]) expected[index(r, c)] = 1;
  assert.deepEqual(evolve(grid, 4), expected);
});

test("boundary setting changes edge behavior", () => {
  const size = 5;
  const grid = new Uint8Array(size * size);
  for (const [row, col] of [[0, 0], [0, 4], [4, 0]]) grid[row * size + col] = 1;
  const rule = parseRule("B3/S23");
  const wrapped = stepGrid(grid, size, rule, 0, Math.random, "wrap");
  const deadOutside = stepGrid(grid, size, rule, 0, Math.random, "dead");
  assert.equal(wrapped[4 * size + 4], 1);
  assert.equal(deadOutside[4 * size + 4], 0);
});

// Tests of the pure helpers of the selection tooltip. Run with: node --test tests/selection.test.mjs
import assert from "node:assert/strict"
import test from "node:test"

import { cleanSelection, inAllowedRegion } from "../src/book_rag/selection.js"

const el = (attributes = {}, classes = []) => ({
  getAttribute: (name) => attributes[name] ?? null,
  classList: { contains: (name) => classes.includes(name) },
})

test("a selection is cleaned: whitespace collapsed, trimmed", () => {
  assert.equal(cleanSelection("  the   Time \n Traveller "), "the Time Traveller")
})

test("a selection that is too short or empty is nothing", () => {
  assert.equal(cleanSelection(""), "")
  assert.equal(cleanSelection(null), "")
  assert.equal(cleanSelection("ab"), "")
  assert.equal(cleanSelection("  a "), "")
})

test("a very long selection is cut", () => {
  assert.equal(cleanSelection("x".repeat(1000)).length, 400)
})

test("chat messages and the book reader allow the tooltip", () => {
  assert.ok(inAllowedRegion([el(), el({ "data-testid": "stChatMessage" })]))
  assert.ok(inAllowedRegion([el(), el({}, ["reader"])]))
})

test("other parts of the page do not", () => {
  assert.ok(!inAllowedRegion([el(), el({ "data-testid": "stSidebar" })]))
  assert.ok(!inAllowedRegion([]))
  assert.ok(!inAllowedRegion([{}, null, undefined])) // window, document and text nodes have no attributes
})

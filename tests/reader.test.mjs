// Tests of the pure helpers of the reader. Run with: node --test tests/reader.test.mjs
import assert from "node:assert/strict"
import test from "node:test"

import { initialWindow, segments } from "../src/book_rag/reader.js"

const text = "hello brave new world" // 21 characters

test("a paragraph without highlight is one plain piece", () => {
  assert.deepEqual(segments(text, 100, 0, 0), [{ text, marked: false }])
  assert.deepEqual(segments(text, 100, 500, 600), [{ text, marked: false }]) // the highlight is further down
  assert.deepEqual(segments(text, 100, 0, 100), [{ text, marked: false }]) // it ends right before the paragraph
})

test("a highlight inside a paragraph splits it in three", () => {
  assert.deepEqual(segments(text, 100, 106, 111), [
    { text: "hello ", marked: false },
    { text: "brave", marked: true },
    { text: " new world", marked: false },
  ])
})

test("a highlight that starts before the paragraph marks its beginning", () => {
  assert.deepEqual(segments(text, 100, 50, 105), [
    { text: "hello", marked: true },
    { text: " brave new world", marked: false },
  ])
})

test("a highlight that goes on after the paragraph marks its end", () => {
  assert.deepEqual(segments(text, 100, 116, 900), [
    { text: "hello brave new ", marked: false },
    { text: "world", marked: true },
  ])
})

test("a paragraph inside the highlight is marked completely", () => {
  assert.deepEqual(segments(text, 100, 0, 900), [{ text, marked: true }])
})

test("the pieces always add up to the paragraph", () => {
  for (const [hs, he] of [[0, 0], [101, 103], [90, 110], [110, 130], [100, 121], [121, 130]]) {
    assert.equal(segments(text, 100, hs, he).map((piece) => piece.text).join(""), text)
  }
})

test("the first window is centred on the passage and stays inside the book", () => {
  assert.deepEqual(initialWindow(1000, 500), { first: 475, last: 525 })
  assert.deepEqual(initialWindow(1000, 3), { first: 0, last: 28 })
  assert.deepEqual(initialWindow(40, 39), { first: 14, last: 39 })
  assert.deepEqual(initialWindow(1, 0), { first: 0, last: 0 })
})

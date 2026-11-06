// The book reader: shows the paragraphs of a book around a passage and loads more above and below while the
// reader scrolls. All paragraphs arrive once in `data`; only a window of them is in the page at any time.

const BATCH = 25; // paragraphs added per load
const MARGIN = 800; // pixels from an edge at which the next batch is loaded
const MAX_RENDERED = 250; // paragraphs kept in the page; the far end is dropped when the window grows

// Split a paragraph into plain and highlighted pieces. `hs` and `he` are the highlight in the whole book,
// `paragraphStart` is the position of the paragraph in the whole book.
export function segments(text, paragraphStart, hs, he) {
  const from = Math.max(hs, paragraphStart)
  const to = Math.min(he, paragraphStart + text.length)
  if (!(hs < he) || from >= to) return [{ text, marked: false }]
  const pieces = []
  if (from > paragraphStart) pieces.push({ text: text.slice(0, from - paragraphStart), marked: false })
  pieces.push({ text: text.slice(from - paragraphStart, to - paragraphStart), marked: true })
  if (to < paragraphStart + text.length) pieces.push({ text: text.slice(to - paragraphStart), marked: false })
  return pieces
}

// The paragraphs [first, last] to show when the book opens at paragraph `focus`.
export function initialWindow(count, focus) {
  return { first: Math.max(0, focus - BATCH), last: Math.min(count - 1, focus + BATCH) }
}

const instances = new WeakMap()

export default function (component) {
  const { data, parentElement } = component
  const root = parentElement.querySelector(".reader")
  const body = root.querySelector(".body")
  const topEdge = root.querySelector(".edge.top")
  const bottomEdge = root.querySelector(".edge.bottom")

  // The script runs again when the theme changes: keep the text and the scroll position if nothing else did.
  const previous = instances.get(parentElement)
  if (previous && previous.id === data.id) return
  instances.set(parentElement, { id: data.id })

  root.style.height = `min(${data.height}px, calc(100vh - 17rem))` // the panel scrolls inside this height

  const paragraphs = data.paragraphs
  const [hs, he] = data.highlight || [0, 0]
  const starts = []
  let position = 0
  for (const p of paragraphs) {
    starts.push(position)
    position += p.length + 2 // paragraphs are separated by a blank line
  }

  let { first, last } = initialWindow(paragraphs.length, data.focus)

  function paragraphElement(i) {
    const el = body.ownerDocument.createElement("p")
    el.dataset.i = String(i)
    for (const piece of segments(paragraphs[i], starts[i], hs, he)) {
      if (piece.marked) {
        const mark = el.ownerDocument.createElement("mark")
        mark.textContent = piece.text
        el.appendChild(mark)
      } else {
        el.appendChild(el.ownerDocument.createTextNode(piece.text))
      }
    }
    return el
  }

  function updateEdges() {
    topEdge.textContent = first === 0 ? "Start of the book" : ""
    bottomEdge.textContent = last === paragraphs.length - 1 ? "End of the book" : ""
  }

  function appendBatch() {
    const to = Math.min(paragraphs.length - 1, last + BATCH)
    for (let i = last + 1; i <= to; i++) body.appendChild(paragraphElement(i))
    last = to
    // Drop paragraphs at the top when too many are in the page; the text the reader sees must not move.
    // The height to remove and the scroll position are read before anything is removed: once the page gets
    // shorter, the browser may already have moved `scrollTop` to the new maximum.
    while (last - first + 1 > MAX_RENDERED) {
      const top = root.scrollTop
      const removed = body.children[BATCH].offsetTop - body.children[0].offsetTop
      for (let k = 0; k < BATCH; k++) body.firstChild.remove()
      first += BATCH
      root.scrollTop = top - removed
    }
    updateEdges()
  }

  function prependBatch() {
    const from = Math.max(0, first - BATCH)
    const top = root.scrollTop
    const before = root.scrollHeight
    const anchor = body.firstChild
    for (let i = from; i < first; i++) body.insertBefore(paragraphElement(i), anchor)
    first = from
    root.scrollTop = top + (root.scrollHeight - before) // keep the text the reader is looking at where it is
    while (last - first + 1 > MAX_RENDERED) {
      for (let k = 0; k < BATCH; k++) body.lastChild.remove()
      last -= BATCH
    }
    updateEdges()
  }

  function fill() {
    for (let guard = 0; guard < 50; guard++) {
      if (first > 0 && root.scrollTop < MARGIN) prependBatch()
      else if (last < paragraphs.length - 1 && root.scrollHeight - root.scrollTop - root.clientHeight < MARGIN) appendBatch()
      else break
    }
  }

  body.replaceChildren()
  for (let i = first; i <= last; i++) body.appendChild(paragraphElement(i))
  updateEdges()

  // Open at the passage: a quarter of the height from the top, so some text before it is visible.
  const target = body.querySelector(`p[data-i="${data.focus}"]`)
  root.scrollTop = target && he > hs ? Math.max(0, target.offsetTop - root.clientHeight / 4) : 0
  root.onscroll = fill // assigned, not added: this function can run again
  fill()
}

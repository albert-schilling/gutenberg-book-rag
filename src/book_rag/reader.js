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

// Pages are virtual: `pageChars` characters of the cleaned text each, counted from the start of the book.
export function pageOf(offset, pageChars, pageCount) {
  return Math.min(pageCount, Math.max(1, Math.floor(offset / pageChars) + 1))
}

// The index of the last paragraph that starts at or before `offset` (`starts` is sorted).
export function paragraphIndexAt(starts, offset) {
  let lo = 0
  let hi = starts.length - 1
  while (lo < hi) {
    const mid = (lo + hi + 1) >> 1
    if (starts[mid] <= offset) lo = mid
    else hi = mid - 1
  }
  return lo
}

// The first paragraph that starts on the given page (or the first one after it, if a long paragraph covers the page).
export function firstParagraphOnPage(starts, page, pageChars) {
  const offset = (page - 1) * pageChars
  const index = paragraphIndexAt(starts, offset)
  return starts[index] < offset && index < starts.length - 1 ? index + 1 : index
}

const instances = new WeakMap()

export default function (component) {
  const { data, parentElement } = component
  const win = parentElement.ownerDocument.defaultView
  const shell = parentElement.querySelector(".shell")
  const root = shell.querySelector(".reader")
  const pageInput = shell.querySelector(".pager .page")
  const pagesLabel = shell.querySelector(".pager .pages")
  const prevButton = shell.querySelector(".pager .prev")
  const nextButton = shell.querySelector(".pager .next")
  const progress = shell.querySelector(".progress")
  const progressFill = shell.querySelector(".progress .fill")
  const body = root.querySelector(".body")
  const topEdge = root.querySelector(".edge.top")
  const bottomEdge = root.querySelector(".edge.bottom")

  // The script runs again when the theme changes: keep the text and the scroll position if nothing else did.
  const previous = instances.get(parentElement)
  if (previous && previous.id === data.id) return
  previous?.observer?.disconnect() // a passage that was waiting for its panel to get a size is replaced
  instances.set(parentElement, { id: data.id })

  // the text scrolls inside this height; "stretch": the whole space that the panel has
  shell.style.height = data.height === "stretch" ? "100%" : `min(${data.height}px, calc(100vh - 17rem))`

  const paragraphs = data.paragraphs
  const [hs, he] = data.highlight || [0, 0]
  const starts = []
  let position = 0
  for (const p of paragraphs) {
    starts.push(position)
    position += p.length + 2 // paragraphs are separated by a blank line
  }

  const total = starts[starts.length - 1] + paragraphs[paragraphs.length - 1].length
  const pageChars = data.pageChars
  const pageCount = Math.max(1, Math.ceil(total / pageChars))
  pagesLabel.textContent = String(pageCount)

  let first = 0
  let last = 0

  function paragraphElement(i) {
    const el = body.ownerDocument.createElement("p")
    el.dataset.i = String(i)
    if (i === 0 || pageOf(starts[i], pageChars, pageCount) !== pageOf(starts[i - 1], pageChars, pageCount)) {
      el.dataset.page = String(pageOf(starts[i], pageChars, pageCount)) // shown above the paragraph by the style
    }
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

  // The reading line is a quarter of the height from the top: the text there decides the page that is shown.
  function readingOffset() {
    const line = root.scrollTop + root.clientHeight / 4
    const children = body.children
    let lo = 0
    let hi = children.length - 1
    while (lo < hi) {
      const mid = (lo + hi + 1) >> 1
      if (children[mid].offsetTop <= line) lo = mid
      else hi = mid - 1
    }
    const el = children[lo]
    const i = Number(el.dataset.i)
    const fraction = Math.min(1, Math.max(0, (line - el.offsetTop) / Math.max(1, el.offsetHeight)))
    return starts[i] + fraction * paragraphs[i].length
  }

  let frame = 0
  function updateIndicator() {
    frame = 0
    const offset = readingOffset()
    if (shell.getRootNode().activeElement !== pageInput) pageInput.value = String(pageOf(offset, pageChars, pageCount))
    const percent = Math.min(100, (offset / total) * 100)
    progressFill.style.width = `${percent}%`
    progress.setAttribute("aria-valuenow", String(Math.round(percent)))
  }

  // Show the text around paragraph `index`, with the paragraph a quarter of the height from the top.
  function openAt(index) {
    ;({ first, last } = initialWindow(paragraphs.length, index))
    body.replaceChildren()
    for (let i = first; i <= last; i++) body.appendChild(paragraphElement(i))
    updateEdges()
    const target = body.querySelector(`p[data-i="${index}"]`)
    root.scrollTop = target && index > 0 ? Math.max(0, target.offsetTop - root.clientHeight / 4) : 0
    fill()
    updateIndicator()
  }

  root.onscroll = () => {
    // assigned, not added: this function can run again
    fill()
    if (!frame) frame = win.requestAnimationFrame(updateIndicator)
  }
  function goToPage(page) {
    page = Math.min(pageCount, Math.max(1, page || 1))
    pageInput.blur() // so that the indicator may write the page again
    openAt(firstParagraphOnPage(starts, page, pageChars))
  }
  const shownPage = () => parseInt(pageInput.value, 10) || 1
  pageInput.onchange = () => goToPage(parseInt(pageInput.value, 10))
  pageInput.onkeydown = (event) => {
    if (event.key === "Enter") goToPage(parseInt(pageInput.value, 10))
  }
  prevButton.onclick = () => goToPage(shownPage() - 1)
  nextButton.onclick = () => goToPage(shownPage() + 1)

  // The panel may not have its final size when the script runs (a fixed panel is laid out after it): the text is opened
  // once its size has been the same for a moment. With no height, "load more above and below" would run against an empty box.
  const state = instances.get(parentElement) // set above, with the id
  let timer = 0
  let lastHeight = -1
  state.observer = new ResizeObserver(() => {
    if (root.clientHeight === lastHeight) return
    lastHeight = root.clientHeight
    win.clearTimeout(timer)
    if (lastHeight > 0) {
      timer = win.setTimeout(() => {
        state.observer.disconnect()
        openAt(data.focus)
      }, 120)
    }
  })
  state.observer.observe(root)
}

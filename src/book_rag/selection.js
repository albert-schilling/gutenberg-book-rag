// A tooltip "Ask about this" for text that the reader selects in a chat message or in the book.
// Streamlit has no selection events, so this runs in the page: it listens for the end of a selection
// (mouse or keyboard), shows the tooltip next to the pointer and sends the text to Python when it is clicked.

const TIP_ID = "book-rag-ask-tip"
const MIN_LENGTH = 3
const MAX_LENGTH = 400
const SETTLE_MS = 600 // scrolls right after a selection (the browser scrolling it into view) do not hide the tooltip

export function cleanSelection(raw) {
  const text = (raw || "").replace(/\s+/g, " ").trim()
  return text.length >= MIN_LENGTH ? text.slice(0, MAX_LENGTH) : ""
}

// `path` is event.composedPath(): it also lists the elements inside the shadow root of the book reader.
export function inAllowedRegion(path) {
  return path.some(
    (el) =>
      el &&
      el.getAttribute &&
      (el.getAttribute("data-testid") === "stChatMessage" || (el.classList && el.classList.contains("reader"))),
  )
}

const instances = new WeakMap()

export default function (component) {
  const { parentElement, setTriggerValue } = component
  const doc = parentElement.ownerDocument
  const win = doc.defaultView

  instances.get(parentElement)?.() // this script can run again: remove the listeners of the previous run first

  const tip = doc.createElement("div")
  tip.id = TIP_ID
  tip.setAttribute("role", "toolbar")
  tip.setAttribute("aria-label", "Ask about the selected text")
  tip.style.cssText =
    "position:fixed;display:none;z-index:100000;background:#262730;color:#fff;border-radius:8px;" +
    "box-shadow:0 2px 10px rgba(0,0,0,.35);font:14px/1.2 system-ui,sans-serif;padding:4px"
  const button = doc.createElement("button")
  button.type = "button"
  button.textContent = "Ask about this"
  button.style.cssText = "all:unset;cursor:pointer;padding:6px 10px;border-radius:6px"
  button.onmouseenter = () => (button.style.background = "#3d3f4b")
  button.onmouseleave = () => (button.style.background = "transparent")
  tip.appendChild(button)
  doc.body.appendChild(tip)

  let current = ""
  let shownAt = 0
  const hide = () => {
    tip.style.display = "none"
    current = ""
  }
  // The tooltip stays where it is, so a scroll that moves the text makes it stale: hide it, but not while the page settles.
  const onScroll = () => {
    if (Date.now() - shownAt > SETTLE_MS) hide()
  }

  function show(text, x, y) {
    current = text
    shownAt = Date.now()
    tip.style.display = "block"
    const width = tip.offsetWidth
    tip.style.left = `${Math.min(Math.max(8, x - width / 2), win.innerWidth - width - 8)}px`
    tip.style.top = `${Math.max(8, y - 52)}px`
  }

  const onSelectionEnd = (event) => {
    if (tip.contains(event.target)) return
    const path = event.composedPath()
    const rect = event.target.getBoundingClientRect ? event.target.getBoundingClientRect() : null
    const x = event.clientX ?? (rect ? rect.left + rect.width / 2 : 100)
    const y = event.clientY ?? (rect ? rect.top : 100)
    win.setTimeout(() => {
      // after a tick, so that the browser has finished the selection
      const text = cleanSelection(doc.getSelection()?.toString())
      if (text && inAllowedRegion(path)) show(text, x, y)
      else hide()
    }, 0)
  }
  const onPress = (event) => {
    if (!tip.contains(event.target)) hide()
  }
  const onKey = (event) => {
    if (event.key === "Escape") hide()
    else if (event.shiftKey || event.key === "Shift") onSelectionEnd(event)
  }
  button.onclick = () => {
    const text = current
    hide()
    if (text) setTriggerValue("ask", text)
  }

  doc.addEventListener("mouseup", onSelectionEnd)
  doc.addEventListener("keyup", onKey)
  doc.addEventListener("mousedown", onPress)
  doc.addEventListener("scroll", onScroll, true)

  const dispose = () => {
    doc.removeEventListener("mouseup", onSelectionEnd)
    doc.removeEventListener("keyup", onKey)
    doc.removeEventListener("mousedown", onPress)
    doc.removeEventListener("scroll", onScroll, true)
    tip.remove()
  }
  instances.set(parentElement, dispose)
  return dispose
}

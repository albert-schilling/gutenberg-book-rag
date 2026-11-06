"""Helpers for the browser tests of the book reader."""


def window(page) -> tuple[int, int, int]:
    """(index of the first paragraph in the page, of the last, how many)."""
    paragraphs = page.locator(".reader p")
    return (
        int(paragraphs.first.get_attribute("data-i")),
        int(paragraphs.last.get_attribute("data-i")),
        paragraphs.count(),
    )


def anchor(page):
    """The paragraph in the middle of the reader and how far it is from the top of the reader."""
    return page.locator(".reader").evaluate(
        """root => { const r = root.getBoundingClientRect(); const mid = r.top + r.height / 2
        for (const p of root.querySelectorAll('p')) { const b = p.getBoundingClientRect()
            if (b.bottom >= mid) return [Number(p.dataset.i), b.top - r.top] } return null }"""
    )


def distance_from_top(page, index):
    return page.locator(".reader").evaluate(
        """(root, i) => { const p = root.querySelector(`p[data-i="${i}"]`)
        return p ? p.getBoundingClientRect().top - root.getBoundingClientRect().top : null }""",
        index,
    )


def scroll_and_measure_drift(page, step, count):
    """Scroll in small steps. Returns the largest difference between where the text should be and where it is."""
    worst = 0.0
    for _ in range(count):
        found = anchor(page)
        page.locator(".reader").evaluate("(root, d) => { root.scrollTop += d }", step)
        page.wait_for_timeout(60)
        if found is None or page.locator(".edge.bottom").inner_text():  # the end of the book: nothing can move
            continue
        after = distance_from_top(page, found[0])
        if after is not None:
            worst = max(worst, abs((after - found[1]) + step))
    return worst

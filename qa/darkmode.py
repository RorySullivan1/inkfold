"""
A model of Outlook.com and new Outlook's dark mode, and the contrast of prose under it (v0.9.0).

Those clients recolour each element whose own background is light (to a dark one, tagging it
``data-ogsb``) and whose own text is dark (to a light one, tagging it ``data-ogsc``), and the
email's ``<style>`` still applies on top. The model does the same in a browser page, so a
gallery email can be measured without the client. It is a model: the owner's check in the
client is the verdict (``qa/clients/MATRIX.md``). Needs the ``[qa]`` extra and a Chromium.
"""

from __future__ import annotations

from typing import Any

#: Colour arithmetic both scripts share: hex and rgb() parsing, WCAG luminance and contrast.
_COLOUR_JS = r"""
  const hex = s => { const m = /#([0-9a-f]{6})/i.exec(s || ""); return m ? m[1] : null; };
  const fromHex = h => [0, 2, 4].map(i => parseInt(h.slice(i, i + 2), 16) / 255);
  const fromCss = s => {
    const m = s.match(/rgba?\(([^)]+)\)/);
    if (!m) return null;
    const p = m[1].split(",").map(Number);
    return {c: p.slice(0, 3).map(v => v / 255), a: p.length > 3 ? p[3] : 1};
  };
  const lum = c => {
    const l = c.map(v => (v <= 0.03928 ? v / 12.92 : ((v + 0.055) / 1.055) ** 2.4));
    return 0.2126 * l[0] + 0.7152 * l[1] + 0.0722 * l[2];
  };
  const ratio = (a, b) => {
    const [x, y] = [lum(a), lum(b)].sort((p, q) => q - p);
    return (x + 0.05) / (y + 0.05);
  };
"""

#: The recolouring, run in the page. Light grounds land near #1f1f1f and dark inks near #e8e8e8,
#: each keeping a little of its hue; a mid-tone ground or ink is left as it is. The message
#: root's default text turns light.
OUTLOOK_DARK_JS = (
    "() => {"
    + _COLOUR_JS
    + r"""
  const toHex = a => "#" + a
    .map(v => Math.round(Math.max(0, Math.min(1, v)) * 255).toString(16).padStart(2, "0"))
    .join("");
  const flip = (h, target) => {
    const c = fromHex(h);
    const mid = (Math.max(...c) + Math.min(...c)) / 2;
    const k = target / Math.max(mid, 0.01);
    return toHex(c.map(v => (v - mid) * 0.35 + mid * k));
  };
  const BG = /background(?:-color)?\s*:\s*([^;]+)/i;
  const INK = /(?:^|;)\s*color\s*:\s*([^;]+)/i;
  for (const el of document.body.querySelectorAll("*")) {
    const style = el.getAttribute("style") || "";
    const bg = hex((BG.exec(style) || [])[1]) || hex(el.getAttribute("bgcolor"));
    if (bg && lum(fromHex(bg)) > 0.4) {
      const dark = flip(bg, 0.13);
      el.setAttribute("data-ogsb", "#" + bg);
      el.style.setProperty("background-color", dark);
      if (el.hasAttribute("bgcolor")) el.setAttribute("bgcolor", dark);
    }
    const ink = hex((INK.exec(style) || [])[1]);
    if (ink && lum(fromHex(ink)) < 0.4) {
      el.setAttribute("data-ogsc", "#" + ink);
      el.style.setProperty("color", flip(ink, 0.88));
    }
  }
  document.body.setAttribute("data-ogsc", "");
  document.body.style.color = "#e8e8e8";
}
"""
)

#: Every run of prose (inside ``.body-text``): its contrast against the first opaque ground
#: behind it, and whether the model recoloured that ground (``recoloured``). Prose over a
#: background image is skipped, having no one colour behind it.
PROSE_CONTRAST_JS = (
    "() => {"
    + _COLOUR_JS
    + r"""
  const ground = el => {
    for (let n = el; n && n.nodeType === 1; n = n.parentElement) {
      const cs = getComputedStyle(n);
      if (cs.backgroundImage && cs.backgroundImage !== "none") return null;
      const bg = fromCss(cs.backgroundColor);
      if (bg && bg.a > 0.5) return {c: bg.c, recoloured: n.hasAttribute("data-ogsb")};
    }
    return {c: [1, 1, 1], recoloured: false};
  };
  const runs = [];
  for (const el of document.querySelectorAll(".body-text, .body-text *")) {
    const own = [...el.childNodes]
      .filter(n => n.nodeType === 3 && n.textContent.trim())
      .map(n => n.textContent.trim())
      .join(" ");
    if (!own) continue;
    const g = ground(el);
    const ink = fromCss(getComputedStyle(el).color);
    if (!g || !ink) continue;
    runs.push({
      text: own.slice(0, 60),
      ratio: Math.round(ratio(ink.c, g.c) * 100) / 100,
      recoloured: g.recoloured,
    });
  }
  return runs;
}
"""
)


def prose_contrast(browser: Any, html: str, *, dark: bool = True) -> list[dict[str, Any]]:
    """
    Each prose run in ``html`` with its contrast ratio, under the dark-mode model unless ``dark``
    is false. Requests leaving the page are refused, as the screenshot runner refuses them.
    """
    page = browser.new_page(viewport={"width": 1000, "height": 900})
    try:
        page.route(
            "**/*", lambda r: r.abort() if r.request.url.startswith("http") else r.continue_()
        )
        page.set_content(html)
        if dark:
            page.evaluate(OUTLOOK_DARK_JS)
        runs: list[dict[str, Any]] = page.evaluate(PROSE_CONTRAST_JS)
        return runs
    finally:
        page.close()


__all__ = ["OUTLOOK_DARK_JS", "PROSE_CONTRAST_JS", "prose_contrast"]

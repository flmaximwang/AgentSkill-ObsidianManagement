#!/usr/bin/env python3
"""Capture the print-time DOM / computed styles / PDF of an Electron app (Obsidian) over CDP.

Companion to references/print-and-pdf-pipeline.md and references/electron-cdp-inspection.md.
An end-to-end verified copy, with an extra HTML structural-diff subcommand, lives at
~/Repositories/Obsidian-Workbench-CSS/tools/print-harness/cdp.py.

  python3 cdp.py targets
  python3 cdp.py --target app     dump --out captures --media print
  python3 cdp.py --target webview dump --out captures          # a plugin's print document
  python3 cdp.py --target app     styles --media print
  python3 cdp.py --target app     pdf --out out.pdf --pagesize A4 --background
  python3 cdp.py png out.pdf --dpi 110
  python3 cdp.py pxdiff a.png b.png --out diff.png

Requires websocket-client; png/pxdiff additionally need poppler and imagemagick.
"""
from __future__ import annotations

import argparse
import base64
import json
import os
import shutil
import subprocess
import sys
import time
import urllib.error
import urllib.request

try:
    import websocket  # websocket-client
except ImportError:  # pragma: no cover
    sys.exit("missing dependency: pip install websocket-client")

DEFAULT_PORT = 9222


def list_targets(port: int) -> list:
    url = "http://127.0.0.1:%d/json/list" % port
    try:
        with urllib.request.urlopen(url, timeout=5) as r:
            return json.load(r)
    except urllib.error.URLError as e:
        sys.exit("cannot reach %s: %s\n-> the app must be launched with "
                 "--remote-debugging-port=%d" % (url, e, port))


class CDP:
    def __init__(self, ws_url: str, timeout: float = 30.0):
        self.ws = websocket.create_connection(ws_url, timeout=timeout,
                                              max_size=512 * 1024 * 1024)
        self._id = 0

    def call(self, method: str, **params):
        self._id += 1
        mid = self._id
        self.ws.send(json.dumps({"id": mid, "method": method, "params": params}))
        deadline = time.time() + 60
        while time.time() < deadline:
            msg = json.loads(self.ws.recv())
            if msg.get("id") == mid:
                if "error" in msg:
                    raise RuntimeError("%s: %s" % (method, msg["error"]))
                return msg.get("result", {})
        raise TimeoutError(method)

    def eval(self, expr: str, await_promise: bool = False):
        r = self.call("Runtime.evaluate", expression=expr, returnByValue=True,
                      awaitPromise=await_promise, userGesture=True)
        if r.get("exceptionDetails"):
            raise RuntimeError("JS exception: %s" % r["exceptionDetails"].get("text"))
        return r["result"].get("value")

    def close(self):
        try:
            self.ws.close()
        except Exception:
            pass


def pick_targets(targets: list, which: str) -> list:
    pages = [t for t in targets
             if t.get("type") in ("page", "webview", "iframe") and t.get("webSocketDebuggerUrl")]
    if which == "all":
        return pages
    if which == "app":  # Obsidian main window: app://obsidian.md/index.html
        return [t for t in pages
                if t.get("url", "").startswith("app://") and "index.html" in t["url"]] or pages[:1]
    if which == "webview":  # a plugin's own document, e.g. better-export-pdf's print preview
        return [t for t in pages
                if t.get("url", "").startswith("app://") and "index.html" not in t["url"]]
    if which == "print":
        return [t for t in pages if t.get("title", "").startswith("print")] or pick_targets(targets, "webview")
    raise ValueError(which)


DEFAULT_SELECTORS = [
    "body", ".print", ".print > .markdown-preview-view", ".markdown-preview-view",
    ".markdown-preview-sizer", ".markdown-preview-view > div", "table", ".callout",
]

STYLE_PROPS = """(cs) => ({
  width: cs.width, maxWidth: cs.maxWidth, minWidth: cs.minWidth,
  margin: cs.margin, padding: cs.padding, display: cs.display,
  fontSize: cs.fontSize, lineHeight: cs.lineHeight, color: cs.color,
  breakInside: cs.breakInside, pageBreakAfter: cs.pageBreakAfter,
  printZoom: cs.getPropertyValue('--print-zoom'),
  printPageWidth: cs.getPropertyValue('--print-page-width')
})"""


def cmd_targets(args):
    for t in list_targets(args.port):
        print("%-14s %-42s %s" % (t.get("type", ""), (t.get("title") or "")[:40],
                                  (t.get("url") or "")[:90]))
        print("               ws: %s" % t.get("webSocketDebuggerUrl", ""))


def cmd_dump(args):
    os.makedirs(args.out, exist_ok=True)
    targets = pick_targets(list_targets(args.port), args.target)
    if not targets:
        sys.exit("no matching debug target")
    for t in targets:
        name = "".join(c if (c.isalnum() or c in "_.-") else "_" for c in
                       (t.get("title") or t.get("url") or t["id"]))[:80]
        if args.media:
            name += "." + args.media + "media"
        c = CDP(t["webSocketDebuggerUrl"])
        try:
            if args.media:  # per-session override: capture in the SAME connection
                c.call("Emulation.setEmulatedMedia", media=args.media)
            html = c.eval("document.documentElement.outerHTML")
            path = os.path.join(args.out, name + ".html")
            with open(path, "w", encoding="utf-8") as f:
                f.write(html)
            print("[html] %s (%d chars) <- %s" % (path, len(html), t.get("url")))
            meta = c.eval('JSON.stringify({body:document.body.className,'
                          'print:!!document.querySelector(".print"),'
                          'media_print:matchMedia("print").matches})')
            print("[meta] %s" % meta)
            try:
                snap = c.call("Page.captureSnapshot", format="mhtml")
                with open(os.path.join(args.out, name + ".mhtml"), "w", encoding="utf-8") as f:
                    f.write(snap.get("data", ""))
                print("[mhtml] %s" % os.path.join(args.out, name + ".mhtml"))
            except Exception as e:  # noqa: BLE001
                print("[mhtml] skipped: %s" % e)
        finally:
            c.close()


def cmd_media(args):
    for t in pick_targets(list_targets(args.port), args.target):
        c = CDP(t["webSocketDebuggerUrl"])
        try:
            c.call("Emulation.setEmulatedMedia", media=args.media)
            print("media=%s  matchMedia('print')=%s  <- %s"
                  % (args.media, c.eval('matchMedia("print").matches'), t.get("url")))
        finally:
            c.close()


def cmd_pdf(args):
    targets = pick_targets(list_targets(args.port), args.target)
    t = targets[0]
    c = CDP(t["webSocketDebuggerUrl"])
    try:
        c.call("Emulation.setEmulatedMedia", media="print")
        opts = dict(printBackground=args.background, landscape=args.landscape,
                    scale=args.scale / 100.0, preferCSSPageSize=args.css_page_size,
                    transferMode="ReturnAsBase64")
        if args.pagesize:
            w, h = {"A4": (8.27, 11.69), "A3": (11.69, 16.54), "Letter": (8.5, 11.0)}[args.pagesize]
            opts["paperWidth"], opts["paperHeight"] = w, h
        r = c.call("Page.printToPDF", **opts)
        with open(args.out, "wb") as f:
            f.write(base64.b64decode(r["data"]))
        print("[pdf] %s (%d bytes) <- %s" % (args.out, os.path.getsize(args.out), t.get("url")))
    finally:
        c.close()


def cmd_styles(args):
    sels = DEFAULT_SELECTORS
    if args.selectors:
        with open(args.selectors, encoding="utf-8") as f:
            sels = json.load(f)
    expr = ('(() => { const sels = %s; const props = %s; const out = {};'
            ' for (const s of sels) { const el = document.querySelector(s);'
            ' if (!el) { out[s] = null; continue; } const cs = getComputedStyle(el);'
            ' const b = el.getBoundingClientRect(); out[s] = Object.assign(props(cs),'
            ' {rect: [Math.round(b.width), Math.round(b.height)]}); }'
            ' return JSON.stringify(out, null, 2); })()') % (json.dumps(sels), STYLE_PROPS)
    for t in pick_targets(list_targets(args.port), args.target):
        c = CDP(t["webSocketDebuggerUrl"])
        try:
            if args.media:
                c.call("Emulation.setEmulatedMedia", media=args.media)
            res = json.loads(c.eval(expr))
            print("# %s  media_print=%s  (emulated=%s)"
                  % (t.get("url"), c.eval('matchMedia("print").matches'), args.media or "none"))
            for k, v in res.items():
                print("  %s: %s" % (k, json.dumps(v, ensure_ascii=False)))
            if args.out:
                os.makedirs(args.out, exist_ok=True)
                with open(os.path.join(args.out, "styles.json"), "w", encoding="utf-8") as f:
                    json.dump(res, f, ensure_ascii=False, indent=2)
        finally:
            c.close()


def cmd_png(args):
    outdir = args.outdir or os.path.splitext(args.pdf)[0] + ".pages"
    os.makedirs(outdir, exist_ok=True)
    exe = shutil.which("pdftoppm") or "pdftoppm"
    subprocess.run([exe, "-png", "-r", str(args.dpi), args.pdf,
                    os.path.join(outdir, "page")], check=True)
    for f in sorted(os.listdir(outdir)):
        print(os.path.join(outdir, f))
    subprocess.run([shutil.which("pdfinfo") or "pdfinfo", args.pdf], check=False)


def cmd_pxdiff(args):
    if not shutil.which("magick"):
        sys.exit("imagemagick (magick) required")
    r = subprocess.run(["magick", "compare", "-metric", "RMSE", args.a, args.b, args.out],
                       capture_output=True, text=True)
    print("RMSE: %s" % r.stderr.strip())
    print("diff image: %s" % args.out)


def build_parser():
    p = argparse.ArgumentParser(
        description="Capture print-time HTML/PDF of an Electron app over CDP",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    p.add_argument("--port", type=int, default=DEFAULT_PORT, help="remote debugging port")
    p.add_argument("--target", default="app", choices=["app", "webview", "print", "all"],
                   help="which debug target to act on")
    sub = p.add_subparsers(dest="cmd", required=True)
    sub.add_parser("targets", help="list debug targets").set_defaults(func=cmd_targets)

    d = sub.add_parser("dump", help="save outerHTML + MHTML snapshot")
    d.add_argument("--out", default="captures")
    d.add_argument("--media", choices=["print", "screen"],
                   help="emulate this media for the capture (same connection)")
    d.set_defaults(func=cmd_dump)

    m = sub.add_parser("media", help="show media emulation state")
    m.add_argument("media", choices=["print", "screen"])
    m.set_defaults(func=cmd_media)

    q = sub.add_parser("pdf", help="export a PDF with print media")
    q.add_argument("--out", default="out.pdf")
    q.add_argument("--pagesize", default="A4", choices=["A4", "A3", "Letter"])
    q.add_argument("--scale", type=int, default=100, help="percent")
    q.add_argument("--background", action="store_true", help="print backgrounds")
    q.add_argument("--landscape", action="store_true")
    q.add_argument("--css-page-size", action="store_true")
    q.set_defaults(func=cmd_pdf)

    s = sub.add_parser("styles", help="computed styles of key selectors")
    s.add_argument("--selectors", help="JSON file holding an array of selectors")
    s.add_argument("--out", help="directory for the JSON result")
    s.add_argument("--media", choices=["print", "screen"])
    s.set_defaults(func=cmd_styles)

    pn = sub.add_parser("png", help="PDF -> one PNG per page")
    pn.add_argument("pdf")
    pn.add_argument("--dpi", type=int, default=110)
    pn.add_argument("--outdir")
    pn.set_defaults(func=cmd_png)

    px = sub.add_parser("pxdiff", help="pixel diff of two images")
    px.add_argument("a")
    px.add_argument("b")
    px.add_argument("--out", default="pxdiff.png")
    px.set_defaults(func=cmd_pxdiff)
    return p


if __name__ == "__main__":
    a = build_parser().parse_args()
    a.func(a)

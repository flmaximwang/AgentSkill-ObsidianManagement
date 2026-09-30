# Inspecting an Electron app from outside (CDP recipes)

For Obsidian, and for any Chromium/Electron app whose DOM, computed styles or print output must be
verified rather than guessed. Verified against Chrome 153 (same engine family).

## 1. Get a debug port

The flag only takes effect **at launch**, so the app must be fully quit first. On macOS use
`open -na ... --args ...` to pass it:

```bash
osascript -e 'quit app "Obsidian"'
open -na /Applications/Obsidian.app --args --remote-debugging-port=9222
```

Acceptance check — poll instead of sleeping blindly; the port binds several seconds after launch:

```bash
for i in $(seq 1 20); do curl -s --max-time 2 http://127.0.0.1:9222/json/version && break; sleep 1; done
```

Expect JSON containing `"webSocketDebuggerUrl": "ws://127.0.0.1:9222/devtools/browser/..."`.
No JSON means the flag did not apply — usually because an instance was already running.

## 2. Discover targets

```bash
curl -s http://127.0.0.1:9222/json/list
```

Match on `url` and `type`, never on order. In Obsidian the app page is
`app://obsidian.md/index.html`; a plugin's `<webview>` appears as its own target, which is how a
plugin-authored print document becomes inspectable. Keep only entries that carry a
`webSocketDebuggerUrl`.

## 3. Talk CDP

Plain WebSocket, one method per message, `id` echoed back; `websocket-client` suffices:

```python
ws = websocket.create_connection(ws_url, timeout=30, max_size=512 * 1024 * 1024)
ws.send(json.dumps({"id": mid, "method": method, "params": params}))
```

Useful methods: `Runtime.evaluate` (`returnByValue=True` to get values rather than handles),
`DOM.getDocument` / `DOM.getOuterHTML`, `Page.captureSnapshot` (`format="mhtml"` gives a single
file with CSS and images), `Page.printToPDF`, `Emulation.setEmulatedMedia`,
`Emulation.setDeviceMetricsOverride`.

`Page.printToPDF` options worth knowing: `printBackground` (backgrounds are off by default — the
usual reason coloured callouts vanish), `paperWidth` / `paperHeight` in **inches**, `scale` as a
fraction (not percent), `preferCSSPageSize`, `landscape`, `displayHeaderFooter` plus
`headerTemplate` / `footerTemplate`.

## 4. Read the app's own code instead of speculating

An installed Electron app's code is readable even though it is packed:

```python
import re
data = open('/Applications/Obsidian.app/Contents/Resources/obsidian.asar', 'rb').read()
for m in list(re.finditer(re.escape(b'printToPDF'), data))[:3]:
    print(data[max(0, m.start() - 200):m.start() + 300].decode('utf-8', 'replace'))
```

For CSS blocks, brace-match from `@media print` (count `{` / `}`) rather than regex-capturing to the
first `}` — nested blocks truncate the rule and you misread what the app does. When grepping
minified bundles, match distinctive tokens, not generic words like `print` or `body`.

## Pitfalls

- **`Emulation.setEmulatedMedia` is per-session.** The override dies with the connection, so one
  connection must both set the media and take the capture. A CLI that sets media in one call and
  captures in another silently captures screen media.
- **Quote shell globs in Chromium flags**: an unquoted `--remote-allow-origins=*` is expanded by
  zsh and the launch dies with `no matches found`. Write `"--remote-allow-origins=*"`.
- **An instance that "did not start" is probably still starting.** Check the process output and
  re-run the probe; the `ls listening on ws://...` line appears a few seconds in.
- **`webContents` identity decides the print output.** Obsidian's native export prints the app
  page's own webContents, so a plugin-authored document (its own webview) will not match it
  byte for byte. Always state which pipeline a captured artifact came from.
- **A rendered image is the only way a text-only agent can judge layout.** Convert first
  (`pdftoppm -png -r 110`, or `magick file.pdf[0]`), then compare with
  `magick compare -metric RMSE a.png b.png diff.png`.

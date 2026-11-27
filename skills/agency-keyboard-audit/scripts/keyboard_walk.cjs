#!/usr/bin/env node
// Drive one page in headless Chromium: run axe-core, then walk it with the Tab key.
// Prints one JSON recording for keyboard_audit.py to judge. Exit 0 recorded, 2 bad args,
// 3 adapter missing (playwright or axe-core not resolvable through NODE_PATH).
"use strict";

const fs = require("fs");
const path = require("path");
const url = require("url");

const CLICK_TYPES = new Set(["click", "mousedown", "mouseup", "pointerdown", "pointerup"]);
const SENTINEL = "__kb_end";

function emit(obj, code) {
  process.stdout.write(JSON.stringify(obj, null, 2) + "\n");
  process.exit(code);
}

const args = process.argv.slice(2);
const page = args[0];
const maxIdx = args.indexOf("--max-tabs");
const maxTabs = maxIdx >= 0 ? Number(args[maxIdx + 1]) : 60;
if (!page || !fs.existsSync(page) || !Number.isInteger(maxTabs) || maxTabs < 1) {
  emit({ error: "usage: keyboard_walk.cjs PAGE.html [--max-tabs N>=1]" }, 2);
}

let playwright, axePath, axeVersion, pwVersion;
try {
  playwright = require("playwright");
  pwVersion = require("playwright/package.json").version;
  axePath = require.resolve("axe-core/axe.min.js");
  axeVersion = require("axe-core/package.json").version;
} catch (err) {
  emit({ error: "adapter-missing", detail: String(err.message).split("\n")[0] }, 3);
}

// Runs inside the page: helpers shared by every evaluate call.
function installHelpers() {
  window.__kb = {
    path(el) {
      if (!el || el === document.body) return "body";
      if (el.id) return "#" + el.id;
      const parts = [];
      for (let n = el; n && n.nodeType === 1 && n !== document.body; n = n.parentElement) {
        if (n.id) { parts.unshift("#" + n.id); break; }
        const same = Array.from(n.parentElement.children).filter((c) => c.tagName === n.tagName);
        parts.unshift(n.tagName.toLowerCase() + (same.length > 1 ? ":nth-of-type(" + (same.indexOf(n) + 1) + ")" : ""));
      }
      return parts.join(" > ");
    },
    name(el) {
      const label = el.labels && el.labels[0] ? el.labels[0].textContent : "";
      return (el.getAttribute("aria-label") || label || el.textContent || el.value || "").trim().replace(/\s+/g, " ").slice(0, 60);
    },
    style(el) {
      const s = getComputedStyle(el);
      return [s.outlineStyle, s.outlineWidth, s.outlineColor, s.boxShadow, s.borderTopColor,
        s.borderBottomColor, s.backgroundColor, s.color, s.textDecorationLine].join(" | ");
    },
    focusable(el) {
      return el.tabIndex >= 0 && !el.disabled && el.getClientRects().length > 0 && getComputedStyle(el).visibility !== "hidden";
    },
  };
}

(async () => {
  const browser = await playwright.chromium.launch({ headless: true });
  let result;
  try {
    const context = await browser.newContext();
    const p = await context.newPage();
    await p.goto(url.pathToFileURL(path.resolve(page)).href);
    await p.addScriptTag({ path: axePath });
    await p.evaluate(installHelpers);

    const axe = await p.evaluate(async () => {
      const r = await window.axe.run(document, { resultTypes: ["violations"] });
      return r.violations.map((v) => ({
        id: v.id, impact: v.impact, help: v.help,
        wcag: v.tags.filter((t) => /^wcag\d+$/.test(t)),
        targets: v.nodes.map((n) => {
          const el = document.querySelector(n.target.join(" "));
          return el ? window.__kb.path(el) : n.target.join(" ");
        }),
      }));
    });

    // Elements with their own click-type listeners, read through the Chrome DevTools Protocol.
    const cdp = await context.newCDPSession(p);
    const all = await cdp.send("Runtime.evaluate", { expression: 'Array.from(document.querySelectorAll("body *"))' });
    const props = await cdp.send("Runtime.getProperties", { objectId: all.result.objectId, ownProperties: true });
    const clickIdx = [];
    for (const prop of props.result) {
      if (!/^\d+$/.test(prop.name)) continue;
      const { listeners } = await cdp.send("DOMDebugger.getEventListeners", { objectId: prop.value.objectId });
      if (listeners.some((l) => CLICK_TYPES.has(l.type))) clickIdx.push(Number(prop.name));
    }

    const snapshot = await p.evaluate((clickIdx) => {
      const ROLES = new Set(["button", "link", "switch", "checkbox", "radio", "tab", "menuitem", "option", "slider", "combobox", "textbox"]);
      const els = Array.from(document.querySelectorAll("body *"));
      const interactive = [];
      els.forEach((el, i) => {
        const role = el.getAttribute("role");
        const click = clickIdx.includes(i) || el.hasAttribute("onclick");
        if (!click && !(role && ROLES.has(role))) return;
        interactive.push({ selector: window.__kb.path(el), name: window.__kb.name(el), role, tag: el.tagName.toLowerCase(),
          click_listener: click, focusable: window.__kb.focusable(el), tabindex: el.getAttribute("tabindex") });
      });
      const baseline = {};
      els.filter((el) => window.__kb.focusable(el)).forEach((el) => { baseline[window.__kb.path(el)] = window.__kb.style(el); });
      const positive = els.filter((el) => el.tabIndex > 0).map((el) => window.__kb.path(el));
      return { interactive, baseline, positive };
    }, clickIdx);

    await p.evaluate((id) => {
      const b = document.createElement("button");
      b.id = id; b.textContent = "end of page (audit sentinel)";
      b.style.position = "absolute"; b.style.insetInlineStart = "-9999px";
      document.body.appendChild(b);
    }, SENTINEL);

    async function walk(limit) {
      const seq = [];
      for (let i = 0; i < limit; i++) {
        await p.keyboard.press("Tab");
        const stop = await p.evaluate((id) => {
          const el = document.activeElement;
          return { selector: window.__kb.path(el), name: window.__kb.name(el), tag: el.tagName.toLowerCase(),
            focused_style: window.__kb.style(el), end: el.id === id };
        }, SENTINEL);
        if (stop.end) return { seq, reached_end: true };
        stop.baseline_style = snapshot.baseline[stop.selector] || null;
        delete stop.end;
        seq.push(stop);
      }
      return { seq, reached_end: false };
    }

    const first = await walk(maxTabs);
    let escapeReleases = null;
    if (!first.reached_end) {
      await p.keyboard.press("Escape");
      escapeReleases = (await walk(maxTabs)).reached_end;
    }

    result = {
      label: "Recorded by keyboard_walk.cjs from a real headless Chromium run.",
      page: path.basename(page),
      adapter: { playwright: pwVersion, chromium: browser.version(), axe_core: axeVersion },
      max_tabs: maxTabs,
      axe_violations: axe,
      interactive: snapshot.interactive,
      positive_tabindex: snapshot.positive,
      tab_sequence: first.seq,
      reached_end: first.reached_end,
      escape_releases: escapeReleases,
    };
  } finally {
    await browser.close();
  }
  emit(result, 0);
})().catch((err) => emit({ error: "walk-failed", detail: String(err.message).split("\n")[0] }, 1));

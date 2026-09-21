#!/usr/bin/env bash
set -euo pipefail

node - "$@" <<'NODE'
const args = process.argv.slice(2);
let vault = "";
let file = "";
let obsidianUrl = "";
let host = "https://obsid.net/";

function usage() {
  console.error("Usage:");
  console.error("  build_obsid_link.sh --vault <vault> --file <file-path> [--host https://obsid.net/]");
  console.error("  build_obsid_link.sh --obsidian-url <obsidian://open?...> [--host https://obsid.net/]");
}

for (let i = 0; i < args.length; i += 1) {
  const arg = args[i];
  if (arg === "--vault") {
    vault = args[i + 1] || "";
    i += 1;
  } else if (arg === "--file") {
    file = args[i + 1] || "";
    i += 1;
  } else if (arg === "--obsidian-url") {
    obsidianUrl = args[i + 1] || "";
    i += 1;
  } else if (arg === "--host") {
    host = args[i + 1] || host;
    i += 1;
  } else if (arg === "-h" || arg === "--help") {
    usage();
    process.exit(0);
  } else {
    console.error("Unknown argument: " + arg);
    usage();
    process.exit(1);
  }
}

if (obsidianUrl) {
  let parsed;
  try {
    parsed = new URL(obsidianUrl);
  } catch {
    console.error("Error: invalid --obsidian-url value");
    process.exit(1);
  }

  if (parsed.protocol !== "obsidian:" || parsed.hostname !== "open") {
    console.error("Error: --obsidian-url must start with obsidian://open");
    process.exit(1);
  }

  vault = parsed.searchParams.get("vault") || vault;
  file = parsed.searchParams.get("file") || file;
}

if (!vault || !file) {
  console.error("Error: both vault and file are required.");
  usage();
  process.exit(1);
}

if (!host.endsWith("/")) {
  host += "/";
}

const normalizedFile = file.replace(/\\/g, "/");
const output =
  host +
  "?vault=" + encodeURIComponent(vault) +
  "&file=" + encodeURIComponent(normalizedFile);

console.log(output);
NODE

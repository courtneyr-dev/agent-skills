#!/usr/bin/env python3
"""Regenerate ledger.json and capability-matrix.json from live state plus the facts recorded below.

Live state: clone HEADs and dates, the skill-sync registry, installed tree hashes, links that leave an
installed skill, qualification results, and which fleet skills exist. Recorded facts: licenses, rights,
installer side effects and native tools, read from the pinned files on 2026-11-25 and 2026-11-26.
Edit facts here, never in the JSON. Rerun after an upstream update or re-pin, then run verify_sources.py.
"""

import json
import os
import re
import subprocess
from datetime import datetime, timezone
from pathlib import Path

import verify_sources as v

HERE = Path(__file__).resolve().parent
SKILLS_ROOT = v.SKILLS_ROOT
UPSTREAM = Path(os.environ.get("FRIG_UPSTREAM_ROOT") or SKILLS_ROOT / "factory-rig" / "upstream")  # as factory-rig
CACHE = v.sync_skills.REPOS  # skill-sync's clone cache ($SKILL_SYNC_HOME/repos)
FR = "skills/factory-rig/registry/components.json#"
REFERENCE_TOOLS = "Checked 2026-11-26 with command -v: present gh (signed in), uv, docker, node, npm, composer, wp, php, go, jq, git; absent terraform, packer, wrangler, ddev, snyk, semgrep, pdflatex, xelatex; python-docx not importable."

# Hidden upstream skills: installed tonight, kept out of the global skill list, loaded by path.
HIDDEN_REPOS = {"alirezarezvani/claude-skills", "coreyhaines31/marketingskills", "samber/developer-relations-skills",
                "zstvns/design-skills", "learning-commons-org/agent-skills", "cloudflare/skills", "kanopi/cms-cultivator",
                "trailofbits/skills", "hashicorp/agent-skills", "Automattic/claude-woocommerce-toolkit",
                "woocommerce/agent-skills", "msitarzewski/agency-agents"}

# Items a factory-rig component record verified with evidence; other items in those repos stay inactive here.
FACTORY_VERIFIED = {
    "magnus919/agent-skills": ["technical-program-management", "technical-project-management", "implementation-planning",
                               "kanban-guru", "multi-agent-coordination", "agent-evals-and-observability",
                               "production-readiness", "release-engineering", "verification-methodology", "incident-learning"],
    "mattpocock/skills": ["wayfinder", "to-spec", "to-tickets", "implement-spec", "implement"],
    "poteto/noodle": ["noodle"],
    "yysun/project-manager": ["project-manager", "test-manager", "brd-writer"],
    "t3dotgg/tstack": ["babysit-pr", "file-pr", "leaving-pr-comments", "resolving-merge-conflicts", "takeover",
                       "full-send", "full-stop", "sol-loop", "council"],
}


def lic(spdx, file, holder, other=None, share_alike=False, note=""):
    return {"spdx": spdx, "file": file, "holder": holder, "other_licenses": other or [], "share_alike": share_alike,
            "note": note}


REPOS = [
    {"id": "alirezarezvani/claude-skills", "clone": "claude-skills", "status": "installed-inactive",
     "license": lic("MIT", "LICENSE", "Copyright (c) 2025 Alireza Rezvani",
                    ["engineering-team/playwright-pro/LICENSE", "engineering-team/self-improving-agent/LICENSE",
                     "engineering/book-to-skill/LICENSE", "engineering/collab-proof/LICENSE", "engineering/hivemind/LICENSE.txt"],
                    note="Nested license files sit outside the 30 installed directories; installed skills that carry a license field say MIT."),
     "rights": "Redistributable under MIT with the notice. VERIFIED.md measures activation only: Claude Code 2.1.317, sonnet, the skill's own plugin installed, 2 positive and 1 negative prompt, one run. It proves neither business accuracy nor Codex behavior.",
     "side_effects": ["scripts/codex-install.sh copies skills into $HOME/.codex/skills (lines 33, 196, 205)",
                      "business-growth/hooks/hooks.json registers a UserPromptSubmit router hook; 20+ plugin hooks.json files exist outside the installed directories",
                      "engineering/skillopt-sleep/scripts/install-cron.sh installs a cron job (outside the installed directories)",
                      "skill-sync copied only the 30 skill directories, so no hook, cron or plugin manifest was installed"],
     "native_tools": ["python3 stdlib scripts (README.md:436 says no pip installs); 6 of 30 SKILL.md files read, the other 24 unread"],
     "decision": "Selected 30 corporate, commercial, finance, operations, product and compliance packages; medical-device and regulatory families excluded (S07-018)."},
    {"id": "msitarzewski/agency-agents", "clone": "agency-agents", "status": "source-only",
     "license": lic("MIT", "LICENSE", "Copyright (c) 2025 AgentLand Contributors"),
     "rights": "MIT. Role briefs are seeds only: product/product-manager.md:14 invents '10+ years' of experience; engineering/engineering-cms-developer.md:469,516,519 states universal Core Web Vitals and TTFB targets. specialized/agents-orchestrator.md is a top-level orchestrator and is not adopted.",
     "side_effects": ["scripts/install.sh copies or symlinks agents into ~/.claude/agents (:863) and ~/.github/agents (:878) after probing $HOME dotdirs (:532-548)",
                      "integrations/mcp-memory/setup.sh reads ~/.config/claude/mcp.json and ~/.cursor/mcp.json (:39, :44) and prints pip/npm steps"],
     "native_tools": ["none for seed reading"],
     "decision": "Nothing installed. Fleet roles may paraphrase responsibilities, never the biographies or numeric targets."},
    {"id": "magnus919/agent-skills", "clone": "agent-skills", "status": "installed-and-verified", "status_owner": FR + "magnus",
     "license": lic("MIT", "LICENSE.md", "Copyright (c) 2026 Magnus Hedemark",
                    ["agent-council/LICENSE", "artifact-pyramids/LICENSE", "harness-engineering/LICENSE", "promise-theory/LICENSE", "semantic-spacetime/LICENSE"],
                    note="kanban-guru has no license field in its frontmatter; nested licenses are outside the installed set."),
     "rights": "MIT with the notice.",
     "side_effects": ["Makefile targets are dev-only (lint, test, deps) and pip-install into .venv (:12-13)",
                      ".claude-plugin/marketplace.json, .codex-plugin/plugin.json and .agents/plugins/marketplace.json are not used; skill-sync installs directories"],
     "native_tools": ["web-accessibility: no runtime dependency (SKILL.md:10)", "release-engineering scripts run git log"],
     "decision": "Ten management skills from the earlier install plus web-accessibility added 2026-11-25 for the accessibility gap."},
    {"id": "kanopi/cms-cultivator", "clone": "cms-cultivator", "status": "installed-inactive",
     "license": lic("GPL-2.0-or-later", "LICENSE.md", "No holder line; .claude-plugin/plugin.json:10 declares GPL-2.0-or-later", share_alike=True,
                    note="Copyleft: redistributed modifications stay GPL."),
     "rights": "GPL v2 or later. Public workflows only; Kanopi's private Audit, DevOps and PM libraries are not available and not claimed.",
     "side_effects": ["No installer script or hooks; .claude-plugin and .codex-plugin manifests unused",
                      "pr-quality-report carries its own 'Side Effect Warning' (creates or edits PRs and comments through gh)"],
     "native_tools": ["code-standards-checker: DDEV prefix when .ddev/ exists (SKILL.md:76-77), Kanopi composer scripts (:107-114), falls back without DDEV (:151)",
                      "composer-security-update: Teamwork task flow and kanopi.teamwork.com (:10-34, :77-84), ddev snapshot/exec/drush (:66-286), scripts/audit_table.py",
                      "pr-quality-report: snyk code test (:103), gh pr view/edit/create/comment (:143-223)"],
     "decision": "Three delivery procedures adopted; DDEV, Teamwork and Snyk steps run only through the actual tools of a project (absent on the reference installation: ddev, snyk)."},
    {"id": "WordPress/agent-skills", "clone": "wordpress-agent-skills", "status": "installed-inactive",
     "license": lic("GPL-2.0-or-later", "LICENSE", "Copyright (C) 2026 WordPress Contributors", share_alike=True),
     "rights": "GPL v2 or later. Default branch trunk; skills target WordPress 7.0+ and PHP 7.4+ (README.md:187), so legacy client sites route by their actual versions.",
     "side_effects": ["shared/scripts/skillpack-install.mjs --global writes ~/.claude/skills, ~/.cursor/skills and ~/.gemini/antigravity/skills (:166-172); not run",
                      "Installed through skill-sync; wp-ability-development lands in ~/.agents/skills (dest)"],
     "native_tools": ["bash and node; wp-env needs Docker and Node 18.12+; wp-playground Node 20.18+; wp-wpcli-and-ops WP-CLI; wpds a WPDS MCP server; wp-phpstan Composer"],
     "decision": "Canonical WordPress source, installed before tonight (19 skills) plus wp-ability-development. Model-visible; this ledger holds no behavioral evidence for it."},
    {"id": "woocommerce/agent-skills", "clone": "woocommerce-agent-skills", "status": "source-only",
     "license": lic("GPL-2.0-or-later", "LICENSE", "Copyright (C) 2026 WooCommerce Contributors", share_alike=True,
                    note="GPL version line not read; recheck before redistribution."),
     "rights": "GPL. Two narrow skills: abilities-api-implement (WordPress 6.9+, WooCommerce 10.9+) and woocommerce-stale-pr-audit (gh, Node 20+).",
     "side_effects": ["shared/scripts/skillpack-install.mjs, same layout as WordPress; not run"],
     "native_tools": ["gh, Python 3.9+, Node 20+ for woocommerce-stale-pr-audit"],
     "decision": "Not installed: neither skill covers a required capability that the Automattic toolkit and WordPress skills leave open."},
    {"id": "Automattic/claude-woocommerce-toolkit", "clone": "claude-woocommerce-toolkit", "status": "installed-inactive",
     "license": lic("GPL-2.0-or-later", "LICENSE", "GNU GPL v2 text, no holder line", share_alike=True,
                    note="Version clause not confirmed beyond the v2 header."),
     "rights": "GPL v2. The three installed SKILL.md files use no Claude-only features; the Claude-specific agents/ and docs/installation.md are not installed.",
     "side_effects": ["docs/installation.md tells users to cp skills into ~/.claude/skills and agents into ~/.claude/agents; not run"],
     "native_tools": ["PHPStan level 7+ (woocommerce-finalize SKILL.md:56)", "git diff between tags (woocommerce-upgrade-safety :72-73)", "PHPUnit and Playwright (woocommerce-plugin-dev references/testing.md)"],
     "decision": "Commerce engineering procedures; Codex compatibility not exercised."},
    {"id": "cloudflare/skills", "clone": "cloudflare-skills", "status": "installed-inactive",
     "license": lic("Apache-2.0", "LICENSE", "Holder line not captured"),
     "rights": "Apache-2.0; keep LICENSE and any NOTICE.",
     "side_effects": ["mcp.json and .mcp.json register https://mcp.cloudflare.com/mcp; the plugin manifests are unused, so no MCP server was added",
                      "Scripts exist only under skills/turnstile-spin (not installed)"],
     "native_tools": ["wrangler with wrangler login OAuth, a wrangler.jsonc project and an API token (absent on the reference installation)",
                      "cloudflare-one and gateway-workers need a Zero Trust account and Access service tokens"],
     "decision": "Four platform skills. Live use is blocked until a Cloudflare account and scope are named; no account is configured."},
    {"id": "hashicorp/agent-skills", "clone": "hashicorp-agent-skills", "status": "installed-inactive",
     "license": lic("MPL-2.0", "LICENSE", "metadata.copyright: Copyright IBM Corp. 2026 (terraform-test SKILL.md:6)", share_alike=True,
                    note="File-level copyleft."),
     "rights": "MPL-2.0. terraform-test SKILL.md:28: apply is the default test mode and creates real resources; local qualification must use command = plan or mock providers (Terraform 1.7.0+, SKILL.md:27).",
     "side_effects": ["Plugin manifests unused; scripts/validate-structure.sh and check-links.py are maintainer tools"],
     "native_tools": ["terraform CLI 1.7.0+ for mocks, 1.9.0+ for parallel; optional tflint (terraform and packer absent on the reference installation)"],
     "decision": "terraform-test and terraform-style-guide only. No test runs against a real provider; nothing ran because terraform is absent."},
    {"id": "trailofbits/skills", "clone": "trailofbits-skills", "status": "installed-inactive",
     "license": lic("CC-BY-SA-4.0", "LICENSE", "Holder line not in the first lines read; README.md:165-167 confirms the license", share_alike=True,
                    note="ShareAlike: adapted material must carry the same license and attribution."),
     "rights": "CC BY-SA 4.0. Local adapters that copy text from these skills inherit ShareAlike; prefer linking by path.",
     "side_effects": ["plugins/fp-check/hooks/hooks.json registers Stop and SubagentStop prompt hooks; not installed (outside the skill directory)",
                      "differential-review commands/ and agents/, and fp-check's three agents, are outside the installed directories"],
     "native_tools": ["differential-review: git", "supply-chain-risk-auditor: uv run, gh auth status, network to GitHub and package registries, Python 3.11+"],
     "decision": "Assurance methods for product and agency review. fp-check runs without its hooks, so its gate is advisory."},
    {"id": "coreyhaines31/marketingskills", "clone": "marketingskills", "status": "installed-inactive",
     "license": lic("MIT", "LICENSE", "Copyright (c) 2025 Corey Haines"),
     "rights": "MIT with the notice. Canonical marketing procedures. Shared context files (.agents/product-marketing.md) need one owner each.",
     "side_effects": ["Plugin manifests unused; validate-skills scripts are maintainer tools; tools/clis/*.js outside the installed set"],
     "native_tools": ["Optional third-party tools and MCP servers listed per skill (seo-audit:470, ads:458, analytics:353); none required"],
     "decision": "22 skills. Sends, scheduling and publishing go through the rig's send gates, never the skills directly."},
    {"id": "zstvns/design-skills", "clone": "design-skills", "status": "installed-inactive",
     "license": lic("MIT", "LICENSE", "Copyright (c) 2026 Zach Stevens"),
     "rights": "MIT with the notice. Canonical brand and design procedures.",
     "side_effects": ["INSTALL.md documents /plugin marketplace add and npx skills add --all, which write .agents/skills, a duplicate tree and .claude/skills symlinks plus skills-lock.json; not run"],
     "native_tools": ["None required (INSTALL.md:3); product-film needs Remotion and Chrome; design-system ships scripts/check-foundations.py"],
     "decision": "All 11 skills."},
    {"id": "samber/developer-relations-skills", "clone": "developer-relations-skills", "status": "installed-inactive",
     "license": lic("MIT", "LICENSE", "Copyright (c) 2026 Samuel Berthe", note="All 93 SKILL.md files carry license: MIT."),
     "rights": "MIT with the notice. Attribution to Samuel Berthe stays in every installed directory.",
     "side_effects": ["README:24, 44, 73 give npx skills add, /plugin install and gemini extensions install; not run",
                      "references/context-artifact.md has the agent write devrel-context.md to the project root; devrel-program-kit maps it"],
     "native_tools": ["8 helper shell scripts, e.g. changelog-writing needs bash 3.2+ and git 2.21+"],
     "decision": "Complete tree (93 of 93) installed to keep the dependency closure; see closure."},
    {"id": "learning-commons-org/agent-skills", "clone": "learning-commons-agent-skills", "status": "installed-inactive",
     "license": lic("Apache-2.0", "LICENSE", "NOTICE: Copyright 2026 Anthropic, PBC; Copyright 2026 Learning Commons",
                    ["skills/*/LICENSE (Apache-2.0)", "skills/*/NOTICE", "skills/k12-check-for-understanding/NOTICE (Student Achievement Partners acknowledgment, not an endorsement)"],
                    note="Each installed directory carries its own LICENSE and NOTICE; k12-fixing-lesson-plans has no license field in SKILL.md."),
     "rights": "Apache-2.0; keep LICENSE and NOTICE. Rubric CSVs live under evals/ (not installed); evals/README.md:40 says using them needs manual setup or an existing harness, and no evaluator code is published.",
     "side_effects": ["scripts/render_all.sh runs python3 -m pip install python-docx==1.1.2 when docx is missing (k12-lesson-differentiation :22, k12-lesson-plan-creation :23); never run"],
     "native_tools": ["python3; python-docx for .docx output (absent); optional Learning Commons Knowledge Graph connector (not configured)"],
     "decision": "Canonical K-12 teaching source, all five skills. No same-named Anthropic teaching skills installed."},
    {"id": "DaRL-GenAI/instructional_agents-skills", "clone": "instructional_agents-skills", "status": "source-only",
     "license": lic("MIT", "LICENSE", "Copyright (c) 2026 DaRL-GenAI"),
     "rights": "MIT. Research wrappers for arXiv 2508.19611. slide-evaluate's 'Test Student' (SKILL.md:13; scripts/evaluate.py:48) is an LLM persona review, a fixture, not learner evidence.",
     "side_effects": ["README:28-34: pip install instructional-agents, /plugin install, or clone into ~/.claude/plugins; not run"],
     "native_tools": ["Python 3.11+, the instructional-agents pip package, OPENAI_API_KEY, Node and npm -g pptxgenjs, pdflatex or xelatex (absent)"],
     "decision": "Not installed: needs a network pip install, an OpenAI key and LaTeX; the default model and simulated student are not accepted."},
    {"id": "DaRL-GenAI/instructional_agents", "clone": "instructional_agents", "status": "source-only",
     "license": lic("MIT", "LICENSE", "Copyright (c) 2025 DaRL-GenAI", ["assets/slide_gen/skill/LICENSE (MIT, Zara Zhang)", "assets/slide_gen/runtime/licenses/ (MathJax, OFL fonts; names only)"]),
     "rights": "MIT. ADDIE research pipeline; src/evaluate.py:27-28 defines a Test Student prompt. Higher-education results do not transfer to K-12 BCIT without evidence.",
     "side_effects": ["Dockerfile installs texlive, pipes nodesource setup into bash and npm -g installs; start.sh runs docker compose and curls localhost:8000; not run"],
     "native_tools": ["Python 3.11+, openai, fastapi, playwright, python-pptx, Docker, OPENAI_API_KEY"],
     "decision": "Reference for gap analysis only."},
    {"id": "wateryqz/instructional_agents112", "clone": "instructional_agents112", "status": "source-only",
     "license": lic("MIT", "LICENSE", "Copyright (c) 2025 DaRL-GenAI (owner is wateryqz)"),
     "rights": "MIT. A near-copy of DaRL-GenAI/instructional_agents last changed 2026-04-17; the README does not say it is a fork.",
     "side_effects": ["Same Dockerfile, start.sh and pyproject as instructional_agents; not run"],
     "native_tools": ["Same as instructional_agents"],
     "decision": "Not used; the canonical DaRL repository supersedes it."},
    {"id": "mattpocock/skills", "clone": "mattpocock-skills", "status": "installed-and-verified", "status_owner": FR + "matt-stable",
     "license": lic("MIT", "LICENSE", "Copyright (c) 2026 Matt Pocock"),
     "rights": "MIT with the notice.",
     "side_effects": ["scripts/link-skills.sh (dev-only) symlinks skills into ~/.claude/skills and ~/.agents/skills; not run",
                      "git-guardrails-claude-code, when invoked, copies a hook script and merges a PreToolUse hook into settings.json"],
     "native_tools": ["gh for GitHub trackers; npm, husky, lint-staged and prettier for setup-pre-commit"],
     "decision": "Earlier install; factory-rig owns the status (matt-stable verified, matt-experimental inactive)."},
    {"id": "poteto/noodle", "clone": "noodle", "status": "installed-and-verified", "status_owner": FR + "noodle",
     "license": lic("MIT", "LICENSE", "Copyright (c) 2026 Lauren Tan", [".agents/skills/frontend-design/LICENSE.txt (Apache-2.0)", ".agents/skills/skill-creator/LICENSE.txt (Apache-2.0)"]),
     "rights": "MIT; the Apache-2.0 nested skills are not installed.",
     "side_effects": ["INSTALL.md: brew install or release download, fetches skill files into .agents/skills/noodle, writes .noodle.toml; the rig built the binary instead (factory-rig record)"],
     "native_tools": ["noodle Go binary built at 82d2921; Claude or Codex provider"],
     "decision": "Execution backend under factory-rig."},
    {"id": "yysun/project-manager", "clone": "project-manager", "status": "installed-and-verified", "status_owner": FR + "yysun-project-manager",
     "license": lic("NOASSERTION", None, "No LICENSE file (git ls-files finds none); plugin.json:6 declares MIT; holder unstated",
                    note="Treat redistribution as unlicensed until a LICENSE file exists."),
     "rights": "Private use only; do not redistribute.",
     "side_effects": ["mcp.json registers a stdio MCP server (node bin/project-manager-mcp.mjs); assets/studio.sh launches a local studio"],
     "native_tools": ["Node.js scripts; optional pm_project_status and pm_open_board MCP tools"],
     "decision": "PM layer owner; earlier install."},
    {"id": "cody-hutson/pmo-platform", "clone": "pmo-platform", "status": "installed-inactive", "status_owner": FR + "pmo-platform",
     "license": lic("BUSL-1.1", "LICENSE", "Licensed Work (c) 2026 Cody Hutson",
                    note="Additional Use Grant: non-production, personal, educational and internal business use; Change Date 2030-05-27 to Apache-2.0. Source-available, not open source."),
     "rights": "Do not redistribute or offer as a hosted or managed service.",
     "side_effects": ["install.sh and core/deploy/deploy.sh write ~/.claude/skills, ~/.claude/rules, ~/.config/pmo-platform and ~/Claude; core/settings.json.template defines hooks; the rig installed into a separate workspace (factory-rig record)"],
     "native_tools": ["macOS 12+, python3, shasum, git, jq, Claude Code"],
     "decision": "Earlier install; not in skill-sync."},
    {"id": "alp82/curia", "clone": "curia", "status": "blocked-platform", "status_owner": FR + "curia",
     "license": lic("NOASSERTION", None, "No root license; skills/LICENSE is MIT (Matt Pocock) for the vendored skills only",
                    note="Treat the application as all rights reserved."),
     "rights": "No license for Curia's own code.",
     "side_effects": ["deploy/bootstrap/curia-install.sh downloads an npm tarball, a Node runtime and a Compose bundle into $HOME/.local/share/curia; not run"],
     "native_tools": ["Linux x86_64 only (curia-install.sh:127-131), Node 22+, tmux, Docker, Tailscale, Discord, gh"],
     "decision": "Blocked: no supported host."},
    {"id": "obsidianmd/obsidian-skills", "clone": "obsidian-skills", "status": "installed-and-verified", "status_owner": FR + "obsidian-connectors",
     "license": lic("MIT", "LICENSE", "Copyright (c) 2026 Steph Ango (@kepano)", ["plugins/obsidian/LICENSE (MIT)"]),
     "rights": "MIT with the notice.",
     "side_effects": ["Installed as Claude plugin obsidian@obsidian-skills 1.2.3 and by npx skills into ~/.agents/skills (factory-rig record); not managed by skill-sync"],
     "native_tools": ["Obsidian app with the obsidian CLI; defuddle via npm -g; ob and Node 22+ for headless; Node 20+ for knap"],
     "decision": "Earlier install; seven skills in ~/.agents/skills."},
    {"id": "t3dotgg/tstack", "clone": None, "cache": "t3dotgg__tstack", "status": "installed-and-verified", "status_owner": FR + "tstack",
     "license": lic("MIT", "LICENSE", "Copyright (c) 2026 Theo Browne"),
     "rights": "MIT with the notice. takeover references modernize, which is not installed.",
     "side_effects": ["README:29-35 tells users to cp skills into ~/.claude/skills or ~/.codex/skills; not run"],
     "native_tools": ["gh and jq; babysit-pr's pr-wait polls GitHub PR state"],
     "decision": "Earlier install; no upstream clone, so the revision is read from the skill-sync cache."},
]

FLEET = {"S03": "corporate", "S04": "agency", "S05": "hosting", "S06": "product", "S07": "consultancies",
         "S08": "devrel", "S09": "community", "S10": "bcit-education", "S11": "instructional-design", "ED": "bcit-education"}
BUILDER = {"corporate": "corporate-and-agency", "agency": "corporate-and-agency", "hosting": "hosting",
           "product": "product-and-consultancies", "consultancies": "product-and-consultancies", "devrel": "devrel-and-community",
           "community": "devrel-and-community", "bcit-education": "education", "instructional-design": "education"}


def U(skills, adapter):
    return {"disposition": "upstream-skill", "skills": skills, "adapter": adapter}


def E(skills, note=""):
    return {"disposition": "existing-skill", "skills": skills, "note": note}


def O(skill, note="", builder=None):
    return {"disposition": "original-local", "local_skill": skill, "note": note, **({"builder": builder} if builder else {})}


def B(blocker, resume):
    return {"disposition": "blocker", "blocker": blocker, "resume": resume}


ALIREZA = ["access-lifecycle", "capacity-planner", "ceo-advisor", "cfo-advisor", "channel-economics", "chro-advisor", "ciso-advisor",
           "compliance-os", "coo-advisor", "cpo-advisor", "cro-advisor", "cto-advisor", "customer-success-manager", "deal-desk",
           "financial-analyst", "gdpr-dsgvo-expert", "general-counsel-advisor", "isms-audit-expert", "month-end-close",
           "partnerships-architect", "pricing-strategist", "process-mapper", "procurement-optimizer", "product-analytics",
           "revenue-operations", "rfp-responder", "sales-engineer", "soc2-compliance", "support-ops", "vendor-management"]
ADVISORY = "Load by path from the role; advisory only, never an officer, lawyer or auditor (S03-028); numeric benchmarks become stated hypotheses (override register)."
FOUND = "foundation"
LC = ["k12-lesson-plan-creation", "k12-lesson-prep", "k12-lesson-differentiation", "k12-check-for-understanding", "k12-fixing-lesson-plans"]
HOST_PLANNED = "fleets/hosting/roles.json had 0 roles at the 2026-11-26 check."

ROWS = {
    "S03-001": O("company-fleets", "Fleet record fleets/corporate/; its roles.json had 0 roles at the 2026-11-26 check.", FOUND),
    "S03-002": U(["ceo-advisor", "coo-advisor"], ADVISORY + " Chief of staff maps to Matt's chief-of-staff (inactive)."),
    "S03-003": U(["ceo-advisor", "coo-advisor"], ADVISORY + " Decision records go to the existing decision log, not a new store."),
    "S03-004": U(["cto-advisor"], ADVISORY),
    "S03-005": U(["cto-advisor"], ADVISORY),
    "S03-006": U(["cpo-advisor", "product-analytics"], ADVISORY),
    "S03-007": U(["cpo-advisor"], ADVISORY + " Requirements stay with yysun brd-writer."),
    "S03-008": U(["cfo-advisor", "financial-analyst", "month-end-close"], ADVISORY + " No tax or audit opinion."),
    "S03-009": U(["financial-analyst", "month-end-close"], "month-end-close scripts take synthetic ledgers; exit 4 means the reconciliation does not prove. " + ADVISORY),
    "S03-010": U(["cro-advisor", "revenue-operations", "sales-engineer", "rfp-responder", "deal-desk"], ADVISORY),
    "S03-011": U(["rfp-responder", "deal-desk", "pricing-strategist"], "Pricing scripts state assumptions; margins come from the actual rate card. " + ADVISORY),
    "S03-012": U(["product-marketing", "marketing-plan", "ads", "content-strategy", "emails", "analytics"], "Corey Haines procedures; sends and publishing pass corporate-email-guard and corporate-claims-check."),
    "S03-013": U(["product-marketing", "marketing-plan", "ad-creative", "channel-economics", "analytics"], "Outputs are staged only; claims pass corporate-claims-check."),
    "S03-014": U(["partnerships-architect", "channel-economics", "referrals"], ADVISORY),
    "S03-015": U(["partnerships-architect", "channel-economics", "attribution"], "Attribution limits are stated, not modeled as fact."),
    "S03-016": U(["customer-success-manager", "support-ops"], ADVISORY),
    "S03-017": U(["customer-success-manager", "support-ops"], "Health evidence comes from real records only; fixtures are synthetic."),
    "S03-018": U(["chro-advisor", "capacity-planner"], "No employment decisions (prompt Instructions); capacity model output carries its assumptions."),
    "S03-019": U(["chro-advisor", "capacity-planner"], "No employment decisions; queueing results are labeled as models."),
    "S03-020": U(["ciso-advisor", "general-counsel-advisor", "gdpr-dsgvo-expert", "isms-audit-expert", "compliance-os"], ADVISORY + " No legal conclusions."),
    "S03-021": U(["compliance-os", "soc2-compliance", "isms-audit-expert"], "Evidence mappings feed consult-compliance-engagement; no certification claims."),
    "S03-022": U(["procurement-optimizer", "vendor-management", "access-lifecycle", "process-mapper"], ADVISORY),
    "S03-023": U(["vendor-management", "access-lifecycle", "process-mapper"], "Access inventories use synthetic fixtures; no real identity system is read."),
    "S03-024": U(["product-analytics", "analytics", "ab-testing"], "Metric definitions stay in the owning record; no new dashboard."),
    "S03-025": U(["analytics", "ab-testing", "product-analytics"], "No dashboard or new BI service (section 15); results are reports."),
    "S03-026": U(["public-relations"], "Claims pass corporate-claims-check; crisis communications need a named human approver."),
    "S03-027": O("corporate-claims-check"),
    "S03-028": O("company-fleets", "role.schema.json and validate reject credentials and self-appointed authority.", FOUND),
    "S03-029": O("company-fleets", "registry/profiles.json selects the operating profile; generic targets become hypotheses.", FOUND),
    "S03-030": U(ALIREZA, "Selection and pins in sources/ledger.json; all 30 hidden from the global list and loaded by path."),
    "S04-001": O("agency-engagement-gate"),
    "S04-002": O("agency-engagement-gate"),
    "S04-003": U(["customer-research"], "Observed findings need real participants; synthetic interviews are labeled fixtures."),
    "S04-004": U(["customer-research", "process-mapper"], "Service blueprints from process-mapper; observed findings need real research."),
    "S04-005": U(["content-strategy", "site-architecture"], "Corey Haines procedures, adapted to the client CMS through agency-platform-adapters."),
    "S04-006": U(["content-strategy", "site-architecture"], "Migration mapping hands to hosting-data-migration."),
    "S04-007": U(["brand-strategy", "creative-direction", "art-direction", "design-system", "motion-design", "web-design"], "Zach Stevens procedures; asset rights recorded per deliverable."),
    "S04-008": U(["design-system", "web-design", "brand"], "Accessible prototypes pass agency-keyboard-audit and web-accessibility."),
    "S04-009": O("agency-platform-adapters"),
    "S04-010": E(["wp-plugin-development", "wp-block-development", "wp-phpstan", "verification-methodology"], "WordPress first; other stacks route through agency-platform-adapters."),
    "S04-011": E(["test-manager", "web-accessibility", "review-security", "wp-performance"]),
    "S04-012": E(["test-manager", "verification-methodology"], "Keyboard defects missed by scanners: agency-keyboard-audit."),
    "S04-013": E(["release-engineering", "production-readiness"]),
    "S04-014": E(["release-engineering", "production-readiness"]),
    "S04-015": O("agency-platform-adapters"),
    "S04-016": O("agency-engagement-gate"),
    "S04-017": O("agency-engagement-gate", "Scope changes return through yysun project-manager."),
    "S04-018": U(["code-standards-checker", "composer-security-update", "pr-quality-report"], "DDEV, Teamwork and Snyk steps replaced by the project's actual tools; private Kanopi libraries not claimed. WordPress through the existing WordPress skills."),
    "S04-019": E(["wp-phpstan", "wp-plugin-development"], "Kanopi code-standards-checker adds PHPCS runs where the project defines them."),
    "S05-001": O("hosting-service-catalogue", HOST_PLANNED),
    "S05-002": O("hosting-service-catalogue"),
    "S05-003": O("hosting-account-lifecycle", "Fake panel adapter only; a real cPanel/WHM adapter is S05-021."),
    "S05-004": B("No VPS provider or alternative panel (Plesk or other) is selected, and no credentials exist.", "Name the provider and panel, record its API docs and a test account, then add an adapter to hosting-account-lifecycle."),
    "S05-005": E(["wp-wpcli-and-ops", "wp-performance", "wp-project-triage"], "WordPress only; Drupal and other CMS operations have no installed skill."),
    "S05-006": U(["wrangler", "workers-best-practices"], "Activation blocked until a Cloudflare account and scope are named; isolation tests through hosting-tenant-isolation."),
    "S05-007": U(["terraform-test", "terraform-style-guide"], "Plan-mode or mock-provider tests only (terraform-test SKILL.md:28 says apply creates real resources); terraform absent on the reference installation."),
    "S05-008": O("hosting-tenant-isolation"),
    "S05-009": B("Failover and failback across real failure domains need redundant infrastructure that this task does not authorize.", "With an authorized disposable multi-host lab, add a failover exercise to hosting-incident-response and record measured results."),
    "S05-010": O("hosting-service-catalogue"),
    "S05-011": O("company-fleets", "Hosting roles belong in fleets/hosting/roles.json; " + HOST_PLANNED, FOUND),
    "S05-012": O("hosting-account-lifecycle"),
    "S05-013": O("hosting-service-catalogue"),
    "S05-014": O("hosting-tenant-isolation"),
    "S05-015": O("hosting-dns-cert-lifecycle", "Backup restore and data migration: hosting-data-migration (scripts only, no SKILL.md at the 2026-11-26 check)."),
    "S05-016": O("hosting-incident-response", "Post-incident learning hands to Magnus incident-learning."),
    "S05-017": O("hosting-metering-reconcile"),
    "S05-018": O("hosting-abuse-response"),
    "S05-019": O("hosting-account-lifecycle", "Export and decommission are lifecycle stages."),
    "S05-020": O("hosting-incident-response", "No disaster-recovery exercise found in the skill text at the 2026-11-26 check; restore drills only."),
    "S05-021": B("No hosting provider is selected and no provider credentials or test account exist, so no real cPanel/WHM or reseller adapter can be built or tested.", "Choose the provider, record its API documentation revision and a test account, then build the adapter in hosting-account-lifecycle against it."),
    "S05-022": O("hosting-tenant-isolation", "Build-execution and preview boundaries."),
    "S05-023": O("hosting-service-catalogue", "No Acquia, Pantheon or VIP benchmark matrix found in hosting skills at the 2026-11-26 check; the contract column stays empty because no plan or contract exists."),
    "S05-024": O("hosting-service-catalogue", "Benchmark dimensions not found at the 2026-11-26 check."),
    "S05-025": O("hosting-service-catalogue"),
    "S05-026": O("hosting-service-catalogue"),
    "S05-027": E(["production-readiness"], "Readiness backlog; demonstrations stay disposable."),
    "S06-001": O("product-release-gate"),
    "S06-002": U(["cpo-advisor", "product-analytics", "developer-ecosystem-strategy"], ADVISORY),
    "S06-003": O("product-release-gate"),
    "S06-004": O("product-release-gate"),
    "S06-005": O("product-release-gate"),
    "S06-006": U(["supply-chain-risk-auditor"], "Needs gh auth and network; output is CC BY-SA material if copied. SBOM generation is not covered."),
    "S06-007": U(["woocommerce-upgrade-safety", "version-migration-guide"], "WooCommerce-specific upgrade checks; other hosts need product-release-gate rows."),
    "S06-008": U(["oss-release-policy", "changelog-writing"], "Release mechanics stay with Magnus release-engineering."),
    "S06-009": O("product-payment-events"),
    "S06-010": E(["wp-plugin-directory-guidelines"], "WordPress.org only; other marketplaces have no checklist."),
    "S06-011": U(["developer-certification-program", "developer-quickstart-guide"], "Quickstarts replay through devrel-quickstart-replay."),
    "S06-012": O("product-release-gate"),
    "S07-001": O("company-fleets", "fleets/consultancies/roles.json had 0 roles at the 2026-11-26 check.", FOUND),
    "S07-002": E(["web-accessibility", "wordpress-accessibility"]),
    "S07-003": O("agency-keyboard-audit", "", "corporate-and-agency"),
    "S07-004": U(["brand-strategy", "brand", "creative-direction", "logo-design"], "Research provenance required; no invented user research."),
    "S07-005": U(["brand", "design-system"], "Token and component use checked against the approved direction."),
    "S07-006": O("consult-i18n-check"),
    "S07-007": O("consult-i18n-check"),
    "S07-008": O("consult-compliance-engagement"),
    "S07-009": O("consult-compliance-engagement"),
    "S07-010": U(["woocommerce-plugin-dev", "woocommerce-finalize"], "WooCommerce only; payment idempotency through product-payment-events."),
    "S07-011": O("product-payment-events"),
    "S07-012": U(["seo-audit", "ai-seo", "schema", "site-architecture"], "Claims pass consult-search-claims-check."),
    "S07-013": O("consult-search-claims-check"),
    "S07-014": U(["emails"], "Sends pass consult-email-send-gate."),
    "S07-015": O("consult-email-send-gate"),
    "S07-016": O("consult-compliance-engagement"),
    "S07-017": O("consult-compliance-engagement"),
    "S07-018": U(["compliance-os"], "Selection in sources/ledger.json: no medical-device or other unrelated regulatory skills installed."),
    "S07-019": O("agency-keyboard-audit", "", "corporate-and-agency"),
    "S07-020": O("consult-i18n-check"),
    "S07-021": O("consult-search-claims-check"),
    "S07-022": U(["seo-audit", "ai-seo", "emails", "product-marketing", "marketing-plan", "brand", "design-system"], "Canonical marketing and design sources; hidden from the global list, loaded by path."),
    "S07-023": U(["product-marketing", "brand"], "One owner per shared context file (.agents/product-marketing.md, .agents/brand.md, .agents/design.md); the owner mapping is open in sources/README.md."),
    "S07-024": U(["marketing-loops"], "Loops stage outputs only; scheduling and sends go through existing authorized tools and the send gates."),
    "S08-001": U(["developer-relations-kickoff"], "All 93 samber skills installed and hidden; attribution to Samuel Berthe kept."),
    "S08-002": O("devrel-program-kit", "Roles in fleets/devrel/roles.json (14 roles at the 2026-11-26 check)."),
    "S08-003": U(["devrel-strategy", "developer-segmentation", "devrel-budget-allocation", "devrel-team-structure"], "Bounded by the devrel fleet coordinator."),
    "S08-004": O("devrel-quickstart-replay", "Journeys and tutorials from samber developer-journey-map, developer-quickstart-guide and developer-tutorial."),
    "S08-005": U(["devrel-field-events", "developer-event-followup", "developer-live-demo-design"], "Event accessibility checked against web-accessibility."),
    "S08-006": U(["developer-feedback-loop"], "Product issues go to the existing tracker owner."),
    "S08-007": U(["devrel-metrics", "devrel-analytics", "devrel-exec-reporting"], "Attribution limits stated."),
    "S08-008": U(["developer-relations-kickoff"], "Bounded delegate under the one-dispatcher rule; its '65-skill' count is stale against the 93-skill tree."),
    "S08-009": U(["devrel-team-structure", "devrel-budget-allocation", "developer-segmentation", "developer-journey-map", "devrel-metrics", "devrel-analytics", "devrel-exec-reporting", "developer-education-strategy", "developer-quickstart-guide", "developer-tutorial"], "Loaded by path through the kickoff router."),
    "S08-010": O("devrel-program-kit", "Maps devrel-context.md into the rig's context records."),
    "S08-011": O("devrel-program-kit"),
    "S08-012": O("devrel-program-kit"),
    "S08-013": O("devrel-program-kit"),
    "S09-001": O("community-operating-kit", "Roles in fleets/community/roles.json (18 roles at the 2026-11-26 check)."),
    "S09-002": O("community-operating-kit"),
    "S09-003": O("community-operating-kit"),
    "S09-004": O("community-moderation-review"),
    "S09-005": U(["oss-contributor-onboarding", "oss-maintainer-sustainability"], "Recognition avoids volunteer rankings (community-health-measures)."),
    "S09-006": U(["developer-meetup-program", "developer-event-followup"], "Existing community-os covers campaigns and Discord rituals."),
    "S09-007": U(["oss-governance", "oss-sponsors-fundraising", "oss-maintainer-sustainability"], "Governance decisions stay with named humans."),
    "S09-008": O("community-health-measures", "Confidential cases stay out of aggregate measures."),
    "S09-009": O("community-health-measures"),
    "S09-010": U(["developer-community-launch", "developer-community-health", "developer-community-moderation", "developer-feedback-loop", "developer-champions", "discord-community-playbook", "discourse-forums-playbook", "oss-contributor-onboarding", "oss-issue-triage", "oss-governance", "oss-release-policy"], "Bounded by the community coordinator; moderation drafts pass community-moderation-review."),
    "S09-011": O("community-operating-kit"),
    "S09-012": O("community-health-measures"),
    "S09-013": O("community-moderation-review"),
    "S09-014": O("community-operating-kit"),
    "S10-001": O("bcit-learning-package", "fleets/bcit-education/roles.json had 0 roles at the 2026-11-26 check."),
    "S10-002": O("bcit-learning-package", "Roles not yet registered at the 2026-11-26 check."),
    "S10-003": O("bcit-learning-package"),
    "S10-004": O("company-fleets", "Persona schema rejects certification and teacher-of-record authority.", FOUND),
    "S10-005": O("edu-standards-alignment"),
    "S10-006": O("edu-standards-alignment"),
    "S10-007": O("edu-standards-alignment"),
    "S10-008": O("edu-standards-alignment"),
    "S10-009": O("edu-standards-alignment", "Content-area names only; NBEA 2023 standard text is licensed and no license is on record, so alignment to its text stays a recorded gap."),
    "S10-010": O("edu-standards-alignment", "NOCTI blueprint access not on record; the category is recorded, items never reproduced."),
    "S10-011": O("edu-standards-alignment"),
    "S10-012": O("edu-standards-alignment"),
    "S10-013": O("edu-standards-alignment"),
    "S10-014": O("edu-student-data-guard"),
    "S10-015": O("edu-assessment-check"),
    "S10-016": U(LC, "Complete set at b23623c, hidden and loaded by path; HTML render runs, DOCX needs python-docx (absent; render_all.sh would pip-install it)."),
    "S10-017": U(LC, "LICENSE and NOTICE kept in each installed directory; formative checks are math-oriented, not BCIT coverage. The rubric CSVs are under evals/ in the clone, not installed, and are not yet wired into the rig evaluator."),
    "S10-018": B("The Learning Commons Knowledge Graph connector is not configured, so no standard can be verified through it.", "Configure the supported connector, confirm it holds the exact standards and edition, then rerun edu-standards-alignment with it."),
    "S10-019": O("bcit-learning-package"),
    "S10-020": O("bcit-learning-package"),
    "S10-021": O("bcit-learning-package", "Answer keys executed by edu-answer-key-check."),
    "S10-022": O("bcit-learning-package"),
    "S10-023": O("bcit-learning-package"),
    "S11-001": O("edu-needs-analysis", "fleets/instructional-design/roles.json had 0 roles at the 2026-11-26 check."),
    "S11-002": O("edu-needs-analysis"),
    "S11-003": O("edu-learning-progression"),
    "S11-004": O("edu-learning-progression"),
    "S11-005": O("edu-trainer-development", "Facilitator and learner materials; captions and media production have no toolchain."),
    "S11-006": B("No target LMS or delivery platform is named, so export formats and platform integration cannot be validated.", "Name the platform and version, then validate one export package against it."),
    "S11-007": B("The DaRL pipeline needs a network pip install, an OPENAI_API_KEY and LaTeX (pdflatex absent); none were run.", "Approve the pip install and a provider key, install TeX, then run course-generate on a synthetic brief with a non-default model and record outputs."),
    "S11-008": B("Same prerequisites as S11-007; the four wrappers were read, not run. slide-evaluate's Test Student is a fixture.", "After S11-007's resume, run each wrapper once and record dependencies and outputs."),
    "S11-009": O("company-fleets", "dispatch is false on every role; no imported orchestrator.", FOUND),
    "S11-010": O("edu-research-review"),
    "S11-011": O("edu-standards-alignment", "The only fleet skill that cites CAST UDL at the 2026-11-26 check."),
    "S11-012": B("Quality Matters review is a formal, licensed process and no CASE or QTI target platform is named.", "Name the target platform and version before validating CASE or QTI; register QM only with access terms."),
    "S11-013": O("edu-trainer-development"),
    "S11-014": O("edu-trainer-development"),
    "S11-015": O("edu-trainer-development"),
}
ED_MAP = {
    "001": ("company-fleets", FOUND), "002": ("edu-research-review", None), "003": ("company-fleets", FOUND),
    "004": ("edu-research-review", None), "005": ("edu-learning-progression", None), "006": ("edu-trainer-development", None),
    "007": ("edu-research-review", None), "008": ("edu-research-review", None), "009": ("edu-research-review", None),
    "010": ("edu-research-review", None), "011": ("edu-research-review", None), "012": ("edu-research-review", None),
    "013": ("bcit-learning-package", None), "014": ("edu-learning-progression", None), "015": ("edu-assessment-check", None),
    "016": ("edu-trainer-development", None), "017": ("edu-learning-progression", None), "018": ("edu-answer-key-check", None),
    "019": ("edu-assessment-check", None), "020": ("cs-classroom-instruction", None), "021": ("cs-classroom-instruction", None),
    "022": ("cs-classroom-instruction", None), "023": ("cs-classroom-instruction", None), "024": ("cs-classroom-instruction", None),
    "025": ("cs-classroom-instruction", None), "026": ("edu-assessment-check", None), "027": ("cs-classroom-instruction", None),
    "028": ("edu-student-data-guard", None), "029": ("edu-research-review", None), "030": ("edu-research-review", None),
    "031": ("edu-learning-progression", None), "032": ("cs-classroom-instruction", None), "033": ("edu-answer-key-check", None),
    "034": ("edu-trainer-development", None), "035": ("edu-research-review", None), "036": ("edu-trainer-development", None),
    "037": ("company-fleets", FOUND), "038": ("company-fleets", FOUND), "039": ("company-fleets", FOUND),
    "040": ("edu-standards-alignment", None), "041": ("edu-standards-alignment", None), "042": ("edu-standards-alignment", None),
    "043": ("edu-standards-alignment", None), "044": ("edu-learning-progression", None), "045": ("edu-standards-alignment", None),
    "046": ("edu-research-review", None), "047": ("edu-standards-alignment", None), "048": ("edu-standards-alignment", None),
    "049": ("edu-standards-alignment", None), "050": ("edu-research-review", None), "051": ("cs-classroom-instruction", None),
    "052": ("edu-assessment-check", None), "053": ("edu-research-review", None), "054": ("edu-standards-alignment", None),
    "055": ("company-fleets", FOUND), "058": ("company-fleets", FOUND),
}
for n, (skill, builder) in ED_MAP.items():
    ROWS[f"ED-{n}"] = O(skill, "", builder)
VAULT = ("Vault notes are the integrator's deliverable, not a rig skill; this workstream does not write the vault.",
         "The integrator writes the entries in its own notes location with that location's existing frontmatter and records.")
ROWS["ED-056"] = B(*VAULT)
ROWS["ED-057"] = B(*VAULT)


def git(path, *args):
    r = subprocess.run(["git", "-C", str(path), *args], capture_output=True, text=True)
    return r.stdout.strip() if r.returncode == 0 else None


def home_rel(p):
    """A path in its portable form: under the upstream root, the skill-sync cache or the skills root, else ~-relative."""
    p = str(p)
    for root, name in ((UPSTREAM, "$FRIG_UPSTREAM_ROOT"), (CACHE, "$SKILL_SYNC_HOME/repos"), (SKILLS_ROOT, "<skills-root>")):
        if p == str(root) or p.startswith(str(root) + os.sep):
            return name + p[len(str(root)):]
    return "~" + p[len(str(Path.home())):] if p.startswith(str(Path.home())) else p


def qualification():
    """{skill: 'pass' | 'fail' | 'blocked'} from qualify.py's evidence; a skill fails if any case failed."""
    path = HERE / "evidence/qualification.json"
    if not path.exists():
        return {}
    data = json.loads(path.read_text())
    if data.get("runner") != "qualify.py":
        return {}
    out = {}
    for c in data["results"]:
        prev = out.get(c["skill"])
        out[c["skill"]] = "fail" if "fail" in (prev, c["outcome"]) else ("pass" if c["outcome"] == "pass" or prev == "pass" else c["outcome"])
    return out


def reason(link):
    m = re.match(r"\.\./([a-z0-9-]+)/SKILL\.md$", link)
    return f"sibling skill {m.group(1)} not installed (selective install)" if m else "upstream file outside the installed directory"


def item_status(repo, name, qual):
    if repo["id"] in FACTORY_VERIFIED:
        return "installed-and-verified" if name in FACTORY_VERIFIED[repo["id"]] else "installed-inactive"
    if qual.get(name) == "fail":
        return "verification-failed"
    if qual.get(name) == "pass":
        return "installed-and-verified"
    return "installed-inactive"


def build_ledger(registry):
    qual = qualification()
    repos, items = [], []
    for spec in REPOS:
        clone = UPSTREAM / spec["clone"] if spec.get("clone") else CACHE / spec["cache"]
        rec = {"id": spec["id"], "url": f"https://github.com/{spec['id']}", "clone": home_rel(clone),
               "revision": git(clone, "rev-parse", "HEAD"), "revision_date": git(clone, "log", "-1", "--format=%cI"),
               "head_author": git(clone, "log", "-1", "--format=%an"), "owner": spec["id"].split("/")[0],
               "status": spec["status"]}
        rec.update({k: spec[k] for k in ("status_owner", "license", "rights", "side_effects", "native_tools", "decision") if k in spec})
        rec["installed"] = []
        for name, entry in sorted(registry.items()):
            if entry["repo"] != spec["id"]:
                continue
            dest = Path(entry["dest"]).expanduser() if entry.get("dest") else SKILLS_ROOT / name
            hidden = entry.get("frontmatter", {}).get("disable-model-invocation") == "disable-model-invocation: true"
            rec["installed"].append({"name": name, "dest": home_rel(dest)})
            it = {"name": name, "repo": spec["id"], "path": entry["path"], "dest": home_rel(dest),
                  "status": item_status(spec, name, qual), "model_invocation": "disabled" if hidden else "enabled",
                  "tree_sha256": v.tree_hash(dest)}
            dangling = [{"from": f, "link": link, "reason": reason(link)}
                        for f, link, target in v.escaping_links(dest) if not target.exists()]
            if dangling:
                it["dangling_links"] = dangling
            items.append(it)
        repos.append(rec)
    return {"schema_version": 1, "generated": datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds"),
            "generator": "sources/build_sources.py", "statuses": sorted(v.STATUSES), "native_tools_on_reference_install": REFERENCE_TOOLS,
            "closure": samber_closure(), "repos": repos, "items": items}


def samber_closure():
    root = UPSTREAM / "developer-relations-skills/skills"
    tree = {p.parent.name for p in root.glob("*/SKILL.md")}
    refs, external = {}, {}
    for md in root.rglob("*.md"):
        text = md.read_text(errors="replace")
        for n in re.findall(r"samber/developer-relations-skills@([a-z0-9-]+)", text):
            refs[n] = refs.get(n, 0) + 1
        for coll in re.findall(r"([a-z0-9-]+/[a-z0-9-]+)@[a-z0-9-]+", text):
            if coll != "samber/developer-relations-skills":
                external[coll] = external.get(coll, 0) + 1
    return {"repo": "samber/developer-relations-skills", "method": "every samber/developer-relations-skills@<name> reference in skills/**/*.md at the pinned revision",
            "skills_in_tree": len(tree), "published_count": "65 (skills/developer-relations-kickoff/SKILL.md:12)",
            "references": sum(refs.values()), "distinct_names": len(refs),
            "unresolved": {n: c for n, c in sorted(refs.items()) if n not in tree},
            "external_collections_not_pinned": dict(sorted(external.items()))}


def build_matrix(registry):
    reqs = json.loads((HERE.parent / "registry/requirements.json").read_text())["rows"]
    rows = []
    for r in reqs:
        fleet = FLEET[r["id"].split("-")[0]]
        row = {"requirement": r["id"], "fleet": fleet, "text": r["text"], **ROWS[r["id"]]}
        if row["disposition"] == "upstream-skill":
            row["upstream"] = [f"{registry[s]['repo']}:{registry[s]['path']}" for s in row["skills"]]
        if row["disposition"] == "original-local":
            row.setdefault("builder", BUILDER[fleet])
            row["state_at_build"] = "present" if (SKILLS_ROOT / row["local_skill"] / "SKILL.md").is_file() else "planned"
        row["verification"] = {
            "upstream-skill": "Installed tree matches the ledger pin; behavior per the ledger item status.",
            "existing-skill": "Skill present; behavior owned by that skill's own evaluations.",
            "original-local": f"Built by the {row.get('builder')} workstream; behavior per its fleet evals.json.",
            "blocker": "Not covered until the resume step runs."}[row["disposition"]]
        rows.append(row)
    summary = {}
    for row in rows:
        s = summary.setdefault(row["fleet"], {"rows": 0, "existing-skill": 0, "upstream-skill": 0, "original-local": 0,
                                              "original-local-planned": 0, "blocker": 0})
        s["rows"] += 1
        s[row["disposition"]] += 1
        s["original-local-planned"] += row.get("state_at_build") == "planned"
    return {"schema_version": 1, "generated": datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds"),
            "generator": "sources/build_sources.py", "requirements": "skills/company-fleets/registry/requirements.json",
            "dispositions": sorted(v.DISPOSITIONS), "summary_by_fleet": summary, "rows": rows}


def main():
    registry = json.loads(Path(v.sync_skills.MANIFEST).read_text())
    for name, obj in (("ledger.json", build_ledger(registry)), ("capability-matrix.json", build_matrix(registry))):
        (HERE / name).write_text(json.dumps(obj, indent=1) + "\n")
        print(f"wrote {name}")


if __name__ == "__main__":
    main()

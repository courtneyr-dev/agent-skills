# Operations

Commands run from the factory-rig folder: `FR="$PWD/bin/frig"`. Every path default is listed in
`config/frig.example.env`. These commands were last run end to end on 2026-11-25 on the reference install.

## Launch a supervised Noodle run

```bash
FR="$PWD/bin/frig"
$FR noodle-init --ws WS --bin-dir "$PWD/bin"     # .noodle.toml + project skills; commit the result in WS/repo
nohup $FR noodle-run --ws WS \
  --max-scheduler-sessions 3 --max-wall 1500 --exit-when-idle > WS/noodle-run.out 2>&1 &
$FR dispatch --ws WS --task TASK-ID --provider codex --model gpt-6-sol     # owner pid read from .factory-rig/noodle.pid
```

`noodle-run` starts `$FRIG_NOODLE_BIN`, else `noodle` on PATH; pass `--noodle-bin` to pick another build.
Valid Codex models are in `$CODEX_HOME/models_cache.json` (default `~/.codex`, visibility `list`); dispatch checks it.

## Inspect

```bash
$FR frontier --ws WS --backend noodle      # eligible work and why the rest is not
$FR report --ws WS                         # task states, leases, open receipts, attempts
cat WS/repo/.noodle/pending-review.json    # parked candidates (Noodle's own state)
```

## Finish or interrupt

```bash
$FR review --ws WS --attempt A... --verdict approve --reviewer-provider claude --implementer-provider codex
$FR complete --ws WS --attempt A...        # gate, merge, tracker evidence, Noodle close-out
$FR abandon  --ws WS --attempt A... --why "reason"   # worker failed or stopped: tracker blocked, lease released
$FR fence    --ws WS --task TASK-ID        # stop a holder that may still be running
$FR reconcile --ws WS                      # finish interrupted completions from real state
```

Never run `noodle start` by hand for real work: `noodle-run` is what bounds scheduler sessions (OVR-NOODLE-SCHEDULER-BUDGET).
To stop a run now: `kill $(cat WS/.factory-rig/noodle.pid)`; the lease stays `active` until `abandon` or `fence`, so side effects stay visible.

## Verify

```bash
(cd scripts && python3 -W ignore -m unittest tests.test_core tests.test_flow tests.test_noodle_integration)
$FR registry-verify
$FR drift                                  # upstream moved since the pin? names the checks to rerun
```

`drift` reads one clone per component under `$FRIG_UPSTREAM_ROOT` (default `upstream/` in this folder),
named by the component's `clone` field. A component with no clone there reports `missing-clone`.

## Update

1. Check installed skills against their sources with your skill manager, and run `$FR drift` for the pinned upstreams.
2. Noodle: rebuild in a clean clone at the new revision (`pnpm install --frozen-lockfile --filter noodle-ui...`, `pnpm --filter noodle-ui build`, `go build -o bin/noodle .`), install it beside the old build in a folder named by revision, point `FRIG_NOODLE_BIN` at it, rerun the three test modules, run one live pilot, then change the revision and checksum in `registry/components.json`.

## Roll back

- Skills: `git revert` the commit.
- Noodle: point `FRIG_NOODLE_BIN` (or `noodle-run --noodle-bin`) at the previous build; keep both on disk.
- Provider policy: `config/provider-policy.json` (or `$FRIG_POLICY`) is a plain file; the wrapper fails closed (exit 64) if it is missing.
- PMO: delete `$PMO_WORKSPACE` (the install writes nowhere else when the variables below are exported).
- MCP: `claude mcp remove project-manager` and `codex mcp remove project-manager`.

## Render the override register

```bash
$FR render-overrides     # registry/overrides.json -> references/overrides.md
```

## PMO, scoped install

`PMO_WORKSPACE` is any empty folder you choose; the clone is `$FRIG_UPSTREAM_ROOT/pmo-platform`.
PMO Platform is BSL 1.1: read its license before you install it, and don't redistribute it.

```bash
W="$PMO_WORKSPACE"
export PMO_PLATFORM_DEPLOY_ROOT=$W/.deploy-root PMO_PLATFORM_CONFIG_ROOT=$W/.config-pmo CLAUDE_WORKSPACE_ROOT=$W/workspace
cd "$FRIG_UPSTREAM_ROOT/pmo-platform"
bash ./install.sh --workspace-root $W/workspace --config-root $W/.config-pmo --non-interactive --dry-run
bash ./install.sh --workspace-root $W/workspace --config-root $W/.config-pmo --non-interactive
# the installer then deploys skills under the workspace; validate with the deploy root it used:
PMO_PLATFORM_DEPLOY_ROOT=$W/workspace bash ./docs/scripts/validate-install.sh --mode install --source-repo $PWD --workspace-root $W/workspace --validation-dir $W/validation
```

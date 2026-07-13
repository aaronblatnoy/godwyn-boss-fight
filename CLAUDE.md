# CLAUDE.md — Godwyn Boss Fight

## What this is

A faithful Elden Ring boss fight — Godwyn the Golden / Miquella, God of Abundance — built from scratch in Godot 4, running natively on a self-hosted Linux render server. The fight replaces Radahn, Consort of Miquella at the end of Shadow of the Erdtree. Fidelity target: indistinguishable from a real FromSoftware encounter.

The project is built entirely by **claude-fable-5** (Claude Fable 5) over multiple sessions. All design decisions are locked in `SPEC.txt`. All lore and narrative are in `boss-fight.txt`.

## Render server

The build and render server is a self-hosted Arch Linux box with 2x RTX 3060 Ti (8GB each). Its SSH alias and connection details are configured in the local (non-committed) `~/CLAUDE.md` — not repeated here to keep this document clean.

```
ssh <server> "cmd"          # run remote command (non-interactive one-shot)
ssh <server> "cmd1 && cmd2" # multi-line remote
scp file <server>:~/path    # copy to server
```

**CRITICAL:** Claude Code cannot open interactive SSH sessions. Always run as one-shot commands. Never use `-t` or expect a shell prompt.

GPU: 2x RTX 3060 Ti (8GB each). CUDA driver 610.43.02. A third card is quarantined at the OS level — do not attempt to use it.

## Repository layout

```
godwyn-boss-fight/
├── SPEC.txt                  # Complete build spec — Fable's source of truth
├── boss-fight.txt            # Lore, narrative, full boss fight sequence
├── blender-build-plan.txt    # Phase plan for Blender character model pipeline
├── blender-workflow.js       # Executable workflow script (Workflow tool)
├── scripts/                  # Blender Python (bpy) scripts, copied to server
├── models/                   # .blend files (generated on server)
├── renders/
│   ├── character/            # Character sheet renders (2K portrait)
│   └── moveset/              # Moveset pose renders (1080p)
└── lifecycle/
    ├── brainstorms/          # Exploratory idea docs
    ├── pending/plans/        # Active phase plans
    └── archive/plans/        # Executed plans
```

The Godot game itself (res://) will live in a subdirectory once Fable starts the build. See SPEC.txt Section 2 for the full Godot project structure.

## Core domain concepts

**Two-phase boss fight:**
- **Phase 1 (Godwyn the Golden / Prince of Gold):** Miquella's idealized memory of Godwyn. Fight in a black void. Clean, golden, sacred. Pure swordsman.
- **Phase 1.5 (50% HP):** Dragon lightning unlocks. Lightning attacks integrate into melee flow. Soft phase transition, no cutscene.
- **Transition:** Void clears, corrupted Godwyn body revealed, Miquella walks out of the Gate of Divinity and possesses it.
- **Phase 2 (Miquella / God of Abundance):** Miquella's soul inside Godwyn's body. Gold running through deathroot. Will system active.

**Godwyn's combat identity:** Relentless mobile swordsman. One continuous flowing assault — not discrete attacks. Low hang guard. Everything chains into everything. Never truly stops. Rewards aggression, punishes hesitation. "Hesitation is defeat."

**State-based combat system:** He moves between states (Facing/Low Hang, Back to Player, Airborne, Extended/Committed). Every exit from every state is an attack. Overshoots are not mistakes — they become attacks.

**Will system (Phase 2 only):** Secondary bar. Drains facing boss, recovers moving. Empties → "Your grace fades," HUD disappears 15s.

## Load-bearing invariants

These violations cause the most bugs. Never break them.

1. **Headless-only on the server.** Every Blender and Godot operation runs via `ssh <server> "blender --background --python script.py"`. No interactive sessions. No GUI.
2. **GPU-real rendering.** Blender Cycles MUST use OptiX/CUDA on the RTX 3060 Tis. CPU fallback is a failure, not degraded output. Assert GPU in every render script preamble.
3. **Spec-fidelity.** All character appearance, damage values, timing, and combat logic come from SPEC.txt. Do not invent. Do not deviate.
4. **Phase 1 appearance rules.** NO crown, NO dark markings, barefoot, partial armor over exposed chest, no deathroot. These are in SPEC.txt lines 293-341. Phase 2 is different — do not conflate.
5. **Overshoot rule.** Any lunge/thrust/jump that carries Godwyn past the player immediately enters Back-to-Player state. There is no neutral reset from an overshoot.
6. **Idempotent scripts.** Every bpy script deletes its own objects by name before recreating. Re-running must never duplicate geometry.
7. **Never auto-push.** Git commits are made on the server after each phase. Push to GitHub only on explicit user instruction.

## Player stats (from SPEC.txt)

- HP: 500 | Stamina: 100 | Flasks: 5 (180 HP each)
- Stamina costs: light attack 12, heavy 22, roll 15
- Roll iframes: frames 4–16 (mid roll)
- Lock-on: 25m max, Q/E to switch targets

## Godwyn Phase 1 stats

- HP: 2500 | Poise: 80 | Stagger duration: 0.8s
- Phase 2 HP resets to 3000 at transition start

## Blender pipeline (current active work)

Workflow script: `blender-workflow.js` — run via `Workflow({ scriptPath: "..." })`.

All bpy scripts authored locally, copied to the server, run headlessly:
```
scp scripts/01_base_mesh.py <server>:~/godwyn-boss-fight/scripts/
ssh <server> "blender --background --python ~/godwyn-boss-fight/scripts/01_base_mesh.py 2>&1"
```

Render outputs saved to `renders/character/` (2K portrait, 2048×2560) and `renders/moveset/` (1080p, 1920×1080). Cinematic Cycles, 128–256 samples, OptiX denoise, Filmic/AgX color management.

## Key colors (linear RGB, from SPEC.txt)

| Element | Value |
|---|---|
| Skin base | 0.95, 0.90, 0.82 |
| Skin emission | 1.0, 0.88, 0.45 @ 2.5 strength |
| Gold armor | 0.82, 0.65, 0.15 (metallic=1) |
| Blue robe | 0.08, 0.12, 0.35 |
| Key light | 1.0, 0.92, 0.6 |
| Void bg | near-black |
| Golden crack | 1.0, 0.85, 0.4 |
| UI / "YOU DIED" | #C8986E |

## Conventions

- **All design decisions go in SPEC.txt.** Not in code comments, not in commit messages. SPEC.txt is the single source of truth.
- **Blender scripts are the reproducible source.** The `.blend` is regenerable from scripts. Commit the scripts, commit the `.blend`, both.
- **bpy scripts named numerically:** `00_env_setup.py`, `01_base_mesh.py`, `02_details.py`, etc. One script per phase.
- **All remote artifacts under `~/godwyn-boss-fight/` on the server** — never write to arbitrary paths.
- **GDScript** for all Godot logic. No C#, no GDNative.
- **Animation-driven combat** — not physics-driven. AttackState → hitbox active on frame N → hitstop via Engine.time_scale = 0.05.

## What NOT to do

- Do not open interactive SSH sessions
- Do not run Blender with a display/GUI on the server
- Do not use the quarantined third GPU (card at PCIe 07:00.0)
- Do not use the Godot physics engine for combat hit detection — use hitbox/hurtbox Areas
- Do not put Phase 2 dark markings or crown on Phase 1 Godwyn
- Do not add a crown to Godwyn at all in Phase 1
- Do not use CPU for Blender renders — fail loud, fix root cause
- Do not push to GitHub without explicit user confirmation
- Do not invent attack timings or damage values not in SPEC.txt

## Working flow

This project uses a **brainstorm → plan → execute** lifecycle.

| Folder | Agent | Purpose |
|---|---|---|
| `lifecycle/brainstorms/` | `feature-brainstormer` | Exploratory idea docs before committing to a direction |
| `lifecycle/pending/plans/` | `phase-plan-architect` | Active phase plans ready to execute |
| `lifecycle/archive/plans/` | `phase-plan-executor` | Plans moved here after successful execution |

**Spawning agents:**
- Explore a new feature or idea → `feature-brainstormer` → writes to `lifecycle/brainstorms/`
- Turn a direction into a build plan → `phase-plan-architect` → writes to `lifecycle/pending/plans/`
- Execute a plan with real parallelism → `phase-plan-executor` → compiles to a workflow script → run via `Workflow({ scriptPath: "..." })`

Plans that are mid-execution live in `pending/plans/`. Once a workflow completes successfully, the plan moves to `archive/plans/`.

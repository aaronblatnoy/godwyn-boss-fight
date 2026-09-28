# Repository cleanup manifest

Prepared on 2026-09-27 before applying any cleanup move. Sizes are byte counts from the Mac working copy. `T` means tracked by Git and `U` means untracked. Every operation is conditional on the source still being older than two hours immediately before it is touched.

## Baseline

- Markdown link check: 46 Markdown files, 66 local links, 0 broken.
- Top-level Python scripts: 455.
- Top-level model files: 59.
- Top-level `renders/astra/char2` files: 606.
- Existing unrelated working-tree changes are preserved and are not staged by this cleanup.
- Concurrent-job exclusions: all `meshy_body_i02*`, `codex_meshy_body_i02*`, `rehost_body_i02/`, `MESHY_BODY_I02_*`, `astra_character_v2_body_i02*`, and every file less than two hours old.

## Script archive moves

The initial inventory found 130 candidates (592,990 bytes). Final dependency validation identified five shared runtime modules required by untouched live pipelines, so 125 campaign-only files (540,297 bytes) use `git mv`. Each destination receives a `README.md` pointing to its campaign report.

| Group | Source match | Files | T/U | Bytes | Destination |
|---|---|---:|---:|---:|---|
| Character round 2 | `scripts/astra_char2_round2_*` | 11 | 11/0 | 48,319 | `scripts/archive/char2-round2/` |
| Character round 3 | `scripts/astra_char2_r3_*` | 15 | 15/0 | 52,398 | `scripts/archive/char2-r3/` |
| Character round 4 | `scripts/astra_char2_r4_*` | 13 | 13/0 | 53,601 | `scripts/archive/char2-r4/` |
| Character round 5 | `scripts/astra_char2_r5_*` | 14 | 14/0 | 51,393 | `scripts/archive/char2-r5/` |
| Character round 6 | `scripts/astra_char2_r6_*` | 9 | 9/0 | 30,237 | `scripts/archive/char2-r6/` |
| Character foundation | `scripts/astra_character_*` except shared `astra_character_common.py` | 25 | 25/0 | 94,162 | `scripts/archive/character-foundation/` |
| MPFB graft | `scripts/astra_char2_mpfb_*` | 19 | 19/0 | 93,153 | `scripts/archive/mpfb/` |
| Armature audit | `scripts/astra_armaudit_*` except shared `astra_armaudit_analyze.py` | 4 | 4/0 | 48,205 | `scripts/archive/armature-audit/` |
| Cinematic tests | `scripts/astra_cine_*` except shared render modules | 5 | 5/0 | 13,792 | `scripts/archive/cinematic/` |
| Likeness | `scripts/astra_likeness_*` except shared `astra_likeness_render.py` | 10 | 10/0 | 55,037 | `scripts/archive/likeness/` |

The live `astra_move_*`, `astra_rehost_*`, `astra_meshy_*`, `astra_body_*`, `astra_xslash_*`, `anim_*`, `hymotion_*`, and numbered build scripts remain at `scripts/`.

## Model archive moves

The model move contains 46 files and 5,550,567,300 bytes. The 11 legacy Godwyn exports are tracked and will use `git mv`; the other 35 files are intentionally untracked and will use plain `mv`.

| Group | Source files or match | Files | T/U | Bytes | Destination |
|---|---|---:|---:|---:|---|
| Pre-char2 backups | `astra_character_v2_prechar2.*` | 2 | 0/2 | 203,688,388 | `models/archive/character-prechar2/` |
| Character round backups | `astra_character_v2_preround*`, `round2_input*`, `round2_work*`, `round2_iteration9*`, `r3_preweights*` | 11 | 0/11 | 2,058,971,450 | `models/archive/character-rounds/` |
| MPFB iterations | `astra_character_mpfb_head_i0*.blend`, `astra_character_v2_premfpb.blend`, `astra_character_v2_mpfb_surface_finish_i03.blend` | 6 | 0/6 | 750,448,614 | `models/archive/mpfb/` |
| Collar, clay, and character work | `astra_character_r5_clay.blend`, `astra_character_v2_char2_work.blend`, `astra_character_v2_collar_banked.*` | 4 | 0/4 | 1,193,451,766 | `models/archive/character-work/` |
| X-slash iterations | `astra_xslash_wip.blend`, `astra_xslash_v2_wip.blend`, `astra_xslash_v2_final_prefix*.blend`, `astra_xslash_v2_final_wip.blend`, `astra_xslash_v2_on_char_wip.blend`, `astra_xslash_v2_armfix_trial.blend` | 7 | 0/7 | 552,997,701 | `models/archive/xslash/` |
| Move WIP and pre-state files | non-v2 `astra_move_*_wip.blend`, `astra_move_*_pre_*` | 5 | 0/5 | 516,053,940 | `models/archive/moves/` |
| Legacy Godwyn exports | noncanonical `godwyn_*.blend` and `godwyn_*.glb` | 11 | 11/0 | 274,955,441 | `models/archive/legacy-godwyn/` |

Canonical files listed in the cleanup brief remain in place, including `astra_character_v2.blend/.glb`, all `astra_character_v2_pre_*.*`, v2 move WIPs, final-on-char2 X-slash, Meshy inputs, and game assets.

## Character evidence archive moves

The initial filename groups contained 487 files and 461,425,967 bytes. Final top-level validation found another 29 old round-1/likeness entries that belonged with those campaigns. The applied archive therefore contains 516 entries (515 regular files and one retained log symlink) and 470,855,049 bytes. Tracked files use `git mv`; untracked evidence uses plain `mv`. Reports move with their evidence except `LIKENESS_REPORT.md`, which remains at `char2/` and is relinked to the likeness archive.

| Group | Source match | Files | T/U | T bytes | U bytes | Destination |
|---|---|---:|---:|---:|---:|---|
| Foundation | `REPORT.md`, before/after/draft/side-by-side/stress evidence, logs, maps, and manifests | 71 | 28/43 | 2,050,434 | 72,891,564 | `renders/astra/char2/archive/foundation/` |
| Round 2 | `ROUND2_REPORT.md`, `r2_*`, `round2_*` | 66 | 30/36 | 194,945 | 79,752,165 | `renders/astra/char2/archive/round2/` |
| Round 3 | `ROUND3_REPORT.md`, `r3_*` | 50 | 33/17 | 2,549,990 | 66,977,458 | `renders/astra/char2/archive/round3/` |
| Round 4 | `ROUND4_REPORT.md`, `r4_*` | 37 | 25/12 | 136,467 | 52,229,676 | `renders/astra/char2/archive/round4/` |
| Round 5 | `ROUND5_STOP_REPORT.md`, `r5_*`, `clay_*`, `three_quarter_iterations.png` | 36 | 17/19 | 64,322 | 35,715,445 | `renders/astra/char2/archive/round5/` |
| Round 6 | `ROUND6_COLLAR_BANKED.md`, `r6_*` | 38 | 18/20 | 81,978 | 36,509,575 | `renders/astra/char2/archive/round6/` |
| MPFB | `MPFB_GRAFT_REPORT.md`, `mpfb_*` | 185 | 82/103 | 14,184,656 | 86,358,924 | `renders/astra/char2/archive/mpfb/` |
| Likeness iterations | `LIKENESS_VERDICTS.md`, `LIKENESS_BRIEF.txt`, `likeness_*`, retained log symlink | 33 | 32/1 | 21,157,380 | 70 | `renders/astra/char2/archive/likeness/` |

Meshy head evidence, Meshy body evidence, `fullbody_*.png`, and `LIKENESS_REPORT.md` remain at `renders/astra/char2/`. All current Meshy body work is additionally protected by the concurrent-job exclusions.

## Planned deletions

No `.blend`, `.glb`, `.npz`, `.mp4`, `.md`, or `.json` file is deleted. The deletion candidates below are all older than two hours at inventory time.

| Target | Files | Bytes | Proof or allowed class |
|---|---:|---:|---|
| `renders/astra/armaudit/decoded_lunge_thrust_strike1/` | 3 | 1,354,800 | sibling `clips_lunge_thrust_strike1_slowmo.mp4` |
| `renders/astra/armaudit/decoded_xslash_strike1/` | 2 | 1,025,604 | sibling `sheet_xslash_inherited.png` |
| `renders/astra/armaudit/decoded_xslash_strike2/` | 3 | 1,207,240 | sibling `sheet_xslash_inherited.png` |
| `renders/astra/final/video_frames/` | 61 | 27,100,468 | sibling `contact_sheet_front.png` |
| `renders/astra/v2_final/video_frames/` | 90 | 45,717,886 | sibling `poses_sheet_three_quarter.png` |
| `renders/astra/v2_final_on_char/video_frames/` | 90 | 35,924,107 | sibling `poses_sheet_three_quarter.png` |
| `renders/astra/v2_on_char/video_frames/` | 90 | 45,014,725 | sibling `poses_sheet_three_quarter.png` |
| `renders/astra/v2_r3/video_frames/` | 90 | 45,703,495 | sibling `candidate.mp4` |
| `.DS_Store`, `renders/.DS_Store` | 2 | 12,296 | explicitly allowed disposable metadata |
| `models/astra_character_v2.blend1` | 1 | 126,617,938 | explicitly allowed Blender backup |
| old files in `scripts/__pycache__/` | 53 | 1,383,422 | explicitly allowed bytecode cache |

Planned deletion total: 331,061,981 bytes. Sixteen recent bytecode files (211,258 bytes at inventory time) are protected and remain in `scripts/__pycache__/`; the directory itself therefore remains until the concurrent-job window has passed.

## Documentation additions and edits

- Add `scripts/README.md`, `models/README.md`, and `renders/astra/README.md`.
- Add one campaign `README.md` to each script archive directory.
- Add a short `Where things are` section to the root `README.md`.
- Rewrite moved foundation-report links and the retained likeness-report links so all local Markdown targets resolve.
- Run the same link checker after all moves and record the final result here before commit.

## Final result

Applied on 2026-09-27 after re-validating the live tree.

- Revalidation found all 130 initial script candidates (592,990 bytes), all 46 model archive candidates (5,550,567,300 bytes), and all 487 initially listed character-evidence candidates (461,425,967 bytes) at the recorded paths and byte totals. None was newer than two hours when touched.
- A post-move dependency audit found five candidate scripts imported directly by untouched live pipelines. Those shared runtime modules were retained at `scripts/`; archiving them would have broken Meshy validation, a live move metric, and retained character utilities.
- Moved the remaining 125 campaign-only files into ten `scripts/archive/<campaign>/` directories, 46 model files into seven `models/archive/<campaign>/` directories, and 516 evidence entries into eight `renders/astra/char2/archive/<campaign>/` directories. The 687 relocated entries total 6,021,962,646 bytes. Tracked files used `git mv`; intentionally untracked assets used plain `mv`.
- Deleted the eight frame/decoded directories listed above only after rechecking their recorded MP4 or contact-sheet proof. Also deleted the two `.DS_Store` files, `models/astra_character_v2.blend1`, and 53 bytecode-cache files. The deletion removed 485 files and freed 331,061,981 bytes. Eighteen bytecode files still inside the two-hour window were retained.
- Added the repository, script, model, render-campaign, and per-script-campaign indexes. Updated the moved foundation report and retained likeness report to resolve their new evidence paths.
- The pre-move local-link check passed with zero broken links. The post-move checker examined 62 Markdown files and 96 local links or images and found 0 broken targets.
- All concurrent-work exclusions remained untouched, including `game/`, `scripts/godot/`, `lifecycle/pending/workflows/`, `CLAUDE.md`, Meshy body i02/i03 work, `rehost_body_i02/`, and the live `astra_body_*` and `astra_meshy_*` scripts.

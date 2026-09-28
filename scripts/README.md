# Script map

## Move authoring

`astra_move_common.py` plus `astra_move_*.py` build, audit, render, and verify the authored combat moves. `astra_armaudit_analyze.py` remains at the top level because a live move metric imports it.

## Rehost

`astra_rehost_*.py` transfers authored moves to the current character while preserving action, rig, grip, and floor checks.

## Meshy head

`astra_meshy_*.py` builds and validates the Meshy head graft. Its shared `astra_likeness_render.py`, `astra_cine_render.py`, and `astra_cine_hero_render.py` runtime dependencies remain at the top level.

## Meshy body

`astra_body_*.py` imports, fits, validates, and rehosts Meshy body candidates. Campaign evidence remains under `renders/astra/char2/` and `renders/astra/rehost_body*/`.

## X-slash

`astra_xslash_*.py` contains the X-slash authoring, naturalness, surface, and clearance checks.

## Hy-Motion

`hymotion_*.py` contains Hy-Motion retarget and render tooling.

## Animation metrics

`anim_*.py` contains shared animation metrics and validation utilities.

## Base asset and archives

Numbered `0*_*.py` scripts remain the reproducible base-asset build pipeline. `astra_character_common.py` remains as a shared dependency for retained character utilities. Superseded one-off campaign scripts are under `scripts/archive/`, with a README in each campaign directory pointing to its report.

# Elden Ring Combat & Game-Feel Reference

**Purpose:** Authoritative combat-tuning reference for the Godwyn boss-fight game (Godot 4). Numbers are pulled from the REAL Elden Ring (base game + Shadow of the Erdtree DLC) rather than guessed, so combat can be calibrated to feel authentic.

**Compiled:** 2026-07-17. Sources: Fextralife wiki, Eldenpedia (wiki.gg), Souls Modding Wiki, soulsmods Paramdex (GitHub param defs), the Elden Ring Frame Data Explorer + its dataset, community frame-data threads, and design-analysis articles.

---

## How to read this document

**Every number is flagged:**

- **EXACT** — from a datamined param dump, a param def (Paramdex/soulsmodding), a wiki data table fed by game params, or documented engine/format behavior.
- **APPROX** — community-measured, rounded, consensus, or measured-from-footage.
- **DERIVED** — computed here from an exact total × a stated threshold.
- **UNKNOWN** — a real param exists but its value is not publicly published; must be read from `regulation.bin`/TAE with Smithbox/DSMapStudio/Yapped/DSAnimStudio, or tuned by feel.

### CRITICAL: the 30fps vs 60fps frame convention (read before touching any frame count)

FromSoftware's animation + i-frame + AI timeline (the TAE format) runs **natively on a 30fps timescale** (30 "frames" = 1 second). The game *renders* at 60fps, but frame-data logic is authored at 30fps.

- Fextralife and most data wikis publish i-frame / cancel / hyperarmor counts on the **30fps scale**.
- To convert to 60fps: **double the frame count** (real-time duration is unchanged).
- Example: a medium roll's 13 i-frames @30fps = **26 i-frames @60fps** = ~433 ms either way.

This single convention is the #1 source of community confusion. **This document tags each frame number with its native scale.** 1 frame @60fps = 16.67 ms; 1 frame @30fps = 33.3 ms.
Source: [Eldenpedia — Invincibility Frames](https://eldenring.wiki.gg/wiki/Invincibility_Frames).

> **Godot note:** We render/tick at 60fps. Store all frame data internally as **60fps frames or as milliseconds** (ms is safest — it's framerate-independent). When you copy a "13 i-frame" number off a wiki, remember it's 30fps and means ~433 ms / 26 of our frames.

---

## 1. Dodge Roll & Backstep

### 1a. Roll i-frames by equip load (30fps native)

| Equip load | Roll type | i-frames (Fextra, 30fps) | i-frames (Eldenpedia, 30fps) | Real time | 60fps equiv | Flag |
|---|---|---|---|---|---|---|
| < 30% | Light / fast | 13 | 14 | ~433–467 ms | ~26–28 | APPROX |
| 30–70% | Medium / normal | 13 | 14 | ~433–467 ms | ~26–28 | APPROX |
| 70–99.9% | Heavy / fat | 12 | 13 | ~400–433 ms | ~24–26 | APPROX |
| ≥ 100% | Overloaded | Cannot roll | Cannot roll | — | — | EXACT (mechanic) |

**Direct answer — medium roll:** **13 i-frames @30fps (Fextralife) / 14 (Eldenpedia)** = ~433–467 ms = **~26 i-frames @60fps**. Light and medium rolls have the **same** i-frame count; heavy is 1 fewer.

**On which frame do i-frames start/end?** Invulnerability begins essentially on the **first active frame** (frame ~1–2) and runs continuously for the count above, followed by a vulnerable recovery tail. The **exact TAE invulnerability start/end indices are UNKNOWN** from accessible sources — the ±1 wiki discrepancy (13/13/12 vs 14/14/13) is an inclusive-vs-exclusive boundary-counting convention, not a gameplay difference. Both wikis are flagged **APPROX** (neither is a raw TAE dump).

Sources: [Fextralife — Equip Load](https://eldenring.wiki.fextralife.com/Equip+Load), [Fextralife — Dodging](https://eldenring.wiki.fextralife.com/Dodging), [Eldenpedia — Invincibility Frames](https://eldenring.wiki.gg/wiki/Invincibility_Frames), [ScreenRant I-Frame Guide](https://screenrant.com/elden-ring-invincibility-iframe-guide/).

### 1b. Roll timing decomposition — startup / active / recovery (30fps)

| Equip load | Startup | i-frame (active-invuln) window | Recovery (vulnerable tail) | Total ≈ | Flag |
|---|---|---|---|---|---|
| Light / Medium | ~0–1 f | ~13–14 f | **8 f** (~233 ms) | ~21–22 f (~700 ms) | APPROX |
| Heavy | ~0–1 f | ~12–13 f | **16 f** (~533 ms) | ~28–29 f (~933 ms) | APPROX |

The key differentiator is **recovery**: the heavy roll's vulnerable tail is **double** light/medium (16 vs 8 frames) — this is why fat-rolling feels punishing even though its i-frame count is only 1 lower. Startup is near-zero (invuln begins almost immediately). Totals are DERIVED (invuln + recovery); wikis don't publish a single "total animation" figure.
Source: [Fextralife — Equip Load](https://eldenring.wiki.fextralife.com/Equip+Load).

### 1c. Roll & backstep stamina + backstep i-frames

| Property | Value | Flag |
|---|---|---|
| Dodge roll stamina cost | **12** (flat, independent of equip load) | EXACT |
| Backstep stamina cost | **12** (same as roll) | EXACT |
| Backstep i-frames (vanilla, no talisman) | **0 — none by default** | EXACT (mechanic) |
| Backstep i-frames WITH Fine Crucible Feather Talisman | 7 (most light/paired) / 8 (1H large, 2H) @30fps | APPROX |
| Roll i-frame bonus, Crucible Feather / All Crucibles Talisman | **+3 i-frames** on rolls | APPROX |

The **vanilla backstep has zero invulnerability** — it's a pure spacing tool; a talisman is required to grant any i-frames.
Sources: [Fextralife — Dodging](https://eldenring.wiki.fextralife.com/Dodging), [Eldenpedia — Invincibility Frames](https://eldenring.wiki.gg/wiki/Invincibility_Frames).

### 1d. Related dodge skills (for reference)

| Move | i-frames (30fps) | Notes | Flag |
|---|---|---|---|
| Quickstep (Ash of War) | 13 | recovery ~10 | APPROX |
| Bloodhound's Step | 16 | longer invuln, that's the point | APPROX |

Source: [Fextralife — Dodging](https://eldenring.wiki.fextralife.com/Dodging).

> **Godot note:** Model the roll as a state machine: `startup (~1 frame) → invuln (~26 frames @60fps for light/med, ~24 for heavy) → recovery (~16 frames light/med, ~32 heavy)`. Give the roll a flat 12 stamina cost. Make the **recovery tail** the tuning lever for weight feel, not the i-frame count. Backstep should have **no i-frames** unless we explicitly add a "feather talisman" analog.

---

## 2. Stamina

### 2a. Max stamina & Endurance scaling (EXACT)

| Endurance | Max Stamina | Notes |
|---|---|---|
| 1 (baseline) | **80** | |
| 15 (soft cap 1) | **105** | +25 over the segment |
| 30 (soft cap 2) | **130** | |
| 50 (soft cap 3) | **155** | **practical stamina soft cap** |
| 99 (max) | **170** | returns nearly flat past 50 |

Segment formulas (EXACT, Fextralife):

- END 1–15: `80 + 25·((L−1)/14)` → ~+1.79/level
- END 16–35: `105 + 25·((L−15)/15)` → ~+1.67/level
- END 36–60: `130 + 25·((L−30)/20)` → +1.25/level
- END 61–99: `155 + 15·((L−50)/49)` → ~+0.31/level

After END 50 returns collapse to ~0.3/level. (END 60 is the separate *Equip Load* soft cap, not stamina.)
Sources: [Fextralife — Stamina](https://eldenring.wiki.fextralife.com/Stamina), [Fextralife — Endurance](https://eldenring.wiki.fextralife.com/Endurance).

### 2b. Stamina regeneration — WEAKLY documented / disputed

| Metric | Value | Flag |
|---|---|---|
| Base regen rate | ~45/sec commonly cited; some measurements ~64/sec | **APPROX — disputed** |
| Post-action regen delay | ~0.5–1 s before regen resumes | **APPROX / UNKNOWN** |
| Regen while guarding | sharply reduced; exact multiplier undocumented | **UNKNOWN** |
| Equip Load > 70% | slower recovery | EXACT (qualitative) |
| Green Turtle Talisman | +8/sec | EXACT (item param) |
| Two-Headed Turtle Talisman (SotE) | +10/sec | EXACT (item param) |

FromSoftware never exposed a clean regen number; Fextralife itself flags the gap. **Treat base regen rate, post-action delay, and the guard-regen penalty as unresolved — tune by feel.**
Sources: [Fextralife — Stamina](https://eldenring.wiki.fextralife.com/Stamina), [Fextralife — Green Turtle Talisman](https://eldenring.wiki.fextralife.com/Green+Turtle+Talisman).

### 2c. Stamina cost of actions

| Action | Stamina cost | Flag |
|---|---|---|
| Roll / dodge / backstep | **12** (fixed) | EXACT |
| Light attack (R1) | weapon-class dependent; no single constant | weapon-dependent |
| Heavy attack (R2) | weapon-class dependent, **> that weapon's R1** | weapon-dependent |
| Jump attack | weapon-class dependent, roughly ≥ R2 | APPROX |
| Sprint | drains per-second **only in combat** (free out of combat) | EXACT (qualitative) |
| Guarding a hit | see 2d (formula) | EXACT (formula) |

Attack costs are stored **per-weapon/per-attack** in behavior params, not as global constants — no clean public table exists. Qualitative facts (EXACT): R1 always costs less than R2 of the same weapon; heavier weapon classes cost more.
Sources: [Fextralife — Stamina](https://eldenring.wiki.fextralife.com/Stamina), [Fextralife — Attacking](https://eldenring.wiki.fextralife.com/Attacking).

### 2d. Stamina damage on block (guard stability) — EXACT formula

```
Stamina lost on block = (attack's atkStam value) × (1 − GuardBoost%)
```

Governing param fields (EXACT, Souls Modding Wiki AtkParam):

| Field | Meaning |
|---|---|
| `atkStam` (u16) | base stamina-attack value of the incoming hit |
| `atkStamCorrection` (f32) | multiplier on atkStam |
| `disableStaminaAttack` (u8) | if ON, no stamina damage when guarded |
| `guardStaminaCutRate` (s16) | guard-side stamina-damage reduction |

Worked examples (EXACT, Fextralife): a +0 Dagger (Guard Boost 15) blocking a 100-stamina hit → `100×(1−0.15) = 85` lost. A +0 Brass Shield (Guard Boost 61) → `100×(1−0.61) = 39` lost. The Scholar's Shield ash gives −35% stamina on block. **Guard break:** if a blocked hit drains all remaining stamina, no extra HP damage is taken but you're stunned and open to a critical.
Sources: [Souls Modding Wiki — AtkParam](https://www.soulsmodding.com/doku.php?id=des-refmat:param:atkparam), [Fextralife — Guarding](https://eldenring.wiki.fextralife.com/Guarding), [Fandom — Guard Boost](https://eldenring.fandom.com/wiki/Guard_Boost).

> **Godot note:** Set base stamina ~80–170 depending on how much we want to reward an "endurance" stat. Roll = flat 12. Model attack cost as a **tunable per-weapon-class constant** scaling from ~12 (dagger) up to ~2–3× (colossal). Blocking: give each incoming attack an `atkStam` value and each shield a `guard_boost` %; lost stamina = `atkStam × (1 − guard_boost)`. When stamina hits 0 on a block → guard break → open to a critical.

---

## 3. Poise & Stagger (two separate systems)

Poise (player-side hitstun resistance) and Stance (enemy-side stagger bar) are **distinct systems** backed by **distinct param fields**. Do not conflate them.

| System | Player field | Enemy field (Paramdex def) |
|---|---|---|
| **Poise** — resist flinching while acting; hyperarmor | displayed Poise stat | `toughness` (強靭度) |
| **Stance** — the bar you break for a riposte | (player has one too, minor) | `superArmorDurability` (SA耐久力) |

Sources: [Paramdex NpcParam.xml](https://raw.githubusercontent.com/soulsmods/Paramdex/master/ER/Defs/NpcParam.xml).

### 3a. Player poise model (ER-specific — differs from DS3)

Elden Ring **replaced DS3's passive-multiplier poise** with a **depleting "poise HP" pool + a stagger threshold** (closer to Sekiro's posture). Each incoming attack deals a discrete poise-damage number subtracted from your poise HP; when it reaches 0 you are **staggered** and poise HP **resets to max**. Overflow damage does **not** carry.

| Fact | Value | Flag |
|---|---|---|
| Player max poise HP | = displayed Poise stat (1:1) | APPROX |
| Stagger threshold | poise HP hits 0 | EXACT (mechanic) |
| Overflow on stagger | does not carry over | EXACT |
| Poise reset (no hit taken) | fully resets after **30 s** | APPROX |
| Internal "Toughness" engine field | = displayed Poise ÷ 10 | EXACT (engine-derived) |
| Enemy attacks are quantized | "practically all deal 50, 100, or higher" | APPROX |

Player poise does **not** gradually regen mid-combat; in active combat it's effectively only restored by a stagger reset (or after 30 s of not being hit).
Sources: [Fextralife — Poise](https://eldenring.wiki.fextralife.com/Poise), [Eldenpedia — Poise](https://eldenring.wiki.gg/wiki/Poise), [ScreenRant — Poise/Super Armor](https://screenrant.com/elden-rings-poise-super-armor-mechanics-guide/).

> **Scale caveat (avoid this trap):** Datamined **PvP weapon poise-damage tables** use a ×10 scale (e.g. Longsword R1 ≈ 110, Greatswords ≈ 229, Colossal Swords ≈ 504) measured against the internal ×10 pool. On the *displayed-stat* scale a Longsword R1 is ~11. Do **not** mix the two scales. PvP table (EXACT, datamined patch 1.13): [aoeah 1.13 spreadsheet](https://www.aoeah.com/news/3406--elden-ring-113-poise-damage-breakpoints-spreadsheet-2024-for-pvp-and-pve).

### 3b. Hyperarmor (active poise)

Two forms of poise:

- **Passive poise** — flat pool from armor, always on.
- **Active poise / hyperarmor** — a bonus added to your poise pool **only during specific attack/skill frames**, letting heavy weapons trade through hits.

Heavy weapons, charged attacks, jump attacks, and colossal weapons carry the strongest hyperarmor; light R1s (daggers/straight swords) have none. **Status procs (Bleed, Frost, Madness, Sleep) and grab attacks bypass hyperarmor entirely.**

**HA frame windows are EXACT and per-animation** — read from the Frame Data Explorer dataset as explicit `hyperArmour: [start, end]` ranges (30fps timeline):

| Animation | HA window (frames, 30fps) |
|---|---|
| Jump attack `202040` | **[0, 69]** (HA from frame 0) |
| Flaming Strike `006000` | [0, 191] |
| Wild Strikes heavy finisher | [0, 61] |
| `004260` | [40, 43] (narrow mid-swing band) |
| `005400`–`005430` | [59, 61] |

**Pattern (EXACT):** big committed attacks (jump, colossal, many Ashes of War) get HA **from frame 0** through most of the swing; some attacks get HA only in a **narrow band** right around the hitbox. It is per-animation, not a global rule.

**Honest gap:** the exact per-animation **poise-absorption multiplier** (the "weapon poise × N" constant that decides how much incoming poise damage HA eats) is **community lore, not confirmed from any param field** — treat any exact multiplier as UNVERIFIED. The mechanism is confirmed (HA adds a temporary bonus stacked with armor poise for the stagger check, and restores some poise HP while active); the constant is not.
Sources: [Eldenpedia — Hyper Armor](https://eldenring.wiki.gg/wiki/Hyper_Armor), [ScreenRant](https://screenrant.com/elden-rings-poise-super-armor-mechanics-guide/), [Frame Data dataset](https://github.com/sovietspaceship/elden-ring-frame-data-explorer-data).

### 3c. Armor poise values (full 4-piece sets) — EXACT

| Armor set | Poise | Weight | Notes |
|---|---|---|---|
| Bull-Goat (highest) | **100** (99.99) | 63.0 | poise king |
| Verdigris (SotE) | ~100 | 61.6 | |
| Fire Prelate | 96 | 58.8 | |
| Omen | 91 | 55.0 | |
| Lionel's | 86 | 50.5 | |
| Veteran's | 80 | 45.0 | |
| Banished Knight | 72 | 41.6 | best poise-to-weight tier |
| Scaled | 71 | 38.0 | best poise-to-weight tier |
| Crucible Axe/Tree | 71 | 36.9 | best poise-to-weight tier |
| Cleanrot | 58 | 35.7 | |
| Carian Knight | 40 | 25.1 | |
| No armor | 0 | 0 | |

Source: [Fextralife — Armor Sets Comparison Table](https://eldenring.wiki.fextralife.com/Armor+Sets+Comparison+Table).

### 3d. Poise breakpoints (practical, all APPROX)

| Poise | What it buys |
|---|---|
| **51** | Tank one standard (~50) hit — baseline PvE target |
| **61** | Medium-weapon trades, small margin — recommended melee floor |
| **71 (~76)** | PvP pressure resistance |
| **101** | Survive two standard hits / one ~100 strong hit — strong PvE target |
| **125+** | Colossal-weapon tanking |

Consensus: **51 = minimum useful PvE, 61+ recommended for melee, 101 = strong.** Higher PvP breakpoints (109/133/192) are testing-dependent and openly disputed.
Sources: [Eldenpedia — Poise](https://eldenring.wiki.gg/wiki/Poise), [Zosygo — Poise breakpoints](https://www.zosygo.com/elden-ring/walkthroughs/poise-explained).

### 3e. Enemy / boss Stance (stagger) system

Every hit deals hidden **stance damage** to `superArmorDurability`, separate from HP damage and **not proportional** to damage dealt. Deplete the stance bar → boss kneels with a glowing weak point → press the critical/riposte input.

| Aspect | Value / behavior | Flag |
|---|---|---|
| Governing field | `superArmorDurability` (stance pool) — separate from `toughness` (poise) | EXACT (def) |
| Reset delay mechanism | global `baseToughnessRecoverTime` × per-boss `superArmorRecoverCorrection` | EXACT (def) |
| Reset delay (community feel) | begins refilling after **~6 s** without a hit, then refills fast | APPROX |
| Refill rate (community) | ~13 points/sec (from Malenia writeups) | APPROX |
| Reset delay range across bosses | ~6 s (~80 poise) → ~15 s (~200 poise) | APPROX |
| Co-op modifier | bosses take **40% less stance damage** when you have a summon | APPROX |
| Riposte triggers | stance break, parry (guard break), backstab (most large bosses immune) | EXACT (mechanic) |

**Stance-break (staggered) window duration:** **UNKNOWN / not publicly datamined.** No authoritative frame count exists for how long a boss stays open. Community guidance is only qualitative ("wait until fully kneeling before pressing the critical or you'll miss it"). Concrete SotE data point: Promised Consort Radahn's stagger/critical window is community-cited at **~6 s vs the usual ~10 s** (APPROX).

Sources: [Fextralife — Stance](https://eldenring.wiki.fextralife.com/Stance), [Paramdex NpcParam.xml](https://raw.githubusercontent.com/soulsmods/Paramdex/master/ER/Defs/NpcParam.xml), [Paramdex GameSystemCommonParam.xml](https://raw.githubusercontent.com/soulsmods/Paramdex/master/ER/Defs/GameSystemCommonParam.xml), [exputer SotE difficulty](https://exputer.com/features/elden-ring-shadow-of-the-erdtree-is-difficult/).

**Per-boss stance values — HONEST STATUS:** There is **no clean public per-boss stance CSV**. The only mainstream-wiki specific number is Malenia (below). All others require reading current-patch `regulation.bin` → NpcParam → `superArmorDurability` in DSMapStudio/Yapped. The "most bosses ~50–200 poise" range is a community characterization, not a dump — **APPROX**.

| Boss | Value | Flag |
|---|---|---|
| Malenia (both phases) | **80 poise**, **3 parries** to break | APPROX (wiki-measured) |
| Margit | "higher poise, recovers faster" (no number) | UNKNOWN (qualitative) |
| All others (Godrick, Radahn, Maliketh, Messmer, Rellana, Consort Radahn, …) | not publicly published | UNKNOWN |

Source: [Fextralife — Malenia](https://eldenring.wiki.fextralife.com/Malenia+Blade+of+Miquella).

### 3f. Player-attack stance/poise damage (all community-measured, APPROX)

FromSoft publishes no official per-attack stance-damage data. `atkSuperArmor` ("Poise damage") × `atkSuperArmorCorrection` is the driving param, but the values live in binary.

| Attack type | Stance damage (approx range) | Notes |
|---|---|---|
| Light attack (R1) | 3–18 | +30% when two-handing light attacks |
| Charged heavy (charged R2) | 12–42 | highest per-hit alongside guard counters |
| Jumping heavy attack | 12–33 | meta stance tool |
| Guard counter | 18–42 | meta stance tool |

Charged-heavy values by class (community-datamined, APPROX): Colossal Hammer 42, Colossal 36, Greatsword 33, Straight Sword 30, Dagger/Claw 18. **Jump attacks and guard counters are the two highest-value stance tools** — that's why they're the stance-break meta. Blood Loss / Frost / Sleep / Madness procs stagger through poise regardless.
Sources: [Fextralife — Stance](https://eldenring.wiki.fextralife.com/Stance), [soulsmodding AtkParam](http://soulsmodding.wikidot.com/param:atkparam).

> **Godot note:** Give each enemy/boss two separate bars: **poise/toughness** (resist flinch mid-attack — mostly invisible) and **stance/superArmorDurability** (the visible "break me for a riposte" bar). Stance damage is per-attack-type, **not** proportional to HP damage — charged heavies, jump attacks, and guard counters deal the most. On stance break: kneel → open a critical window (start with ~3 s and tune; the real window is unpublished). Reset the stance bar after ~6 s of not being hit, refilling at a fast rate. If we add co-op/summons, apply the −40% stance modifier.

---

## 4. Flasks

### 4a. Flask of Crimson Tears (HP) — **flat HP, not percentage** (EXACT)

Values from [Fextralife — Flask of Crimson Tears](https://eldenring.wiki.fextralife.com/Flask+of+Crimson+Tears). "Standard" = base; seed columns add the Crimson Seed / Crimson Seed +1 talismans.

| Upgrade | Standard | + Crimson Seed | + Crimson Seed +1 |
|---|---|---|---|
| +0 | 250 | 300 | 325 |
| +1 | 345 | 414 | 448 |
| +2 | 430 | 516 | 559 |
| +3 | 505 | 606 | 656 |
| +4 | 570 | 684 | 741 |
| +5 | 625 | 750 | 812 |
| +6 | 670 | 804 | 871 |
| +7 | 700 | 840 | 910 |
| +8 | 730 | 876 | 949 |
| +9 | 755 | 906 | 981 |
| +10 | 780 | 936 | 1014 |
| +11 | 795 | 954 | 1033 |
| +12 (max) | 810 | 972 | 1053 |

Diminishing returns are clear: +0→+1 = +95 HP; the last two upgrades = +15 HP each. Sacred Tears raise the heal amount (each upgrade costs 1); Golden Seeds add flask *charges*.

### 4b. Flask of Cerulean Tears (FP) — flat FP (EXACT)

| Upgrade | +0 | +1 | +2 | +3 | +4 | +5 | +6 | +7 | +8 | +9 | +10 | +11 | +12 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| FP | 80 | 95 | 110 | 125 | 140 | 150 | 160 | 170 | 180 | 190 | 200 | 210 | 220 |

Source: [Fextralife — Flask of Cerulean Tears](https://eldenring.wiki.fextralife.com/Flask+of+Cerulean+Tears). From +4 onward each upgrade adds +10 FP.

### 4c. Flask animation duration — APPROX / not frame-documented

No source gives a clean frame count. Best available estimate: **~3 seconds total** — roughly ~1 s to raise the flask, ~1 s for HP to actually restore, ~1 s to holster. **HP applies partway through the animation, not instantly on press.** The Crimson (HP) drink is faster than the Cerulean. This is unconfirmed community estimation — **frame-count footage if exactness matters.**
Sources: [Fextralife forum comment](https://eldenring.wiki.fextralife.com/Flask+of+Crimson+Tears), [The Gamer — enemies attack before you heal](https://www.thegamer.com/elden-ring-enemies-attack-before-use-healing-flask/).

> **Godot note:** Heal is a **flat amount**, not a %. Use ~3 s (~180 frames @60fps) for the drink animation and apply the heal **mid-animation** (~50–60% through), not on button press — this is what makes healing riskable and lets bosses punish it. Bosses react to the heal *animation start* (see §6), so healing must be a committed, punishable action.

---

## 5. Attack Frame Data Structure

Every swing decomposes as **startup / windup** (no hitbox) → **active** (hitbox live) → **recovery / endlag** (cancelable per the windows in 5c).

### 5a. Startup / active / recovery by weapon class (mostly APPROX @60fps)

The offline frame-data bundle leaves active-hitbox arrays empty; exact per-weapon triples come from the live [Frame Data Explorer](https://er-frame-data.nyasu.business/) and community counts.

| Weapon class | Attack | Startup → first active | Active | Recovery | Flag |
|---|---|---|---|---|---|
| Dagger | 1h R1 | ~11–13 f | ~2–4 f | fastest in game | APPROX |
| Straight Sword | 1h R1 | ~13–16 f | ~3–5 f | short | APPROX |
| Straight Sword | 1h R2 (uncharged) | ~22–28 f | ~4 f | medium | APPROX |
| Greatsword | 2h R1 | ~20–26 f | ~4–6 f | long | APPROX |
| Greatsword | charged R2 | ~30 f+ (+ fixed charge hold) | — | very long | APPROX |
| Colossal Sword / Weapon | R1/R2 | ~30–45 f+ | ~4–8 f | very long | APPROX |

(All @60fps, from [er-frame-data.nyasu.business](https://er-frame-data.nyasu.business/).)

**Parry frame data is cleanly EXACT @60fps** for contrast: standard parry startup **8 f**, active **4–10 f** (daggers 8 active, medium shields 4); Golden Parry 8/6; Carian Retaliation 8/12.
Source: [Steam — Parry Frame Data 1.16 (60FPS)](https://steamcommunity.com/sharedfiles/filedetails/?id=3360984277).

### 5b. Hyperarmor on heavy attacks

See §3b for the full treatment. Summary: HA is a per-animation `[start, end]` window (30fps). Heavy attacks, jump attacks, and colossal weapons get HA from frame 0 through most of the swing; light R1s have none. The poise-absorption *multiplier* is unverified.

### 5c. Combo / chain / roll-cancel windows — EXACT (dataset `cancels`, 30fps)

Example: R2 attack animation `030505` (total length 68 frames @30fps), showing the frame each cancel becomes available:

| Cancel type | Available from frame (30fps) | Meaning |
|---|---|---|
| HeavyAttackOnly | **20** | chain into next R2 |
| FastWeaponArt | 20 | Ash of War |
| **Dodge (roll-cancel)** | **22** | earliest roll out of recovery |
| LightAttackOnly | **25** | chain into R1 |
| WeaponArt | 27 | |
| Block / Goods / Magic | 28 | |
| **Move (free walk)** | **31** | recovery fully over |

**Key EXACT takeaways:**

- **Roll-cancel opens before free movement** — you can dodge-cancel at frame 22 but can't just walk until frame 31 (~9 frames @30fps earlier). This is the general roll-cancel feel.
- **Attack-into-attack chaining opens even earlier:** next-R2 at frame 20, next-R1 at frame 25 — chaining a follow-up attack is available *before* rolling, and R2-follow precedes R1-follow.
- Windows are **per-animation**; the ordering (attack-cancel → dodge → move) is consistent, but exact frames vary by weapon.
- You can also **cancel hitstun into a roll** when being combo'd.

Source: [Frame Data dataset (GitHub)](https://github.com/sovietspaceship/elden-ring-frame-data-explorer-data), [err.fandom Combat Mechanics](https://err.fandom.com/wiki/Combat_Mechanics).

### 5d. Input buffer

- **No exact universal base-game frame count is officially published.** Community consensus: the buffer is **large** — inputs pressed a couple frames after the valid window still store and fire on recovery. **APPROX.**
- **Roll-during-stagger buffer (specific):** begins **3–30 frames after the stagger starts, scaling with animation length** (deliberately not accepting the roll at the very start of stagger, to reduce panic-rolls). Documented for the Elden Ring Reforged mod; treat as APPROX for base game.

Sources: [Steam — input buffer thread](https://steamcommunity.com/app/1245620/discussions/0/3183488149023495553/), [err.fandom Combat Mechanics](https://err.fandom.com/wiki/Combat_Mechanics).

> **Godot note:** Recovery is the tuning lever for weapon weight. Structure attacks as `startup → active → recovery`, and expose per-animation cancel frames: **roll-cancel available slightly before free-move**, and **attack-chain cancels available even earlier** (R2-follow before R1-follow). Implement a generous input buffer (~queue the last input for ~150–200 ms and fire it when the cancel window opens) — this is a huge part of why ER feels responsive despite committed animations. Allow **cancelling hitstun into a roll** so players can escape combos.

---

## 6. Boss / Enemy Conventions

### 6a. Boss HP — Base Game (EXACT, base/solo/NG)

All HP is **base, solo, first playthrough**. HP scales up per co-op player and per NG+ cycle.

| Boss | HP | Phase structure | Flag |
|---|---|---|---|
| Margit, the Fell Omen | **4,174** | single bar | EXACT |
| Godrick the Grafted | **6,080** | continuous, no refill | EXACT |
| Rennala, Queen of the Full Moon | **7,590 total** (P1 3,493 + P2 4,097) | two **separate** pools (P1 is an invuln puzzle-gate) | EXACT |
| Starscourge Radahn | **9,572** | continuous, no refill | EXACT |
| Maliketh (w/ Beast Clergyman) | **10,620 total** | one **shared** bar; transforms at 50% (~5,310/5,310) | EXACT total; split DERIVED |
| Godfrey / Hoarah Loux | **21,903** | continuous, no refill | EXACT |
| Malenia, Blade of Miquella | **33,251 total** — P1 18,473, P2 14,778 | two **separate** pools; P2 **refills to 80%** of max; lifesteal on every hit | EXACT |
| Elden Beast | **22,127** | single bar (after Radagon) | EXACT |

Sources: individual Fextralife boss pages (linked in 6c).

### 6b. Boss HP — Shadow of the Erdtree (EXACT, base/solo)

DLC boss base HP is **fixed** — Scadutree Blessing changes *your* damage/defense, not boss HP.

| Boss | HP | Phase structure | Flag |
|---|---|---|---|
| Divine Beast Dancing Lion | **22,571** | single bar | EXACT |
| Rellana, Twin Moon Knight | **29,723** | single bar | EXACT |
| Golden Hippopotamus | **33,866** | single bar | EXACT |
| Messmer the Impaler | **38,981 total** | one **shared** bar; P2 at 50% (~19,490/19,491); serpent + Messmer share the bar, separate hurtboxes | EXACT total; split DERIVED |
| Bayle the Dread | **41,612** | single bar | EXACT |
| Promised Consort Radahn | **46,134 total** | one **continuous** bar; Miquella phase below ~65% HP | EXACT total; split DERIVED |

Sources: Fextralife boss pages ([Dancing Lion](https://eldenring.wiki.fextralife.com/Divine+Beast+Dancing+Lion), [Rellana](https://eldenring.wiki.fextralife.com/Rellana+Twin+Moon+Knight), [Golden Hippopotamus](https://eldenring.wiki.fextralife.com/Golden+Hippopotamus), [Messmer](https://eldenring.wiki.fextralife.com/Messmer+the+Impaler), [Bayle](https://eldenring.wiki.fextralife.com/Bayle+The+Dread), [Promised Consort Radahn](https://eldenring.wiki.fextralife.com/Promised+Consort+Radahn)).

*Note:* an older community split for Consort Radahn ("35k + 22k") is superseded by the current Fextralife total of 46,134 — treat the old split as APPROX/superseded. HP numbers trace to Fextralife combat-info boxes (fed by game params); a second-source check against a raw param CSV is the recommended next step if you want belt-and-suspenders verification.

### 6c. Multi-phase HP — the load-bearing design fact

**The dominant ER convention is a single CONTINUOUS health bar across phases** — the phase-2 cutscene is theatrical, but accumulated damage carries over. **Do NOT reset HP on phase transition by default.**

- **Malenia is the headline exception — an 80% refill, NOT 100%.** After her first bar depletes she heals to ~80% of max and enters phase 2 (Goddess of Rot). She also has **lifesteal on every hit, including blocked hits** — this (plus the refill) is why her effective HP exceeds 33,251. [EXACT — "80%" stated verbatim]. [Fextralife — Malenia](https://eldenring.wiki.fextralife.com/Malenia+Blade+of+Miquella), [GamesRadar](https://www.gamesradar.com/elden-ring-malenia-boss-fight-how-to-beat-blade-miquella-goddess-rot/).
- **Rennala ≠ Malenia:** her two "bars" are separate pools because P1 is an invulnerability puzzle (kill glowing scholars), not a refill. [Fextralife — Rennala](https://eldenring.wiki.fextralife.com/Rennala+Queen+of+the+Full+Moon).
- **Godfrey → Hoarah Loux, Radahn, Godrick, Maliketh, Messmer, Consort Radahn:** all continuous/shared, **no refill**. [Godfrey](https://eldenring.wiki.fextralife.com/Godfrey,+First+Elden+Lord), [Maliketh/Beast Clergyman](https://eldenring.wiki.fextralife.com/Beast+Clergyman), [Messmer](https://eldenring.wiki.fextralife.com/Messmer+the+Impaler), [Consort Radahn](https://eldenring.wiki.fextralife.com/Promised+Consort+Radahn).

### 6d. Punish windows / attack recovery

- **The "1–2 hits then roll away" meta:** SotE deliberately gives bosses short punish windows + large AOEs (partly to counter Spirit Summons); if a boss's first combo hit lands, the follow-up chain is "almost impossible to dodge." [APPROX — design analysis]. [exputer](https://exputer.com/features/elden-ring-shadow-of-the-erdtree-is-difficult/).
- **Concrete SotE tightening:** Promised Consort Radahn's stagger/critical window is community-cited at **~6 s vs the usual ~10 s**. [APPROX].
- **UNKNOWN:** authoritative exact recovery-frame counts ("N light attacks per window") were not found in a reputable technical source. Any specific count needs param confirmation.

### 6e. Aggression / attack-string design (SotE philosophy)

- **Malenia — Waterfowl Dance:** leaps up, hovers ~1–2 s, then a multi-lunge flurry Fextralife describes as "four consecutive lunges" (community: "three strokes + a phantom fourth"). First available below 75% HP; in P2 also applies Scarlet Rot. The phantom stroke catches early punishes. The reliable counter is **distance or running *into* her** (exploiting the commit point, §7/§8), not out-i-framing. [EXACT for four-lunge/75%; APPROX dodge timing]. [Fextralife — Waterfowl Dance](https://eldenring.wiki.fextralife.com/Waterfowl+Dance).
- **Messmer / SotE philosophy:** long medium-range combos, quick movement, minimal gaps between strings; correct play is to dodge the *entire* string and attack only after it finishes. [APPROX]. [Mobalytics — Messmer](https://mobalytics.gg/blog/elden-ring/messmer-guide/).
- **Delayed/staggered attacks to bait rolls:** a core ER pattern (heavy in SotE) — deliberately delayed timings punish the panic-roll during roll recovery. [APPROX — design consensus].
- **Input reading (honestly disputed):** consensus is **animation-flag reaction, not literal input reading** — the AI responds within a few frames of your heal/cast *animation starting*, before it's fully visible. Functionally similar to input reading, mechanically distinct. [APPROX — contested]. [ResetEra](https://www.resetera.com/threads/does-elden-ring-have-input-reading-its-complicated.623839/).

> **Godot note:** Default to a **single continuous HP bar** across phases — never silently refill on phase 2. If we want a Malenia-style "second wind," use an explicit **80% refill** (not 100%) and telegraph it. Design boss combos as **long strings with a short punish window at the end** (aim for the ~1–2-hit-then-roll rhythm), and add **delayed/variable-timing attacks** to punish panic rolls. Have the boss react to the player's **heal-animation start** (a few frames in), not to the button press, so healing is genuinely committing.

---

## 7. Camera / Lock-On

All EXACT values below come from the datamined `LockCamParam` def.

| Property | Value | Flag |
|---|---|---|
| Lock-on max radius | **15 m** (`chrLockRangeMaxRadius`) | EXACT |
| Camera distance from target (locked) | **4 m** (`camDistTarget`) | EXACT |
| Lock keep-alive after conditions fail | **2 s** (`lockTgtKeepTime`) — held ~2 s after target leaves range / breaks line-of-sight before dropping | EXACT |
| Camera pitch min | −40° (`rotRangeMinX`) | EXACT |
| Vertical FOV | 43° (`camFovY`) | EXACT |
| Focus-point height offset | 1.42 m (`chrOrgOffset_Y`) | EXACT |
| Per-enemy override | big bosses use `NpcParam.lockCameraParamId` for bigger radius / different camera row (per-boss values UNKNOWN) | EXACT (mechanism) |

**There is no separate larger "unlock distance"** — it's one radius + a 2 s grace, not dual radii.

**Target switching:** flick the right stick left/right; next-target selection is **screen-space directional** (flick direction picks the next on-screen candidate), not strictly world-nearest. The exact algorithm/deadzone is community-inferred, not param-exposed. [APPROX].

**Hard-lock vs soft-lock:** *hard-lock* = manual lock-on (`LockCamParam` state); *soft-lock* = the no-lock auto-assist that orients unlocked melee toward a nearby enemy, governed by the `close*` capture-cone fields (`closeMaxRadius`, `closeAngRange`, `closeMaxHeight/MinHeight`).

**Large-boss camera problems:** the camera clips into huge models (Bayle, Ulcerated Tree Spirit, Dancing Lion cited as worst); lock-on can target an unreachable point causing melee whiffs; the expert workaround is to fight large melee bosses **unlocked**. [APPROX — well-documented].

Sources: [Paramdex LockCamParam.xml](https://raw.githubusercontent.com/soulsmods/Paramdex/master/ER/Defs/LockCamParam.xml), [Paramdex NpcParam.xml](https://raw.githubusercontent.com/soulsmods/Paramdex/master/ER/Defs/NpcParam.xml), [GameRant — lock-on](https://gamerant.com/elden-ring-camera-lock-onto-enemies/), [Steam — large-boss camera](https://steamcommunity.com/app/1245620/discussions/0/6982351509014127458/).

> **Godot note:** Lock-on radius ~15 m, camera ~4 m behind target, hold lock for ~2 s after the target leaves range/LoS before dropping. Right-stick flick switches to the next **on-screen** target in the flick direction. Allow a per-boss lock radius/camera override for large bosses. Consider raising the camera focus point / pulling back for very large bosses to mitigate the classic ER large-boss camera clip.

---

## 8. Hit Feedback

### 8a. Hitstop / hitlag

**Hitstop is a real per-attack param:** `AtkParam.hitStopTime` ("Hit stop time [s]"). Every swing/boss attack is its own AtkParam row, so hitstop is authored **per-attack** — this is *why* colossal weapons feel heavier than daggers. It briefly pauses both attacker and victim on a landed hit. [EXACT mechanism]. Exact seconds per weapon class are **UNKNOWN** (binary — read via Smithbox/Yapped or tune by feel).

### 8b. Knockback

**Knockback is a per-attack meters value:** `AtkParam.knockbackDist` ("Knockback distance [m]") — distance the victim travels if stunned, or the attacker recoils if not. Values UNKNOWN (binary). The reaction animation is chosen by the `dmgLevel` (Damage Level) enum, separate from poise damage; enemies can be immune to low damage levels.

### 8c. Attack tracking — the load-bearing boss-feel topic

**Tracking is authored per-attack on the animation timeline** via **TAE event Type 224 "Character Rotation Speed"**: it "sets the rotation speed of the character for the duration of the event. Once the event ends the character returns to default rotation speed." Parameter `RotationSpeed` (f32; unit possibly degrees/second, unconfirmed). **Type 232** handles vertical aiming/pitch. There is no global homing setting — horizontal tracking is default face-target logic gated/scaled by Type-224 windows. [EXACT — documented format behavior].

**The commit point = when the Type-224 rotation window ends.** The character then reverts to its slow default turn rate, so the swing follows a largely fixed trajectory through its active frames. **This is the "commit."**

- **Exploit that follows from the mechanism:** roll *late* / roll *into* the boss so it commits its swing to where you *were* — delayed windups are a timing test, not a walk-out test. [APPROX].
- **SotE "strong tracking" feel** is a strong community *perception* corroborated across many threads, but **there is NO datamined proof SotE globally raised rotation-speed values vs base game.** [APPROX / disputed].
- **UNKNOWN:** no published table of per-boss/per-attack rotation-speed values exists — anyone quoting a specific deg/s is estimating. Read Type-224 values per animation in DSAnimStudio if you need them.

Sources: [soulsmodding AtkParam](http://soulsmodding.wikidot.com/param:atkparam), [soulsmodding TAE format](https://www.soulsmodding.com/doku.php?id=format:tae), [Steam — tracking/commit discussion](https://steamcommunity.com/app/1245620/discussions/0/3183487463214418277/).

> **Godot note (this is the most important section for boss feel):** Model attack **tracking as a per-attack window** — the boss turns to face the player rapidly during the **windup**, then **commits** (locks its facing/trajectory) partway through the swing, so a late roll *into* or *around* the boss dodges it. Do NOT let attacks home in during active frames. Add per-attack **hitstop** (freeze both actors a few frames on a landed hit — more for heavy weapons) and per-attack **knockback distance**. This windup-tracking-then-commit model, plus delayed attack timings, is what makes ER combat feel like a reaction/timing duel rather than a walk-out-of-range dance.

---

## 9. General / Load-bearing feel notes

| Topic | Value / rule | Flag |
|---|---|---|
| Frame rate the game is balanced at | **60 fps rendered; 30 fps native TAE/frame-data timeline** | EXACT |
| Input buffer | large / generous (~150–200 ms feel); no official exact count | APPROX |
| Roll-cancel | available slightly **before** free movement resumes (see §5c) | EXACT (per-animation) |
| Attack-chain cancel | available **earlier** than roll-cancel (R2-follow before R1-follow) | EXACT (per-animation) |
| Hitstun → roll cancel | you can cancel being-combo'd hitstun into a roll (buffered 3–30 f into stagger) | APPROX |
| Attack tracking | per-attack windup tracking → commit point (§8c) | EXACT (mechanism) |
| Healing | flat amount, applied mid-animation, punishable, boss reacts to animation start | EXACT/APPROX |

### The short list of what makes it *feel* like Elden Ring

1. **Committed animations + generous buffering + early cancel windows.** Actions commit, but a big input buffer and roll/attack cancel windows keep it responsive.
2. **Roll i-frames as a timing test, not a get-out-of-jail.** ~26 i-frames @60fps (light/med), meaningful recovery tail, and bosses whose attacks **track during windup then commit** — so you dodge *into/through* attacks on reaction.
3. **Two separate stagger economies.** Player poise-HP (flinch resistance, resets on stagger / after 30 s) and enemy stance (break for a riposte, resets ~6 s after last hit). Stance damage is per-attack-type, not proportional to HP damage.
4. **Continuous boss HP across phases** (Malenia's 80% refill is the rare, telegraphed exception).
5. **Per-attack hitstop + knockback + delayed timings** for weight and mind-games.

---

## 10. Honest gaps — do NOT fabricate these; read params or tune by feel

1. **Exact TAE roll invulnerability start/end frame indices** — UNKNOWN (±1 wiki discrepancy is boundary-counting).
2. **Base stamina regen rate** (~45 vs ~64/sec), **post-action regen delay**, and **guard-regen penalty** — disputed/UNKNOWN.
3. **Per-swing R1/R2/jump attack stamina constants** — weapon-class-specific in params, no clean public table.
4. **Per-animation hyperarmor poise-absorption multiplier** — mechanism confirmed, constant unverified.
5. **Per-boss stance (`superArmorDurability`) values** for every boss except Malenia's poise (80) — UNKNOWN; read `regulation.bin` → NpcParam.
6. **Stance-break/riposte window duration in frames** — UNKNOWN (Consort Radahn ~6 s, standard ~10 s are the only APPROX anchors).
7. **Per-attack `hitStopTime`, `knockbackDist`, and tracking deg/s values** — exist as params, values in binary; read via Smithbox/Yapped/DSAnimStudio.
8. **Target-switch selection algorithm + deadzone** — community-inferred, not param-exposed.
9. **Flask animation exact frames** — ~3 s estimate; frame-count footage if needed.
10. **Exact recovery-frame counts for punish windows** — not found in a reputable technical source.

**Authoritative path for the missing EXACT numbers:** read the current-patch `regulation.bin` (NpcParam / AtkParam / EquipParam) in **DSMapStudio / Smithbox / Yapped**, and per-animation TAE (i-frames, hyperarmor, tracking Type-224, cancels) in **DSAnimStudio**, using the [soulsmods Paramdex](https://github.com/soulsmods/Paramdex) defs. Or frame-count reference footage directly.

---

## Source index

- Fextralife wiki: Dodging, Equip Load, Stamina, Endurance, Guarding, Poise, Stance, Armor Sets Comparison, Flask of Crimson/Cerulean Tears, and individual boss pages (eldenring.wiki.fextralife.com)
- Eldenpedia / wiki.gg: Invincibility Frames, Poise, Hyper Armor (eldenring.wiki.gg)
- Souls Modding Wiki: AtkParam, TAE format (soulsmodding.com / soulsmodding.wikidot.com)
- soulsmods Paramdex (GitHub): NpcParam, LockCamParam, GameSystemCommonParam, SpEffect defs; Frame Data Explorer dataset
- Elden Ring Frame Data Explorer (er-frame-data.nyasu.business) + Steam parry frame-data guide 1.16
- aoeah 1.13 PvP poise-damage spreadsheet
- Design analysis: exputer, Mobalytics, GamesRadar, ScreenRant, Den of Geek, ResetEra, The Gamer, GameRant, Zosygo
- Community: r/Eldenring and Steam discussion threads (flagged APPROX)

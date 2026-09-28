# Meshy clip scout — Godwyn Phase 1

Reviewed 2026-09-28 by the Codex default model through direct inspection of the extracted frames. **107/107 previews fetched and reviewed; 856 required sample frames.** No Blender, SSH, Git, animation downloads, or remote model calls. Network requests were only for catalog-derived preview GIFs. No previous retarget verdict was treated as a source-preview verdict.

## Selection

These are conservative **source-motion candidates**, not production approvals. Grip changes and Godwyn rig/cloth/weapon compatibility remain untested. Up to two candidates are listed per role; empty roles are intentional. A four-score sum never overrides a choreography mismatch.

| SPEC role | Ranked action IDs | Decision |
|---|---|---|
| idle_low_hang | — | No preview establishes the specified active sword grip hanging low at the side with point toward ground; Combat_Stance is a crouched shield guard. |
| stalk_walk | 112 Monster_Walk, 114 Proud_Strut | Compact forward gait, low arms and little flourish; best stalking base, needs sword hand pose. / Broad upright forward steps and restrained low arms; second stalking base, soften swagger and author grip. |
| x_combo | 241 Weapon_Combo_2 | Alternating raised right-hand windups and descending cross-body cuts with steps; strongest X-combo base, needs blade-path confirmation. |
| horizontal_sweep | 242 Charged_Slash | Compact planted waist/chest-level cross-body swing with torso follow-through; best horizontal-sweep base, weapon absent. |
| overhead | 4 Attack, 128 Heavy_Hammer_Swing | Two-handed overhead lift followed by committed downward strike and planted recovery; strong overhead candidate. / Grounded high two-arm windup and deep committed downward strike; second overhead base, hammer grip needs sword adaptation. |
| jump_lunge | — | No clip shows a clear gap-closing jump whose landing is a thrust followed by overshoot continuation. |
| rising_spin | — | No candidate establishes both a rising sword arc and controlled rotation at no more than roughly one revolution per second; roll/spin names are unsafe substitutes. |
| the_pause | — | No complete clip combines low-sword stillness with a sudden offline step; boxing counters and alert pivots do not meet this role. |
| stagger | 179 Hit_Reaction_1, 171 Hit_Reaction_to_Waist | Small planted torso compression and recovery; best restrained stagger, needs armed hand pose. / Clear weighty waist recoil with feet supporting and controlled return; second stagger, adapt boxing arms. |
| death | 8 Dead, 188 Fall_Dead_from_Abdominal_Injury | Knees buckle from armed stance into prone collapse; best death source, raw preview contains no aerial tumble. / Clutches abdomen, sinks to knees and folds onto side; convincing collapse, adapt occupied sword hand. |
| dodge | 157 Stand_Dodge_1, 156 Stand_Dodge | Single bent-knee evasive step with balanced recovery; best dodge base, replace boxing hands with sword carriage. / Compact standing torso slip with low arms and return; second dodge candidate, does not establish an offline step. |

## Important visual findings

- **Attack (4)** visibly performs a grounded overhead strike in the raw preview; the earlier report describing an acrobatic retarget does not describe these source frames. Its denser sheet shows the overhead lift, downward commitment and planted return. It merits a new source-to-rig diagnosis, not reuse of the old retarget.
- **Dead (8)** shows knees buckling into a prone collapse. It is a valid source candidate even though the old character transfer failed geometry checks.
- **Double_Combo_Attack (92)** and **Triple_Combo_Attack (105)** are not obviously inverted tumbling in the raw previews, but their hopping/high-cut choreography still fails the strict vanilla X requirement. Neither is selected.
- **Weapon_Combo_2 (241)** is the strongest alternating descending-cut base. No sword is drawn in that preview: opposite diagonal blade trajectories remain a specific validation requirement. It is not certified as an exact X combo. **Charged_Slash (242)** is likewise an inferred sword sweep from the hand/torso path.
- **Left_Slash (97)** is planted and sword-readable, but the denser sheet shows a raised diagonal cut; it is excluded from the level horizontal-sweep picks. **Rightward_Spin (100)** and all five Roll_Dodge variants visibly tumble and are rejected.
- **Combat_Stance (89)** is stable but its sword sits across a crouched sword-and-shield guard. Strictly applying SPEC section 7 leaves idle_low_hang empty despite its previous acceptance as a placeholder.

## Method and limits

The provided catalog contains 107 IDs, category labels and a preview base URL, but no Fighting group field and no per-clip preview_url field. I reviewed every supplied entry, including all Blocking, Punching, weapon, spell and acting entries, so missing group metadata cannot silently exclude a supplied clip. This proves coverage of the supplied catalog only, not of any larger online library.

URL rule: `https://cdn.meshy.ai/webapp-assets/feature-demo/animation/preview/biped/<Name>.gif`; `_inplace` suffixes would be stripped as directed by the catalog. Every fetch succeeded. PIL extracted indices `round(k*(N-1)/7)`, k=0…7. These are evenly spaced by frame index, not variable GIF delay. Per-GIF durations, hashes, frame counts, indices and URLs are in [manifest.json](meshy_scout_evidence/manifest.json). The 27 overview sheets contain all 856 required frames. Twelve supplementary sheets contain 16 samples each for IDs 4, 97, 92, 105, 99, 199, 241, 238, 221, 89, 112 and 114; all were also inspected.

Eight stills cannot certify every intermediate contact, blade path, transient flip, root translation or peak rotation speed. The extra samples narrow ambiguity but are not continuous playback. Ground contact is a visual inference on a mannequin without a measured ground plane. No claim of the ≤1 rotation/second bound is made from full-clip average duration. No rising-spin pick is made without that evidence. Scouting acceptance does not clear prior rig/geometry failures.

Scores are subjective integers 0–5: **G** grounded/natural support; **B** boss-scale weight/control; **S** readable sword action or compatible armed posture; **R** match to the best relevant requested SPEC role. 0 = incompatible/absent, 1 = poor, 2 = weak, 3 = plausible with substantial adaptation, 4 = strong source candidate with stated limitations, 5 = clear visual match. S remains low for good unarmed walks/reactions/deaths; it does not disqualify these non-attack roles. Grounded death means loss of support into collapse rather than a launch or gymnastic tumble.

## Every reviewed clip

| ID | Name | Category | G | B | S | R | Direct visual judgment | Evidence (8 frames) |
|---:|---|---|---:|---:|---:|---:|---|---|
| 0 | Idle | Idle | 5 | 2 | 0 | 1 | Restless unarmed stance with torso turns; no loaded low sword guard. | [frames](meshy_scout_evidence/0.jpg) |
| 11 | Idle_02 | Idle | 5 | 3 | 1 | 2 | Quiet broad stance but right hand lifted and no low blade silhouette. | [frames](meshy_scout_evidence/11.jpg) |
| 12 | Idle_03 | Idle | 5 | 1 | 0 | 0 | Arms lift and spread in an expressive stretch; reject idle. | [frames](meshy_scout_evidence/12.jpg) |
| 243 | Idle_3 | Idle | 5 | 3 | 1 | 2 | Restrained arms-down neutral; useful pose reference, not demonstrated combat grip. | [frames](meshy_scout_evidence/243.jpg) |
| 244 | Idle_4 | Idle | 5 | 3 | 1 | 2 | Quiet upright breathing stance; lacks armed tension and point-down sword. | [frames](meshy_scout_evidence/244.jpg) |
| 245 | Idle_5 | Idle | 5 | 3 | 1 | 2 | Bent-knee asymmetric ready pose; open hands, no low-hang grip. | [frames](meshy_scout_evidence/245.jpg) |
| 246 | Idle_6 | Idle | 5 | 3 | 1 | 2 | Stable relaxed standing; too passive for loaded combat neutral. | [frames](meshy_scout_evidence/246.jpg) |
| 247 | Idle_7 | Idle | 5 | 3 | 1 | 2 | Restrained weight shift with loose arms; no weapon readiness. | [frames](meshy_scout_evidence/247.jpg) |
| 248 | Idle_8 | Idle | 5 | 2 | 0 | 1 | Crouched fidget and looking about; breaks threatening stillness. | [frames](meshy_scout_evidence/248.jpg) |
| 249 | Idle_9 | Idle | 5 | 3 | 1 | 2 | Static upright neutral; plausible authoring reference only. | [frames](meshy_scout_evidence/249.jpg) |
| 250 | Idle_10 | Idle | 5 | 2 | 0 | 1 | Deep unarmed crouch with hands high; wrong silhouette. | [frames](meshy_scout_evidence/250.jpg) |
| 251 | Idle_11 | Idle | 5 | 3 | 1 | 2 | Arms-down broad neutral, but no identifiable sword grip. | [frames](meshy_scout_evidence/251.jpg) |
| 252 | Idle_12 | Idle | 5 | 3 | 1 | 2 | Upright passive breathing; no loaded guard. | [frames](meshy_scout_evidence/252.jpg) |
| 253 | Idle_13 | Idle | 5 | 2 | 0 | 0 | Repeated conversational hand gestures; reject. | [frames](meshy_scout_evidence/253.jpg) |
| 254 | Idle_14 | Idle | 3 | 1 | 0 | 0 | Hand theatrics and conspicuous lifted knee; reject. | [frames](meshy_scout_evidence/254.jpg) |
| 599 | Idle_15 | Idle | 5 | 1 | 0 | 0 | Wave near face; social idle, not combat. | [frames](meshy_scout_evidence/599.jpg) |
| 89 | Combat_Stance | AttackingwithWeapon | 5 | 3 | 3 | 2 | Stable crouched sword-and-shield guard; blade across waist, not hanging point-down at side. | [frames](meshy_scout_evidence/89.jpg) |
| 85 | Axe_Stance | Transitioning | 5 | 3 | 2 | 1 | Rises from deep crouch into upright polearm hold; not low sword neutral. | [frames](meshy_scout_evidence/85.jpg) |
| 21 | Walk_Fight_Forward | Walking | 4 | 2 | 1 | 1 | Crossing light steps with hands held high at chest; not deliberate low-guard stalking. | [frames](meshy_scout_evidence/21.jpg) |
| 20 | Walk_Fight_Back | Walking | 4 | 2 | 1 | 1 | Backward high-guard shuffle; wrong travel direction and guard. | [frames](meshy_scout_evidence/20.jpg) |
| 546 | Walk_Backward_with_Sword | Walking | 4 | 3 | 2 | 1 | Backward bent-knee steps with arms spread; not forward pursuit. | [frames](meshy_scout_evidence/546.jpg) |
| 560 | Spear_Walk | Walking | 5 | 3 | 2 | 2 | Natural upright stride; ordinary cadence, no threatening sword carriage. | [frames](meshy_scout_evidence/560.jpg) |
| 106 | Confident_Walk | Walking | 5 | 1 | 0 | 0 | Hand-on-hip runway walk with head gesture; reject. | [frames](meshy_scout_evidence/106.jpg) |
| 114 | Proud_Strut | Walking | 5 | 4 | 2 | 4 | Broad upright forward steps and restrained low arms; second stalking base, soften swagger and author grip. | [frames](meshy_scout_evidence/114.jpg) |
| 119 | Slow_Orc_Walk | Walking | 4 | 2 | 0 | 1 | Exaggerated hunch and alternating high elbows; caricatured orc weight. | [frames](meshy_scout_evidence/119.jpg) |
| 112 | Monster_Walk | Walking | 5 | 4 | 2 | 4 | Compact forward gait, low arms and little flourish; best stalking base, needs sword hand pose. | [frames](meshy_scout_evidence/112.jpg) |
| 30 | Casual_Walk | Walking | 5 | 2 | 1 | 2 | Ordinary relaxed walking and arm swing; lacks relentless intent. | [frames](meshy_scout_evidence/30.jpg) |
| 115 | Quick_Walk | Walking | 5 | 2 | 1 | 1 | Brisk narrow stride; too light and hurried. | [frames](meshy_scout_evidence/115.jpg) |
| 543 | Step_Back | Walking | 5 | 3 | 0 | 3 | Short grounded retreat but boxing guard; alternate dodge reference, not stalking. | [frames](meshy_scout_evidence/543.jpg) |
| 575 | Combat_Idle_Turn_Left | TurningAround | 5 | 3 | 0 | 1 | Small planted turn in boxing guard; no sword action. | [frames](meshy_scout_evidence/575.jpg) |
| 580 | Sword_and_Shield_Alert_Turn_Left | TurningAround | 4 | 3 | 3 | 2 | Bent-knee armed quarter turn; utility transition, not requested attack or low guard. | [frames](meshy_scout_evidence/580.jpg) |
| 590 | Sword_and_Shield_Alert_Turn_Right | TurningAround | 4 | 3 | 3 | 2 | Stepping rotation with shield-like off-arm; utility turn, no rising cut. | [frames](meshy_scout_evidence/590.jpg) |
| 574 | Walk_Turn_Left_with_Weapon | TurningAround | 5 | 3 | 2 | 2 | Ordinary walking turn with low arms; no held guard then sudden offline step. | [frames](meshy_scout_evidence/574.jpg) |
| 589 | Alert_Quick_Turn_Right | TurningAround | 5 | 3 | 1 | 2 | Alert pause then pivot in place; no clear offline displacement or low sword grip. | [frames](meshy_scout_evidence/589.jpg) |
| 4 | Attack | AttackingwithWeapon | 5 | 5 | 5 | 5 | Two-handed overhead lift followed by committed downward strike and planted recovery; strong overhead candidate. | [frames](meshy_scout_evidence/4.jpg) |
| 97 | Left_Slash | AttackingwithWeapon | 5 | 4 | 5 | 3 | Grounded sword-and-shield cross-body cut; denser samples show a raised diagonal path, not a clean level chest sweep. | [frames](meshy_scout_evidence/97.jpg) |
| 219 | Right_Hand_Sword_Slash | Punching | 4 | 4 | 4 | 3 | Stepping single cross-body/upward arm arc with high recovery; useful single cut, not two crossing diagonals. | [frames](meshy_scout_evidence/219.jpg) |
| 221 | Charged_Upward_Slash | Punching | 4 | 3 | 3 | 2 | Large backward lean and turning rising arm action; controlled rising sword spin and speed cap not established. | [frames](meshy_scout_evidence/221.jpg) |
| 240 | Thrust_Slash | AttackingwithWeapon | 4 | 3 | 3 | 2 | Extended arm then rotating slash-like sweep; no airborne gap close or landing thrust. | [frames](meshy_scout_evidence/240.jpg) |
| 242 | Charged_Slash | AttackingwithWeapon | 5 | 4 | 4 | 4 | Compact planted waist/chest-level cross-body swing with torso follow-through; best horizontal-sweep base, weapon absent. | [frames](meshy_scout_evidence/242.jpg) |
| 199 | Weapon_Combo | Punching | 4 | 3 | 3 | 2 | Multiple high arm cuts and pivots; exact opposite descending X diagonals not established. | [frames](meshy_scout_evidence/199.jpg) |
| 202 | Weapon_Combo_1 | Punching | 2 | 1 | 3 | 0 | Conspicuous high airborne kick/leap between strikes; reject gymnastics. | [frames](meshy_scout_evidence/202.jpg) |
| 241 | Weapon_Combo_2 | AttackingwithWeapon | 4 | 4 | 4 | 4 | Alternating raised right-hand windups and descending cross-body cuts with steps; strongest X-combo base, needs blade-path confirmation. | [frames](meshy_scout_evidence/241.jpg) |
| 92 | Double_Combo_Attack | AttackingwithWeapon | 3 | 3 | 5 | 2 | Two high cuts with lifted-knee/hopping commitment; does not clearly trace the required opposing X. | [frames](meshy_scout_evidence/92.jpg) |
| 105 | Triple_Combo_Attack | AttackingwithWeapon | 3 | 3 | 5 | 2 | Mixed shield combo with high cut, hopping commitment and extra slash; not vanilla two-diagonal X. | [frames](meshy_scout_evidence/105.jpg) |
| 102 | Sword_Judgment | AttackingwithWeapon | 4 | 3 | 5 | 2 | Thrust/bowed extension then sword flourish and reset; not overhead slam or landing-thrust lunge. | [frames](meshy_scout_evidence/102.jpg) |
| 99 | Reaping_Swing | Transitioning | 4 | 3 | 5 | 2 | Rises from crouch into broad sword flourishes and turn; no clean rising-spin phrase with demonstrated speed cap. | [frames](meshy_scout_evidence/99.jpg) |
| 100 | Rightward_Spin | Transitioning | 0 | 0 | 3 | 0 | Inverted shoulder/back roll across floor; outright reject. | [frames](meshy_scout_evidence/100.jpg) |
| 91 | Double_Blade_Spin | AttackingwithWeapon | 3 | 2 | 2 | 1 | Double-ended weapon overhead rotations with crouch/step; wrong weapon and no controlled single-sword rising cut. | [frames](meshy_scout_evidence/91.jpg) |
| 128 | Heavy_Hammer_Swing | AttackingwithWeapon | 5 | 4 | 3 | 4 | Grounded high two-arm windup and deep committed downward strike; second overhead base, hammer grip needs sword adaptation. | [frames](meshy_scout_evidence/128.jpg) |
| 237 | Charged_Axe_Chop | AttackingwithWeapon | 5 | 3 | 2 | 1 | Long crouched hold then rise into raised-hand stance; no clear overhead strike in samples. | [frames](meshy_scout_evidence/237.jpg) |
| 238 | Axe_Spin_Attack | AttackingwithWeapon | 4 | 3 | 3 | 2 | Turning swing with forward fold and crossing feet; rising blade path and instantaneous rotation limit unproven. | [frames](meshy_scout_evidence/238.jpg) |
| 127 | Charged_Ground_Slam | CastingSpell | 4 | 3 | 1 | 2 | Raised fist into low ground impact; reads as spell/punch rather than sword slam. | [frames](meshy_scout_evidence/127.jpg) |
| 86 | Basic_Jump | AttackingwithWeapon | 3 | 3 | 4 | 1 | Upright jump and crouched sword/shield landing; no visible landing thrust or overshoot continuation. | [frames](meshy_scout_evidence/86.jpg) |
| 90 | Counterstrike | Punching | 5 | 3 | 0 | 1 | High boxing guard and straight punches; wrong weapon language. | [frames](meshy_scout_evidence/90.jpg) |
| 93 | Dodge_and_Counter | Punching | 4 | 2 | 0 | 1 | Extended boxing dodge/punch sequence; not low-guard stillness and single offline step. | [frames](meshy_scout_evidence/93.jpg) |
| 101 | Sword_Shout | Acting | 5 | 3 | 5 | 1 | Raises sword in salute then rests it on shoulder; theatrical taunt, not The Pause. | [frames](meshy_scout_evidence/101.jpg) |
| 88 | Chest_Pound_Taunt | Transitioning | 5 | 2 | 4 | 0 | Chest-pound/raised-sword display with shield; not threatening stillness. | [frames](meshy_scout_evidence/88.jpg) |
| 147 | Sword_Parry | Blocking | 5 | 4 | 4 | 2 | Stationary high sword parry posture; useful defense, wrong low-hang neutral. | [frames](meshy_scout_evidence/147.jpg) |
| 148 | Sword_Parry_Backward | Blocking | 5 | 3 | 4 | 3 | Upper-body recoil from high parry and return; alternate stagger reference, less clean than selected hit reactions. | [frames](meshy_scout_evidence/148.jpg) |
| 151 | Sword_Parry_Backward_1 | Blocking | 5 | 3 | 3 | 2 | Very restrained low armed brace; too little response and blade direction absent. | [frames](meshy_scout_evidence/151.jpg) |
| 152 | Sword_Parry_Backward_2 | Blocking | 5 | 3 | 3 | 2 | Short torso recoil with low hand; defensive beat, not complete requested role. | [frames](meshy_scout_evidence/152.jpg) |
| 153 | Sword_Parry_Backward_3 | Blocking | 5 | 2 | 2 | 1 | Very deep squat/brace; oversized crouch for regal combat guard. | [frames](meshy_scout_evidence/153.jpg) |
| 154 | Sword_Parry_Backward_4 | Blocking | 5 | 3 | 3 | 2 | Small low-guard recoil and return; usable defense fragment only. | [frames](meshy_scout_evidence/154.jpg) |
| 155 | Sword_Parry_Backward_5 | Blocking | 4 | 3 | 3 | 2 | Large backward lean and recovery step; overextended parry recoil. | [frames](meshy_scout_evidence/155.jpg) |
| 149 | Two_Handed_Parry | Blocking | 5 | 4 | 4 | 2 | Two hands braced high across face; readable weapon defense, not low neutral. | [frames](meshy_scout_evidence/149.jpg) |
| 138 | Block1 | Blocking | 5 | 3 | 0 | 1 | Boxing guard held near face; no sword language. | [frames](meshy_scout_evidence/138.jpg) |
| 139 | Block2 | Blocking | 5 | 3 | 0 | 1 | High unarmed block with side recoil; wrong guard. | [frames](meshy_scout_evidence/139.jpg) |
| 140 | Block3 | Blocking | 5 | 3 | 0 | 1 | Head turns behind raised boxing forearm; wrong guard. | [frames](meshy_scout_evidence/140.jpg) |
| 141 | Block4 | Blocking | 5 | 2 | 0 | 1 | Multiple swaying upper-body blocks; fussy unarmed reaction. | [frames](meshy_scout_evidence/141.jpg) |
| 142 | Block5 | Blocking | 5 | 3 | 0 | 1 | Forearm crosses face during recoil; unarmed defense. | [frames](meshy_scout_evidence/142.jpg) |
| 143 | Block6 | Blocking | 5 | 2 | 0 | 1 | Broad high-arm block and side bend; too busy and unarmed. | [frames](meshy_scout_evidence/143.jpg) |
| 144 | Block8 | Blocking | 5 | 2 | 1 | 1 | Pronounced backward arch with lifted arms; excessive recoil. | [frames](meshy_scout_evidence/144.jpg) |
| 145 | Block9 | Blocking | 5 | 3 | 1 | 1 | Small upper-body brace with hands near chest; no low sword guard. | [frames](meshy_scout_evidence/145.jpg) |
| 146 | Block10 | Blocking | 5 | 3 | 1 | 2 | Short bracing step into lowered posture; defense fragment without hold/attack. | [frames](meshy_scout_evidence/146.jpg) |
| 156 | Stand_Dodge | Transitioning | 5 | 4 | 2 | 4 | Compact standing torso slip with low arms and return; second dodge candidate, does not establish an offline step. | [frames](meshy_scout_evidence/156.jpg) |
| 157 | Stand_Dodge_1 | Transitioning | 5 | 4 | 1 | 4 | Single bent-knee evasive step with balanced recovery; best dodge base, replace boxing hands with sword carriage. | [frames](meshy_scout_evidence/157.jpg) |
| 162 | Stand_Dodge_2 | Transitioning | 4 | 2 | 0 | 2 | Repeated boxing duck/weave and foot shifts; too busy for single deliberate dodge. | [frames](meshy_scout_evidence/162.jpg) |
| 164 | Stand_Dodge_3 | Transitioning | 4 | 2 | 0 | 2 | Repeated lateral boxing slips; long sequence rather than concise boss evade. | [frames](meshy_scout_evidence/164.jpg) |
| 158 | Roll_Dodge | Transitioning | 0 | 0 | 0 | 0 | Forward tuck and shoulder roll; prohibited tumble. | [frames](meshy_scout_evidence/158.jpg) |
| 159 | Roll_Dodge_1 | Transitioning | 0 | 0 | 0 | 0 | Diving forward roll with inverted legs; prohibited. | [frames](meshy_scout_evidence/159.jpg) |
| 160 | Roll_Dodge_2 | Transitioning | 0 | 0 | 0 | 0 | Backward tucked roll with feet overhead; prohibited. | [frames](meshy_scout_evidence/160.jpg) |
| 161 | Roll_Dodge_3 | Transitioning | 0 | 0 | 0 | 0 | Side/back roll through inversion; prohibited. | [frames](meshy_scout_evidence/161.jpg) |
| 163 | Roll_Dodge_4 | Transitioning | 0 | 0 | 0 | 0 | Low tumbling roll then guard reset; prohibited. | [frames](meshy_scout_evidence/163.jpg) |
| 178 | Hit_Reaction | GettingHit | 4 | 2 | 0 | 2 | Large hand flare and lifted-knee recoil; too light compared with selected staggers. | [frames](meshy_scout_evidence/178.jpg) |
| 179 | Hit_Reaction_1 | GettingHit | 5 | 4 | 1 | 4 | Small planted torso compression and recovery; best restrained stagger, needs armed hand pose. | [frames](meshy_scout_evidence/179.jpg) |
| 171 | Hit_Reaction_to_Waist | Transitioning | 5 | 4 | 1 | 4 | Clear weighty waist recoil with feet supporting and controlled return; second stagger, adapt boxing arms. | [frames](meshy_scout_evidence/171.jpg) |
| 173 | Slap_Reaction | GettingHit | 4 | 1 | 0 | 1 | Long slap recoil with face-touch gesture; comedic/social read. | [frames](meshy_scout_evidence/173.jpg) |
| 174 | Face_Punch_Reaction | GettingHit | 5 | 3 | 0 | 3 | Grounded head recoil but extended face-covering recovery; boxing-specific. | [frames](meshy_scout_evidence/174.jpg) |
| 175 | Face_Punch_Reaction_1 | GettingHit | 5 | 3 | 0 | 3 | Head snaps back then folds forward behind fists; more theatrical than selected small stagger. | [frames](meshy_scout_evidence/175.jpg) |
| 176 | Face_Punch_Reaction_2 | GettingHit | 4 | 2 | 0 | 2 | Broad backward sway and delayed recovery; low control. | [frames](meshy_scout_evidence/176.jpg) |
| 177 | Gunshot_Reaction | GettingHit | 5 | 2 | 0 | 1 | Arms fling high and chest recoils; firearm-specific hit read. | [frames](meshy_scout_evidence/177.jpg) |
| 172 | Electrocution_Reaction | GettingHit | 4 | 1 | 0 | 0 | Rigid extended arms and convulsive backward posture; electrical reaction, not sword stagger. | [frames](meshy_scout_evidence/172.jpg) |
| 7 | BeHit_FlyUp | GettingHit | 0 | 0 | 0 | 0 | Launched high and rotating through air; reject. | [frames](meshy_scout_evidence/7.jpg) |
| 8 | Dead | Dying | 5 | 4 | 3 | 5 | Knees buckle from armed stance into prone collapse; best death source, raw preview contains no aerial tumble. | [frames](meshy_scout_evidence/8.jpg) |
| 187 | Knock_Down | Dying | 0 | 0 | 0 | 0 | Explosive backward launch with inverted body; reject. | [frames](meshy_scout_evidence/187.jpg) |
| 190 | Knock_Down_1 | Dying | 1 | 1 | 0 | 0 | Backward airborne knockdown with legs thrown high; reject. | [frames](meshy_scout_evidence/190.jpg) |
| 189 | dying_backwards | Dying | 4 | 3 | 0 | 3 | Sits/falls backward onto back; plausible fallback but less weighty than selected collapses. | [frames](meshy_scout_evidence/189.jpg) |
| 188 | Fall_Dead_from_Abdominal_Injury | Dying | 5 | 4 | 1 | 4 | Clutches abdomen, sinks to knees and folds onto side; convincing collapse, adapt occupied sword hand. | [frames](meshy_scout_evidence/188.jpg) |
| 183 | Shot_and_Fall_Backward | Dying | 2 | 2 | 0 | 1 | Stiff backward shot fall travelling partly out of frame; incomplete visibility and wrong cause. | [frames](meshy_scout_evidence/183.jpg) |
| 184 | Shot_and_Fall_Forward | Dying | 3 | 2 | 0 | 2 | Shot recoil and sprawling forward/side fall; more flailing than collapse. | [frames](meshy_scout_evidence/184.jpg) |
| 185 | Shot_and_Slow_Fall_Backward | Dying | 4 | 3 | 0 | 3 | Slow chest recoil into seated/back fall; plausible fallback, firearm posture and foot kick reduce fit. | [frames](meshy_scout_evidence/185.jpg) |
| 186 | Strangled_and_Fall_Forward | Dying | 5 | 2 | 0 | 2 | Prolonged throat clutch then kneeling collapse; explicit strangling pantomime dominates. | [frames](meshy_scout_evidence/186.jpg) |
| 181 | Electrocuted_Fall | Dying | 3 | 1 | 0 | 0 | Electrical convulsion then falling partly out of frame; reject. | [frames](meshy_scout_evidence/181.jpg) |
| 182 | Shot_and_Blown_Back | Dying | 1 | 1 | 0 | 0 | Blast-like backward lift and legs thrown up; reject. | [frames](meshy_scout_evidence/182.jpg) |
| 366 | falling_down | Transitioning | 4 | 2 | 0 | 2 | Casual sideways sit/fall and roll onto back; lacks final heavy collapse. | [frames](meshy_scout_evidence/366.jpg) |
| 365 | Kneel_on_One_Knee_and_Stand | Transitioning | 5 | 3 | 0 | 1 | Rises from one knee to standing; reverse of desired death and no attack. | [frames](meshy_scout_evidence/365.jpg) |

Machine-readable shortlist: [meshy_clip_picks.json](meshy_clip_picks.json). Cached source GIFs and reproducible extraction/report scripts are retained in `meshy_scout_evidence/`.

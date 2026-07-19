"""
PHASE 3 FIXER r1 — numeric verification probe (fresh process, no render).

  blender --background models/godwyn_mocap.blend --python scripts/p3_fixer_r1_probe.py

Checks:
  * per-frame max vertex displacement of CapeGrid/RobeGrid (world, meters)
    - action window f10-34 must have no sim blow-up (was 1.55m spikes)
    - settled window f60-68 must be < 0.03 m/frame
  * per-frame min foot Z after per-frame grounding (contact ~0, jump keeps air)
  * cape centroid Y vs chest: is the cape still hanging behind the torso at
    the finish (f45-68)?
"""
import bpy
from mathutils import Vector

scene = bpy.context.scene
arm = next(o for o in scene.objects if o.type == "ARMATURE")
s = arm.scale.x
frames = list(range(scene.frame_start, scene.frame_end + 1))
grids = [bpy.data.objects[n] for n in ("CapeGrid", "RobeGrid")]
for g in grids:
    pc = g.modifiers["Cloth"].point_cache
    print(f"{g.name}: cache {pc.frame_start}..{pc.frame_end} baked={pc.is_baked}")

FOOT = ("LeftFoot", "RightFoot", "LeftToeBase", "RightToeBase")
prev = {}
disp = {g.name: {} for g in grids}
footz = {}
capeinfo = {}
for f in frames:
    scene.frame_set(f)
    dg = bpy.context.evaluated_depsgraph_get()
    ae = arm.evaluated_get(dg)
    footz[f] = min(ae.pose.bones[b].head.z for b in FOOT) * s
    for g in grids:
        ge = g.evaluated_get(dg)
        pts = [v.co.copy() for v in ge.data.vertices]
        if g.name in prev and len(prev[g.name]) == len(pts):
            disp[g.name][f] = max((a - b).length for a, b in zip(pts, prev[g.name]))
        prev[g.name] = pts
    # cape hang check: centroid of cape verts vs spine02/hips (local +Y is?)
    ce = grids[0].evaluated_get(dg)
    cen = sum((v.co for v in ce.data.vertices), Vector()) / len(ce.data.vertices)
    sp = ae.pose.bones["Spine02"].head * s
    hp = ae.pose.bones["Hips"].head * s
    hd = ae.pose.bones["Head"].head * s
    capeinfo[f] = (cen, sp, hp, hd)

print("\nframe  minFootZ  capeDisp  robeDisp")
for f in frames:
    print(f"f{f:03d}  {footz[f]:7.3f}  "
          f"{disp['CapeGrid'].get(f, 0):8.3f}  {disp['RobeGrid'].get(f, 0):8.3f}")

act_win = [f for f in frames if 10 <= f <= 34]
set_win = [f for f in frames if 60 <= f <= 68]
for name in ("CapeGrid", "RobeGrid"):
    a = max(disp[name].get(f, 0) for f in act_win)
    st = max(disp[name].get(f, 0) for f in set_win)
    print(f"{name}: action-window max disp {a:.3f} m/frame "
          f"({'OK' if a < 0.50 else 'BLOWUP'}), settled f60-68 max {st:.3f} "
          f"({'OK' if st < 0.03 else 'JITTER'})")

contact = [f for f in frames if not (28 < f < 33)]
print(f"grounding: contact min={min(footz[f] for f in contact):.4f} "
      f"max={max(footz[f] for f in contact):.4f} "
      f"jump apex={max(footz[f] for f in range(28, 34)):.4f}")

# cape side check at the finish: cape centroid should sit on the OPPOSITE side
# of the torso from the facing direction (behind the back, not on the chest)
print("\ncape-vs-back f45-68 (dot>0 means cape is BEHIND the torso):")
for f in range(45, frames[-1] + 1, 4):
    cen, sp, hp, hd = capeinfo[f]
    scene.frame_set(f)
    ae = arm.evaluated_get(bpy.context.evaluated_depsgraph_get())
    # facing = spine forward: use hips->head lean removed, take bone Y axis
    pbm = ae.pose.bones["Spine02"].matrix
    back = -(arm.matrix_world.to_3x3() @ pbm.col[1].to_3d())  # -bone Y ~ back?
    back.z = 0
    if back.length > 1e-6:
        back.normalize()
    v = cen - sp
    v.z = 0
    d = v.dot(back)
    print(f"f{f:03d}: cape-centroid offset from spine "
          f"({v.x:.2f},{v.y:.2f}) dot_back={d:.2f}")
print("PROBE DONE")

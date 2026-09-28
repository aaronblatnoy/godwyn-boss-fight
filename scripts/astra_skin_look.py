"""Natural skin look for the Meshy head material: SSS gated by the skin mask, no pale multiply, warmer HSV, rosy tint. Idempotent."""
import bpy, sys, json
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
args = dict(a.split("=", 1) for a in sys.argv[sys.argv.index("--") + 1:]) if "--" in sys.argv else {}
cand = args.get("candidate", "models/astra_character_v2.blend"); out = args.get("out", "models/astra_character_v2_skin_i01.blend")
P = dict(sat=float(args.get("sat", 1.28)), val=float(args.get("val", 1.0)), hue=float(args.get("hue", 0.492)),
         sss=float(args.get("sss", 0.32)), sss_scale=float(args.get("sss_scale", 0.008)), rosy=float(args.get("rosy", 0.10)),
         spec_mult=float(args.get("spec_mult", 0.35)))
bpy.ops.wm.open_mainfile(filepath=str(ROOT / cand))
o = bpy.data.objects["AstraChar2_Meshy_HeadHair"]; m = o.data.materials[0]; nt = m.node_tree; N = nt.nodes; L = nt.links
for n in [n for n in N if n.name.startswith("SkinLook ")]: N.remove(n)
bsdf = N["Principled BSDF"]; hsv = N["Meshy i02 warm HSV"]; mul = N["Meshy i02 SPEC multiply"]; mask = N["Meshy i02 skin mask"]; mix = N["Meshy i02 skin mix"]
mul.inputs["Factor"].default_value = P["spec_mult"]
hsv.inputs["Hue"].default_value = P["hue"]; hsv.inputs["Saturation"].default_value = P["sat"]; hsv.inputs["Value"].default_value = P["val"]
rosy = N.new("ShaderNodeMixRGB"); rosy.name = "SkinLook rosy"; rosy.blend_type = "SOFT_LIGHT"; rosy.inputs["Fac"].default_value = P["rosy"]; rosy.inputs["Color2"].default_value = (0.85, 0.42, 0.38, 1.0)
L.new(hsv.outputs["Color"], rosy.inputs["Color1"]); L.new(rosy.outputs["Color"], mix.inputs["Color2"])
sssm = N.new("ShaderNodeMath"); sssm.name = "SkinLook sss gate"; sssm.operation = "MULTIPLY"; sssm.inputs[1].default_value = P["sss"]
L.new(mask.outputs["Fac"], sssm.inputs[0]); L.new(sssm.outputs["Value"], bsdf.inputs["Subsurface Weight"])
bsdf.inputs["Subsurface Radius"].default_value = (1.0, 0.35, 0.2); bsdf.inputs["Subsurface Scale"].default_value = P["sss_scale"]
bsdf.inputs["Subsurface Weight"].default_value = 0.0
bpy.ops.wm.save_as_mainfile(filepath=str(ROOT / out), copy=True)
print("SKINLOOK_SAVED", out, json.dumps(P), flush=True)

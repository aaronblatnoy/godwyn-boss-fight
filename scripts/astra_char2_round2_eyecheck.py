import bpy
bpy.ops.wm.open_mainfile(filepath='/Users/aaron_7nh0yzm/godwyn-boss-fight/models/astra_character_v2_round2_work.blend')
for name in ['AstraChar2_Eyeball_L','AstraChar2_Iris_L','AstraChar2_Eyeball_R','AstraChar2_Iris_R']:
 o=bpy.data.objects[name];ev=o.evaluated_get(bpy.context.evaluated_depsgraph_get());me=ev.to_mesh();ps=[o.matrix_world@v.co for v in me.vertices];print(name,[(min(p[i] for p in ps),max(p[i] for p in ps)) for i in range(3)]);ev.to_mesh_clear()

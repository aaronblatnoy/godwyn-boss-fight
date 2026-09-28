import bpy,sys,json,collections,hashlib,numpy as np
from pathlib import Path
sys.dont_write_bytecode=True
ROOT=Path('/Users/aaron_7nh0yzm/godwyn-boss-fight');OUT=ROOT/'renders/astra/char2';sys.path.insert(0,str(ROOT/'scripts'))
import astra_character_common as c
from astra_char2_render import configure
bpy.ops.wm.open_mainfile(filepath=str(ROOT/'models/astra_character_v2_round2_input.blend'))
o=bpy.data.objects['char1'];me=o.data;mw=o.matrix_world
blue=[f for f in me.polygons if f.material_index==1 and (mw@f.center).z<2.78];ids={i for f in blue for i in f.vertices};p=[mw@me.vertices[i].co for i in ids];groups=collections.Counter()
for i in ids:
 for g in me.vertices[i].groups:groups[o.vertex_groups[g.group].name]+=g.weight
r={'cloth_objects':[x.name for x in bpy.data.objects if x.type=='MESH' and any(m and ('blue' in m.name.lower() or 'robe' in m.name.lower()) for m in x.data.materials)],'blue_primary_material':me.materials[1].name,'blue_polygons':len(blue),'bounds_m':[[min(v[i] for v in p),max(v[i] for v in p)] for i in range(3)],'dominant_weight_totals':groups.most_common(15),'cloth_modifiers_on_char1':[(m.name,m.type) for m in o.modifiers],'geometry_changed':False,'assessment':'Blue is assigned inside the combined char1 mesh, plus Astra_Undersleeves. Front waist-to-floor center panel, diagonal torso/left-shoulder drape, and broad side/back floor-length skirt panels. It is not a separate standalone robe object. Visual back/side assessment follows in ROUND2_REPORT.md.'}
(OUT/'round2_garment.json').write_text(json.dumps(r,indent=2));configure();c.VIEWS['garment_back']=((0,9,3.1),(0,0,1.61),3.75);c.VIEWS['garment_side']=((8,0,3.1),(0,0,1.61),3.75)
for v in ['garment_back','garment_side']:c.render_view('r2',v)

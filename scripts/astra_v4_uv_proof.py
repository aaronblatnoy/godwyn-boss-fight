import bpy,sys,json,numpy as np,hashlib
from pathlib import Path
R=Path(__file__).resolve().parents[1];sys.path.insert(0,str(R/'scripts'));import astra_v3_build as b
O=R/'renders/astra/v4';bpy.ops.wm.open_mainfile(filepath=str(O/'raw.blend'));ob=bpy.data.objects['V4_Body']
def uvset(ob):
 uv=np.array([d.uv[:] for d in ob.data.uv_layers.active.data]);u=np.unique(np.round(uv,6),axis=0);return u
u=uvset(ob);before=set(bpy.data.objects);bpy.ops.import_scene.gltf(filepath=str(R/'models/meshy_godwyn_full.glb'));src=next(o for o in bpy.data.objects if o not in before and o.type=='MESH');v=uvset(src);rep={'rigged_unique_uvs':len(u),'unrigged_unique_uvs':len(v),'unique_uvs_exact_at_1e_6':u.shape==v.shape and bool(np.array_equal(u,v))}
bpy.ops.wm.open_mainfile(filepath=str(R/'models/astra_character_v3.blend'));rig=bpy.data.objects['Astra_V3_Rig'];rig.data.pose_position='REST';bpy.context.view_layer.update();ob=bpy.data.objects['AstraChar2_Meshy_HeadHair'];pts=np.array([(ob.matrix_world@x.co)[:] for x in ob.data.vertices]);attr=ob.data.color_attributes['meshy_skin_mask'];uv=ob.data.uv_layers.active.data;worlda=0.;uva=0.;count=0
for f in ob.data.polygons:
 if np.mean([attr.data[i].color[0] for i in f.loop_indices])<.5:continue
 ids=list(f.vertices);li=list(f.loop_indices)
 for i in range(1,len(ids)-1):
  a,bb,c=pts[[ids[0],ids[i],ids[i+1]]];t=np.array([uv[x].uv[:] for x in [li[0],li[i],li[i+1]]]);worlda+=float(np.linalg.norm(np.cross(bb-a,c-a))/2);d=t[1]-t[0];e=t[2]-t[0];uva+=float(abs(d[0]*e[1]-d[1]*e[0])/2);count+=1
im=next(n.image for n in ob.data.materials[0].node_tree.nodes if n.type=='TEX_IMAGE' and n.image and n.image.name.startswith('Image_0'));rep['v3_skin_region']={'triangles':count,'region':'all skin-mask triangles on separate donor head, including neck; not identically cropped to v4 face ROI','texture_size':list(im.size),'surface_cm2':worlda*1e4,'uv_area':uva,'texels_per_cm':float(np.sqrt(uva*im.size[0]*im.size[1]/(worlda*1e4)))};(O/'uv_proof.json').write_text(json.dumps(rep,indent=2));print('V4_UV_PROOF',json.dumps(rep),flush=True)

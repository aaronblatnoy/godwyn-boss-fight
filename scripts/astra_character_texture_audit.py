import bpy,numpy as np,json
from pathlib import Path
P=Path('/Users/aaron_7nh0yzm/godwyn-boss-fight/renders/astra/character')
def read(path):
 im=bpy.data.images.load(str(P/path),check_existing=False);a=np.empty(len(im.pixels),dtype=np.float32);im.pixels.foreach_get(a);return a.reshape(im.size[1],im.size[0],4)[:,:,:3]
src=read('source_1.png');orm=read('source_2.png');gold=orm[:,:,2]>.6;blue=(src[:,:,2]>src[:,:,0]*1.35)&~gold
out={}
base=read('textures/astra_character_char1_basecolor_4096.png');finalnorm=read('textures/astra_character_char1_normal_4096.png');finalmr=read('textures/astra_character_char1_orm_4096.png');painted=base.max(2)>.05
lengths=np.linalg.norm(finalnorm*2-1,axis=2);coverage=float(((lengths>.9)&(lengths<1.1))[painted].mean());rough_coverage=float((finalmr[:,:,1]>.06)[painted].mean())
out['coverage']={'valid_tangent_normal_fraction_on_painted_texels':coverage,'roughness_coverage_on_painted_texels':rough_coverage}
assert coverage>.97,('Incomplete or invalid normal bake',coverage)
assert rough_coverage>.99,('Incomplete roughness bake',rough_coverage)
for region,mask in [('gold',gold),('robe',blue)]:
 for _ in range(3):mask=mask&np.roll(mask,1,0)&np.roll(mask,-1,0)&np.roll(mask,1,1)&np.roll(mask,-1,1)
 report={'source_interior_pixels':int(mask.sum()),'source_color_std':src[mask].std(0).tolist(),'source_roughness_mean':float(orm[:,:,1][mask].mean()),'source_roughness_std':float(orm[:,:,1][mask].std())}
 finalorm=read('textures/astra_character_char1_orm_4096.png');normal=read('textures/astra_character_char1_normal_4096.png');m=mask.repeat(2,0).repeat(2,1)
 report.update(final_roughness_mean=float(finalorm[:,:,1][m].mean()),final_roughness_std=float(finalorm[:,:,1][m].std()),normal_xy_std=normal[:,:,:2][m].std(0).tolist(),normal_perturbed_fraction=float((np.linalg.norm(normal[:,:,:2][m]-.5,axis=1)>.012).mean()))
 out[region]=report
(P/'texture_detail_audit.json').write_text(json.dumps(out,indent=2));print(json.dumps(out,indent=2))

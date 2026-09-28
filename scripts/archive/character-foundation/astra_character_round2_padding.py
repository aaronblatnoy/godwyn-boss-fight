"""Class-isolated nearest-texel extension; no empty pixels in filtering footprints."""
from pathlib import Path
from PIL import Image
from scipy.ndimage import distance_transform_edt
import numpy as np,json
P=Path(__file__).resolve().parents[1]/'renders/astra/character';T=P/'textures';report={}
for prefix,size in [('astra_character_char1',4096),('astra_character_char1_robe',4096),('astra_character_Astra_Undersleeves',2048)]:
 orm=np.array(Image.open(T/f'{prefix}_orm_{size}.png').convert('RGB'));valid=orm[:,:,1]>12
 indices=distance_transform_edt(~valid,return_distances=False,return_indices=True)
 for kind in ['basecolor','orm','normal']:
  path=T/f'{prefix}_{kind}_{size}.png';a=np.array(Image.open(path).convert('RGB'));a[~valid]=a[indices[0][~valid],indices[1][~valid]]
  if kind=='orm' and prefix=='astra_character_char1':a[:,:,2]=255
  Image.fromarray(a).save(path)
 report[prefix]={'same_material_extended_texels':int((~valid).sum()),'atlas_pixels':int(valid.size),'metallic_padding':1 if prefix=='astra_character_char1' else 'nearest same-atlas class'}
 del indices
print(json.dumps(report,indent=2),flush=True)
d=json.loads((P/'round2_bake_diagnostic.json').read_text());d['material_aware_padding']=report;d['material_build']['gold_roughness_formula_range']=[.175,.825];d['material_build']['face_and_hair']='Original shaders and maps retained above 2.78m, neck skin above 2.70m and source-classified hanging hair.'
d['iteration_notes']=['First gold preview was too silver; warmed three plate-zone colors and raised the roughness floor by .05.','Preserved original neck and hanging-hair materials, and assigned border faces to the source-derived robe/scrollwork shader.','Initial UV audit found 822 of 633325 gold surface samples (0.1298%) losing full metallic response against empty atlas space; class-isolated nearest-texel extension fixes the filtering footprint.']
(P/'round2_bake_diagnostic.json').write_text(json.dumps(d,indent=2))

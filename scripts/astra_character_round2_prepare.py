"""Prepare class-constrained masks using the read-only NumPy audit, never geometry."""
from pathlib import Path
import json,numpy as np
from PIL import Image
from scipy import ndimage as nd
P=Path(__file__).resolve().parents[1]/'renders/astra/character'
O=P/'round2_work';O.mkdir(exist_ok=True)
d=np.load(P/'round1_backup/audit_arrays.npz')
src=d['source'];orm=d['source_orm'];mask=orm[:,:,2]>.6
# Preserve the source's continuous scrollwork. Close single-source-pixel holes,
# then remove isolated <= 3-pixel metal specks, not narrow connected ornaments.
closed=nd.binary_closing(mask,iterations=1)
labels,n=nd.label(closed);sizes=np.bincount(labels.ravel());clean=closed&(sizes[labels]>3)
# Smooth antialiasing at the original resolution; all detail remains source UV based.
trim=nd.gaussian_filter(clean.astype(np.float32),.45)
def write(name,a):
 if a.ndim==2:a=np.repeat(a[:,:,None],3,2)
 Image.fromarray(np.uint8(np.clip(a[::-1],0,1)*255+.5)).save(O/name)
write('source_trim_mask.png',trim)
old=d['orm'];ao=old[:,:,0];valid=old[:,:,1]>.05
# A 2-sample AO bake had binary salt-and-pepper values. Normalized convolution
# retains its cavity trend without carrying invalid border texels into the result.
w=nd.gaussian_filter(valid.astype(np.float32),2.5)
smooth=nd.gaussian_filter(ao*valid,2.5)/np.maximum(w,1e-6)
smooth=np.where(w>.05,smooth,1)
write('cavity_4096.png',smooth)
report=json.loads((P/'round2_bake_diagnostic.json').read_text())
report['root_cause']={'cage_pull_ruled_out':True,'shared_dilation_margin_pixels':12,'margin_type':report['round1_bake_settings']['margin_type'],'gold_interior_blue_texels':report['regions']['gold_source_inset_3px']['blue_in_gold_fraction'],'additional_causes':['Shared UV atlas has fragmented islands and mixed-material borders; a common 12px dilation gives opposite classes access to narrow islands and their filtering footprints.','Per-pixel thresholding of a filtered source texture makes hard discontinuities in bump/material masks; neutral transition colors were treated as skin, giving pale trim flecks.','Some blue triangles and open seams are already present in the original before_chest reference; those are outside a texture-only repair.'],'repair':'Per-material target atlases with homogeneous gold on every armor texel, source-derived repaired trim only in the robe shader, EXTEND margin 4, no cage, no selected-to-active transfer; original UV coordinates remain unchanged.'}
report['trim_mask_repair']={'original_gold_pixels':int(mask.sum()),'cleaned_gold_pixels':int(clean.sum()),'added_pixels':int((clean&~mask).sum()),'removed_pixels':int((mask&~clean).sum())}
(P/'round2_bake_diagnostic.json').write_text(json.dumps(report,indent=2))
print(report['trim_mask_repair'],flush=True)

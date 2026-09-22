"""Read-only installed MPFB base and targets; no addon registration/config writes."""
import sys,json,gzip
from pathlib import Path
sys.dont_write_bytecode=True
A=Path.home()/'Library/Application Support/Blender/5.2/extensions/user_default/mpfb';R=Path('/Users/aaron_7nh0yzm/godwyn-boss-fight')
v=[];faces=[];group='';groups={}
for line in (A/'data/3dobjs/base.obj').open():
 if line.startswith('v '):v.append(list(map(float,line.split()[1:4])))
 elif line.startswith('g '):group=line.split()[1]
 elif line.startswith('f '):
  ids=[int(s.split('/')[0])-1 for s in line.split()[1:]];faces.append((group,ids));groups.setdefault(group,set()).update(ids)
for line in gzip.open(A/'data/targets/macrodetails/caucasian-male-young.target.gz','rt'):
 s=line.split()
 if len(s)==4:
  i=int(s[0]);v[i]=[a+float(b) for a,b in zip(v[i],s[1:])]
r={'base_vertices':len(v),'targets':len(list((A/'data/targets').rglob('*.target.gz'))),'groups':{}}
for g in ['body','joint-head','joint-head-2','joint-neck','joint-jaw','joint-l-eye','joint-r-eye','joint-mouth','helper-l-eye','helper-r-eye']:
 ids=groups[g];pts=[v[i] for i in ids];r['groups'][g]={'vertices':len(ids),'mean':[sum(p[k] for p in pts)/len(pts) for k in range(3)],'min':[min(p[k] for p in pts) for k in range(3)],'max':[max(p[k] for p in pts) for k in range(3)]}
body=[v[i] for i in groups['body'] if v[i][1]>6.4];r['head_body_range']={'min':[min(p[k] for p in body) for k in range(3)],'max':[max(p[k] for p in body) for k in range(3)]}
(R/'renders/astra/char2/r6_mpfb_recon.json').write_text(json.dumps(r,indent=2));print(json.dumps(r,indent=2))

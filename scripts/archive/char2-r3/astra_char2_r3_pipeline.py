"""Reproduce Round 3 from immutable backup; only allowed output prefixes are used."""
import os,sys,subprocess
from pathlib import Path
sys.dont_write_bytecode=True
ROOT=Path('/Users/aaron_7nh0yzm/godwyn-boss-fight');OUT=ROOT/'renders/astra/char2';env=dict(os.environ,PYTHONDONTWRITEBYTECODE='1')
steps=[('build',[]),('hair',[]),('repair',[]),('relief',[]),('weightfix',['--','--fresh']),('render',['--','after']),('stress',[]),('export',[]),('haircompare',[]),('validate',[])]
if '--finish' in sys.argv:steps=steps[3:]
if '--validate-final' in sys.argv:steps=steps[5:]
for step,args in steps:
 print('START',step,flush=True)
 with (OUT/('r3_'+step+'_pipeline.log')).open('w') as log:subprocess.run(['/opt/homebrew/bin/blender','--background','--python-exit-code','1','--python',str(ROOT/'scripts'/('astra_char2_r3_'+step+'.py'))]+args,env=env,cwd=ROOT,stdout=log,stderr=subprocess.STDOUT,check=True)
 print('DONE',step,flush=True)
subprocess.run([sys.executable,str(ROOT/'scripts/astra_char2_r3_compare.py')],env=env,cwd=ROOT,check=True)

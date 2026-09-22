"""Import and inspect the unmodified Godwyn rig; also shared render staging."""
from pathlib import Path
import bpy
from mathutils import Vector
import json

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'renders/astra'

def fresh():
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete(use_global=False)
    bpy.ops.import_scene.gltf(filepath=str(ROOT / 'models/godwyn_game.glb'))
    rig = bpy.data.objects['Armature']
    rig.animation_data_clear()
    for p in rig.pose.bones:
        p.matrix_basis.identity()
    bpy.context.view_layer.update()
    return rig

def stage():
    scene = bpy.context.scene
    scene.render.engine = 'BLENDER_EEVEE'
    scene.render.resolution_x = 640
    scene.render.resolution_y = 640
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = 'PNG'
    scene.render.fps = 30
    scene.world.color = (0.14, 0.14, 0.14)
    scene.view_settings.view_transform = 'AgX'
    bpy.ops.mesh.primitive_plane_add(size=200, location=(0,0,-0.015))
    floor = bpy.context.object
    floor.name = 'Astra_Stage'
    mat = bpy.data.materials.new('Astra slate')
    mat.diffuse_color = (0.055, 0.072, 0.095, 1)
    floor.data.materials.append(mat)
    for name, pos, power, color, size in [
        ('Key', (3,-4,6), 1500, (1.0,0.86,0.70), 5),
        ('Fill', (-4,-2,3), 1100, (0.64,0.78,1.0), 4),
        ('Rim', (1,3,5), 1800, (1.0,0.77,0.43), 3)]:
        data=bpy.data.lights.new('Astra_'+name,'AREA')
        data.energy=power; data.color=color; data.shape='DISK'; data.size=size
        obj=bpy.data.objects.new(data.name,data); scene.collection.objects.link(obj)
        obj.location=pos
        obj.rotation_euler=(Vector((0,0,1.2))-obj.location).to_track_quat('-Z','Y').to_euler()
    data=bpy.data.cameras.new('Astra_Camera')
    cam=bpy.data.objects.new(data.name,data); scene.collection.objects.link(cam)
    data.type='ORTHO'; data.ortho_scale=3.8
    scene.camera=cam
    return scene

def camera(view='front', scale=3.8, target=(0,0,1.3)):
    cam=bpy.context.scene.camera
    positions={'front':(0,-8,2.0),'side':(8,0,2.0),'three_quarter':(4,-7,2.8)}
    cam.location=positions[view]
    cam.rotation_euler=(Vector(target)-cam.location).to_track_quat('-Z','Y').to_euler()
    cam.data.ortho_scale=scale

def main():
    OUT.mkdir(parents=True,exist_ok=True)
    rig=fresh()
    result={'rig_matrix':[list(row) for row in rig.matrix_world], 'bones':{}}
    for p in rig.pose.bones:
        if not p.name.startswith('phys_'):
            h=rig.matrix_world @ p.head; t=rig.matrix_world @ p.tail
            result['bones'][p.name]={'head':list(h),'tail':list(t),'parent':p.parent.name if p.parent else None}
            print('BONE',p.name, 'HEAD',tuple(round(v,4) for v in h),'TAIL',tuple(round(v,4) for v in t),flush=True)
    sword=bpy.data.objects['Godwyn_Sword']
    result['sword']={'parent':sword.parent.name if sword.parent else None,'parent_type':sword.parent_type,'parent_bone':sword.parent_bone,'modifiers':[(m.name,m.type,m.object.name if getattr(m,'object',None) else None) for m in sword.modifiers],'groups':[g.name for g in sword.vertex_groups], 'bbox':[list(sword.matrix_world @ Vector(c)) for c in sword.bound_box]}
    print('SWORD',json.dumps(result['sword']),flush=True)
    result['secondary']=[p.name for p in rig.pose.bones if p.name.startswith('phys_')]
    (OUT/'probe.json').write_text(json.dumps(result,indent=2))
    scene=stage()
    for view in ['front','side']:
        camera(view)
        scene.render.filepath=str(OUT/f'rest_{view}.png')
        bpy.ops.render.render(write_still=True)

if __name__=='__main__': main()

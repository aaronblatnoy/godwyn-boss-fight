import bpy, sys, json, importlib, types
from pathlib import Path
sys.dont_write_bytecode = True
R = Path('/Users/aaron_7nh0yzm/godwyn-boss-fight')
EXT = Path('/Users/aaron_7nh0yzm/Library/Application Support/Blender/5.2/extensions/user_default')

def enable_mpfb():
    # Use the installed extension, with all runtime caches/logs confined to /tmp.
    old = bpy.utils.extension_path_user
    def scratch_path(package, path='', create=False):
        if package == 'bl_ext.user_default.mpfb':
            p = Path('/tmp/astra_char2_mpfb_runtime') / path
            p.mkdir(parents=True, exist_ok=True)
            return str(p)
        return old(package, path=path, create=create)
    bpy.utils.extension_path_user = scratch_path
    for name, path in [('bl_ext', EXT.parent), ('bl_ext.user_default', EXT)]:
        if name not in sys.modules:
            mod = types.ModuleType(name); mod.__path__ = [str(path)]; sys.modules[name] = mod
        elif not hasattr(sys.modules[name], '__path__'):
            sys.modules[name].__path__ = [str(path)]
        elif str(path) not in sys.modules[name].__path__:
            sys.modules[name].__path__.append(str(path))
    mod = importlib.import_module('bl_ext.user_default.mpfb')
    original = mod.get_preference
    def pref(key):
        if key == 'mpfb_user_data': return '/tmp/astra_char2_mpfb_runtime'
        if key == 'mh_auto_user_data': return False
        if 'bl_ext.user_default.mpfb' not in bpy.context.preferences.addons: return None
        try: return original(key)
        except ValueError: return None
    mod.get_preference = pref
    mod.register()
    return mod

if __name__ == '__main__':
    enable_mpfb()
    from bl_ext.user_default.mpfb.services.humanservice import HumanService
    from bl_ext.user_default.mpfb.services.targetservice import TargetService
    human = HumanService.create_human()
    report = {'version': list(bpy.app.version), 'vertices': len(human.data.vertices),
              'bounds': [list(v) for v in human.bound_box],
              'groups': [g.name for g in human.vertex_groups],
              'macros': TargetService.get_default_macro_info_dict()}
    (R/'renders/astra/char2/mpfb_probe.json').write_text(json.dumps(report, indent=2))
    print('MPFB_VERIFIED', len(human.data.vertices), flush=True)
    bpy.ops.wm.open_mainfile(filepath=str(R/'models/astra_character_v2.blend'))
    arm = bpy.data.objects['Armature']
    data = {'bones': {b.name: {'head': list(arm.matrix_world@b.head_local), 'rest': [list(row) for row in b.matrix_local], 'parent': b.parent.name if b.parent else None} for b in arm.data.bones},
            'objects': {o.name: {'type': o.type, 'vertices': len(o.data.vertices) if o.type == 'MESH' else 0, 'faces': len(o.data.polygons) if o.type == 'MESH' else 0, 'hidden': o.hide_render, 'slots': [m.name if m else None for m in o.data.materials] if hasattr(o.data, 'materials') else [], 'bounds': [list(o.matrix_world@__import__('mathutils').Vector(p)) for p in o.bound_box] if o.type == 'MESH' else []} for o in bpy.data.objects},
            'actions': len(bpy.data.actions)}
    (R/'renders/astra/char2/mpfb_baseline.json').write_text(json.dumps(data, indent=2))
    print('BASELINE', len(arm.data.bones), len(bpy.data.actions), flush=True)

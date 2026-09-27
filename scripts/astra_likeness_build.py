"""Build a head-only Godwyn likeness candidate from the validated MPFB surface source."""
import bpy
import math
import sys
import json
import numpy as np
from pathlib import Path
from mathutils import Vector
from mathutils.bvhtree import BVHTree

ROOT = Path.cwd()
OUT = ROOT / 'renders/astra/char2'
BASE = ROOT / 'models/astra_character_v2_mpfb_surface_finish_i03.blend'


def reset_pose(arm):
    for bone in arm.pose.bones:
        bone.matrix_basis.identity()
    bpy.context.view_layer.update()


def bind_head(ob, arm):
    ob.parent = arm
    vg = ob.vertex_groups.new(name='Head')
    vg.add(range(len(ob.data.vertices)), 1.0, 'REPLACE')
    mod = ob.modifiers.new('Likeness head binding', 'ARMATURE')
    mod.object = arm


def material(name, color, roughness=.4, coat=0.0, coat_rough=.15, subsurface=0.0):
    mat = bpy.data.materials.get(name) or bpy.data.materials.new(name)
    mat.use_nodes = True
    mat.node_tree.nodes.clear()
    out = mat.node_tree.nodes.new('ShaderNodeOutputMaterial')
    bs = mat.node_tree.nodes.new('ShaderNodeBsdfPrincipled')
    bs.inputs['Base Color'].default_value = (*color, 1)
    bs.inputs['Roughness'].default_value = roughness
    if 'Coat Weight' in bs.inputs:
        bs.inputs['Coat Weight'].default_value = coat
        bs.inputs['Coat Roughness'].default_value = coat_rough
    if 'Subsurface Weight' in bs.inputs:
        bs.inputs['Subsurface Weight'].default_value = subsurface
    mat.node_tree.links.new(bs.outputs['BSDF'], out.inputs['Surface'])
    return mat


def mesh_object(name, verts, faces, mat, arm):
    old = bpy.data.objects.get(name)
    if old:
        bpy.data.objects.remove(old, do_unlink=True)
    me = bpy.data.meshes.new(name + ' Mesh')
    me.from_pydata(verts, [], faces)
    me.materials.append(mat)
    for p in me.polygons:
        p.use_smooth = True
    ob = bpy.data.objects.new(name, me)
    bpy.context.scene.collection.objects.link(ob)
    bind_head(ob, arm)
    return ob


def tube(name, points, radii, mat, arm, sides=8):
    points = np.asarray(points, dtype=float)
    if np.isscalar(radii):
        radii = np.full(len(points), float(radii))
    verts = []
    faces = []
    for i, p in enumerate(points):
        if i == 0:
            tangent = Vector(points[1] - p).normalized()
        elif i == len(points) - 1:
            tangent = Vector(p - points[i - 1]).normalized()
        else:
            tangent = Vector(points[i + 1] - points[i - 1]).normalized()
        basis_a = tangent.cross(Vector((0, 0, 1)))
        if basis_a.length < .05:
            basis_a = tangent.cross(Vector((0, 1, 0)))
        basis_a.normalize()
        basis_b = tangent.cross(basis_a).normalized()
        for j in range(sides):
            angle = math.tau * j / sides
            q = Vector(p) + float(radii[i]) * (math.cos(angle) * basis_a + math.sin(angle) * basis_b)
            verts.append(tuple(q))
    for i in range(len(points) - 1):
        for j in range(sides):
            a = i * sides + j
            b = i * sides + (j + 1) % sides
            faces.append((a, b, b + sides, a + sides))
    faces.append(tuple(range(sides - 1, -1, -1)))
    end = (len(points) - 1) * sides
    faces.append(tuple(end + j for j in range(sides)))
    return mesh_object(name, verts, faces, mat, arm)


def front_surface(tree, x, z, fallback=-.414):
    hit, normal, _, _ = tree.ray_cast(Vector((x, -1.0, z)), Vector((0, 1, 0)), 1.5)
    return float(hit.y) if hit else fallback


def sculpt_lid_soft_tissue(head):
    """Close the MPFB aperture at the lid margins without changing topology or bone structure."""
    changed = 0
    centers = (-.05284, .05284)
    cz = 2.97255
    for vert in head.data.vertices:
        p = vert.co
        if p.y > -.385:
            continue
        for cx in centers:
            dx = abs(p.x - cx)
            if dx >= .026:
                continue
            fx = max(0.0, 1.0 - (dx / .026) ** 2) ** 2
            if cz + .0015 <= p.z <= cz + .016:
                fz = max(0.0, 1.0 - (p.z - (cz + .0015)) / .0145)
                amount = .0052 * fx * fz
                p.z -= amount
                p.y -= .0010 * fx * fz
                changed += 1
            elif cz - .012 <= p.z <= cz - .0030:
                fz = max(0.0, 1.0 - abs(p.z - (cz - .0065)) / .0060)
                amount = .00115 * fx * fz
                p.z += amount
                p.y -= .00045 * fx * fz
                changed += 1
    head.data.update()
    assert changed > 100
    return changed


def rebuild_skin():
    mat = bpy.data.materials['Astra pale golden skin final']
    mat.use_nodes = True
    nt = mat.node_tree
    nt.nodes.clear()
    out = nt.nodes.new('ShaderNodeOutputMaterial')
    out.location = (920, 0)
    bs = nt.nodes.new('ShaderNodeBsdfPrincipled')
    bs.name = 'Living likeness skin • 3.2mm SSS scale'
    bs.location = (650, 0)
    nt.links.new(bs.outputs['BSDF'], out.inputs['Surface'])
    bs.inputs['Roughness'].default_value = .38
    bs.inputs['IOR'].default_value = 1.42
    bs.inputs['Subsurface Weight'].default_value = .24
    bs.inputs['Subsurface Radius'].default_value = (1.0, .42, .18)
    for key in ('Subsurface Scale', 'Subsurface IOR Level'):
        if key in bs.inputs:
            bs.inputs[key].default_value = .0032 if key == 'Subsurface Scale' else .55
    if 'Coat Weight' in bs.inputs:
        bs.inputs['Coat Weight'].default_value = .055
        bs.inputs['Coat Roughness'].default_value = .24

    tex = nt.nodes.new('ShaderNodeTexCoord')
    tex.location = (-1000, 80)
    noise = nt.nodes.new('ShaderNodeTexNoise')
    noise.location = (-800, 120)
    noise.inputs['Scale'].default_value = 92
    noise.inputs['Detail'].default_value = 5
    noise.inputs['Roughness'].default_value = .72
    nt.links.new(tex.outputs['Generated'], noise.inputs['Vector'])
    ramp = nt.nodes.new('ShaderNodeValToRGB')
    ramp.location = (-580, 140)
    ramp.color_ramp.elements[0].position = .25
    ramp.color_ramp.elements[0].color = (.40, .24, .17, 1)
    ramp.color_ramp.elements[1].position = .76
    ramp.color_ramp.elements[1].color = (.58, .39, .27, 1)
    nt.links.new(noise.outputs['Fac'], ramp.inputs['Fac'])

    geom = nt.nodes.new('ShaderNodeNewGeometry')
    geom.location = (-1020, -360)
    masks = []
    centers = [
        ((0, -.445, 2.900), .018, .070, .18),
        ((-.074, -.412, 2.918), .018, .074, .12),
        ((.074, -.412, 2.918), .018, .074, .12),
        ((-.053, -.414, 2.973), .006, .034, .18),
        ((.053, -.414, 2.973), .006, .034, .18),
        ((0, -.442, 2.835), .006, .050, .22),
    ]
    for idx, (center, inner, outer, strength) in enumerate(centers):
        dist = nt.nodes.new('ShaderNodeVectorMath')
        dist.operation = 'DISTANCE'
        dist.location = (-790, -260 - idx * 105)
        dist.inputs[1].default_value = center
        nt.links.new(geom.outputs['Position'], dist.inputs[0])
        mr = nt.nodes.new('ShaderNodeMapRange')
        mr.location = (-590, -260 - idx * 105)
        mr.clamp = True
        mr.inputs['From Min'].default_value = inner
        mr.inputs['From Max'].default_value = outer
        mr.inputs['To Min'].default_value = strength
        mr.inputs['To Max'].default_value = 0
        nt.links.new(dist.outputs['Value'], mr.inputs['Value'])
        masks.append(mr.outputs['Result'])
    add = None
    for idx, socket in enumerate(masks):
        if add is None:
            add = socket
        else:
            node = nt.nodes.new('ShaderNodeMath')
            node.operation = 'ADD'
            node.use_clamp = True
            node.location = (-330 + idx * 15, -330 - idx * 70)
            nt.links.new(add, node.inputs[0])
            nt.links.new(socket, node.inputs[1])
            add = node.outputs[0]
    blush = nt.nodes.new('ShaderNodeMixRGB')
    blush.blend_type = 'MIX'
    blush.location = (70, 80)
    blush.inputs[2].default_value = (.32, .065, .038, 1)
    nt.links.new(add, blush.inputs[0])
    nt.links.new(ramp.outputs['Color'], blush.inputs[1])
    nt.links.new(blush.outputs['Color'], bs.inputs['Base Color'])

    rough_noise = nt.nodes.new('ShaderNodeTexNoise')
    rough_noise.location = (-250, -30)
    rough_noise.inputs['Scale'].default_value = 245
    rough_noise.inputs['Detail'].default_value = 3
    rough_noise.inputs['Roughness'].default_value = .68
    nt.links.new(tex.outputs['Generated'], rough_noise.inputs['Vector'])
    rough_map = nt.nodes.new('ShaderNodeMapRange')
    rough_map.location = (10, -70)
    rough_map.clamp = True
    rough_map.inputs['From Min'].default_value = .22
    rough_map.inputs['From Max'].default_value = .78
    rough_map.inputs['To Min'].default_value = .35
    rough_map.inputs['To Max'].default_value = .52
    nt.links.new(rough_noise.outputs['Fac'], rough_map.inputs['Value'])
    nt.links.new(rough_map.outputs['Result'], bs.inputs['Roughness'])

    pores = nt.nodes.new('ShaderNodeTexNoise')
    pores.location = (-240, -560)
    pores.inputs['Scale'].default_value = 520
    pores.inputs['Detail'].default_value = 2
    pores.inputs['Roughness'].default_value = .62
    nt.links.new(tex.outputs['Generated'], pores.inputs['Vector'])
    bump = nt.nodes.new('ShaderNodeBump')
    bump.location = (390, -250)
    bump.inputs['Strength'].default_value = .028
    bump.inputs['Distance'].default_value = .00020
    nt.links.new(pores.outputs['Fac'], bump.inputs['Height'])
    nt.links.new(bump.outputs['Normal'], bs.inputs['Normal'])

    if 'Emission Color' in bs.inputs:
        emission_mix = nt.nodes.new('ShaderNodeMixRGB')
        emission_mix.blend_type = 'MULTIPLY'
        emission_mix.inputs[0].default_value = 1.0
        emission_mix.inputs[2].default_value = (.0020, .0017, .0010, 1)
        nt.links.new(blush.outputs['Color'], emission_mix.inputs[1])
        nt.links.new(emission_mix.outputs['Color'], bs.inputs['Emission Color'])
        bs.inputs['Emission Strength'].default_value = 2.5
    return mat


def rebuild_hair_materials():
    native = [m for m in bpy.data.materials if m.name.startswith('AstraChar2 R4 Native blonde')]
    for mat in native:
        mat.use_nodes = True
        nt = mat.node_tree
        nt.nodes.clear()
        out = nt.nodes.new('ShaderNodeOutputMaterial')
        hair = nt.nodes.new('ShaderNodeBsdfHairPrincipled')
        try:
            hair.parametrization = 'DIRECT'
        except Exception:
            pass
        info = nt.nodes.new('ShaderNodeHairInfo')
        ramp = nt.nodes.new('ShaderNodeValToRGB')
        ramp.color_ramp.elements[0].position = 0
        ramp.color_ramp.elements[0].color = (.030, .012, .004, 1)
        ramp.color_ramp.elements[1].position = .66
        ramp.color_ramp.elements[1].color = (.16, .085, .030, 1)
        warm = ramp.color_ramp.elements.new(.22)
        warm.color = (.070, .030, .010, 1)
        nt.links.new(info.outputs['Intercept'], ramp.inputs['Fac'])
        if 'Color' in hair.inputs:
            nt.links.new(ramp.outputs['Color'], hair.inputs['Color'])
        for key, value in [('Roughness', .34), ('Radial Roughness', .30), ('Coat', .25), ('IOR', 1.48)]:
            if key in hair.inputs:
                hair.inputs[key].default_value = value
        nt.links.new(hair.outputs[0], out.inputs['Surface'])
    for mat in bpy.data.materials:
        if not mat.name.startswith('AstraChar2 R4 Portable blonde'):
            continue
        for node in mat.node_tree.nodes:
            if node.type == 'BSDF_PRINCIPLED':
                node.inputs['Base Color'].default_value = (.14, .072, .026, 1)
                node.inputs['Roughness'].default_value = .38
    scalp = bpy.data.materials.get('AstraChar2 R4 scalp beneath roots')
    if scalp:
        for node in scalp.node_tree.nodes:
            if node.type == 'BSDF_PRINCIPLED':
                node.inputs['Base Color'].default_value = (.035, .007, .002, 1)


def reshape_hair(iteration):
    reports = []
    strength = 1.0 + .12 * max(0, min(iteration, 5) - 1)
    for cu in [o for o in bpy.data.objects if o.type == 'CURVES' and o.name.startswith('AstraChar2_R5_Curves_MPFB_')]:
        label = cu.name.removeprefix('AstraChar2_R5_Curves_')
        ctl = bpy.data.objects['AstraChar2_R5_Control_' + label]
        portable = bpy.data.objects['AstraChar2_R5_Strands_' + label]
        n = int(cu['groom_strands'])
        k = int(cu['groom_points_per_strand'])
        ek = int(cu['export_points_per_strand'])
        raw = np.empty(n * k * 3, np.float32)
        ctl.data.vertices.foreach_get('co', raw)
        old = raw.reshape(n, k, 3)
        p = old.copy()
        t = np.linspace(0, 1, k)
        if 'Braids' in label:
            sign = -1 if '_L_' in label else 1
            axis = old.mean(axis=0)
            residual = old - axis[None, :, :]
            u = t
            target = np.zeros_like(axis)
            root = axis[0].copy()
            target[:, 0] = root[0] + sign * (.045 * np.sin(np.pi * u) + .042 * u)
            target[:, 1] = root[1] + .335 * u
            target[:, 2] = root[2] - .072 * u - .018 * np.sin(np.pi * u)
            fade = np.clip((u - .015) / .10, 0, 1)
            target = axis * (1 - fade[:, None]) + target * fade[:, None]
            p = target[None, :, :] + residual * .72
        elif 'ScalpBed' not in label:
            sign = -1 if '_L_' in label else 1
            group = np.arange(n) // 100
            phase = (group * 2.399963229728653) % math.tau
            fade = np.clip((t - .025) / .16, 0, 1)
            body = np.sin(np.pi * t) ** 1.15
            amount = (.034 if 'Front' in label else .049 if 'Side' in label else .035) * strength
            p[:, :, 0] += sign * amount * (body * fade)[None, :]
            amp = (.013 if 'Front' in label else .019 if 'Side' in label else .017) * strength
            wave = np.sin(t[None, :] * math.tau * 2.25 + phase[:, None]) * body[None, :] * fade[None, :]
            p[:, :, 0] += sign * amp * wave
            p[:, :, 1] += amp * .55 * np.sin(t[None, :] * math.tau * 1.72 + phase[:, None] * .7) * body[None, :] * fade[None, :]
            p[:, :, 1] -= .105 * (t ** 2)[None, :] * fade[None, :]
            p[:, :, 2] += .021 * np.sin(np.pi * np.clip(t / .34, 0, 1))[None, :] * (1 - t)[None, :] * fade[None, :]
        else:
            continue
        delta = p - old
        ctl.data.vertices.foreach_set('co', p.ravel())
        ctl.data.update()
        cu.data.position_data.foreach_set('vector', p.ravel())
        sample = np.unique(np.r_[np.arange(0, k, 2), k - 1])
        assert len(sample) == ek
        tubes = np.empty(len(portable.data.vertices) * 3, np.float32)
        portable.data.vertices.foreach_get('co', tubes)
        tubes = tubes.reshape(n, ek, 3, 3)
        tubes += delta[:, sample, None, :]
        portable.data.vertices.foreach_set('co', tubes.ravel())
        portable.data.update()
        if 'Braids' in label:
            for ob in (ctl, portable):
                ob.vertex_groups.clear()
                group = ob.vertex_groups.new(name='Head')
                group.add(range(len(ob.data.vertices)), 1.0, 'REPLACE')
        reports.append({'group': label, 'strands': n, 'max_displacement_m': float(np.linalg.norm(delta, axis=2).max())})
    return reports


def rebuild_eyes_and_features(head, arm):
    tree = BVHTree.FromObject(head, bpy.context.evaluated_depsgraph_get())
    lid_mat = material('AstraChar2 likeness living lids', (.38, .14, .085), .43, .08, .2, .16)
    lash_mat = material('AstraChar2 likeness lash line', (.055, .018, .009), .48)
    tear_mat = material('AstraChar2 likeness tear duct', (.48, .12, .095), .22, .55, .06, .18)
    lip_mat = material('AstraChar2 likeness lips', (.14, .022, .014), .38, .10, .16, .12)
    mouth_mat = material('AstraChar2 likeness closed mouth line', (.075, .018, .014), .52)

    for side, cx in [('L', -.05284), ('R', .05284)]:
        cz = 2.97255
        u = np.linspace(-1, 1, 43)
        upper = []
        lower = []
        for q in u:
            x = cx + .0210 * q
            arch = math.sqrt(max(0, 1 - q * q))
            zu = cz + .0033 * arch + (-.0019 * q if side == 'L' else .0019 * q)
            zl = cz - .0063 * arch + (-.0008 * q if side == 'L' else .0008 * q)
            upper.append((x, front_surface(tree, x, zu) - .0011, zu))
            lower.append((x, front_surface(tree, x, zl) - .0009, zl))
        tube(f'AstraChar2_Likeness_UpperLid_{side}', upper, np.linspace(.00255, .00170, len(upper)), lid_mat, arm, 10)
        tube(f'AstraChar2_Likeness_LowerLid_{side}', lower, .00110, lid_mat, arm, 8)
        patch_verts = []
        patch_faces = []
        patch_rows = 5
        for row in range(patch_rows):
            v = row / (patch_rows - 1)
            for q in u:
                x = cx + .0210 * q
                arch = math.sqrt(max(0, 1 - q * q))
                slope = -.0016 * q if side == 'L' else .0016 * q
                z_top = cz + .0090 * arch + slope
                z_low = cz + .0018 * arch + slope
                z = z_top * (1 - v) + z_low * v
                y = -.4095 - .0012 * math.sin(math.pi * v) * arch
                patch_verts.append((x, y, z))
        for row in range(patch_rows - 1):
            for col in range(len(u) - 1):
                a = row * len(u) + col
                patch_faces.append((a, a + 1, a + len(u) + 1, a + len(u)))
        mesh_object(f'AstraChar2_Likeness_UpperLidPatch_{side}', patch_verts, patch_faces, lid_mat, arm)
        lash_path = [(x, y - .00055, z + .00025) for x, y, z in upper[5:-4]]
        tube(f'AstraChar2_Likeness_LashLine_{side}', lash_path, .00042, lash_mat, arm, 7)
        for j, idx in enumerate(range(8, 38, 3)):
            x, y, z = upper[idx]
            frac = abs(u[idx])
            length = .0026 + .0025 * frac
            direction = -1 if side == 'L' else 1
            path = [(x, y - .0004, z), (x + direction * .0006 * frac, y - length, z + .0015 + .0012 * frac)]
            tube(f'AstraChar2_Likeness_Lash_{side}_{j:02}', path, [.00032, .00007], lash_mat, arm, 6)
        inner_x = cx + (.0206 if side == 'L' else -.0206)
        inner_z = cz - .0018
        bpy.ops.mesh.primitive_uv_sphere_add(segments=20, ring_count=10, location=(inner_x, front_surface(tree, inner_x, inner_z) - .0018, inner_z))
        tear = bpy.context.object
        tear.name = f'AstraChar2_Likeness_TearDuct_{side}'
        tear.scale = (.0031, .00135, .00215)
        bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
        tear.data.materials.append(tear_mat)
        bind_head(tear, arm)

        eye = bpy.data.objects[f'AstraChar2_Eyeball_{side}']
        sclera = eye.data.materials[0]
        for node in sclera.node_tree.nodes:
            if node.type == 'BSDF_PRINCIPLED':
                node.inputs['Base Color'].default_value = (.38, .34, .29, 1)
                node.inputs['Roughness'].default_value = .31
                node.inputs['Subsurface Weight'].default_value = .08
                if 'Coat Weight' in node.inputs:
                    node.inputs['Coat Weight'].default_value = .16
        for stem in ('Iris', 'Pupil'):
            ob = bpy.data.objects[f'AstraChar2_{stem}_{side}']
            for v in ob.data.vertices:
                v.co.z -= .0022

    iris = bpy.data.materials['AstraChar2 hazel green iris']
    iris.use_nodes = True
    nt = iris.node_tree
    nt.nodes.clear()
    out = nt.nodes.new('ShaderNodeOutputMaterial')
    bs = nt.nodes.new('ShaderNodeBsdfPrincipled')
    bs.inputs['Roughness'].default_value = .22
    if 'Coat Weight' in bs.inputs:
        bs.inputs['Coat Weight'].default_value = .72
        bs.inputs['Coat Roughness'].default_value = .055
    tex = nt.nodes.new('ShaderNodeTexCoord')
    sep = nt.nodes.new('ShaderNodeVectorMath')
    sep.operation = 'SUBTRACT'
    sep.inputs[1].default_value = (.5, .5, 0)
    length = nt.nodes.new('ShaderNodeVectorMath')
    length.operation = 'LENGTH'
    ramp = nt.nodes.new('ShaderNodeValToRGB')
    ramp.color_ramp.elements.remove(ramp.color_ramp.elements[1])
    stops = [
        (0.0, (.075, .026, .004, 1)),
        (.28, (.050, .060, .010, 1)),
        (.68, (.018, .050, .012, 1)),
        (.88, (.018, .040, .012, 1)),
    ]
    ramp.color_ramp.elements[0].position = stops[0][0]
    ramp.color_ramp.elements[0].color = stops[0][1]
    for pos, col in stops[1:]:
        e = ramp.color_ramp.elements.new(pos)
        e.color = col
    nt.links.new(tex.outputs['UV'], sep.inputs[0])
    nt.links.new(sep.outputs['Vector'], length.inputs[0])
    nt.links.new(length.outputs['Value'], ramp.inputs['Fac'])
    nt.links.new(ramp.outputs['Color'], bs.inputs['Base Color'])
    nt.links.new(bs.outputs['BSDF'], out.inputs['Surface'])

    for side in ('L', 'R'):
        brow = bpy.data.objects[f'AstraChar2_Eyebrows_{side}']
        center = np.mean([v.co[:] for v in brow.data.vertices], axis=0)
        for layer, dz in enumerate((-.0011, .00125)):
            dup = brow.copy()
            dup.data = brow.data.copy()
            dup.name = f'AstraChar2_Likeness_BrowFill_{side}_{layer}'
            bpy.context.scene.collection.objects.link(dup)
            for v in dup.data.vertices:
                taper = max(0.35, 1 - abs(float(v.co.x - center[0])) / .055)
                v.co.z += dz * taper
                v.co.y -= .00028 * taper
    brow_mat = bpy.data.materials.get('AstraChar2 warm blonde eyebrows')
    if brow_mat:
        for node in brow_mat.node_tree.nodes:
            if node.type == 'BSDF_PRINCIPLED':
                node.inputs['Base Color'].default_value = (.115, .045, .012, 1)
                node.inputs['Roughness'].default_value = .58

    lip_z = 2.8335
    rows = 9
    cols = 49
    verts = []
    faces = []
    for row in range(rows):
        v = row / (rows - 1)
        for col in range(cols):
            u = -1 + 2 * col / (cols - 1)
            width = .051
            x = width * u
            arch = math.sqrt(max(0, 1 - u * u))
            if v < .5:
                q = v / .5
                z = lip_z + .0003 + .0063 * arch * (1 - q)
                bulge = math.sin(math.pi * q) * .0020
            else:
                q = (v - .5) / .5
                z = lip_z - .0003 - .0073 * arch * q
                bulge = math.sin(math.pi * q) * .0025
            y = front_surface(tree, x, z) - .0010 - bulge
            verts.append((x, y, z))
    for r in range(rows - 1):
        for c in range(cols - 1):
            a = r * cols + c
            faces.append((a, a + 1, a + cols + 1, a + cols))
    lips = mesh_object('AstraChar2_Likeness_Lips', verts, faces, lip_mat, arm)
    solid = lips.modifiers.new('Lip thickness', 'SOLIDIFY')
    solid.thickness = .00065
    seam = []
    for u in np.linspace(-1, 1, 51):
        x = .0505 * u
        z = lip_z + .00015 * math.cos(math.pi * u)
        seam.append((x, front_surface(tree, x, z) - .0032, z))
    tube('AstraChar2_Likeness_MouthSeam', seam, .00042, mouth_mat, arm, 7)


def protected_digest(ob):
    arr = np.empty(len(ob.data.vertices) * 3, np.float32)
    ob.data.vertices.foreach_get('co', arr)
    return float(arr.sum()), len(ob.data.vertices), len(ob.data.polygons)


def main(iteration):
    bpy.ops.wm.open_mainfile(filepath=str(BASE))
    arm = bpy.data.objects['Armature']
    reset_pose(arm)
    assert len(arm.data.bones) == 121 and len(bpy.data.actions) == 0
    protected_names = [o.name for o in bpy.data.objects if o.type == 'MESH' and any(x in o.name for x in ('Cuirass', 'Gorget', 'Pauldron', 'Undersleeve', 'char1'))]
    before = {n: protected_digest(bpy.data.objects[n]) for n in protected_names}
    lid_vertices = sculpt_lid_soft_tissue(bpy.data.objects['AstraChar2_Mpfb_Head'])
    skin = rebuild_skin()
    rebuild_hair_materials()
    hair_report = reshape_hair(iteration)
    rebuild_eyes_and_features(bpy.data.objects['AstraChar2_Mpfb_Head'], arm)
    reset_pose(arm)
    after = {n: protected_digest(bpy.data.objects[n]) for n in protected_names}
    assert before == after
    assert len(arm.data.bones) == 121 and len(bpy.data.actions) == 0
    out_model = ROOT / f'models/astra_character_v2_likeness_i{iteration:02}.blend'
    bpy.context.preferences.filepaths.save_version = 0
    bpy.ops.wm.save_as_mainfile(filepath=str(out_model))
    report = {
        'iteration': iteration,
        'source': str(BASE.relative_to(ROOT)),
        'output': str(out_model.relative_to(ROOT)),
        'bones': len(arm.data.bones),
        'actions': len(bpy.data.actions),
        'protected_armor_cloth_body_geometry_unchanged': before == after,
        'hair_groups': hair_report,
        'skin': {'sss_weight': .24, 'sss_scale_m': .0032, 'radius': [1.0, .42, .18], 'spec_anchor': [.95, .90, .82], 'masked_emission_strength': 2.5},
        'lid_soft_tissue_vertices_adjusted': lid_vertices,
        'features': {'lid_meshes': 6, 'lash_lines': 2, 'individual_lashes': 20, 'tear_ducts': 2, 'brow_fill_layers': 4, 'closed_lip_shell': True},
    }
    (OUT / f'likeness_i{iteration:02}_build.json').write_text(json.dumps(report, indent=2) + '\n')
    print('LIKENESS_BUILD_PASS', out_model, flush=True)


if __name__ == '__main__':
    args = sys.argv[sys.argv.index('--') + 1:]
    main(int(args[0]))

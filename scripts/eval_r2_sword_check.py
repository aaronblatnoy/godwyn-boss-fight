import bpy, os, math
from mathutils import Vector, Euler
HOME=os.path.expanduser("~")
bpy.ops.wm.open_mainfile(filepath=f"{HOME}/godwyn-boss-fight/models/godwyn_face.blend")
scn=bpy.context.scene
char=max((o for o in scn.objects if o.type=="MESH" and len(o.vertex_groups)>0), key=lambda o:len(o.data.vertices))
arm=next(o for o in scn.objects if o.type=="ARMATURE")
sword=next(o for o in scn.objects if o.type=="MESH" and "sword" in o.name.lower())
for e in ("BLENDER_EEVEE_NEXT","BLENDER_EEVEE"):
    try: scn.render.engine=e; break
    except: pass
ee=scn.eevee
for a,v in (("use_raytracing",True),("use_shadows",True),("use_ssr",True),("use_gtao",True)):
    if hasattr(ee,a):
        try: setattr(ee,a,v)
        except: pass
if hasattr(ee,"taa_render_samples"): ee.taa_render_samples=96
scn.render.image_settings.file_format="PNG"
scn.view_settings.view_transform="AgX"
def bbox(o,ev=False):
    ob=o
    if ev:
        dg=bpy.context.evaluated_depsgraph_get(); ob=o.evaluated_get(dg)
    pts=[o.matrix_world@Vector(c) for c in ob.bound_box]
    return (Vector((min(p.x for p in pts),min(p.y for p in pts),min(p.z for p in pts))),
            Vector((max(p.x for p in pts),max(p.y for p in pts),max(p.z for p in pts))))
bmn,bmx=bbox(char); center=(bmn+bmx)/2; H=bmx.z-bmn.z
w=bpy.data.worlds.new("W"); scn.world=w; w.use_nodes=True
nt=w.node_tree; nt.nodes.clear()
bg=nt.nodes.new("ShaderNodeBackground"); ou=nt.nodes.new("ShaderNodeOutputWorld")
bg.inputs["Color"].default_value=(0.012,0.013,0.018,1); bg.inputs["Strength"].default_value=0.4
nt.links.new(bg.outputs["Background"],ou.inputs["Surface"])
def area(n,loc,tg,sz,col,pw):
    o=bpy.data.objects.get(n)
    if o: bpy.data.objects.remove(o,do_unlink=True)
    d=bpy.data.lights.new(n,"AREA"); d.size=sz; d.color=col; d.energy=pw
    ob=bpy.data.objects.new(n,d); scn.collection.objects.link(ob); ob.location=loc
    ob.rotation_euler=(Vector(tg)-Vector(loc)).normalized().to_track_quat("-Z","Y").to_euler()
def relight(c,bx,h):
    t=(c.x,c.y,c.z+0.12*h)
    area("K",(c.x-1.0*h,c.y-1.3*h,bx.z+0.5*h),t,1.1*h,(1.0,0.78,0.45),220*h*h)
    area("R",(c.x+1.2*h,c.y+1.0*h,c.z+0.5*h),t,0.7*h,(0.45,0.6,1.0),130*h*h)
    area("F",(c.x+1.2*h,c.y-1.1*h,c.z),t,1.6*h,(0.4,0.5,0.85),26*h*h)
relight(center,bmx,H)
def shoot(n,foc,look,fit,yaw,path,res=(1080,1350)):
    o=bpy.data.objects.get(n)
    if o: bpy.data.objects.remove(o,do_unlink=True)
    scn.render.resolution_x,scn.render.resolution_y=res
    cd=bpy.data.cameras.new(n); cd.lens=foc; cd.sensor_fit="VERTICAL"; cd.sensor_height=36
    cam=bpy.data.objects.new(n,cd); scn.collection.objects.link(cam)
    fov=2*math.atan(36/(2*foc)); dist=(fit/2*1.18)/math.tan(fov/2)
    y=math.radians(yaw); off=Vector((math.sin(y),-math.cos(y),0))*dist
    cam.location=look+off+Vector((0,0,0.03*H))
    cam.rotation_euler=(look-cam.location).normalized().to_track_quat("-Z","Y").to_euler()
    scn.camera=cam; scn.render.filepath=path; bpy.ops.render.render(write_still=True)
    print("wrote",path)
# rest pose, framed on the sword region (right side of char)
smn,smx=bbox(sword); sc=(smn+smx)/2
print("SWORD rest bbox z",round(smn.z,2),round(smx.z,2),"len",round(smx.z-smn.z,2))
shoot("SwordRest",50,Vector((sc.x,sc.y,sc.z)),(smx.z-smn.z)*1.15,20.0,"/tmp/eval_sword_rest.png")
# hand-grip closeup at rest
rh=arm.data.bones.get("RightHand"); rhw=arm.matrix_world@rh.head_local
shoot("Grip",95,Vector((rhw.x,rhw.y,rhw.z-0.15)),0.55*H,35.0,"/tmp/eval_grip_rest.png",res=(1200,1200))
print("DONE")

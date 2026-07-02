"""Generate assets/earth_globe.{fbx,glb} and assets/satellite.{fbx,glb} with bpy.

Earth mesh is built manually so the UV mapping is exact equirectangular:
vertex at longitude λ, latitude φ gets u=(λ+180)/360, v=(φ+90)/180, with the
mesh oriented so that after Blender→Unity FBX axis conversion longitude 0
faces Unity +X and the north pole is Unity +Y — matching SatelliteGlobe.cs
(ECEF X,Y,Z → Unity X,Z,Y).
"""
import math
import os

import bpy

OUT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "assets")
TEX = os.path.join(OUT, "textures", "earth_bmng_4k.jpg")
RADIUS = 0.5  # meters → 1 m diameter globe


def clear_scene():
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete()
    for block in (bpy.data.meshes, bpy.data.materials, bpy.data.images):
        for item in list(block):
            if item.users == 0:
                block.remove(item)


def smooth(obj):
    obj.data.polygons.foreach_set("use_smooth", [True] * len(obj.data.polygons))
    obj.data.update()


# ---------------------------------------------------------------- earth ----

def build_earth():
    SEG, RING = 96, 48  # longitude, latitude divisions
    verts, faces = [], []
    # rings from south (-90) to north (+90), duplicated seam column for UVs
    for i in range(RING + 1):
        phi = math.pi * (i / RING - 0.5)
        for j in range(SEG + 1):
            lam = 2 * math.pi * (j / SEG) - math.pi
            # Blender Z-up: x=cosφcosλ, y=cosφsinλ, z=sinφ
            verts.append((
                RADIUS * math.cos(phi) * math.cos(lam),
                RADIUS * math.cos(phi) * math.sin(lam),
                RADIUS * math.sin(phi),
            ))
    cols = SEG + 1
    for i in range(RING):
        for j in range(SEG):
            a = i * cols + j
            b = a + 1
            c = a + cols + 1
            d = a + cols
            if i == 0:
                faces.append((a, c, d))          # south pole fan (a is a pole vertex)
            elif i == RING - 1:
                faces.append((a, b, d))          # north pole fan
            else:
                faces.append((a, b, c, d))

    mesh = bpy.data.meshes.new("EarthGlobe")
    mesh.from_pydata(verts, [], faces)
    mesh.validate()

    uv = mesh.uv_layers.new(name="UVMap")
    for poly in mesh.polygons:
        for li in poly.loop_indices:
            vi = mesh.loops[li].vertex_index
            i, j = divmod(vi, cols)
            uv.data[li].uv = (j / SEG, i / RING)

    obj = bpy.data.objects.new("EarthGlobe", mesh)
    bpy.context.collection.objects.link(obj)
    smooth(obj)

    mat = bpy.data.materials.new("Earth")
    mat.use_nodes = True
    bsdf = mat.node_tree.nodes["Principled BSDF"]
    bsdf.inputs["Roughness"].default_value = 0.9
    img = bpy.data.images.load(TEX)
    tex = mat.node_tree.nodes.new("ShaderNodeTexImage")
    tex.image = img
    mat.node_tree.links.new(tex.outputs["Color"], bsdf.inputs["Base Color"])
    obj.data.materials.append(mat)
    return obj


# ------------------------------------------------------------ satellite ----

def flat_mat(name, rgba, metallic=0.0, roughness=0.5):
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    bsdf = mat.node_tree.nodes["Principled BSDF"]
    bsdf.inputs["Base Color"].default_value = rgba
    bsdf.inputs["Metallic"].default_value = metallic
    bsdf.inputs["Roughness"].default_value = roughness
    return mat

def add_box(name, size, loc, mat):
    bpy.ops.mesh.primitive_cube_add(size=1, location=loc)
    o = bpy.context.active_object
    o.name = name
    o.scale = (size[0] / 2, size[1] / 2, size[2] / 2)
    bpy.ops.object.transform_apply(scale=True)
    o.data.materials.append(mat)
    return o

def build_satellite():
    gold = flat_mat("SatGoldFoil", (0.75, 0.55, 0.12, 1), metallic=0.9, roughness=0.35)
    panel = flat_mat("SatSolarPanel", (0.05, 0.10, 0.30, 1), metallic=0.3, roughness=0.25)
    silver = flat_mat("SatSilver", (0.75, 0.75, 0.78, 1), metallic=0.9, roughness=0.4)
    white = flat_mat("SatWhite", (0.85, 0.85, 0.82, 1), roughness=0.6)

    parts = []
    # bus (body) wrapped in gold foil, long axis = Blender Y
    parts.append(add_box("Bus", (0.10, 0.16, 0.10), (0, 0, 0), gold))
    # solar wings on ±X with connecting booms
    for sx in (-1, 1):
        parts.append(add_box("Boom", (0.06, 0.02, 0.01), (sx * 0.08, 0, 0), silver))
        parts.append(add_box("Panel", (0.22, 0.12, 0.005), (sx * 0.22, 0, 0), panel))
    # dish antenna: shallow cone facing -Y (nadir when oriented to Earth)
    bpy.ops.mesh.primitive_cone_add(vertices=24, radius1=0.055, radius2=0.012,
                                    depth=0.03, location=(0, -0.095, 0),
                                    rotation=(math.pi / 2, 0, 0))
    dish = bpy.context.active_object
    dish.name = "Dish"
    dish.data.materials.append(white)
    smooth(dish)
    parts.append(dish)
    # feed rod from dish center
    bpy.ops.mesh.primitive_cylinder_add(vertices=12, radius=0.004, depth=0.05,
                                        location=(0, -0.115, 0),
                                        rotation=(math.pi / 2, 0, 0))
    rod = bpy.context.active_object
    rod.name = "Rod"
    rod.data.materials.append(silver)
    parts.append(rod)
    # aft antenna
    bpy.ops.mesh.primitive_cylinder_add(vertices=8, radius=0.003, depth=0.09,
                                        location=(0, 0.11, 0),
                                        rotation=(math.pi / 2, 0, 0))
    ant = bpy.context.active_object
    ant.name = "Antenna"
    ant.data.materials.append(silver)
    parts.append(ant)

    bpy.ops.object.select_all(action="DESELECT")
    for p in parts:
        p.select_set(True)
    bpy.context.view_layer.objects.active = parts[0]
    bpy.ops.object.join()
    sat = bpy.context.active_object
    sat.name = "Satellite"
    return sat


# -------------------------------------------------------------- exports ----

def export(obj, basename):
    bpy.ops.object.select_all(action="DESELECT")
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj
    bpy.ops.export_scene.fbx(
        filepath=os.path.join(OUT, basename + ".fbx"),
        use_selection=True, path_mode="RELATIVE", embed_textures=False,
        apply_scale_options="FBX_SCALE_UNITS",
    )
    bpy.ops.export_scene.gltf(
        filepath=os.path.join(OUT, basename + ".glb"),
        use_selection=True, export_format="GLB",
    )
    print("exported", basename, "verts:", len(obj.data.vertices),
          "tris≈", sum(len(p.vertices) - 2 for p in obj.data.polygons))


clear_scene()
earth = build_earth()
export(earth, "earth_globe")
earth.hide_set(True)
sat = build_satellite()
export(sat, "satellite")
print("done")

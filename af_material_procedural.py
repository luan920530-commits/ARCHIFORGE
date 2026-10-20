# -*- coding: utf-8 -*-

# ╔══════════════════════════════════════════════════════════╗
# ║        ARCHIFORGE — af_material_procedural.py           ║
# ║        Recetas de nodos para materiales procedurales    ║
# ║        GPL v3 — ArchiForge Devs                         ║
# ╚══════════════════════════════════════════════════════════╝

# <pep8 compliant>

"""Node recipes for ArchiForge's procedural materials (no ``bpy``).

A *recipe* is a plain description of a shader node tree::

    {"nodes": [{"id": "brick", "type": "ShaderNodeTexBrick",
                "loc": (-450, 100), "props": {...}, "inputs": {...}}, ...],
     "links": [("coord", "Object", "sep", "Vector"), ...]}

``af_material._create_recipe_material`` turns it into real nodes. Keeping
the recipes declarative lets ``tests/test_material_procedural.py`` check
node types, socket names and link consistency without Blender, and makes
every recipe a function of the catalogue colour so one builder serves
light floor wood, dark door wood, etc.

Textures use *Object* coordinates (metres in object space), so sizes
below are physical: bricks 24 x 7 cm, structural blocks 39 x 19 cm. Walls
run along any horizontal direction, so the brick recipe maps the
horizontal axis to ``x + y``: exact for walls aligned with X or Y and
stretched by up to 41 % on diagonal walls (a texture, not the geometry).
Only node types and socket names that exist from Blender 3.3 to 4.2 are
used.
"""

# Node names other modules rely on (``nodes.get("Principled BSDF")``).
BSDF_NODE_NAME = "Principled BSDF"
OUTPUT_NODE_NAME = "Material Output"

# Recipe kinds exposed to the catalogue.
BRICK = 'BRICK'
CERAMIC = 'CERAMIC'
WOOD = 'WOOD'
CONCRETE = 'CONCRETE'
MARBLE = 'MARBLE'
CLAY = 'CLAY'
PLASTER = 'PLASTER'
FABRIC = 'FABRIC'

# Node types a recipe may use (all present in Blender 3.3 LTS and 4.x).
ALLOWED_NODE_TYPES = frozenset({
    "ShaderNodeTexCoord", "ShaderNodeSeparateXYZ", "ShaderNodeCombineXYZ",
    "ShaderNodeMath", "ShaderNodeMapRange", "ShaderNodeTexBrick",
    "ShaderNodeTexNoise", "ShaderNodeTexWave", "ShaderNodeValToRGB",
    "ShaderNodeMixRGB", "ShaderNodeBump", "ShaderNodeBsdfPrincipled",
    "ShaderNodeOutputMaterial",
})

# Output / input socket names per node type, used by the recipe checks.
NODE_SOCKETS = {
    "ShaderNodeTexCoord": ((), ("Generated", "Normal", "UV", "Object",
                                "Camera", "Window", "Reflection")),
    "ShaderNodeSeparateXYZ": (("Vector",), ("X", "Y", "Z")),
    "ShaderNodeCombineXYZ": (("X", "Y", "Z"), ("Vector",)),
    "ShaderNodeMath": ((0, 1, 2), ("Value",)),
    "ShaderNodeMapRange": (("Value", "From Min", "From Max", "To Min",
                            "To Max", "Steps"), ("Result",)),
    "ShaderNodeTexBrick": (("Vector", "Color1", "Color2", "Mortar", "Scale",
                            "Mortar Size", "Mortar Smooth", "Bias",
                            "Brick Width", "Row Height"), ("Color", "Fac")),
    "ShaderNodeTexNoise": (("Vector", "W", "Scale", "Detail", "Roughness",
                            "Distortion"), ("Fac", "Color")),
    "ShaderNodeTexWave": (("Vector", "Scale", "Distortion", "Detail",
                           "Detail Scale", "Detail Roughness",
                           "Phase Offset"), ("Color", "Fac")),
    "ShaderNodeValToRGB": (("Fac",), ("Color", "Alpha")),
    "ShaderNodeMixRGB": (("Fac", "Color1", "Color2"), ("Color",)),
    "ShaderNodeBump": (("Strength", "Distance", "Height", "Normal"),
                       ("Normal",)),
    "ShaderNodeBsdfPrincipled": (("Base Color", "Metallic", "Roughness",
                                  "Alpha", "Normal"), ("BSDF",)),
    "ShaderNodeOutputMaterial": (("Surface", "Volume", "Displacement"), ()),
}

MORTAR_COLOR = (0.78, 0.76, 0.72, 1.0)
GROUT_COLOR = (0.55, 0.53, 0.50, 1.0)


# ════════════════════════════════════════════════════════════
#  Colour helpers
# ════════════════════════════════════════════════════════════
def rgba(color):
    """Return a 4-tuple of floats clamped to [0, 1]."""
    values = [max(0.0, min(1.0, float(c))) for c in tuple(color)[:4]]
    while len(values) < 3:
        values.append(values[-1] if values else 0.8)
    if len(values) == 3:
        values.append(1.0)
    return tuple(values)


def shade(color, factor):
    """Scale the RGB part of ``color`` by ``factor`` (alpha untouched)."""
    r, g, b, a = rgba(color)
    return rgba((r * factor, g * factor, b * factor, a))


def _clamp01(value):
    return max(0.0, min(1.0, float(value)))


# ════════════════════════════════════════════════════════════
#  Recipe building blocks
# ════════════════════════════════════════════════════════════
def node(node_id, node_type, loc, inputs=None, props=None, ramp=None,
         name=None):
    spec = {"id": node_id, "type": node_type, "loc": tuple(loc)}
    if inputs:
        spec["inputs"] = dict(inputs)
    if props:
        spec["props"] = dict(props)
    if ramp:
        spec["ramp"] = [(float(pos), rgba(col)) for pos, col in ramp]
    if name:
        spec["name"] = name
    return spec


def _shader_tail(rough, metal, bsdf_inputs=None):
    """Principled BSDF + output nodes shared by every recipe."""
    inputs = {"Roughness": _clamp01(rough), "Metallic": _clamp01(metal)}
    if bsdf_inputs:
        inputs.update(bsdf_inputs)
    return [
        node("bsdf", "ShaderNodeBsdfPrincipled", (200, 0), inputs=inputs,
             name=BSDF_NODE_NAME),
        node("out", "ShaderNodeOutputMaterial", (520, 0),
             name=OUTPUT_NODE_NAME),
    ], [("bsdf", "BSDF", "out", "Surface")]


def _wall_mapping_nodes():
    """Object coords → (x + y, z, 0) so bricks follow any wall direction."""
    return [
        node("coord", "ShaderNodeTexCoord", (-1500, 0)),
        node("sep", "ShaderNodeSeparateXYZ", (-1300, 0)),
        node("add", "ShaderNodeMath", (-1100, 80), inputs={2: 0.0},
             props={"operation": 'ADD'}),
        node("comb", "ShaderNodeCombineXYZ", (-900, 0), inputs={"Z": 0.0}),
    ], [
        ("coord", "Object", "sep", "Vector"),
        ("sep", "X", "add", 0),
        ("sep", "Y", "add", 1),
        ("add", "Value", "comb", "X"),
        ("sep", "Z", "comb", "Y"),
    ]


# ════════════════════════════════════════════════════════════
#  Recipes
# ════════════════════════════════════════════════════════════
def recipe_brick(color, rough, metal, brick_width=0.24, row_height=0.07,
                 mortar_size=0.012, offset=0.5, mortar_color=MORTAR_COLOR,
                 color_variation=0.8):
    """Running-bond brick / block pattern with recessed mortar joints."""
    nodes, links = _wall_mapping_nodes()
    nodes += [
        node("brick", "ShaderNodeTexBrick", (-650, 150),
             props={"offset": float(offset), "offset_frequency": 2,
                    "squash": 1.0, "squash_frequency": 2},
             inputs={"Color1": rgba(color),
                     "Color2": shade(color, color_variation),
                     "Mortar": rgba(mortar_color), "Scale": 1.0,
                     "Mortar Size": float(mortar_size),
                     "Mortar Smooth": 0.1, "Bias": 0.0,
                     "Brick Width": float(brick_width),
                     "Row Height": float(row_height)}),
        node("noise", "ShaderNodeTexNoise", (-650, -200),
             inputs={"Scale": 18.0, "Detail": 4.0, "Roughness": 0.6}),
        node("mix", "ShaderNodeMixRGB", (-350, 150), inputs={"Fac": 0.25},
             props={"blend_type": 'MULTIPLY'}),
        node("rough", "ShaderNodeMapRange", (-350, -120),
             inputs={"From Min": 0.0, "From Max": 1.0,
                     "To Min": _clamp01(rough),
                     "To Max": _clamp01(rough + 0.15)}),
        node("bump", "ShaderNodeBump", (-350, -400),
             inputs={"Strength": 0.4, "Distance": 0.02},
             props={"invert": True}),
    ]
    links += [
        ("comb", "Vector", "brick", "Vector"),
        ("comb", "Vector", "noise", "Vector"),
        ("brick", "Color", "mix", "Color1"),
        ("noise", "Color", "mix", "Color2"),
        ("mix", "Color", "bsdf", "Base Color"),
        ("brick", "Fac", "rough", "Value"),
        ("rough", "Result", "bsdf", "Roughness"),
        ("brick", "Fac", "bump", "Height"),
        ("bump", "Normal", "bsdf", "Normal"),
    ]
    tail_nodes, tail_links = _shader_tail(rough, metal)
    return {"nodes": nodes + tail_nodes, "links": links + tail_links}


def recipe_ceramic(color, rough, metal, speckle_scale=12.0, variation=0.08):
    """Glazed ceramic: subtle tone variation, fine bump, glossy finish.

    No grid lines: ArchiForge floors already model tiles and grout joints
    as geometry, so the pattern must not be repeated by the texture.
    """
    nodes = [
        node("coord", "ShaderNodeTexCoord", (-1100, 0)),
        node("noise", "ShaderNodeTexNoise", (-800, 150),
             inputs={"Scale": float(speckle_scale), "Detail": 3.0,
                     "Roughness": 0.5}),
        node("ramp", "ShaderNodeValToRGB", (-550, 150),
             ramp=[(0.3, shade(color, 1.0 - variation)),
                   (0.7, shade(color, 1.0 + variation))]),
        node("fine", "ShaderNodeTexNoise", (-800, -200),
             inputs={"Scale": 150.0, "Detail": 2.0, "Roughness": 0.4}),
        node("bump", "ShaderNodeBump", (-350, -200),
             inputs={"Strength": 0.03, "Distance": 0.001}),
    ]
    links = [
        ("coord", "Object", "noise", "Vector"),
        ("coord", "Object", "fine", "Vector"),
        ("noise", "Fac", "ramp", "Fac"),
        ("ramp", "Color", "bsdf", "Base Color"),
        ("fine", "Fac", "bump", "Height"),
        ("bump", "Normal", "bsdf", "Normal"),
    ]
    tail_nodes, tail_links = _shader_tail(rough, metal)
    return {"nodes": nodes + tail_nodes, "links": links + tail_links}


def recipe_wood(color, rough, metal, bands_direction='X', grain_scale=30.0,
                distortion=6.0):
    """Wood grain from a distorted wave texture through a colour ramp.

    ``bands_direction`` is the axis across which the grain varies: 'Y'
    for planks running along X (floors, treads), 'X' for standing boards
    (doors, pickets), 'Z' for horizontal rails.
    """
    nodes = [
        node("coord", "ShaderNodeTexCoord", (-1100, 0)),
        node("wave", "ShaderNodeTexWave", (-800, 150),
             props={"wave_type": 'BANDS', "bands_direction": bands_direction,
                    "wave_profile": 'SIN'},
             inputs={"Scale": float(grain_scale),
                     "Distortion": float(distortion), "Detail": 3.0,
                     "Detail Scale": 1.2, "Detail Roughness": 0.5}),
        node("ramp", "ShaderNodeValToRGB", (-550, 150),
             ramp=[(0.0, shade(color, 0.65)), (0.5, rgba(color)),
                   (1.0, shade(color, 1.15))]),
        node("bump", "ShaderNodeBump", (-350, -200),
             inputs={"Strength": 0.1, "Distance": 0.002}),
    ]
    links = [
        ("coord", "Object", "wave", "Vector"),
        ("wave", "Fac", "ramp", "Fac"),
        ("ramp", "Color", "bsdf", "Base Color"),
        ("wave", "Fac", "bump", "Height"),
        ("bump", "Normal", "bsdf", "Normal"),
    ]
    tail_nodes, tail_links = _shader_tail(rough, metal)
    return {"nodes": nodes + tail_nodes, "links": links + tail_links}


def recipe_concrete(color, rough, metal, scale=6.0, variation=0.12):
    """Cast concrete: cloudy tone variation plus fine surface grain."""
    nodes = [
        node("coord", "ShaderNodeTexCoord", (-1100, 0)),
        node("noise", "ShaderNodeTexNoise", (-800, 150),
             inputs={"Scale": float(scale), "Detail": 8.0, "Roughness": 0.65}),
        node("ramp", "ShaderNodeValToRGB", (-550, 150),
             ramp=[(0.35, shade(color, 1.0 - variation)),
                   (0.65, shade(color, 1.0 + variation * 0.7))]),
        node("fine", "ShaderNodeTexNoise", (-800, -200),
             inputs={"Scale": 60.0, "Detail": 2.0, "Roughness": 0.5}),
        node("bump", "ShaderNodeBump", (-350, -200),
             inputs={"Strength": 0.15, "Distance": 0.003}),
    ]
    links = [
        ("coord", "Object", "noise", "Vector"),
        ("coord", "Object", "fine", "Vector"),
        ("noise", "Fac", "ramp", "Fac"),
        ("ramp", "Color", "bsdf", "Base Color"),
        ("fine", "Fac", "bump", "Height"),
        ("bump", "Normal", "bsdf", "Normal"),
    ]
    tail_nodes, tail_links = _shader_tail(rough, metal)
    return {"nodes": nodes + tail_nodes, "links": links + tail_links}


def recipe_marble(color, rough, metal, vein_color=None, scale=1.2):
    """Polished marble: thin dark veins from a strongly distorted wave."""
    vein = rgba(vein_color) if vein_color is not None else shade(color, 0.72)
    nodes = [
        node("coord", "ShaderNodeTexCoord", (-1100, 0)),
        node("wave", "ShaderNodeTexWave", (-800, 150),
             props={"wave_type": 'BANDS', "bands_direction": 'DIAGONAL',
                    "wave_profile": 'SIN'},
             inputs={"Scale": float(scale), "Distortion": 9.0, "Detail": 5.0,
                     "Detail Scale": 2.5, "Detail Roughness": 0.6}),
        node("ramp", "ShaderNodeValToRGB", (-550, 150),
             ramp=[(0.0, rgba(color)), (0.42, rgba(color)), (0.5, vein),
                   (0.58, rgba(color)), (1.0, shade(color, 0.96))]),
    ]
    links = [
        ("coord", "Object", "wave", "Vector"),
        ("wave", "Fac", "ramp", "Fac"),
        ("ramp", "Color", "bsdf", "Base Color"),
    ]
    tail_nodes, tail_links = _shader_tail(rough, metal)
    return {"nodes": nodes + tail_nodes, "links": links + tail_links}


def recipe_clay(color, rough, metal, scale=3.0, variation=0.14):
    """Fired clay (roof tiles): warm tone variation and a matte grain."""
    nodes = [
        node("coord", "ShaderNodeTexCoord", (-1100, 0)),
        node("noise", "ShaderNodeTexNoise", (-800, 150),
             inputs={"Scale": float(scale), "Detail": 3.0, "Roughness": 0.55}),
        node("ramp", "ShaderNodeValToRGB", (-550, 150),
             ramp=[(0.3, shade(color, 1.0 - variation)),
                   (0.7, shade(color, 1.0 + variation))]),
        node("fine", "ShaderNodeTexNoise", (-800, -200),
             inputs={"Scale": 80.0, "Detail": 2.0, "Roughness": 0.5}),
        node("bump", "ShaderNodeBump", (-350, -200),
             inputs={"Strength": 0.2, "Distance": 0.002}),
    ]
    links = [
        ("coord", "Object", "noise", "Vector"),
        ("coord", "Object", "fine", "Vector"),
        ("noise", "Fac", "ramp", "Fac"),
        ("ramp", "Color", "bsdf", "Base Color"),
        ("fine", "Fac", "bump", "Height"),
        ("bump", "Normal", "bsdf", "Normal"),
    ]
    tail_nodes, tail_links = _shader_tail(rough, metal)
    return {"nodes": nodes + tail_nodes, "links": links + tail_links}


def recipe_plaster(color, rough, metal, scale=50.0, strength=0.08):
    """Painted plaster / stucco: flat colour with a fine bump."""
    nodes = [
        node("coord", "ShaderNodeTexCoord", (-1100, 0)),
        node("fine", "ShaderNodeTexNoise", (-800, -200),
             inputs={"Scale": float(scale), "Detail": 4.0, "Roughness": 0.6}),
        node("bump", "ShaderNodeBump", (-350, -200),
             inputs={"Strength": float(strength), "Distance": 0.002}),
    ]
    links = [
        ("coord", "Object", "fine", "Vector"),
        ("fine", "Fac", "bump", "Height"),
        ("bump", "Normal", "bsdf", "Normal"),
    ]
    tail_nodes, tail_links = _shader_tail(
        rough, metal, bsdf_inputs={"Base Color": rgba(color)})
    return {"nodes": nodes + tail_nodes, "links": links + tail_links}


def recipe_fabric(color, rough, metal, weave_scale=200.0):
    """Carpet / upholstery: dense micro bump and soft tone variation."""
    nodes = [
        node("coord", "ShaderNodeTexCoord", (-1100, 0)),
        node("noise", "ShaderNodeTexNoise", (-800, 150),
             inputs={"Scale": 8.0, "Detail": 2.0, "Roughness": 0.5}),
        node("ramp", "ShaderNodeValToRGB", (-550, 150),
             ramp=[(0.35, shade(color, 0.92)), (0.65, shade(color, 1.06))]),
        node("fine", "ShaderNodeTexNoise", (-800, -200),
             inputs={"Scale": float(weave_scale), "Detail": 2.0,
                     "Roughness": 0.5}),
        node("bump", "ShaderNodeBump", (-350, -200),
             inputs={"Strength": 0.3, "Distance": 0.002}),
    ]
    links = [
        ("coord", "Object", "noise", "Vector"),
        ("coord", "Object", "fine", "Vector"),
        ("noise", "Fac", "ramp", "Fac"),
        ("ramp", "Color", "bsdf", "Base Color"),
        ("fine", "Fac", "bump", "Height"),
        ("bump", "Normal", "bsdf", "Normal"),
    ]
    tail_nodes, tail_links = _shader_tail(rough, metal)
    return {"nodes": nodes + tail_nodes, "links": links + tail_links}


RECIPES = {
    BRICK: recipe_brick,
    CERAMIC: recipe_ceramic,
    WOOD: recipe_wood,
    CONCRETE: recipe_concrete,
    MARBLE: recipe_marble,
    CLAY: recipe_clay,
    PLASTER: recipe_plaster,
    FABRIC: recipe_fabric,
}


def build_recipe(kind, color, rough, metal, params=None):
    """Recipe dict for ``kind`` or ``None`` when the kind is unknown."""
    builder = RECIPES.get(kind)
    if builder is None:
        return None
    return builder(color, rough, metal, **(params or {}))


# ════════════════════════════════════════════════════════════
#  Static validation (used by the tests and by the builder)
# ════════════════════════════════════════════════════════════
def recipe_problems(recipe):
    """List human-readable inconsistencies; empty when the recipe is sound."""
    problems = []
    nodes = recipe.get("nodes", [])
    links = recipe.get("links", [])
    by_id = {}
    for spec in nodes:
        node_id = spec.get("id")
        if node_id in by_id:
            problems.append("duplicate node id {!r}".format(node_id))
        by_id[node_id] = spec
        if spec.get("type") not in ALLOWED_NODE_TYPES:
            problems.append("node {!r} has unsupported type {!r}".format(
                node_id, spec.get("type")))
            continue
        inputs, _outputs = NODE_SOCKETS[spec["type"]]
        for key in spec.get("inputs", {}):
            if key not in inputs:
                problems.append("node {!r}: unknown input {!r}".format(
                    node_id, key))
        for pos, col in spec.get("ramp", []):
            if not 0.0 <= pos <= 1.0 or len(col) != 4:
                problems.append("node {!r}: bad ramp stop {!r}".format(
                    node_id, (pos, col)))
        ramp_positions = [pos for pos, _c in spec.get("ramp", [])]
        if ramp_positions != sorted(ramp_positions):
            problems.append("node {!r}: ramp stops not sorted".format(node_id))
    for src, out, dst, inp in links:
        if src not in by_id or dst not in by_id:
            problems.append("link {!r} references unknown node".format(
                (src, out, dst, inp)))
            continue
        src_type, dst_type = by_id[src]["type"], by_id[dst]["type"]
        if src_type in NODE_SOCKETS and out not in NODE_SOCKETS[src_type][1]:
            problems.append("link {!r}: unknown output".format(
                (src, out, dst, inp)))
        if dst_type in NODE_SOCKETS and inp not in NODE_SOCKETS[dst_type][0]:
            problems.append("link {!r}: unknown input".format(
                (src, out, dst, inp)))
    if "bsdf" not in by_id or "out" not in by_id:
        problems.append("recipe needs 'bsdf' and 'out' nodes")
    elif ("bsdf", "BSDF", "out", "Surface") not in links:
        problems.append("recipe does not connect the BSDF to the output")
    return problems

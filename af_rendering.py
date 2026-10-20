# -*- coding: utf-8 -*-

# ╔══════════════════════════════════════════════════════════╗
# ║         ARCHIFORGE — af_rendering.py                    ║
# ║         Rendering / Thumbnails — Blender 3.3 LTS        ║
# ║         GPL v3 — ArchiForge Devs                        ║
# ╚══════════════════════════════════════════════════════════╝

# <pep8 compliant>

import bpy
import os
import math

from mathutils import Vector
from bpy.types import (
    PropertyGroup, Operator, Panel
)
from bpy.props import (
    BoolProperty, FloatProperty, IntProperty,
    EnumProperty, StringProperty, PointerProperty,
    FloatVectorProperty,
)

try:
    from .af_i18n import tr_report as _tr
except ImportError:  # pragma: no cover - fuera del paquete
    def _tr(text):
        return text


# ════════════════════════════════════════════════════════════
#  CONSTANTES
# ════════════════════════════════════════════════════════════
AF_THUMB_SIZE    = 256   # px
AF_THUMB_SUBDIR  = "archiforge_thumbs"
AF_RENDER_PRESET = [
    ('PREVIEW',      "Preview",       "Fast preview render",     'RESTRICT_RENDER_OFF', 0),
    ('PRESENTATION', "Presentation",  "High quality render",     'RENDER_STILL',        1),
    ('WIREFRAME',    "Wireframe",     "Wireframe / technical",   'MOD_WIREFRAME',       2),
    ('CLAY',         "Clay",          "Clay / no-texture render",'SHADING_SOLID',       3),
]


# ════════════════════════════════════════════════════════════
#  PROPERTYGROUP
# ════════════════════════════════════════════════════════════
class AF_RenderSettings(PropertyGroup):

    # ── Engine ───────────────────────────────────────────────
    engine : EnumProperty(
        name  = "Engine",
        items = [
            ('CYCLES',   "Cycles",   "Cycles path tracer"),
            ('BLENDER_EEVEE', "EEVEE", "EEVEE real-time"),
            ('BLENDER_WORKBENCH', "Workbench", "Workbench solid"),
        ],
        default = 'BLENDER_EEVEE',
    )
    preset : EnumProperty(
        name  = "Preset",
        items = AF_RENDER_PRESET,
        default = 'PREVIEW',
    )

    # ── Resolución ────────────────────────────────────────────
    res_x : IntProperty(
        name="Width",  default=1920, min=64, max=7680,
    )
    res_y : IntProperty(
        name="Height", default=1080, min=64, max=4320,
    )
    res_pct : IntProperty(
        name="Scale %", default=100, min=10, max=200,
        subtype='PERCENTAGE',
    )

    # ── Calidad ───────────────────────────────────────────────
    samples : IntProperty(
        name="Samples", default=128, min=1, max=4096,
    )
    use_denoiser : BoolProperty(
        name="Denoiser", default=True,
    )

    # ── Cámara AF ─────────────────────────────────────────────
    auto_camera : BoolProperty(
        name        = "Auto Camera",
        description = "Automatically set camera to frame AF objects",
        default     = True,
    )
    camera_angle : EnumProperty(
        name  = "View Angle",
        items = [
            ('PERSPECTIVE_45', "Perspective 45°", "3/4 perspective view"),
            ('FRONT',          "Front",           "Orthographic front view"),
            ('TOP',            "Top",             "Orthographic top view"),
            ('ISOMETRIC',      "Isometric",       "Isometric view"),
            ('CUSTOM',         "Custom",          "Use current camera"),
        ],
        default = 'PERSPECTIVE_45',
    )

    # ── Output ────────────────────────────────────────────────
    output_path : StringProperty(
        name        = "Output Path",
        description = "Folder for rendered images",
        default     = "//renders/",
        subtype     = 'DIR_PATH',
    )
    output_format : EnumProperty(
        name  = "Format",
        items = [
            ('PNG',  "PNG",  "PNG lossless"),
            ('JPEG', "JPEG", "JPEG compressed"),
            ('EXR',  "EXR",  "OpenEXR HDR"),
        ],
        default = 'PNG',
    )

    # ── Ambiente ─────────────────────────────────────────────
    hdri_strength : FloatProperty(
        name="HDRI Strength", default=1.0, min=0.0, max=10.0,
    )
    bg_color : FloatVectorProperty(
        name="Background",
        subtype='COLOR_GAMMA',
        default=(0.9, 0.9, 0.9, 1.0),
        size=4, min=0, max=1,
    )
    use_shadow_catcher : BoolProperty(
        name="Shadow Catcher", default=False,
    )


# ════════════════════════════════════════════════════════════
#  UTILIDADES
# ════════════════════════════════════════════════════════════
def _get_af_objects_bounds(context):
    """
    Calcula el bounding box global de todos los
    objetos ArchiForge en la escena.
    Retorna (center, max_dim) o (None, None).
    """
    from . af_panel import _get_af_objects
    af_objs = _get_af_objects(context.scene)

    if not af_objs:
        return None, None

    min_co = Vector((1e9, 1e9, 1e9))
    max_co = Vector((-1e9, -1e9, -1e9))

    for obj, attr, label, icon in af_objs:
        mw = obj.matrix_world
        for corner in obj.bound_box:
            wco = mw @ Vector(corner)
            min_co.x = min(min_co.x, wco.x)
            min_co.y = min(min_co.y, wco.y)
            min_co.z = min(min_co.z, wco.z)
            max_co.x = max(max_co.x, wco.x)
            max_co.y = max(max_co.y, wco.y)
            max_co.z = max(max_co.z, wco.z)

    center  = (min_co + max_co) * 0.5
    max_dim = max(
        max_co.x - min_co.x,
        max_co.y - min_co.y,
        max_co.z - min_co.z,
    )
    return center, max_dim


def _setup_camera_auto(context, angle_preset: str):
    """
    Crea o reposiciona la cámara para enmarcar
    todos los objetos AF.
    """
    center, max_dim = _get_af_objects_bounds(context)
    if center is None:
        return None

    dist = max_dim * 2.0

    angles = {
        'PERSPECTIVE_45': (
            Vector((1, -1, 0.7)).normalized() * dist + center,
            math.radians(65), 0, math.radians(45),
        ),
        'FRONT': (
            center + Vector((0, -dist, max_dim * 0.5)),
            math.radians(90), 0, 0,
        ),
        'TOP': (
            center + Vector((0, 0, dist)),
            0, 0, 0,
        ),
        'ISOMETRIC': (
            center + Vector((1, -1, 1)).normalized() * dist,
            math.radians(54.7), 0, math.radians(45),
        ),
    }

    cam_data = angles.get(angle_preset)
    if cam_data is None:
        return None

    loc, rx, ry, rz = cam_data

    # Buscar cámara AF existente o crear una nueva
    cam_obj = bpy.data.objects.get("AF_Camera")
    if cam_obj is None:
        cam_data_block = bpy.data.cameras.new("AF_Camera")
        cam_obj = bpy.data.objects.new("AF_Camera", cam_data_block)
        context.collection.objects.link(cam_obj)

    cam_obj.location       = loc
    cam_obj.rotation_euler = (rx, ry, rz)

    # Ajustar FOV
    cam_obj.data.type  = 'PERSP'
    cam_obj.data.lens  = 35.0

    return cam_obj


def _apply_render_settings(context, rs: AF_RenderSettings):
    """Aplica la configuración de render de AF a la escena."""
    scene   = context.scene
    render  = scene.render
    cycles  = scene.cycles if hasattr(scene, 'cycles') else None
    eevee   = scene.eevee  if hasattr(scene, 'eevee')  else None

    render.engine      = rs.engine
    render.resolution_x          = rs.res_x
    render.resolution_y          = rs.res_y
    render.resolution_percentage = rs.res_pct
    render.filepath    = bpy.path.abspath(rs.output_path)
    render.image_settings.file_format = rs.output_format

    if rs.preset == 'PREVIEW':
        if cycles:
            cycles.samples        = min(rs.samples, 64)
            cycles.use_denoising  = rs.use_denoiser
        if eevee:
            eevee.taa_render_samples = 16

    elif rs.preset == 'PRESENTATION':
        if cycles:
            cycles.samples        = rs.samples
            cycles.use_denoising  = rs.use_denoiser
        if eevee:
            eevee.taa_render_samples = 64
            eevee.use_ssr         = True
            eevee.use_bloom       = False

    elif rs.preset == 'CLAY':
        render.engine = 'BLENDER_WORKBENCH'

    elif rs.preset == 'WIREFRAME':
        render.engine = 'BLENDER_WORKBENCH'


# ════════════════════════════════════════════════════════════
#  OPERADORES
# ════════════════════════════════════════════════════════════
class ARCHIFORGE_OT_render_setup(Operator):
    """Configura el render según los ajustes de AF."""
    bl_idname      = "archiforge.render_setup"
    bl_label       = "Setup AF Render"
    bl_description = "Apply ArchiForge render settings to the scene"
    bl_options     = {'REGISTER', 'UNDO'}

    def execute(self, context):
        rs = getattr(context.scene, "af_render", None)
        if rs is None:
            self.report({'ERROR'}, _tr("Render settings not available"))
            return {'CANCELLED'}
        _apply_render_settings(context, rs)
        if rs.auto_camera and rs.camera_angle != 'CUSTOM':
            cam = _setup_camera_auto(context, rs.camera_angle)
            if cam:
                context.scene.camera = cam
        self.report({'INFO'}, _tr("Render settings applied"))
        return {'FINISHED'}


class ARCHIFORGE_OT_render_preview(Operator):
    """Renderiza una preview rápida del proyecto AF."""
    bl_idname      = "archiforge.render_preview"
    bl_label       = "Render Preview"
    bl_description = "Quick render preview of AF objects"
    bl_options     = {'REGISTER'}

    def execute(self, context):
        rs = getattr(context.scene, "af_render", None)
        if rs:
            _apply_render_settings(context, rs)
        bpy.ops.render.render('INVOKE_DEFAULT', write_still=False)
        return {'FINISHED'}


class ARCHIFORGE_OT_render_thumbs(Operator):
    """Genera thumbnails de presets (stub para UI)."""
    bl_idname      = "archipack.render_thumbs"
    bl_label       = "Regenerate Thumbnails"
    bl_description = "Regenerate preset thumbnails"
    bl_options     = {'REGISTER'}

    def execute(self, context):
        # Stub — en producción renderiza cada preset
        self.report({'INFO'}, _tr("Thumbnails regenerated (stub)"))
        return {'FINISHED'}


class ARCHIFORGE_OT_camera_auto(Operator):
    """Posiciona la cámara automáticamente para el proyecto."""
    bl_idname      = "archiforge.camera_auto"
    bl_label       = "Auto Camera"
    bl_description = "Automatically position camera to frame all AF objects"
    bl_options     = {'REGISTER', 'UNDO'}

    def execute(self, context):
        rs = getattr(context.scene, "af_render", None)
        angle = rs.camera_angle if rs else 'PERSPECTIVE_45'
        cam   = _setup_camera_auto(context, angle)
        if cam:
            context.scene.camera = cam
            self.report({'INFO'}, _tr("Camera set: {}").format(cam.name))
        else:
            self.report({'WARNING'}, _tr("No AF objects found to frame"))
        return {'FINISHED'}


class ARCHIFORGE_OT_set_view_to_camera(Operator):
    """Establece la vista activa a la cámara AF."""
    bl_idname      = "archiforge.view_to_camera"
    bl_label       = "Look Through Camera"
    bl_description = "Set viewport to look through AF camera"
    bl_options     = {'REGISTER'}

    def execute(self, context):
        cam = bpy.data.objects.get("AF_Camera")
        if cam is None:
            self.report({'WARNING'}, _tr("No AF camera found"))
            return {'CANCELLED'}
        context.scene.camera = cam
        for area in context.screen.areas:
            if area.type == 'VIEW_3D':
                for space in area.spaces:
                    if space.type == 'VIEW_3D':
                        space.region_3d.view_perspective = 'CAMERA'
        return {'FINISHED'}


# ════════════════════════════════════════════════════════════
#  PANEL
# ════════════════════════════════════════════════════════════
class ARCHIFORGE_PT_rendering(Panel):
    bl_label       = "Rendering"
    bl_idname      = "ARCHIFORGE_PT_rendering"
    bl_space_type  = "VIEW_3D"
    bl_region_type = "UI"
    bl_category    = "ArchiForge"
    bl_context     = "objectmode"
    bl_order       = 40
    bl_options     = {'DEFAULT_CLOSED'}

    @classmethod
    def poll(cls, context):
        return context.mode == 'OBJECT'

    def draw_header(self, context):
        self.layout.label(text="", icon='RENDER_STILL')

    def draw(self, context):
        rs     = getattr(context.scene, "af_render", None)
        layout = self.layout
        layout.use_property_split   = True
        layout.use_property_decorate = False

        if rs is None:
            layout.label(text="Not available", icon='ERROR')
            return

        # ── Preset + Engine ───────────────────────────────────
        box = layout.box()
        col = box.column(align=True)
        col.label(text="Render Mode", icon='RENDER_STILL')
        col.prop(rs, "preset")
        col.prop(rs, "engine")

        # ── Resolución ────────────────────────────────────────
        box = layout.box()
        col = box.column(align=True)
        col.label(text="Resolution", icon='IMAGE_DATA')
        row = col.row(align=True)
        row.prop(rs, "res_x", text="W")
        row.prop(rs, "res_y", text="H")
        col.prop(rs, "res_pct")

        # ── Calidad ───────────────────────────────────────────
        box = layout.box()
        col = box.column(align=True)
        col.label(text="Quality", icon='MODIFIER')
        col.prop(rs, "samples")
        col.prop(rs, "use_denoiser")

        # ── Cámara ────────────────────────────────────────────
        box = layout.box()
        col = box.column(align=True)
        col.label(text="Camera", icon='CAMERA_DATA')
        col.prop(rs, "auto_camera")
        if rs.auto_camera:
            col.prop(rs, "camera_angle")
        row = col.row(align=True)
        row.operator(
            "archiforge.camera_auto",
            text="Auto Camera",
            icon='CAMERA_DATA'
        )
        row.operator(
            "archiforge.view_to_camera",
            text="Look Through",
            icon='HIDE_OFF'
        )

        # ── Output ────────────────────────────────────────────
        box = layout.box()
        col = box.column(align=True)
        col.label(text="Output", icon='OUTPUT')
        col.prop(rs, "output_path", text="")
        col.prop(rs, "output_format")

        # ── Acciones ─────────────────────────────────────────
        layout.separator(factor=0.3)
        row = layout.row(align=True)
        row.operator(
            "archiforge.render_setup",
            text="Apply Settings",
            icon='CHECKMARK'
        )
        row.operator(
            "archiforge.render_preview",
            text="Render",
            icon='RENDER_STILL'
        )


# ════════════════════════════════════════════════════════════
#  REGISTRO
# ════════════════════════════════════════════════════════════
classes = [
    AF_RenderSettings,
    ARCHIFORGE_OT_render_setup,
    ARCHIFORGE_OT_render_preview,
    ARCHIFORGE_OT_render_thumbs,
    ARCHIFORGE_OT_camera_auto,
    ARCHIFORGE_OT_set_view_to_camera,
    ARCHIFORGE_PT_rendering,
]


def register():
    for cls in classes:
        try:
            bpy.utils.register_class(cls)
        except Exception as e:
            print(f"[ArchiForge] ⚠️  af_rendering '{cls.__name__}': {e}")

    bpy.types.Scene.af_render = PointerProperty(
        type        = AF_RenderSettings,
        name        = "AF Render",
        description = "ArchiForge rendering settings",
    )
    print("[ArchiForge] ✅ af_rendering — registered")


def unregister():
    if hasattr(bpy.types.Scene, "af_render"):
        del bpy.types.Scene.af_render

    for cls in reversed(classes):
        try:
            bpy.utils.unregister_class(cls)
        except Exception as e:
            print(f"[ArchiForge] ⚠️  af_rendering '{cls.__name__}': {e}")

    print("[ArchiForge] 🔴 af_rendering — unregistered")
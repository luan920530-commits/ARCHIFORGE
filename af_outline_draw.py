# -*- coding: utf-8 -*-
"""Shared modal viewport interaction for closed ArchiForge outlines."""

import math

import bpy
from mathutils import Vector
try:
    from .af_wall_path import build_wall_segments
except ImportError:
    from af_wall_path import build_wall_segments

try:
    from .af_i18n import tr_report as _tr
except ImportError:  # pragma: no cover - fuera del paquete
    def _tr(text):
        return text


_MAX_OUTLINE_POINTS = 64
_CLOSE_DISTANCE_PIXELS = 12.0
_MIN_SEGMENT_LENGTH = 0.01


def _mouse_world_point(context, event, plane_z):
    """Intersect the viewport mouse ray with the horizontal drawing plane."""
    try:
        from bpy_extras.view3d_utils import (
            region_2d_to_origin_3d,
            region_2d_to_vector_3d,
        )
        region = context.region
        rv3d = context.region_data
        if region is None or rv3d is None:
            return None
        coord = (event.mouse_region_x, event.mouse_region_y)
        origin = region_2d_to_origin_3d(region, rv3d, coord)
        direction = region_2d_to_vector_3d(region, rv3d, coord)
        if abs(direction.z) < 1e-7:
            return None
        distance = (plane_z - origin.z) / direction.z
        if distance < 0.0:
            return None
        point = origin + direction * distance
        return Vector((point.x, point.y, plane_z))
    except (AttributeError, ReferenceError, TypeError, ValueError):
        return None


def _screen_point(context, point):
    try:
        from bpy_extras.view3d_utils import location_3d_to_region_2d
        if context.region is None or context.region_data is None:
            return None
        return location_3d_to_region_2d(
            context.region, context.region_data, point)
    except (AttributeError, ReferenceError, TypeError, ValueError):
        return None


class AF_OutlineDrawMixin:
    """Reusable click-to-draw interaction for slab and floor operators."""

    outline_tool_label = "floor/slab"

    @classmethod
    def poll(cls, context):
        return (
            context.area is not None
            and context.area.type == 'VIEW_3D'
            and context.mode == 'OBJECT'
        )

    def invoke(self, context, event):
        return self._start_outline_draw(context)

    def execute(self, context):
        return self._start_outline_draw(context)

    def _start_outline_draw(self, context):
        self._draw_points = []
        self._draw_hover = None
        self._draw_closing_hint = False
        self._draw_z = float(context.scene.cursor.location.z)
        self._draw_area = context.area
        self._draw_handle = None
        try:
            self._draw_handle = bpy.types.SpaceView3D.draw_handler_add(
                self._draw_outline_preview, (), 'WINDOW', 'POST_PIXEL')
            context.window_manager.modal_handler_add(self)
        except Exception as exc:
            self._remove_outline_draw_handler()
            self.report({'ERROR'}, _tr("No se pudo iniciar el dibujo: {}").format(exc))
            return {'CANCELLED'}

        if context.area is not None:
            context.area.header_text_set(
                f"ArchiForge {self.outline_tool_label}: clic para vértice · "
                "clic en inicio / C / Enter para cerrar · "
                "Backspace: quitar punto · Esc: cancelar")
            context.area.tag_redraw()
        return {'RUNNING_MODAL'}

    def _remove_outline_draw_handler(self):
        handle = getattr(self, "_draw_handle", None)
        if handle is not None:
            try:
                bpy.types.SpaceView3D.draw_handler_remove(handle, 'WINDOW')
            except (ReferenceError, RuntimeError, TypeError):
                pass
            self._draw_handle = None

        area = getattr(self, "_draw_area", None)
        if area is not None:
            try:
                area.header_text_set(None)
                area.tag_redraw()
            except (ReferenceError, RuntimeError, TypeError):
                pass
            self._draw_area = None

    def _draw_outline_preview(self):
        if not self._draw_points:
            return
        try:
            import blf
            import gpu
            from gpu_extras.batch import batch_for_shader

            context = bpy.context
            if (context.area is None or context.area.type != 'VIEW_3D'
                    or context.region is None or context.region_data is None):
                return

            points = list(self._draw_points)
            if self._draw_hover is not None:
                points.append(self._draw_hover)
            screen_points = []
            for point in points:
                screen = _screen_point(context, point)
                if screen is not None:
                    screen_points.append((screen.x, screen.y))
            if self._draw_closing_hint and len(screen_points) > 1:
                first = _screen_point(context, self._draw_points[0])
                if first is not None:
                    screen_points.append((first.x, first.y))
            if len(screen_points) < 2:
                return

            try:
                shader = gpu.shader.from_builtin('2D_UNIFORM_COLOR')
            except Exception:
                shader = gpu.shader.from_builtin('UNIFORM_COLOR')
            gpu.state.blend_set('ALPHA')
            gpu.state.line_width_set(2.0)
            shader.bind()
            shader.uniform_float(
                "color", (0.20, 0.85, 1.0, 0.95)
                if not self._draw_closing_hint
                else (0.25, 1.0, 0.35, 1.0))
            batch_for_shader(
                shader, 'LINE_STRIP', {"pos": screen_points}).draw(shader)

            gpu.state.point_size_set(7.0)
            batch_for_shader(
                shader, 'POINTS', {"pos": screen_points[:-1]}).draw(shader)
            gpu.state.point_size_set(1.0)
            gpu.state.line_width_set(1.0)
            gpu.state.blend_set('NONE')

            font_id = 0
            try:
                blf.size(font_id, 14)
            except TypeError:
                blf.size(font_id, 14, 72)
            blf.position(font_id, 18, context.region.height - 28, 0)
            blf.color(font_id, 1.0, 1.0, 1.0, 1.0)
            blf.draw(
                font_id,
                "Clic: vértice | Clic en inicio, C o Enter: cerrar | "
                "Backspace: quitar punto | Esc: cancelar",
            )
        except Exception:
            # A drawing overlay must never interrupt viewport interaction.
            try:
                import gpu
                gpu.state.point_size_set(1.0)
                gpu.state.line_width_set(1.0)
                gpu.state.blend_set('NONE')
            except Exception:
                pass

    def _snap_draw_point(self, context, point):
        point = Vector((point.x, point.y, self._draw_z))
        snap = getattr(context.scene, "af_snap", None)
        if snap is None or not getattr(snap, "enabled", False):
            return point

        if getattr(snap, "grid_snap", False):
            grid = max(0.001, float(snap.grid_size))
            point.x = round(point.x / grid) * grid
            point.y = round(point.y / grid) * grid

        if self._draw_points and getattr(snap, "angle_snap", False):
            delta = point - self._draw_points[-1]
            distance = math.hypot(delta.x, delta.y)
            if distance > 1e-6:
                step = math.radians(max(1, int(snap.angle_step)))
                angle = math.atan2(delta.y, delta.x)
                angle = round(angle / step) * step
                point.x = self._draw_points[-1].x + math.cos(angle) * distance
                point.y = self._draw_points[-1].y + math.sin(angle) * distance
        return point

    def _near_first_draw_point(self, context, event):
        if len(self._draw_points) < 3:
            return False
        screen = _screen_point(context, self._draw_points[0])
        if screen is None:
            return False
        return math.hypot(
            screen.x - event.mouse_region_x,
            screen.y - event.mouse_region_y,
        ) <= _CLOSE_DISTANCE_PIXELS

    def _finish_outline_draw(self, context):
        try:
            build_wall_segments(
                self._draw_points,
                closed=True,
                min_segment_length=_MIN_SEGMENT_LENGTH,
                max_segments=_MAX_OUTLINE_POINTS,
            )
        except ValueError as exc:
            self.report({'WARNING'}, _tr(str(exc)))
            return {'RUNNING_MODAL'}

        try:
            obj = self._create_from_outline(context, list(self._draw_points))
        except Exception as exc:
            self.report({'ERROR'}, _tr("No se pudo crear el contorno: {}").format(exc))
            self._remove_outline_draw_handler()
            return {'CANCELLED'}

        self._remove_outline_draw_handler()
        self.report({'INFO'}, _tr("{} creado: {}")
                              .format(self.outline_tool_label, obj.name))
        return {'FINISHED'}

    def modal(self, context, event):
        if context.area is None or context.area.type != 'VIEW_3D':
            self._remove_outline_draw_handler()
            return {'CANCELLED'}

        if event.type in {'ESC', 'RIGHTMOUSE'} and event.value == 'PRESS':
            self._remove_outline_draw_handler()
            return {'CANCELLED'}

        if event.type == 'MOUSEMOVE':
            self._draw_closing_hint = self._near_first_draw_point(
                context, event)
            if self._draw_closing_hint:
                self._draw_hover = self._draw_points[0].copy()
            else:
                point = _mouse_world_point(context, event, self._draw_z)
                self._draw_hover = (
                    self._snap_draw_point(context, point)
                    if point is not None else None
                )
            context.area.tag_redraw()
            return {'RUNNING_MODAL'}

        if event.type == 'LEFTMOUSE' and event.value == 'PRESS':
            if self._near_first_draw_point(context, event):
                return self._finish_outline_draw(context)
            point = _mouse_world_point(context, event, self._draw_z)
            if point is None:
                self.report({'WARNING'},
                            _tr("No se pudo intersectar el cursor con el plano de dibujo"))
                return {'RUNNING_MODAL'}
            point = self._snap_draw_point(context, point)
            if (self._draw_points
                    and (point - self._draw_points[-1]).length
                    < _MIN_SEGMENT_LENGTH):
                return {'RUNNING_MODAL'}
            if len(self._draw_points) >= _MAX_OUTLINE_POINTS:
                self.report({'WARNING'}, _tr("Máximo de 64 vértices alcanzado"))
                return {'RUNNING_MODAL'}
            self._draw_points.append(point)
            self._draw_hover = point.copy()
            context.area.tag_redraw()
            return {'RUNNING_MODAL'}

        if event.type in {'BACK_SPACE', 'DEL'} and event.value == 'PRESS':
            if self._draw_points:
                self._draw_points.pop()
                self._draw_hover = (
                    self._draw_points[-1].copy() if self._draw_points else None
                )
                self._draw_closing_hint = False
                context.area.tag_redraw()
            return {'RUNNING_MODAL'}

        if event.type in {'C', 'RET', 'NUMPAD_ENTER'} and event.value == 'PRESS':
            return self._finish_outline_draw(context)
        if event.type in {'MIDDLEMOUSE', 'WHEELUPMOUSE', 'WHEELDOWNMOUSE'}:
            return {'PASS_THROUGH'}
        return {'RUNNING_MODAL'}

    def _create_from_outline(self, context, points):
        raise NotImplementedError

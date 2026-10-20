"""Minimal ``bpy`` / ``bmesh`` / ``mathutils`` stand-ins for headless tests.

The real generators only need a vertex/face container plus a 3D vector to
build their geometry, so this module provides just enough of the Blender API
to import a generator module and inspect the mesh it produces. Nothing here
emulates the depsgraph, properties or operators; UI code is never executed.

Usage::

    from blender_stub import load_addon_module
    af_window = load_addon_module("af_window")
    bm = af_window.AF_WindowGenerator(props).generate()
"""

import math
import sys
import types
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PACKAGE_NAME = "ArchiForgeHeadless"


class Vector:
    """Three-component vector with the attribute access generators rely on."""

    def __init__(self, seq=(0.0, 0.0, 0.0)):
        values = [float(v) for v in seq]
        while len(values) < 3:
            values.append(0.0)
        self.x, self.y, self.z = values[:3]

    def __iter__(self):
        return iter((self.x, self.y, self.z))

    def __getitem__(self, index):
        return (self.x, self.y, self.z)[index]

    def __len__(self):
        return 3

    def __add__(self, other):
        return Vector((self.x + other.x, self.y + other.y, self.z + other.z))

    def __sub__(self, other):
        return Vector((self.x - other.x, self.y - other.y, self.z - other.z))

    def __mul__(self, scalar):
        return Vector((self.x * scalar, self.y * scalar, self.z * scalar))

    __rmul__ = __mul__

    @property
    def length(self):
        return math.sqrt(self.x ** 2 + self.y ** 2 + self.z ** 2)

    def copy(self):
        return Vector((self.x, self.y, self.z))

    def __repr__(self):
        return "Vector(({:.5f}, {:.5f}, {:.5f}))".format(self.x, self.y, self.z)


class _Transform:
    """Placeholder for mathutils.Matrix / Euler; never evaluated in tests."""

    def __init__(self, *args, **kwargs):
        pass

    @classmethod
    def Rotation(cls, *args, **kwargs):
        return cls()

    @classmethod
    def Translation(cls, *args, **kwargs):
        return cls()

    @classmethod
    def Identity(cls, *args, **kwargs):
        return cls()


class BMVert:
    def __init__(self, co, index):
        self.co = co
        self.index = index


class BMFace:
    def __init__(self, verts):
        self.verts = list(verts)
        self.material_index = 0
        self._layers = {}

    def __setitem__(self, layer, value):
        self._layers[layer] = value

    def __getitem__(self, layer):
        return self._layers.get(layer, 0)


class _VertSeq(list):
    def new(self, co):
        vert = BMVert(co if isinstance(co, Vector) else Vector(co), len(self))
        self.append(vert)
        return vert

    def ensure_lookup_table(self):
        pass


class _IntLayers:
    def new(self, name):
        return name


class _FaceSeq(list):
    def __init__(self):
        super().__init__()
        self.layers = types.SimpleNamespace(int=_IntLayers())

    def new(self, verts):
        face = BMFace(verts)
        self.append(face)
        return face

    def ensure_lookup_table(self):
        pass


class BMesh:
    def __init__(self):
        self.verts = _VertSeq()
        self.faces = _FaceSeq()

    def free(self):
        pass


def _noop(*args, **kwargs):
    return None


class Translations:
    """Stand-in for ``bpy.app.translations`` (Blender 3.3 semantics).

    One ``{locale: {(context, msgid): msgstr}}`` dictionary per module;
    registering a module twice raises ``ValueError``; unregistering an
    unknown module is silently ignored. Lookups resolve the locale the
    way Blender does (exact, language_country, language) and honour the
    *Translate Interface* / *Translate Tooltips* preferences.
    """

    def __init__(self, locale="en_US"):
        self.locale = locale
        self.registered = {}

    def register(self, module_name, translations):
        if module_name in self.registered:
            raise ValueError("bpy.app.translations.register: module '{}' "
                             "already registered".format(module_name))
        for lang, table in translations.items():
            if not isinstance(lang, str):
                raise TypeError("language key must be str")
            for key, msgstr in table.items():
                context, msgid = key
                if not all(isinstance(x, str) for x in (context, msgid, msgstr)):
                    raise TypeError("translation entries must be str")
        self.registered[module_name] = translations

    def unregister(self, module_name):
        self.registered.pop(module_name, None)

    def _lang_dict(self, translations):
        language = self.locale.split("_")[0]
        for key in (self.locale, language):
            if key in translations:
                return translations[key]
        return {}

    def _lookup(self, msgid, msgctxt):
        for translations in self.registered.values():
            table = self._lang_dict(translations)
            hit = table.get((msgctxt or "*", msgid))
            if hit is not None:
                return hit
        return msgid

    def pgettext(self, msgid, msgctxt=None):
        return self._lookup(msgid, msgctxt)

    def pgettext_iface(self, msgid, msgctxt=None):
        view = _view_preferences()
        if view is None or not view.use_translate_interface:
            return msgid
        return self._lookup(msgid, msgctxt)

    def pgettext_tip(self, msgid, msgctxt=None):
        view = _view_preferences()
        if view is None or not view.use_translate_tooltips:
            return msgid
        return self._lookup(msgid, msgctxt)


def _view_preferences():
    bpy = sys.modules.get("bpy")
    prefs = getattr(getattr(bpy, "context", None), "preferences", None)
    return getattr(prefs, "view", None)


class _Area:
    def __init__(self):
        self.redraws = 0

    def tag_redraw(self):
        self.redraws += 1


def install_ui_context(locale="en_US", language="EN", addon_name="ArchiForge",
                       translate_interface=False, translate_tooltips=True):
    """Give the stub a Blender-like UI context for i18n tests.

    Defaults mirror a fresh English Blender 3.3: interface translation
    off, tooltip translation on. Returns ``bpy`` for assertions.
    """
    install()
    bpy = sys.modules["bpy"]
    bpy.app.translations = Translations(locale)
    addon_prefs = types.SimpleNamespace(
        language=language,
        i18n_forced_use_translate_interface=False,
        i18n_forced_use_translate_tooltips=False)
    addons = {addon_name: types.SimpleNamespace(preferences=addon_prefs)}
    bpy.context.preferences = types.SimpleNamespace(
        view=types.SimpleNamespace(
            use_translate_interface=translate_interface,
            use_translate_tooltips=translate_tooltips),
        addons=addons)
    area = _Area()
    bpy.context.window_manager = types.SimpleNamespace(
        windows=[types.SimpleNamespace(
            screen=types.SimpleNamespace(areas=[area]))])
    return bpy


def install():
    """Register the stand-ins in ``sys.modules`` (idempotent)."""
    if "bpy" in sys.modules and getattr(sys.modules["bpy"], "_af_stub", False):
        return

    class _Base:
        pass

    bpy = types.ModuleType("bpy")
    bpy._af_stub = True
    bpy.__path__ = []
    bpy_types = types.ModuleType("bpy.types")
    for name in ("PropertyGroup", "Operator", "Panel", "Menu", "UIList",
                 "Object", "Scene", "AddonPreferences", "SpaceView3D"):
        setattr(bpy_types, name, type(name, (_Base,), {}))
    bpy_props = types.ModuleType("bpy.props")
    for name in ("StringProperty", "BoolProperty", "IntProperty",
                 "FloatProperty", "EnumProperty", "CollectionProperty",
                 "PointerProperty", "FloatVectorProperty",
                 "IntVectorProperty"):
        setattr(bpy_props, name, _noop)
    bpy_utils = types.ModuleType("bpy.utils")
    bpy_utils.register_class = _noop
    bpy_utils.unregister_class = _noop
    bpy.types = bpy_types
    bpy.props = bpy_props
    bpy.utils = bpy_utils
    bpy.data = types.SimpleNamespace(objects={}, materials={}, meshes={})
    bpy.ops = types.SimpleNamespace()
    bpy.app = types.SimpleNamespace(version=(3, 3, 0), version_string="3.3.0")
    bpy.context = types.SimpleNamespace()

    bmesh = types.ModuleType("bmesh")
    bmesh.new = BMesh
    bmesh.ops = types.SimpleNamespace(recalc_face_normals=_noop)

    mathutils = types.ModuleType("mathutils")
    mathutils.Vector = Vector
    mathutils.Matrix = _Transform
    mathutils.Euler = _Transform

    sys.modules.update({
        "bpy": bpy,
        "bpy.types": bpy_types,
        "bpy.props": bpy_props,
        "bpy.utils": bpy_utils,
        "bmesh": bmesh,
        "mathutils": mathutils,
    })

    # Expose the repository as a package without running its Blender-only
    # __init__.py, so relative imports inside af_*.py resolve normally.
    package = types.ModuleType(PACKAGE_NAME)
    package.__path__ = [str(ROOT)]
    sys.modules[PACKAGE_NAME] = package


def load_addon_module(name):
    """Import ``af_<name>`` from the repository through the stub package."""
    install()
    import importlib
    return importlib.import_module("{}.{}".format(PACKAGE_NAME, name))


def face_vertices(bm, material_index, layer=None):
    """Unique vertices of the faces carrying ``material_index``.

    ``layer`` selects generators that store the index in a bmesh int layer
    (``face[layer]``) instead of ``face.material_index``.
    """
    unique = {}
    for face in bm.faces:
        index = face[layer] if layer is not None else face.material_index
        if index == material_index:
            for vert in face.verts:
                unique[id(vert)] = vert
    return list(unique.values())


def bounds(verts):
    """``((xmin, xmax), (ymin, ymax), (zmin, zmax))`` of ``verts``."""
    xs = [v.co.x for v in verts]
    ys = [v.co.y for v in verts]
    zs = [v.co.z for v in verts]
    return ((min(xs), max(xs)), (min(ys), max(ys)), (min(zs), max(zs)))

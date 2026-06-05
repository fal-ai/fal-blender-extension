"""3D Gaussian Splat (3DGS) parsing and Blender import.

This module turns an INRIA/3DGS ``.ply`` (or antimatter15 ``.splat``) file —
the kind produced by ``tripo3d/triposplat`` — into renderable geometry inside
Blender.

Splats are not a native Blender primitive, so :func:`import_splat` builds a
point-cloud mesh (one vertex per Gaussian) carrying the decoded per-splat
attributes (color, opacity, scale, rotation), then attaches a Geometry Nodes
modifier that instances a small billboard quad per point with an EEVEE-friendly
material whose alpha is a radial Gaussian falloff times the splat opacity.

Design constraint: ``bpy`` is imported **lazily** inside the functions that
need it so that the pure-python + numpy parser (:func:`parse_splat_ply`) can be
unit-tested on a host machine that has no Blender. Keep the module top level
free of any ``import bpy``.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

import numpy as np

if TYPE_CHECKING:
    import bpy

__all__ = [
    "parse_splat_ply",
    "parse_splat_file",
    "import_splat",
]

# Zeroth-order spherical-harmonics constant (Y_0_0). 3DGS stores diffuse color
# as SH DC coefficients; the rendered base color is ``0.5 + C0 * f_dc``.
SH_C0 = 0.28209479177387814

# Names of the standard Blender point-domain attributes we write. These are the
# contract between :func:`import_splat` and the Geometry Nodes group / material.
ATTR_COLOR = "splat_color"
ATTR_OPACITY = "splat_opacity"
ATTR_SCALE = "splat_scale"
ATTR_ROTATION = "splat_rotation"

# Datablock names so re-import reuses the same node group / material.
NODE_GROUP_NAME = "fal_splat_nodes"
MATERIAL_NAME = "fal_splat_material"

# PLY scalar type -> numpy dtype string (byte order is prepended later).
_PLY_TYPE_TO_NUMPY: dict[str, str] = {
    "char": "i1",
    "int8": "i1",
    "uchar": "u1",
    "uint8": "u1",
    "short": "i2",
    "int16": "i2",
    "ushort": "u2",
    "uint16": "u2",
    "int": "i4",
    "int32": "i4",
    "uint": "u4",
    "uint32": "u4",
    "float": "f4",
    "float32": "f4",
    "double": "f8",
    "float64": "f8",
}


# ---------------------------------------------------------------------------
# PLY parsing (pure python + numpy — host-unit-testable, no bpy)
# ---------------------------------------------------------------------------


def _sigmoid(x: np.ndarray) -> np.ndarray:
    """Numerically-stable logistic sigmoid, applied element-wise."""
    out = np.empty_like(x, dtype=np.float64)
    pos = x >= 0
    neg = ~pos
    out[pos] = 1.0 / (1.0 + np.exp(-x[pos]))
    exp_x = np.exp(x[neg])
    out[neg] = exp_x / (1.0 + exp_x)
    return out


def _parse_ply_header(raw: bytes) -> tuple[str, int, list[tuple[str, str]], int]:
    """Parse a PLY header.

    Returns ``(fmt, vertex_count, properties, body_offset)`` where:

    - ``fmt`` is one of ``"ascii"``, ``"binary_little_endian"``,
      ``"binary_big_endian"``.
    - ``properties`` is the list of ``(name, numpy_dtype)`` for the ``vertex``
      element, in file order.
    - ``body_offset`` is the byte index just past ``end_header``.

    Only the ``vertex`` element is read — 3DGS PLYs store every Gaussian as a
    vertex with no faces. Any other element's properties are ignored.
    """
    end_token = b"end_header"
    idx = raw.find(end_token)
    if idx == -1:
        raise ValueError("Not a PLY file: missing 'end_header'")
    # Body starts after the newline that follows 'end_header'.
    newline = raw.find(b"\n", idx)
    body_offset = newline + 1 if newline != -1 else idx + len(end_token)

    header = raw[:idx].decode("ascii", errors="replace")
    lines = [ln.strip() for ln in header.splitlines() if ln.strip()]
    if not lines or lines[0] != "ply":
        raise ValueError("Not a PLY file: missing 'ply' magic")

    fmt = "ascii"
    vertex_count = 0
    properties: list[tuple[str, str]] = []
    current_element: str | None = None

    for line in lines[1:]:
        tokens = line.split()
        keyword = tokens[0]
        if keyword == "format":
            fmt = tokens[1]
        elif keyword == "element":
            current_element = tokens[1]
            if current_element == "vertex":
                vertex_count = int(tokens[2])
        elif keyword == "property" and current_element == "vertex":
            # We never expect list properties on the vertex element of a 3DGS
            # file, so only scalar `property <type> <name>` is handled.
            if tokens[1] == "list":
                raise ValueError("List properties on vertex element are unsupported")
            ply_type, name = tokens[1], tokens[2]
            np_type = _PLY_TYPE_TO_NUMPY.get(ply_type)
            if np_type is None:
                raise ValueError(f"Unknown PLY property type: {ply_type}")
            properties.append((name, np_type))

    if not properties:
        raise ValueError("PLY has no 'vertex' element properties")

    return fmt, vertex_count, properties, body_offset


def _read_ply_fields(path: str) -> tuple[dict[str, np.ndarray], int]:
    """Read every vertex property of a PLY into ``{name: column}`` arrays."""
    with open(path, "rb") as f:
        raw = f.read()

    fmt, count, properties, body_offset = _parse_ply_header(raw)
    names = [name for name, _ in properties]

    if fmt == "ascii":
        # Whitespace-separated rows; one Gaussian per line.
        body = raw[body_offset:].decode("ascii", errors="replace")
        rows = [ln.split() for ln in body.splitlines() if ln.strip()]
        rows = rows[:count] if count else rows
        data = np.array(rows, dtype=np.float64)
        if data.ndim == 1:
            data = data.reshape(-1, len(names)) if data.size else data.reshape(0, len(names))
        fields = {name: data[:, i].astype(np.float64) for i, name in enumerate(names)}
        return fields, (data.shape[0] if data.size else 0)

    byte_order = "<" if fmt == "binary_little_endian" else ">"
    dtype = np.dtype([(name, byte_order + t) for name, t in properties])
    record_bytes = dtype.itemsize
    available = len(raw) - body_offset
    if count == 0:
        count = available // record_bytes
    needed = count * record_bytes
    if available < needed:
        raise ValueError(
            f"PLY body truncated: need {needed} bytes for {count} vertices, "
            f"have {available}"
        )
    structured = np.frombuffer(raw, dtype=dtype, count=count, offset=body_offset)
    # Cast every column to float64 so downstream math is uniform.
    fields = {name: structured[name].astype(np.float64) for name in names}
    return fields, count


def _stack(fields: dict[str, np.ndarray], names: list[str], count: int) -> np.ndarray | None:
    """Stack named columns into ``(N, len(names))``; ``None`` if any are absent."""
    if not all(name in fields for name in names):
        return None
    return np.stack([fields[name] for name in names], axis=-1).astype(np.float64)


def parse_splat_ply(path: str) -> dict[str, Any]:
    """Parse a 3DGS ``.ply`` file into decoded numpy arrays.

    Returns a dict with float32 arrays:

    - ``positions`` ``(N, 3)`` — raw XYZ.
    - ``colors`` ``(N, 3)`` — RGB in 0..1, decoded from the SH DC terms
      ``f_dc_0/1/2`` via ``0.5 + C0 * f_dc`` (clamped to 0..1). Defaults to
      mid-grey when the DC terms are absent.
    - ``opacity`` ``(N,)`` — sigmoid of the ``opacity`` field (defaults to 1.0).
    - ``scales`` ``(N, 3)`` — ``exp`` of ``scale_0..2`` (defaults to 1.0).
    - ``rotations`` ``(N, 4)`` — quaternion ``wxyz`` normalized from
      ``rot_0..3`` (defaults to identity ``1,0,0,0``).
    - ``count`` ``int`` — number of Gaussians.

    Robust to missing optional fields and to ascii / binary little- or
    big-endian PLYs. Pure python + numpy — no ``bpy`` dependency.
    """
    fields, count = _read_ply_fields(path)

    # Positions are required; without them there is nothing to render.
    positions = _stack(fields, ["x", "y", "z"], count)
    if positions is None:
        raise ValueError("PLY vertex element is missing x/y/z position properties")
    count = positions.shape[0]

    # Color from the spherical-harmonics DC band.
    f_dc = _stack(fields, ["f_dc_0", "f_dc_1", "f_dc_2"], count)
    if f_dc is not None:
        colors = np.clip(0.5 + SH_C0 * f_dc, 0.0, 1.0)
    else:
        colors = np.full((count, 3), 0.5, dtype=np.float64)

    # Opacity is stored as a logit; squash into 0..1.
    if "opacity" in fields:
        opacity = _sigmoid(fields["opacity"])
    else:
        opacity = np.ones(count, dtype=np.float64)

    # Scales are stored in log space.
    scales = _stack(fields, ["scale_0", "scale_1", "scale_2"], count)
    if scales is not None:
        scales = np.exp(scales)
    else:
        scales = np.ones((count, 3), dtype=np.float64)

    # Rotation quaternion is stored unnormalized as (w, x, y, z).
    rotations = _stack(fields, ["rot_0", "rot_1", "rot_2", "rot_3"], count)
    if rotations is not None:
        norms = np.linalg.norm(rotations, axis=-1, keepdims=True)
        # Guard against zero-length quaternions -> fall back to identity.
        zero = norms[:, 0] < 1e-12
        norms[zero] = 1.0
        rotations = rotations / norms
        if np.any(zero):
            rotations[zero] = np.array([1.0, 0.0, 0.0, 0.0])
    else:
        rotations = np.tile(np.array([1.0, 0.0, 0.0, 0.0]), (count, 1))

    return {
        "positions": positions.astype(np.float32),
        "colors": colors.astype(np.float32),
        "opacity": opacity.astype(np.float32),
        "scales": scales.astype(np.float32),
        "rotations": rotations.astype(np.float32),
        "count": int(count),
    }


def _parse_splat_buffer(raw: bytes) -> dict[str, Any]:
    """Parse the antimatter15 ``.splat`` packed format.

    Layout is 32 bytes per Gaussian: position ``3×float32``, scale
    ``3×float32``, color ``4×uint8`` (RGBA, already 0..255), rotation
    ``4×uint8`` (each byte ``(q+1)*128`` of a normalized quaternion ``wxyz``).
    Colors/opacity arrive display-ready, so no SH / sigmoid decode is needed.
    """
    stride = 32
    count = len(raw) // stride
    arr = np.frombuffer(raw, dtype=np.uint8, count=count * stride).reshape(count, stride)

    floats = arr[:, :24].copy().view(np.float32).reshape(count, 6)
    positions = floats[:, 0:3].astype(np.float32)
    scales = floats[:, 3:6].astype(np.float32)

    rgba = arr[:, 24:28].astype(np.float32) / 255.0
    colors = rgba[:, 0:3]
    opacity = rgba[:, 3]

    # Bytes encode each quaternion component as (q + 1) * 128.
    quat = (arr[:, 28:32].astype(np.float32) - 128.0) / 128.0
    norms = np.linalg.norm(quat, axis=-1, keepdims=True)
    norms[norms[:, 0] < 1e-12] = 1.0
    rotations = quat / norms

    return {
        "positions": positions,
        "colors": colors.astype(np.float32),
        "opacity": opacity.astype(np.float32),
        "scales": scales,
        "rotations": rotations.astype(np.float32),
        "count": int(count),
    }


def parse_splat_file(path: str) -> dict[str, Any]:
    """Parse a splat file, dispatching on extension (``.ply`` vs ``.splat``)."""
    lower = path.lower()
    if lower.endswith(".splat"):
        with open(path, "rb") as f:
            return _parse_splat_buffer(f.read())
    return parse_splat_ply(path)


# ---------------------------------------------------------------------------
# Blender import (bpy imported lazily; not exercised by host unit tests)
# ---------------------------------------------------------------------------


def _ensure_splat_material(get_eevee_blend: bool = True) -> "bpy.types.Material":
    """Build (or reuse) the EEVEE billboard material for splat instances.

    The material reads two instance attributes written by :func:`import_splat`:

    - ``splat_color`` — per-splat RGB, drives an Emission shader so the cloud
      reads correctly regardless of scene lighting.
    - ``splat_opacity`` — per-splat alpha multiplier.

    The quad's UV is used to build a radial Gaussian falloff: alpha peaks at
    the quad center and decays toward the edges, approximating a 2D Gaussian
    footprint. Final alpha = ``gaussian(uv) * splat_opacity``, blended over the
    background via a Transparent/Emission Mix Shader.
    """
    import bpy

    mat = bpy.data.materials.get(MATERIAL_NAME)
    if mat is not None:
        return mat

    mat = bpy.data.materials.new(MATERIAL_NAME)
    mat.use_nodes = True

    # EEVEE-Next (Blender 4.2) renamed the legacy `blend_method`. Set whichever
    # the running build exposes so transparency actually composits.
    if hasattr(mat, "surface_render_method"):
        # 4.2+: "BLENDED" = order-independent alpha blend (no z-prepass).
        mat.surface_render_method = "BLENDED"
    if hasattr(mat, "blend_method"):
        mat.blend_method = "BLEND"
    if hasattr(mat, "show_transparent_back"):
        mat.show_transparent_back = False

    tree = mat.node_tree
    nodes = tree.nodes
    links = tree.links
    nodes.clear()

    output = nodes.new("ShaderNodeOutputMaterial")
    output.location = (600, 0)

    mix = nodes.new("ShaderNodeMixShader")
    mix.location = (400, 0)

    transparent = nodes.new("ShaderNodeBsdfTransparent")
    transparent.location = (200, 120)

    emission = nodes.new("ShaderNodeEmission")
    emission.location = (200, -120)
    emission.inputs["Strength"].default_value = 1.0

    # Per-instance color (the points carry it; instancing promotes it to the
    # instance domain, which the INSTANCER attribute type reads back).
    color_attr = nodes.new("ShaderNodeAttribute")
    color_attr.location = (-200, -120)
    color_attr.attribute_type = "INSTANCER"
    color_attr.attribute_name = ATTR_COLOR
    links.new(color_attr.outputs["Color"], emission.inputs["Color"])

    # Per-instance opacity multiplier.
    opacity_attr = nodes.new("ShaderNodeAttribute")
    opacity_attr.location = (-200, 320)
    opacity_attr.attribute_type = "INSTANCER"
    opacity_attr.attribute_name = ATTR_OPACITY

    # Radial Gaussian falloff from the quad UVs: center the UV, take its length,
    # then alpha = exp(-(r * k)^2). k controls how tight the dot is.
    tex_coord = nodes.new("ShaderNodeTexCoord")
    tex_coord.location = (-600, 200)

    center = nodes.new("ShaderNodeVectorMath")
    center.location = (-400, 200)
    center.operation = "SUBTRACT"
    center.inputs[1].default_value = (0.5, 0.5, 0.0)
    links.new(tex_coord.outputs["UV"], center.inputs[0])

    radius = nodes.new("ShaderNodeVectorMath")
    radius.location = (-200, 200)
    radius.operation = "LENGTH"
    links.new(center.outputs["Vector"], radius.inputs[0])

    # Scale radius (0..~0.707 across the quad) so the falloff fills the quad.
    scale_r = nodes.new("ShaderNodeMath")
    scale_r.location = (0, 320)
    scale_r.operation = "MULTIPLY"
    scale_r.inputs[1].default_value = 4.0  # falloff tightness
    links.new(radius.outputs["Value"], scale_r.inputs[0])

    sq = nodes.new("ShaderNodeMath")
    sq.location = (160, 320)
    sq.operation = "MULTIPLY"
    links.new(scale_r.outputs["Value"], sq.inputs[0])
    links.new(scale_r.outputs["Value"], sq.inputs[1])

    neg = nodes.new("ShaderNodeMath")
    neg.location = (320, 320)
    neg.operation = "MULTIPLY"
    neg.inputs[1].default_value = -1.0
    links.new(sq.outputs["Value"], neg.inputs[0])

    gauss = nodes.new("ShaderNodeMath")
    gauss.location = (480, 320)
    gauss.operation = "EXPONENT"  # e^x
    links.new(neg.outputs["Value"], gauss.inputs[0])

    # alpha = gaussian * splat_opacity
    alpha = nodes.new("ShaderNodeMath")
    alpha.location = (640, 320)
    alpha.operation = "MULTIPLY"
    links.new(gauss.outputs["Value"], alpha.inputs[0])
    links.new(opacity_attr.outputs["Fac"], alpha.inputs[1])

    # Mix factor 0 -> transparent, 1 -> emission, so feed alpha as the factor.
    links.new(alpha.outputs["Value"], mix.inputs["Fac"])
    links.new(transparent.outputs["BSDF"], mix.inputs[1])
    links.new(emission.outputs["Emission"], mix.inputs[2])
    links.new(mix.outputs["Shader"], output.inputs["Surface"])

    return mat


def _ensure_splat_node_group(material: "bpy.types.Material") -> "bpy.types.GeometryNodeTree":
    """Build (or reuse) the Geometry Nodes group that instances billboards.

    Pipeline: the input point-cloud mesh feeds *Instance on Points*; each point
    gets a unit billboard quad (a 2×2 *Grid*) carrying ``material``, scaled by
    the ``splat_scale`` vector attribute and oriented by the ``splat_rotation``
    quaternion attribute. The per-point color/opacity attributes ride along to
    the instance domain for the material to read.
    """
    import bpy

    group = bpy.data.node_groups.get(NODE_GROUP_NAME)
    if group is not None:
        return group

    group = bpy.data.node_groups.new(NODE_GROUP_NAME, "GeometryNodeTree")

    # Group interface: geometry in, geometry out (Blender 4.x interface API).
    group.interface.new_socket(
        name="Geometry", in_out="INPUT", socket_type="NodeSocketGeometry"
    )
    group.interface.new_socket(
        name="Geometry", in_out="OUTPUT", socket_type="NodeSocketGeometry"
    )

    nodes = group.nodes
    links = group.links

    group_in = nodes.new("NodeGroupInput")
    group_in.location = (-600, 0)
    group_out = nodes.new("NodeGroupOutput")
    group_out.location = (600, 0)

    # The billboard source: a single quad (2×2 grid) with UVs for the material.
    grid = nodes.new("GeometryNodeMeshGrid")
    grid.location = (-400, -260)
    grid.inputs["Size X"].default_value = 1.0
    grid.inputs["Size Y"].default_value = 1.0
    grid.inputs["Vertices X"].default_value = 2
    grid.inputs["Vertices Y"].default_value = 2

    set_mat = nodes.new("GeometryNodeSetMaterial")
    set_mat.location = (-200, -260)
    set_mat.inputs["Material"].default_value = material
    links.new(grid.outputs["Mesh"], set_mat.inputs["Geometry"])

    # Per-point scale (FLOAT_VECTOR) and rotation (QUATERNION -> Rotation socket).
    scale_attr = nodes.new("GeometryNodeInputNamedAttribute")
    scale_attr.location = (-400, 180)
    scale_attr.data_type = "FLOAT_VECTOR"
    scale_attr.inputs["Name"].default_value = ATTR_SCALE

    rot_attr = nodes.new("GeometryNodeInputNamedAttribute")
    rot_attr.location = (-400, 60)
    rot_attr.data_type = "QUATERNION"
    rot_attr.inputs["Name"].default_value = ATTR_ROTATION

    instance = nodes.new("GeometryNodeInstanceOnPoints")
    instance.location = (0, 0)
    links.new(group_in.outputs["Geometry"], instance.inputs["Points"])
    links.new(set_mat.outputs["Geometry"], instance.inputs["Instance"])
    links.new(scale_attr.outputs["Attribute"], instance.inputs["Scale"])
    links.new(rot_attr.outputs["Attribute"], instance.inputs["Rotation"])

    links.new(instance.outputs["Instances"], group_out.inputs["Geometry"])

    return group


def import_splat(
    filepath: str,
    *,
    name: str = "fal_splat",
    location: tuple[float, float, float] | None = None,
) -> "bpy.types.Object":
    """Import a Gaussian-splat file as a renderable Blender object.

    Builds a point-cloud mesh (one vertex per Gaussian) with the decoded
    per-splat attributes, then attaches a Geometry Nodes modifier (shared
    node group + EEVEE material) that renders each splat as a soft billboard.

    Returns the created object.
    """
    import bpy

    data = parse_splat_file(filepath)
    positions = data["positions"]
    colors = data["colors"]
    opacity = data["opacity"]
    scales = data["scales"]
    rotations = data["rotations"]
    count = data["count"]

    # --- Mesh: verts only, no edges/faces ---
    mesh = bpy.data.meshes.new(name)
    mesh.from_pydata(positions.tolist(), [], [])
    mesh.update()

    # --- Per-point attributes ---
    # FLOAT_COLOR stores RGBA; pack the decoded RGB with alpha=1 (the live
    # alpha multiplier lives in the separate splat_opacity attribute).
    color_attr = mesh.attributes.new(ATTR_COLOR, "FLOAT_COLOR", "POINT")
    rgba = np.empty((count, 4), dtype=np.float32)
    rgba[:, :3] = colors
    rgba[:, 3] = 1.0
    color_attr.data.foreach_set("color", rgba.reshape(-1))

    opacity_attr = mesh.attributes.new(ATTR_OPACITY, "FLOAT", "POINT")
    opacity_attr.data.foreach_set("value", np.ascontiguousarray(opacity, dtype=np.float32))

    scale_attr = mesh.attributes.new(ATTR_SCALE, "FLOAT_VECTOR", "POINT")
    scale_attr.data.foreach_set("vector", np.ascontiguousarray(scales, dtype=np.float32).reshape(-1))

    rot_attr = mesh.attributes.new(ATTR_ROTATION, "QUATERNION", "POINT")
    rot_attr.data.foreach_set("value", np.ascontiguousarray(rotations, dtype=np.float32).reshape(-1))

    mesh.update()

    # --- Object + Geometry Nodes modifier ---
    obj = bpy.data.objects.new(name, mesh)
    if location is not None:
        obj.location = location

    material = _ensure_splat_material()
    group = _ensure_splat_node_group(material)

    modifier = obj.modifiers.new(name="fal_splat", type="NODES")
    modifier.node_group = group

    # Link into the active collection (fall back to the scene collection).
    collection = getattr(bpy.context, "collection", None) or bpy.context.scene.collection
    collection.objects.link(obj)

    print(f"fal.ai: Imported Gaussian splat '{name}' with {count} splats")
    return obj

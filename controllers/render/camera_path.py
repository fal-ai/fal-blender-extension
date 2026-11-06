"""Scene-camera helpers for the Render > Video > Camera mode."""

from __future__ import annotations

import math
import os

import bpy
from mathutils import Matrix, Vector

FOV_TOLERANCE_DEGREES = 5.0
IMAGE_CARD_NAME = "fal Image Card"
_RAYS_PER_SIDE = 24


def sample_camera_poses(scene: bpy.types.Scene) -> list[list[list[float]]]:
    """Camera ``matrix_world`` (row-major 4x4) at every frame in the scene range.

    Moves the current frame; the caller restores it.
    """
    camera = scene.camera
    poses = []
    for frame in range(scene.frame_start, scene.frame_end + 1):
        scene.frame_set(frame)
        # 5 decimals: ~1e-5 error, far inside the server's 1e-3 rotation check.
        poses.append([[round(v, 5) for v in row] for row in camera.matrix_world])
    return poses


def camera_hfov_degrees(scene: bpy.types.Scene) -> float:
    """Horizontal field of view of the scene camera at the render aspect."""
    corners = scene.camera.data.view_frame(scene=scene)
    half_width = max(abs(c.x) for c in corners)
    return math.degrees(2 * math.atan2(half_width, abs(corners[0].z)))


def near_depth(scene: bpy.types.Scene, depsgraph: bpy.types.Depsgraph) -> float | None:
    """25th-percentile z-depth of geometry seen by the camera at the current frame.

    This is the model's unit of distance: the training data was normalized the
    same way. None when no ray hits anything. The image card is ignored.
    """
    camera = scene.camera
    corners = camera.data.view_frame(scene=scene)
    xs = [c.x for c in corners]
    ys = [c.y for c in corners]
    z = corners[0].z
    rotation = camera.matrix_world.to_3x3().normalized()
    origin = camera.matrix_world.translation
    forward = rotation @ Vector((0.0, 0.0, -1.0))
    depths = []
    steps = [(i + 0.5) / _RAYS_PER_SIDE for i in range(_RAYS_PER_SIDE)]
    for u in steps:
        for v in steps:
            local = Vector(
                (
                    min(xs) + u * (max(xs) - min(xs)),
                    min(ys) + v * (max(ys) - min(ys)),
                    z,
                )
            )
            direction = (rotation @ local).normalized()
            hit, location, _, _, obj, _ = scene.ray_cast(depsgraph, origin, direction)
            if hit and obj.name == IMAGE_CARD_NAME:
                hit, location, *_ = scene.ray_cast(
                    depsgraph, location + direction * 1e-4, direction
                )
            if hit:
                depths.append((location - origin).dot(forward))
    if not depths:
        return None
    depths.sort()
    return depths[int(0.25 * (len(depths) - 1))]


def _new_image_card() -> bpy.types.Object:
    """A unit plane with an unlit image material (preview only, never rendered)."""
    mesh = bpy.data.meshes.new(IMAGE_CARD_NAME)
    corners = [(-0.5, -0.5), (0.5, -0.5), (0.5, 0.5), (-0.5, 0.5)]
    mesh.from_pydata([(x, y, 0.0) for x, y in corners], [], [(0, 1, 2, 3)])
    uv = mesh.uv_layers.new()
    for loop, (x, y) in zip(uv.data, corners):
        loop.uv = (x + 0.5, y + 0.5)
    material = bpy.data.materials.new(IMAGE_CARD_NAME)
    material.use_nodes = True
    nodes = material.node_tree.nodes
    nodes.clear()
    texture = nodes.new("ShaderNodeTexImage")
    emission = nodes.new("ShaderNodeEmission")
    output = nodes.new("ShaderNodeOutputMaterial")
    material.node_tree.links.new(texture.outputs["Color"], emission.inputs["Color"])
    material.node_tree.links.new(emission.outputs[0], output.inputs[0])
    nodes.active = texture  # Solid view's "Texture" color shows the active node
    mesh.materials.append(material)
    card = bpy.data.objects.new(IMAGE_CARD_NAME, mesh)
    card.hide_render = True
    return card


def place_image_card(scene: bpy.types.Scene, props: bpy.types.PropertyGroup) -> None:
    """Put the input image on a plane at Subject Distance in front of the
    first-frame camera, filling its view, so playback previews the move."""
    camera = scene.camera
    path = bpy.path.abspath(props.camera_image_path)
    if camera is None or camera.type != "CAMERA" or not os.path.isfile(path):
        return
    card = bpy.data.objects.get(IMAGE_CARD_NAME) or _new_image_card()
    if card.name not in scene.objects:
        scene.collection.objects.link(card)
    texture = next(
        n for n in card.data.materials[0].node_tree.nodes if n.type == "TEX_IMAGE"
    )
    texture.image = bpy.data.images.load(path, check_existing=True)

    current = scene.frame_current
    scene.frame_set(scene.frame_start)
    location, rotation, _ = camera.matrix_world.decompose()
    scene.frame_set(current)
    frame = camera.data.view_frame(scene=scene)
    distance = props.camera_subject_distance
    stretch = distance / abs(frame[0].z)
    size = Vector(
        (
            2 * max(abs(c.x) for c in frame) * stretch,
            2 * max(abs(c.y) for c in frame) * stretch,
            1.0,
        )
    )
    card.matrix_world = Matrix.LocRotScale(
        location + rotation @ Vector((0.0, 0.0, -distance)), rotation, size
    )


def on_image_changed(props: bpy.types.PropertyGroup, context: bpy.types.Context):
    """Match the render aspect to the image, then place the preview card."""
    path = bpy.path.abspath(props.camera_image_path)
    if not os.path.isfile(path):
        return
    image = bpy.data.images.load(path, check_existing=True)
    render = context.scene.render
    render.resolution_x, render.resolution_y = image.size
    render.resolution_percentage = 100
    place_image_card(context.scene, props)
    for area in context.screen.areas if context.screen else []:
        if area.type == "VIEW_3D" and area.spaces.active.shading.type == "SOLID":
            area.spaces.active.shading.color_type = "TEXTURE"


def on_distance_changed(props: bpy.types.PropertyGroup, context: bpy.types.Context):
    if props.camera_image_source == "FILE":
        place_image_card(context.scene, props)


def camera_problems(context: bpy.types.Context, model) -> list[str]:
    """Reasons the Camera mode can't submit, in the order a user would fix them."""
    scene = context.scene
    camera = scene.camera
    if camera is None:
        return ["Add a scene camera"]
    if camera.data.type != "PERSP":
        return ["The scene camera must be perspective"]
    fps = scene.render.fps / scene.render.fps_base
    seconds = (scene.frame_end - scene.frame_start + 1) / fps
    if not model.duration_min <= seconds <= model.duration_max:
        return [
            f"Frame range is {seconds:.1f}s; needs "
            f"{model.duration_min}-{model.duration_max}s"
        ]
    return []


def draw_camera_checks(
    layout: bpy.types.UILayout, context: bpy.types.Context, props, model
) -> None:
    """Card refresh, then problems, then a lens warning with a one-click fix."""
    if props.camera_image_source == "FILE" and props.camera_image_path.strip():
        box = layout.box()
        col = box.column(align=True)
        col.label(text="Image card: preview only, not rendered.", icon="INFO")
        col.label(text="It fills the first-frame camera view,")
        col.label(text="Subject Distance in front of it.")
        col.label(text="Your camera path is never changed.")
        box.operator(FAL_OT_PlaceImageCard.bl_idname, icon="IMAGE_PLANE")
    problems = camera_problems(context, model)
    for problem in problems:
        layout.label(text=problem, icon="ERROR")
    if problems:
        return
    hfov = camera_hfov_degrees(context.scene)
    if abs(hfov - model.horizontal_fov_degrees) > FOV_TOLERANCE_DEGREES:
        box = layout.box()
        box.label(
            text=f"Camera FOV {hfov:.0f}°, model sees {model.horizontal_fov_degrees:.0f}°",
            icon="INFO",
        )
        box.operator(FAL_OT_MatchModelFov.bl_idname, icon="CAMERA_DATA")


class FAL_OT_MatchModelFov(bpy.types.Operator):
    """Set the scene camera's horizontal field of view to what the model assumes"""

    bl_idname = "fal.match_model_fov"
    bl_label = "Set Camera FOV to 64°"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context: bpy.types.Context) -> set[str]:
        camera = context.scene.camera
        if camera is None or camera.data.type != "PERSP":
            self.report({"ERROR"}, "Needs a perspective scene camera")
            return {"CANCELLED"}
        camera.data.sensor_fit = "HORIZONTAL"
        camera.data.angle_x = math.radians(64.0)
        on_distance_changed(context.scene.falrendercontroller_props, context)
        return {"FINISHED"}


class FAL_OT_PlaceImageCard(bpy.types.Operator):
    """Re-place the image card after editing the camera's first frame or lens"""

    bl_idname = "fal.place_image_card"
    bl_label = "Update Image Card"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context: bpy.types.Context) -> set[str]:
        place_image_card(context.scene, context.scene.falrendercontroller_props)
        return {"FINISHED"}

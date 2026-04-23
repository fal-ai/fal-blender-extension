from __future__ import annotations

from ...models import ImageTo3DModel, TextTo3DModel
from ..base import FalController
from ..ui import FalControllerPanel
from .operator import FalGenerate3DOperator
from .props import FalGenerate3DPropertyGroup


def _selected_model(ctx, props):
    """Return the model class currently selected by the mode/endpoint enums."""
    if props.mode == "TEXT":
        catalog = TextTo3DModel.catalog()
        key = props.text_endpoint
    else:
        catalog = ImageTo3DModel.catalog()
        key = props.image_endpoint
    return catalog.get(key)


def _endpoint_supports(field_name):
    """Condition factory: True if the selected endpoint declares this UI field."""

    def check(ctx, props):
        model = _selected_model(ctx, props)
        if model is None:
            return False
        return field_name in getattr(model, "ui_parameter_map", {})

    return check


class FalGenerate3DController(FalController):
    """Controller for text-to-3D and image-to-3D model generation via fal.ai."""

    display_name = "3D Generation"
    description = "Generate 3D models from text or images using fal.ai"
    icon = "MESH_MONKEY"
    operator_class = FalGenerate3DOperator
    properties_class = FalGenerate3DPropertyGroup
    panel_3d = FalControllerPanel(
        field_orders=[
            "mode",
            "text_endpoint",
            "image_endpoint",
            "prompt",
            "negative_prompt",
            "texture_prompt",
            "image_source",
            "image_path",
            "generate_materials",
            # Meshy-specific
            "meshy_mode",
            "art_style",
            # Hunyuan
            "hunyuan_generate_type",
            "enable_geometry",
            # Tripo h3.1 quality knobs
            "geometry_quality",
            "texture_quality",
            "quad",
            "auto_size",
            "orientation",
            "texture_alignment",
            # Shared
            "face_count",
            "symmetry_mode",
            "pose_mode",
            "seed",
            "texture_seed",
        ],
        field_conditions={
            "text_endpoint": lambda ctx, props: props.mode == "TEXT",
            "image_endpoint": lambda ctx, props: props.mode == "IMAGE",
            "image_source": lambda ctx, props: props.mode == "IMAGE",
            "image_path": lambda ctx, props: props.mode == "IMAGE"
            and props.image_source == "FILE",
            "negative_prompt": _endpoint_supports("negative_prompt"),
            "texture_prompt": _endpoint_supports("texture_prompt"),
            "meshy_mode": _endpoint_supports("meshy_mode"),
            "art_style": _endpoint_supports("art_style"),
            "hunyuan_generate_type": _endpoint_supports("hunyuan_generate_type"),
            "enable_geometry": _endpoint_supports("enable_geometry"),
            "geometry_quality": _endpoint_supports("geometry_quality"),
            "texture_quality": _endpoint_supports("texture_quality"),
            "quad": _endpoint_supports("quad"),
            "auto_size": _endpoint_supports("auto_size"),
            "orientation": _endpoint_supports("orientation"),
            "texture_alignment": _endpoint_supports("texture_alignment"),
            "face_count": _endpoint_supports("face_count"),
            "symmetry_mode": _endpoint_supports("symmetry_mode"),
            "pose_mode": _endpoint_supports("pose_mode"),
            "seed": _endpoint_supports("seed"),
            "texture_seed": _endpoint_supports("texture_seed"),
        },
        endpoint_models={
            "text_endpoint": TextTo3DModel,
            "image_endpoint": ImageTo3DModel,
        },
    )

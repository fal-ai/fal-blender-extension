from ...models import MaterialGenerationModel, PBREstimationModel, TilingTextureModel
from ..base import FalController
from ..ui import FalControllerPanel
from .operator import FalMaterialOperator
from .props import FalMaterialPropertyGroup


class FalMaterialController(FalController):
    """Controller for PBR material generation via fal.ai."""

    display_name = "Material"
    description = "Generate PBR materials using fal.ai"
    icon = "MATERIAL"
    operator_class = FalMaterialOperator
    properties_class = FalMaterialPropertyGroup
    panel_3d = FalControllerPanel(
        field_orders=[
            "mode",
            "full_endpoint",
            "tiling_endpoint",
            "pbr_endpoint",
            "prompt",
            "enable_prompt_expansion",
            "image_source",
            "image_path",
            "texture",
            "width",
            "height",
            "tiling_mode",
            "upscale_factor",
            "output_format",
            "seed",
        ],
        field_conditions={
            "full_endpoint": lambda ctx, props: props.mode == "FULL",
            "tiling_endpoint": lambda ctx, props: props.mode == "TILING_ONLY",
            "pbr_endpoint": lambda ctx, props: props.mode == "PBR_ONLY",
            "prompt": lambda ctx, props: props.mode in ("FULL", "TILING_ONLY"),
            "enable_prompt_expansion": lambda ctx, props: props.mode
            in ("FULL", "TILING_ONLY"),
            "image_source": lambda ctx, props: props.mode == "PBR_ONLY",
            "image_path": lambda ctx, props: props.mode == "PBR_ONLY"
            and props.image_source == "FILE",
            "texture": lambda ctx, props: props.mode == "PBR_ONLY"
            and props.image_source == "TEXTURE",
            "width": lambda ctx, props: props.mode in ("FULL", "TILING_ONLY"),
            "height": lambda ctx, props: props.mode in ("FULL", "TILING_ONLY"),
            "tiling_mode": lambda ctx, props: props.mode in ("FULL", "TILING_ONLY"),
            "upscale_factor": lambda ctx, props: props.mode in ("FULL", "PBR_ONLY"),
            "seed": lambda ctx, props: props.mode in ("FULL", "TILING_ONLY"),
        },
        field_groupings=[
            {"width", "height"},
        ],
        field_separators=["mode"],
        endpoint_models={
            "full_endpoint": MaterialGenerationModel,
            "tiling_endpoint": TilingTextureModel,
            "pbr_endpoint": PBREstimationModel,
        },
    )

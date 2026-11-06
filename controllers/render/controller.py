from ...models import (
    DepthGuidedImageGenerationModel,
    DepthVideoModel,
    EdgeGuidedImageGenerationModel,
    EdgeVideoModel,
    H3MaxCameraControlVideoModel,
    ImageRefinementModel,
    SketchGuidedImageGenerationModel,
)
from ..base import FalController
from ..ui import FalControllerPanel
from .camera_path import draw_camera_checks
from .operator import FalRenderOperator
from .props import FalRenderPropertyGroup

# Models that support system prompts in refine mode
REFINE_MODELS = ImageRefinementModel.catalog()


def _show_refine_system_prompt(context, props) -> bool:
    """Show system prompt only for refine mode with models that support it."""
    if props.render_type != "IMAGE" or props.mode != "REFINE":
        return False
    model_cls = REFINE_MODELS.get(props.refine_endpoint)
    if model_cls is None:
        return False
    return getattr(model_cls, "supports_system_prompt", True)


def _show_cns_toggle(context, props) -> bool:
    """Show the CNS toggle only for refine models that support CNS sampling."""
    if props.render_type != "IMAGE" or props.mode != "REFINE":
        return False
    model_cls = REFINE_MODELS.get(props.refine_endpoint)
    if model_cls is None:
        return False
    return getattr(model_cls, "supports_cns", False)


def _show_cns_params(context, props) -> bool:
    """Show the individual CNS knobs only once CNS is enabled."""
    return _show_cns_toggle(context, props) and props.enable_cns


def _is_image(context, props) -> bool:
    return props.render_type == "IMAGE"


def _is_video(context, props) -> bool:
    return props.render_type == "VIDEO"


def _image_mode(mode):
    """Return a condition that checks render_type == IMAGE and mode matches."""

    def check(context, props) -> bool:
        return props.render_type == "IMAGE" and props.mode == mode

    return check


def _video_mode(mode):
    """Return a condition that checks render_type == VIDEO and video_mode matches."""

    def check(context, props) -> bool:
        return props.render_type == "VIDEO" and props.video_mode == mode

    return check


def _video_not_camera(context, props) -> bool:
    return props.render_type == "VIDEO" and props.video_mode != "CAMERA"


class _RenderPanel(FalControllerPanel):
    """Camera Controls has one model, so no endpoint dropdown to resolve."""

    def _get_active_model(self, context, props):
        if _video_mode("CAMERA")(context, props):
            return H3MaxCameraControlVideoModel
        return super()._get_active_model(context, props)

    def draw_status(self, layout, context, props) -> None:
        super().draw_status(layout, context, props)
        if _video_mode("CAMERA")(context, props):
            draw_camera_checks(layout, context, props, H3MaxCameraControlVideoModel)


class FalRenderController(FalController):
    """Controller for rendering workflows via fal.ai."""

    display_name = "Render"
    description = "Render scene data and generate AI images or video via fal.ai"
    icon = "RENDER_RESULT"
    operator_class = FalRenderOperator
    properties_class = FalRenderPropertyGroup
    panel_3d = _RenderPanel(
        field_orders=[
            "render_type",
            # Image-specific
            "mode",
            "depth_endpoint",
            "edge_endpoint",
            "sketch_endpoint",
            "sketch_system_prompt",
            "enable_labels",
            "auto_label",
            "refine_endpoint",
            "refine_strength",
            "refine_system_prompt",
            "enable_cns",
            "cns_s_churn",
            "cns_gamma_source",
            "cns_power_gamma",
            "cns_gamma_divider",
            "cns_alpha_tilt_start",
            "cns_alpha_tilt_end",
            "cns_alpha_use_fnorm",
            "cns_alpha_exp_interp",
            "cns_alpha_exp_sharpness",
            "cns_num_freq_bins",
            "cns_energy_scale",
            # Video-specific
            "video_mode",
            "depth_video_endpoint",
            "edge_video_endpoint",
            "edge_parallel_threads",
            "camera_image_source",
            "camera_image_path",
            "camera_resolution",
            "camera_auto_scale",
            "camera_subject_distance",
            "use_scene_duration",
            "duration",
            "video_use_first_frame",
            "video_image_source",
            "video_image_path",
            "video_texture",
            # Common
            "prompt",
            "enable_prompt_expansion",
            "use_scene_resolution",
            "width",
            "height",
            "seed",
        ],
        field_conditions={
            # Image vs Video visibility
            "mode": _is_image,
            "seed": _is_image,
            "video_mode": _is_video,
            "use_scene_duration": _video_not_camera,
            "duration": lambda context, props: _video_not_camera(context, props)
            and not props.use_scene_duration,
            "video_use_first_frame": _video_not_camera,
            "video_image_source": lambda context, props: _video_not_camera(
                context, props
            )
            and props.video_use_first_frame,
            "video_image_path": lambda context, props: _video_not_camera(context, props)
            and props.video_use_first_frame
            and props.video_image_source == "FILE",
            "video_texture": lambda context, props: _video_not_camera(context, props)
            and props.video_use_first_frame
            and props.video_image_source == "TEXTURE",
            # Image mode endpoints
            "depth_endpoint": _image_mode("DEPTH"),
            "edge_endpoint": _image_mode("EDGE"),
            "sketch_endpoint": _image_mode("SKETCH"),
            "sketch_system_prompt": _image_mode("SKETCH"),
            "enable_labels": _image_mode("SKETCH"),
            "auto_label": _image_mode("SKETCH"),
            "refine_endpoint": _image_mode("REFINE"),
            "refine_strength": _image_mode("REFINE"),
            "refine_system_prompt": _show_refine_system_prompt,
            "enable_cns": _show_cns_toggle,
            "cns_s_churn": _show_cns_params,
            "cns_gamma_source": _show_cns_params,
            "cns_power_gamma": _show_cns_params,
            "cns_gamma_divider": _show_cns_params,
            "cns_alpha_tilt_start": _show_cns_params,
            "cns_alpha_tilt_end": _show_cns_params,
            "cns_alpha_use_fnorm": _show_cns_params,
            "cns_alpha_exp_interp": _show_cns_params,
            "cns_alpha_exp_sharpness": _show_cns_params,
            "cns_num_freq_bins": _show_cns_params,
            "cns_energy_scale": _show_cns_params,
            # Video mode endpoints
            "depth_video_endpoint": _video_mode("DEPTH"),
            "edge_video_endpoint": _video_mode("EDGE"),
            "edge_parallel_threads": _video_mode("EDGE"),
            "camera_image_source": _video_mode("CAMERA"),
            "camera_image_path": lambda context, props: _video_mode("CAMERA")(
                context, props
            )
            and props.camera_image_source == "FILE",
            "camera_resolution": _video_mode("CAMERA"),
            "camera_auto_scale": lambda context, props: _video_mode("CAMERA")(
                context, props
            )
            and props.camera_image_source == "RENDER",
            "camera_subject_distance": lambda context, props: _video_mode("CAMERA")(
                context, props
            )
            and (props.camera_image_source == "FILE" or not props.camera_auto_scale),
            # Common conditional fields
            "enable_prompt_expansion": lambda context, props: not (
                props.render_type == "IMAGE" and props.mode == "SKETCH"
            ),
            "use_scene_resolution": lambda context, props: not _video_mode("CAMERA")(
                context, props
            ),
            "width": lambda context, props: not props.use_scene_resolution
            and not _video_mode("CAMERA")(context, props),
            "height": lambda context, props: not props.use_scene_resolution
            and not _video_mode("CAMERA")(context, props),
        },
        field_groupings=[
            {"width", "height"},
        ],
        endpoint_models={
            "depth_endpoint": DepthGuidedImageGenerationModel,
            "edge_endpoint": EdgeGuidedImageGenerationModel,
            "sketch_endpoint": SketchGuidedImageGenerationModel,
            "refine_endpoint": ImageRefinementModel,
            "depth_video_endpoint": DepthVideoModel,
            "edge_video_endpoint": EdgeVideoModel,
        },
    )

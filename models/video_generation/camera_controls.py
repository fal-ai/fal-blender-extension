from __future__ import annotations

from typing import Any, ClassVar

from .base import VideoFalModel

__all__ = ["H3MaxCameraControlVideoModel"]


class H3MaxCameraControlVideoModel(VideoFalModel):
    """MiniMax H3 Max image-to-video that follows the scene camera's path.

    ``camera_poses`` are Blender ``matrix_world`` rows, one per scene frame;
    ``camera_poses_scale`` converts Blender units into the model's unit.
    """

    endpoint = "minimax/h3-max/camera-controls"
    display_name = "MiniMax H3 Max Camera Controls"
    image_url_parameter: ClassVar[str | None] = "image_url"
    # The model renders as if the camera had this horizontal field of view.
    horizontal_fov_degrees: ClassVar[float] = 64.0
    # The canvas follows the input image; the caller picks the tier.
    use_resolution_aspect_ratio = True
    emit_aspect_ratio = False
    emit_resolution = False
    resolutions = {"480P": 480, "768P": 768, "1080P": 1080}
    duration_min = 1
    duration_max = 15

    @classmethod
    def parameters(cls, **kwargs: Any) -> dict[str, Any]:
        params: dict[str, Any] = super().parameters(**kwargs)
        params["duration"] = round(float(kwargs["duration"]), 3)
        params["resolution"] = kwargs["resolution"]
        params["camera_poses"] = {
            "convention": "blender",
            "c2w": kwargs["camera_poses"],
        }
        params["camera_poses_scale"] = float(f"{kwargs['camera_poses_scale']:.5g}")
        if not kwargs.get("enable_prompt_expansion", True):
            params["prompt_expansion_mode"] = "disabled"
        return params

"""Unit tests for model parameter generation.
These tests don't require Blender — run with pytest.

Note: These tests mock the minimal VisualFalModel behavior
since the full models module requires Blender imports.
"""

import warnings
from typing import Any, ClassVar


# Minimal mock of VisualFalModel for testing. Mirrors models/base.py —
# keep them in sync when behavior changes.
class VisualFalModel:
    """Mock of VisualFalModel for unit testing."""

    use_resolution_aspect_ratio: ClassVar[bool] = False
    emit_aspect_ratio: ClassVar[bool] = True
    emit_resolution: ClassVar[bool] = True
    aspect_ratios: ClassVar[list[str]] = []
    resolutions: ClassVar[dict[str, int]] = {}
    size_parameter: ClassVar[str | None] = None
    modulo: ClassVar[int | None] = None

    @classmethod
    def _closest_aspect_ratio(cls, width: int, height: int) -> str:
        """Pick the nearest defined aspect ratio."""
        if not cls.aspect_ratios:
            raise RuntimeError(f"No aspect ratios defined for {cls.__name__}")
        target_ratio = width / height
        best_ar = cls.aspect_ratios[0]
        best_diff = float("inf")
        for ar in cls.aspect_ratios:
            try:
                w, h = map(int, ar.split(":"))
            except ValueError as e:
                warnings.warn(f"Invalid aspect ratio {ar} for {cls.__name__}: {e}")
                continue
            diff = abs(target_ratio - w / h)
            if diff < best_diff:
                best_diff = diff
                best_ar = ar
        return best_ar

    @classmethod
    def _closest_resolution(cls, width: int, height: int) -> str:
        """Smallest tier ≥ short-side target (5% tolerance); else largest."""
        if not cls.resolutions:
            raise RuntimeError(f"No resolutions defined for {cls.__name__}")
        shortest = min(width, height)
        threshold = shortest * 0.95
        eligible = [
            (name, pixels)
            for name, pixels in cls.resolutions.items()
            if pixels >= threshold
        ]
        if eligible:
            return min(eligible, key=lambda item: item[1])[0]
        return max(cls.resolutions.items(), key=lambda item: item[1])[0]

    @classmethod
    def _to_resolution_aspect_ratio(cls, width: int, height: int) -> tuple[str, str]:
        """Kept for the legacy test helper — delegates to the split methods."""
        return (
            cls._closest_aspect_ratio(width, height),
            cls._closest_resolution(width, height),
        )

    @classmethod
    def describe_output_size(cls, width: int, height: int) -> str:
        """Human-readable summary of the effective output size."""
        if cls.use_resolution_aspect_ratio:
            parts: list[str] = []
            if cls.emit_resolution and cls.resolutions:
                parts.append(cls._closest_resolution(width, height))
            if cls.emit_aspect_ratio and cls.aspect_ratios:
                parts.append(cls._closest_aspect_ratio(width, height))
            if parts:
                return " ".join(parts)
        if cls.modulo:
            width = width // cls.modulo * cls.modulo
            height = height // cls.modulo * cls.modulo
        return f"{width}x{height}"

    @classmethod
    def _get_size_parameters(cls, width: int, height: int) -> dict[str, Any]:
        """Returns the size parameters for the model."""
        if cls.use_resolution_aspect_ratio:
            aspect_ratio, resolution = cls._to_resolution_aspect_ratio(width, height)
            return {
                "aspect_ratio": aspect_ratio,
                "resolution": resolution,
            }

        if cls.modulo:
            width = width // cls.modulo * cls.modulo
            height = height // cls.modulo * cls.modulo

        if cls.size_parameter:
            return {
                cls.size_parameter: {"width": width, "height": height},
            }

        return {
            "width": width,
            "height": height,
        }


class TestResolutionMapping:
    """Test aspect ratio and resolution tier mapping."""

    def test_16_9_aspect_ratio(self):
        """1920x1080 should map to 16:9."""

        class TestModel(VisualFalModel):
            use_resolution_aspect_ratio = True
            aspect_ratios = ["16:9", "4:3", "1:1", "9:16"]
            resolutions = {"1K": 1024, "2K": 2048}

        ar, res = TestModel._to_resolution_aspect_ratio(1920, 1080)
        assert ar == "16:9"
        assert res == "2K"  # 1920 is closer to 2048 than 1024

    def test_1280x720_maps_to_1k(self):
        """1280x720 should map to 1K (closer to 1024 than 2048)."""

        class TestModel(VisualFalModel):
            use_resolution_aspect_ratio = True
            aspect_ratios = ["16:9", "4:3", "1:1"]
            resolutions = {"1K": 1024, "2K": 2048}

        ar, res = TestModel._to_resolution_aspect_ratio(1280, 720)
        assert ar == "16:9"
        assert res == "1K"  # |1280-1024|=256 < |1280-2048|=768

    def test_square_aspect_ratio(self):
        """1024x1024 should map to 1:1."""

        class TestModel(VisualFalModel):
            use_resolution_aspect_ratio = True
            aspect_ratios = ["16:9", "4:3", "1:1", "9:16"]
            resolutions = {"1K": 1024}

        ar, res = TestModel._to_resolution_aspect_ratio(1024, 1024)
        assert ar == "1:1"
        assert res == "1K"

    def test_portrait_aspect_ratio(self):
        """720x1280 should map to 9:16."""

        class TestModel(VisualFalModel):
            use_resolution_aspect_ratio = True
            aspect_ratios = ["16:9", "4:3", "1:1", "9:16"]
            resolutions = {"1K": 1024, "2K": 2048}

        ar, res = TestModel._to_resolution_aspect_ratio(720, 1280)
        assert ar == "9:16"
        assert res == "1K"


class TestModelParameters:
    """Test model parameter building."""

    def test_size_parameter_nested(self):
        """Models with size_parameter should nest width/height."""

        class TestModel(VisualFalModel):
            size_parameter = "video_size"

        params = TestModel._get_size_parameters(1280, 720)
        assert params == {"video_size": {"width": 1280, "height": 720}}

    def test_size_parameter_flat(self):
        """Models without size_parameter should use flat width/height."""

        class TestModel(VisualFalModel):
            size_parameter = None

        params = TestModel._get_size_parameters(1280, 720)
        assert params == {"width": 1280, "height": 720}

    def test_modulo_rounding(self):
        """Models with modulo should round dimensions."""

        class TestModel(VisualFalModel):
            modulo = 64

        params = TestModel._get_size_parameters(1000, 500)
        assert params == {"width": 960, "height": 448}  # Rounded to 64


class TestResolutionCeilingPreference:
    """Resolution selection should prefer the smallest tier ≥ target."""

    def test_1080p_picks_2k_over_1k(self):
        """1920x1080 on {1K, 2K}: 1K upscales a lot, 2K downscales slightly — pick 2K."""

        class TestModel(VisualFalModel):
            use_resolution_aspect_ratio = True
            aspect_ratios = ["16:9"]
            resolutions = {"1K": 1024, "2K": 2048}

        assert TestModel._closest_resolution(1920, 1080) == "2K"

    def test_exact_1024_stays_on_1k(self):
        """1024 is an exact match — don't jump to 2K for zero benefit."""

        class TestModel(VisualFalModel):
            resolutions = {"1K": 1024, "2K": 2048}

        assert TestModel._closest_resolution(1024, 1024) == "1K"

    def test_small_overshoot_within_tolerance_stays(self):
        """1025 is 0.1% over 1024 — within tolerance, keep 1K."""

        class TestModel(VisualFalModel):
            resolutions = {"1K": 1024, "2K": 2048}

        assert TestModel._closest_resolution(1025, 1025) == "1K"

    def test_target_exceeds_all_tiers_falls_back_to_largest(self):
        """Wan 2.2 maxes at 720p; 1920x1080 must fall back to 720p."""

        class TestModel(VisualFalModel):
            use_resolution_aspect_ratio = True
            aspect_ratios = ["16:9"]
            resolutions = {"480p": 480, "580p": 580, "720p": 720}

        assert TestModel._closest_resolution(1920, 1080) == "720p"

    def test_shortest_side_drives_selection(self):
        """Portrait 720x1280 should use the 720 short-side, not 1280."""

        class TestModel(VisualFalModel):
            resolutions = {"1K": 1024, "2K": 2048}

        # shortest=720; threshold=684; both eligible; pick smallest=1K.
        assert TestModel._closest_resolution(720, 1280) == "1K"


class TestDescribeOutputSize:
    """describe_output_size should match what the API actually receives."""

    def test_aspect_ratio_and_resolution(self):
        """Models with both should report 'resolution aspect_ratio'."""

        class Wan(VisualFalModel):
            use_resolution_aspect_ratio = True
            aspect_ratios = ["16:9", "9:16"]
            resolutions = {"480p": 480, "720p": 720}

        assert Wan.describe_output_size(1920, 1080) == "720p 16:9"

    def test_modulo_rounded(self):
        """Modulo models should report the rounded dims, not the input."""

        class Flux(VisualFalModel):
            modulo = 64

        assert Flux.describe_output_size(1000, 500) == "960x448"

    def test_passthrough_when_no_mapping(self):
        """Without modulo, aspect, or resolution mapping, return WxH verbatim."""

        class Raw(VisualFalModel):
            pass

        assert Raw.describe_output_size(1280, 720) == "1280x720"


class TestGPTImage15SizeMapping:
    """GPT Image 1.5 accepts a fixed enum — pick the closest aspect ratio."""

    # Inlined copy of the production mapping — keep in sync with
    # models/image_generation/sketch_guided.py:GPTImage15EditModel.
    class _Model:
        _SIZE_CHOICES = [
            ("1024x1024", 1024, 1024),
            ("1536x1024", 1536, 1024),
            ("1024x1536", 1024, 1536),
        ]

        @classmethod
        def choose(cls, width: int, height: int) -> str:
            target = width / height if height else 1.0
            label, _, _ = min(
                cls._SIZE_CHOICES,
                key=lambda item: abs(target - item[1] / item[2]),
            )
            return label

    def test_landscape_maps_to_3_2(self):
        assert self._Model.choose(1920, 1080) == "1536x1024"

    def test_portrait_maps_to_2_3(self):
        assert self._Model.choose(1080, 1920) == "1024x1536"

    def test_square_maps_to_1_1(self):
        assert self._Model.choose(1024, 1024) == "1024x1024"

    def test_small_square_still_1_1(self):
        assert self._Model.choose(512, 512) == "1024x1024"

    def test_near_square_landscape_prefers_square(self):
        """5:4 is closer to 1:1 than 3:2 — don't over-stretch."""
        assert self._Model.choose(1280, 1024) == "1024x1024"


class TestMeshGenerationUIParameterMap:
    """The MeshGenerationModel forwards declared UI params and clamps
    ``face_count`` to each endpoint's schema range. Runs here (bpy-free)
    against a local mirror of the base-class logic from
    ``models/mesh_generation/base.py`` — keep them in sync when behavior
    changes."""

    class _MeshModel:
        """Minimal mirror of the MeshGenerationModel forwarding rules."""

        ui_parameter_map: ClassVar[dict[str, str]] = {}
        face_count_range: ClassVar[tuple[int, int] | None] = None

        @classmethod
        def parameters(cls, **kwargs: Any) -> dict[str, Any]:
            params: dict[str, Any] = {}
            for ui_name, api_name in cls.ui_parameter_map.items():
                if ui_name not in kwargs:
                    continue
                value = kwargs[ui_name]
                if value is None:
                    continue
                if isinstance(value, str):
                    if not value.strip() or value == "NONE":
                        continue
                if ui_name == "face_count" and cls.face_count_range:
                    lo, hi = cls.face_count_range
                    value = max(lo, min(hi, int(value)))
                params[api_name] = value
            return params

    def _make(self, ui_map, face_range=None):
        M = type("M", (self._MeshModel,), {})
        M.ui_parameter_map = ui_map
        M.face_count_range = face_range
        return M

    def test_declared_ui_param_is_forwarded_under_api_name(self):
        M = self._make({"face_count": "target_polycount"}, face_range=(100, 300_000))
        assert M.parameters(face_count=30_000) == {"target_polycount": 30_000}

    def test_undeclared_ui_param_is_dropped(self):
        M = self._make({"seed": "model_seed"})
        # quad is not in the map — should never reach the params dict.
        assert M.parameters(seed=42, quad=True) == {"model_seed": 42}

    def test_face_count_clamped_to_endpoint_range(self):
        # Tripo P1 caps at 20_000 even though the UI slider allows 2M.
        M = self._make({"face_count": "face_limit"}, face_range=(48, 20_000))
        assert M.parameters(face_count=1_000_000) == {"face_limit": 20_000}
        assert M.parameters(face_count=10) == {"face_limit": 48}
        assert M.parameters(face_count=5_000) == {"face_limit": 5_000}

    def test_sentinel_none_enum_is_dropped(self):
        # pose_mode="NONE" means "leave unset" — should not be forwarded.
        M = self._make({"pose_mode": "pose_mode"})
        assert M.parameters(pose_mode="NONE") == {}
        assert M.parameters(pose_mode="a-pose") == {"pose_mode": "a-pose"}

    def test_empty_string_is_dropped(self):
        # An empty negative_prompt should not send the server an empty string.
        M = self._make({"negative_prompt": "negative_prompt"})
        assert M.parameters(negative_prompt="") == {}
        assert M.parameters(negative_prompt="blurry") == {"negative_prompt": "blurry"}

    def test_none_value_is_dropped(self):
        M = self._make({"seed": "model_seed"})
        assert M.parameters(seed=None) == {}

    def test_multiple_fields_forwarded_and_renamed(self):
        # Real-world Tripo H3.1 subset.
        M = self._make(
            {
                "face_count": "face_limit",
                "seed": "model_seed",
                "quad": "quad",
                "geometry_quality": "geometry_quality",
            },
            face_range=(1_000, 2_000_000),
        )
        result = M.parameters(
            face_count=500_000,
            seed=123,
            quad=True,
            geometry_quality="detailed",
        )
        assert result == {
            "face_limit": 500_000,
            "model_seed": 123,
            "quad": True,
            "geometry_quality": "detailed",
        }


class TestMeshMixinMRO:
    """Regression test: the per-endpoint mixin (Meshy/Hunyuan/Tripo) must
    win MRO lookup over the ``MeshGenerationModel`` defaults. When the
    mixin extended ``FalModel`` directly, C3 linearization placed
    ``MeshGenerationModel`` *before* the mixin, so the mixin's populated
    ``ui_parameter_map`` / ``image_url_parameter`` were shadowed by the
    base's empty defaults — silently erasing every per-endpoint control.
    Fix: the mixin extends ``MeshGenerationModel``, which makes C3 put
    the mixin before the base.

    This mirrors the real class shape from
    ``models/mesh_generation/base.py`` — keep them in sync."""

    def _build(self, mixin_extends_base: bool):
        """Build a minimal copy of the mesh class hierarchy; the flag
        toggles whether the per-endpoint mixin extends the mesh base."""

        class FalModel:
            pass

        class MeshGenerationModel(FalModel):
            image_url_parameter: ClassVar = None
            ui_parameter_map: ClassVar[dict] = {}

        parent = MeshGenerationModel if mixin_extends_base else FalModel

        class MeshyMixin(parent):
            image_url_parameter = "image_url"
            ui_parameter_map = {"face_count": "target_polycount"}

        class ImageTo3DModel(MeshGenerationModel):
            pass

        class MeshyImageModel(ImageTo3DModel, MeshyMixin):
            endpoint = "x"

        return MeshyImageModel

    def test_mixin_extending_falmodel_is_shadowed(self):
        """Documents the bug — when the mixin extends FalModel, the
        MeshGenerationModel default shadows the mixin's value."""
        M = self._build(mixin_extends_base=False)
        assert M.image_url_parameter is None, "MRO bug surface: shadowed by base"
        assert M.ui_parameter_map == {}, "MRO bug surface: shadowed by base"

    def test_mixin_extending_mesh_base_wins(self):
        """The fix — mixin extends MeshGenerationModel so C3 puts it
        before the base in the concrete class's MRO."""
        M = self._build(mixin_extends_base=True)
        assert M.image_url_parameter == "image_url"
        assert M.ui_parameter_map == {"face_count": "target_polycount"}


if __name__ == "__main__":
    import pytest

    pytest.main([__file__, "-v"])

"""Unit tests for model parameter generation.
These tests don't require Blender — run with pytest.

Note: These tests mock the minimal VisualFalModel behavior
since the full models module requires Blender imports.
"""

import struct
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


class TestRodinV25Parameters:
    """Hyper3D Rodin v2.5 forwards plain enum/bool controls through the
    generic ``ui_parameter_map`` machinery, but three controls need
    post-processing: ``rodin_high_pack`` → ``addons``, the bbox toggle +
    dimensions → ``bbox_condition``, and ``seed`` is clamped to 0–65535.

    Runs here (bpy-free) against a local mirror of
    ``models/mesh_generation/base.py::RodinV25Model.parameters`` — keep them
    in sync when behavior changes."""

    class _Rodin:
        """Minimal mirror of MeshGenerationModel + RodinV25Model forwarding."""

        seed_range: ClassVar[tuple[int, int]] = (0, 65535)
        image_urls_parameter: ClassVar[str | None] = "image_urls"
        ui_parameter_map: ClassVar[dict[str, str]] = {
            "seed": "seed",
            "rodin_tier": "tier",
            "rodin_material": "material",
            "rodin_texture_mode": "texture_mode",
            "rodin_hd_texture": "hd_texture",
            "rodin_high_pack": "addons",
            "rodin_use_bbox": "bbox_condition",
            "rodin_bbox_width": "bbox_condition",
            "rodin_bbox_height": "bbox_condition",
            "rodin_bbox_length": "bbox_condition",
        }

        @classmethod
        def _forward(cls, **kwargs: Any) -> dict[str, Any]:
            params: dict[str, Any] = {}
            image_paths = []
            if "image_path" in kwargs:
                image_paths.append(kwargs["image_path"])
            if cls.image_urls_parameter and image_paths:
                params[cls.image_urls_parameter] = list(image_paths)
            params["prompt"] = kwargs.get("prompt", "")
            for ui_name, api_name in cls.ui_parameter_map.items():
                if ui_name not in kwargs:
                    continue
                value = kwargs[ui_name]
                if value is None:
                    continue
                if isinstance(value, str) and (not value.strip() or value == "NONE"):
                    continue
                params[api_name] = value
            return params

        @classmethod
        def parameters(cls, **kwargs: Any) -> dict[str, Any]:
            kwargs = dict(kwargs)
            high_pack = kwargs.pop("rodin_high_pack", False)
            use_bbox = kwargs.pop("rodin_use_bbox", False)
            bbox = (
                kwargs.pop("rodin_bbox_width", 0),
                kwargs.pop("rodin_bbox_height", 0),
                kwargs.pop("rodin_bbox_length", 0),
            )
            params = cls._forward(**kwargs)
            seed = params.get("seed")
            if seed is not None:
                lo, hi = cls.seed_range
                params["seed"] = max(lo, min(hi, int(seed)))
            if high_pack:
                params["addons"] = ["HighPack"]
            if use_bbox:
                params["bbox_condition"] = [int(v) for v in bbox]
            return params

    def test_high_pack_bool_becomes_addons_list(self):
        assert self._Rodin.parameters(rodin_high_pack=True)["addons"] == ["HighPack"]
        assert "addons" not in self._Rodin.parameters(rodin_high_pack=False)

    def test_bbox_assembled_only_when_enabled(self):
        off = self._Rodin.parameters(
            rodin_use_bbox=False,
            rodin_bbox_width=10,
            rodin_bbox_height=20,
            rodin_bbox_length=30,
        )
        assert "bbox_condition" not in off
        on = self._Rodin.parameters(
            rodin_use_bbox=True,
            rodin_bbox_width=10,
            rodin_bbox_height=20,
            rodin_bbox_length=30,
        )
        assert on["bbox_condition"] == [10, 20, 30]

    def test_seed_clamped_to_api_range(self):
        assert self._Rodin.parameters(seed=999_999)["seed"] == 65535
        assert self._Rodin.parameters(seed=42)["seed"] == 42

    def test_texture_mode_auto_sentinel_dropped(self):
        assert "texture_mode" not in self._Rodin.parameters(rodin_texture_mode="NONE")
        assert (
            self._Rodin.parameters(rodin_texture_mode="high")["texture_mode"] == "high"
        )

    def test_material_none_string_is_preserved(self):
        # The API's "None" material (geometry only) must survive — it is a
        # real value, distinct from the "NONE" auto/unset sentinel.
        assert self._Rodin.parameters(rodin_material="None")["material"] == "None"


class TestTripoSplatParameters:
    """TripoSplat is image-only and always requests PLY output. It declares no
    prompt field, and forwards num_gaussians / num_inference_steps /
    guidance_scale / seed through the generic ``ui_parameter_map`` machinery.

    Runs here (bpy-free) against a local mirror of
    ``models/mesh_generation/base.py::TripoSplatModel`` — keep them in sync."""

    class _TripoSplat:
        """Minimal mirror of MeshGenerationModel + TripoSplatModel forwarding."""

        image_url_parameter: ClassVar[str | None] = "image_url"
        # No prompt field on this endpoint.
        prompt_parameter: ClassVar[str | None] = None
        static_parameters: ClassVar[dict[str, Any]] = {"output_format": "ply"}
        ui_parameter_map: ClassVar[dict[str, str]] = {
            "num_gaussians": "num_gaussians",
            "num_inference_steps": "num_inference_steps",
            "guidance_scale": "guidance_scale",
            "seed": "seed",
        }

        @classmethod
        def parameters(cls, **kwargs: Any) -> dict[str, Any]:
            # static defaults first (copy so we don't mutate the class dict).
            params: dict[str, Any] = dict(cls.static_parameters)

            image_urls: list[str] = []
            if "image_url" in kwargs:
                image_urls.append(kwargs["image_url"])
            if "image_path" in kwargs:
                # Real code data-URI-encodes the path; the value is opaque here.
                image_urls.append(kwargs["image_path"])
            if cls.image_url_parameter and image_urls:
                params[cls.image_url_parameter] = image_urls[0]

            if cls.prompt_parameter:
                params[cls.prompt_parameter] = kwargs.get("prompt", "")

            for ui_name, api_name in cls.ui_parameter_map.items():
                if ui_name not in kwargs:
                    continue
                value = kwargs[ui_name]
                if value is None:
                    continue
                if isinstance(value, str) and (not value.strip() or value == "NONE"):
                    continue
                params[api_name] = value
            return params

    def test_image_url_and_static_output_format(self):
        params = self._TripoSplat.parameters(image_url="https://x/cat.png")
        assert params["image_url"] == "https://x/cat.png"
        assert params["output_format"] == "ply"

    def test_no_prompt_emitted(self):
        # The endpoint takes no prompt — even when the operator passes one,
        # nothing should be forwarded.
        params = self._TripoSplat.parameters(
            image_url="https://x/cat.png", prompt="a cat"
        )
        assert "prompt" not in params

    def test_all_knobs_forwarded(self):
        params = self._TripoSplat.parameters(
            image_url="https://x/cat.png",
            num_gaussians=131072,
            num_inference_steps=30,
            guidance_scale=5.5,
            seed=99,
        )
        assert params == {
            "output_format": "ply",
            "image_url": "https://x/cat.png",
            "num_gaussians": 131072,
            "num_inference_steps": 30,
            "guidance_scale": 5.5,
            "seed": 99,
        }

    def test_unset_knobs_drop_to_defaults(self):
        # None / undeclared values must not reach the params dict.
        params = self._TripoSplat.parameters(
            image_url="https://x/cat.png",
            seed=None,
            quad=True,  # not in the map
        )
        assert "seed" not in params
        assert "quad" not in params
        assert params == {"output_format": "ply", "image_url": "https://x/cat.png"}


# ---------------------------------------------------------------------------
# Splat PLY parser tests
#
# parse_splat_ply lives in the repo's bpy-free splat.py. This test file is
# copied to /tmp before pytest runs, so locate splat.py via FAL_REPO_DIR (set
# by run_tests.sh) or by walking up from the current working directory, then
# import it directly.
# ---------------------------------------------------------------------------


def _load_splat_module():
    """Import the repo's ``splat.py`` as a standalone module (no bpy needed)."""
    import importlib.util
    import os

    candidates: list[str] = []
    repo = os.environ.get("FAL_REPO_DIR")
    if repo:
        candidates.append(os.path.join(repo, "splat.py"))
    directory = os.getcwd()
    while True:
        candidates.append(os.path.join(directory, "splat.py"))
        parent = os.path.dirname(directory)
        if parent == directory:
            break
        directory = parent

    for path in candidates:
        if os.path.isfile(path):
            spec = importlib.util.spec_from_file_location("fal_splat_under_test", path)
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            return module

    raise FileNotFoundError(
        "Could not locate splat.py (set FAL_REPO_DIR or run from the repo root)"
    )


def _write_binary_3dgs_ply(path, gaussians):
    """Synthesize a tiny binary_little_endian 3DGS PLY at *path*.

    ``gaussians`` is a list of dicts with keys x, y, z, f_dc_0/1/2, opacity,
    scale_0/1/2, rot_0/1/2/3 (all floats). Property order mirrors a real INRIA
    export (including unused nx/ny/nz so the parser must skip them).
    """
    props = [
        "x", "y", "z",
        "nx", "ny", "nz",
        "f_dc_0", "f_dc_1", "f_dc_2",
        "opacity",
        "scale_0", "scale_1", "scale_2",
        "rot_0", "rot_1", "rot_2", "rot_3",
    ]
    header_lines = ["ply", "format binary_little_endian 1.0", f"element vertex {len(gaussians)}"]
    header_lines += [f"property float {name}" for name in props]
    header_lines.append("end_header")
    header = ("\n".join(header_lines) + "\n").encode("ascii")

    body = bytearray()
    for g in gaussians:
        for name in props:
            body += struct.pack("<f", float(g.get(name, 0.0)))

    with open(path, "wb") as f:
        f.write(header)
        f.write(body)


class TestSplatPlyParser:
    """parse_splat_ply decodes SH→RGB color, sigmoid opacity, exp scale, and
    normalized wxyz quaternions from a 3DGS PLY."""

    SH_C0 = 0.28209479177387814

    def _gaussians(self):
        return [
            {
                "x": 1.0, "y": 2.0, "z": 3.0,
                "nx": 0.1, "ny": 0.2, "nz": 0.3,  # unused, must be skipped
                "f_dc_0": 1.0, "f_dc_1": -1.0, "f_dc_2": 0.0,
                "opacity": 0.0,  # sigmoid(0) = 0.5
                "scale_0": 0.0, "scale_1": 1.0, "scale_2": -1.0,  # exp -> 1, e, 1/e
                "rot_0": 0.0, "rot_1": 0.0, "rot_2": 0.0, "rot_3": 2.0,  # -> (0,0,0,1)
            },
            {
                "x": -4.0, "y": -5.0, "z": -6.0,
                "nx": 0.0, "ny": 0.0, "nz": 0.0,
                "f_dc_0": 0.0, "f_dc_1": 0.0, "f_dc_2": 0.0,  # -> 0.5 grey
                "opacity": 100.0,  # sigmoid -> ~1.0
                "scale_0": 2.0, "scale_1": 2.0, "scale_2": 2.0,
                "rot_0": 1.0, "rot_1": 1.0, "rot_2": 1.0, "rot_3": 1.0,  # -> 0.5 each
            },
        ]

    def _parse(self, tmp_path):
        import numpy as np

        splat = _load_splat_module()
        ply = str(tmp_path / "tiny.ply")
        _write_binary_3dgs_ply(ply, self._gaussians())
        return splat, np, splat.parse_splat_ply(ply)

    def test_count_and_positions(self, tmp_path):
        import numpy as np

        _, _, data = self._parse(tmp_path)
        assert data["count"] == 2
        np.testing.assert_allclose(
            data["positions"],
            [[1.0, 2.0, 3.0], [-4.0, -5.0, -6.0]],
            rtol=1e-5,
        )

    def test_colors_from_sh_dc(self, tmp_path):
        import numpy as np

        _, _, data = self._parse(tmp_path)
        c0 = self.SH_C0
        expected = np.array(
            [
                [0.5 + c0 * 1.0, 0.5 + c0 * -1.0, 0.5 + c0 * 0.0],
                [0.5, 0.5, 0.5],
            ]
        )
        np.testing.assert_allclose(data["colors"], expected, rtol=1e-5, atol=1e-6)
        # All channels stay within the valid 0..1 display range.
        assert data["colors"].min() >= 0.0
        assert data["colors"].max() <= 1.0

    def test_opacity_sigmoid(self, tmp_path):
        import numpy as np

        _, _, data = self._parse(tmp_path)
        np.testing.assert_allclose(data["opacity"], [0.5, 1.0], rtol=1e-4, atol=1e-4)

    def test_scales_exp(self, tmp_path):
        import numpy as np

        _, _, data = self._parse(tmp_path)
        expected = np.exp([[0.0, 1.0, -1.0], [2.0, 2.0, 2.0]])
        np.testing.assert_allclose(data["scales"], expected, rtol=1e-5)

    def test_rotations_normalized_wxyz(self, tmp_path):
        import numpy as np

        _, _, data = self._parse(tmp_path)
        # First quat (0,0,0,2) normalizes to (0,0,0,1).
        np.testing.assert_allclose(
            data["rotations"][0], [0.0, 0.0, 0.0, 1.0], atol=1e-6
        )
        # Second quat (1,1,1,1) normalizes to 0.5 each.
        np.testing.assert_allclose(
            data["rotations"][1], [0.5, 0.5, 0.5, 0.5], atol=1e-6
        )
        # Every quaternion is unit length.
        norms = np.linalg.norm(data["rotations"], axis=-1)
        np.testing.assert_allclose(norms, [1.0, 1.0], atol=1e-6)

    def test_missing_optional_fields_use_defaults(self, tmp_path):
        import numpy as np

        splat = _load_splat_module()
        # A minimal PLY with only positions — color/opacity/scale/rot absent.
        ply = str(tmp_path / "pos_only.ply")
        header = (
            "ply\n"
            "format binary_little_endian 1.0\n"
            "element vertex 1\n"
            "property float x\n"
            "property float y\n"
            "property float z\n"
            "end_header\n"
        ).encode("ascii")
        with open(ply, "wb") as f:
            f.write(header)
            f.write(struct.pack("<fff", 7.0, 8.0, 9.0))

        data = splat.parse_splat_ply(ply)
        assert data["count"] == 1
        np.testing.assert_allclose(data["colors"], [[0.5, 0.5, 0.5]], atol=1e-6)
        np.testing.assert_allclose(data["opacity"], [1.0], atol=1e-6)
        np.testing.assert_allclose(data["scales"], [[1.0, 1.0, 1.0]], atol=1e-6)
        np.testing.assert_allclose(
            data["rotations"], [[1.0, 0.0, 0.0, 0.0]], atol=1e-6
        )

    def test_ascii_ply_round_trips(self, tmp_path):
        import numpy as np

        splat = _load_splat_module()
        ply = str(tmp_path / "ascii.ply")
        header = (
            "ply\n"
            "format ascii 1.0\n"
            "element vertex 2\n"
            "property float x\n"
            "property float y\n"
            "property float z\n"
            "property float f_dc_0\n"
            "property float f_dc_1\n"
            "property float f_dc_2\n"
            "property float opacity\n"
            "property float scale_0\n"
            "property float scale_1\n"
            "property float scale_2\n"
            "property float rot_0\n"
            "property float rot_1\n"
            "property float rot_2\n"
            "property float rot_3\n"
            "end_header\n"
        )
        rows = (
            "1 2 3 1 -1 0 0 0 1 -1 0 0 0 2\n"
            "-4 -5 -6 0 0 0 100 2 2 2 1 1 1 1\n"
        )
        with open(ply, "w") as f:
            f.write(header)
            f.write(rows)

        data = splat.parse_splat_ply(ply)
        assert data["count"] == 2
        np.testing.assert_allclose(
            data["positions"], [[1, 2, 3], [-4, -5, -6]], rtol=1e-5
        )
        np.testing.assert_allclose(data["opacity"], [0.5, 1.0], atol=1e-4)


if __name__ == "__main__":
    import pytest

    pytest.main([__file__, "-v"])

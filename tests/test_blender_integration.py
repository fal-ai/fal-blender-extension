"""
Integration tests that run inside Blender.
Run with: blender --background --python tests/test_blender_integration.py

These tests verify that operators register correctly and basic functionality works.
"""

import sys
import traceback

# Check if we're running in Blender
try:
    import bpy
except ImportError:
    print("ERROR: This test must be run inside Blender")
    print("Usage: blender --background --python tests/test_blender_integration.py")
    sys.exit(1)


def _ensure_extension_enabled():
    """Try to enable the fal.ai extension if not already loaded."""
    if hasattr(bpy.types.Scene, "fal_3d"):
        return True  # Already loaded

    from pathlib import Path

    # Get Blender's user extension path via official API
    user_extensions = Path(bpy.utils.user_resource("EXTENSIONS")) / "user_default"
    fal_path = user_extensions / "fal_ai"

    if fal_path.exists() and str(user_extensions) not in sys.path:
        sys.path.insert(0, str(user_extensions))
        print(f"Added extension path: {user_extensions}")

    # Try addon_utils — this calls register() automatically
    try:
        import addon_utils

        addon_utils.enable("fal_ai", default_set=True)
    except Exception as e:
        print(f"addon_utils.enable failed: {e}")

    # Check if it worked
    if hasattr(bpy.types.Scene, "fal_3d"):
        print("fal.ai extension enabled")
        return True

    return False


def test_extension_registers():
    """Test that the extension registers without errors."""
    if not _ensure_extension_enabled():
        print("⚠ Skipping: extension not installed or couldn't be enabled")
        print("  Install via: Edit > Preferences > Get Extensions")
        return

    # Verify scene property groups
    assert hasattr(bpy.types.Scene, "fal_3d"), "3D scene property group not registered"
    assert hasattr(
        bpy.types.Scene, "fal_vse"
    ), "VSE scene property group not registered"
    print("✓ Extension property groups registered")


def test_operators_registered():
    """Test that operators are registered."""
    # Extension must be registered first (test_extension_registers runs first)
    if not hasattr(bpy.types.Scene, "fal_3d"):
        print("⚠ Skipping operator test (extension not loaded)")
        return

    # Check that our operators exist
    operators = [
        "FAL_OT_fal_render_operator",
        "FAL_OT_fal_video_operator",
        "FAL_OT_fal_upscale_operator",
    ]

    for op_name in operators:
        assert hasattr(bpy.types, op_name), f"Operator {op_name} not registered"
    print("✓ Operators registered")


def test_scene_resolution_reading():
    """Test that we can read scene resolution correctly."""
    scene = bpy.context.scene

    # Set known values
    scene.render.resolution_x = 1920
    scene.render.resolution_y = 1080
    scene.render.resolution_percentage = 50

    # Calculate expected
    scale = scene.render.resolution_percentage / 100.0
    expected_w = int(scene.render.resolution_x * scale)
    expected_h = int(scene.render.resolution_y * scale)

    assert expected_w == 960, f"Expected width 960, got {expected_w}"
    assert expected_h == 540, f"Expected height 540, got {expected_h}"
    print("✓ Scene resolution reading works")


def test_render_result_has_data_attribute():
    """Test that Image.has_data exists (Blender 5 compatibility)."""
    # Create a test image
    img = bpy.data.images.new("test_image", width=64, height=64)

    # Check has_data attribute exists
    assert hasattr(img, "has_data"), "Image.has_data attribute not found"

    # A new image should have data
    assert img.has_data, "New image should have data"

    # Cleanup
    bpy.data.images.remove(img)
    print("✓ Image.has_data attribute works")


def test_media_type_for_video_output():
    """Test Blender 5 video output settings."""
    scene = bpy.context.scene

    # Check if media_type exists (Blender 5+)
    if hasattr(scene.render.image_settings, "media_type"):
        scene.render.image_settings.media_type = "VIDEO"
        assert scene.render.image_settings.media_type == "VIDEO"
        print("✓ Blender 5 media_type works")
    else:
        # Blender 4.x fallback
        scene.render.image_settings.file_format = "FFMPEG"
        assert scene.render.image_settings.file_format == "FFMPEG"
        print("✓ Blender 4 FFMPEG file_format works")


def test_video_operators_opt_into_confirm():
    """FalVideoOperator always confirms; FalRenderOperator only for VIDEO."""
    if not hasattr(bpy.types.Scene, "fal_3d"):
        print("⚠ Skipping confirm opt-in test (extension not loaded)")
        return

    from fal_ai.controllers.render.operator import FalRenderOperator
    from fal_ai.controllers.video.operator import FalVideoOperator

    ctx = bpy.context
    v_props = ctx.scene.falvideocontroller_props
    r_props = ctx.scene.falrendercontroller_props

    v_props.mode = "TEXT"
    assert FalVideoOperator.needs_confirm(ctx, v_props) is True
    v_props.mode = "IMAGE"
    assert FalVideoOperator.needs_confirm(ctx, v_props) is True

    r_props.render_type = "VIDEO"
    assert FalRenderOperator.needs_confirm(ctx, r_props) is True
    r_props.render_type = "IMAGE"
    assert FalRenderOperator.needs_confirm(ctx, r_props) is False

    print("✓ Video operators opt into confirm; image renders skip it")


def test_confirm_message_has_model_and_size():
    """The confirm body should name the model and the request size."""
    if not hasattr(bpy.types.Scene, "fal_3d"):
        print("⚠ Skipping confirm message test (extension not loaded)")
        return

    from fal_ai.controllers.video.operator import FalVideoOperator
    from fal_ai.models import TextToVideoModel

    ctx = bpy.context
    props = ctx.scene.falvideocontroller_props
    props.mode = "TEXT"
    props.prompt = "a cat surfing"
    props.use_scene_duration = False
    props.duration = 7
    props.use_scene_resolution = False
    props.width = 1280
    props.height = 720

    catalog = TextToVideoModel.catalog()
    first_key = next(iter(catalog.keys()))
    props.text_endpoint = first_key

    title = FalVideoOperator.confirm_title(ctx, props)
    message = FalVideoOperator.confirm_message(ctx, props)
    button = FalVideoOperator.confirm_button(ctx, props)

    model = catalog[first_key]
    expected_size = model.describe_output_size(1280, 720)

    assert "text-to-video" in title.lower(), f"Unexpected title: {title}"
    assert "7s" in message, f"Duration missing from message: {message}"
    assert (
        expected_size in message
    ), f"Effective size '{expected_size}' missing from message: {message}"
    # When the model clamps/reshapes, the message should also show the raw request.
    if expected_size != "1280x720":
        assert (
            "1280x720" in message
        ), f"Expected requested-size disclosure for clamp: {message}"
    assert model.display_name in message, f"Model name missing from message: {message}"
    assert button == "Generate"

    props.mode = "IMAGE"
    assert "image-to-video" in FalVideoOperator.confirm_title(ctx, props).lower()

    print("✓ Confirm message includes model, duration, and effective dimensions")


def test_invoke_shows_confirm_for_video_and_skips_for_image():
    """Monkey-patch invoke_confirm, verify it fires for video and not for image render."""
    if not hasattr(bpy.types.Scene, "fal_3d"):
        print("⚠ Skipping invoke_confirm routing test (extension not loaded)")
        return

    captured: list[dict] = []
    original = bpy.types.WindowManager.invoke_confirm

    def fake_invoke_confirm(self, operator, event, **kwargs):
        captured.append({"operator": operator.bl_idname, **kwargs})
        return {"RUNNING_MODAL"}

    try:
        bpy.types.WindowManager.invoke_confirm = fake_invoke_confirm
    except (AttributeError, TypeError) as e:
        print(f"⚠ Skipping: cannot monkey-patch invoke_confirm ({e})")
        return

    try:
        # Video (T2V) — should trigger confirm.
        v_props = bpy.context.scene.falvideocontroller_props
        v_props.mode = "TEXT"
        v_props.prompt = "test prompt"
        bpy.ops.fal.fal_video_operator("INVOKE_DEFAULT")

        video_calls = [c for c in captured if c["operator"] == "fal.fal_video_operator"]
        assert (
            len(video_calls) == 1
        ), f"Expected 1 confirm for video, got {len(video_calls)}: {captured}"
        kwargs = video_calls[0]
        assert "title" in kwargs and kwargs["title"], "confirm title missing"
        assert "message" in kwargs and kwargs["message"], "confirm message missing"
        assert kwargs.get("confirm_text") == "Generate"

        # Image render — confirm must NOT fire.
        r_props = bpy.context.scene.falrendercontroller_props
        r_props.render_type = "IMAGE"
        r_props.mode = "DEPTH"
        r_props.prompt = "test prompt"

        if bpy.context.scene.camera is None:
            cam_data = bpy.data.cameras.new("TestCamera")
            cam = bpy.data.objects.new("TestCamera", cam_data)
            bpy.context.scene.collection.objects.link(cam)
            bpy.context.scene.camera = cam

        before = len(captured)
        # Image render actually starts a real render — we only care that the
        # dialog does NOT fire. Wrap in try to swallow downstream errors.
        try:
            bpy.ops.fal.fal_render_operator("INVOKE_DEFAULT")
        except Exception:
            pass
        image_calls = [
            c for c in captured[before:] if c["operator"] == "fal.fal_render_operator"
        ]
        assert (
            len(image_calls) == 0
        ), f"Image render should not confirm, got: {image_calls}"

        print("✓ Confirm fires for video, skipped for image render")
    finally:
        bpy.types.WindowManager.invoke_confirm = original
        # Cancel any render that may have started.
        try:
            from fal_ai.controllers.render.operator import FalRenderOperator

            FalRenderOperator._rendering = False
        except Exception:
            pass


def test_panel_output_size_hint():
    """Panel should show a hint when the model reshapes the requested size."""
    if not hasattr(bpy.types.Scene, "fal_3d"):
        print("⚠ Skipping output-size hint test (extension not loaded)")
        return

    from fal_ai.controllers.render.controller import FalRenderController

    ctx = bpy.context
    props = ctx.scene.falrendercontroller_props

    # Image mode + Sketch + Nano Banana (only has 1K tier) + 1920x1080 should
    # trip the hint: the request is 1920x1080 but NB1 is locked to 1K.
    props.render_type = "IMAGE"
    props.mode = "SKETCH"
    props.sketch_endpoint = "NanoBanana"
    props.use_scene_resolution = False
    props.width = 1920
    props.height = 1080

    panel = FalRenderController.panel_3d
    hint = panel.output_size_hint(ctx, props)
    assert hint is not None, "Expected hint when NB1 clamps 1920x1080 to 1K"
    assert "Will generate at" in hint
    assert "1K" in hint

    # Exact-match size — no hint, no noise.
    props.width = 1024
    props.height = 1024
    exact_hint = panel.output_size_hint(ctx, props)
    assert (
        exact_hint is None
    ), f"Expected no hint for exact size match, got: {exact_hint}"

    print("✓ Output-size hint fires only when model reshapes the request")


def test_has_usable_compositor_detects_empty_tree():
    """has_usable_compositor should be False for a fresh 5.x compositor tree.

    Regression guard for the "No Group Output or File Output nodes in scene"
    error on Blender 5.2 fresh scenes — the tree exists with no output node.
    """
    if not hasattr(bpy.types.Scene, "fal_3d"):
        print("⚠ Skipping has_usable_compositor test (extension not loaded)")
        return

    from fal_ai.utils import (
        create_compositor_output_node,
        ensure_compositor_enabled,
        has_usable_compositor,
    )

    scene = bpy.context.scene
    tree = ensure_compositor_enabled(scene)

    for node in list(tree.nodes):
        tree.nodes.remove(node)

    assert not has_usable_compositor(
        scene
    ), "Empty compositor tree should report as unusable"

    create_compositor_output_node(tree)
    assert has_usable_compositor(scene), "Tree with output node should report as usable"

    for node in list(tree.nodes):
        tree.nodes.remove(node)

    print("✓ has_usable_compositor distinguishes empty vs wired trees")


def test_refine_setup_disables_empty_compositor():
    """_setup_refine should flip off use_compositing when the tree is empty.

    Fresh 5.x scenes default ``use_compositing=True`` with no output node,
    which makes ``bpy.ops.render.render()`` explode. Operators that don't
    build their own compositor path must guard against it.
    """
    if not hasattr(bpy.types.Scene, "fal_3d"):
        print("⚠ Skipping refine compositor guard test (extension not loaded)")
        return

    from fal_ai.controllers.render.operator import FalRenderOperator
    from fal_ai.utils import ensure_compositor_enabled

    scene = bpy.context.scene
    tree = ensure_compositor_enabled(scene)
    for node in list(tree.nodes):
        tree.nodes.remove(node)

    original_use_compositing = scene.render.use_compositing
    original_res_x = scene.render.resolution_x
    original_res_y = scene.render.resolution_y
    original_res_pct = scene.render.resolution_percentage
    scene.render.use_compositing = True

    op = FalRenderOperator.__new__(FalRenderOperator)
    op._saved = {}
    op._render_w = 512
    op._render_h = 512

    try:
        op._setup_refine(bpy.context)
        assert (
            not scene.render.use_compositing
        ), "Empty compositor should be disabled during refine setup"
        assert (
            op._saved.get("use_compositing") is True
        ), "Original use_compositing should be stashed for restore"
    finally:
        scene.render.resolution_x = original_res_x
        scene.render.resolution_y = original_res_y
        scene.render.resolution_percentage = original_res_pct
        scene.render.use_compositing = original_use_compositing

    print("✓ _setup_refine disables empty compositor and saves prior state")


def test_fit_movie_strip_reports_readiness():
    """_fit_movie_strip_to_target returns False until native dims are known.

    Endpoints often round output dimensions (e.g. requesting 1920x1080 and
    getting 1344x768 back), and Blender doesn't decode the video header
    synchronously — ``elements[0].orig_width`` stays 0 for a beat. The fit
    function must report that clearly so the caller can schedule a retry.
    """
    if not hasattr(bpy.types.Scene, "fal_3d"):
        print("⚠ Skipping _fit_movie_strip_to_target test (extension not loaded)")
        return

    from fal_ai.importers import _fit_movie_strip_to_target

    class _Element:
        def __init__(self, w: int, h: int):
            self.orig_width = w
            self.orig_height = h

    class _Transform:
        def __init__(self):
            self.scale_x = 1.0
            self.scale_y = 1.0

    class _Strip:
        def __init__(self, w: int, h: int):
            self.elements = [_Element(w, h)]
            self.transform = _Transform()

    scene = bpy.context.scene

    # Native dims not ready yet → caller should schedule a retry.
    pending = _Strip(0, 0)
    assert _fit_movie_strip_to_target(scene, pending, 1920, 1080) is False

    # Native dims known → scale uniformly to fit target, preserve aspect.
    ready = _Strip(1344, 768)
    assert _fit_movie_strip_to_target(scene, ready, 1920, 1080) is True
    expected_scale = min(1920 / 1344, 1080 / 768)
    assert abs(ready.transform.scale_x - expected_scale) < 1e-6
    assert (
        ready.transform.scale_x == ready.transform.scale_y
    ), "Uniform scale should apply the same factor to x and y"

    print("✓ _fit_movie_strip_to_target signals readiness for deferred retry")


def test_vse_importer_uses_explicit_scene():
    """add_audio_to_vse should attach to the scene kwarg, not bpy.context.scene.

    Regression guard: in 5.2 fresh scenes, the Video Editing workspace shows
    a "New" button until the VSE area redraws. By threading the originating
    scene through callbacks (instead of trusting bpy.context.scene at timer
    time), the strip lands on the right scene even if focus has drifted.
    """
    if not hasattr(bpy.types.Scene, "fal_3d"):
        print("⚠ Skipping VSE importer test (extension not loaded)")
        return

    import os
    import tempfile
    import wave

    from fal_ai.importers import _refresh_vse_for_scene, add_audio_to_vse

    origin_scene = bpy.context.scene
    origin_name = origin_scene.name
    bpy.ops.scene.new(type="NEW")
    other_scene = bpy.context.scene
    # bpy.context.scene is now `other_scene` — origin_scene is intentionally
    # NOT the active scene, so we can prove we ignore context.scene.

    # Write a tiny silent WAV — new_sound needs a real audio file.
    tmp = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
    tmp.close()
    try:
        with wave.open(tmp.name, "wb") as wav:
            wav.setnchannels(1)
            wav.setsampwidth(2)
            wav.setframerate(44100)
            wav.writeframes(b"\x00\x00" * 4410)

        assert (
            origin_scene.sequence_editor is None
        ), "Origin scene should start without a sequence_editor"
        strip = add_audio_to_vse(tmp.name, name="fal_test", scene=origin_scene)
        assert strip is not None, "Expected a strip to be created"
        assert (
            origin_scene.sequence_editor is not None
        ), "Sequence editor should be created on the explicit scene"
        assert (
            not other_scene.sequence_editor
        ), "Other scene should be untouched when scene kwarg is passed"

        # _refresh_vse_for_scene is best-effort — must not raise even when
        # no VSE areas exist (background mode).
        _refresh_vse_for_scene(origin_scene)

        print("✓ VSE importer threads scene kwarg and refresh is safe")
    finally:
        os.unlink(tmp.name)
        bpy.context.window.scene = origin_scene
        bpy.data.scenes.remove(other_scene)
        if origin_scene.sequence_editor:
            bpy.context.window.scene = origin_scene
            origin_scene.sequence_editor_clear()
        assert bpy.context.scene.name == origin_name


def test_pointer_property_for_images():
    """Test that PointerProperty works for Image selection."""
    # Create a test image
    test_img = bpy.data.images.new("test_texture", width=64, height=64)

    # Check that our property groups can hold image references
    # (This tests the texture selector fix)
    # Controller props are registered as {controllername}_props
    props_name = "falupscalecontroller_props"
    if hasattr(bpy.context.scene, props_name):
        props = getattr(bpy.context.scene, props_name)
        if hasattr(props, "texture"):
            props.texture = test_img
            assert props.texture == test_img, "PointerProperty assignment failed"
            print("✓ PointerProperty for images works")
        else:
            print("⚠ texture property not found on upscale props")
    else:
        print("⚠ Skipping PointerProperty test (extension not loaded)")

    # Cleanup
    bpy.data.images.remove(test_img)


def test_label_anchor_avoids_occluded_surfaces():
    """Regression: a label whose origin AND bbox corners are occluded must
    find a visible surface point, not snap to an image margin.

    Reproduces the sketch-render "stray wall label" bug — a back-wall plane
    was occluded by a foreground cube, the origin + all bbox corners failed
    the visibility check, and the previous margin-snap fallback planted the
    leader line on the bottom edge of the frame — visually behind the
    blocker. The fix samples mesh vertices as a final candidate source and
    removes the margin snap.
    """
    if not hasattr(bpy.types.Scene, "fal_3d"):
        print("⚠ Skipping label anchor test (extension not loaded)")
        return

    from fal_ai.controllers.render.utils import _iter_anchor_candidates, is_occluded

    scene = bpy.context.scene

    # Clean slate — start with an empty scene to keep occlusion deterministic.
    for obj in list(scene.objects):
        bpy.data.objects.remove(obj, do_unlink=True)

    cam_data = bpy.data.cameras.new("TestLabelCam")
    cam = bpy.data.objects.new("TestLabelCam", cam_data)
    scene.collection.objects.link(cam)
    scene.camera = cam
    cam.location = (0, -6, 1)
    cam.rotation_euler = (1.5708, 0, 0)  # look along +Y

    # Back wall behind the scene — its origin is directly behind the blocker.
    bpy.ops.mesh.primitive_plane_add(size=8, location=(0, 3, 1))
    wall = bpy.context.active_object
    wall.rotation_euler = (1.5708, 0, 0)  # stand upright facing the camera
    wall["fal_ai_label"] = "wall"

    # Big opaque cube directly in front of the wall's origin.
    bpy.ops.mesh.primitive_cube_add(size=2, location=(0, 0, 1))
    blocker = bpy.context.active_object

    bpy.context.view_layer.update()
    depsgraph = bpy.context.evaluated_depsgraph_get()

    width, height = 960, 540
    candidates = list(_iter_anchor_candidates(wall, depsgraph))
    assert (
        len(candidates) > 8
    ), f"Expected origin + bbox center + face centers + corners, got {len(candidates)}"

    # Origin must be occluded by the blocker (sanity check on the scene setup).
    assert is_occluded(
        scene, depsgraph, cam, wall, width, height
    ), "Test scene broken: wall origin should be occluded by blocker"

    # At least one candidate on the wall must be visible around the blocker —
    # that's the whole point of face centers + vertex sampling.
    visible_count = sum(
        1
        for pt in candidates
        if not is_occluded(scene, depsgraph, cam, wall, width, height, override_pos=pt)
    )
    assert (
        visible_count > 0
    ), "Wall should have at least one visible surface point past the blocker"

    # Now grow the blocker until the entire wall is hidden — every candidate
    # must be rejected and overlay_labels must draw nothing.
    blocker.scale = (10, 1, 10)
    bpy.context.view_layer.update()
    depsgraph = bpy.context.evaluated_depsgraph_get()

    all_occluded = all(
        is_occluded(scene, depsgraph, cam, wall, width, height, override_pos=pt)
        for pt in _iter_anchor_candidates(wall, depsgraph)
    )
    assert all_occluded, "Fully blocked wall should have no visible candidates"

    # overlay_labels against a blank canvas should leave it untouched when
    # every labeled object is fully occluded.
    import hashlib
    import os
    import tempfile

    from fal_ai.controllers.render.utils import overlay_labels
    from PIL import Image

    tmp = tempfile.NamedTemporaryFile(suffix=".png", delete=False)
    tmp.close()
    try:
        Image.new("RGB", (width, height), (255, 255, 255)).save(tmp.name)
        before = hashlib.md5(open(tmp.name, "rb").read()).hexdigest()
        overlay_labels(bpy.context, tmp.name, width, height)
        after = hashlib.md5(open(tmp.name, "rb").read()).hexdigest()
        assert before == after, "Fully occluded label should not draw onto the image"
    finally:
        os.unlink(tmp.name)

    print(
        "✓ Label anchor picker avoids occluded surfaces and skips truly hidden labels"
    )


def run_all_tests():
    """Run all tests and report results."""
    tests = [
        test_extension_registers,
        test_operators_registered,
        test_scene_resolution_reading,
        test_render_result_has_data_attribute,
        test_media_type_for_video_output,
        test_video_operators_opt_into_confirm,
        test_confirm_message_has_model_and_size,
        test_invoke_shows_confirm_for_video_and_skips_for_image,
        test_panel_output_size_hint,
        test_has_usable_compositor_detects_empty_tree,
        test_refine_setup_disables_empty_compositor,
        test_fit_movie_strip_reports_readiness,
        test_vse_importer_uses_explicit_scene,
        test_pointer_property_for_images,
        test_label_anchor_avoids_occluded_surfaces,
    ]

    passed = 0
    failed = 0

    print("\n" + "=" * 60)
    print("fal.ai Blender Extension - Integration Tests")
    print("=" * 60 + "\n")

    for test in tests:
        try:
            test()
            passed += 1
        except AssertionError as e:
            print(f"✗ {test.__name__}: {e}")
            failed += 1
        except Exception as e:
            print(f"✗ {test.__name__}: Unexpected error")
            traceback.print_exc()
            failed += 1

    print("\n" + "-" * 60)
    print(f"Results: {passed} passed, {failed} failed")
    print("-" * 60 + "\n")

    return failed == 0


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)

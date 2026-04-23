import bpy

from ...models import (
    DepthGuidedImageGenerationModel,
    DepthVideoModel,
    EdgeGuidedImageGenerationModel,
    EdgeVideoModel,
    ImageRefinementModel,
    SketchGuidedImageGenerationModel,
)
from ..advanced_params import with_advanced_params


@with_advanced_params
class FalRenderPropertyGroup(bpy.types.PropertyGroup):
    """Property group for render settings."""

    # ── Top-level Type ───────────────────────────────────────────────────
    render_type: bpy.props.EnumProperty(
        name="Type",
        items=[
            ("IMAGE", "Image", "Generate a single image from scene data"),
            ("VIDEO", "Video", "Generate video from rendered animation"),
        ],
        default="IMAGE",
    )

    # ── Common ──────────────────────────────────────────────────────────
    prompt: bpy.props.StringProperty(
        name="Prompt",
        description="Describe what to generate from the rendered input",
        default="",
    )

    enable_prompt_expansion: bpy.props.BoolProperty(
        name="Prompt Expansion",
        description="Let the AI model expand and enhance your prompt for better results",
        default=True,
    )

    use_scene_resolution: bpy.props.BoolProperty(
        name="Use Scene Resolution",
        description="Read dimensions from scene render settings (Output Properties)",
        default=True,
    )

    width: bpy.props.IntProperty(
        name="W",
        description="Output width in pixels (only when 'Use Scene Resolution' is off)",
        default=1024,
        min=64,
        max=4096,
        step=16,
    )

    height: bpy.props.IntProperty(
        name="H",
        description="Output height in pixels (only when 'Use Scene Resolution' is off)",
        default=1024,
        min=64,
        max=4096,
        step=16,
    )

    seed: bpy.props.IntProperty(
        name="Seed",
        description="Random seed (-1 for random)",
        default=-1,
        min=-1,
        max=2147483647,
    )

    # ── Image Mode ──────────────────────────────────────────────────────
    mode: bpy.props.EnumProperty(
        name="Mode",
        items=[
            (
                "DEPTH",
                "Depth",
                "Render depth pass and generate image via depth ControlNet",
            ),
            ("SKETCH", "Sketch", "Render scene and reimagine via image generation"),
            ("REFINE", "Refine", "Render normally then refine via image-to-image AI"),
            (
                "EDGE",
                "Edge",
                "Render normally then detect edges for edge-conditioned generation",
            ),
        ],
        default="DEPTH",
    )

    # ── Video Mode ──────────────────────────────────────────────────────
    video_mode: bpy.props.EnumProperty(
        name="Video Mode",
        items=[
            ("DEPTH", "Depth", "Render depth animation for depth-conditioned video"),
            (
                "EDGE",
                "Edge",
                "Render animation then detect edges for edge-conditioned video",
            ),
        ],
        default="DEPTH",
    )

    # ── Depth Image Endpoint ────────────────────────────────────────────
    depth_endpoint: bpy.props.EnumProperty(
        name="Depth Endpoint",
        items=DepthGuidedImageGenerationModel.enumerate()
        or [("NONE", "No Models Available", "")],
        description="Endpoint for depth-controlled generation",
    )

    # ── Edge Image Endpoint ─────────────────────────────────────────────
    edge_endpoint: bpy.props.EnumProperty(
        name="Edge Endpoint",
        items=EdgeGuidedImageGenerationModel.enumerate()
        or [("NONE", "No Models Available", "")],
        description="Endpoint for edge-controlled generation",
    )

    # ── Sketch Mode ─────────────────────────────────────────────────────
    sketch_endpoint: bpy.props.EnumProperty(
        name="Sketch Endpoint",
        items=SketchGuidedImageGenerationModel.enumerate()
        or [("NONE", "No Models Available", "")],
        description="Endpoint for sketch reimagining",
    )

    sketch_system_prompt: bpy.props.StringProperty(
        name="System Prompt",
        description="Instructions for how the AI should interpret the sketch (Sketch mode only)",
        default=(
            "Render a photorealistic image that conforms to the layout presented. "
            "If labels are present on the image, follow those instructions to inform "
            "what should fill that space. Do not include the outlines or labels in "
            "your final image."
        ),
    )

    enable_labels: bpy.props.BoolProperty(
        name="Enable Labels",
        description="Overlay text labels on the sketch to guide generation",
        default=False,
    )

    auto_label: bpy.props.BoolProperty(
        name="Auto-label from Names",
        description="Use Blender object names as labels (no custom property needed). "
        "Objects with 'fal_ai_label' custom property override their name",
        default=True,
    )

    # ── Refine Mode ─────────────────────────────────────────────────────
    refine_endpoint: bpy.props.EnumProperty(
        name="Refine Endpoint",
        items=ImageRefinementModel.enumerate() or [("NONE", "No Models Available", "")],
        description="Endpoint for image-to-image refinement",
        default="FLUX2Klein9BImageRefinementModel",
    )

    refine_strength: bpy.props.FloatProperty(
        name="Strength",
        description="How much AI changes the render (0 = no change, 1 = full reimagine)",
        default=0.35,
        min=0.0,
        max=1.0,
        step=5,
        precision=2,
    )

    refine_system_prompt: bpy.props.StringProperty(
        name="System Prompt",
        description="Instructions for how the AI should refine the render (Refine mode only)",
        default=(
            "You are presented with a 3D-rendered image. Recreate this image in a "
            "photorealistic manner, being sure to represent the original artistic "
            "intent, only using a photorealistic style. Adjust lighting to be more "
            "realistic while adding details and texture where appropriate."
        ),
    )

    # ── Video: Depth Endpoint ───────────────────────────────────────────
    depth_video_endpoint: bpy.props.EnumProperty(
        name="Depth Endpoint",
        items=DepthVideoModel.enumerate() or [("NONE", "No Models Available", "")],
        description="Endpoint for depth-conditioned video",
    )

    # ── Video: Edge Endpoint ────────────────────────────────────────────
    edge_video_endpoint: bpy.props.EnumProperty(
        name="Edge Endpoint",
        items=EdgeVideoModel.enumerate() or [("NONE", "No Models Available", "")],
        description="Endpoint for edge-conditioned video",
    )

    edge_parallel_threads: bpy.props.IntProperty(
        name="Parallel Threads",
        description="Number of threads for Canny edge detection (0 = auto based on CPU cores)",
        default=0,
        min=0,
        max=32,
    )

    # ── Video Duration & First Frame ────────────────────────────────────
    use_scene_duration: bpy.props.BoolProperty(
        name="Use Scene Duration",
        description="Calculate duration from scene frame range and FPS",
        default=True,
    )

    duration: bpy.props.EnumProperty(
        name="Duration",
        items=[
            ("5", "5 seconds", ""),
            ("10", "10 seconds", ""),
        ],
        default="5",
    )

    video_use_first_frame: bpy.props.BoolProperty(
        name="Use First Frame Image",
        description="Provide a reference image as the first frame",
        default=False,
    )

    video_image_source: bpy.props.EnumProperty(
        name="First Frame Source",
        items=[
            ("FILE", "File", "Load image from disk"),
            ("RENDER", "Render Result", "Use the current render result"),
            ("TEXTURE", "Blender Texture", "Use an existing Blender image"),
        ],
        default="RENDER",
    )

    video_image_path: bpy.props.StringProperty(
        name="First Frame",
        description="Path to the first frame image",
        subtype="FILE_PATH",
        default="",
    )

    video_texture: bpy.props.PointerProperty(
        name="First Frame Texture",
        description="Blender image to use as first frame",
        type=bpy.types.Image,
    )

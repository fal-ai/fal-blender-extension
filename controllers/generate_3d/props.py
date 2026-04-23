import bpy

from ...models import ImageTo3DModel, TextTo3DModel
from ..advanced_params import with_advanced_params


@with_advanced_params
class FalGenerate3DPropertyGroup(bpy.types.PropertyGroup):
    """Properties for text-to-3D and image-to-3D generation."""

    mode: bpy.props.EnumProperty(
        name="Mode",
        items=[
            ("TEXT", "Text-to-3D", "Generate 3D model from text prompt"),
            ("IMAGE", "Image-to-3D", "Generate 3D model from an image"),
        ],
        default="TEXT",
    )

    text_endpoint: bpy.props.EnumProperty(
        name="Endpoint",
        items=TextTo3DModel.enumerate() or [("NONE", "No Models Available", "")],
        description="Which model to use for text-to-3D",
    )

    image_endpoint: bpy.props.EnumProperty(
        name="Endpoint",
        items=ImageTo3DModel.enumerate() or [("NONE", "No Models Available", "")],
        description="Which model to use for image-to-3D",
    )

    prompt: bpy.props.StringProperty(
        name="Prompt",
        description="Describe the 3D model you want to generate",
        default="",
    )

    image_source: bpy.props.EnumProperty(
        name="Image Source",
        items=[
            ("FILE", "File", "Load image from disk"),
            ("RENDER", "Render Result", "Use the current render result"),
        ],
        default="FILE",
    )

    image_path: bpy.props.StringProperty(
        name="Image",
        description="Path to the source image",
        subtype="FILE_PATH",
        default="",
    )

    generate_materials: bpy.props.BoolProperty(
        name="Generate Materials",
        description="Generate materials for the 3D model",
        default=True,
    )

    # ── Endpoint-specific controls ────────────────────────────────────────
    # These are declared once on the PropertyGroup and conditionally shown
    # based on the selected endpoint's ``ui_parameter_map``. Only values for
    # fields the endpoint declares are forwarded — everything else is
    # silently dropped on submit.

    # Shared: polygon budget. The UI range is the union of every endpoint's
    # range; the model clamps per-endpoint at submit time.
    face_count: bpy.props.IntProperty(
        name="Face Count",
        description=(
            "Target polygon budget. Clamped to the selected endpoint's "
            "valid range at submit time"
        ),
        default=30000,
        min=48,
        max=2_000_000,
    )

    # Shared: seed. -1 = leave unset (server picks randomly).
    seed: bpy.props.IntProperty(
        name="Seed",
        description="Random seed for reproducibility (-1 = random)",
        default=-1,
        min=-1,
        max=2_147_483_647,
    )

    # Tripo H3.1 only: separate seed for texture synthesis.
    texture_seed: bpy.props.IntProperty(
        name="Texture Seed",
        description="Seed for texture synthesis (-1 = random)",
        default=-1,
        min=-1,
        max=2_147_483_647,
    )

    # Meshy-only: preview vs full-texture mode.
    meshy_mode: bpy.props.EnumProperty(
        name="Meshy Mode",
        description="Meshy pipeline stage",
        items=[
            ("full", "Full (textured)", "Generate geometry and textures"),
            ("preview", "Preview (geometry only)", "Untextured geometry"),
        ],
        default="full",
    )

    # Meshy-only: art style.
    art_style: bpy.props.EnumProperty(
        name="Art Style",
        description="Art style preset",
        items=[
            ("realistic", "Realistic", "Realistic rendering"),
            ("sculpture", "Sculpture", "Sculpture style"),
        ],
        default="realistic",
    )

    # Meshy-only: symmetry hint.
    symmetry_mode: bpy.props.EnumProperty(
        name="Symmetry",
        description="Enforce left/right symmetry",
        items=[
            ("auto", "Auto", "Detect from input"),
            ("on", "On", "Force symmetry"),
            ("off", "Off", "Disable symmetry"),
        ],
        default="auto",
    )

    # Meshy-only: character pose hint. 'NONE' sentinel is dropped at submit.
    pose_mode: bpy.props.EnumProperty(
        name="Pose Mode",
        description="Character pose hint (leave unset for non-characters)",
        items=[
            ("NONE", "Unset", "Do not hint a pose"),
            ("a-pose", "A-Pose", "Character A-pose"),
            ("t-pose", "T-Pose", "Character T-pose"),
        ],
        default="NONE",
    )

    # Meshy-only: optional separate texture prompt.
    texture_prompt: bpy.props.StringProperty(
        name="Texture Prompt",
        description="Extra prompt just for texture synthesis",
        default="",
    )

    # Hunyuan Pro only: geometry-only vs normal generation.
    hunyuan_generate_type: bpy.props.EnumProperty(
        name="Generation",
        description="Hunyuan output flavor",
        items=[
            ("Normal", "Normal (textured)", "Full textured output"),
            ("Geometry", "Geometry (white model)", "Untextured geometry only"),
        ],
        default="Normal",
    )

    # Hunyuan Rapid only: white-model-only toggle.
    enable_geometry: bpy.props.BoolProperty(
        name="Geometry Only",
        description="Generate only geometry (no textures)",
        default=False,
    )

    # Tripo H3.1: quad topology toggle.
    quad: bpy.props.BoolProperty(
        name="Quad Topology",
        description="Generate quad-dominant topology instead of triangles",
        default=False,
    )

    # Tripo H3.1: real-world scaling.
    auto_size: bpy.props.BoolProperty(
        name="Auto Size",
        description="Scale output to real-world meters",
        default=False,
    )

    # Tripo H3.1: geometry fidelity tier.
    geometry_quality: bpy.props.EnumProperty(
        name="Geometry Quality",
        description="Geometry detail level",
        items=[
            ("standard", "Standard", "Default geometry detail"),
            ("detailed", "Detailed", "Higher-detail geometry"),
        ],
        default="standard",
    )

    # Tripo H3.1: texture fidelity tier.
    texture_quality: bpy.props.EnumProperty(
        name="Texture Quality",
        description="Texture detail level",
        items=[
            ("standard", "Standard", "Default texture detail"),
            ("detailed", "Detailed", "Higher-detail textures"),
        ],
        default="standard",
    )

    # Tripo H3.1 text-to-3D only.
    negative_prompt: bpy.props.StringProperty(
        name="Negative Prompt",
        description="What to avoid in the generation",
        default="",
    )

    # Tripo H3.1 image-to-3D only.
    orientation: bpy.props.EnumProperty(
        name="Orientation",
        description="Output orientation",
        items=[
            ("default", "Default", "Standard orientation"),
            ("align_image", "Align to Image", "Rotate to match input view"),
        ],
        default="default",
    )

    # Tripo H3.1 image-to-3D only.
    texture_alignment: bpy.props.EnumProperty(
        name="Texture Alignment",
        description="How textures relate to the input image",
        items=[
            ("original_image", "Original Image", "Follow the input image"),
            ("geometry", "Geometry", "Follow the generated geometry"),
        ],
        default="original_image",
    )

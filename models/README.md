# Adding Models

This guide covers how to add new fal.ai model definitions to the addon.

## Architecture Overview

```
models/
├── base.py                  # FalModel, VisualFalModel, AudioFalModel
├── image_generation/        # Sketch, depth, refinement models
│   ├── base.py              # Backend presets (NanoBanana, FLUX1Dev, etc.)
│   ├── sketch_guided.py
│   ├── depth_guided.py
│   └── refinement.py
├── image_processing/        # Image upscaling
│   └── upscaling.py
├── video_processing/        # Video upscaling
│   └── upscaling.py
└── audio_generation/        # Speech, music, sound effects
    ├── speech.py
    ├── music.py
    └── sfx.py
```

Models are organized into **domain directories** (`image_generation/`, `audio_generation/`, etc.). Each domain directory contains:

- An **abstract task class** that represents a capability (e.g. `ImageUpscalingModel`, `MusicGenerationModel`)
- One or more **concrete model classes** that bind an endpoint to that capability

Models are discovered automatically via subclass introspection — `Model.enumerate()` and `Model.catalog()` walk `__subclasses__()` at runtime. No central registry is needed; just subclass and import.

## Base Classes

Pick the right base depending on what your model produces:

| Base Class | Use For |
|---|---|
| `VisualFalModel` | Image/video generation and processing (handles size, image/video URLs, prompt expansion) |
| `AudioFalModel` | Audio generation (handles prompt/text, audio URLs, duration) |
| `FalModel` | Anything else (you must implement `parameters()` yourself) |

## Simple Case: Adding a Model to an Existing Task

When a task class already exists and the new model's API matches the base `parameters()` output, you only need class attributes.

### Step 1 — Define the model class

```python
# models/image_processing/upscaling.py

class SeedVR29BImageUpscalingModel(ImageUpscalingModel):
    endpoint = "fal-ai/seedvr/upscale/image"
    display_name = "SeedVR2 9B"
    image_url_parameter = "image_url"
```

The required attributes are:

| Attribute | Purpose |
|---|---|
| `endpoint` | The fal.ai endpoint path |
| `display_name` | Human-readable name shown in Blender UI |

Additional attributes depend on the base class. For `VisualFalModel`:

| Attribute | When to set |
|---|---|
| `image_url_parameter` | Endpoint accepts a single image URL |
| `image_urls_parameter` | Endpoint accepts a list of image URLs |
| `video_url_parameter` / `video_urls_parameter` | Same, for video |
| `size_parameter` | Endpoint wraps width/height in a nested object (e.g. `"image_size"`) |
| `prompt_expansion_parameter` | Endpoint has a prompt expansion toggle (e.g. `"enable_prompt_expansion"`) |
| `use_resolution_aspect_ratio` | Set `True` if the endpoint uses aspect ratio + resolution tier instead of pixel dimensions; also define `aspect_ratios` and `resolutions` |
| `modulo` | Snap dimensions to a multiple (e.g. `64`) |
| `static_parameters` | Dict of fixed parameters always sent with every request |

For `AudioFalModel`:

| Attribute | When to set |
|---|---|
| `prompt_parameter` | Parameter name for the prompt field (e.g. `"prompt"`, `"text"`) |
| `text_parameter` | Parameter name for TTS text input |
| `audio_url_parameter` / `audio_urls_parameter` | Endpoint accepts audio input |
| `duration_parameter` | Parameter name for duration (e.g. `"duration_seconds"`) |
| `duration_in_ms` | Set `True` if the endpoint expects milliseconds; the base converts seconds to ms automatically |

### Step 2 — Export it

Add the class to the `__all__` list and imports in the module's `__init__.py`, then bubble it up through `models/__init__.py`.

```python
# models/image_processing/__init__.py
from .upscaling import ImageUpscalingModel, SeedVR29BImageUpscalingModel

__all__ = [
    "ImageUpscalingModel",
    "SeedVR29BImageUpscalingModel",
]
```

```python
# models/__init__.py  (add to existing imports and __all__)
from .image_processing import (
    ImageUpscalingModel,
    SeedVR29BImageUpscalingModel,
)
```

That's it. The model will appear in any UI that calls `ImageUpscalingModel.enumerate()`.

## Intermediate Case: Backend Presets with Multiple Tasks

Some backends (NanoBanana, FLUX.1 Dev, etc.) serve multiple tasks — sketch generation, refinement, depth guidance — using different endpoints but sharing the same size/resolution logic. These are defined as **backend preset classes** in a `base.py` inside the domain directory.

### Step 1 — Define the backend preset

```python
# models/image_generation/base.py

class ZImageTurbo(VisualFalModel):
    display_name = "Z-Image Turbo"
    size_parameter = "image_size"
```

Backend presets do **not** set `endpoint` — they only define shared attributes like size handling, aspect ratios, or resolutions.

### Step 2 — Compose task + backend via multiple inheritance

```python
# models/image_generation/depth_guided.py

class ZImageTurboDepthGuidedImageGenerationModel(
    DepthGuidedImageGenerationModel, ZImageTurbo
):
    endpoint = "fal-ai/z-image/turbo/controlnet"
    image_url_parameter = "image_url"
    prompt_expansion_parameter = "enable_prompt_expansion"
```

The class inherits from both the **task class** (left) and the **backend preset** (right). Python's MRO resolves method calls left-to-right, so task-specific `parameters()` overrides run first.

## Complex Case: Custom `parameters()` Logic

When the fal.ai endpoint requires non-standard payload shaping — merging prompts, restructuring fields, adding nested objects — override `parameters()`.

### Example: Merging system and user prompts

```python
class SketchGuidedImageGenerationModel(VisualFalModel):
    @classmethod
    def parameters(cls, **kwargs: Any) -> dict[str, Any]:
        params = super().parameters(**kwargs)
        prompt = params.pop("prompt", "")
        system_prompt = params.pop("system_prompt", "")
        if system_prompt and prompt:
            prompt = f"{system_prompt}\n\nFollow the user's prompt: {prompt}"
        elif system_prompt and not prompt:
            prompt = system_prompt
        params["prompt"] = prompt
        return params
```

### Example: Restructuring into nested controlnet format

```python
class FLUX1DevDepthGuidedImageGenerationModel(
    DepthGuidedImageGenerationModel, FLUX1Dev
):
    endpoint = "fal-ai/flux-general"
    image_url_parameter = "image_url"

    @classmethod
    def parameters(cls, **kwargs: Any) -> dict[str, Any]:
        params = super().parameters(**kwargs)
        params["controlnet_unions"] = [
            {
                "path": "Shakker-Labs/FLUX.1-dev-ControlNet-Union-Pro",
                "controls": [
                    {
                        "control_image_url": params.pop("image_url", None),
                        "control_mode": "depth",
                    }
                ],
            },
        ]
        return params
```

### Example: Non-standard parameter names

When the endpoint uses parameter names that don't match the base class conventions, just map them in the class attributes:

```python
class ElevenLabsSoundEffectsGenerationModel(SoundEffectsGenerationModel):
    endpoint = "fal-ai/elevenlabs/sound-effects/v2"
    display_name = "ElevenLabs Sound Effects v2"
    prompt_parameter = "text"
    duration_parameter = "duration_seconds"
```

### Guidelines for overriding `parameters()`

1. Always call `super().parameters(**kwargs)` first to get the base payload.
2. Use `params.pop()` to consume fields you're restructuring so they don't leak into the final payload.
3. Access raw kwargs for values the base class doesn't handle (e.g. `kwargs.get("strength", 0.5)`).
4. Return the complete dict that should be sent to the fal.ai API.

## Adding a New Task / Domain

When you need to support an entirely new capability:

### Step 1 — Create a new task class

If it fits an existing domain, add a file to that directory. Otherwise create a new domain directory.

```
models/
└── audio_generation/
    └── new_task.py
```

```python
# models/audio_generation/new_task.py
from ..base import AudioFalModel

class VoiceCloningModel(AudioFalModel):
    text_parameter = "text"
    audio_url_parameter = "reference_audio_url"
```

The task class can be a plain subclass (like `SoundEffectsGenerationModel`) if the base `parameters()` already does the right thing. Override `parameters()` or `enumerate()` only when the task has unique needs.

### Step 2 — Add concrete models

```python
class ElevenLabsVoiceCloningModel(VoiceCloningModel):
    endpoint = "fal-ai/elevenlabs/voice-clone"
    display_name = "ElevenLabs Voice Clone"
```

### Step 3 — Wire up exports

Follow the same pattern: module `__init__.py` → domain `__init__.py` → `models/__init__.py`.

## Disabling a Model

Set `enabled = False` on the class. It will be excluded from `enumerate()` but remain importable for testing.

```python
class DeprecatedModel(ImageUpscalingModel):
    enabled = False
    endpoint = "fal-ai/old-model"
    display_name = "Old Model"
```

## Checklist

- [ ] Subclass the right base (`VisualFalModel`, `AudioFalModel`, or `FalModel`)
- [ ] Set `endpoint` and `display_name`
- [ ] Set media parameter attributes (`image_url_parameter`, `audio_url_parameter`, etc.)
- [ ] Override `parameters()` only if the endpoint requires non-standard payload shaping
- [ ] Export from module `__init__.py` → domain `__init__.py` → `models/__init__.py`
- [ ] Verify it appears in `.enumerate()` output

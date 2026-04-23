# fal.ai Blender Extension

AI-powered 3D, materials, rendering, video, and audio — directly inside Blender.

**Update: this package will soon be transferred to the `fal-ai` organization as the official fal blender extension!** Links will be posted when complete. 

~Work in progress and not officially supported. If/when this is officially supported, the repository will be moved under fal's GitHub organization.~

---

## Quick Start

1. Install the addon (see [Installation](#installation)) - supports Blender 4.2 and up on all platforms
2. Enable **fal.ai — AI Generation Suite** in `Edit → Preferences → Add-ons`
3. Set your [fal.ai](https://fal.ai) API key in the addon preferences
4. Open the sidebar (`N`) in either the **3D Viewport** or the **Video Sequence Editor** and click the **fal.ai** tab
5. Pick a workflow, configure its parameters, and click **Generate**

Jobs run in the background — keep working and they'll appear in the **Active Jobs** sub-panel. Multiple jobs can run at once.

<div align="center">
<img width="564" height="453" alt="image" src="https://github.com/user-attachments/assets/6b46660a-c4eb-41dd-9ec9-a6c9adb75cca" /><br />
<em>The fal.ai Blender extension preferences window.</em>
</div>

---

## 3D Panel Workflows

Available in the 3D Viewport sidebar under the **fal.ai** tab.

### 3D Generation

https://github.com/user-attachments/assets/4dbb0511-933b-43e6-986a-343f606cedc3

Generates 3D models from image or text and imports the resulting mesh at the 3D cursor as GLB (falls back to OBJ + MTL + texture when needed).

#### Text-to-3D

Generate a textured 3D mesh from a prompt. Exposes endpoint-specific controls (face budget, symmetry, pose hints, art style, quad vs triangle topology, etc.) conditionally based on which endpoint you pick.

| Endpoint | Notes |
|----------|-------|
| [Meshy v6 Preview](https://fal.ai/models/fal-ai/meshy/v6-preview/text-to-3d) | Fast geometry + texture, 100–300k face budget, pose / symmetry hints |
| [Hunyuan 3D v3.1 Pro](https://fal.ai/models/fal-ai/hunyuan-3d/v3.1/pro/text-to-3d) | High-fidelity, 40k–1.5M faces, optional geometry-only output |
| [Hunyuan 3D v3.1 Rapid](https://fal.ai/models/fal-ai/hunyuan-3d/v3.1/rapid/text-to-3d) | Quick turnaround, geometry-only toggle |
| [Tripo P1](https://fal.ai/models/tripo3d/p1/text-to-3d) | Low-poly friendly, 48–20k face budget |
| [Tripo H3.1](https://fal.ai/models/tripo3d/h3.1/text-to-3d) | Quad topology option, real-world auto-sizing, separate texture-seed |

#### Image-to-3D

Same endpoints, but conditioned on a source image (file on disk or current render result). Prompt is still available as an optional guide.

| Endpoint | Notes |
|----------|-------|
| [Meshy v6 Preview](https://fal.ai/models/fal-ai/meshy/v6-preview/image-to-3d) | Pose / symmetry hints, texture prompt |
| [Hunyuan 3D v3.1 Pro](https://fal.ai/models/fal-ai/hunyuan-3d/v3.1/pro/image-to-3d) | Geometry-only option |
| [Hunyuan 3D v3.1 Rapid](https://fal.ai/models/fal-ai/hunyuan-3d/v3.1/rapid/image-to-3d) | Geometry-only option |
| [Tripo P1](https://fal.ai/models/tripo3d/p1/image-to-3d) | Low-poly |
| [Tripo H3.1](https://fal.ai/models/tripo3d/h3.1/image-to-3d) | Orientation + texture-alignment controls for image-to-3D |

---

### Materials

https://github.com/user-attachments/assets/8d65a83b-8fee-48c6-b0e5-83446ebc98cf

Produces a full Principled BSDF material (base color, roughness, metalness, normal, displacement) applied to the selected object.

#### Text-to-Material

Generate a complete tiling PBR material from a text prompt.

| Endpoint | Notes |
|----------|-------|
| [PATINA Material](https://fal.ai/models/fal-ai/patina/material) | Generates base color + all PBR maps from a prompt |

#### Image-to-Maps

Estimate PBR maps (roughness, normal, displacement, metalness) from an existing base-color image. Useful when you already have a texture and want the rest of the stack.

| Endpoint | Notes |
|----------|-------|
| [PATINA](https://fal.ai/models/fal-ai/patina) | Estimates PBR maps from a supplied base-color image |

There's also a **Tiling Texture** sub-mode if you just want a seamless base color from a prompt without the PBR stack.

---

### Image Rendering

Each mode does a quick technical render of the scene (depth, edges, sketch, or a normal render), then hands that off to fal as conditioning for an AI image.

*Note: All videos in this section have processing time truncated.*

#### Depth-to-Image

https://github.com/user-attachments/assets/b7646563-6361-4b2c-b573-17977e1d0e33

Renders a Mist depth pass, then generates an AI image guided by scene depth. Great for preserving spatial layout while restyling.

| Endpoint | Notes |
|----------|-------|
| [Z-Image Turbo (ControlNet)](https://fal.ai/models/fal-ai/z-image/turbo/controlnet) | Fast, general-purpose |
| [FLUX.1 \[dev\] (ControlNet)](https://fal.ai/models/fal-ai/flux-general) | Higher quality, slower |

#### Edge-to-Image

https://github.com/user-attachments/assets/48f1c5bc-9684-4312-8360-a8805b65a978

Runs Canny edge detection on a scene render and uses the edges as structural guidance for the AI image.

| Endpoint | Notes |
|----------|-------|
| [Z-Image Turbo (ControlNet)](https://fal.ai/models/fal-ai/z-image/turbo/controlnet) | Fast |
| [FLUX.1 \[dev\] (ControlNet)](https://fal.ai/models/fal-ai/flux-general) | Higher quality |

#### Sketch-to-Image

https://github.com/user-attachments/assets/65923871-ce5d-4f6b-a258-d541fa1c51f4

Renders a Freestyle line drawing (optionally with object-name labels overlaid) and reimagines it as a finished image. Label overlays let the model ground parts of the sketch to specific concepts.

| Endpoint | Notes |
|----------|-------|
| [Nano Banana](https://fal.ai/models/fal-ai/nano-banana/edit) | Google's image-edit |
| [Nano Banana Pro](https://fal.ai/models/fal-ai/nano-banana-pro/edit) | Google's image-edit, higher quality |
| [Nano Banana 2](https://fal.ai/models/fal-ai/nano-banana-2/edit) | Google's image-edit, newer |
| [GPT Image 1.5](https://fal.ai/models/fal-ai/gpt-image-1.5/edit) | OpenAI's image-edit |
| [GPT Image 2](https://fal.ai/models/openai/gpt-image-2/edit) | OpenAI's latest image-edit |
| [Seedream 4.5](https://fal.ai/models/fal-ai/bytedance/seedream/v4.5/edit) | ByteDance's image-edit |
| [Seedream 5 Lite](https://fal.ai/models/fal-ai/bytedance/seedream/v5/lite/edit) | ByteDance's image-edit, lite variant |

#### Render-to-Image (Refine)

https://github.com/user-attachments/assets/24077dae-da98-41a8-bfa5-91c35080252d

Renders the scene normally and refines the result with img2img or an edit model. A strength slider controls how far the model drifts from the input render.

| Endpoint | Notes |
|----------|-------|
| [Nano Banana](https://fal.ai/models/fal-ai/nano-banana/edit) | Image-edit style |
| [Nano Banana Pro](https://fal.ai/models/fal-ai/nano-banana-pro/edit) | Image-edit style, higher quality |
| [Nano Banana 2](https://fal.ai/models/fal-ai/nano-banana-2/edit) | Image-edit style, newer |
| [GPT Image 1.5](https://fal.ai/models/fal-ai/gpt-image-1.5/edit) | OpenAI's image-edit |
| [GPT Image 2](https://fal.ai/models/openai/gpt-image-2/edit) | OpenAI's latest image-edit |
| [Z-Image Turbo](https://fal.ai/models/fal-ai/z-image/turbo/image-to-image) | Img2img with strength control, fast |
| [FLUX.1 \[dev\]](https://fal.ai/models/fal-ai/flux/dev/image-to-image) | Img2img with strength control |
| [FLUX.2 Klein 9B](https://fal.ai/models/fal-ai/flux-2/klein/9b/edit) | Img2img with strength control |

---

### Video Rendering

https://github.com/user-attachments/assets/5645a408-225b-4d67-b1f6-934c456d5f2a

Same controller as image rendering, but the mode switcher is set to **Video**. Renders an animation sequence as depth or edges, then generates a video conditioned on that sequence.

*Note: The above video has processing time truncated.*

#### Depth-to-Video

Exports a depth animation across the scene's frame range and generates a depth-guided video. Optionally supply a first-frame reference image.

| Endpoint | Notes |
|----------|-------|
| [LTX-2 19B](https://fal.ai/models/fal-ai/ltx-2-19b/video-to-video) | Open-weight, fast |
| [LTX-2 19B Distilled](https://fal.ai/models/fal-ai/ltx-2-19b/distilled/video-to-video) | Open-weight, faster |
| [LTX 2.3 22B Ref V2V](https://fal.ai/models/fal-ai/ltx-2.3-22b/reference-video-to-video) | Newer LTX with reference-image support |
| [LTX 2.3 22B Distilled Ref V2V](https://fal.ai/models/fal-ai/ltx-2.3-22b/distilled/reference-video-to-video) | Distilled, with reference-image support |
| [Wan-VACE 14B](https://fal.ai/models/fal-ai/wan-vace-14b/depth) | Good at natural motion |
| [Wan Fun 2.2 A14B](https://fal.ai/models/fal-ai/wan-22-vace-fun-a14b/depth) | Stylized |

#### Edge-to-Video

Canny edges are computed per frame (in parallel threads) and fed to the model as structural conditioning.

| Endpoint | Notes |
|----------|-------|
| [LTX-2 19B](https://fal.ai/models/fal-ai/ltx-2-19b/video-to-video) | Open-weight |
| [LTX-2 19B Distilled](https://fal.ai/models/fal-ai/ltx-2-19b/distilled/video-to-video) | Open-weight, faster |
| [LTX 2.3 22B Ref V2V](https://fal.ai/models/fal-ai/ltx-2.3-22b/reference-video-to-video) | Supports a reference image |
| [LTX 2.3 22B Distilled Ref V2V](https://fal.ai/models/fal-ai/ltx-2.3-22b/distilled/reference-video-to-video) | Distilled, with reference image |

Video results import into the Video Sequence Editor. The addon auto-disables `scene.render.use_sequencer` so F12 keeps rendering the 3D view, and pops up a notification when the clip lands.

---

## Video Editor Workflows

Available in the Video Sequence Editor sidebar under the **fal.ai** tab. Results drop in as VSE strips at the current frame and are scaled to the scene's target resolution.

### Audio

https://github.com/user-attachments/assets/f1f087c3-c867-4aad-bf52-cc505944f740

#### Text-to-Speech (Presets)

Generate speech from text using a named preset voice.

| Endpoint | Notes |
|----------|-------|
| [ElevenLabs TTS Turbo v2.5](https://fal.ai/models/fal-ai/elevenlabs/tts/turbo-v2.5) | Broad voice catalog |
| [ElevenLabs v3](https://fal.ai/models/fal-ai/elevenlabs/tts/eleven-v3) | Broad voice catalog, newer |
| [MiniMax Speech Turbo](https://fal.ai/models/fal-ai/minimax/speech-2.8-turbo) | |
| [MiniMax Speech 2.8 HD](https://fal.ai/models/fal-ai/minimax/speech-2.8-hd) | Higher quality |
| [Kokoro](https://fal.ai/models/fal-ai/kokoro/american-english) | Open-weight |
| [xAI TTS](https://fal.ai/models/xai/tts/v1) | |
| [Gemini Flash TTS](https://fal.ai/models/fal-ai/gemini-3.1-flash-tts) | |
| [Inworld TTS](https://fal.ai/models/fal-ai/inworld-tts) | |

#### Text-to-Speech (Voice Clone)

Same catalog (for endpoints that support it) but conditioned on a reference audio file — the model clones that voice.

| Endpoint | Notes |
|----------|-------|
| [MiniMax Voice Clone](https://fal.ai/models/fal-ai/minimax/voice-clone) | Used by MiniMax Speech Turbo and 2.8 HD |

#### Text-to-SFX

Generate sound effects from a text description.

| Endpoint | Notes |
|----------|-------|
| [ElevenLabs Sound Effects v2](https://fal.ai/models/fal-ai/elevenlabs/sound-effects/v2) | |
| [CassetteAI SFX](https://fal.ai/models/cassetteai/sound-effects-generator) | |

#### Text-to-Music

Generate music from a text prompt with duration control.

| Endpoint | Notes |
|----------|-------|
| [ElevenLabs Music](https://fal.ai/models/fal-ai/elevenlabs/music) | |
| [MiniMax Music 2.6](https://fal.ai/models/fal-ai/minimax-music/v2.6) | |
| [Stable Audio 2.5](https://fal.ai/models/fal-ai/stable-audio-25/text-to-audio) | |
| [CassetteAI Music](https://fal.ai/models/cassetteai/music-generator) | |

---

### Video

https://github.com/user-attachments/assets/b0255483-bcac-4f18-969f-5209cee85ef0

Before submitting a video job you'll see a confirm dialog with the effective size, duration, and cost-relevant settings.

*Note: The above video has processing time truncated.*

#### Text-to-Video

Generate a video clip directly from a prompt.

| Endpoint | Notes |
|----------|-------|
| [LTX-2 19B](https://fal.ai/models/fal-ai/ltx-2-19b/text-to-video) | Open-weight |
| [LTX-2 19B Distilled](https://fal.ai/models/fal-ai/ltx-2-19b/distilled/text-to-video) | Open-weight, faster |
| [LTX 2.3 22B](https://fal.ai/models/fal-ai/ltx-2.3-22b/text-to-video) | Newer LTX |
| [LTX 2.3 22B Distilled](https://fal.ai/models/fal-ai/ltx-2.3-22b/distilled/text-to-video) | Newer LTX, faster |
| [Seedance 2.0](https://fal.ai/models/bytedance/seedance-2.0/text-to-video) | ByteDance |
| [Seedance 2.0 Fast](https://fal.ai/models/bytedance/seedance-2.0/fast/text-to-video) | ByteDance, faster |
| [Kling v3 Standard](https://fal.ai/models/fal-ai/kling-video/v3/standard/text-to-video) | |
| [Kling v3 Pro](https://fal.ai/models/fal-ai/kling-video/v3/pro/text-to-video) | Higher quality |
| [Veo 3.1](https://fal.ai/models/fal-ai/veo3.1) | Google |
| [Veo 3.1 Fast](https://fal.ai/models/fal-ai/veo3.1/fast) | Google, faster |
| [Wan 2.2](https://fal.ai/models/fal-ai/wan/v2.2-a14b/text-to-video) | |
| [Wan 2.2 Turbo](https://fal.ai/models/fal-ai/wan/v2.2-a14b/text-to-video/turbo) | Faster |
| [Wan 2.7](https://fal.ai/models/fal-ai/wan/v2.7/text-to-video) | Newer |
| [Sora 2](https://fal.ai/models/fal-ai/sora-2/text-to-video) | OpenAI |

#### Image-to-Video

Animate a still image. Same catalog of video endpoints (those that support image conditioning).

| Endpoint | Notes |
|----------|-------|
| [LTX-2 19B](https://fal.ai/models/fal-ai/ltx-2-19b/image-to-video) | Open-weight |
| [LTX-2 19B Distilled](https://fal.ai/models/fal-ai/ltx-2-19b/distilled/image-to-video) | Open-weight, faster |
| [LTX 2.3 22B](https://fal.ai/models/fal-ai/ltx-2.3-22b/image-to-video) | Newer LTX |
| [LTX 2.3 22B Distilled](https://fal.ai/models/fal-ai/ltx-2.3-22b/distilled/image-to-video) | Newer LTX, faster |
| [Seedance 2.0](https://fal.ai/models/bytedance/seedance-2.0/image-to-video) | ByteDance |
| [Seedance 2.0 Fast](https://fal.ai/models/bytedance/seedance-2.0/fast/image-to-video) | ByteDance, faster |
| [Kling v3 Standard](https://fal.ai/models/fal-ai/kling-video/v3/standard/image-to-video) | |
| [Kling v3 Pro](https://fal.ai/models/fal-ai/kling-video/v3/pro/image-to-video) | Higher quality |
| [Veo 3.1](https://fal.ai/models/fal-ai/veo3.1/image-to-video) | Google |
| [Veo 3.1 Fast](https://fal.ai/models/fal-ai/veo3.1/fast/image-to-video) | Google, faster |
| [Wan 2.2](https://fal.ai/models/fal-ai/wan/v2.2-a14b/image-to-video) | |
| [Wan 2.2 Turbo](https://fal.ai/models/fal-ai/wan/v2.2-a14b/image-to-video/turbo) | Faster |
| [Wan 2.7](https://fal.ai/models/fal-ai/wan/v2.7/image-to-video) | Newer |

---

## Shared Workflows

These appear in both the 3D Viewport sidebar and the VSE sidebar with shared config.

### Upscale Image

Upscale an image from a file on disk, the current render result, or a texture slot on the active object.

| Endpoint | Notes |
|----------|-------|
| [SeedVR2 9B](https://fal.ai/models/fal-ai/seedvr/upscale/image) | Highest quality |
| [AuraSR](https://fal.ai/models/fal-ai/aura-sr) | Fast 4x |
| [Clarity Upscaler](https://fal.ai/models/fal-ai/clarity-upscaler) | Detail-preserving |

### Upscale Video

Upscale a video file on disk or from the VSE.

| Endpoint | Notes |
|----------|-------|
| [SeedVR2 9B](https://fal.ai/models/fal-ai/seedvr/upscale/video) | |
| [Topaz Video](https://fal.ai/models/fal-ai/topaz/upscale/video) | |

---

## Preferences

`Edit → Preferences → Add-ons → fal.ai — AI Generation Suite`:

- **API Key** — your [fal.ai](https://fal.ai) key (required)
- **Output Directory** — where generated files are saved
- **Auto-Import** — whether results are imported into the active scene automatically

## Advanced Parameters

Every workflow has a collapsible **Advanced Parameters** section that lets you set arbitrary key/value pairs on the request. Useful when fal ships a new endpoint option before the addon's UI catches up — just add it by name. Values are typed (string / int / float / bool / JSON).

## Requirements

- Blender 4.2+ (works on 4.x and 5.x)
- A [fal.ai](https://fal.ai) API key

## Installation

### From Release

1. Download the latest `.zip` from Releases
2. Open Blender, then either a.) use `Edit → Preferences → Add-ons → Install from Disk`, then select the `.zip` file, or b.) drag and drop the `.zip` into the interface anywhere
3. Set your API key in the addon preferences


## Architecture

```
controllers/          Blender-side workflows (UI, operators, properties)
  base.py             FalController base class and registration
  operators.py        FalOperator base class (background job submission)
  ui.py               FalControllerPanel (declarative field layout)
  advanced_params.py  Key/value override UIList shared across controllers
  audio/              TTS (preset + clone), SFX, Music (VSE)
  generate_3d/        Text/Image-to-3D (3D Viewport)
  material/           Text-to-Material, Image-to-Maps, Tiling (3D Viewport)
  render/             Depth / Edge / Sketch / Refine modes + Video (3D Viewport)
  upscale/            Image and video upscaling (shared: 3D + VSE)
  video/              Text/Image-to-Video (VSE)

models/               fal.ai endpoint definitions and parameter builders
  base.py             FalModel, VisualFalModel, AudioFalModel, VideoFalModel
  audio_generation/   Speech, SFX, music
  image_generation/   Depth / edge / sketch / refine endpoints
  image_processing/   Image upscaling
  material_generation/ Material, PBR estimation, tiling
  mesh_generation/    Text-to-3D, image-to-3D
  video_generation/   Text/image-to-video, depth/edge video
  video_processing/   Video upscaling

app.py                Panel registration for 3D and VSE sidebars
job_queue.py          Async FalJob / JobManager (threads + bpy timer)
importers.py          GLB/OBJ import, texture application, VSE strip helpers
preferences.py        API key, output dir, auto-import
utils.py              Upload/download, compositor snapshot/restore, fonts
```

Design notes:

- **Controller / Model separation.** Controllers handle Blender-side UI, operators, and scene interaction. Models define the fal.ai endpoint URL and translate UI params into the endpoint's schema. Adding a new endpoint is usually a single new `FalModel` subclass.
- **Declarative panels.** `FalControllerPanel` drives field layout, conditional visibility, and grouping from lists and lambdas — no manual `draw()` per workflow. Conditionals key off the selected endpoint's `ui_parameter_map`, so fields show up only when the current endpoint actually supports them.
- **Async job queue.** API calls run in background threads via `fal_client.subscribe()`. A `bpy.app.timers` loop polls for completion, keeping Blender's UI responsive.
- **Dual-context panels.** Controllers declare `panel_3d`, `panel_vse`, or both and auto-register in the appropriate editor sidebar.

## Tests

```bash
cd fal-blender
./tests/run_tests.sh
```

Model tests don't require Blender; they exercise the `FalModel.parameters()` builders and the per-endpoint `ui_parameter_map` forwarding.

## Planned

- Image-to-Grease Pencil-to-Curves (vector workflow)
- Multi-Image-to-3D pipeline (multi-angle capture to mesh)
- Real-time neural rendering preview
- LoRA support for consistent styling

## License

GPL-3.0-or-later — Copyright 2026 Features and Labels, Inc.

---

Built with love by Benjamin Paine for [fal.ai](https://fal.ai)

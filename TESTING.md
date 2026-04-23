# fal.ai Blender Extension — Test Plan

**Version:** 0.1.0 (Pre-release)
**Date:** 2026-03-02
**Testers:** Internal (fal team)
**Platforms:** Windows, Linux (Ubuntu), macOS (Intel + Apple Silicon)

---

## Pre-Test Setup

### 1. Build the Extension

```bash
cd ~/fal-blender  # or wherever you cloned it

# Download wheel dependencies
bash scripts/build_wheels.sh

# Generate blender_manifest.toml from the template (wheel list)
make sync-manifest
# Then create the zip:
zip -r fal_ai-0.1.0.zip . \
  -x ".*" -x "__pycache__/*" -x "scripts/*" -x "tests/*" -x "*.md" -x ".git/*"
```

### 2. Install in Blender

1. Open Blender 4.5+
2. Edit → Preferences → Add-ons
3. Click "Install from Disk" (top right dropdown)
4. Select `fal_ai-0.1.0.zip`
5. Enable "fal.ai — AI Generation Suite"
6. In the addon preferences, enter your fal.ai API key
7. Press N in 3D Viewport to open sidebar → find "fal.ai" tab

### 3. Test Environment

| Platform | Blender Version | GPU | Tester |
|----------|-----------------|-----|--------|
| Windows 11 | 4.5 LTS | NVIDIA | |
| Windows 11 | 4.3 | NVIDIA | |
| Ubuntu 24.04 | 4.5 LTS | NVIDIA | |
| macOS Sonoma (Intel) | 4.5 LTS | AMD | |
| macOS Sonoma (M3) | 4.5 LTS | Apple Silicon | |

---

## Test Cases

### T0: Installation & Setup

| ID | Test | Steps | Expected | Pass? | Notes |
|----|------|-------|----------|-------|-------|
| T0.1 | Clean install | Install zip on fresh Blender | Addon appears in list, enables without error | | |
| T0.2 | API key prompt | Enable addon without key set | Preferences show warning + link to fal.ai/dashboard | | |
| T0.3 | API key via env | Set `FAL_KEY` env var, restart Blender | Addon uses env key, no warning | | |
| T0.4 | Panel appears | Press N in 3D Viewport | "fal.ai" tab visible in sidebar | | |
| T0.5 | Tab switching | Click each tab (Texture, 3D, Upscale, Render, Video, Audio, Mesh Ops) | Each panel content updates correctly | | |

---

### T1: Text-to-Texture

| ID | Test | Steps | Expected | Pass? | Notes |
|----|------|-------|----------|-------|-------|
| T1.1 | Basic generation | Select cube, enter prompt "red brick wall texture", click Generate | Texture generated, applied to cube's material | | |
| T1.2 | Endpoint switch | Change endpoint to "Nano Banana 2", generate | Different endpoint used, still works | | |
| T1.3 | Custom resolution | Set 512x512, generate | Image is ~512x512 (or closest aspect) | | |
| T1.4 | Seed consistency | Set seed=42, generate twice | Same result both times | | |
| T1.5 | No object selected | Deselect all, generate | Texture generates, saved to Images but not applied | | |
| T1.6 | Empty prompt | Leave prompt blank, try generate | Button disabled or shows error | | |
| T1.7 | Job status | Generate, watch Jobs panel | Shows progress, then "complete" | | |

---

### T2: 3D Generation

| ID | Test | Steps | Expected | Pass? | Notes |
|----|------|-------|----------|-------|-------|
| T2.1 | Text-to-3D | Mode: Text, prompt "a medieval wooden chair", Generate | GLB downloaded, imported at 3D cursor | | |
| T2.2 | Image-to-3D (file) | Mode: Image, Source: File, pick an image, Generate | 3D model generated from image | | |
| T2.3 | Image-to-3D (render) | Render a frame (F12), Mode: Image, Source: Render Result, Generate | Uses render result as source | | |
| T2.4 | Endpoint switch | Switch between Meshy v5 and v6 | Both work | | |
| T2.5 | Long prompt | Use 200+ character description | Handles gracefully, truncates label if needed | | |
| T2.6 | Job cancellation | Start generation, try to close Blender | Warns about active jobs OR handles gracefully | | |

---

### T3: AI Upscale

| ID | Test | Steps | Expected | Pass? | Notes |
|----|------|-------|----------|-------|-------|
| T3.1 | Image upscale (file) | Mode: Image, Source: File, pick small image, Generate | Upscaled image loaded into Image Editor | | |
| T3.2 | Image upscale (render) | Render small (480p), Source: Render Result, Generate | Render upscaled | | |
| T3.3 | Image upscale (texture) | Source: Texture, pick from dropdown, Generate | Selected texture upscaled | | |
| T3.4 | Video upscale | Mode: Video, pick a short video file, Generate | Upscaled video downloaded, optionally added to VSE | | |
| T3.5 | Endpoint comparison | Try SeedVR2 vs AuraSR vs Clarity on same image | All work, compare quality | | |

---

### T4: Neural Rendering

| ID | Test | Steps | Expected | Pass? | Notes |
|----|------|-------|----------|-------|-------|
| T4.1 | Depth mode basic | Create simple scene, Mode: Depth, prompt "forest landscape", Generate | Depth pass rendered, image generated with depth structure | | |
| T4.2 | Sketch mode basic | Create blocky scene (cubes), Mode: Sketch, prompt "cozy living room", Generate | Scene reimagined with AI | | |
| T4.3 | Sketch with labels | Add cubes, give each `fal_ai_label` custom property ("sofa", "lamp", "bookshelf"), enable labels, Generate | Labels appear on render, AI interprets them | | |
| T4.4 | Label projection | Place labeled object at edge of frame | Label still renders at correct 2D position | | |
| T4.5 | No camera | Delete camera, try Depth mode | Shows error "No active camera" | | |
| T4.6 | Different endpoints | Try FLUX Depth ControlNet vs z-image ControlNet | Both work | | |

---

### T5: Video Generation

| ID | Test | Steps | Expected | Pass? | Notes |
|----|------|-------|----------|-------|-------|
| T5.1 | Text-to-video | Mode: Text, prompt "a cat walking through a garden", duration 5s, Generate | Video generated, downloads | | |
| T5.2 | Image-to-video | Mode: Image, Source: File, pick image, Generate | Video generated from image | | |
| T5.3 | Depth video | Mode: Depth, set up animated camera, Generate | Depth sequence → video | | |
| T5.4 | Import to VSE | Enable "Import to VSE", generate | Video appears as strip in VSE | | |
| T5.5 | Duration options | Try 5s vs 10s | Both work | | |

---

### T6: Audio Generation

| ID | Test | Steps | Expected | Pass? | Notes |
|----|------|-------|----------|-------|-------|
| T6.1 | TTS preset | Mode: TTS, Voice: Preset, enter text, Generate | Speech audio generated | | |
| T6.2 | TTS voice clone | Mode: TTS, Voice: Clone, pick reference audio, enter text, Generate | Speech matches reference voice | | |
| T6.3 | SFX | Mode: SFX, prompt "thunderstorm with rain", duration 5s, Generate | Sound effect generated | | |
| T6.4 | Music | Mode: Music, prompt "upbeat electronic", duration 10s, Generate | Music generated | | |
| T6.5 | VSE import | Generate any audio | Audio strip added to VSE at playhead | | |
| T6.6 | VSE panel | Open Video Sequence Editor, check sidebar | fal.ai Audio panel appears | | |

**Note:** Audio endpoints may be placeholder — test what we have, note what's missing.

---

### T7: Mesh Operations

| ID | Test | Steps | Expected | Pass? | Notes |
|----|------|-------|----------|-------|-------|
| T7.1 | Retexture | Select mesh with UV, Mode: Retexture, prompt "stone brick texture", Generate | Mesh exported, retextured, reimported | | |
| T7.2 | Remesh | Select mesh, Mode: Remesh, Generate | Mesh exported, remeshed, reimported | | |
| T7.3 | No selection | Deselect all, try generate | Shows error "No object selected" | | |
| T7.4 | Non-mesh selected | Select empty or light, try generate | Shows error or skips gracefully | | |

---

### T8: Error Handling & Edge Cases

| ID | Test | Steps | Expected | Pass? | Notes |
|----|------|-------|----------|-------|-------|
| T8.1 | Invalid API key | Set garbage API key, try generate | Clear error message about auth | | |
| T8.2 | Network disconnect | Disable network mid-generation | Job fails with network error, doesn't crash | | |
| T8.3 | Rapid fire | Click Generate 5x quickly | Jobs queue up, all complete eventually | | |
| T8.4 | Large render | Set output to 4K, try Neural Render | Handles or shows reasonable error | | |
| T8.5 | Concurrent jobs | Start texture gen + 3D gen simultaneously | Both complete, no conflicts | | |
| T8.6 | Blender quit during job | Start long job, quit Blender | Quits (warn?) without hanging | | |

---

### T9: UI/UX Feedback

| ID | Area | Feedback | Severity | Notes |
|----|------|----------|----------|-------|
| T9.1 | Panel layout | | | |
| T9.2 | Dropdown usability | | | |
| T9.3 | Progress feedback | | | |
| T9.4 | Error messages | | | |
| T9.5 | Tooltips/help | | | |
| T9.6 | Keyboard shortcuts | | | |
| T9.7 | Icon clarity | | | |

---

## Platform-Specific Tests

### Windows
- [ ] Wheel loading (especially msgpack with C extension)
- [ ] File paths with spaces
- [ ] Temp file cleanup

### macOS Intel
- [ ] Wheel compatibility
- [ ] Gatekeeper warnings on first run

### macOS Apple Silicon
- [ ] ARM64 wheel loading
- [ ] Performance comparison

### Linux
- [ ] Permissions on temp files
- [ ] Headless rendering for depth pass

---

## Known Issues to Verify

1. **Audio endpoints** — TTS/SFX/Music endpoint lists may be empty (placeholders). Document which are actually available.
2. **Tiling endpoint** — Not yet implemented. Tiling checkbox should be disabled or hidden.
3. **PBR generation** — Not yet implemented.
4. **Video import to VSE** — May use wrong method (`new_movie` vs `new_sound`). Verify.

---

## Feedback Template

After testing, create an issue or note with:

```
## Environment
- OS: 
- Blender version:
- GPU:

## Test Results
- Passed: T1.1, T1.2, T2.1, ...
- Failed: T4.3 (description of failure)
- Skipped: T6.x (audio endpoints not available)

## Bugs Found
1. [BUG] Description — steps to reproduce
2. [BUG] Description — steps to reproduce

## UX Feedback
1. Panel X is confusing because...
2. Would be nice if...

## Performance Notes
- Texture gen took Xs on average
- 3D gen took Xs on average
```

---

## Success Criteria for v0.1.0

- [ ] Installs without error on all 3 platforms
- [ ] API key setup works
- [ ] At least 80% of T1-T4 tests pass
- [ ] No crashes during normal operation
- [ ] Error messages are user-friendly
- [ ] Jobs panel shows accurate status

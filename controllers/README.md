# Adding Controllers

This guide covers how to add new controllers — the Blender-side workflows that wire models to UI panels and operators.

## Architecture Overview

```
controllers/
├── base.py              # FalController base class
├── operators.py         # FalOperator base class
├── ui.py                # FalControllerPanel (declarative UI layout)
├── __init__.py          # Exports all controllers (auto-discovered)
├── audio/               # Audio generation controller
│   ├── controller.py    # FalAudioController
│   ├── operator.py      # FalAudioOperator
│   ├── props.py         # FalAudioPropertyGroup
│   └── __init__.py
└── render/              # Image/video generation controller
    ├── controller.py    # FalRenderController
    ├── operator.py      # FalRenderOperator
    ├── props.py         # FalRenderPropertyGroup
    ├── utils.py         # Rendering helpers (depth, sketch, labels)
    └── __init__.py
```

A controller is a directory with four concerns:

| File | What it defines | Base class |
|---|---|---|
| `props.py` | Blender properties shown in the sidebar | `bpy.types.PropertyGroup` |
| `operator.py` | What happens when the user clicks the button | `FalOperator` |
| `controller.py` | Wires props + operator + panel config together | `FalController` |
| `__init__.py` | Exports the controller class | — |

Controllers are auto-discovered via `FalController.__subclasses__()`. Once a controller subclass is imported in `controllers/__init__.py`, calling `FalController.register_all()` (in the addon's `register()`) handles Blender class registration, panel creation, and scene property binding automatically.

## How It All Fits Together

```
User clicks "Generate" button
        │
        ▼
FalOperator.__call__()          ← your operator logic
        │
        ├─ reads props from PropertyGroup
        ├─ calls Model.catalog()[props.endpoint]
        ├─ builds params via model.parameters(...)
        ├─ creates a FalJob(endpoint, params, on_complete)
        └─ submits to JobManager
                │
                ▼
        Background thread calls fal.ai API
                │
                ▼
        on_complete(job)        ← downloads result, imports into Blender
```

## Simple Case: Fire-and-Forget Operator

The audio controller is the simplest pattern — collect props, call the API, handle the result. No scene modification or modal loop needed.

### Step 1 — Define properties (`props.py`)

Properties are standard Blender `PropertyGroup` fields. Each property becomes a UI widget in the sidebar panel.

```python
import bpy
from ...models import SpeechGenerationModel

class FalAudioPropertyGroup(bpy.types.PropertyGroup):
    mode: bpy.props.EnumProperty(
        name="Mode",
        items=[
            ("TTS", "Text-to-Speech", "Generate speech from text"),
            ("SFX", "Sound Effects", "Generate sound effects from prompt"),
        ],
        default="TTS",
    )

    tts_endpoint: bpy.props.EnumProperty(
        name="Endpoint",
        items=SpeechGenerationModel.enumerate() or [("NONE", "No Models Available", "")],
    )

    text: bpy.props.StringProperty(
        name="Text",
        description="Text to convert to speech",
    )
```

Use `Model.enumerate()` to populate endpoint dropdowns. The fallback `or [("NONE", ...)]` prevents Blender errors when no models are available.

### Step 2 — Define the operator (`operator.py`)

Subclass `FalOperator` and implement `__call__`. The framework passes `props` (your PropertyGroup instance) and `context` automatically.

```python
import bpy
from ..operators import FalOperator
from ...job_queue import FalJob, JobManager
from ...models import SpeechGenerationModel

SPEECH_MODELS = SpeechGenerationModel.catalog()

class FalAudioOperator(FalOperator):
    label = "Generate Audio"

    @classmethod
    def enabled(cls, context, props) -> bool:
        """Controls whether the button is clickable."""
        return bool(props.text.strip())

    def __call__(self, context, props, event=None, invoke=False) -> set[str]:
        model = SPEECH_MODELS[props.tts_endpoint]
        params = model.parameters(text=props.text)

        def on_complete(job: FalJob) -> None:
            # Runs on main thread after API returns
            if job.status == "error":
                print(f"Failed: {job.error}")
                return
            # Download and import result...

        job = FalJob(
            endpoint=model.endpoint,
            arguments=params,
            on_complete=on_complete,
            label=f"TTS: {props.text[:30]}",
        )
        JobManager.get().submit(job)
        self.report({"INFO"}, "Generating speech...")
        return {"FINISHED"}
```

Key points:
- `label` sets the button text in the UI.
- `enabled()` controls the button's enabled/disabled state based on current props.
- `__call__` is the main entry point. It should build the API params, create a `FalJob`, submit it, and return `{"FINISHED"}`.
- `on_complete` runs on the **main thread** (via Blender's timer system), so it can safely call `bpy` APIs.
- Use `self.report({"INFO"}, ...)` to show status messages in Blender's status bar.

### Step 3 — Define the controller (`controller.py`)

The controller wires everything together and declares the panel layout using `FalControllerPanel`.

```python
from ..base import FalController
from ..ui import FalControllerPanel
from .operator import FalAudioOperator
from .props import FalAudioPropertyGroup

class FalAudioController(FalController):
    display_name = "Audio"
    description = "Generate audio using fal.ai"
    icon = "SPEAKER"
    operator_class = FalAudioOperator
    properties_class = FalAudioPropertyGroup
    panel_vse = FalControllerPanel(
        field_orders=[
            "mode",
            "tts_endpoint",
            "text",
        ],
        field_conditions={
            "tts_endpoint": lambda ctx, props: props.mode == "TTS",
            "text": lambda ctx, props: props.mode == "TTS",
        },
    )
```

| Attribute | Purpose |
|---|---|
| `display_name` | Name shown in the workflow selector dropdown |
| `description` | Tooltip text |
| `icon` | Blender icon identifier (e.g. `"SPEAKER"`, `"RENDER_RESULT"`, `"FILE_IMAGE"`) |
| `operator_class` | Your `FalOperator` subclass |
| `properties_class` | Your `PropertyGroup` subclass |
| `panel_3d` | Panel config for 3D Viewport sidebar (set `None` to skip) |
| `panel_vse` | Panel config for Video Sequence Editor sidebar (set `None` to skip) |

A controller can appear in one or both editor types. Set `panel_3d` for 3D Viewport workflows (like rendering) and `panel_vse` for timeline/sequence workflows (like audio generation).

### Step 4 — Export and register

```python
# controllers/your_controller/__init__.py
from .controller import FalYourController

__all__ = ["FalYourController"]
```

Then import it in `controllers/__init__.py`:

```python
from .your_controller import FalYourController
```

That's all. `FalController.register_all()` discovers it via `__subclasses__()` and handles panel creation, operator registration, and scene property binding.

## Panel Layout with `FalControllerPanel`

`FalControllerPanel` is a declarative UI configuration — you describe what to show and the framework draws it. No custom `draw()` method needed.

### `field_orders`

Controls the display order of properties. Properties not listed here are drawn after the listed ones, in their definition order.

```python
field_orders=["mode", "endpoint", "prompt", "width", "height", "seed"]
```

### `field_conditions`

Conditionally show/hide properties based on current state. Each value is a `(context, props) -> bool` callable.

```python
field_conditions={
    "endpoint": lambda ctx, props: props.mode == "DEPTH",
    "width": lambda ctx, props: not props.use_scene_resolution,
    "height": lambda ctx, props: not props.use_scene_resolution,
}
```

### `field_groupings`

Render multiple properties on the same row. Each set is a group that shares a horizontal row.

```python
field_groupings=[
    {"width", "height"},
]
```

### `field_separators`

Add visual spacing after specific properties.

```python
field_separators=["mode", "seed"]
```

### Complete example

```python
panel_3d = FalControllerPanel(
    field_orders=[
        "mode",
        "depth_endpoint",
        "sketch_endpoint",
        "prompt",
        "use_scene_resolution",
        "width",
        "height",
        "seed",
    ],
    field_conditions={
        "depth_endpoint": lambda ctx, props: props.mode == "DEPTH",
        "sketch_endpoint": lambda ctx, props: props.mode == "SKETCH",
        "width": lambda ctx, props: not props.use_scene_resolution,
        "height": lambda ctx, props: not props.use_scene_resolution,
    },
    field_groupings=[
        {"width", "height"},
    ],
)
```

## Complex Case: Modal Operator (Scene Render + API Call)

The render controller is a complex example — it modifies the scene, triggers a Blender render, waits for completion via a modal loop, then submits the result to fal.ai.

### Modal lifecycle

```
__call__(invoke=True)
    ├─ Cache all props (context may be stale in handlers)
    ├─ _setup_*()       ← modify scene for render
    ├─ bpy.ops.render.render("INVOKE_DEFAULT")
    ├─ Register render_complete / render_cancel handlers
    ├─ Start event timer + modal_handler_add
    └─ return {"RUNNING_MODAL"}

modal()
    ├─ Wait for TIMER events
    ├─ Check _render_done / _render_cancelled flags
    ├─ On done: _finish_*() → restore scene, submit FalJob
    └─ return {"FINISHED"} or {"CANCELLED"}
```

Key patterns in the render operator:

**Cache everything in `__call__`** — modal handlers and render callbacks may run in contexts where `props` or `context` are no longer valid:

```python
self._mode = props.mode
self._prompt = props.prompt
self._model = DEPTH_MODELS[props.depth_endpoint]
self._render_w, self._render_h = get_dimensions(context, props)
```

**Save and restore scene state** — any scene modifications must be undone after render, whether it succeeds or fails:

```python
self._saved["engine"] = scene.render.engine
scene.render.engine = "BLENDER_EEVEE_NEXT"
# ... in _restore_state():
if "engine" in s:
    scene.render.engine = s["engine"]
```

**Guard against overlapping runs** — use a class-level flag to prevent re-entry:

```python
_rendering: ClassVar[bool] = False

@classmethod
def enabled(cls, context, props) -> bool:
    if cls._rendering:
        return False
    # ...
```

**Module-level result handlers** — `on_complete` callbacks outlive the operator instance, so define them as module-level functions:

```python
def _handle_image_result(job: FalJob, render_w: int, render_h: int) -> None:
    if job.status == "error":
        print(f"Failed: {job.error}")
        return
    # Download and import...
```

## Working with `FalJob`

`FalJob` wraps asynchronous fal.ai API calls. Create one and submit it to `JobManager`:

```python
job = FalJob(
    endpoint=model.endpoint,
    arguments=params,             # dict sent to fal API
    on_complete=on_complete,      # called on main thread when done
    label="Short description",    # shown in the Jobs panel
)
JobManager.get().submit(job)
```

Inside `on_complete(job)`:
- `job.status` — `"complete"` or `"error"`
- `job.result` — the API response dict (on success)
- `job.error` — error message string (on failure)
- `job.request_id` — fal server request ID (for debugging)

For automatic file downloads, pass `download_keys`:

```python
job = FalJob(
    ...,
    download_keys=["model_mesh.url", "images.0.url"],
)
# After completion: job.downloaded_files["model_mesh.url"] → "/tmp/fal_xxx.glb"
```

## Disabling a Controller

Set `enabled = False` on the controller class. It will be skipped by `register_all()`.

```python
class FalExperimentalController(FalController):
    enabled = False
    # ...
```

## Checklist

- [ ] Create directory under `controllers/` with `__init__.py`, `controller.py`, `operator.py`, `props.py`
- [ ] Define a `PropertyGroup` with all user-facing settings
- [ ] Use `Model.enumerate()` for endpoint dropdowns, with `or [("NONE", ...)]` fallback
- [ ] Subclass `FalOperator` — implement `__call__`, `enabled`, and optionally `modal`
- [ ] Use `FalJob` + `JobManager` for API calls — never call fal.ai synchronously
- [ ] Define `on_complete` handlers at module level (not as methods on the operator)
- [ ] Subclass `FalController` — set `operator_class`, `properties_class`, and at least one of `panel_3d`/`panel_vse`
- [ ] Configure `FalControllerPanel` with `field_orders`, `field_conditions`, `field_groupings` as needed
- [ ] Export from `controllers/your_controller/__init__.py` and import in `controllers/__init__.py`
- [ ] If using modal operators: save/restore all scene state, guard against re-entry

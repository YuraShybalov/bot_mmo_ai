# PW AI Bot

Desktop bot prototype for Windows with:
- Tkinter GUI
- configurable attack timers
- game window capture through `pywin32`
- automatic vision monitoring on app launch
- YOLO categories for enemies, resources and other players
- live preview with bounding boxes
- basic HP/MP/Pet HP bar analysis from configurable screen regions

## Run

```bash
python main.py
```

## Install

```bash
pip install -r requirements.txt
```

## YOLO

When the app starts it immediately:
- binds to the configured game window
- captures frames
- runs YOLO if enabled
- updates the preview panel

The `Start Modes` button only enables the selected action modes from the UI:
- `Auto farm`
- `Gather resources`
- `Use pet mode`

Configure in `Settings`:
- `Enemy classes`
- `Resource classes`
- `Other bot classes`
- `Player HP ROI`
- `Player MP ROI`
- `Pet HP ROI`

## Preview and CV

- The `Bot` tab shows a live preview with YOLO boxes.
- `Player HP ROI`, `Player MP ROI` and `Pet HP ROI` accept `x,y,width,height`.
- ROI values can be fractions of the captured window (`0.05,0.05,0.25,0.03`) or absolute pixels.
- When HP/MP/Pet HP analysis is enabled, the bot can press the configured heal keys based on the detected fill percentage.

## Training Flow

- Use `Save current frame` in the `Training` tab to collect screenshots.
- Label those screenshots into classes like `enemy`, `resource`, `player`, `pet`.
- Train a custom YOLO model and point `Model path` to the exported `.pt`.

## Gameplay Object Training

- The gameplay dataset lives in `datasets/gameplay_objects/`.
- Classes are `enemy`, `resource`, `player` and `pet`.
- Because the controlled character is always in the screen center, do not label your own character.
- Label only objects around the character: mobs, resources, other players/bots and pets when they matter.
- Include screenshots from different camera angles, distances, UI states, combat effects, lighting and crowded scenes.
- Start training with `python scripts/train_gameplay_yolo.py`.
- After training, set the GUI model path to `runs/gameplay_objects/weights/best.pt`.
- In the GUI YOLO settings use `enemy` for enemy classes, `resource` for resource classes and `player` for bot/player classes.

## HUD Bar Training

- Added a starter dataset in [datasets/hud_bars/dataset.yaml](/d:/Projekt/bot_mmo_ai/datasets/hud_bars/dataset.yaml) for `hp_bar` and `mp_bar`.
- The reference image `ydyh.png` is included in `datasets/hud_bars/images/train/`.
- Its YOLO labels live in [ydyh.txt](/d:/Projekt/bot_mmo_ai/datasets/hud_bars/labels/train/ydyh.txt).
- Start training with `python scripts/train_hud_yolo.py`.
- For a usable model you still need many more labeled screenshots from real gameplay states: full HP, half HP, low HP, different MP levels, combat overlays, night/day scenes, UI scale changes.

---
name: gaze-follow-site
description: "This skill should be used when the user supplies a single photo or image (a real person, a pet, or an anime/illustrated character) and wants a static personal homepage in which the subject's head and gaze smoothly follow the mouse cursor with video-grade, stutter-free, ghost-free motion. It produces one self-contained index.html (zero external dependencies, double-click to run) by generating a short image-to-video gaze-loop clip from the uploaded image, extracting it into a sprite atlas, and rendering it on a canvas with mouse-direction interpolation. Trigger on requests such as building a personal site from a photo where the subject looks at the mouse, or any single-image gaze-follow homepage task."
agent_created: true
---

# Gaze-Follow Personal Site

## Overview

Generate a single-file, zero-dependency personal homepage from one uploaded image. The
subject (person / pet / anime character) appears in a portrait card and its head + eyes
smoothly track the mouse pointer in every direction (up/down/left/right and diagonals),
with **continuous video-like motion** — not discrete photo switching, not CSS transforms,
not WebGL displacement. When the pointer is still, the subject eases back to facing front
and then **stays completely still** (no auto motion).

The output `index.html` embeds the animation as a base64 sprite atlas, so it runs by
double-clicking with no server, no CDN, no fonts, no external assets.

## When to use

- User uploads exactly one image and asks for a personal/portrait site with a
  mouse-following gaze effect.
- The image subject may be: a real human face, a pet (cat/dog/etc.), or an anime /
  illustrated character. All three are supported; only the video prompt wording changes.
- Do **not** use this skill for: multi-photo galleries, non-gaze animations, or sites
  that need a backend. For those, build a normal site instead.

## Hard constraints (do not violate)

1. **Never** implement the follow with CSS `transform`/`transition`, WebGL pixel
   displacement, or crossfading a few discrete photos. All three were proven to produce
   stutter, "double-image" ghosts, or "switching-photo" feel. The ONLY working approach
   is **image-to-video → sprite atlas → canvas interpolation** (this skill's pipeline).
2. **Never** let the idle (pointer-still) state auto-animate. Returning to front and
   freezing is mandatory; any perpetual scan reads as "creepy/jittery" (鬼畜).
3. **Phase easing must use modulo N (frame count), never modulo 2π.** This is the single
   most common failure that causes perpetual twitching. See `references/pitfalls.md`.
4. Output must remain a **single self-contained HTML file** with the atlas inlined as
   base64. Keep it dependency-free.
5. Keep the included template and scripts byte-stable. Customize only copy text and the
   three calibration knobs; do not rewrite the player logic.

## Workflow

### Step 0 — Receive the image and classify the subject

Accept the uploaded image. If the file is not obviously a face/head/character (e.g., a
landscape with no subject), ask the user for a clearer portrait; otherwise proceed.
Classify subject as one of: `person`, `pet`, `anime`. This only changes the video prompt.

### Step 1 — Generate the gaze-loop video (image-to-video)

Use the environment's **image-to-video generation tool** (e.g. the `VideoGen` tool) with
the uploaded image as the **first/starting frame**. Required prompt properties:

- The subject performs ONE smooth, seamless, loopable head turn that sweeps a full circle
  of gaze: **right → down → left → up → back to the exact starting pose** (so frame 121 ≈
  frame 0 and the sprite atlas wraps with no seam).
- Keep identity, hairstyle/fur, clothing, and background **identical and unchanged**
  throughout. Explicitly name the real background if known (the original project used a
  "blurred night city street with warm bokeh lights" — adapt or just say "keep the
  background exactly as in the input image").
- Natural, subtle eye movement; no zoom; no camera movement.
- Duration ~5 s, any resolution (the model may upscale; that is fine).

Prompt template (fill `{subject}` / `{pronoun}` / `{background}`):

> The same {subject} slowly turns {pronoun} head to look around in a smooth, continuous,
> seamless loop — first looking to {pronoun} right, then down, then to {pronoun} left, then
> up, then back to facing the camera. Natural eye movement, no zoom, no camera movement.
> Keep {pronoun} face, hairstyle/fur, clothing, and the {background} completely unchanged
> and identical throughout.

- `person` → {subject}=young woman/man, {pronoun}=her/his, {background}=blurred night city
  street background with warm bokeh lights (or the actual background).
- `pet`    → {subject}=cat/dog, {pronoun}=its, {background}=the room/background from the photo.
- `anime`  → {subject}=character, {pronoun}=her/his, {background}=the original background.

Note: image-to-video costs roughly 50–100 credits for a 5 s clip. The model upscales
resolution automatically; accept it.

Save the video to a working directory, e.g. `work/video.mp4`.

### Step 2 — Build the sprite atlas

Run the bundled `scripts/make_atlas.py`. It probes the video, resamples to exactly **121
frames**, and tiles them into an **11×11 grid** of **256×370** cells → `atlas.jpg`. The
fixed geometry (COLS=11, ROWS=11, N=121, CELL=256, CELLH=370) MUST match the template
constants, so do not change cell size or grid elsewhere.

```bash
python scripts/make_atlas.py work/video.mp4 work/atlas.jpg
```

Requires `ffmpeg` on PATH. Verify the printed size equals 2816×4070 (11×11 × 256×370).

### Step 3 — Inline the atlas into the template

Copy `assets/index.template.html` into the working directory, then run
`scripts/build.py` to replace the `__ATLAS_B64__` placeholder with the base64 atlas and
write `index.html`.

```bash
cp assets/index.template.html work/index.template.html
python scripts/build.py --template work/index.template.html --atlas work/atlas.jpg --out work/index.html
```

### Step 4 — Verify (MANDATORY before delivery)

Run all three; do not skip.

1. **JS syntax** — extract the last inline script block from the template and run
   `node --check` on it. Must print no errors.
2. **Runtime smoke** — open `index.html` in headless Chrome
   (`--headless=new --no-sandbox --dump-dom --virtual-time-budget=3500`) and grep stderr
   for `Uncaught|TypeError|ReferenceError|is not defined|Cannot read`. Must be empty.
3. **Convergence simulation** — run the node snippet in `references/pitfalls.md`
   ("convergence test"). From rest, `tailMaxJump` must be `0` (fully still); a right→up
   sweep must have single-frame jump ≤ ~0.6 (smooth, no reverse jump).

### Step 5 — Visual / direction check (ask the user)

The only things only a human can judge: (a) does the subject still look like the original
(视频换脸一致性), and (b) does gaze direction match the pointer. If direction is wrong
(mirrored left/right or up/down), do **not** regenerate the video — just adjust the two
knobs in the template's player script:

- `ANGLE_OFFSET` (radians): rotate the whole gaze mapping if the loop order differs.
- `FLIP_Y` (true/false): flip vertical if up/down is reversed.

Re-run `build.py` after any knob change.

### Step 6 — Fill placeholder copy, then deliver

Replace these placeholders in `index.html` (search the template text) with the user's real
info, then deliver `index.html` (and optionally the `work/` folder) via `present_files`:

- `你的名字` (×4: title, brand, h1, footer) → the person's/site name.
- `一句话介绍你自己 —— …` (tagline) → one-line identity.
- The `.lead` opening paragraph → 2–3 sentence intro.
- About section `prose` (two paragraphs) → bio.
- Doing section three `.card` blocks → projects / learning / sharing.
- Contact: `hello@example.com`, `github.com/yourname`, `你的微信号` → real contacts.
- the page title and meta description tags → name + tagline.
- Footer line `人像特效：AI 视频逐帧 · 全方位视线跟随` → keep or localize.

If the user has not supplied copy, ship with placeholders and tell them what to replace.

## Calibration knobs (player script, in the template)

| Knob | Default | Meaning |
|------|---------|---------|
| `ANGLE_OFFSET` | `0` | Radians; rotate whole gaze→frame mapping if loop order mismatches. |
| `FLIP_Y` | `false` | Set `true` if up/down is reversed. |
| `SPAN_R` | `0.55` | Pointer distance (in portrait-widths) to reach full turn; smaller = more sensitive. |
| `EASE` | `0.14` | Phase easing; smaller = slower/smoother. |
| `IDLE_MS` | `2600` | Pointer-still ms before easing back to front and freezing. |

## Resources

- `assets/index.template.html` — the single-file site template. Contains the canvas player
  (sprite-atlas interpolation), the placeholder copy, and the `__ATLAS_B64__` slot. **Do
  not alter the player logic**; only edit copy and the knobs above.
- `scripts/make_atlas.py` — video → 11×11 sprite atlas (requires ffmpeg).
- `scripts/build.py` — inline atlas base64 into the template → `index.html`.
- `references/pitfalls.md` — the full list of failure modes and the exact convergence
  test snippet. Read it before debugging any motion/jitter issue.

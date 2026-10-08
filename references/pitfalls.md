# Gaze-Follow Site — Pitfalls & Verification

Detailed failure modes encountered while building this skill, and the exact fixes. Read
this before debugging any motion / jitter / ghosting issue. The pipeline that works is:
**image-to-video → sprite atlas (121 frames, 11×11, 256×370) → canvas interpolation**.

---

## 1. The twitch bug (CRITICAL — most likely failure)

**Symptom:** pointer is still, but the portrait keeps jittering / convulsing (抽搐). Mouse
not moving yet it still moves.

**Wrong code (causes it):**
```js
curPhase = norm2pi(curPhase + delta * EASE) % (Math.PI * 2);
curPhase = (curPhase / (Math.PI * 2)) * N;
```
`curPhase` is in **frame units (0..N=121)**, but `norm2pi` wraps at `2π ≈ 6.28` then
rescales by `N/2π`. The phase gets folded to wrong positions every frame, so the control
loop **never converges and oscillates** → canvas draws a different frame each tick → twitch.

**Correct code (use this):**
```js
var delta = tgtPhase - curPhase;
if (delta > N / 2) delta -= N; else if (delta < -N / 2) delta += N;  // shortest path on ring
if (Math.abs(delta) < 0.002) delta = 0;   // lock when settled -> no sub-pixel jitter
curPhase += delta * EASE;
curPhase = ((curPhase % N) + N) % N;        // MODULO N (frame count), never 2π
paint(curPhase);
```

**Rule:** phase is a frame index on a ring of size `N`. Always take modulo `N`. Never
convert to radians here.

---

## 2. Idle must freeze, not scan

**Symptom:** pointer still → subject slowly rotates in a circle forever (鬼畜 / creepy).

**Wrong:** an idle timer that advances a `scanPos` phase around the full ring.

**Correct:** after `IDLE_MS` of no pointer movement, set `tgtPhase = 0` (front) and ease
there, then stop. No perpetual motion. The template already does this.

---

## 3. Discrete photos / CSS transform / WebGL all fail

Do **not** fall back to these when "video feels too heavy":

- **Crossfading a few discrete head-turn photos** → the two frames have the head at
  different pixel positions, so alpha blending yields a *double-image ghost* in mid-states.
  Morph/light-field is the only real fix; the video approach already gives that for free.
- **CSS `transform: translate/rotate` + `transition`** on a single photo → reads as the
  whole picture sliding, not a head turn; also `transition` adds lag that feels like
  stutter.
- **WebGL fragment-shader pixel displacement** → on a real face the perspective looks
  "wrong/uncanny"; acceptable only for stylized art, not photos.

The video→atlas→canvas approach is the only one that yields genuine continuous motion.

---

## 4. Atlas geometry must match the template

Template constants: `COLS=11, ROWS=11, N=121, CELL=256, CELLH=370`.

- `make_atlas.py` forces `scale=256:370` and `tile=11x11`, so cells are exactly 256×370
  regardless of source aspect. Output must be **2816×4070**.
- If you change resolution, change `CELL`/`CELLH` in BOTH the template and `make_atlas.py`
  together, and keep `COLS*ROWS == N`. Mismatched geometry = shifted/wrong frames.
- The video must **loop seamlessly** (prompt it to return to the starting pose), otherwise
  frame 120 → frame 0 jumps at the wrap.

---

## 5. Seamless loop prompt

The image-to-video prompt MUST ask for a *smooth, continuous, seamless loop* ending in the
same pose it started (right → down → left → up → back to front). If not, the atlas wrap
(phase 120→0) shows a visible pop.

---

## 6. Headless Chrome mobile check quirk

`--window-size` has a **504 px minimum viewport width** in headless Chrome. Setting 414 or
300 still reports `innerWidth = 504`, and screenshots get cropped to the requested width —
this can falsely look like mobile overflow. To verify mobile layout, use
`--window-size=504,<h>` or CDP device emulation, and inject
`.rise{opacity:1!important;transition:none!important}` (headless `--virtual-time-budget`
does not advance CSS transitions, so `.rise` reveal elements freeze half-transparent).

---

## 7. Verification — convergence test (node)

Paste and run. Confirms the eased phase loop converges (no twitch) and is smooth.

```js
var N = 121, EASE = 0.14;
function step(cur, tgt) {
  var delta = tgt - cur;
  if (delta > N / 2) delta -= N; else if (delta < -N / 2) delta += N;
  if (Math.abs(delta) < 0.002) delta = 0;
  cur += delta * EASE;
  cur = ((cur % N) + N) % N;
  return cur;
}
function restTest(start) {
  var cur = start, hist = [];
  for (var i = 0; i < 400; i++) { cur = step(cur, 0); hist.push(+cur.toFixed(3)); }
  var tail = hist.slice(350), maxJump = 0;
  for (var i = 1; i < tail.length; i++) maxJump = Math.max(maxJump, Math.abs(tail[i] - tail[i - 1]));
  return { start: start, final: +cur.toFixed(3), tailMaxJump: maxJump };
}
[0, 1, 30, 60, 90, 120, 121.4].forEach(function (s) {
  console.log("rest from", s, "=>", JSON.stringify(restTest(s)));
});
var cur = 0, prev = 0, worst = 0;
for (var tgt = 0; tgt <= 90; tgt += 0.5) { cur = step(cur, tgt); worst = Math.max(worst, Math.abs(cur - prev)); prev = cur; }
console.log("sweep right->up: final", +cur.toFixed(2), "maxSingleFrameJump", +worst.toFixed(3));
```

Expected: every `rest from` line has `tailMaxJump:0` (fully still at rest); sweep
`maxSingleFrameJump` ≈ 0.5 (smooth, no reverse jump).

---

## 8. Verification — JS syntax & runtime smoke

- **Syntax:** extract the last `<script>...</script>` from the template and `node --check`.
- **Runtime:** headless Chrome `--dump-dom --virtual-time-budget=3500`; grep stderr for
  `Uncaught|TypeError|ReferenceError|is not defined|Cannot read` → must be empty.
- **Atlas content check (optional, Pillow):** adjacent atlas frames differ by ~1–7 luma
  (sub-perceptual → cross-fade invisible); opposite frames differ by ~26–71 (real gaze
  sweep, not a static image).

---

## 9. Direction calibration (no video re-gen needed)

If the subject looks the wrong way after build:

- Mirrored left/right or wrong rotational offset → adjust `ANGLE_OFFSET` (radians) in the
  template player script.
- Up/down reversed → set `FLIP_Y = true`.

Then re-run `build.py`. Do not regenerate the video for direction fixes.

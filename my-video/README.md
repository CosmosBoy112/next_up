# NextUp demo video

Product demo of NextUp, built with [Remotion](https://www.remotion.dev). Three compositions (1920×1080, 30 fps):

| Composition | What it is |
|---|---|
| `NextUpDemoVoice2` | **Main cut.** Narrated, ~1:42. Voice-over from `narration/generate_v2.py` (clips in `public/narration2/`). |
| `NextUpDemoVoice` | First narrated cut, ~1:36 (`narration/generate.py`, clips in `public/narration/`). |
| `NextUpDemo` | 90-second captions-only cut, built from `VIDEO_PROMPT.md`. |

```console
npm i
npx remotion studio                                                  # preview
npx remotion render NextUpDemoVoice2 out/nextup-demo-voice-v2.mp4    # render the main cut
```

The narrated cuts reuse the scenes in `src/scenes/`; after editing a scene, run `node src/voice/sync-scenes.mjs`. If Remotion's bundled Chrome fails to start on macOS, add `--browser-executable="/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"`.

The video follows the README demo script: Michael Brooks (from `scripts/seed.py`) cancels the Saturday Delivery Run, and Alice is the coordinator. Replacement candidates in the mockups are illustrative; the live agent picks from the seeded volunteers.

## Assets to drop into `public/`

Every file is optional. Without a screen recording, the scene shows an animated mockup of the NextUp UI instead, so the video always renders. In the Studio, a small chip on each mockup names the file that would replace it.

| File | Scene | Length |
|---|---|---|
| `michael.mp4` | 2 · Michael's volunteer calendar | 8 s |
| `alice.mp4` | 3 · Alice's coordinator calendar | 8 s |
| `scenario1.mp4` | 5 · Cancellation → proposal → approve → accept | 28 s |
| `scenario2.mp4` | 6 · "Need 2 more drivers…" request | 10 s |
| `scenario3.mp4` | 7 · Storm forecast → alternatives → crew notified | 12 s |
| `background.webp` | Backdrop behind every scene (included) | — |
| `voiceover.mp3` | Whole video, from 0:00 | 90 s |
| `music.mp3` | Whole video, looped at volume 0.15 | any |

Recordings play from their first frame and are cropped to 16:9 (`object-fit: cover`). Trim each one to its scene length. Callout badges are timed to the offsets in `VIDEO_PROMPT.md`, so match the recording to them.

## Layout

- `src/timing.ts`: scene lengths in seconds and asset filenames. Retime here.
- `src/scenes/`: one file per scene. Caption cues and callout times are at the bottom of each file.
- `src/ui/overlay.tsx`: captions, name tags, callouts, the browser frame, and the recording-or-mockup switch.
- `src/ui/app.tsx`, `src/ui/coordinator.tsx`: the UI mockups (calendar, side peek, proposal panel, weather panel, chat).

---

# Remotion video

<p align="center">
  <a href="https://github.com/remotion-dev/logo">
    <picture>
      <source media="(prefers-color-scheme: dark)" srcset="https://github.com/remotion-dev/logo/raw/main/animated-logo-banner-dark.apng">
      <img alt="Animated Remotion Logo" src="https://github.com/remotion-dev/logo/raw/main/animated-logo-banner-light.gif">
    </picture>
  </a>
</p>

Welcome to your Remotion project!

## Commands

**Install Dependencies**

```console
npm i --loglevel=error
```

**Start Preview**

```console
npm run dev
```

**Render video**

```console
npx remotion render
```

**Upgrade Remotion**

```console
npx remotion upgrade
```

## Docs

Get started with Remotion by reading the [fundamentals page](https://www.remotion.dev/docs/the-fundamentals).

## Help

We provide help on our [Discord server](https://discord.gg/6VzzNDwUwV).

## Issues

Found an issue with Remotion? [File an issue here](https://github.com/remotion-dev/remotion/issues/new).

## License

Note that for some entities a company license is needed. [Read the terms here](https://github.com/remotion-dev/remotion/blob/main/LICENSE.md).

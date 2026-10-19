// All scene timings live here. Edit seconds; frames are derived.
export const FPS = 30;
export const s = (seconds: number) => Math.round(seconds * FPS);

export const SCENES = {
  intro: 3,
  michael: 8,
  alice: 8,
  title: 3,
  scenario1: 28,
  scenario2: 10,
  scenario3: 12,
  results: 15,
  outro: 3,
} as const;

export const TOTAL_FRAMES = Object.values(SCENES).reduce((sum, sec) => sum + s(sec), 0);

// Screen recordings dropped into public/ replace the matching UI mockup.
export const RECORDINGS = {
  michael: "michael.mp4",
  alice: "alice.mp4",
  scenario1: "scenario1.mp4",
  scenario2: "scenario2.mp4",
  scenario3: "scenario3.mp4",
} as const;

export const BACKGROUND = "background.webp";
export const VOICEOVER = "voiceover.mp3";
export const MUSIC = "music.mp3";

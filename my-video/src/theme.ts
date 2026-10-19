import { loadFont } from "@remotion/google-fonts/NunitoSans";

export const { fontFamily } = loadFont("normal", {
  weights: ["400", "600", "700", "800"],
  subsets: ["latin"],
});

// Video chrome (from VIDEO_PROMPT.md).
export const brand = {
  primary: "#5b5ff0",
  text: "#1f2547",
  muted: "#5b6080",
  bg: "#f3f4fa",
  border: "#e4e7f2",
  white: "#ffffff",
  green: "#3a9a5b",
};

// The app's own palette (ui/floating.py, ui/schedule.py), used by the UI mockups.
export const app = {
  accent: "#5b5ff0",
  accentSoft: "#eceefe",
  ink: "#1f2547",
  muted: "#8a90a8",
  page: "#f1f3f9",
  line: "#e4e7f2",
  shadow: "0 12px 40px rgba(76,86,150,.08)",
  shadowLg: "0 24px 60px rgba(76,86,150,.16)",
};

// kind -> badge text, event background, event text, accent bar (ui/schedule.py KINDS)
export const KINDS = {
  open: { badgeBg: "#e1effa", badge: "#1f6f9e", bg: "#e4f3fb", text: "#1f6f9e", bar: "#3aa0d8" },
  filled: { badgeBg: "#e1f3e6", badge: "#3a7a4a", bg: "#e7f5eb", text: "#3a7a4a", bar: "#5aa469" },
  pending: { badgeBg: "#ece8fb", badge: "#4c32b0", bg: "#ece8fb", text: "#4c32b0", bar: "#6c4fd8" },
  recommended: { badgeBg: "#fde3e9", badge: "#b8405a", bg: "#fdecf0", text: "#b8405a", bar: "#e86a7f" },
  weather: { badgeBg: "#ffedd0", badge: "#94570a", bg: "#fff4e2", text: "#94570a", bar: "#f59e0b" },
  muted: { badgeBg: "#eceef3", badge: "#7b839a", bg: "#f2f3f7", text: "#7b839a", bar: "#c3c8d6" },
  severe: { badgeBg: "#fde2e2", badge: "#c0392b", bg: "#fdecec", text: "#c0392b", bar: "#e5484d" },
} as const;

export type Kind = keyof typeof KINDS;

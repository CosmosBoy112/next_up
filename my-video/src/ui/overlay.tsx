import React from "react";
import {
  AbsoluteFill,
  getRemotionEnvironment,
  getStaticFiles,
  Img,
  interpolate,
  OffthreadVideo,
  spring,
  staticFile,
  useCurrentFrame,
  useVideoConfig,
} from "remotion";
import { brand, fontFamily } from "../theme";
import { s } from "../timing";

export const clamp = { extrapolateLeft: "clamp", extrapolateRight: "clamp" } as const;

export const hasStatic = (name: string) => getStaticFiles().some((f) => f.name === name);

/** 0 → 1 spring that starts at `delay` frames; ~15 frames to settle. */
export const useEnter = (delay = 0) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  return spring({ frame: frame - delay, fps, config: { damping: 200 }, durationInFrames: 15 });
};

export const FadeSlide: React.FC<{
  delay?: number;
  dx?: number;
  dy?: number;
  style?: React.CSSProperties;
  children: React.ReactNode;
}> = ({ delay = 0, dx = 0, dy = 16, style, children }) => {
  const p = useEnter(delay);
  return (
    <div style={{ opacity: p, transform: `translate(${(1 - p) * dx}px, ${(1 - p) * dy}px)`, ...style }}>
      {children}
    </div>
  );
};

/** Scene background with a short fade-in and fade-out so cuts aren't harsh. */
export const SceneShell: React.FC<{ children: React.ReactNode; bg?: string }> = ({
  children,
  bg = "transparent",
}) => {
  const frame = useCurrentFrame();
  const { durationInFrames } = useVideoConfig();
  const opacity = interpolate(frame, [0, 8, durationInFrames - 8, durationInFrames], [0, 1, 1, 0], clamp);
  return (
    <AbsoluteFill style={{ fontFamily, color: brand.text }}>
      <AbsoluteFill style={{ opacity, background: bg }}>{children}</AbsoluteFill>
    </AbsoluteFill>
  );
};

/** Full-frame photo behind every scene, with a slow push-in and a soft tint for legibility. */
export const Background: React.FC<{ file: string }> = ({ file }) => {
  const frame = useCurrentFrame();
  const { durationInFrames } = useVideoConfig();
  const scale = interpolate(frame, [0, durationInFrames], [1.02, 1.12]);
  return (
    <AbsoluteFill style={{ background: brand.text }}>
      {hasStatic(file) && (
        <Img src={staticFile(file)} style={{ width: "100%", height: "100%", objectFit: "cover", transform: `scale(${scale})` }} />
      )}
      <AbsoluteFill style={{ background: "linear-gradient(180deg, rgba(31,37,71,.18) 0%, rgba(31,37,71,.42) 100%)" }} />
    </AbsoluteFill>
  );
};

// ---------- captions ----------

export type CaptionCue = [atSeconds: number, text: string];

/** Bottom-center caption pill; shows the latest cue whose time has passed. */
export const Captions: React.FC<{ cues: CaptionCue[] }> = ({ cues }) => {
  const frame = useCurrentFrame();
  const idx = cues.reduce((acc, [at], i) => (frame >= s(at) ? i : acc), -1);
  if (idx < 0) return null;
  const [at, text] = cues[idx];
  const local = frame - s(at);
  const opacity = interpolate(local, [0, 6], [0, 1], clamp);
  return (
    <AbsoluteFill style={{ justifyContent: "flex-end", alignItems: "center", paddingBottom: 34, pointerEvents: "none" }}>
      <div
        style={{
          opacity,
          maxWidth: 1500,
          padding: "14px 30px",
          borderRadius: 999,
          background: "rgba(31,37,71,0.85)",
          color: "#fff",
          fontSize: 30,
          fontWeight: 600,
          lineHeight: 1.3,
          textAlign: "center",
        }}
      >
        {text}
      </div>
    </AbsoluteFill>
  );
};

// ---------- labels and callouts ----------

export const NameTag: React.FC<{ name: string; role: string; delay?: number }> = ({ name, role, delay = 10 }) => {
  const p = useEnter(delay);
  return (
    <div
      style={{
        position: "absolute",
        left: 48,
        top: 36,
        opacity: p,
        transform: `translateX(${(1 - p) * -40}px)`,
        display: "flex",
        alignItems: "center",
        gap: 14,
        padding: "12px 24px 12px 14px",
        background: "#fff",
        border: `1px solid ${brand.border}`,
        borderRadius: 999,
        boxShadow: "0 12px 30px rgba(31,37,71,.14)",
        zIndex: 10,
      }}
    >
      <div
        style={{
          width: 44,
          height: 44,
          borderRadius: 999,
          background: brand.primary,
          color: "#fff",
          display: "grid",
          placeItems: "center",
          fontSize: 22,
          fontWeight: 800,
        }}
      >
        {name[0]}
      </div>
      <div style={{ fontSize: 28 }}>
        <b>{name}</b>
        <span style={{ color: brand.muted }}> · {role}</span>
      </div>
    </div>
  );
};

export const ChapterLabel: React.FC<{ text: string }> = ({ text }) => {
  const p = useEnter(4);
  return (
    <div
      style={{
        position: "absolute",
        left: 48,
        top: 36,
        opacity: p,
        transform: `translateX(${(1 - p) * -40}px)`,
        padding: "10px 24px",
        background: brand.primary,
        color: "#fff",
        borderRadius: 999,
        fontSize: 26,
        fontWeight: 800,
        letterSpacing: 0.3,
        boxShadow: "0 10px 26px rgba(91,95,240,.35)",
        zIndex: 10,
      }}
    >
      {text}
    </div>
  );
};

type CalloutTone = "default" | "green" | "subtle";

/** A badge that springs in at `at` seconds and, if `until` is set, fades out then. */
export const Callout: React.FC<{
  at: number;
  until?: number;
  tone?: CalloutTone;
  small?: boolean;
  style?: React.CSSProperties;
  children: React.ReactNode;
}> = ({ at, until, tone = "default", small, style, children }) => {
  const frame = useCurrentFrame();
  const p = useEnter(s(at));
  const out = until === undefined ? 1 : interpolate(frame, [s(until) - 6, s(until)], [1, 0], clamp);
  if (frame < s(at) || (until !== undefined && frame >= s(until))) return null;
  const colors = {
    default: { bg: "#fff", fg: brand.text, border: brand.border },
    green: { bg: brand.green, fg: "#fff", border: brand.green },
    subtle: { bg: brand.text, fg: "#fff", border: brand.text },
  }[tone];
  return (
    <div
      style={{
        opacity: p * out,
        transform: `scale(${0.9 + 0.1 * p})`,
        transformOrigin: "right center",
        padding: small ? "8px 18px" : "12px 26px",
        fontSize: small ? 22 : 28,
        fontWeight: 800,
        borderRadius: 14,
        background: colors.bg,
        color: colors.fg,
        border: `2px solid ${colors.border}`,
        boxShadow: "0 14px 36px rgba(31,37,71,.18)",
        whiteSpace: "nowrap",
        ...style,
      }}
    >
      {children}
    </div>
  );
};

/** Column of callouts pinned to the right edge of the browser frame. */
export const CalloutStack: React.FC<{ top?: number; children: React.ReactNode }> = ({ top = 170, children }) => (
  <div
    style={{
      position: "absolute",
      right: 40,
      top,
      display: "flex",
      flexDirection: "column",
      alignItems: "flex-end",
      gap: 14,
      zIndex: 10,
    }}
  >
    {children}
  </div>
);

// ---------- browser frame ----------

export const SCREEN_W = 1440;
export const SCREEN_H = 810;

export const BrowserFrame: React.FC<{ url?: string; children: React.ReactNode }> = ({
  url = "nextup.app",
  children,
}) => {
  const p = useEnter(0);
  return (
    <AbsoluteFill style={{ alignItems: "center", paddingTop: 108 }}>
      <div
        style={{
          opacity: p,
          transform: `translateY(${(1 - p) * 24}px)`,
          borderRadius: 18,
          overflow: "hidden",
          background: "#fff",
          border: `1px solid ${brand.border}`,
          boxShadow: "0 30px 80px rgba(31,37,71,.18)",
        }}
      >
        <div
          style={{
            height: 40,
            display: "flex",
            alignItems: "center",
            gap: 8,
            padding: "0 16px",
            background: "#f7f8fc",
            borderBottom: `1px solid ${brand.border}`,
          }}
        >
          {["#ff5f57", "#febc2e", "#28c840"].map((c) => (
            <div key={c} style={{ width: 12, height: 12, borderRadius: 99, background: c }} />
          ))}
          <div
            style={{
              marginLeft: 18,
              padding: "4px 18px",
              borderRadius: 8,
              background: "#fff",
              border: `1px solid ${brand.border}`,
              fontSize: 15,
              color: brand.muted,
              width: 420,
            }}
          >
            {url}
          </div>
        </div>
        <div style={{ width: SCREEN_W, height: SCREEN_H, position: "relative", overflow: "hidden" }}>
          {children}
        </div>
      </div>
    </AbsoluteFill>
  );
};

/**
 * Plays public/<file> if it exists. Otherwise renders the animated UI mockup, so the video
 * still shows the product. In the Studio, a small chip says which file would replace it.
 */
export const Screen: React.FC<{ file: string; url?: string; children: React.ReactNode }> = ({
  file,
  url,
  children,
}) => {
  const present = hasStatic(file);
  return (
    <BrowserFrame url={url}>
      {present ? (
        <OffthreadVideo src={staticFile(file)} muted style={{ width: "100%", height: "100%", objectFit: "cover" }} />
      ) : (
        <>
          {children}
          {getRemotionEnvironment().isStudio && (
            <div
              style={{
                position: "absolute",
                left: 12,
                bottom: 12,
                padding: "4px 12px",
                borderRadius: 8,
                background: "rgba(31,37,71,.75)",
                color: "#fff",
                fontSize: 14,
                fontFamily,
                zIndex: 50,
              }}
            >
              Mockup · drop public/{file} to replace
            </div>
          )}
        </>
      )}
    </BrowserFrame>
  );
};

// ---------- logo ----------

export const LogoIcon: React.FC<{ size: number }> = ({ size }) => (
  <div
    style={{
      width: size,
      height: size,
      borderRadius: size * 0.3,
      background: `linear-gradient(140deg, #7b7ff6, ${brand.primary})`,
      boxShadow: `0 ${size * 0.2}px ${size * 0.45}px rgba(91,95,240,.35)`,
      display: "grid",
      placeItems: "center",
      flexShrink: 0,
    }}
  >
    <svg width={size * 0.58} height={size * 0.58} viewBox="0 0 24 24" fill="none" stroke="#fff" strokeWidth={2.6} strokeLinecap="round" strokeLinejoin="round">
      <path d="M6 13l6-6 6 6" />
      <path d="M6 19l6-6 6 6" opacity={0.55} />
    </svg>
  </div>
);

export const Logo: React.FC<{ size: number; color?: string }> = ({ size, color = brand.text }) => (
  <div style={{ display: "flex", alignItems: "center", gap: size * 0.32 }}>
    <LogoIcon size={size} />
    <span style={{ fontSize: size * 0.82, fontWeight: 800, letterSpacing: -size * 0.02, color }}>NextUp</span>
  </div>
);

import React from "react";
import { AbsoluteFill } from "remotion";
import { FadeSlide, Logo, SceneShell, useEnter } from "../ui/overlay";

// Scene 1: logo + tagline. The tagline is the on-screen caption.
export const Intro: React.FC = () => {
  const p = useEnter(0);
  return (
    <SceneShell>
      <AbsoluteFill style={{ alignItems: "center", justifyContent: "center", gap: 34 }}>
        <div style={{ opacity: p, transform: `scale(${0.85 + 0.15 * p})` }}>
          <Logo size={140} color="#fff" />
        </div>
        <FadeSlide delay={14} style={{ fontSize: 52, fontWeight: 700, color: "#fff", textShadow: "0 4px 24px rgba(31,37,71,.5)" }}>
          Your volunteers, covered.
        </FadeSlide>
      </AbsoluteFill>
    </SceneShell>
  );
};

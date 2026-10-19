import React from "react";
import { AbsoluteFill } from "remotion";
import { FadeSlide, SceneShell } from "../ui/overlay";

// Scene 4: the principle, on the primary color. The title is the on-screen caption.
export const TitleCard: React.FC = () => (
  <SceneShell bg="rgba(91,95,240,.78)">
    <AbsoluteFill style={{ alignItems: "center", justifyContent: "center", color: "#fff", textAlign: "center" }}>
      <FadeSlide delay={4} style={{ fontSize: 84, fontWeight: 800, letterSpacing: -1.5, lineHeight: 1.15 }}>
        The agent proposes.
      </FadeSlide>
      <FadeSlide delay={16} style={{ fontSize: 84, fontWeight: 800, letterSpacing: -1.5, lineHeight: 1.15 }}>
        The coordinator decides.
      </FadeSlide>
    </AbsoluteFill>
  </SceneShell>
);

import React, { createContext, useContext } from "react";
import { interpolate, useCurrentFrame } from "remotion";
import { s } from "../timing";
import { Captions as BaseCaptions, clamp, type CaptionCue } from "../ui/overlay";
import type { NarrationCue } from "./narration";

// Same look as ../ui/overlay. Only Captions changes: it follows the narration timing.
export * from "../ui/overlay";

/** The narration cues for the current scene; Captions reads these instead of its own props. */
export const NarrationContext = createContext<NarrationCue[] | null>(null);

/** The original caption pill, shown while its line is spoken. */
export const Captions: React.FC<{ cues: CaptionCue[] }> = ({ cues }) => {
  const narration = useContext(NarrationContext);
  const frame = useCurrentFrame();
  if (!narration) return <BaseCaptions cues={cues} />;
  const idx = narration.reduce((acc, c, i) => (frame >= s(c.at) ? i : acc), -1);
  if (idx < 0) return null;
  const cue = narration[idx];
  const end = s(cue.at + cue.dur) + 15;
  const next = narration[idx + 1];
  if (frame > end && (!next || frame < s(next.at))) return null;
  const opacity = interpolate(frame - s(cue.at), [0, 6], [0, 1], clamp) * interpolate(frame, [end - 6, end], [1, 0], clamp);
  return (
    <div style={{ opacity }}>
      <BaseCaptions cues={[[cue.at, cue.text]]} />
    </div>
  );
};

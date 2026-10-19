import React from "react";
import { AbsoluteFill, Html5Audio, Sequence, Series, staticFile } from "remotion";
import { BACKGROUND, MUSIC, s } from "../timing";
import { NARRATION } from "./narration";
import { Background, hasStatic, NarrationContext } from "./overlay";
import { Alice } from "./scenes/Alice";
import { Intro } from "./scenes/Intro";
import { Michael } from "./scenes/Michael";
import { Outro } from "./scenes/Outro";
import { Results } from "./scenes/Results";
import { Scenario1 } from "./scenes/Scenario1";
import { Scenario2 } from "./scenes/Scenario2";
import { Scenario3 } from "./scenes/Scenario3";
import { TitleCard } from "./scenes/TitleCard";

// Narrated cut of the demo, same look as NextUpDemo. Scene lengths and voice timing come from
// narration.ts (narration/generate.py); scene content is synced from src/scenes.
const SCENE_COMPONENTS: Record<string, React.FC> = {
  intro: Intro,
  michael: Michael,
  alice: Alice,
  title: TitleCard,
  scenario1: Scenario1,
  scenario2: Scenario2,
  scenario3: Scenario3,
  results: Results,
  outro: Outro,
};

export const VOICE_TOTAL_FRAMES = NARRATION.reduce((sum, sc) => sum + s(sc.seconds), 0);

export const NextUpDemoVoice: React.FC = () => (
  <AbsoluteFill>
    <Background file={BACKGROUND} />
    <Series>
      {NARRATION.map(({ id, seconds, cues }) => {
        const Scene = SCENE_COMPONENTS[id];
        return (
          <Series.Sequence key={id} durationInFrames={s(seconds)} name={id}>
            <NarrationContext.Provider value={cues}>
              <Scene />
            </NarrationContext.Provider>
            {cues.map((c) => (
              <Sequence key={c.file} from={s(c.at)} durationInFrames={s(c.dur) + 3} name={c.text} layout="none">
                <Html5Audio src={staticFile(c.file)} />
              </Sequence>
            ))}
          </Series.Sequence>
        );
      })}
    </Series>
    {hasStatic(MUSIC) && <Html5Audio src={staticFile(MUSIC)} volume={0.08} loop />}
  </AbsoluteFill>
);

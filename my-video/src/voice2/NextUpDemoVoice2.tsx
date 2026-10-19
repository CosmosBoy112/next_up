import React from "react";
import { AbsoluteFill, Html5Audio, Sequence, Series, staticFile } from "remotion";
import { BACKGROUND, MUSIC, s } from "../timing";
import { Background, hasStatic, NarrationContext } from "../voice/overlay";
import { Alice } from "../voice/scenes/Alice";
import { Intro } from "../voice/scenes/Intro";
import { Michael } from "../voice/scenes/Michael";
import { Outro } from "../voice/scenes/Outro";
import { Results } from "../voice/scenes/Results";
import { Scenario1 } from "../voice/scenes/Scenario1";
import { Scenario2 } from "../voice/scenes/Scenario2";
import { Scenario3 } from "../voice/scenes/Scenario3";
import { TitleCard } from "../voice/scenes/TitleCard";
import { NARRATION } from "./narration";

// Second narrated cut, to compare with NextUpDemoVoice. Same scenes; only the voice-over
// (narration/generate_v2.py) and the scene lengths it implies differ.
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

export const VOICE2_TOTAL_FRAMES = NARRATION.reduce((sum, sc) => sum + s(sc.seconds), 0);

export const NextUpDemoVoice2: React.FC = () => (
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

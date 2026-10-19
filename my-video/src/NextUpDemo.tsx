import React from "react";
import { AbsoluteFill, Html5Audio, Series, staticFile } from "remotion";
import { Alice } from "./scenes/Alice";
import { Intro } from "./scenes/Intro";
import { Michael } from "./scenes/Michael";
import { Outro } from "./scenes/Outro";
import { Results } from "./scenes/Results";
import { Scenario1 } from "./scenes/Scenario1";
import { Scenario2 } from "./scenes/Scenario2";
import { Scenario3 } from "./scenes/Scenario3";
import { TitleCard } from "./scenes/TitleCard";
import { BACKGROUND, MUSIC, s, SCENES, VOICEOVER } from "./timing";
import { Background, hasStatic } from "./ui/overlay";

export const NextUpDemo: React.FC = () => (
  <AbsoluteFill>
    <Background file={BACKGROUND} />
    <Series>
      <Series.Sequence durationInFrames={s(SCENES.intro)}>
        <Intro />
      </Series.Sequence>
      <Series.Sequence durationInFrames={s(SCENES.michael)}>
        <Michael />
      </Series.Sequence>
      <Series.Sequence durationInFrames={s(SCENES.alice)}>
        <Alice />
      </Series.Sequence>
      <Series.Sequence durationInFrames={s(SCENES.title)}>
        <TitleCard />
      </Series.Sequence>
      <Series.Sequence durationInFrames={s(SCENES.scenario1)}>
        <Scenario1 />
      </Series.Sequence>
      <Series.Sequence durationInFrames={s(SCENES.scenario2)}>
        <Scenario2 />
      </Series.Sequence>
      <Series.Sequence durationInFrames={s(SCENES.scenario3)}>
        <Scenario3 />
      </Series.Sequence>
      <Series.Sequence durationInFrames={s(SCENES.results)}>
        <Results />
      </Series.Sequence>
      <Series.Sequence durationInFrames={s(SCENES.outro)}>
        <Outro />
      </Series.Sequence>
    </Series>
    {hasStatic(VOICEOVER) && <Html5Audio src={staticFile(VOICEOVER)} />}
    {hasStatic(MUSIC) && <Html5Audio src={staticFile(MUSIC)} volume={0.15} loop />}
  </AbsoluteFill>
);

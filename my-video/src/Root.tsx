import { Composition } from "remotion";
import { NextUpDemoVoice, VOICE_TOTAL_FRAMES } from "./voice/NextUpDemoVoice";
import { NextUpDemoVoice2, VOICE2_TOTAL_FRAMES } from "./voice2/NextUpDemoVoice2";
import { NextUpDemo } from "./NextUpDemo";
import { FPS, TOTAL_FRAMES } from "./timing";

export const RemotionRoot: React.FC = () => {
  return (
    <>
      <Composition
        id="NextUpDemo"
        component={NextUpDemo}
        durationInFrames={TOTAL_FRAMES}
        fps={FPS}
        width={1920}
        height={1080}
      />
      <Composition
        id="NextUpDemoVoice"
        component={NextUpDemoVoice}
        durationInFrames={VOICE_TOTAL_FRAMES}
        fps={FPS}
        width={1920}
        height={1080}
      />
      <Composition
        id="NextUpDemoVoice2"
        component={NextUpDemoVoice2}
        durationInFrames={VOICE2_TOTAL_FRAMES}
        fps={FPS}
        width={1920}
        height={1080}
      />
    </>
  );
};

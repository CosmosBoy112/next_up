import React from "react";
import { useCurrentFrame } from "remotion";
import { RECORDINGS } from "../timing";
import {
  AppShell,
  Btn,
  Caption,
  Cursor,
  eventCenter,
  MICHAEL_ACCOUNT,
  michaelEvents,
  michaelGroups,
  PeekTop,
  shiftById,
  ShiftHeader,
  SidePanel,
  VOL_LEGEND,
  WeekCalendar,
} from "../ui/app";
import { Captions, NameTag, SceneShell, Screen } from "../ui/overlay";

// Scene 2: the volunteer's calendar. Michael opens his Saturday shift.
const CLICK = 75;

const MichaelMock: React.FC = () => {
  const delivery = shiftById("delivery");
  const target = eventCenter(delivery);
  const frame = useCurrentFrame();
  return (
    <AppShell account={MICHAEL_ACCOUNT} groups={michaelGroups()}>
      <WeekCalendar events={michaelEvents()} legend={VOL_LEGEND} />
      {frame >= CLICK && (
        <SidePanel delay={CLICK + 2}>
          <PeekTop />
          <ShiftHeader sh={delivery} label="you're signed up" kind="filled" place="Departs Pantry Warehouse, 12 Mill St" />
          <Caption style={{ marginTop: 10 }}>
            Drive the pantry van to deliver grocery boxes to families across the valley; lift boxes up to 40 lbs. · Needs: driving,
            heavy lifting
          </Caption>
          <div style={{ marginTop: 14 }}>
            <Btn>Cancel this shift</Btn>
          </div>
        </SidePanel>
      )}
      <Cursor path={[[0, 640, 600], [20, 640, 600], [CLICK - 4, target.x - 286, target.y]]} clicks={[CLICK]} />
    </AppShell>
  );
};

export const Michael: React.FC = () => (
  <SceneShell>
    <Screen file={RECORDINGS.michael}>
      <MichaelMock />
    </Screen>
    <NameTag name="Michael" role="Volunteer" />
    <Captions
      cues={[
        [0.2, "Hey, this is Michael. He volunteers for Valley Community Pantry's Saturday delivery run."],
        [4.4, "Cancelling used to mean a guilty group text, and hoping someone sees it."],
      ]}
    />
  </SceneShell>
);

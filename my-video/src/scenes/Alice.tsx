import React from "react";
import { useCurrentFrame } from "remotion";
import { RECORDINGS } from "../timing";
import {
  AppShell,
  Btn,
  Caption,
  COORD_ACCOUNT,
  COORD_LEGEND,
  coordEvents,
  coordGroups,
  Cursor,
  eventCenter,
  Fab,
  Icon,
  PeekTop,
  shiftById,
  ShiftHeader,
  SidePanel,
  WeekCalendar,
} from "../ui/app";
import { Captions, NameTag, SceneShell, Screen } from "../ui/overlay";

// Scene 3: the coordinator's calendar. Alice checks a shift that still needs people.
const CLICK = 95;

const AliceMock: React.FC = () => {
  const frame = useCurrentFrame();
  const dinner = shiftById("dinner");
  const target = eventCenter(dinner);
  const events = coordEvents();
  return (
    <AppShell account={COORD_ACCOUNT} groups={coordGroups(events, frame >= CLICK ? "dinner" : undefined)}>
      <WeekCalendar events={events} legend={COORD_LEGEND} />
      {frame >= CLICK && (
        <SidePanel delay={CLICK + 2} bottom={96}>
          <PeekTop />
          <ShiftHeader sh={dinner} label="open" kind="open" place="Grace Hall, 40 Oak Ave" date="Thursday, Oct 15" />
          <Caption style={{ marginTop: 10 }}>Crew: Dana K., Luis M., Ana R., Tom B. · Needs: food handling, event setup</Caption>
          <div style={{ marginTop: 14 }}>
            <Btn>
              <Icon name="search" size={15} /> Find volunteers (2 open)
            </Btn>
          </div>
        </SidePanel>
      )}
      <Fab />
      <Cursor path={[[0, 300, 260], [24, 300, 260], [CLICK - 4, target.x - 286, target.y]]} clicks={[CLICK]} />
    </AppShell>
  );
};

export const Alice: React.FC = () => (
  <SceneShell>
    <Screen file={RECORDINGS.alice}>
      <AliceMock />
    </Screen>
    <NameTag name="Alice" role="Event Coordinator" />
    <Captions
      cues={[
        [0.2, "And this is Alice, the event coordinator."],
        [2.6, "Every cancellation meant spreadsheets, a dozen texts,"],
        [5.2, "and asking the same reliable people until they burned out."],
      ]}
    />
  </SceneShell>
);

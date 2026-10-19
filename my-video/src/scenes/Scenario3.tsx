import React from "react";
import { Sequence, useCurrentFrame } from "remotion";
import { RECORDINGS, s } from "../timing";
import {
  AppShell,
  COORD_ACCOUNT,
  COORD_LEGEND,
  coordEvents,
  coordGroups,
  Cursor,
  eventCenter,
  Fab,
  pressed,
  shiftById,
  SidePanel,
  Toast,
  WeekCalendar,
} from "../ui/app";
import { Alternative, ProposalHeader, ShiftPage, WeatherCard } from "../ui/coordinator";
import { Callout, CalloutStack, Captions, ChapterLabel, SceneShell, Screen } from "../ui/overlay";

// Scene 7 (12 s): a storm is forecast for an outdoor shift.
const PAGE_AT = 3.5;
const popup = shiftById("popup");
const PLACE = "Riverside Park Pavilion";

const ALTERNATIVES: Alternative[] = [
  {
    title: "Reschedule to Sunday, Oct 18",
    details: "Same time; the forecast is clear. Crew asked to confirm.",
    notice: "Hi all! A severe thunderstorm is forecast for Saturday, so we're moving the pop-up to Sunday, Oct 18, same time. Please confirm you can make it.",
  },
  {
    title: "Move indoors to Valley Community Center",
    details: "Same day and time, out of the storm.",
    notice: "Hi all! A severe thunderstorm is forecast for Saturday, so the pop-up moves indoors to Valley Community Center, same time (2–5 PM). See you there!",
  },
  {
    title: "Switch to a 1-hour drive-through pickup",
    details: "Pre-packed boxes handed out from the van, 2–3 PM.",
    notice: "Hi all! Because of Saturday's storm forecast, we'll run a short drive-through pickup from the van, 2–3 PM. Thanks for staying flexible!",
  },
];

const CalendarScreen: React.FC = () => {
  const ALERT = 18;
  const CLICK = 82;
  const frame = useCurrentFrame();
  const target = eventCenter(popup);
  const events = coordEvents({
    delivery: { conf: 3 },
    popup: frame >= ALERT ? { kind: "weather", pulseAt: ALERT } : {},
  });
  return (
    <AppShell account={COORD_ACCOUNT} groups={coordGroups(events)}>
      <WeekCalendar events={events} legend={COORD_LEGEND} />
      <Fab />
      <Cursor path={[[0, 640, 560], [30, 640, 560], [CLICK - 4, target.x - 286, target.y]]} clicks={[CLICK]} />
    </AppShell>
  );
};

const PageScreen: React.FC = () => {
  const frame = useCurrentFrame();
  const PICK = s(6.5 - PAGE_AT);
  const APPROVE = s(9 - PAGE_AT);
  const pick = frame >= PICK ? 1 : 0;
  const approved = frame >= APPROVE + 8;
  const events = coordEvents({ popup: { kind: approved ? "filled" : "weather" } });
  return (
    <AppShell account={COORD_ACCOUNT} groups={coordGroups(events, "popup")} calendarActive={false}>
      <ShiftPage
        sh={popup}
        label={approved ? "filled" : "weather alert"}
        kind={approved ? "filled" : "weather"}
        place={PLACE}
        skills="event setup, food handling"
        about="Set up tents and hand out groceries at a pop-up distribution in the park."
        roster={[
          ["Ana Ruiz", "event setup", "", "Self sign-up"],
          ["Tom Baker", "food handling", "Yes", "Self sign-up"],
          ["Sara Ito", "event setup, food handling", "", "Coordinator request"],
        ]}
        extraProps={approved ? [["Weather plan", <span key="p"><b>{ALTERNATIVES[1].title}</b> · {ALTERNATIVES[1].details}</span>]] : []}
        width={approved ? 1060 : 600}
      />
      {!approved && (
        <SidePanel delay={4} width={490}>
          <ProposalHeader />
          <WeatherCard alternatives={ALTERNATIVES} pick={pick} crew={popup.conf} delay={8} approvePressed={pressed(frame, APPROVE)} />
        </SidePanel>
      )}
      <Toast at={APPROVE + 8} text={`Plan set: ${ALTERNATIVES[1].title}. Notified ${popup.conf} volunteer(s).`} />
      <Cursor
        path={[
          [0, 520, 600],
          [PICK - 26, 520, 600],
          [PICK - 4, 693, 371],
          [APPROVE - 24, 693, 371],
          [APPROVE - 4, 783, 594],
        ]}
        clicks={[PICK, APPROVE]}
        hideAfter={APPROVE + 30}
      />
    </AppShell>
  );
};

export const Scenario3: React.FC = () => (
  <SceneShell>
    <Screen file={RECORDINGS.scenario3}>
      <Sequence durationInFrames={s(PAGE_AT)}>
        <CalendarScreen />
      </Sequence>
      <Sequence from={s(PAGE_AT)}>
        <PageScreen />
      </Sequence>
    </Screen>
    <ChapterLabel text="3 · Weather" />
    <CalloutStack top={780}>
      <Callout at={0.6} until={4.3}>⛈ Storm forecast Sat</Callout>
      <Callout at={4.5} until={9.2}>Alternatives proposed</Callout>
      <Callout at={9.3} tone="green">Crew notified ✓</Callout>
    </CalloutStack>
    <Captions
      cues={[
        [0, "It watches the forecast too. A storm on Saturday?"],
        [4, "The agent proposes alternatives, Alice picks one,"],
        [8.5, "and the whole crew is notified."],
      ]}
    />
  </SceneShell>
);

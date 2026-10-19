import React from "react";
import { interpolate, Sequence, useCurrentFrame, Easing } from "remotion";
import { app } from "../theme";
import { RECORDINGS, s } from "../timing";
import {
  AppShell,
  Btn,
  Caption,
  COORD_ACCOUNT,
  COORD_LEGEND,
  coordEvents,
  coordGroups,
  Cursor,
  Fab,
  MICHAEL_ACCOUNT,
  michaelEvents,
  michaelGroups,
  PeekTop,
  pressed,
  shiftById,
  ShiftHeader,
  SidePanel,
  Toast,
  VOL_LEGEND,
  WeekCalendar,
} from "../ui/app";
import { VolunteerRequestScreen } from "../ui/volunteer";
import { ApprovalCard, Candidate, LogEntry, ProposalHeader, RequestsSent, RunLog, ShiftPage } from "../ui/coordinator";
import { Callout, CalloutStack, Captions, ChapterLabel, clamp, SceneShell, Screen, useEnter } from "../ui/overlay";

// Scene 5 (28 s). Sub-screens, in scene seconds:
//   0–5.5   Michael cancels from the side peek
//   5.5–8   Alice's calendar: the slot opens, then a proposal lands
//   8–25    Shift page with the agent's proposal, its Why? log, and approval
//   25–27.3 Jordan accepts the request on his volunteer page
//   27.3–28 Calendar: the shift is filled
const T = { cancel: 0, calendar: 5.5, page: 8, respond: 25, filled: 27.3, end: 28 };

const delivery = shiftById("delivery");
const PLACE = "Departs Pantry Warehouse, 12 Mill St";

const CANDIDATES: Candidate[] = [
  {
    rank: 1,
    name: "Jordan Lee",
    hours: 2,
    selected: true,
    reasons: ["Free all Saturday morning and can drive", "Only 2 h in the last 28 days: least busy of the good fits"],
    draft: "Hi Jordan! A spot opened on Saturday's delivery run (10 AM–1 PM). You're free and can drive. Could you help out?",
  },
  {
    rank: 2,
    name: "Priya Natarajan",
    hours: 18,
    selected: true,
    reasons: ["Free Saturday, can drive and lift boxes", "18 h in the last 28 days, so ranked below Jordan"],
    draft: "Hi Priya! We need one more driver for Saturday's delivery run, 10 AM–1 PM. Would you be up for it?",
  },
  {
    rank: 3,
    name: "Wei Zhang",
    hours: 6,
    selected: false,
    reasons: ["Can drive and is free Saturday", "No heavy-lifting experience listed"],
    draft: "Hi Wei! Saturday's delivery run (10 AM–1 PM) has an open seat. Interested?",
  },
];

const LOG: LogEntry[] = [
  ["thought", "", "The run needs 1 more driver who can lift boxes. Checking the shift first."],
  ["call", "get_shift", '{"shift_id": "…a41"}'],
  ["result", "get_shift", "Saturday Delivery Run · 2/3 confirmed · needs driving, heavy lifting"],
  ["call", "find_candidates", '{"shift_id": "…a41", "limit": 8}'],
  ["result", "find_candidates", "6 volunteers free for the whole shift, ranked by fit and recent hours"],
  ["call", "volunteer_history", '{"volunteer_id": "…7c2"}'],
  ["call", "propose_action", '{"candidates": 3, "drafts": 3}'],
  ["result", "propose_action", "Queued for coordinator approval"],
  ["final", "", "Proposed Jordan, Priya and Wei. Nothing is sent until approved."],
];

const ROSTER: [string, string, string, string][] = [
  ["Dana Kim", "driving, heavy lifting", "Yes", "Self sign-up"],
  ["Luis Moreno", "driving", "Yes", "Self sign-up"],
];

// ---------- sub-screens ----------

const CancelScreen: React.FC = () => {
  const frame = useCurrentFrame();
  const OPEN = 24;
  const CONFIRM = 69;
  const cancelled = frame >= CONFIRM + 4;
  const pop = useEnter(OPEN + 2);
  return (
    <AppShell account={MICHAEL_ACCOUNT} groups={michaelGroups(cancelled)}>
      <WeekCalendar events={michaelEvents(cancelled)} legend={VOL_LEGEND} />
      {!cancelled && (
        <SidePanel delay={-20}>
          <PeekTop />
          <ShiftHeader sh={delivery} label="you're signed up" kind="filled" place={PLACE} />
          <Caption style={{ marginTop: 10 }}>
            Drive the pantry van to deliver grocery boxes to families across the valley. · Needs: driving, heavy lifting
          </Caption>
          <div style={{ marginTop: 14 }}>
            <Btn pressed={pressed(frame, OPEN)}>Cancel this shift ▾</Btn>
          </div>
          {frame >= OPEN && (
            <div
              style={{
                marginTop: 8,
                padding: 14,
                borderRadius: 14,
                border: `1px solid ${app.line}`,
                boxShadow: app.shadowLg,
                opacity: pop,
                width: 300,
                background: "#fff",
              }}
            >
              <div style={{ fontSize: 14, marginBottom: 10 }}>Cancel this shift? Your coordinator will be notified.</div>
              <Btn primary pressed={pressed(frame, CONFIRM)}>
                Yes, cancel
              </Btn>
            </div>
          )}
        </SidePanel>
      )}
      <Toast at={CONFIRM + 4} text="Shift cancelled. Thanks for letting us know." />
      <Cursor
        path={[
          [0, 870, 330],
          [OPEN - 4, 820, 262],
          [OPEN + 14, 820, 262],
          [CONFIRM - 4, 810, 362],
        ]}
        clicks={[OPEN, CONFIRM]}
        hideAfter={CONFIRM + 20}
      />
    </AppShell>
  );
};

const CalendarScreen: React.FC = () => {
  const frame = useCurrentFrame();
  const PROPOSAL = 55;
  const pending = frame >= PROPOSAL;
  const events = coordEvents({ delivery: pending ? { conf: 2, kind: "pending", pulseAt: PROPOSAL } : { conf: 2, pulseAt: 6 } });
  return (
    <AppShell account={COORD_ACCOUNT} groups={coordGroups(events)}>
      <WeekCalendar events={events} legend={COORD_LEGEND} />
      <Fab />
    </AppShell>
  );
};

const PageScreen: React.FC = () => {
  const frame = useCurrentFrame();
  const LOG_OPEN = s(14 - T.page);
  const APPROVE = s(21 - T.page);
  const approved = frame >= APPROVE + 8;
  const scroll = interpolate(frame, [LOG_OPEN - 22, LOG_OPEN - 4], [0, 340], {
    ...clamp,
    easing: Easing.inOut(Easing.cubic),
  });
  const shift = { ...delivery, conf: 2 };
  const events = coordEvents({ delivery: { conf: 2, kind: approved ? "open" : "pending" } });
  return (
    <AppShell account={COORD_ACCOUNT} groups={coordGroups(events, "delivery")} calendarActive={false}>
      <ShiftPage
        sh={shift}
        label={approved ? "open" : "proposal pending"}
        kind={approved ? "open" : "pending"}
        place={PLACE}
        skills="driving, heavy lifting"
        about="Drive the pantry van to deliver grocery boxes to families across the valley; lift boxes up to 40 lbs."
        roster={ROSTER}
        width={approved ? 1060 : 600}
      >
        {approved && (
          <RequestsSent
            delay={APPROVE + 12}
            rows={[
              ["Jordan Lee", "awaiting reply", "emailed", "Oct 11, 6:42 PM"],
              ["Priya Natarajan", "awaiting reply", "emailed", "Oct 11, 6:42 PM"],
            ]}
          />
        )}
      </ShiftPage>
      {!approved && (
        <SidePanel delay={6} width={490} scroll={scroll}>
          <ProposalHeader />
          <ApprovalCard
            delay={10}
            trigger="Vacancy · Michael Brooks cancelled"
            summary="Michael cancelled, so the run has 1 open slot (needs driving and heavy lifting). Here are 3 available drivers, least busy first."
            candidates={CANDIDATES}
            approvePressed={pressed(frame, APPROVE)}
            logOpen={frame >= LOG_OPEN}
            log={<RunLog entries={LOG} start={LOG_OPEN + 4} every={8} />}
          />
        </SidePanel>
      )}
      <Toast at={APPROVE + 8} text="Sent 2 request(s)." />
      <Cursor
        path={[
          [0, 520, 520],
          [LOG_OPEN - 20, 520, 520],
          [LOG_OPEN - 4, 760, 474],
          [APPROVE - 30, 760, 474],
          [APPROVE - 4, 760, 425],
        ]}
        clicks={[LOG_OPEN, APPROVE]}
        hideAfter={APPROVE + 30}
      />
    </AppShell>
  );
};

const RespondScreen: React.FC = () => (
  <VolunteerRequestScreen
    name="Jordan Lee"
    sh={{ ...delivery, conf: 2 }}
    date="Saturday, October 17, 2026"
    time="10:00 AM–1:00 PM"
    place={PLACE}
    skills="driving, heavy lifting"
    about="Drive the pantry van to deliver grocery boxes to families across the valley; lift boxes up to 40 lbs."
    message={CANDIDATES[0].draft}
    crew={["Dana Kim", "Luis Moreno"]}
    acceptAt={26}
  />
);

const FilledScreen: React.FC = () => {
  const events = coordEvents({ delivery: { conf: 3, kind: "filled", pulseAt: 4 } });
  return (
    <AppShell account={COORD_ACCOUNT} groups={coordGroups(events)}>
      <WeekCalendar events={events} legend={COORD_LEGEND} />
      <Fab />
    </AppShell>
  );
};

const Mock: React.FC = () => {
  const seg = (a: number, b: number) => ({ from: s(a), durationInFrames: s(b) - s(a) });
  return (
    <>
      <Sequence {...seg(T.cancel, T.calendar)}>
        <CancelScreen />
      </Sequence>
      <Sequence {...seg(T.calendar, T.page)}>
        <CalendarScreen />
      </Sequence>
      <Sequence {...seg(T.page, T.respond)}>
        <PageScreen />
      </Sequence>
      <Sequence {...seg(T.respond, T.filled)}>
        <RespondScreen />
      </Sequence>
      <Sequence {...seg(T.filled, T.end)}>
        <FilledScreen />
      </Sequence>
    </>
  );
};

export const Scenario1: React.FC = () => (
  <SceneShell>
    <Screen file={RECORDINGS.scenario1}>
      <Mock />
    </Screen>
    <ChapterLabel text="1 · Cancellation" />
    <div style={{ position: "absolute", right: 40, top: 40, zIndex: 10 }}>
      <Callout at={6} until={7} tone="subtle" small>
        ⏳ agent working…
      </Callout>
    </div>
    <CalloutStack>
      <Callout at={0} until={5.5}>1-click cancel</Callout>
      <Callout at={8} until={13.8}>Available ✓</Callout>
      <Callout at={8.6} until={13.8}>Driver ✓</Callout>
      <Callout at={9.2} until={13.8}>Fair workload ✓</Callout>
      <Callout at={14} until={18.8}>Full audit trail</Callout>
      <Callout at={19} until={24.8}>Human approval required</Callout>
      <Callout at={26} tone="green">Filled ✓</Callout>
    </CalloutStack>
    <Captions
      cues={[
        [0, "Michael can't make Saturday. One click."],
        [5.5, "Within seconds, the agent finds people who are free, can drive, and haven't been overworked,"],
        [11, "and drafts a message for each."],
        [14, "Every step is logged."],
        [19, "Nothing is sent until Alice approves."],
        [24.5, "The volunteer accepts the request, and the shift is covered."],
      ]}
    />
  </SceneShell>
);

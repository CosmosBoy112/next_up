import React from "react";
import { Sequence, useCurrentFrame } from "remotion";
import { app } from "../theme";
import { RECORDINGS, s } from "../timing";
import {
  AppShell,
  COORD_ACCOUNT,
  COORD_LEGEND,
  coordEvents,
  coordGroups,
  Cursor,
  Fab,
  Icon,
  pressed,
  shiftById,
  SidePanel,
  Spinner,
  typed,
  WeekCalendar,
} from "../ui/app";
import { ApprovalCard, Candidate, ProposalHeader, ShiftPage } from "../ui/coordinator";
import { Callout, CalloutStack, Captions, ChapterLabel, hasStatic, SceneShell, Screen, useEnter } from "../ui/overlay";

// Scene 6 (10 s): Alice asks the assistant in plain English.
const REQUEST = "Need drivers for the Senior Grocery Delivery";
const PAGE_AT = 6.3;

const CANDIDATES: Candidate[] = [
  {
    rank: 1,
    name: "Wei Zhang",
    hours: 6,
    selected: true,
    reasons: ["Can drive", "Free for the whole shift, 2–5 PM"],
    draft: "Hi Wei! Could you drive for the Senior Grocery Delivery on Wednesday, Oct 14, 2–5 PM? No pressure at all.",
  },
  {
    rank: 2,
    name: "Marcus Hill",
    hours: 11,
    selected: true,
    reasons: ["Can drive", "Free Wednesday afternoon"],
    draft: "Hi Marcus! We need one more driver for the Senior Grocery Delivery, Wed Oct 14, 2–5 PM. Are you free?",
  },
];

// Chat bar geometry in main-area coordinates (the main area is 1154×810).
const BAR = { left: 227, width: 700, bottom: 26, height: 56 };
const SEND = { x: BAR.left + BAR.width - 34, y: 810 - BAR.bottom - BAR.height / 2 };

const Bubble: React.FC<{ user?: boolean; delay: number; children: React.ReactNode }> = ({ user, delay, children }) => {
  const p = useEnter(delay);
  return (
    <div style={{ display: "flex", gap: 10, alignItems: "flex-start", marginTop: 12, opacity: p }}>
      <div
        style={{
          width: 28,
          height: 28,
          borderRadius: 8,
          flexShrink: 0,
          display: "grid",
          placeItems: "center",
          background: user ? "#ffe3d6" : app.accentSoft,
          color: user ? "#c2562a" : app.accent,
          fontSize: 13,
          fontWeight: 800,
        }}
      >
        {user ? "A" : <Icon name="spark" size={15} />}
      </div>
      <div style={{ fontSize: 14.5, lineHeight: 1.5, paddingTop: 3 }}>{children}</div>
    </div>
  );
};

const ChatScreen: React.FC = () => {
  const frame = useCurrentFrame();
  const FAB = 12;
  const TYPE = [26, 92] as const;
  const SENT = 100;
  const REPLY = 160;
  const bar = useEnter(FAB + 2);
  const panel = useEnter(SENT + 2);
  const events = coordEvents();
  const text = frame >= SENT ? "" : typed(frame, REQUEST, TYPE[0], TYPE[1]);
  return (
    <AppShell account={COORD_ACCOUNT} groups={coordGroups(events)}>
      <WeekCalendar events={events} legend={COORD_LEGEND} />
      {frame >= SENT && (
        <div
          style={{
            position: "absolute",
            left: BAR.left,
            width: BAR.width,
            bottom: BAR.bottom + BAR.height + 16,
            background: "#fff",
            borderRadius: 26,
            boxShadow: app.shadowLg,
            padding: "16px 22px 18px",
            opacity: panel,
            transform: `translateY(${(1 - panel) * 18}px)`,
            zIndex: 15,
          }}
        >
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
            <b style={{ fontSize: 15 }}>Assistant</b>
            <div style={{ display: "flex", gap: 14, fontSize: 13, color: app.ink, fontWeight: 600 }}>
              <span>☁ Weather check</span>
              <span>◎ Coverage scan</span>
            </div>
          </div>
          <Bubble delay={-10}>
            Hi! Ask me to find volunteers for a shift, check the weather for outdoor shifts, or run a coverage scan.
          </Bubble>
          <Bubble user delay={SENT + 2}>
            {REQUEST}
          </Bubble>
          {frame < REPLY ? (
            <Bubble delay={SENT + 8}>
              <span style={{ display: "inline-flex", gap: 8, alignItems: "center", color: app.muted }}>
                <Spinner /> Working on it…
              </span>
            </Bubble>
          ) : (
            <Bubble delay={REPLY}>
              1 new proposal(s) are waiting for your approval:
              <br />• <b>Senior Grocery Delivery</b> · Wed Oct 14 · 2:00 PM–5:00 PM
            </Bubble>
          )}
        </div>
      )}
      {frame >= FAB && (
        <div
          style={{
            position: "absolute",
            left: BAR.left,
            width: BAR.width,
            bottom: BAR.bottom,
            height: BAR.height,
            borderRadius: 99,
            background: "#fff",
            boxShadow: app.shadowLg,
            display: "flex",
            alignItems: "center",
            gap: 12,
            padding: "0 8px 0 20px",
            opacity: bar,
            transform: `translateY(${(1 - bar) * 18}px)`,
            zIndex: 15,
          }}
        >
          <span style={{ color: app.accent }}>
            <Icon name="spark" size={22} />
          </span>
          <div style={{ flex: 1, fontSize: 16, color: text ? app.ink : app.muted }}>
            {text || "Ask the assistant to find volunteers…"}
            {text && frame < SENT && <span style={{ opacity: frame % 16 < 8 ? 1 : 0 }}>|</span>}
          </div>
          <div
            style={{
              width: 42,
              height: 42,
              borderRadius: 13,
              background: app.accent,
              display: "grid",
              placeItems: "center",
              color: "#fff",
              fontSize: 18,
              transform: pressed(frame, SENT) ? "scale(0.9)" : undefined,
            }}
          >
            ➤
          </div>
        </div>
      )}
      <Fab open={frame >= FAB} pressed={pressed(frame, FAB)} />
      <Cursor
        path={[
          [0, 1010, 640],
          [FAB - 4, 1126, 782],
          [TYPE[1] - 6, 1126, 782],
          [SENT - 4, SEND.x, SEND.y],
        ]}
        clicks={[FAB, SENT]}
        hideAfter={SENT + 24}
      />
    </AppShell>
  );
};

const ProposalScreen: React.FC = () => {
  const senior = shiftById("senior");
  const events = coordEvents({ delivery: { conf: 3 }, senior: { kind: "pending" } });
  return (
    <AppShell account={COORD_ACCOUNT} groups={coordGroups(events, "senior")} calendarActive={false}>
      <ShiftPage
        sh={senior}
        label="proposal pending"
        kind="pending"
        date="Wednesday, October 14, 2026"
        place="Departs Pantry Warehouse"
        skills="driving"
        about="Drive pre-packed grocery boxes to homebound seniors and check in with them briefly."
        roster={[["Michael Brooks", "driving, heavy lifting", "Yes", "Self sign-up"]]}
      />
      <SidePanel delay={4} width={490}>
        <ProposalHeader />
        <ApprovalCard
          delay={8}
          trigger={`Request · “${REQUEST}”`}
          summary="The Senior Grocery Delivery has 2 open spots and needs drivers. Both candidates can drive and are free for the whole shift."
          candidates={CANDIDATES}
        />
      </SidePanel>
    </AppShell>
  );
};

/** Typed request bubble, only over a real recording (the mockup types into its own chat bar). */
const RequestOverlay: React.FC = () => {
  const frame = useCurrentFrame();
  const p = useEnter(s(0.6));
  return (
    <div
      style={{
        position: "absolute",
        left: "50%",
        bottom: 130,
        transform: `translate(-50%, ${(1 - p) * 20}px)`,
        opacity: p,
        background: "#fff",
        border: `1px solid ${app.line}`,
        borderRadius: 22,
        padding: "16px 26px",
        fontSize: 30,
        fontWeight: 700,
        boxShadow: "0 18px 44px rgba(31,37,71,.2)",
        zIndex: 10,
      }}
    >
      “{typed(frame, REQUEST, s(0.8), s(3.2))}”
    </div>
  );
};

export const Scenario2: React.FC = () => (
  <SceneShell>
    <Screen file={RECORDINGS.scenario2}>
      <Sequence durationInFrames={s(PAGE_AT)}>
        <ChatScreen />
      </Sequence>
      <Sequence from={s(PAGE_AT)}>
        <ProposalScreen />
      </Sequence>
    </Screen>
    <ChapterLabel text="2 · Ask" />
    {hasStatic(RECORDINGS.scenario2) && (
      <Sequence durationInFrames={s(5)}>
        <RequestOverlay />
      </Sequence>
    )}
    <CalloutStack>
      <Callout at={7}>Drivers only ✓</Callout>
    </CalloutStack>
    <Captions
      cues={[
        [0, "Alice can also just ask."],
        [5, "The agent finds the shift and proposes only people who can drive."],
      ]}
    />
  </SceneShell>
);

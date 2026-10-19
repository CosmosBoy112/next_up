// Volunteer task page for a coordinator request (ui/volunteer_view.py task_page),
// laid out after the real app's "Request from your coordinator" screen.
import React from "react";
import { useCurrentFrame } from "remotion";
import { app } from "../theme";
import { AppShell, Badge, Cursor, Icon, IconName, pressed, Progress, Shift, Toast } from "./app";
import { useEnter } from "./overlay";

const PropRow: React.FC<{ icon: IconName; label: string; children: React.ReactNode }> = ({ icon, label, children }) => (
  <div style={{ display: "flex", alignItems: "center", padding: "9px 8px", fontSize: 16 }}>
    <div style={{ width: 260, color: app.muted, display: "flex", alignItems: "center", gap: 8 }}>
      <Icon name={icon} size={16} /> {label}
    </div>
    <div style={{ flex: 1 }}>{children}</div>
  </div>
);

const H2: React.FC<{ children: React.ReactNode }> = ({ children }) => (
  <div style={{ fontSize: 27, fontWeight: 600, letterSpacing: -0.5, margin: "22px 0 12px" }}>{children}</div>
);

export const VolunteerRequestScreen: React.FC<{
  name: string;
  sh: Shift;
  date: string;
  time: string;
  place: string;
  skills: string;
  about: string;
  message: string;
  crew: string[];
  acceptAt: number;
}> = ({ name, sh, date, time, place, skills, about, message, crew, acceptAt }) => {
  const frame = useCurrentFrame();
  const accepted = frame >= acceptAt + 4;
  const conf = accepted ? sh.conf + 1 : sh.conf;
  const done = useEnter(acceptAt + 4);
  const sidebarItem = accepted
    ? { title: "My shifts", tag: "signed up", kind: "filled" as const }
    : { title: "Requests for you", tag: "request", kind: "pending" as const };
  return (
    <AppShell
      account={{ name, sub: "Volunteer · Valley Community Pantry" }}
      calendarActive={false}
      groups={[{ title: sidebarItem.title, items: [{ kind: sidebarItem.kind, tag: sidebarItem.tag, title: sh.title, when: "Sat 10/17 · 10:00 AM", active: true }] }]}
      footer={
        <div style={{ borderTop: `1px solid ${app.line}`, margin: "20px 8px 0", paddingTop: 18, display: "flex", gap: 8, alignItems: "center", fontSize: 14 }}>
          <Icon name="profile" size={16} /> Edit profile
        </div>
      }
    >
      <div style={{ position: "absolute", left: 76, top: 26, right: 40 }}>
        <div style={{ display: "flex", alignItems: "center", gap: 8, fontSize: 15 }}>
          <Icon name="back" size={16} /> Calendar
        </div>
        <div style={{ fontSize: 44, fontWeight: 800, letterSpacing: -1.2, margin: "22px 0 10px", display: "flex", alignItems: "center", gap: 14 }}>
          {sh.title}
          <Badge kind={accepted ? "filled" : "pending"} size={14}>
            {accepted ? "you're signed up" : "request for you"}
          </Badge>
        </div>
        <PropRow icon="calendar" label="Date">{date}</PropRow>
        <PropRow icon="clock" label="Time">{time}</PropRow>
        <PropRow icon="pin" label="Location">{place}</PropRow>
        <PropRow icon="tools" label="Skills needed">{skills}</PropRow>
        <PropRow icon="people" label="Volunteers">
          <Progress value={conf / sh.req} text={`${conf}/${sh.req} filled`} color={conf >= sh.req ? "#5aa469" : app.accent} />
        </PropRow>
        <H2>About</H2>
        <div style={{ fontSize: 16 }}>{about}</div>
        {accepted ? (
          <div style={{ opacity: done }}>
            <H2>Who's going</H2>
            <div style={{ display: "flex", gap: 8 }}>
              {[...crew, name].map((n) => (
                <Badge key={n} kind={n === name ? "filled" : "muted"} size={14}>
                  {n}
                </Badge>
              ))}
            </div>
            <div style={{ fontSize: 13, color: app.muted, marginTop: 14 }}>Joined via coordinator request</div>
          </div>
        ) : (
          <>
            <H2>Request from your coordinator</H2>
            <div style={{ border: `1px solid ${app.line}`, borderRadius: 14, padding: "16px 16px 14px", background: "#f6f7fb" }}>
              <div style={{ fontSize: 16, lineHeight: 1.55 }}>{message}</div>
              <div style={{ fontSize: 13, color: app.muted, margin: "12px 0 14px" }}>
                Suggested by the coordinator's assistant, approved by Valley Community Pantry coordinator
              </div>
              <div style={{ display: "flex", gap: 16 }}>
                <div
                  style={{
                    flex: 1,
                    height: 38,
                    borderRadius: 10,
                    background: app.accent,
                    color: "#fff",
                    display: "grid",
                    placeItems: "center",
                    fontSize: 15,
                    boxShadow: "0 8px 20px rgba(91,95,240,.30)",
                    transform: pressed(frame, acceptAt) ? "scale(0.97)" : undefined,
                  }}
                >
                  Accept
                </div>
                <div style={{ flex: 1, height: 38, borderRadius: 10, background: "#fff", border: `1px solid ${app.line}`, display: "grid", placeItems: "center", fontSize: 15 }}>
                  Decline
                </div>
              </div>
            </div>
          </>
        )}
      </div>
      <Toast at={acceptAt + 4} text={`You're confirmed for ${sh.title}. Thank you!`} />
      <Cursor path={[[0, 760, 300], [acceptAt - 4, 360, 611]]} clicks={[acceptAt]} hideAfter={acceptAt + 20} />
    </AppShell>
  );
};

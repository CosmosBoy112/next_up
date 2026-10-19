// Coordinator task page and agent panels (ui/coordinator_view.py).
import React from "react";
import { interpolate, useCurrentFrame } from "remotion";
import { app, Kind } from "../theme";
import { Badge, Btn, Caption, Icon, Progress, Shift } from "./app";
import { clamp, useEnter } from "./overlay";

const H3: React.FC<{ children: React.ReactNode }> = ({ children }) => (
  <div style={{ fontSize: 19, fontWeight: 800, margin: "18px 0 8px", letterSpacing: -0.3 }}>{children}</div>
);

const Table: React.FC<{ cols: string[]; rows: React.ReactNode[][]; delay?: number }> = ({ cols, rows, delay = 0 }) => (
  <div style={{ background: "#fff", borderRadius: 14, boxShadow: app.shadow, overflow: "hidden", fontSize: 13 }}>
    <div style={{ display: "flex", background: "#f7f8fc", color: app.muted, fontWeight: 700 }}>
      {cols.map((c) => (
        <div key={c} style={{ flex: 1, padding: "8px 12px" }}>
          {c}
        </div>
      ))}
    </div>
    {rows.map((r, i) => (
      <Row key={i} delay={delay + i * 6}>
        {r.map((cell, j) => (
          <div key={j} style={{ flex: 1, padding: "8px 12px", borderTop: `1px solid ${app.line}` }}>
            {cell}
          </div>
        ))}
      </Row>
    ))}
  </div>
);

const Row: React.FC<{ delay: number; children: React.ReactNode }> = ({ delay, children }) => {
  const p = useEnter(delay);
  return <div style={{ display: "flex", opacity: p }}>{children}</div>;
};

/** Notion-style shift page: title, property rows, about, roster, and optional extra sections. */
export const ShiftPage: React.FC<{
  sh: Shift;
  label: string;
  kind: Kind;
  place: string;
  skills: string;
  about: string;
  roster: [string, string, string, string][];
  extraProps?: [string, React.ReactNode][];
  children?: React.ReactNode;
  width?: number;
  date?: string;
}> = ({ sh, label, kind, place, skills, about, roster, extraProps = [], children, width = 610, date = "Saturday, October 17, 2026" }) => (
  <div style={{ position: "absolute", left: 30, top: 22, width }}>
    <div style={{ display: "flex", alignItems: "center", gap: 6, fontSize: 14, fontWeight: 600, color: app.ink }}>
      <Icon name="back" size={16} /> Calendar
    </div>
    <div style={{ fontSize: 30, fontWeight: 800, letterSpacing: -0.6, margin: "12px 0 14px", lineHeight: 1.15 }}>
      {sh.title} <Badge kind={kind} size={14}>{label}</Badge>
    </div>
    {(
      [
        ["Date", date],
        ["Time", `${sh.start > 12 ? sh.start - 12 : sh.start}:00 ${sh.start >= 12 ? "PM" : "AM"}–${sh.end - 12}:00 PM`],
        ["Location", place],
        ["Skills needed", skills],
        ...extraProps,
      ] as [string, React.ReactNode][]
    ).map(([k, v]) => (
      <div key={k} style={{ display: "flex", padding: "5px 8px", fontSize: 14 }}>
        <div style={{ width: 150, color: app.muted }}>{k}</div>
        <div style={{ flex: 1 }}>{v}</div>
      </div>
    ))}
    <div style={{ display: "flex", padding: "5px 8px", fontSize: 14, alignItems: "center" }}>
      <div style={{ width: 150, color: app.muted }}>Volunteers</div>
      <div style={{ flex: 1 }}>
        <Progress value={sh.conf / sh.req} text={`${sh.conf}/${sh.req} filled`} color={sh.conf >= sh.req ? "#5aa469" : app.accent} />
      </div>
    </div>
    <H3>About</H3>
    <div style={{ fontSize: 14, lineHeight: 1.5 }}>{about}</div>
    <H3>Volunteers</H3>
    <Table cols={["Name", "Skills", "Drives", "Joined via"]} rows={roster} />
    {children}
  </div>
);

export const RequestsSent: React.FC<{ rows: [string, string, string, string][]; delay?: number }> = ({ rows, delay = 0 }) => {
  const p = useEnter(delay);
  return (
    <div style={{ opacity: p }}>
      <H3>Requests sent</H3>
      <Table cols={["Volunteer", "Status", "Email", "Sent"]} rows={rows} delay={delay + 4} />
    </div>
  );
};

// ---------- proposal panel ----------

export type Candidate = { rank: number; name: string; hours: number; reasons: string[]; draft: string; selected: boolean };

const Checkbox: React.FC<{ on: boolean }> = ({ on }) => (
  <div
    style={{
      width: 18,
      height: 18,
      borderRadius: 5,
      background: on ? app.accent : "#fff",
      border: on ? "none" : `2px solid ${app.line}`,
      display: "grid",
      placeItems: "center",
      color: "#fff",
      flexShrink: 0,
    }}
  >
    {on && <Icon name="check" size={13} color="#fff" />}
  </div>
);

export const CandidateCard: React.FC<{ c: Candidate; delay: number; hoursMax?: number }> = ({ c, delay }) => {
  const p = useEnter(delay);
  return (
    <div
      style={{
        border: `1px solid ${app.line}`,
        borderRadius: 16,
        padding: "12px 14px",
        marginTop: 10,
        opacity: p,
        transform: `translateY(${(1 - p) * 14}px)`,
      }}
    >
      <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
        <Checkbox on={c.selected} />
        <div style={{ fontWeight: 800, fontSize: 15, flex: 1 }}>
          #{c.rank} {c.name}
        </div>
        <div style={{ width: 150 }}>
          <Progress value={(c.hours / 30) * p} text={`${c.hours} h in last 28 days`} />
        </div>
      </div>
      <ul style={{ margin: "8px 0 8px", paddingLeft: 20, fontSize: 13, lineHeight: 1.5 }}>
        {c.reasons.map((r) => (
          <li key={r}>{r}</li>
        ))}
      </ul>
      <div style={{ border: `1px solid ${app.line}`, borderRadius: 10, padding: "8px 10px", fontSize: 13, color: app.ink, background: "#fbfbfe", lineHeight: 1.45 }}>
        {c.draft}
      </div>
    </div>
  );
};

export type LogEntry = [kind: "thought" | "call" | "result" | "final", tool: string, text: string];

export const RunLog: React.FC<{ entries: LogEntry[]; start: number; every?: number }> = ({ entries, start, every = 9 }) => {
  const frame = useCurrentFrame();
  return (
    <div style={{ marginTop: 8, fontSize: 12.5, lineHeight: 1.45 }}>
      {entries.map(([kind, tool, text], i) => {
        const o = interpolate(frame, [start + i * every, start + i * every + 6], [0, 1], clamp);
        return (
          <div key={i} style={{ opacity: o, padding: "3px 0", display: "flex", gap: 8 }}>
            <code style={{ color: app.muted, width: 16, textAlign: "right", flexShrink: 0 }}>{i + 1}</code>
            <div>
              <span style={{ color: app.muted }}>{kind}</span>{" "}
              {tool && <code style={{ background: "#f1f3f9", borderRadius: 4, padding: "0 4px", color: "#4c32b0" }}>{tool}</code>} {text}
            </div>
          </div>
        );
      })}
    </div>
  );
};

export const Expander: React.FC<{ open: boolean; title: string; children?: React.ReactNode }> = ({ open, title, children }) => (
  <div style={{ border: `1px solid ${app.line}`, borderRadius: 12, padding: "8px 12px", marginTop: 12 }}>
    <div style={{ fontSize: 13.5, fontWeight: 600, display: "flex", gap: 8 }}>
      <span style={{ display: "inline-block", transform: `rotate(${open ? 90 : 0}deg)` }}>›</span> {title}
    </div>
    {open && children}
  </div>
);

export const ProposalHeader: React.FC = () => (
  <>
    <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
      <div style={{ display: "flex", alignItems: "center", gap: 8, fontSize: 16, fontWeight: 800 }}>
        <span style={{ color: "#3aa0d8" }}>
          <Icon name="spark" size={18} />
        </span>
        Agent proposal
      </div>
      <span style={{ color: app.muted }}>
        <Icon name="close" size={16} />
      </span>
    </div>
    <Caption style={{ margin: "4px 0 10px" }}>Nothing reaches a volunteer until you approve.</Caption>
  </>
);

export const ApprovalCard: React.FC<{
  trigger: string;
  summary: string;
  candidates: Candidate[];
  delay?: number;
  approvePressed?: boolean;
  logOpen?: boolean;
  log?: React.ReactNode;
}> = ({ trigger, summary, candidates, delay = 0, approvePressed, logOpen = false, log }) => {
  const selected = candidates.filter((c) => c.selected).length;
  const p = useEnter(delay);
  return (
    <div style={{ border: `1px solid ${app.line}`, borderRadius: 18, padding: "14px 16px", opacity: p }}>
      <Caption>{trigger}</Caption>
      <div style={{ fontSize: 14, lineHeight: 1.5, marginTop: 4 }}>{summary}</div>
      {candidates.map((c, i) => (
        <CandidateCard key={c.name} c={c} delay={delay + 8 + i * 8} />
      ))}
      <div style={{ border: `1px solid ${app.line}`, borderRadius: 10, padding: "8px 10px", fontSize: 13, color: app.muted, marginTop: 12 }}>
        Note (optional)
      </div>
      <div style={{ display: "flex", gap: 10, marginTop: 12 }}>
        <Btn primary pressed={approvePressed}>
          Approve selected ({selected})
        </Btn>
        <Btn>Reject</Btn>
      </div>
      <Expander open={logOpen} title="Why? (agent reasoning & tool calls)">
        {log}
      </Expander>
    </div>
  );
};

// ---------- weather panel ----------

export type Alternative = { title: string; details: string; notice: string };

const Radio: React.FC<{ on: boolean }> = ({ on }) => (
  <div
    style={{
      width: 18,
      height: 18,
      borderRadius: 99,
      border: `2px solid ${on ? app.accent : app.line}`,
      display: "grid",
      placeItems: "center",
      flexShrink: 0,
      marginTop: 2,
    }}
  >
    {on && <div style={{ width: 9, height: 9, borderRadius: 99, background: app.accent }} />}
  </div>
);

const AltRow: React.FC<{ a: Alternative; on: boolean; delay: number }> = ({ a, on, delay }) => {
  const p = useEnter(delay);
  return (
    <div style={{ display: "flex", gap: 10, padding: "5px 0", opacity: p }}>
      <Radio on={on} />
      <div>
        <div style={{ fontSize: 14, fontWeight: 600 }}>{a.title}</div>
        <Caption style={{ fontSize: 12.5 }}>{a.details}</Caption>
      </div>
    </div>
  );
};

export const WeatherCard: React.FC<{
  alternatives: Alternative[];
  pick: number;
  crew: number;
  delay?: number;
  approvePressed?: boolean;
}> = ({ alternatives, pick, crew, delay = 0, approvePressed }) => {
  const p = useEnter(delay);
  return (
    <div style={{ border: `1px solid ${app.line}`, borderRadius: 18, padding: "14px 16px", opacity: p }}>
      <div style={{ fontSize: 15 }}>
        <Badge kind="severe">severe</Badge> <b>Thunderstorm</b> <span style={{ color: app.muted }}>· Weather check · simulated (demo)</span>
      </div>
      <div style={{ fontSize: 13.5, margin: "8px 0", display: "flex", gap: 14 }}>
        <span>💧 90%</span>
        <span>🌧 18.0 mm</span>
        <span>💨 72 km/h</span>
        <span>🌡 21–25°C</span>
      </div>
      <ul style={{ margin: "4px 0 8px", paddingLeft: 20, fontSize: 13, lineHeight: 1.55 }}>
        <li>Thunderstorms likely (90% chance of rain)</li>
        <li>Heavy rain: about 18.0 mm</li>
        <li>Damaging wind gusts up to 72 km/h</li>
      </ul>
      <div style={{ fontSize: 13.5, lineHeight: 1.5 }}>
        A severe thunderstorm is forecast during this outdoor pop-up. Here are three ways to keep families served and the crew safe.
      </div>
      <div style={{ fontSize: 13.5, fontWeight: 600, margin: "12px 0 6px" }}>Choose a plan</div>
      {alternatives.map((a, i) => (
        <AltRow key={a.title} a={a} on={i === pick} delay={delay + 30 + i * 8} />
      ))}
      <div style={{ fontSize: 13.5, fontWeight: 600, margin: "12px 0 6px" }}>Notice to the crew</div>
      <div style={{ border: `1px solid ${app.line}`, borderRadius: 10, padding: "8px 10px", fontSize: 13, lineHeight: 1.45, background: "#fbfbfe", minHeight: 76 }}>
        {alternatives[pick].notice}
      </div>
      <div style={{ display: "flex", gap: 10, marginTop: 12 }}>
        <Btn primary pressed={approvePressed}>
          Approve & notify crew ({crew})
        </Btn>
        <Btn>Dismiss</Btn>
      </div>
    </div>
  );
};

// Animated recreations of the NextUp Streamlit UI (ui/*.py), used when no screen
// recording is present. Coordinates are in the 1440×810 browser viewport.
import React from "react";
import { interpolate, useCurrentFrame, Easing } from "remotion";
import { app, fontFamily, KINDS, Kind } from "../theme";
import { clamp, LogoIcon, useEnter } from "./overlay";

// ---------- data ----------

export const DAYS = ["SUN 10/11", "MON 10/12", "TUE 10/13", "WED 10/14", "THU 10/15", "FRI 10/16", "SAT 10/17"];

export type Shift = {
  id: string;
  day: number;
  start: number;
  end: number;
  title: string;
  conf: number;
  req: number;
};

export const SHIFTS: Shift[] = [
  { id: "sorting", day: 0, start: 9, end: 12, title: "Pantry Sorting", conf: 3, req: 5 },
  { id: "intake", day: 1, start: 10, end: 13, title: "Client Intake Desk", conf: 2, req: 2 },
  { id: "inventory", day: 1, start: 18, end: 20, title: "Inventory Data Entry", conf: 1, req: 2 },
  { id: "truck", day: 2, start: 13, end: 15, title: "Truck Unloading", conf: 4, req: 4 },
  { id: "kids", day: 2, start: 16, end: 18, title: "Kids Reading Hour", conf: 1, req: 3 },
  { id: "gleaning", day: 3, start: 9, end: 12, title: "Produce Gleaning", conf: 2, req: 4 },
  { id: "senior", day: 3, start: 14, end: 17, title: "Senior Grocery Delivery", conf: 1, req: 3 },
  { id: "health", day: 4, start: 12, end: 15, title: "Health Fair Booth", conf: 3, req: 3 },
  { id: "dinner", day: 4, start: 17, end: 20, title: "Community Dinner", conf: 4, req: 6 },
  { id: "snack", day: 5, start: 15, end: 17, title: "Kids Snack Packing", conf: 4, req: 4 },
  { id: "restock", day: 5, start: 18, end: 20, title: "Evening Restock", conf: 1, req: 3 },
  { id: "delivery", day: 6, start: 10, end: 13, title: "Saturday Delivery Run", conf: 3, req: 3 },
  { id: "popup", day: 6, start: 14, end: 17, title: "Mobile Pantry Pop-up", conf: 5, req: 5 },
];

export const shiftById = (id: string) => SHIFTS.find((x) => x.id === id)!;

export type CalEvent = { shift: Shift; kind: Kind; title: string; pulseAt?: number };

/** Coordinator calendar events; `over` replaces fill counts / kinds for some shifts. */
export const coordEvents = (over: Record<string, { conf?: number; kind?: Kind; pulseAt?: number }> = {}): CalEvent[] =>
  SHIFTS.map((sh) => {
    const o = over[sh.id] ?? {};
    const conf = o.conf ?? sh.conf;
    const kind = o.kind ?? (conf >= sh.req ? "filled" : "open");
    return { shift: { ...sh, conf }, kind, title: `${sh.title} (${conf}/${sh.req})`, pulseAt: o.pulseAt };
  });

const MICHAEL_KINDS: Record<string, Kind> = {
  delivery: "filled",
  senior: "filled",
  truck: "recommended",
  sorting: "open",
  gleaning: "open",
  dinner: "open",
  restock: "open",
  kids: "muted",
  inventory: "muted",
};

/** Michael's volunteer calendar: his shifts, recommendations, and open shifts. */
export const michaelEvents = (cancelled = false): CalEvent[] =>
  SHIFTS.filter((sh) => MICHAEL_KINDS[sh.id] && !(cancelled && sh.id === "delivery")).map((sh) => {
    const kind = MICHAEL_KINDS[sh.id];
    const title = kind === "recommended" ? `${sh.title} · for you` : sh.title;
    return { shift: sh, kind, title };
  });

// ---------- primitives ----------

export type IconName = "calendar" | "spark" | "close" | "back" | "search" | "check" | "clock" | "pin" | "tools" | "people" | "profile";

export const Icon: React.FC<{ name: IconName; size?: number; color?: string }> = ({
  name,
  size = 18,
  color = "currentColor",
}) => {
  const paths: Record<string, React.ReactNode> = {
    calendar: (
      <>
        <rect x="3" y="5" width="18" height="16" rx="3" />
        <path d="M3 10h18M8 3v4M16 3v4" />
      </>
    ),
    spark: <path d="M12 3l1.8 5.2L19 10l-5.2 1.8L12 17l-1.8-5.2L5 10l5.2-1.8zM19 15l.8 2.2L22 18l-2.2.8L19 21l-.8-2.2L16 18l2.2-.8z" />,
    close: <path d="M6 6l12 12M18 6L6 18" />,
    back: <path d="M19 12H5M11 6l-6 6 6 6" />,
    search: (
      <>
        <circle cx="10" cy="10" r="6" />
        <path d="M15 15l5 5" />
      </>
    ),
    check: <path d="M5 12l5 5 9-10" />,
    clock: (
      <>
        <circle cx="12" cy="12" r="9" />
        <path d="M12 7v5l3 2" />
      </>
    ),
    pin: (
      <>
        <path d="M12 21s-7-6.2-7-11.5a7 7 0 0114 0C19 14.8 12 21 12 21z" />
        <circle cx="12" cy="9.5" r="2.5" />
      </>
    ),
    tools: <path d="M14.5 6.5l3-3 3 3-3 3M17.5 6.5L6 18M4 4l5.5 5.5M14 14l6 6M3.5 20.5l3-3" />,
    people: (
      <>
        <circle cx="9" cy="8" r="3.5" />
        <path d="M2.5 20c.8-3.5 3.4-5.5 6.5-5.5s5.7 2 6.5 5.5M16 4.8a3.3 3.3 0 010 6.4M18 14.8c2 .7 3.2 2.4 3.6 5.2" />
      </>
    ),
    profile: (
      <>
        <circle cx="10" cy="8" r="4" />
        <path d="M3 20c.9-3.6 3.7-6 7-6 1.4 0 2.6.4 3.7 1.1M17.5 14.5v6M14.5 17.5h6" />
      </>
    ),
  };
  const filled = name === "spark";
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill={filled ? color : "none"} stroke={filled ? "none" : color} strokeWidth={2.2} strokeLinecap="round" strokeLinejoin="round">
      {paths[name]}
    </svg>
  );
};

export const Badge: React.FC<{ kind: Kind; children: React.ReactNode; size?: number }> = ({ kind, children, size = 12 }) => (
  <span
    style={{
      display: "inline-block",
      background: KINDS[kind].badgeBg,
      color: KINDS[kind].badge,
      borderRadius: 6,
      padding: "1px 7px",
      fontSize: size,
      fontWeight: 700,
      lineHeight: 1.5,
      verticalAlign: "middle",
      whiteSpace: "nowrap",
    }}
  >
    {children}
  </span>
);

export const Btn: React.FC<{
  primary?: boolean;
  pressed?: boolean;
  disabled?: boolean;
  style?: React.CSSProperties;
  children: React.ReactNode;
}> = ({ primary, pressed, disabled, style, children }) => (
  <div
    style={{
      display: "inline-flex",
      alignItems: "center",
      justifyContent: "center",
      gap: 6,
      padding: "8px 16px",
      borderRadius: 12,
      fontSize: 14,
      fontWeight: primary ? 700 : 600,
      color: primary ? "#fff" : app.ink,
      background: primary ? app.accent : "#fff",
      border: primary ? "none" : `1px solid ${app.line}`,
      boxShadow: primary ? "0 8px 20px rgba(91,95,240,.30)" : "none",
      transform: pressed ? "scale(0.95)" : undefined,
      opacity: disabled ? 0.5 : 1,
      whiteSpace: "nowrap",
      ...style,
    }}
  >
    {children}
  </div>
);

export const Progress: React.FC<{ value: number; text?: string; color?: string }> = ({ value, text, color = app.accent }) => (
  <div>
    {text && <div style={{ fontSize: 12, color: app.ink, marginBottom: 4 }}>{text}</div>}
    <div style={{ height: 6, borderRadius: 99, background: "#e8eaf4" }}>
      <div style={{ width: `${Math.min(value, 1) * 100}%`, height: "100%", borderRadius: 99, background: color }} />
    </div>
  </div>
);

export const Caption: React.FC<{ children: React.ReactNode; style?: React.CSSProperties }> = ({ children, style }) => (
  <div style={{ fontSize: 13, color: app.muted, lineHeight: 1.45, ...style }}>{children}</div>
);

export const Spinner: React.FC<{ size?: number }> = ({ size = 16 }) => {
  const frame = useCurrentFrame();
  return (
    <div
      style={{
        width: size,
        height: size,
        borderRadius: 99,
        border: `2.5px solid ${app.accentSoft}`,
        borderTopColor: app.accent,
        transform: `rotate(${frame * 14}deg)`,
        flexShrink: 0,
      }}
    />
  );
};

/** A text input that reveals `text` one character at a time between `from` and `to` frames. */
export const typed = (frame: number, text: string, from: number, to: number) =>
  text.slice(0, Math.round(interpolate(frame, [from, to], [0, text.length], clamp)));

// ---------- app shell ----------

export type TaskItem = { kind: Kind; tag: string; title: string; when: string; active?: boolean };
export type TaskGroup = { title: string; items: TaskItem[] };

export const AppShell: React.FC<{
  account: { name: string; sub: string };
  groups: TaskGroup[];
  calendarActive?: boolean;
  footer?: React.ReactNode;
  children: React.ReactNode;
}> = ({ account, groups, calendarActive = true, footer, children }) => (
  <div style={{ position: "absolute", inset: 0, background: app.page, fontFamily, color: app.ink }}>
    {/* sidebar */}
    <div style={{ position: "absolute", left: 0, top: 0, bottom: 0, width: 286, background: "#f7f8fc", padding: "22px 16px", display: "flex", flexDirection: "column", gap: 16 }}>
      <div style={{ display: "flex", alignItems: "center", gap: 10, marginLeft: 4 }}>
        <LogoIcon size={34} />
        <span style={{ fontSize: 22, fontWeight: 800, letterSpacing: -0.4 }}>NextUp</span>
      </div>
      <div style={{ background: "#fff", borderRadius: 22, padding: "12px 10px 14px", boxShadow: app.shadow, flex: 1, overflow: "hidden" }}>
        <div
          style={{
            display: "flex",
            alignItems: "center",
            gap: 8,
            padding: "8px 12px",
            borderRadius: 12,
            fontSize: 14,
            fontWeight: 600,
            background: calendarActive ? app.accentSoft : "transparent",
            color: calendarActive ? app.accent : app.ink,
          }}
        >
          <Icon name="calendar" size={17} /> Calendar
        </div>
        <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", padding: "10px 6px 4px" }}>
          <span style={{ fontSize: 13, fontWeight: 700, color: app.muted }}>Tasks</span>
          <div style={{ display: "flex", gap: 2, padding: 3, borderRadius: 99, background: "#eef0f7", fontSize: 12, fontWeight: 700 }}>
            <span style={{ padding: "2px 12px", borderRadius: 99, background: "#fff", color: app.accent, boxShadow: "0 2px 8px rgba(76,86,150,.16)" }}>Week</span>
            <span style={{ padding: "2px 12px", color: app.muted }}>Month</span>
          </div>
        </div>
        {groups
          .filter((g) => g.items.length)
          .map((g) => (
            <div key={g.title}>
              <Caption style={{ fontSize: 12, padding: "10px 8px 2px" }}>
                {g.title} · {g.items.length}
              </Caption>
              {g.items.map((it) => (
                <div
                  key={it.title + it.tag}
                  style={{
                    padding: "6px 10px",
                    borderRadius: 12,
                    background: it.active ? app.accentSoft : "transparent",
                  }}
                >
                  <div style={{ fontSize: 13, fontWeight: 700, display: "flex", gap: 6, alignItems: "center" }}>
                    <Badge kind={it.kind} size={11}>
                      {it.tag}
                    </Badge>
                    <span style={{ whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis" }}>{it.title}</span>
                  </div>
                  <div style={{ fontSize: 12, color: app.muted }}>{it.when}</div>
                </div>
              ))}
            </div>
          ))}
        {footer}
      </div>
      <div style={{ background: "#fff", borderRadius: 18, padding: "10px 14px", boxShadow: app.shadow, display: "flex", gap: 10, alignItems: "center" }}>
        <div style={{ width: 30, height: 30, borderRadius: 99, background: app.accentSoft, color: app.accent, display: "grid", placeItems: "center", fontWeight: 800, fontSize: 14 }}>
          {account.name[0]}
        </div>
        <div style={{ lineHeight: 1.2 }}>
          <div style={{ fontSize: 14, fontWeight: 700 }}>{account.name}</div>
          <div style={{ fontSize: 12, color: app.muted }}>{account.sub}</div>
        </div>
      </div>
    </div>
    {/* main */}
    <div style={{ position: "absolute", left: 286, top: 0, right: 0, bottom: 0 }}>{children}</div>
  </div>
);

export const COORD_ACCOUNT = { name: "Alice · Coordinator", sub: "Valley Community Pantry" };
export const MICHAEL_ACCOUNT = { name: "Michael Brooks", sub: "Volunteer · Valley Community Pantry" };

const when = (sh: Shift) => {
  const day = DAYS[sh.day].split(" ");
  const h = sh.start > 12 ? `${sh.start - 12}:00 PM` : `${sh.start}:00 ${sh.start === 12 ? "PM" : "AM"}`;
  return `${day[0][0]}${day[0].slice(1).toLowerCase()} ${day[1]} · ${h}`;
};

/** Coordinator sidebar groups, derived from the same events as the calendar. */
export const coordGroups = (events: CalEvent[], activeId?: string): TaskGroup[] => {
  const todo: TaskItem[] = [];
  const covered: TaskItem[] = [];
  for (const e of events) {
    const fill = `${e.shift.conf}/${e.shift.req}`;
    const item = { title: e.shift.title, when: when(e.shift), active: e.shift.id === activeId };
    if (e.kind === "weather") todo.push({ ...item, kind: "weather", tag: "weather" });
    else if (e.kind === "pending") todo.push({ ...item, kind: "pending", tag: "review" });
    else if (e.kind === "open") todo.push({ ...item, kind: "open", tag: fill });
    else covered.push({ ...item, kind: "filled", tag: fill });
  }
  return [
    { title: "Needs action", items: todo },
    { title: "Covered", items: covered.slice(0, 4) },
  ];
};

export const michaelGroups = (cancelled = false): TaskGroup[] => [
  {
    title: "My shifts",
    items: [
      { kind: "filled" as Kind, tag: "signed up", title: "Senior Grocery Delivery", when: when(shiftById("senior")) },
      ...(cancelled ? [] : [{ kind: "filled" as Kind, tag: "signed up", title: "Saturday Delivery Run", when: when(shiftById("delivery")) }]),
    ],
  },
  { title: "Recommended", items: [{ kind: "recommended", tag: "for you", title: "Truck Unloading", when: when(shiftById("truck")) }] },
];

// ---------- calendar ----------

export const CAL = { left: 18, top: 18, width: 1118, height: 720, toolbar: 58, header: 40, axis: 52, startHour: 8, endHour: 20 };
const gridH = CAL.height - CAL.toolbar - CAL.header - 24;
const hourH = gridH / (CAL.endHour - CAL.startHour);
const colW = (CAL.width - 48 - CAL.axis) / 7;

/** Viewport position of the middle of a shift's event block (for the cursor). */
export const eventCenter = (sh: Shift) => ({
  x: 286 + CAL.left + 24 + CAL.axis + colW * sh.day + colW / 2,
  y: CAL.top + 16 + CAL.toolbar + CAL.header + ((sh.start + sh.end) / 2 - CAL.startHour) * hourH,
});

export const WeekCalendar: React.FC<{ events: CalEvent[]; legend: [string, Kind][] }> = ({ events, legend }) => {
  const frame = useCurrentFrame();
  return (
    <>
      <div
        style={{
          position: "absolute",
          left: CAL.left,
          top: CAL.top,
          width: CAL.width,
          height: CAL.height,
          background: "#fff",
          borderRadius: 26,
          boxShadow: app.shadow,
          padding: "16px 24px",
        }}
      >
        <div style={{ height: CAL.toolbar, display: "flex", alignItems: "center", justifyContent: "space-between" }}>
          <div style={{ display: "flex", alignItems: "center", gap: 12, fontSize: 24, fontWeight: 800, letterSpacing: -0.4 }}>
            <span style={{ color: app.ink, fontSize: 18 }}>‹ ›</span> Oct 11 – 17, 2026
          </div>
          <div style={{ padding: "6px 16px", borderRadius: 99, background: app.page, fontWeight: 700, fontSize: 14 }}>Today</div>
        </div>
        <div style={{ display: "flex", height: CAL.header, background: "#f7f8fc", marginLeft: CAL.axis, alignItems: "center" }}>
          {DAYS.map((d, i) => (
            <div key={d} style={{ width: colW, textAlign: "center", fontSize: 13, fontWeight: 700, letterSpacing: 0.4, color: i === 0 ? app.accent : app.muted }}>
              {d}
            </div>
          ))}
        </div>
        <div style={{ position: "relative", height: gridH }}>
          {Array.from({ length: CAL.endHour - CAL.startHour }, (_, i) => (
            <div key={i} style={{ position: "absolute", left: 0, right: 0, top: i * hourH, borderTop: i ? "1px solid #eef0f6" : "none" }}>
              <span style={{ position: "absolute", left: 0, top: 4, fontSize: 11, fontWeight: 600, color: app.muted }}>
                {String(CAL.startHour + i).padStart(2, "0")}:00
              </span>
            </div>
          ))}
          {Array.from({ length: 7 }, (_, i) => (
            <div key={i} style={{ position: "absolute", top: 0, bottom: 0, left: CAL.axis + colW * i, borderLeft: "1px solid #eef0f6" }} />
          ))}
          {events.map((e) => {
            const k = KINDS[e.kind];
            const pulse = e.pulseAt === undefined ? 0 : interpolate(frame, [e.pulseAt, e.pulseAt + 8, e.pulseAt + 22], [0, 1, 0], clamp);
            return (
              <div
                key={e.shift.id}
                style={{
                  position: "absolute",
                  left: CAL.axis + colW * e.shift.day + 3,
                  width: colW - 6,
                  top: (e.shift.start - CAL.startHour) * hourH + 2,
                  height: (e.shift.end - e.shift.start) * hourH - 4,
                  background: k.bg,
                  color: k.text,
                  borderLeft: `5px solid ${k.bar}`,
                  borderRadius: "4px 12px 12px 4px",
                  padding: "6px 8px",
                  display: "flex",
                  flexDirection: "column",
                  justifyContent: "space-between",
                  boxShadow: pulse ? `0 0 0 ${4 * pulse}px ${k.bar}55` : "none",
                  transform: `scale(${1 + 0.04 * pulse})`,
                }}
              >
                <div style={{ fontSize: 13, fontWeight: 700, lineHeight: 1.2 }}>{e.title}</div>
                <div style={{ fontSize: 11, fontWeight: 600, opacity: 0.85 }}>
                  {String(e.shift.start).padStart(2, "0")}:00 - {String(e.shift.end).padStart(2, "0")}:00
                </div>
              </div>
            );
          })}
        </div>
      </div>
      <div style={{ position: "absolute", left: CAL.left + 6, top: CAL.top + CAL.height + 16, display: "flex", gap: 8 }}>
        {legend.map(([label, kind]) => (
          <Badge key={label} kind={kind} size={13}>
            {label}
          </Badge>
        ))}
      </div>
    </>
  );
};

export const COORD_LEGEND: [string, Kind][] = [
  ["Needs volunteers", "open"],
  ["Filled", "filled"],
  ["Proposal to review", "pending"],
  ["Weather alert", "weather"],
];
export const VOL_LEGEND: [string, Kind][] = [
  ["My shift", "filled"],
  ["Request for you", "pending"],
  ["Recommended", "recommended"],
  ["Open, fits you", "open"],
  ["Outside your availability", "muted"],
];

// ---------- floating panels ----------

/** Right-hand floating panel (side peek / proposals), slides in from the right at `delay`. */
export const SidePanel: React.FC<{ delay?: number; width?: number; bottom?: number; children: React.ReactNode; scroll?: number }> = ({
  delay = 0,
  width = 400,
  bottom = 16,
  children,
  scroll = 0,
}) => {
  const p = useEnter(delay);
  return (
    <div
      style={{
        position: "absolute",
        right: 16,
        top: 16,
        bottom,
        width,
        background: "#fff",
        borderRadius: 26,
        boxShadow: app.shadowLg,
        opacity: p,
        transform: `translateX(${(1 - p) * 30}px)`,
        overflow: "hidden",
        zIndex: 5,
      }}
    >
      <div style={{ padding: "16px 20px 24px", transform: `translateY(${-scroll}px)` }}>{children}</div>
    </div>
  );
};

export const fmtHour = (h: number) => `${h > 12 ? h - 12 : h}:00 ${h >= 12 ? "PM" : "AM"}`;

export const ShiftHeader: React.FC<{ sh: Shift; label: string; kind: Kind; place: string; date?: string }> = ({
  sh,
  label,
  kind,
  place,
  date = "Saturday, Oct 17",
}) => (
  <div>
    <div style={{ fontSize: 20, fontWeight: 800, marginBottom: 4 }}>
      {sh.title} <Badge kind={kind}>{label}</Badge>
    </div>
    <Caption>
      {date} · {fmtHour(sh.start)}–{fmtHour(sh.end)} · {place}
    </Caption>
    <div style={{ marginTop: 10 }}>
      <Progress value={sh.conf / sh.req} text={`${sh.conf}/${sh.req} filled`} color={sh.conf >= sh.req ? "#5aa469" : app.accent} />
    </div>
  </div>
);

export const PeekTop: React.FC = () => (
  <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", fontSize: 14, fontWeight: 600, marginBottom: 12 }}>
    <span>⤢ Open page</span>
    <span style={{ color: app.muted }}>
      <Icon name="close" size={16} />
    </span>
  </div>
);

export const Toast: React.FC<{ at: number; text: string; until?: number }> = ({ at, text, until }) => {
  const frame = useCurrentFrame();
  const p = useEnter(at);
  const out = until === undefined ? 1 : interpolate(frame, [until - 6, until], [1, 0], clamp);
  if (frame < at) return null;
  return (
    <div
      style={{
        position: "absolute",
        right: 24,
        bottom: 24,
        zIndex: 40,
        opacity: p * out,
        transform: `translateY(${(1 - p) * 20}px)`,
        background: "#fff",
        borderRadius: 14,
        boxShadow: app.shadowLg,
        padding: "14px 20px",
        fontSize: 15,
        fontWeight: 600,
        display: "flex",
        gap: 10,
        alignItems: "center",
        border: `1px solid ${app.line}`,
      }}
    >
      <span style={{ color: "#3a7a4a" }}>
        <Icon name="check" size={18} />
      </span>
      {text}
    </div>
  );
};

export const Fab: React.FC<{ open?: boolean; pressed?: boolean }> = ({ open, pressed }) => (
  <div
    style={{
      position: "absolute",
      right: 26,
      bottom: 26,
      width: 54,
      height: 54,
      borderRadius: 99,
      background: app.accent,
      color: "#fff",
      display: "grid",
      placeItems: "center",
      boxShadow: "0 12px 28px rgba(91,95,240,.45)",
      transform: pressed ? "scale(0.92)" : undefined,
      zIndex: 20,
    }}
  >
    <Icon name={open ? "close" : "spark"} size={24} color="#fff" />
  </div>
);

// ---------- cursor ----------

export type Waypoint = [frame: number, x: number, y: number];

/** Pointer that eases between waypoints; a ring pulses at each click frame. */
export const Cursor: React.FC<{ path: Waypoint[]; clicks?: number[]; hideAfter?: number }> = ({ path, clicks = [], hideAfter }) => {
  const frame = useCurrentFrame();
  if (hideAfter !== undefined && frame > hideAfter) return null;
  let x = path[0][1];
  let y = path[0][2];
  for (let i = 1; i < path.length; i++) {
    const [f0, x0, y0] = path[i - 1];
    const [f1, x1, y1] = path[i];
    if (frame >= f0) {
      const t = interpolate(frame, [f0, f1], [0, 1], { ...clamp, easing: Easing.inOut(Easing.cubic) });
      x = x0 + (x1 - x0) * t;
      y = y0 + (y1 - y0) * t;
    }
  }
  const click = clicks.find((c) => frame >= c && frame < c + 14);
  const r = click === undefined ? 0 : (frame - click) / 14;
  return (
    <div style={{ position: "absolute", left: x, top: y, zIndex: 100, pointerEvents: "none" }}>
      {click !== undefined && (
        <div
          style={{
            position: "absolute",
            left: -22 * r - 4,
            top: -22 * r - 4,
            width: 44 * r + 8,
            height: 44 * r + 8,
            borderRadius: 99,
            border: `3px solid ${app.accent}`,
            opacity: 1 - r,
          }}
        />
      )}
      <svg width="26" height="30" viewBox="0 0 26 30" style={{ filter: "drop-shadow(0 3px 4px rgba(0,0,0,.3))" }}>
        <path d="M2 2 L2 24 L8 18.5 L12.5 28 L16.5 26 L12 17 L20 17 Z" fill="#1f2547" stroke="#fff" strokeWidth="2" strokeLinejoin="round" />
      </svg>
    </div>
  );
};

/** True while a click on frame `at` is "pressing" its button. */
export const pressed = (frame: number, at: number) => frame >= at - 2 && frame < at + 5;

import React from "react";
import { AbsoluteFill, Easing, interpolate, useCurrentFrame } from "remotion";
import { brand } from "../theme";
import { s } from "../timing";
import { Icon } from "../ui/app";
import { Captions, clamp, FadeSlide, SceneShell, useEnter } from "../ui/overlay";

// Scene 8: one headline number (14/15 LLM scenario runs passed = 93%, from the README's
// evaluation) and how every agent action is checked. No other figures on purpose.
const SUCCESS = 93;

const GUARDS: [title: string, detail: string][] = [
  ["Only real volunteers", "Every proposed person must come from a search in the same run."],
  ["Rules enforced in code", "Unavailable, already confirmed, or declined? Blocked before Alice sees it."],
  ["Every step logged", "Each thought and tool call is saved, so Alice can see why."],
  ["Human approval", "Nothing reaches a volunteer until the coordinator approves."],
];

const card: React.CSSProperties = {
  background: "rgba(255,255,255,.94)",
  border: `1px solid ${brand.border}`,
  borderRadius: 12,
  boxShadow: "0 24px 60px rgba(31,37,71,.25)",
};

const Ring: React.FC<{ delay: number }> = ({ delay }) => {
  const frame = useCurrentFrame();
  const p = useEnter(delay);
  const value = interpolate(frame, [delay + 6, delay + 56], [0, SUCCESS], { ...clamp, easing: Easing.out(Easing.cubic) });
  const R = 150;
  const C = 2 * Math.PI * R;
  return (
    <div style={{ ...card, opacity: p, transform: `translateY(${(1 - p) * 20}px)`, width: 600, padding: "44px 40px", display: "flex", flexDirection: "column", alignItems: "center" }}>
      <div style={{ position: "relative", width: 360, height: 360 }}>
        <svg width={360} height={360} viewBox="0 0 360 360" style={{ transform: "rotate(-90deg)" }}>
          <circle cx={180} cy={180} r={R} fill="none" stroke="#e8eaf4" strokeWidth={26} />
          <circle
            cx={180}
            cy={180}
            r={R}
            fill="none"
            stroke={brand.primary}
            strokeWidth={26}
            strokeLinecap="round"
            strokeDasharray={C}
            strokeDashoffset={C * (1 - value / 100)}
          />
        </svg>
        <div style={{ position: "absolute", inset: 0, display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center" }}>
          <div style={{ fontSize: 112, fontWeight: 800, color: brand.text, letterSpacing: -3, lineHeight: 1 }}>{Math.round(value)}%</div>
        </div>
      </div>
      <div style={{ fontSize: 36, fontWeight: 800, marginTop: 26 }}>scenario success rate</div>
      <div style={{ fontSize: 22, color: brand.muted, marginTop: 6 }}>real model · AI scenarios, 3 runs each</div>
    </div>
  );
};

const Guard: React.FC<{ title: string; detail: string; delay: number }> = ({ title, detail, delay }) => {
  const p = useEnter(delay);
  const tick = useEnter(delay + 8);
  return (
    <div style={{ display: "flex", gap: 20, alignItems: "flex-start", padding: "18px 0", opacity: p, transform: `translateX(${(1 - p) * 24}px)` }}>
      <div
        style={{
          width: 46,
          height: 46,
          borderRadius: 999,
          flexShrink: 0,
          background: brand.green,
          display: "grid",
          placeItems: "center",
          transform: `scale(${0.6 + 0.4 * tick})`,
        }}
      >
        <Icon name="check" size={26} color="#fff" />
      </div>
      <div>
        <div style={{ fontSize: 30, fontWeight: 800 }}>{title}</div>
        <div style={{ fontSize: 22, color: brand.muted, marginTop: 4, lineHeight: 1.35 }}>{detail}</div>
      </div>
    </div>
  );
};

export const Results: React.FC = () => {
  const panel = useEnter(s(4.5));
  return (
    <SceneShell>
      <AbsoluteFill style={{ padding: "64px 110px 0", alignItems: "center" }}>
        <FadeSlide delay={0} style={{ fontSize: 50, fontWeight: 800, letterSpacing: -1, color: "#fff", textShadow: "0 4px 24px rgba(31,37,71,.55)", marginBottom: 40 }}>
          Tested on real scenarios, with the real model
        </FadeSlide>
        <div style={{ display: "flex", gap: 40, alignItems: "stretch" }}>
          <Ring delay={s(0.6)} />
          <div style={{ ...card, opacity: panel, transform: `translateY(${(1 - panel) * 20}px)`, width: 980, padding: "30px 44px" }}>
            <div style={{ fontSize: 22, fontWeight: 800, color: brand.primary, letterSpacing: 1.2, textTransform: "uppercase" }}>
              Every agent action is checked
            </div>
            {GUARDS.map(([title, detail], i) => (
              <Guard key={title} title={title} detail={detail} delay={s(5.2 + i * 1.6)} />
            ))}
          </div>
        </div>
      </AbsoluteFill>
      <Captions
        cues={[
          [0.5, "On the real model, 93% of scenario runs passed."],
          [4.8, "And we watch every action the agent takes:"],
          [8.4, "only real volunteers, rules enforced in code,"],
          [11.6, "every step logged, and nothing sent without approval."],
        ]}
      />
    </SceneShell>
  );
};

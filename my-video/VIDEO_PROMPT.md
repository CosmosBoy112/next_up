Build a 90-second product demo video for **NextUp** in this Remotion project.

## Product context
NextUp is an AI agent for volunteer coordinators at small nonprofits. **The agent does the work; the coordinator stays in charge.** When a volunteer cancels, the agent finds the best available replacements (free for the whole shift, right skills, fair recent workload), drafts personal messages, and proposes them. Nothing is sent until the coordinator approves. Built with Luminal (LLM inference) and MongoDB Atlas (Vector Search, Change Streams, transactions). Fictional organization: *Valley Community Pantry*.

## Technical spec
- One composition `NextUpDemo`: 1920×1080, 30 fps, **2700 frames (90 s)**. Register it in `src/Root.tsx`.
- One file per scene in `src/scenes/`, sequenced with `<Series>` or `<Sequence>`. Keep timings in one constants file so they're easy to retime.
- Brand: primary `#5b5ff0`, text `#1f2547`, muted `#5b6080`, light background `#f3f4fa`, card border `#e4e7f2`, white cards with 12px radius. Font: **Nunito Sans** via `@remotion/google-fonts`.
- Motion: subtle and professional. `spring()` fade/slide-ins of about 12–18 frames, no flashy transitions. Use `interpolate` with `extrapolateRight: "clamp"`.
- **Screen recordings** will be placed in `public/` with the filenames below. Render each one with `<OffthreadVideo>` inside a rounded "browser window" frame on the light background. If a file is missing, show a labeled placeholder card so the video still renders.
- **Captions on every scene** (many judges watch muted): a bottom-center pill with the narration line, white text on a `#1f2547` pill at 85% opacity.
- Optional voice-over: if `public/voiceover.mp3` exists, play it with `<Audio>`; otherwise skip it. Same for `public/music.mp3` at low volume (0.15).

## Scenes (timings in seconds)

| # | Time | Visual | Caption / narration |
|---|---|---|---|
| 1 | 0–3 | NextUp logo (wordmark + a double-chevron "up" icon in primary color) fades and scales in on white. Tagline below. | *Your volunteers, covered.* |
| 2 | 3–11 | `michael.mp4` (volunteer calendar). Name tag slides in top-left: **Michael · Volunteer** | "Hey, this is Michael. He volunteers for Valley Community Pantry's Saturday delivery run. Cancelling used to mean a guilty group text, and hoping someone sees it." |
| 3 | 11–19 | `alice.mp4` (coordinator calendar). Name tag: **Alice · Event Coordinator** | "And this is Alice, the event coordinator. Every cancellation meant spreadsheets, a dozen texts, and asking the same reliable people until they burned out." |
| 4 | 19–22 | Title card on primary background, white text | **The agent proposes. The coordinator decides.** |
| 5 | 22–50 | **Scenario 1: Last-minute cancellation.** Chapter label "1 · Cancellation". Play `scenario1.mp4`. Add callout badges at these offsets: 0 s "1-click cancel", 6 s "⏳ agent working…" (small, top-right, 1 s), 8 s three checks appearing one by one: "Available ✓", "Driver ✓", "Fair workload ✓"; 14 s "Full audit trail"; 19 s "Human approval required"; 25 s "Filled ✓" (green). | "Michael can't make Saturday. One click. Within seconds, the agent finds people who are free, can drive, and haven't been overworked, and drafts a message for each. Every step is logged. Nothing is sent until Alice approves. The volunteer accepts from the email, and the shift is covered." |
| 6 | 50–60 | **Scenario 2: Ask in plain English.** Chapter "2 · Ask". `scenario2.mp4`. Animate the typed request in a chat bubble overlay: *"Need 2 more drivers for Saturday's pantry delivery"*. Badge: "Drivers only ✓". | "Alice can also just ask. The agent finds the shift and proposes only people who can drive." |
| 7 | 60–72 | **Scenario 3: Weather risk.** Chapter "3 · Weather". `scenario3.mp4`. Badges: "Storm forecast Sat", then "Alternatives proposed", then "Crew notified ✓". | "It watches the forecast too. A storm on Saturday? The agent proposes alternatives, Alice picks one, and the whole crew is notified." |
| 8 | 72–87 | **Results.** Heading "Tested on 10 scenarios · real model · 3 runs each". Six stat cards in a 3×2 grid, staggered in about 2 s apart; each big number counts up from 0. | "Zero rule violations. Zero made-up volunteers. The least-busy volunteer ranked first every time. No shift was ever overfilled." |
| 9 | 87–90 | Logo again, with "Built with Luminal · MongoDB Atlas" and the repo URL `github.com/CosmosBoy112/next_up` | "NextUp. The agent does the work. The coordinator stays in charge." |

### Stat cards for scene 8 (use exactly these values; don't invent others)
1. **0** rule violations: *across 15 agent runs*
2. **0** invented volunteers
3. **3/3** least-busy volunteer ranked first
4. **0** overfilled shifts: *concurrent accepts · MongoDB transactions*
5. **14/15** scenario runs passed: *+ 5/5 platform checks*
6. **<20 s** from cancellation to ranked proposal

Small footnote under the grid (muted, 18px): *Measured with DeepSeek-V4.1-Flash on a 12-volunteer test fixture.*

## Deliverables
- The composition renders without errors with `npx remotion render NextUpDemo out/nextup-demo.mp4`, even before the screen recordings exist (placeholders).
- Brief README notes listing the asset filenames to drop into `public/`: `michael.mp4`, `alice.mp4`, `scenario1.mp4`, `scenario2.mp4`, `scenario3.mp4`, and optional `voiceover.mp3` and `music.mp3`.
- Don't add stats, claims, or features beyond those listed above.

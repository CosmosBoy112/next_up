# Phase 5 — README, demo hardening, submission prep (target: 30 min)

Feature freeze. Only fixes and documentation from here on.

## Tasks
1. **Hardening**
   - Run the full demo script from Phase 4 three times in a row after `reset_demo.py`. Fix anything flaky.
   - Make sure every UI action survives an LLM timeout (show an error toast, keep the app alive).
   - Confirm no secrets are in the repo: `git grep -i "api_key\|mongodb+srv"` must only show `.env.example` placeholders.
2. **README.md** with these sections, in this order:
   1. One-line pitch + a GIF/screenshot placeholder at the top
   2. **The problem**: one paragraph based on the coordinator interview. Leave a clearly marked `<!-- TODO: interview quote -->` placeholder for the user to fill in. Do not invent a quote.
   3. **How it works**: a diagram (ASCII or Mermaid) of Volunteer UI ↔ MongoDB ↔ Agent ↔ Coordinator UI
   4. **The coordinator stays in charge**: explain that the agent's only write tools are `propose_action` and `log_note`; every outreach requires approval; every decision is auditable in `agent_log`
   5. **Why MongoDB** (aura section): a table mapping each feature (document model, Atlas Vector Search with filters, Change Streams with resume tokens, aggregation pipelines, transactions for accept, audit log) to where it is used in the code, with file paths
   6. **Agent design**: hand-written ReAct harness, tool list, fairness heuristic, validation that blocks hallucinated volunteer IDs, JSON-mode fallback
   7. **Run it locally**: env setup, `check_env.py`, `reset_demo.py`, `worker.py`, `streamlit run app.py`
   8. **Demo script**: the 7 steps from Phase 4
   9. **Built with**: Luminal (LLM inference), MongoDB Atlas, Streamlit, sentence-transformers
   10. **Limitations and next steps**: real SMS/email, auth, multi-org support, learning from coordinator edits
3. `DEMO_VIDEO_SCRIPT.md`: a 90-second shot list with timestamps:
   - 0–10 s: problem
   - 10–60 s: live flow (cancel → agent proposal → why → approve → accept)
   - 60–75 s: NL request
   - 75–90 s: MongoDB features + "coordinator stays in charge"
   Include the narration lines.

## Files you MAY create or change
`README.md`, `DEMO_VIDEO_SCRIPT.md`, and bug fixes anywhere (list each fix in the report).

## Files FROZEN
`00_SPEC.md`, phase files.

## Report back
The final checklist: demo passes 3×, no secrets, README complete except the interview TODO, and the commands to push to a public GitHub repo.

"""App-wide styles: a soft lavender-gray page with white rounded cards and an indigo accent.
Covers the sidebar (logo, nav card, period toggle, account), floating panels (side peek,
proposal panel, assistant chat), buttons, dialogs and property rows. Elements opt in via
st.container(key=...)."""

from __future__ import annotations

import streamlit as st

ACCENT = "#5b5ff0"
PAGE = "#f1f3f9"
SIDEBAR_PX = 300  # Streamlit's default sidebar width

# st.html strips inline <svg>, so the icon goes in as an <img> data URI.
_LOGO_SVG = ("<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24' fill='none' stroke='white' "
             "stroke-width='2.6' stroke-linecap='round' stroke-linejoin='round'>"
             "<path d='M6 13l6-6 6 6'/><path d='M6 19l6-6 6 6' opacity='.55'/></svg>")
LOGO_HTML = f"""
<div class="vo-brand">
  <span class="vo-logo"><img alt="" width="22" height="22"
    src="data:image/svg+xml;utf8,{_LOGO_SVG.replace('<', '%3C').replace('>', '%3E')}"></span>
  <span class="vo-name">NextUp</span>
</div>
"""


def logo() -> None:
    st.html(LOGO_HTML)


COORDINATOR = "Alice"


def _data_uri(svg: str) -> str:
    return "data:image/svg+xml;utf8," + svg.replace("<", "%3C").replace(">", "%3E").replace("#", "%23")


def initial_avatar(name: str, bg: str = "#fde3d6", fg: str = "#d2603a") -> str:
    """A rounded square with the person's initial, as an image for st.chat_message."""
    return _data_uri(f"<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 32 32'>"
                     f"<rect width='32' height='32' rx='8' fill='{bg}'/>"
                     f"<text x='16' y='21.5' text-anchor='middle' font-family='Nunito Sans,Arial,sans-serif' "
                     f"font-size='15' font-weight='700' fill='{fg}'>{name[:1].upper()}</text></svg>")


def account_avatar(name: str) -> None:
    """The initial in a circle at the start of the account switcher."""
    st.html(f"""<style>.st-key-account button::before {{ content: "{name[:1].upper()}"; }}</style>""")


def inject_css() -> None:
    st.html(f"""<style>
:root {{
  --vo-accent: {ACCENT}; --vo-accent-soft: #eceefe; --vo-ink: #1f2547; --vo-muted: #8a90a8;
  --vo-page: {PAGE}; --vo-card: #ffffff; --vo-line: #e4e7f2;
  --vo-shadow: 0 12px 40px rgba(76,86,150,.08); --vo-shadow-lg: 0 24px 60px rgba(76,86,150,.16);
}}
@keyframes vo-rise {{ from {{ opacity: 0; transform: translate(-50%, 18px); }} to {{ opacity: 1; transform: translate(-50%, 0); }} }}
@keyframes vo-pop  {{ from {{ opacity: 0; transform: scale(.6); }} to {{ opacity: 1; transform: none; }} }}
@keyframes vo-in-r {{ from {{ opacity: 0; transform: translateX(28px); }} to {{ opacity: 1; transform: none; }} }}

/* ---- Page ---- */
.stApp {{ background: var(--vo-page); color: var(--vo-ink); }}
[data-testid="stHeader"] {{ background: transparent; }}
[data-testid="stMainBlockContainer"] {{ padding-top: 2.6rem; }}

/* ---- White cards ---- */
.st-key-calwrap, .st-key-side_card, .st-key-account,
.st-key-peek, .st-key-proposals, .st-key-chatpanel, .st-key-chatbar {{
  background: var(--vo-card); border: none; box-shadow: var(--vo-shadow);
}}
.st-key-calwrap {{ border-radius: 28px; padding: 22px 24px 10px; }}
.st-key-side_card {{ border-radius: 24px; padding: 14px 12px 16px; }}
[data-testid="stVerticalBlockBorderWrapper"] {{ border-color: var(--vo-line); border-radius: 18px; }}

/* ---- Buttons ---- */
.stApp button[kind="secondary"], .stApp button[kind="secondaryFormSubmit"] {{
  background: #fff; border: 1px solid var(--vo-line); border-radius: 12px; color: var(--vo-ink);
  font-weight: 600; transition: border-color .15s ease, color .15s ease, box-shadow .15s ease;
}}
.stApp button[kind="secondary"]:hover {{
  border-color: var(--vo-accent); color: var(--vo-accent); box-shadow: 0 6px 18px rgba(91,95,240,.12);
}}
.stApp button[kind="primary"], .stApp button[kind="primaryFormSubmit"] {{
  border: none; border-radius: 12px; font-weight: 700; box-shadow: 0 8px 20px rgba(91,95,240,.30);
}}

/* ---- Sidebar ---- */
.vo-brand {{ display: flex; align-items: center; gap: 12px; margin: -44px 0 6px 4px; }}
.vo-logo {{
  width: 40px; height: 40px; border-radius: 12px; display: grid; place-items: center;
  background: linear-gradient(140deg, #7b7ff6, var(--vo-accent)); box-shadow: 0 8px 18px rgba(91,95,240,.35);
}}
.vo-name {{ font-size: 1.45rem; font-weight: 800; color: var(--vo-ink); letter-spacing: -.02em; }}

[data-testid="stSidebar"] button {{ justify-content: flex-start; text-align: left; border-radius: 12px; }}
[data-testid="stSidebar"] button > div,
[data-testid="stSidebar"] button > div > span {{ justify-content: flex-start; text-align: left; }}
[data-testid="stSidebar"] button[kind="secondary"] {{
  background: var(--vo-accent-soft); border-color: transparent; color: var(--vo-accent); box-shadow: none;
}}
[data-testid="stSidebar"] button[kind="secondary"] p, [data-testid="stSidebar"] button[kind="secondary"] strong {{
  color: var(--vo-accent);
}}
[data-testid="stSidebar"] button[kind="tertiary"]:hover {{ background: #f5f6fb; }}
[data-testid="stSidebar"] [data-testid="stCaptionContainer"] {{ margin-top: .4rem; }}

/* Week / Month pill toggle */
[data-testid="stSidebar"] [data-testid="stButtonGroup"] > div {{
  gap: 2px; padding: 3px; border-radius: 999px; background: #eef0f7;
}}
[data-testid="stSidebar"] button[data-variant="segmented_control"] {{
  justify-content: center; text-align: center; min-height: 28px; padding: 2px 14px;
  border: none !important; border-radius: 999px !important; background: transparent !important;
  color: var(--vo-muted) !important; font-size: .82rem; font-weight: 600; box-shadow: none;
  transition: background .2s ease, color .2s ease, box-shadow .2s ease;
}}
[data-testid="stSidebar"] button[data-variant="segmented_control"]:hover {{ color: var(--vo-ink) !important; }}
[data-testid="stSidebar"] button[data-variant="segmented_control"][aria-checked="true"] {{
  background: #fff !important; color: var(--vo-accent) !important; font-weight: 700;
  box-shadow: 0 2px 8px rgba(76,86,150,.16);
}}
[data-testid="stSidebar"] button[data-variant="segmented_control"] > div,
[data-testid="stSidebar"] button[data-variant="segmented_control"] > div > span {{ justify-content: center; }}

/* Account switcher pinned to the bottom of the sidebar */
.st-key-account {{ position: sticky; bottom: 10px; margin-top: 1rem; z-index: 5; border-radius: 18px; }}
.st-key-account button {{ padding: 8px 10px; gap: 12px; }}
.st-key-account button::before {{
  flex: none; width: 34px; height: 34px; border-radius: 50%; display: grid; place-items: center;
  background: var(--vo-accent-soft); color: var(--vo-accent); font-weight: 800; font-size: .95rem;
}}
.st-key-account button [data-testid="stIconMaterial"] {{ display: none; }}
.st-key-account [data-testid="stMarkdownContainer"] p {{ line-height: 1.25; }}

/* ---- Floating assistant ---- */
/* The chat is centered in the main area, beside the sidebar (when it's open and not overlaying),
   leaving room for the round button on the right. */
:root {{ --vo-side: 0px; }}
@media (min-width: 768px) {{
  .stApp:has([data-testid="stSidebar"][aria-expanded="true"]) {{ --vo-side: {SIDEBAR_PX}px; }}
}}
.stApp {{ --vo-chat-x: calc(var(--vo-side) + (100vw - var(--vo-side)) / 2);
          --vo-chat-w: min(760px, calc(100vw - var(--vo-side) - 190px)); }}
.st-key-fab {{ position: fixed; right: 28px; bottom: 28px; z-index: 1003; width: auto !important; }}
.st-key-fab button {{
  width: 58px; height: 58px; min-height: 58px; border-radius: 50% !important; padding: 0;
  border: none !important; color: #fff !important; background: var(--vo-accent) !important;
  box-shadow: 0 12px 28px rgba(91,95,240,.45) !important;
  transition: transform .18s ease; animation: vo-pop .25s ease-out;
}}
.st-key-fab button:hover {{ transform: translateY(-2px) scale(1.05); }}
.st-key-fab [data-testid="stIconMaterial"] {{ font-size: 1.7rem; }}

.st-key-chatbar {{
  position: fixed; left: var(--vo-chat-x); bottom: 28px; transform: translateX(-50%); z-index: 1002;
  width: var(--vo-chat-w); padding: 6px 8px 6px 22px; gap: .5rem;
  border-radius: 999px; box-shadow: var(--vo-shadow-lg); animation: vo-rise .28s ease-out;
}}
.st-key-chatbar [data-testid="stChatInput"], .st-key-chatbar [data-testid="stChatInput"] > div {{
  background: transparent !important; border: none !important; box-shadow: none !important;
}}
.st-key-chatbar textarea {{ background: transparent !important; font-size: 1.05rem; padding-right: 56px !important; }}
.st-key-chatbar [data-testid="stChatInputSubmitButton"] {{
  width: 46px; height: 46px; border-radius: 14px; color: #fff !important; background: var(--vo-accent) !important;
}}
.st-key-chatbar [data-testid="stChatInputSubmitButton"]:disabled {{ opacity: 1; }}
.st-key-chatbar [data-testid="stChatInputSubmitButton"] svg {{ fill: #fff; color: #fff; }}
.st-key-chat_spark {{ color: var(--vo-accent); width: auto !important; }}
.st-key-chat_spark [data-testid="stIconMaterial"] {{ font-size: 1.6rem; }}
.st-key-chatpanel [data-testid="stChatMessage"] {{ background: transparent; padding: .35rem 0; gap: .8rem; }}
.st-key-chatpanel [data-testid="stChatMessage"] > div:first-child [data-testid="stIconMaterial"] {{ color: var(--vo-accent); }}

.st-key-chatpanel {{
  position: fixed; left: var(--vo-chat-x); bottom: 118px; transform: translateX(-50%); z-index: 1002;
  width: var(--vo-chat-w); max-height: 58vh; overflow-y: auto; padding: 18px 22px;
  border-radius: 28px; box-shadow: var(--vo-shadow-lg); animation: vo-rise .28s ease-out;
}}

/* ---- Right-hand panels: side peek and agent proposals ---- */
.st-key-peek, .st-key-proposals {{
  position: fixed; right: 18px; top: 18px; bottom: 104px; z-index: 1001; overflow-y: auto;
  border-radius: 28px; box-shadow: var(--vo-shadow-lg); animation: vo-in-r .3s ease-out;
}}
.st-key-peek {{ width: min(420px, calc(100vw - 36px)); padding: 16px 22px 24px; }}
.st-key-proposals {{ width: min(480px, calc(100vw - 36px)); padding: 16px 20px 24px; }}

/* ---- Dialogs and popovers ---- */
[data-testid="stDialog"] {{ background: rgba(31,37,71,.22) !important; }}
[role="dialog"] {{
  background: #fff !important; border: none !important; border-radius: 22px !important;
  box-shadow: var(--vo-shadow-lg) !important;
}}

/* ---- Shift page ---- */
.st-key-props [data-testid="stHorizontalBlock"] {{ padding: 2px 8px; border-radius: 10px; }}
.st-key-props [data-testid="stHorizontalBlock"]:hover {{ background: #fff; }}
[data-testid="stProgressBarTrack"] {{ background: #e8eaf4; }}
[data-testid="stProgressBarTrack"] > div {{ background: var(--vo-accent); }}
[data-testid="stDataFrame"] {{ background: #fff; border-radius: 14px; box-shadow: var(--vo-shadow); }}
h1, h2, h3 {{ color: var(--vo-ink); letter-spacing: -.02em; }}
</style>""")


def reserve_right(width_px: int) -> None:
    """Keep page content clear of a fixed right-hand panel."""
    st.html(f"""<style>
@media (min-width: 1100px) {{ [data-testid="stMainBlockContainer"] {{ padding-right: {width_px + 40}px; }} }}
</style>""")

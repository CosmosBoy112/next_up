"""NextUp: Streamlit entry point. Run: streamlit run app.py"""

from __future__ import annotations

import streamlit as st

st.set_page_config(page_title="NextUp", page_icon=":material/keyboard_double_arrow_up:", layout="wide", initial_sidebar_state="expanded")

from core import db, repo  # noqa: E402
from core.config import ConfigError  # noqa: E402
from core.embeddings import get_model  # noqa: E402
from ui import coordinator_view, volunteer_view  # noqa: E402
from ui.common import show_flash  # noqa: E402
from ui.floating import inject_css, logo  # noqa: E402
from scripts.seed import ORG  # noqa: E402

@st.cache_resource(show_spinner="Connecting to MongoDB…")
def init_db():
    client = db.get_client()
    client.admin.command("ping")
    db.ensure_indexes()
    return client


@st.cache_resource(show_spinner="Loading embedding model…")
def init_model():
    return get_model()


def main() -> None:
    try:
        init_db()
        init_model()
    except ConfigError as e:
        st.error(str(e))
        st.stop()
    except Exception as e:  # noqa: BLE001
        st.error(f"Could not connect to MongoDB: {type(e).__name__}: {e}")
        st.stop()

    show_flash()
    inject_css()
    volunteers = repo.list_volunteers()
    view, volunteer = current_identity(volunteers)
    with st.sidebar:
        logo()
        if view == "Volunteer" and volunteer is not None:
            volunteer_view.sidebar(volunteer)
        elif view == "Coordinator":
            coordinator_view.sidebar()
        account_switcher(view, volunteer, volunteers)

    if view == "Volunteer":
        if volunteer is None:
            st.info("No volunteers yet. Run `python scripts/reset_demo.py`.")
            st.stop()
        volunteer_view.render(volunteer)
    else:
        coordinator_view.render()


def current_identity(volunteers: list[dict]) -> tuple[str, dict | None]:
    """Who we're viewing as, from the switcher's widget state. The switcher renders at the
    bottom of the sidebar, after the pages that depend on this."""
    view = st.session_state.get("view", "Coordinator")
    if view != "Volunteer" or not volunteers:
        return view, None
    by_name = {v["name"]: v for v in volunteers}
    name = st.session_state.get("as_volunteer")
    if name not in by_name:
        name = "Alex Rivera" if "Alex Rivera" in by_name else volunteers[0]["name"]
    return view, by_name[name]


def account_switcher(view: str, volunteer: dict | None, volunteers: list[dict]) -> None:
    """Bottom of the sidebar, like Slack/Notion: the current user; click to switch (demo has no login)."""
    if view == "Volunteer" and volunteer is not None:
        label, icon = f"**{volunteer['name']}**  \n:gray[Volunteer · {ORG}]", ":material/account_circle:"
    else:
        label, icon = f"**Coordinator**  \n:gray[{ORG}]", ":material/admin_panel_settings:"
    with st.container(key="account"), st.popover(label, icon=icon, type="tertiary", width="stretch"):
        st.radio("View as", ["Coordinator", "Volunteer"], key="view", horizontal=True)
        if st.session_state.get("view") == "Volunteer" and volunteers:
            names = [v["name"] for v in volunteers]
            st.selectbox("Volunteer", names, key="as_volunteer",
                         index=names.index(volunteer["name"]) if volunteer else 0)
        st.caption("Demo accounts: switch between the coordinator and any volunteer.")

main()

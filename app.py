"""VolunteerOps: Streamlit entry point. Run: streamlit run app.py"""

from __future__ import annotations

import streamlit as st

st.set_page_config(page_title="VolunteerOps", page_icon="🤝", layout="wide")

from core import db, repo  # noqa: E402
from core.config import ConfigError  # noqa: E402
from core.embeddings import get_model  # noqa: E402
from ui import coordinator_view, volunteer_view  # noqa: E402
from ui.common import show_flash  # noqa: E402


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
        st.error(f"⚙️ {e}")
        st.stop()
    except Exception as e:  # noqa: BLE001
        st.error(f"Could not connect to MongoDB: {type(e).__name__}: {e}")
        st.stop()

    show_flash()
    st.sidebar.title("🤝 VolunteerOps")
    st.sidebar.caption("Valley Community Pantry")
    view = st.sidebar.radio("View", ["Coordinator", "Volunteer"], key="view")

    if view == "Volunteer":
        volunteers = repo.list_volunteers()
        if not volunteers:
            st.info("No volunteers yet. Run `python scripts/reset_demo.py`.")
            st.stop()
        names = [v["name"] for v in volunteers]
        default = names.index("Alex Rivera") if "Alex Rivera" in names else 0
        name = st.sidebar.selectbox("Logged in as", names, index=default, key="as_volunteer")
        volunteer_view.render(next(v for v in volunteers if v["name"] == name))
    else:
        coordinator_view.render()

    st.sidebar.divider()
    st.sidebar.caption("🤖 The agent proposes. The coordinator decides.")


main()

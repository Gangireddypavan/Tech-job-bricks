import streamlit as st

st.set_page_config(page_title="HN Tech Job Market", page_icon=":material/insights:", layout="wide")

from backend import sidebar_filters  # noqa: E402  (set_page_config must run first)

pages = [
    st.Page("views/overview.py", title="Overview", icon=":material/insights:", default=True),
    st.Page("views/skills.py", title="Skills", icon=":material/code:"),
    st.Page("views/salary.py", title="Salary", icon=":material/payments:"),
    st.Page("views/locations.py", title="Locations", icon=":material/public:"),
    st.Page("views/explore.py", title="Explore posts", icon=":material/search:"),
    st.Page("views/ask.py", title="Ask a question", icon=":material/forum:"),
]
page = st.navigation(pages)

# The Ask page talks to Genie, which writes its own SQL, so the sidebar filters don't apply there.
if page.title != "Ask a question":
    sidebar_filters()

page.run()

import streamlit as st


def auth_sidebar() -> None:
    """Show the login state in the sidebar, with a log in or log out button."""
    with st.sidebar:
        if st.user.is_logged_in:
            st.caption(f"Logged in as {st.user.email}")
            st.button("Log out", on_click=st.logout)
        else:
            st.button("Log in", on_click=st.login)

import streamlit as st
st.set_page_config(layout="wide")

from utils.streamlit_db import DatabaseClient

db = DatabaseClient()

st.title("VarMT Database")

if st.button("Test Database Connection"):
    try:
        db.execute_query("SELECT 1")        
        st.success("✅ Connection successful!")
    except Exception as e:
        st.error(f"❌ Connection failed: {e}")
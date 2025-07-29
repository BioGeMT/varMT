import streamlit as st
from utils.streamlit_db import DatabaseClient

# Initialize database client
db = DatabaseClient()

st.title("VarMT Database")

if st.button("Test Database Connection"):
    try:
        variant_locations = db.execute_query("SELECT COUNT(*) as count FROM variant_locations")
        total_variants = db.execute_query("SELECT COUNT(*) as count FROM variants")
        
        st.success("✅ Connection successful!")
        st.dataframe(variant_locations)
        st.dataframe(total_variants)
        
    except Exception as e:
        st.error(f"❌ Connection failed: {e}")

st.info("Click the button above to test your PostgreSQL connection.")
import streamlit as st


st.set_page_config(page_title="Main page", page_icon="👋")
st.logo("st-website\dg-logo.png")
# @st.cache_resource
# def init_connection():
#     url = st.secrets["SUPABASE_URL"]
#     key = st.secrets["SUPABASE_KEY"]
#     return create_client(url, key)


st.markdown("# Welcome to the Horse Racing Odds Prediction")

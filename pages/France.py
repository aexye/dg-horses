import streamlit as st
import pandas as pd
from supabase import create_client, Client
from google.oauth2 import service_account
from google.cloud import bigquery

st.set_page_config(page_title="France horse racing", page_icon="🇫🇷")
st.logo("dg-logo.png")
#fr emoji: 🇫🇷

url = st.secrets["supabase_url"]
key = st.secrets["supabase_key"]
credentials = service_account.Credentials.from_service_account_info(
    st.secrets["gcp_service_account"]
)
supabase: Client = create_client(url, key)

@st.cache_data(ttl=600)
def get_data_fr():
    response_fr = supabase.table('fr_horse_racing').select('race_date', 'race_name', 'city', 'horse', 'jockey', 'odds_predicted').execute()
    response_fr = pd.DataFrame(response_fr.data)
    return response_fr


def main():
    st.title("Horse Racing Odds Prediction")
    response_fr = get_data_fr()
    response_fr_pre = response_fr[['race_date', 'race_name', 'city', 'horse', 'jockey', 'odds_predicted']]
    st.write(response_fr_pre)


if __name__ == "__main__":
    main()

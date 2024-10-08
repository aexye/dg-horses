import streamlit as st
import pandas as pd
import numpy as np
from supabase import create_client, Client
from google.oauth2 import service_account
from google.cloud import bigquery
import plotly.express as px

st.set_page_config(page_title="HK Horse Racing", page_icon="🇭🇰", layout="wide")
st.logo("dg-logo.png")
# Initialize clients (consider moving this to a separate function)
@st.cache_resource
def init_clients():
    url = st.secrets["supabase_url"]
    key = st.secrets["supabase_key"]
    supabase: Client = create_client(url, key)
    
    credentials = service_account.Credentials.from_service_account_info(
        st.secrets["gcp_service_account"]
    )
    bq_client = bigquery.Client(credentials=credentials)
    
    return supabase, bq_client

supabase, bq_client = init_clients()

# Fetch data from Supabase
@st.cache_data(ttl=600)
def get_data_hk():
    try:
        response_hk = supabase.table('hk_horse_racing_full').select('race_date', 'race_name', 'city', 'horse', 'jockey','odds', 'odds_predicted', 'horse_num', 'positive_hint', 'negative_hint', 'draw_norm', 'last_5_positions', 'odds_predicted_intial', 'winner_prob','trifecta_prob','quinella_prob','place_prob','last_place_prob').execute()
        df = pd.DataFrame(response_hk.data)
        df['race_date'] = pd.to_datetime(df['race_date'])
        df.rename(columns={'horse': 'Horse', 'jockey': 'Jockey', 'odds_predicted': 'Odds predicted', 'horse_num': 'Horse number', 'odds': 'Initial market odds', 'positive_hint': 'Betting hint (+)', 
                           'negative_hint': 'Betting hint (-)', 'last_5_positions': 'Last 5 races', 'draw_norm': 'Draw', 'odds_predicted_intial': 'Odds predicted (raw)',
                           'winner_prob': 'Win probability','trifecta_prob': 'Trifecta probability','quinella_prob': 'Quinella probability','place_prob': 'Place probability','last_place_prob': 'Last place probability'
                            }, inplace=True)
        return df
    except Exception as e:
        st.error(f"Error fetching data from Supabase: {e}")
        return pd.DataFrame()

# Fetch data from BigQuery
@st.cache_data(ttl=600)
def get_bigquery_data():
    query = "SELECT * FROM `data-gaming-425312.dbt_prod_fr_horse_racing.fr_model_stats`"
    try:
        df = bq_client.query(query).to_dataframe()
        df['race_date'] = pd.to_datetime(df['race_date'])
        return df
    except Exception as e:
        st.error(f"Error fetching data from BigQuery: {e}")
        return pd.DataFrame()

def display_race_data(df):
    st.subheader("Race Data")
    print(df.head())
    selected_city = st.selectbox("Select city", ["All"] + list(df['city'].unique()))
    
    # Filter dataframe by city if a specific city is selected
    if selected_city != "All":
        df = df[df['city'] == selected_city]
    
    selected = st.multiselect("Select race name", df['race_name'].unique())
    
    if selected:
        for race in selected:
            race_df = df[df['race_name'] == race]
            
            race_df['Odds difference'] = np.absolute(race_df['Initial market odds'] - race_df['Odds predicted'])
            odds_diff = race_df['Odds difference'].sum().round(2)
            #calculate over round
            race_df['market_overround'] = 1/race_df['Initial market odds']
            race_df['our_overround'] = 1/race_df['Odds predicted']
            market_ovr = (race_df['market_overround'].sum()).round(2)
            our_ovr = race_df['our_overround'].sum().round(2)
            
            # Get the race details for the header
            race_date = race_df['race_date'].iloc[0].strftime('%Y-%m-%d')
            city = race_df['city'].iloc[0]
            
            # Create a header for each race
            #make two columns view 
            
            st.markdown(f"### {race}")
            st.markdown(f"**Date:** {race_date} | **City:** {city}")
            # st.markdown(f"**Odds difference:** {odds_diff}")
            # st.markdown(f"**Market Overround:** {market_ovr} | **Our Overround:** {our_ovr}")
            
            # Display only horse, jockey, and odds
            display_df = race_df[['Horse number', 'Horse', 'Jockey', 'Draw', 'Last 5 races', 'Initial market odds', 'Odds predicted', 'Odds predicted (raw)', 'Betting hint (+)', 'Betting hint (-)']].reset_index(drop=True)
            display_df_prob = race_df[['Horse', 'Win probability', 'Trifecta probability', 'Quinella probability', 'Place probability', 'Last place probability']]
            display_df.index += 1  # Start index from 1 instead of 0
            display_df_prob.index += 1  # Start index from 1 instead of 0
            st.dataframe(display_df, use_container_width=True)
            st.dataframe(display_df_prob, use_container_width=True)
            st.markdown("---")  # Add a separator between races
    else:
        st.info("Please select at least one race name to display the data.")

def plot_accuracy(df):
    st.subheader("Accuracy metric")
    st.markdown("Accuracy over time metric - in other words, how well our model is predicting the top 3 finishers in each race. It is NOT the accuracy of the odds or overall accuracy of the model.")
    fig = px.bar(df, x='race_date', y='avg_acc_top3', title='Average Accuracy (Top 3)', labels={'avg_acc_top3': 'Accuracy', 'race_date': 'Date'})
    st.plotly_chart(fig, use_container_width=True)

def plot_earnings(df):
    st.subheader("Cumulative Earnings")
    st.markdown("This chart illustrates the earnings that would have resulted from betting $10 on the top 1 finisher in each race, using the closing odds to determine the payout. The chart shows the total amount of money that would have been earned if this strategy had been employed.")
    fig = px.bar(df, x='race_date', y='money_earned_top1', title='Cumulative Sum Earned (Top 1)', labels={'money_earned_top1': 'Earnings over time in $', 'race_date': 'Date'})
    st.plotly_chart(fig, use_container_width=True)

def main():
    st.title("🏇 HK Horse Racing Odds Prediction")
    
    tab1, tab2 = st.tabs(["Race Data", "Performance Metrics"])
    
    with tab1:
        st.subheader("Work in progress")
        # race_data = get_data_hk()
        # display_race_data(race_data)
        # st.dataframe(race_data)
    with tab2:
        st.subheader("Work in progress")
        # st.dataframe(bq_data)

if __name__ == "__main__":
    main()

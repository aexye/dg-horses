import streamlit as st
import pandas as pd
from supabase import create_client, Client
from google.oauth2 import service_account
from google.cloud import bigquery
import numpy as np

st.set_page_config(page_title="France horse racing", page_icon="🇫🇷", layout="wide")
st.logo("dg-logo.png")
#fr emoji: 🇫🇷

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
def get_data_fr():
    try:
        response_fr = supabase.table('fr_horse_racing').select('race_date', 'race_name', 'city', 'horse', 'jockey','odds', 'odds_predicted', 'horse_num', 'positive_hint', 'negative_hint').execute()
        df = pd.DataFrame(response_fr.data)
        df['race_date'] = pd.to_datetime(df['race_date'])
        df.rename(columns={'horse': 'Horse', 'jockey': 'Jockey', 'odds_predicted': 'Odds predicted', 'horse_num': 'Horse number', 'odds': 'Initial market odds', 'positive_hint': 'Betting hint (+)', 'negative_hint': 'Betting hint (-)'}, inplace=True)
        return df
    except Exception as e:
        st.error(f"Error fetching data from Supabase: {e}")
        return pd.DataFrame()

# Fetch data from BigQuery
@st.cache_data(ttl=600)
def get_bigquery_data():
    query = "SELECT * FROM `data-gaming-425312.dbt_prod_uk_horse_racing.uk_model_stats`"
    try:
        df = bq_client.query(query).to_dataframe()
        df['race_date'] = pd.to_datetime(df['race_date'])
        df['money_earned_top3_cm'] = df['money_earned_top3'].cumsum()
        return df
    except Exception as e:
        st.error(f"Error fetching data from BigQuery: {e}")
        return pd.DataFrame()

def display_race_data(df):
    st.subheader("Race Data")
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
            display_df = race_df[['Horse number', 'Horse', 'Jockey', 'Initial market odds', 'Odds predicted', 'Betting hint (+)', 'Betting hint (-)']].reset_index(drop=True)

            display_df.index += 1  # Start index from 1 instead of 0
            st.dataframe(display_df, use_container_width=True)
            
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
    st.markdown("This chart illustrates the cumulative earnings that would have resulted from betting $10 on the top 3 finishers in each race, using the closing odds to determine the payout. The chart shows the total amount of money that would have been earned if this strategy had been employed.")
    fig = px.area(df, x='race_date', y='money_earned_top3_cm', title='Cumulative Sum Earned (Top 3)', labels={'money_earned_top3_cm': 'Earnings over time in $', 'race_date': 'Date'})
    st.plotly_chart(fig, use_container_width=True)
    
def main():
    st.title("🏇 FR Horse Racing Odds Prediction")
    
    tab1, tab2, tab3 = st.tabs(["Race Data", "Performance Metrics", "Preview Demo"])
    
    with tab1:
        race_data = get_data_fr()
        display_race_data(race_data)
        # st.dataframe(race_data)
    with tab2:
        #placeholder
        st.markdown("Performance metrics will be displayed here.")
        # bq_data = get_bigquery_data()
        # col1, col2 = st.columns(2)
        # with col1:
        #     plot_accuracy(bq_data)
        # with col2:
        #     plot_earnings(bq_data)
    with tab3:
        st.title("Example of race preview with both per runner and general description")
        st.markdown("R1C7 COMPIÈGNE Prix des Hauts-de-France - 22.07.2024")

        preview_full = """
        # Race Preview

        As the gates prepare to open for this exciting 1600m hybrid track race, the anticipation builds for a thrilling contest. 
        
        **Bo Lywood** emerges as the clear favorite, despite a recent setback, with past victories hinting at potential glory. 
        Hot on his heels, **Iken** and **Alva** are primed to challenge, their recent performances suggesting they're in fine form.

        **Zvaroshka** and **Terredequerre** shouldn't be overlooked, both showing consistency that could translate into success today. 
        Meanwhile, **Sky Power** and **Lamento** face a tough challenge but could surprise if fortune favors them.

        The middle of the pack is anybody's guess, with several contenders poised to make a move. **Marzouk** and **Camelot Song** are particularly intriguing, their mixed recent results adding an element of unpredictability.

        From seasoned performers to potential dark horses, this race promises excitement at every turn. Will the favorite prevail, or will we witness an underdog steal the show? 
        The stage is set for a captivating contest that could go down to the wire!
        """

        st.markdown(preview_full)

        df_llm = pd.read_csv("pages/fr_betting_hints_llm.csv")
        df_llm = df_llm[['horse', 'preview']]
        st.dataframe(df_llm, use_container_width=True)
        
        
if __name__ == "__main__":
    main()

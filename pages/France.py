import streamlit as st
import pandas as pd
from supabase import create_client, Client
from google.oauth2 import service_account
from google.cloud import bigquery
import numpy as np
import plotly.express as px

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
        response_fr = supabase.table('fr_horse_racing').select('race_date', 'race_name', 'city', 'horse', 'jockey','odds', 'odds_predicted', 'horse_num', 'positive_hint', 'negative_hint', 'draw_norm', 'last_5_positions', 'odds_predicted_intial', 'winner_prob','trifecta_prob','quinella_prob','last_place_prob', 'race_time_off').execute()
        df = pd.DataFrame(response_fr.data)
        df['race_date'] = pd.to_datetime(df['race_date'])
        # convert 23:00:00 to 23:00
        df['race_time_off'] = df['race_time_off'].str[:-3]
        df.rename(columns={'horse': 'Horse', 'jockey': 'Jockey', 'odds_predicted': 'Odds predicted', 'horse_num': 'Horse number', 'odds': 'Initial market odds', 'positive_hint': 'Betting hint (+)', 
                           'negative_hint': 'Betting hint (-)', 'last_5_positions': 'Last 5 races', 'draw_norm': 'Draw', 'odds_predicted_intial': 'Odds predicted (raw)',
                           'winner_prob': 'Win probability','trifecta_prob': 'Top3 probability','quinella_prob': 'Top2 probability','last_place_prob': 'Last place probability'
                            }, inplace=True)
        return df
    except Exception as e:
        st.error(f"Error fetching data from Supabase: {e}")
        return pd.DataFrame()

# Fetch data from BigQuery
@st.cache_data(ttl=600)
def get_bigquery_data():
    query = "SELECT * FROM `data-gaming-425312.fr_horse_data.fr_data__predictions_stats`"
    try:
        df = bq_client.query(query).to_dataframe()
        df['race_date'] = pd.to_datetime(df['race_date'])
        return df
    except Exception as e:
        st.error(f"Error fetching data from BigQuery: {e}")
        return pd.DataFrame()

def display_race_data(df):
    st.subheader("Race Data")

    selected_city = st.selectbox("Select racecourse", ["All"] + list(df['city'].unique()))
    
    if selected_city != "All":
        df = df[df['city'] == selected_city]
    
    # Create a sortable race name with time
    df['race_name_with_time_off'] = df['race_time_off'] + " - " + df['race_name']
    
    # Sort the unique race names by time
    unique_races = sorted(df['race_name_with_time_off'].unique())
    selected = st.multiselect("Select race name", unique_races)
    
    if selected:
        for race in selected:
            # Extract just the race name part (after the time)
            race_name = race.split(" - ", 1)[1]
            race_df = df[df['race_name'] == race_name]
            
            # Check if race_df is not empty before proceeding
            if race_df.empty:
                st.warning(f"No data found for race: {race}")
                continue
                
            race_df['Odds difference'] = np.absolute(race_df['Initial market odds'] - race_df['Odds predicted'])
            odds_diff = race_df['Odds difference'].sum().round(2)
            race_df['market_overround'] = 1/race_df['Initial market odds']
            race_df['our_overround'] = 1/race_df['Odds predicted']
            market_ovr = (race_df['market_overround'].sum()).round(2)
            our_ovr = race_df['our_overround'].sum().round(2)
            
            # Get the race details for the header
            race_date = race_df['race_date'].iloc[0].strftime('%Y-%m-%d')
            city = race_df['city'].iloc[0]
            
            st.markdown(f"### {race}")
            st.markdown(f"**Date:** {race_date} | **City:** {city}")
            
            # Display only horse, jockey, and odds
            display_df = race_df[['Horse number', 'Horse', 'Jockey', 'Draw', 'Last 5 races', 'Initial market odds', 'Odds predicted', 'Odds predicted (raw)', 'Betting hint (+)', 'Betting hint (-)']].reset_index(drop=True)
            display_df_prob = race_df[['Horse', 'Win probability', 'Top2 probability', 'Top3 probability', 'Last place probability']]
            display_df.index += 1
            display_df_prob.index += 1
            st.dataframe(display_df, use_container_width=True)
            st.dataframe(display_df_prob, use_container_width=True)
            st.markdown("---")
    else:
        st.info("Please select at least one race name to display the data.")

def plot_accuracy(df):
    st.subheader("Accuracy metric")
    st.markdown("Accuracy over time metric - in other words, how well our model is predicting the top 3 finishers in each race. It is NOT the accuracy of the odds or overall accuracy of the model.")
    fig = px.bar(df, x='race_date', y='avg_acc_top3', title='Average Accuracy (Top 3)', labels={'avg_acc_top3': 'Accuracy', 'race_date': 'Date'})
    st.plotly_chart(fig, use_container_width=True)

def plot_earnings(df):
    st.subheader("Cumulative Earnings")
    st.markdown("This chart illustrates the earnings that would have resulted from betting $10 on the top 3 finishers in each race, using the closing odds to determine the payout. The chart shows the total amount of money that would have been earned if this strategy had been employed.")
    fig = px.bar(df, x='race_date', y='money_earned_top3', title='Cumulative Sum Earned (Top 3)', labels={'money_earned_top3': 'Earnings over time in $', 'race_date': 'Date'})
    st.plotly_chart(fig, use_container_width=True)
    
def main():
    st.title("🇫🇷 FR Horse Racing Odds Prediction")
    
    tab1, tab2, tab3, tab4 = st.tabs(["Race Data", "Performance Metrics", "Preview Demo", "Horse Racing Assistant"])
    
    with tab1:
        race_data = get_data_fr()
        display_race_data(race_data)
        # st.dataframe(race_data)
    with tab2:
        bq_data = get_bigquery_data()
        col1, col2 = st.columns(2)
        with col1:
            plot_accuracy(bq_data)
        with col2:
            plot_earnings(bq_data)
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
    with tab4:
        st.subheader("Chat with Bernard")
        st.markdown("Chat with Bernard, your horse racing assistant, to get insights about races, horses, and predictions.")
        
        # Add Dialogflow Messenger component as a direct chat interface (not a bubble)
        st.components.v1.html(
            """
            <style>
                :root {
                    /* Window dimensions */
                    --df-messenger-chat-window-height: 600px !important;
                    --df-messenger-chat-window-width: 100% !important;
                    
                    /* Colors from documentation */
                    --df-messenger-bot-message: #f3f6fc;
                    --df-messenger-button-titlebar-color: #0b57d0;
                    --df-messenger-button-titlebar-font-color: #ffffff;
                    --df-messenger-chat-background-color: #ffffff;
                    --df-messenger-font-color: #444746;
                    --df-messenger-input-box-color: #ffffff;
                    --df-messenger-input-font-color: #444746;
                    --df-messenger-input-placeholder-font-color: #757575;
                    --df-messenger-minimized-chat-close-icon-color: #0b57d0;
                    --df-messenger-send-icon: #0b57d0;
                    --df-messenger-user-message: #e8f0fe;
                    
                    /* Additional styling variables */
                    --df-messenger-primary-color: #0b57d0;
                    --df-messenger-input-box-border: 1px solid #e0e0e0;
                    --df-messenger-input-box-border-radius: 8px;
                    --df-messenger-input-box-padding: 15px;
                    --df-messenger-message-border-radius: 8px;
                    --df-messenger-titlebar-background: #ffffff;
                    --df-messenger-titlebar-font-color: #202124;
                    --df-messenger-titlebar-border-bottom: 1px solid #e0e0e0;
                }
                
                df-messenger {
                    width: 100% !important;
                    height: 600px !important;
                    display: block !important;
                }
                
                df-messenger-chat {
                    width: 100% !important;
                    height: 600px !important;
                    display: block !important;
                    border: 1px solid #e0e0e0;
                    border-radius: 8px;
                    overflow: hidden;
                    box-shadow: 0 2px 6px rgba(0, 0, 0, 0.1);
                }
                
                /* Fix for the horse icon */
                .df-messenger-chat-title-icon {
                    width: 24px;
                    height: 24px;
                    margin-right: 8px;
                }
            </style>
            
            <link rel="stylesheet" href="https://www.gstatic.com/dialogflow-console/fast/df-messenger/prod/v1/themes/df-messenger-default.css">
            <script src="https://www.gstatic.com/dialogflow-console/fast/df-messenger/prod/v1/df-messenger.js"></script>
            
            <df-messenger
                location="europe-west3"
                project-id="data-gaming-425312"
                agent-id="7293f408-37d3-4aeb-ac9e-347b831b806e"
                language-code="fr"
                max-query-length="-1"
                allow-feedback="all"
                storage-option="none"
                intent="WELCOME">
                <df-messenger-chat
                    chat-title="Bernard - votre assistant hippique"
                    chat-title-icon="data:image/svg+xml;base64,PHN2ZyB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciIHZpZXdCb3g9IjAgMCA1MTIgNTEyIj48cGF0aCBkPSJNNDgwIDEyOHYyMDhjMCAxOC4yLTguMyAzNC45LTIyLjggNDUuOS0xNC40IDEwLjktMzIuNyAxNC42LTUwLjIgOS43bC0xNTYuNi00My4zYy0xNy4yLTQuOC0zMi4zLTE1LjEtNDMuMi0yOS44TDE0NCAzNDRWMjI0YzAtMTcuNyAxNC4zLTMyIDMyLTMyaDY0YzE3LjcgMCAzMiAxNC4zIDMyIDMydjY0aDk2bDU1LjUtNTUuNWMxOS4xLTE5LjEgNDQuMi0yOS41IDcxLTI5LjVIMTQ0YzE3LjcgMCAzMi0xNC4zIDMyLTMycy0xNC4zLTMyLTMyLTMySDMyQzE0LjMgMTI4IDAgMTQyLjMgMCAxNjB2MjI0YzAgMTcuNyAxNC4zIDMyIDMyIDMyaDY0YzE3LjcgMCAzMi0xNC4zIDMyLTMyVjM0NGMwLTEwLjYgNC4xLTIwLjggMTEuNS0yOC4zTDI0MCAyMTQuN1YyNTZjMCAxNy43LTE0LjMgMzItMzIgMzJoLTY0Yy0xNy43IDAtMzItMTQuMy0zMi0zMnYtNjRjMC0xNy43IDE0LjMtMzIgMzItMzJoMTkyYzE3LjcgMCAzMiAxNC4zIDMyIDMydjEyOGMwIDEwLjYtNC4xIDIwLjgtMTEuNSAyOC4zbC0xMDEuNyAxMDEuN2MtMy42IDMuNi04LjUgNS42LTEzLjcgNS42SDEyOGMtMTcuNyAwLTMyLTE0LjMtMzItMzJzMTQuMy0zMiAzMi0zMmgxMjhjMTcuNyAwIDMyIDE0LjMgMzIgMzJzLTE0LjMgMzItMzIgMzJIMTI4Yy01MyAwLTk2LTQzLTk2LTk2czQzLTk2IDk2LTk2aDI3LjFjMjYuOCAwIDUxLjkgMTAuNCA3MC44IDI5LjNsNTYuMSA1Ni4xaDc0LjFjMTcuNyAwIDMyIDE0LjMgMzIgMzJzLTE0LjMgMzItMzIgMzJIMzIwYy0xNy43IDAtMzItMTQuMy0zMi0zMnMxNC4zLTMyIDMyLTMyaDMyYzE3LjcgMCAzMi0xNC4zIDMyLTMycy0xNC4zLTMyLTMyLTMyaC0zMmMtNTMgMC05NiA0My05NiA5NnM0MyA5NiA5NiA5NmgxMjhjMTcuNyAwIDMyIDE0LjMgMzIgMzJzLTE0LjMgMzItMzIgMzJIMTI4Yy0xNy43IDAtMzItMTQuMy0zMi0zMnMxNC4zLTMyIDMyLTMyaDEyOGMxNy43IDAgMzIgMTQuMyAzMiAzMnMtMTQuMyAzMi0zMiAzMkgxMjhjLTUzIDAtOTYtNDMtOTYtOTZzNDMtOTYgOTYtOTZoMjcuMWMyNi44IDAgNTEuOSAxMC40IDcwLjggMjkuM2w1Ni4xIDU2LjFoNzQuMWMxNy43IDAgMzIgMTQuMyAzMiAzMnMtMTQuMyAzMi0zMiAzMkgzMjBjLTE3LjcgMC0zMi0xNC4zLTMyLTMyVjE2MGMwLTE3LjcgMTQuMy0zMiAzMi0zMmgxMjhjMTcuNyAwIDMyIDE0LjMgMzIgMzJ6Ii8+PC9zdmc+"
                    placeholder-text="Posez une question sur les courses hippiques..."
                    bot-writing-text="Bernard réfléchit... 🐎 (cela peut prendre quelques secondes)"
                    expand="true">
                </df-messenger-chat>
            </df-messenger>
            """,
            height=650,
        )
        
        
if __name__ == "__main__":
    main()

import streamlit as st
import pandas as pd
import numpy as np
from supabase import create_client, Client
from google.oauth2 import service_account
from google.cloud import bigquery
import plotly.express as px

st.set_page_config(page_title="UK Horse Racing", page_icon="🇬🇧", layout="wide")
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
def get_data_uk():
    try:
        response_gb = supabase.table('uk_horse_racing_full').select(
            'race_date', 'race_id', 'horse_id', 'race_name', 'city', 'horse', 'jockey',
            'odds', 'odds_predicted', 'horse_num', 'positive_hint', 'draw_norm',
            'last_5_positions', 'odds_predicted_intial', 'winner_prob', 'trifecta_prob',
            'quinella_prob', 'place_prob', 'last_place_prob',
            'horse_form_score', 'horse_form_score_diff',
            'horse_potential_skill_score', 'horse_potential_skill_score_diff', 
            'horse_fitness_score', 'horse_fitness_score_diff',
            'horse_enthusiasm_score', 'horse_enthusiasm_score_diff',
            'horse_jumping_skill_score', 'horse_jumping_skill_score_diff',
            'horse_going_skill_score', 'horse_going_skill_score_diff',
            'horse_distance_skill_score', 'horse_distance_skill_score_diff',
            'jockey_skill_score', 'jockey_skill_score_diff',
            'trainer_skill_score', 'trainer_skill_score_diff',
            'using_sire_stats', 'race_time_off'
        ).execute()
        
        df = pd.DataFrame(response_gb.data)
        
        df['race_date'] = pd.to_datetime(df['race_date'])
        df.rename(columns={'horse': 'Horse', 'jockey': 'Jockey', 'odds_predicted': 'Odds predicted', 'horse_num': 'Horse number', 'odds': 'Initial market odds', 'positive_hint': 'Betting hint', 
                            'last_5_positions': 'Last 5 races', 'draw_norm': 'Draw', 'odds_predicted_intial': 'Odds predicted (raw)',
                           'winner_prob': 'Win probability','trifecta_prob': 'Top3 probability','quinella_prob': 'Top2 probability','last_place_prob': 'Last place probability'
                            }, inplace=True)
        return df
        
    except Exception as e:
        st.error(f"Error fetching data from Supabase: {str(e)}")
        return pd.DataFrame()

# Fetch data from BigQuery
@st.cache_data(ttl=600)
def get_bigquery_data():
    query = "SELECT * FROM `data-gaming-425312.gb_horse_data.gb_data__predictions_stats`"
    try:
        df = bq_client.query(query).to_dataframe()
        df['race_date'] = pd.to_datetime(df['race_date'])
        return df
    except Exception as e:
        st.error(f"Error fetching data from BigQuery: {e}")
        return pd.DataFrame()

@st.cache_data(ttl=600)
def get_bigquery_odds_data():
    try:
        query = "SELECT * FROM `data-gaming-425312.gb_horse_data.gb_horse_odds`"
        df = bq_client.query(query).to_dataframe()
        return df
    except Exception as e:
        st.error(f"Error fetching data from BigQuery: {e}")
        return pd.DataFrame()

# Define stats at module level
STATS = [
    ('horse_form_score', 'horse_form_score_diff'),
    ('horse_potential_skill_score', 'horse_potential_skill_score_diff'),
    ('horse_fitness_score', 'horse_fitness_score_diff'),
    ('horse_enthusiasm_score', 'horse_enthusiasm_score_diff'),
    ('horse_jumping_skill_score', 'horse_jumping_skill_score_diff'),
    ('horse_going_skill_score', 'horse_going_skill_score_diff'),
    ('horse_distance_skill_score', 'horse_distance_skill_score_diff'),
    ('jockey_skill_score', 'jockey_skill_score_diff'),
    ('trainer_skill_score', 'trainer_skill_score_diff')
]

def create_computeform_table(race_df):
    # Create a new dataframe for display
    display_data = []
    
    for _, horse in race_df.iterrows():
        row = {'Horse': horse['Horse']}
        
        # Add sire stats indicator
        # Add a symbol to the horse name if using sire stats
        horse_name = horse['Horse']
        if horse['using_sire_stats']:
            horse_name = f"{horse_name} 🧬"  # DNA emoji to indicate sire stats usage
        row['Horse'] = horse_name
        
        # Calculate total score
        total_score = sum(horse[stat[0]] for stat in STATS)
        
        if total_score < 10:
            row['COMPUTE'] = "Not enough data"
            for stat, _ in STATS:
                row[stat] = None
            display_data.append(row)
            continue
            
        # Process each stat
        for stat, _ in STATS:
            row[stat] = int(round(horse[stat]))
        
        row['COMPUTE'] = int(round(total_score))
        display_data.append(row)
    
    # Convert to dataframe and sort
    result_df = pd.DataFrame(display_data)
    
    # Sort by COMPUTE, handling "Not enough data"
    result_df['sort_value'] = pd.to_numeric(result_df['COMPUTE'], errors='coerce')
    result_df = result_df.sort_values('sort_value', ascending=False)
    result_df = result_df.drop('sort_value', axis=1)
    
    # Create a function to apply styles
    def apply_styles(col):
        if col.name not in [stat[0] for stat in STATS]:
            return [''] * len(col)
            
        styles = []
        for idx, value in col.items():
            # If value is None, use default background
            if pd.isna(value):
                styles.append('')
                continue
                
            horse_name = result_df.loc[idx, 'Horse'].split(' 🧬')[0]  # Remove emoji for matching
            horse_idx = race_df[race_df['Horse'] == horse_name].index[0]
            
            diff = race_df.loc[horse_idx, f"{col.name}_diff"]
            if diff < 0:
                styles.append('background-color: #d4edda; color: #155724')
            elif diff > 0:
                styles.append('background-color: #f8d7da; color: #721c24')
            else:
                styles.append('')  # Changed: No background color for unchanged values
        return styles
    
    # Apply styling
    styled_df = result_df.style.apply(apply_styles)
    
    # Format numbers as integers, skip non-numeric
    number_format = {stat[0]: '{:,.0f}' for stat in STATS}
    number_format['COMPUTE'] = lambda x: '{:,.0f}'.format(x) if isinstance(x, (int, float)) else x
    styled_df = styled_df.format(number_format)
    
    return styled_df

def display_race_data(df, odds_df):
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
        for race_with_time in selected:
            st.markdown(f"### {race_with_time}")
            # Extract the original race name (everything after " - ")
            race_name = race_with_time.split(" - ")[1]
            race_df = df[df['race_name'] == race_name]
            
            # Get the race_id for this race
            race_id = race_df['race_id'].iloc[0]
            
            # Filter odds data for this race
            race_odds_df = odds_df[odds_df['race_id'] == race_id]
            #join the two dataframes on horse_id
            race_odds_df = race_odds_df.rename(columns={'horse_link': 'horse_id'})
            race_odds_df = pd.merge(race_odds_df, race_df, on=['horse_id', 'race_id'], how='left')
            
            # Display race details
            race_date = race_df['race_date'].iloc[0].strftime('%Y-%m-%d')
            city = race_df['city'].iloc[0]
            st.markdown(f"**Date:** {race_date} | **City:** {city}")
            
            # Display main race data
            display_df = race_df[['Horse number', 'Horse', 'Jockey', 'Draw', 'Last 5 races', 
                                'Initial market odds', 'Odds predicted', 'Odds predicted (raw)', 
                                'Betting hint']].reset_index(drop=True)
            display_df.index += 1
            st.dataframe(display_df, use_container_width=True)
            
            # Display probability data
            display_df_prob = race_df[['Horse', 'Win probability', 'Top2 probability', 
                                     'Top3 probability', 'Last place probability']]
            display_df_prob.index += 1
            st.dataframe(display_df_prob, use_container_width=True)
            
            # Move the chart creation inside the race loop
            if not race_odds_df.empty:
                # Randomly select 6 horses to display initially
                import random
                all_horses = race_odds_df['Horse'].unique()
                initial_horses = random.sample(list(all_horses), min(6, len(all_horses)))  # Added min() to handle races with fewer than 6 horses
                
                fig = px.line(
                    race_odds_df,
                    x='scraped_time',
                    y='odds',
                    color='Horse',
                    labels={
                        'scraped_time': 'Time',
                        'odds': 'Odds',
                        'Horse': 'Horse'
                    },
                    title=f'Odds Movement - {race_name}',  # Added race name to title for clarity
                    log_y=True
                )
                
                # Add markers (dots) to the lines
                fig.update_traces(
                    mode='lines+markers',
                    marker=dict(size=6),
                    line=dict(width=2)
                )
                
                # Customize the layout
                fig.update_layout(
                    xaxis_title="Time",
                    yaxis_title="Odds",
                    legend_title="Horses",
                    height=450,
                    yaxis={
                        'autorange': 'reversed',
                        'type': 'log',
                        'gridwidth': 0.5,
                        'gridcolor': 'rgba(128, 128, 128, 0.2)',
                    },
                    xaxis={
                        'gridwidth': 0.5,
                        'gridcolor': 'rgba(128, 128, 128, 0.2)',
                    },
                    plot_bgcolor='rgba(0,0,0,0)',
                    paper_bgcolor='rgba(0,0,0,0)',
                    font=dict(size=12),
                    legend=dict(
                        yanchor="top",
                        y=0.99,
                        xanchor="left",
                        x=1.02,
                        itemsizing='constant'
                    )
                )
                
                # Add horse names to legend and hide non-selected horses
                horse_names = race_df.set_index('horse_id')['Horse'].to_dict()
                for trace in fig.data:
                    horse_name = horse_names.get(trace.name, trace.name)
                    trace.update(
                        name=horse_name,
                        visible='legendonly' if horse_name not in initial_horses else True
                    )
                # Create computeform table in an expander
                with st.expander("SHOW ODDS MOVEMENT"):
                    st.plotly_chart(fig, use_container_width=True)
                with st.expander("SHOW SKILLS DATA"):
                    computeform_df = create_computeform_table(race_df)
                    st.dataframe(
                        computeform_df,
                        use_container_width=True,
                        column_config={
                            'Horse': st.column_config.TextColumn('Horse', width='medium', help="🧬 indicates sire stats are being used"),
                            'horse_form_score': st.column_config.NumberColumn('FORM', width='small', help="Form score", format='%d'),
                            'horse_potential_skill_score': st.column_config.NumberColumn('POTENTIAL', width='small', help="Potential skill score", format='%d'),
                            'horse_fitness_score': st.column_config.NumberColumn('FITNESS', width='small', help="Fitness score", format='%d'),
                            'horse_enthusiasm_score': st.column_config.NumberColumn('ENTHUSIASM', width='small', help="Enthusiasm score", format='%d'),
                            'horse_jumping_skill_score': st.column_config.NumberColumn('JUMPING', width='small', help="Jumping skill score", format='%d'),
                            'horse_going_skill_score': st.column_config.NumberColumn('GOING', width='small', help="Going skill score", format='%d'),
                            'horse_distance_skill_score': st.column_config.NumberColumn('DISTANCE', width='small', help="Distance skill score", format='%d'),
                            'jockey_skill_score': st.column_config.NumberColumn('JOCKEY', width='small', help="Jockey skill score", format='%d'),
                            'trainer_skill_score': st.column_config.NumberColumn('TRAINER', width='small', help="Trainer skill score", format='%d'),
                            'COMPUTE': st.column_config.NumberColumn('DG SCORE', width='small', help="Final computed score", format='%d'),
                        },
                        hide_index=True
                    )
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
    st.title("🇬🇧 UK Horse Racing Odds Prediction")
    
    
    # Create tabs with a dedicated chat tab
    tab1, tab2, tab3 = st.tabs(["Race Data", "Performance Metrics", "Chat with Henry"])
    
    with tab1:
        race_data = get_data_uk()
        odds_data = get_bigquery_odds_data()
        display_race_data(race_data, odds_data)
    
    with tab2:
        bq_data = get_bigquery_data()
        col1, col2 = st.columns(2)
        with col1:
            plot_accuracy(bq_data)
        with col2:
            plot_earnings(bq_data)
        # st.dataframe(bq_data)
    
    with tab3:
        st.subheader("Horse Racing Assistant")
        st.markdown("Chat with Henry, your horse racing assistant, to get insights about races, horses, and predictions.")

        # Add Dialogflow Messenger com
        st.components.v1.html(
            f"""
            <style>
                :root {{
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
                }}
                
                df-messenger {{
                    width: 100% !important;
                    height: 600px !important;
                    display: block !important;
                }}
                
                df-messenger-chat {{
                    width: 100% !important;
                    height: 600px !important;
                    display: block !important;
                    border: 1px solid #e0e0e0;
                    border-radius: 8px;
                    overflow: hidden;
                    box-shadow: 0 2px 6px rgba(0, 0, 0, 0.1);
                }}
                
                /* Fix for the horse icon */
                .df-messenger-chat-title-icon {{
                    width: 24px;
                    height: 24px;
                    margin-right: 8px;
                }}
            </style>
            
            <link rel="stylesheet" href="https://www.gstatic.com/dialogflow-console/fast/df-messenger/prod/v1/themes/df-messenger-default.css">
            <script src="https://www.gstatic.com/dialogflow-console/fast/df-messenger/prod/v1/df-messenger.js"></script>
            
            <df-messenger
                location="us-central1"
                project-id="data-gaming-425312"
                agent-id="840d8e2a-1a6e-460a-b54d-a62a90d30b67"
                language-code="en"
                max-query-length="-1"
                allow-feedback="all"
                storage-option="none"
                intent="Hello">
                <df-messenger-chat
                    chat-title="Henry - your horse assistant"
                    chat-title-icon="data:image/svg+xml;base64,PHN2ZyB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciIHZpZXdCb3g9IjAgMCA1MTIgNTEyIj48cGF0aCBkPSJNNDgwIDEyOHYyMDhjMCAxOC4yLTguMyAzNC45LTIyLjggNDUuOS0xNC40IDEwLjktMzIuNyAxNC42LTUwLjIgOS43bC0xNTYuNi00My4zYy0xNy4yLTQuOC0zMi4zLTE1LjEtNDMuMi0yOS44TDE0NCAzNDRWMjI0YzAtMTcuNyAxNC4zLTMyIDMyLTMyaDY0YzE3LjcgMCAzMiAxNC4zIDMyIDMydjY0aDk2bDU1LjUtNTUuNWMxOS4xLTE5LjEgNDQuMi0yOS41IDcxLTI5LjVIMTQ0YzE3LjcgMCAzMi0xNC4zIDMyLTMycy0xNC4zLTMyLTMyLTMySDMyQzE0LjMgMTI4IDAgMTQyLjMgMCAxNjB2MjI0YzAgMTcuNyAxNC4zIDMyIDMyIDMyaDY0YzE3LjcgMCAzMi0xNC4zIDMyLTMyVjM0NGMwLTEwLjYgNC4xLTIwLjggMTEuNS0yOC4zTDI0MCAyMTQuN1YyNTZjMCAxNy43LTE0LjMgMzItMzIgMzJoLTY0Yy0xNy43IDAtMzItMTQuMy0zMi0zMnYtNjRjMC0xNy43IDE0LjMtMzIgMzItMzJoMTkyYzE3LjcgMCAzMiAxNC4zIDMyIDMydjEyOGMwIDEwLjYtNC4xIDIwLjgtMTEuNSAyOC4zbC0xMDEuNyAxMDEuN2MtMy42IDMuNi04LjUgNS42LTEzLjcgNS42SDEyOGMtMTcuNyAwLTMyLTE0LjMtMzItMzJzMTQuMy0zMiAzMi0zMmgxMjhjMTcuNyAwIDMyIDE0LjMgMzIgMzJzLTE0LjMgMzItMzIgMzJIMTI4Yy01MyAwLTk2LTQzLTk2LTk2czQzLTk2IDk2LTk2aDI3LjFjMjYuOCAwIDUxLjkgMTAuNCA3MC44IDI5LjNsNTYuMSA1Ni4xaDc0LjFjMTcuNyAwIDMyIDE0LjMgMzIgMzJzLTE0LjMgMzItMzIgMzJIMzIwYy0xNy43IDAtMzItMTQuMy0zMi0zMnMxNC4zLTMyIDMyLTMyaDMyYzE3LjcgMCAzMi0xNC4zIDMyLTMycy0xNC4zLTMyLTMyLTMyaC0zMmMtNTMgMC05NiA0My05NiA5NnM0MyA5NiA5NiA5NmgxMjhjMTcuNyAwIDMyIDE0LjMgMzIgMzJzLTE0LjMgMzItMzIgMzJIMTI4Yy0xNy43IDAtMzItMTQuMy0zMi0zMnMxNC4zLTMyIDMyLTMyaDEyOGMxNy43IDAgMzIgMTQuMyAzMiAzMnMtMTQuMyAzMi0zMiAzMkgxMjhjLTUzIDAtOTYtNDMtOTYtOTZzNDMtOTYgOTYtOTZoMjcuMWMyNi44IDAgNTEuOSAxMC40IDcwLjggMjkuM2w1Ni4xIDU2LjFoNzQuMWMxNy43IDAgMzIgMTQuMyAzMiAzMnMtMTQuMyAzMi0zMiAzMkgzMjBjLTE3LjcgMC0zMi0xNC4zLTMyLTMyVjE2MGMwLTE3LjcgMTQuMy0zMiAzMi0zMmgxMjhjMTcuNyAwIDMyIDE0LjMgMzIgMzJ6Ii8+PC9zdmc+"
                    placeholder-text="Ask Henry about horse racing..."
                    bot-writing-text="Henry is thinking... 🐎 (this may take a few seconds)"
                    expand="true">
                </df-messenger-chat>
            </df-messenger>
            """,
            height=650,
        )

if __name__ == "__main__":
    main()

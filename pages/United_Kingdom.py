def display_race_data(df, odds_df):
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
            
            # Get the race_id for this race
            race_id = race_df['race_id'].iloc[0]
            
            # Filter odds data for this race
            race_odds_df = odds_df[odds_df['race_id'] == race_id]
            #join the two dataframes on horse_id
            race_odds_df = race_odds_df.rename(columns={'horse_link': 'horse_id'})
            race_odds_df = pd.merge(race_odds_df, race_df, on=['horse_id', 'race_id'], how='left')
            
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
            display_df = race_df[['Horse number', 'Horse', 'Jockey', 'Draw', 'Last 5 races', 'Initial market odds', 'Odds predicted', 'Odds predicted (raw)', 'Betting hint']].reset_index(drop=True)
            display_df_prob = race_df[['Horse', 'Win probability', 'Top2 probability', 'Top3 probability', 'Last place probability']]
            display_df.index += 1  # Start index from 1 instead of 0
            display_df_prob.index += 1  # Start index from 1 instead of 0
            st.dataframe(display_df, use_container_width=True)
            st.dataframe(display_df_prob, use_container_width=True)
            
            # Add odds movement plot
            if not race_odds_df.empty:
                fig = px.line(
                    race_odds_df,
                    x='scraped_time',
                    y='odds',
                    color='horse',
                    labels={
                        'scraped_time': 'Time',
                        'odds': 'Odds',
                        'horse': 'Horse'
                    },
                    title='Odds Movement'
                )
                
                # Customize the layout
                fig.update_layout(
                    xaxis=dict(
                        type='category',  # This will treat x-axis as discrete points
                        tickangle=-45,    # Angle the time labels for better readability
                        tickformat='%H:%M',  # Show only hours and minutes
                    ),
                    yaxis=dict(
                        title="Odds",
                        autorange="reversed",  # Lower odds (favorites) appear at the top
                        gridcolor='rgba(128, 128, 128, 0.2)',  # Lighter grid lines
                    ),
                    plot_bgcolor='rgba(0,0,0,0)',  # Transparent background
                    paper_bgcolor='rgba(0,0,0,0)',
                    height=500,  # Taller chart
                    margin=dict(b=100),  # More bottom margin for rotated labels
                    legend=dict(
                        yanchor="top",
                        y=0.99,
                        xanchor="left",
                        x=1.02,
                        bgcolor='rgba(255, 255, 255, 0.8)'  # Semi-transparent legend background
                    ),
                    hovermode='x unified'  # Show all values for a given x-position
                )
                
                # Make lines thicker and add markers
                fig.update_traces(
                    line=dict(width=2),
                    mode='lines+markers',
                    marker=dict(size=8)
                )
                
                # Add horse names to legend
                horse_names = race_df.set_index('horse_id')['Horse'].to_dict()
                fig.for_each_trace(lambda t: t.update(name=horse_names.get(t.name, t.name)))
                
                st.plotly_chart(fig, use_container_width=True)
            
            st.markdown("---")  # Add a separator between races
    else:
        st.info("Please select at least one race name to display the data.")

import streamlit as st
import pandas as pd
import plotly.express as px
import json

# Titel van de app
st.title("📊 Actie Analyse Dashboard")

# Upload dataset (Excel ondersteuning)
uploaded_file = st.file_uploader("📂 Upload een Excel-bestand", type=["xlsx"])

if uploaded_file:
    df = pd.read_excel(uploaded_file)  # Lees het Excel-bestand
    
    # Sidebar navigatie
    page = st.sidebar.radio("📌 Navigatie", ["🏠 Algemene statistieken", "👤 Gebruiker statistieken"])

    if page == "🏠 Algemene statistieken":
        st.header("📈 Algemene Statistieken")

        required_columns = {'Action User ID', 'Model naam', 'Action'}
        if not required_columns.issubset(df.columns):
            st.error(f"De dataset mist vereiste kolommen: {required_columns - set(df.columns)}")
        else:
            # Groeperen op Action User ID en Model naam en het aantal acties tellen
            actions_per_user_model = df.groupby(['Action User ID', 'Model naam']).size().reset_index(name='Aantal acties')
            average_actions_per_model = actions_per_user_model.groupby('Model naam')['Aantal acties'].mean().reset_index()

            # Gemiddeld aantal acties per model plotten
            fig = px.bar(average_actions_per_model, x='Model naam', y='Aantal acties',
                         title='Gemiddeld aantal acties per gebruiker per model',
                         labels={'Aantal acties': 'Gemiddeld aantal acties', 'Model naam': 'Model'},
                         template='plotly_white')
            st.plotly_chart(fig, use_container_width=True)

            # Functie om fouten te tellen in de Arguments-kolom
            def count_errors(argument):
                try:
                    parsed = json.loads(argument)
                    if isinstance(parsed, dict) and "telling" in parsed:
                        return parsed["telling"].get("entity", {}).get("fouten", 0)
                except json.JSONDecodeError:
                    pass
                return 0

            # Functie om te controleren op WRONG_NAME in de Arguments-kolom
            def contains_wrong_name(argument):
                try:
                    if isinstance(argument, str):
                        parsed = json.loads(argument)
                        if isinstance(parsed, list) and "fouten" in parsed[0] and "WRONG_NAME" in parsed[0]["fouten"]:
                            return True
                except (json.JSONDecodeError, KeyError, IndexError):
                    return False
                return False

            # Voeg kolommen toe om vorige actie en arguments te controleren
            df["Previous_Action"] = df["Action"].shift(1)
            df["Previous_Arguments"] = df["Arguments"].shift(1)

            # Markeer rijen om uit te sluiten
            df["Exclude"] = (df["Previous_Action"] == "create") & df["Arguments"].apply(contains_wrong_name)

            # Zorg ervoor dat ook de twee volgende fouten worden uitgesloten
            df["Exclude_next_1"] = df["Exclude"].shift(1).fillna(False)
            df["Exclude_next_2"] = df["Exclude"].shift(2).fillna(False)

            # Filter de dataset
            df_filtered = df[~(df["Exclude"] | df["Exclude_next_1"] | df["Exclude_next_2"])]

            # Voeg een kolom toe met het aantal fouten per rij
            df_filtered["Aantal fouten"] = df_filtered["Arguments"].apply(count_errors)

            # Filter fout-acties
            error_actions = df_filtered[df_filtered["Aantal fouten"] > 0]

            # Groepeer per gebruiker en model en bereken het gemiddelde aantal fouten
            errors_per_user_model = error_actions.groupby(["Action User ID", "Model naam"])["Aantal fouten"].sum().reset_index()
            average_errors_per_model = errors_per_user_model.groupby("Model naam")["Aantal fouten"].mean().reset_index()

            # Gemiddeld aantal fouten per model plotten
            fig = px.bar(average_errors_per_model, x='Model naam', y='Aantal fouten',
                        title='Gemiddeld aantal fouten per gebruiker per model',
                        labels={'Aantal fouten': 'Gemiddeld aantal fouten', 'Model naam': 'Model'},
                        template='plotly_white')
            fig.update_traces(marker_color="#d62728")

            st.plotly_chart(fig, use_container_width=True)

            # Top 10 meest voorkomende acties
            action_counts = df['Action'].value_counts().head(10).reset_index()
            action_counts.columns = ['Action', 'Aantal keer']

            fig = px.bar(action_counts, x='Aantal keer', y='Action',
                         title='Top 10 meest voorkomende acties',
                         labels={'Aantal keer': 'Aantal keer voorgekomen', 'Action': 'Actie'},
                         template='plotly_white', orientation='h', color='Aantal keer')
            fig.update_yaxes(categoryorder='total ascending')  # Sorteren op aantal keer voorgekomen
            
            st.plotly_chart(fig, use_container_width=True)

            # Acties vs. fouten per gebruiker scatterplot
            # Bereken totaal aantal acties en fouten per gebruiker
            user_stats = df_filtered.groupby('Action User ID').agg({'Action': 'count'}).rename(columns={'Action': 'Aantal acties'})
            error_stats = error_actions.groupby('Action User ID').agg({'Action': 'count'}).rename(columns={'Action': 'Aantal fouten'})

            # Merge de datasets
            user_stats = user_stats.join(error_stats, how='left').fillna(0)  # Voeg fouten toe, zet NaN op 0
            user_stats = user_stats.reset_index()  # Zorg dat de gebruikers-ID weer een kolom is

            # Maak een scatterplot met gebruikers-ID in hover-informatie
            fig2 = px.scatter(user_stats, 
                            x='Aantal acties', 
                            y='Aantal fouten', 
                            title="📊 Acties vs. fouten per gebruiker",
                            labels={'Aantal acties': 'Totaal aantal acties', 'Aantal fouten': 'Totaal aantal fouten'},
                            template='plotly_white', 
                            size='Aantal acties', 
                            color='Aantal fouten',
                            hover_data={'Action User ID': True, 'Aantal acties': True, 'Aantal fouten': True})  # Voeg gebruikers-ID toe aan hover

            st.plotly_chart(fig2, use_container_width=True)

            # Controleer of de kolommen aanwezig zijn
            if {'Leerling Id', 'Model naam', 'Moment'}.issubset(df.columns):

                # Zet 'Moment' om naar datetime
                df['Moment'] = pd.to_datetime(df['Moment'])

                # Bereken de eerste en laatste actie per model en leerling
                model_times = df.groupby(['Leerling Id', 'Model naam']).agg(
                    starttijd=('Moment', 'min'),
                    eindtijd=('Moment', 'max')
                ).reset_index()

                # Bereken de duur in minuten
                model_times['Duur (min)'] = (model_times['eindtijd'] - model_times['starttijd']).dt.total_seconds() / 60

                # Bereken het gemiddelde per model
                avg_time_per_model = model_times.groupby('Model naam')['Duur (min)'].mean().reset_index()

                # Maak een bar plot
                fig = px.bar(avg_time_per_model, x='Model naam', y='Duur (min)',
                            title="⏳ Gemiddelde tijd om een model te maken",
                            labels={'Duur (min)': 'Gemiddelde duur (minuten)', 'Model naam': 'Model'},
                            template='plotly_white')
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.warning("⚠️ De dataset mist de vereiste kolommen 'Leerling Id', 'Model naam' of 'Moment'. Kan geen duur berekenen.")
            
            # Data voorbereiden
            df['Hour'] = df['Moment'].dt.hour
            hourly_counts = df.groupby('Hour').size().reset_index(name='Aantal Activiteiten')

            # Interactieve staafgrafiek met Plotly
            fig = px.bar(hourly_counts, 
                        x='Hour', 
                        y='Aantal Activiteiten', 
                        title='Acties per uur van de dag', 
                        labels={'Hour': 'Uur van de dag', 'Aantal Activiteiten': 'Aantal acties'},
                        template='plotly_white')

            st.plotly_chart(fig, use_container_width=True)




            

    elif page == "👤 Gebruiker statistieken":
        st.header("📊 Gebruiker specifieke statistieken")

        users = df['Action User ID'].unique()
        selected_user = st.sidebar.selectbox("👤 Selecteer een gebruiker", users)

        if selected_user:
            st.subheader(f"📊 Statistieken voor gebruiker: {selected_user}")
            user_df = df[df['Action User ID'] == selected_user]

            # Acties per model voor gebruiker
            actions_per_model_user = user_df.groupby('Model naam').size().reset_index(name='Aantal acties')
            fig = px.bar(actions_per_model_user, x='Model naam', y='Aantal acties',
                         title=f'Aantal acties per model voor gebruiker {selected_user}',
                         labels={'Aantal acties': 'Aantal acties', 'Model naam': 'Model'},
                         template='plotly_white')
            st.plotly_chart(fig, use_container_width=True)

            # Fouten per model voor gebruiker
            # Functie om fouten te tellen in de Arguments-kolom
            def count_errors(argument):
                try:
                    parsed = json.loads(argument)
                    if isinstance(parsed, dict) and "telling" in parsed:
                        return parsed["telling"].get("entity", {}).get("fouten", 0)
                except json.JSONDecodeError:
                    pass
                return 0

            # Functie om te controleren op WRONG_NAME in de Arguments-kolom
            def contains_wrong_name(argument):
                try:
                    if isinstance(argument, str):
                        parsed = json.loads(argument)
                        if isinstance(parsed, list) and "fouten" in parsed[0] and "WRONG_NAME" in parsed[0]["fouten"]:
                            return True
                except (json.JSONDecodeError, KeyError, IndexError):
                    return False
                return False
            # Voeg kolommen toe om vorige actie en arguments te controleren
            df["Previous_Action"] = df["Action"].shift(1)
            df["Previous_Arguments"] = df["Arguments"].shift(1)

            # Markeer rijen om uit te sluiten
            df["Exclude"] = (df["Previous_Action"] == "create") & df["Arguments"].apply(contains_wrong_name)

            # Zorg ervoor dat ook de twee volgende fouten worden uitgesloten
            df["Exclude_next_1"] = df["Exclude"].shift(1).fillna(False)
            df["Exclude_next_2"] = df["Exclude"].shift(2).fillna(False)

            # Filter de dataset
            df_filtered = df[~(df["Exclude"] | df["Exclude_next_1"] | df["Exclude_next_2"])]

            # Voeg een kolom toe met het aantal fouten per rij
            df_filtered["Aantal fouten"] = df_filtered["Arguments"].apply(count_errors)

            # Filter dataset voor de geselecteerde gebruiker
            user_df = df_filtered[df_filtered["Action User ID"] == selected_user]

            # Filter fout-acties binnen de gebruiker en tel fouten per model
            user_errors = user_df[user_df["Aantal fouten"] > 0]
            errors_per_model_user = user_errors.groupby("Model naam")["Aantal fouten"].sum().reset_index()

            # Gemiddeld aantal fouten per model voor gebruiker plotten
            fig = px.bar(
                errors_per_model_user,
                x='Model naam',
                y='Aantal fouten',
                title=f'Aantal fouten per model voor gebruiker {selected_user}',
                labels={'Aantal fouten': 'Aantal fouten', 'Model naam': 'Model'},
                template='plotly_white'
            )
            fig.update_traces(marker_color="#d62728")

            st.plotly_chart(fig, use_container_width=True)

            # Top 10 acties van gebruiker
            user_action_counts = user_df['Action'].value_counts().head(10).reset_index()
            user_action_counts.columns = ['Action', 'Aantal keer']

            fig = px.bar(user_action_counts, x='Aantal keer', y='Action',
                         title=f'Top 10 meest voorkomende acties voor gebruiker {selected_user}',
                         labels={'Aantal keer': 'Aantal keer voorgekomen', 'Action': 'Actie'},
                         template='plotly_white', orientation='h', color='Aantal keer')
            fig.update_yaxes(categoryorder='total ascending')
            st.plotly_chart(fig, use_container_width=True)

            # Filter data voor de geselecteerde gebruiker
            user_df = df[df['Action User ID'] == selected_user]

            # Controleer of de tijdsgegevens aanwezig zijn
            if {'Leerling Id', 'Model naam', 'Moment'}.issubset(user_df.columns):
                user_df['Moment'] = pd.to_datetime(user_df['Moment'])

                # Bereken de eerste en laatste actie per model en leerling
                user_model_times = user_df.groupby(['Leerling Id', 'Model naam']).agg(
                    starttijd=('Moment', 'min'),
                    eindtijd=('Moment', 'max')
                ).reset_index()

                # Bereken de duur in minuten
                user_model_times['Duur (min)'] = (user_model_times['eindtijd'] - user_model_times['starttijd']).dt.total_seconds() / 60

                # Bereken het gemiddelde per model
                avg_time_per_model_user = user_model_times.groupby('Model naam')['Duur (min)'].mean().reset_index()

                fig = px.bar(avg_time_per_model_user, x='Model naam', y='Duur (min)',
                            title=f"⏳ Gemiddelde tijd per model voor {selected_user}",
                            labels={'Duur (min)': 'Gemiddelde duur (minuten)', 'Model naam': 'Model'},
                            template='plotly_white')
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.warning("⚠️ De dataset mist de vereiste kolommen 'Leerling Id', 'Model naam' of 'Moment'. Kan geen duur berekenen.")

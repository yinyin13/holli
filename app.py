import streamlit as st
import datetime
import sqlite3
from datetime import timedelta
from openai import OpenAI
from dotenv import load_dotenv
from st_pages import Page, show_pages

load_dotenv()

# Define function to insert trip details into database
def insert_trip_to_db(location, purpose, start_date, end_date, itinerary):
    conn = sqlite3.connect('trip_plans.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS trip_plans 
                 (location TEXT, purpose TEXT, start_date DATE, end_date DATE, itinerary TEXT)''')
    c.execute("INSERT INTO trip_plans (location, purpose, start_date, end_date, itinerary) VALUES (?, ?, ?, ?, ?)",
              (location, purpose, start_date, end_date, itinerary))
    conn.commit()
    conn.close()

# Define function for AI to plan trip
def plan_trip(location, purpose, date_range):
    client = OpenAI()
    system_prompt="You are a professional travel guide. You will be given a location, purpose of trip, and date range. Provide a detailed itinerary for the user. Each day should be titled in this format: Day: All Locations planned. Don't provide a general title nor conclusion for the trip"
    user_prompt=f"Location: {location}\nPurpose: {purpose}\nDate Range: {date_range[0]} to {date_range[1]}"
    response = client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        temperature=0.0,
    )

    st.session_state["response"] = response.choices[0].message.content

if "response" not in st.session_state:
    st.session_state["response"] = "-"

# Set page config
st.set_page_config(
    page_title="Holli - Your Personal AI Travel Planner",
    page_icon="🏖️",
    layout="centered",
    initial_sidebar_state="auto",
    menu_items=None,
)

# Declare pages
show_pages(
    [
        Page("app.py", "Home", "🏠"),
        Page("pages/itinerary.py", "Trip", "✈️"),
    ]
)

# Landing Page
st.title("Where to next? 🏖️")

location = st.text_input("Take me to...")
purpose = st.selectbox("Purpose of trip", ["Leisure", "Business", "Family", "Solo"])
current_date = datetime.date.today()
max_date = current_date + timedelta(days=5)
selected_date = st.date_input("Select date range", value=[current_date, max_date])
plan_button = st.button("Plan my trip")
    
# Redirect to Ideas page
if plan_button:
    plan_trip(location, purpose, selected_date)
    plan = st.session_state.response

    insert_trip_to_db(location, purpose, selected_date[0], selected_date[1], plan)
    st.switch_page("pages/itinerary.py")
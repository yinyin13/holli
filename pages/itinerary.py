import streamlit as st
import sqlite3
import re
import requests
import folium
import geocoder
import pandas as pd
import io
import spacy
import en_core_web_sm
from streamlit_folium import st_folium
from geopy.geocoders import Nominatim
from search_media import search_image
from PIL import Image
from pydantic import BaseModel
from enum import Enum

# Layout
st.set_page_config(
    page_title="Holli - Your Personal AI Travel Planner",
    page_icon="🏖️",
    layout="wide",
    initial_sidebar_state="auto",
    menu_items=None,
)
st.page_link("app.py", label="Back", icon="⬅️")
tab1, tab2, tab3 = st.tabs(["Itinerary", "Saved Trips", "Packing List"])

# Define functions
def fetch_trip_from_db():
    conn = sqlite3.connect('trip_plans.db')
    c = conn.cursor()
    c.execute("PRAGMA table_info(trip_plans)")
    columns = [column[1] for column in c.fetchall()]
    if 'saved' not in columns:
        # Add a new column named 'Saved' with type BOOLEAN to the 'trip_plans' table
        c.execute("ALTER TABLE trip_plans ADD COLUMN saved BOOLEAN DEFAULT 0")
    conn.commit()
    
    # Fetch the trip data after committing the schema changes
    c.execute("SELECT * FROM trip_plans")
    trip_data = c.fetchall()
    
    conn.close()
    return trip_data

geolocator = Nominatim(user_agent="trip_planner")

# Load full itinerary from the database
trip_data = fetch_trip_from_db()
itinerary_list = trip_data[-1][4]

# Split the text into title and activities list
days = [day for day in itinerary_list.split("\n\n")]
activities = [day.split("\n") for day in days]
titles = [day[0] for day in activities]
options = ["Overview"] + [t.strip("**") for t in titles if t.startswith("Day")]

# Extract locations
specific_locations = []
# Load the English model
nlp = spacy.load("en_core_web_sm")

# Extract locations from activities using spaCy
for day_activities in activities:
    # Skip the title (first item) and start from the second item
    for activity in day_activities:
        # Apply spaCy NER (Named Entity Recognition) to extract entities
        doc = nlp(activity)
        # Extract entities identified as 'LOC' (locations)
        for ent in doc.ents:
            if ent.label_ == 'LOC' or ent.label_ == 'GPE' or ent.label_ == 'FAC' or ent.label_ == 'ORG':
                specific_locations.append(ent.text.strip())

# Remove duplicates and convert to title case
specific_locations = list(set(specific_locations))

# Itinerary tab
with tab1:
    if len(trip_data) == 0:
        st.warning("No trip plans found.")
    else:
        sidebar_selection = st.selectbox("Select Day", options)

        trip_info = trip_data[-1]
        purpose = trip_info[1]
        destination = trip_info[0]

    col1, col2 = st.columns([1, 2])
    # Overview view                   
    with col1:
        st.title(f"{purpose.capitalize()} Trip to {destination.capitalize()}")
        if sidebar_selection == "Overview":
            st.subheader("Overview")

            # Initialize map centered at location
            destination_coords = geolocator.geocode(destination)
            m = folium.Map(location=[destination_coords.latitude, destination_coords.longitude], zoom_start=12)

            # Add marker for destination coordinates
            folium.Marker(location=[destination_coords.latitude, destination_coords.longitude],
                        popup=destination,
                        icon=folium.Icon(color='red', icon="flag")).add_to(m)

            # Plot attractions on the map
            for att in specific_locations:
                lat_lng = geocoder.arcgis(att).latlng
                if lat_lng:
                    folium.Marker(location=lat_lng, popup=att).add_to(m)

            # Display map using st_folium
            st_folium(m)
        with col2:
            st.write("📆  {} ~ {}".format(trip_data[-1][2], trip_data[-1][3]))
            save_trip = st.checkbox("Save this trip")
            # Use the state of the checkbox to execute the saving logic
            if save_trip:
                conn = sqlite3.connect('trip_plans.db')
                c = conn.cursor()
                c.execute("UPDATE trip_plans SET saved = 1 WHERE location = ?", (destination,))
                conn.commit()
                conn.close()
                st.success("Trip saved successfully!")
            st.subheader("Itinerary")
            placeholder = st.empty()
            placeholder.write(itinerary_list)

    if sidebar_selection != "Overview":
        placeholder.empty()
        with col1:
            # Display the itinerary based on the selected day
            for activity in activities:
                for i in titles:
                    if activity[0] == i:
                        activity.remove(i)
                        if sidebar_selection == i.strip("**"):
                            st.subheader(i)
                            for a in activity:
                                activity_images_dict = search_image([a])
                                # Alternative: This provides HQ images, but causes the app to be super slow
                                # activity_images_dict = search_image(specific_locations)
                                for key, value in activity_images_dict.items():
                                    if key in a:
                                        st.image(value, width=250)
                                        # Alternative: This provides HQ images, but causes the app to be super slow
                                        # img = Image.open(io.BytesIO(value))
                                        # st.image(img)
                            with col2:
                                activities_text = "\n".join(activity)
                                placeholder.write(activities_text)

# Saved Trips tab
with tab2:
    st.title("📍 Saved Trips")

    with st.container():
        st.subheader(" ")
        # Create three columns for search bar, filter, and sorting options
        search_col, filter_col, sort_col, order_col = st.columns([2, 1, 1, 1])

        # Search bar
        with search_col:
            search_query = st.text_input("🔎 Search trips", "")

        # Search filters
        with filter_col:
            search_filters = ["Location", "Purpose", "Start Date", "End Date"]
            selected_filter = st.selectbox("Filter by", search_filters)

        # Sorting options
        with sort_col:
            sort_by = ["Location", "Purpose", "Start Date", "End Date"]
            selected_sort_by = st.selectbox("Sort by", sort_by)

        # Radio button to select sorting order
        with order_col:
            sort_order = st.radio("Sort order", ["Ascending", "Descending"])

    conn = sqlite3.connect('trip_plans.db')
    c = conn.cursor()

    # Constructing the SQL query based on search parameters
    if search_query:
        sql_query = f"SELECT * FROM trip_plans WHERE saved = 1 AND {selected_filter} LIKE ?"
        search_param = f"%{search_query}%"
        c.execute(sql_query, (search_param,))
    else:
        c.execute("SELECT * FROM trip_plans WHERE saved = 1")

    saved_trips = c.fetchall()
    conn.close()
    
    if len(saved_trips) == 0:
        st.warning("No saved trips found.")
    else:
        # Create a DataFrame for saved trips
        saved_trips_df = pd.DataFrame(saved_trips, columns=['Location', 'Purpose', 'Start Date', 'End Date', 'Itinerary', 'Saved'])
        
        # Sort the DataFrame based on selected sorting option
        ascending = (sort_order == "Ascending")
        saved_trips_df.sort_values(by=selected_sort_by, ascending=ascending, inplace=True)
        
        # Display the DataFrame using st.dataframe()
        st.dataframe(saved_trips_df)

        # Select a trip to view the itinerary
        selected_trip_index = st.selectbox("Select Trip", saved_trips_df['Location'])

        # Display the full itinerary of the selected trip
        selected_trip = saved_trips_df.loc[saved_trips_df['Location'] == selected_trip_index]
        st.subheader(" ")
        st.subheader(f"🗒️ Full Itinerary for {selected_trip['Purpose'].values[0]} Trip to {selected_trip['Location'].values[0]}")
        st.image(Image.open(io.BytesIO(requests.get(f"https://source.unsplash.com/800x500/?{selected_trip['Location'].values[0]}").content)), width=800)
        st.write(selected_trip['Itinerary'].values[0])

# Packing List tab
with tab3:
    st.title("🧳 Packing List")
    
    class PackingItem(BaseModel):
        item: str
        category: str
        quantity: int
        packed: bool = False

    class Category(Enum):
        CLOTHING = "Clothing"
        TOILETRIES = "Toiletries"
        ELECTRONICS = "Electronics"
        OTHER = "Other"

    con = sqlite3.connect("packing_list.sqlite", isolation_level=None)
    cur = con.cursor()

    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS packing_items (
            id INTEGER PRIMARY KEY,
            item TEXT,
            category TEXT,
            quantity INTEGER,
            packed INTEGER
        )
        """
    )

    def insert_item(data):
        cur.execute(
            """
            INSERT INTO packing_items (item, category, quantity, packed) VALUES (?, ?, ?, ?)
            """,
            (data.item, data.category, data.quantity, 0),
        )
        st.success(f"✅ New item added: {data.item}")

    def delete_item(id):
        cur.execute(
            """
            DELETE FROM packing_items WHERE id = ?
            """,
            (id,),
        )
        st.info("🗑️ Item deleted successfully")

    def main():
        st.markdown("**Add items to your packing list:**")
        item = st.text_input("Item")
        category = st.selectbox("Category", [category.value for category in Category])
        quantity = st.number_input("Quantity", min_value=1, step=1, value=1)

        if st.button("Add Item"):
            new_item = PackingItem(item=item, category=category, quantity=quantity)
            insert_item(new_item)

        st.subheader("Your packing list:")
        headings = ["Item", "Category", "Quantity", "Packed"]

        data = cur.execute(
            """
            SELECT * FROM packing_items
            """
        ).fetchall()

        cols = st.columns(6)
        for heading, col in zip(headings, cols[1:]):
            col.write(heading)

        for row in data:
            cols = st.columns(6)
            delete_button_id = f"delete_button_{row[0]}"
            if cols[0].button("Delete", key=delete_button_id):
                delete_item(row[0])
                st.rerun()

            packed = cols[4].checkbox("Packed", value=row[4]==1, key=f"packed_{row[0]}")
            if packed != (row[4]==1):
                cur.execute(
                    """
                    UPDATE packing_items SET packed = ? WHERE id = ?
                    """,
                    (int(packed), row[0])
                )

            cols[1].write(row[1])
            cols[2].write(row[2])
            cols[3].write(row[3])

    if __name__ == "__main__":
        main()
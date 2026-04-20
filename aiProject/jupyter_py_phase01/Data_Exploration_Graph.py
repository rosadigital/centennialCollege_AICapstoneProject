# -*- coding: utf-8 -*-
"""
Created on Thu Feb 12 14:09:57 2026

@author: marco
"""

import pandas as pd
from sklearn.preprocessing import MinMaxScaler
import matplotlib.pyplot as plt
import folium
from folium.plugins import HeatMap

# -----------------------------
# 1. Load and preprocess delays dataset
# -----------------------------
df = pd.read_csv("../dataset/ttc_delays_2017_2025_unified_with_coords_corrected.csv")

# Convert Date and Time into datetime object
df['Date'] = pd.to_datetime(df['Date'])
df['Time'] = pd.to_datetime(df['Time'], errors='coerce').dt.time
df['Datetime'] = pd.to_datetime(df['Date'].astype(str) + ' ' + df['Time'].astype(str))

# Encode categorical variables
df_encoded = pd.get_dummies(df, columns=['Vehicle_Type','Code','Bound'])

# Normalize numeric features
scaler = MinMaxScaler()
df[['Min Delay','Min Gap']] = scaler.fit_transform(df[['Min Delay','Min Gap']])

# -----------------------------
# 2. Geospatial visualization
# -----------------------------
# Scatter plot of all incidents with coordinates
plt.figure(figsize=(8,8))
plt.scatter(df['Longitude'], df['Latitude'], s=5, alpha=0.5, c='blue')
plt.title("Incident Locations (All Data)")
plt.xlabel("Longitude")
plt.ylabel("Latitude")
plt.show()

# Folium map centered on Toronto
m = folium.Map(location=[43.7, -79.4], zoom_start=11)

# Add incident markers
for _, row in df.dropna(subset=['Latitude','Longitude']).iterrows():
    folium.CircleMarker(
        location=[row['Latitude'], row['Longitude']],
        radius=2,
        color='red',
        fill=True,
        fill_opacity=0.6
    ).add_to(m)

m.save("incident_map_all.html")

# Heatmap
m = folium.Map(location=[43.7, -79.4], zoom_start=11)
heat_data = df.dropna(subset=['Latitude','Longitude'])[['Latitude','Longitude']].values.tolist()
HeatMap(heat_data, radius=8, blur=6, max_zoom=13).add_to(m)
m.save("incident_heatmap_all.html")

# -----------------------------
# 3. Top 20 incident locations
# -----------------------------
top_locations = df['Station'].value_counts().head(20)
print(top_locations)

plt.figure(figsize=(10,6))
top_locations.plot(kind='bar', color='steelblue')
plt.title("Top 20 Incident Locations (All Data)")
plt.ylabel("Number of Incidents")
plt.xticks(rotation=45, ha='right')
plt.show()





import pandas as pd
import folium
from folium.plugins import HeatMap

# Load corrected dataset
df = pd.read_csv("../dataset/ttc_delays_2017_2025_unified_with_coords_corrected.csv")

# Drop Station_cleaned if present
if 'Station_cleaned' in df.columns:
    df = df.drop(columns=['Station_cleaned'])

# Function to build heatmap for a given vehicle type
def build_heatmap(df, vehicle_type, filename):
    subset = df[(df['Vehicle_Type'] == vehicle_type) & df['Latitude'].notna() & df['Longitude'].notna()]
    heat_data = subset[['Latitude','Longitude']].values.tolist()
    
    m = folium.Map(location=[43.7, -79.4], zoom_start=11)
    HeatMap(heat_data, radius=8, blur=6, max_zoom=13).add_to(m)
    m.save(filename)
    print(f"{vehicle_type} heatmap saved to {filename} with {len(heat_data)} points.")

# Build three maps
build_heatmap(df, "BUS", "bus_heatmap.html")
build_heatmap(df, "STREETCAR", "streetcar_heatmap.html")
build_heatmap(df, "SUBWAY", "subway_heatmap.html")



# TOP 20 Incident location per transportation type
import matplotlib.pyplot as plt

def plot_top_locations(df, vehicle_type):
    subset = df[df['Vehicle_Type'] == vehicle_type]
    top_locations = subset['Station'].value_counts().head(20)
    
    plt.figure(figsize=(10,6))
    ax = top_locations.plot(kind='bar', color='steelblue')
    plt.title(f"Top 20 Incident Locations ({vehicle_type})")
    plt.ylabel("Number of Incidents")
    
    # Rotate tick labels 45 degrees for readability
    plt.xticks(rotation=45, ha='right')
    
    # Add numbers on top of each bar, centered horizontally
    for p in ax.patches:
        ax.annotate(
            str(int(p.get_height())),
            (p.get_x() + p.get_width() / 2., p.get_height() + 50),  # spacing above bar
            ha='center', va='bottom', fontsize=9, color='black', rotation=45
        )
    
    # Expand y-axis limit so labels don’t overlap the border
    ax.set_ylim(0, max(top_locations) * 1.10)
    
    # Remove top and right spines (borders)
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    
    plt.tight_layout()
    plt.show()
    print(f"\nTop 20 {vehicle_type} incident locations:\n")
    print(top_locations)

# Generate one graph per transportation type
plot_top_locations(df, "BUS")
plot_top_locations(df, "STREETCAR")
plot_top_locations(df, "SUBWAY")


# TOP 20 Incident cause per transportation type
import pandas as pd
import matplotlib.pyplot as plt

# Load enriched unified dataset (already saved with 'Cause' column)
df = pd.read_csv("../dataset/ttc_delays_2017_2025_unified_with_coords_corrected.csv")

def plot_top_causes(df, vehicle_type):
    subset = df[df['Vehicle_Type'] == vehicle_type]
    
    # Count top 20 causes using the enriched 'Cause' column
    top_causes = subset['Description'].value_counts().head(20)
    
    plt.figure(figsize=(10,6))
    ax = top_causes.plot(kind='bar', color='darkorange')
    plt.title(f"Top 20 Causes of Incidents ({vehicle_type})")
    plt.ylabel("Number of Incidents")
    
    # Rotate tick labels
    plt.xticks(rotation=45, ha='right')
    
    # Add numbers on top of each bar
    for p in ax.patches:
        ax.annotate(
            str(int(p.get_height())),
            (p.get_x() + p.get_width() / 2., p.get_height() + 50),
            ha='center', va='bottom', fontsize=9, color='black', rotation=45
        )
    
    # Expand y-axis
    ax.set_ylim(0, top_causes.max() * 1.10)
    
    # Remove top and right spines
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    
    plt.tight_layout()
    plt.show()
    
    # Print top 20 causes with counts
    print(f"\nTop 20 {vehicle_type} incident causes:")
    print(top_causes)

# Generate plots per transportation type
plot_top_causes(df, "BUS")
plot_top_causes(df, "STREETCAR")
plot_top_causes(df, "SUBWAY")







# Correlations
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from scipy.stats import chi2_contingency

# Load enriched unified dataset (already saved with 'Cause' column)
df = pd.read_csv("../dataset/ttc_delays_2017_2025_unified_with_coords_corrected.csv")

# Ensure datetime parsing
df['Datetime'] = pd.to_datetime(df['Date'].astype(str) + ' ' + df['Time'].astype(str), errors='coerce')
df['Hour'] = df['Datetime'].dt.hour
df['DayOfWeek'] = df['Datetime'].dt.day_name()

# -----------------------------
# Function for correlation analysis
# -----------------------------
def correlation_analysis(df, vehicle_type):
    subset = df[df['Vehicle_Type'] == vehicle_type].copy()
    print(f"\n=== Correlation Analysis for {vehicle_type} ===")
    
    # --- Day vs Cause heatmap ---
    pivot_day_cause = subset.pivot_table(index='DayOfWeek', columns='Description', values='Station', aggfunc='count').fillna(0)
    plt.figure(figsize=(14,6))
    sns.heatmap(pivot_day_cause, cmap='Blues')
    plt.title(f"Incidents by Day and Cause ({vehicle_type})")
    plt.xlabel("Cause of Accident")
    plt.ylabel("Day of Week")
    plt.tight_layout()
    plt.show()
            
    # --- Hour vs Cause heatmap 
    pivot_hour_cause = subset.pivot_table(index='Description', columns='Hour', values='Station', aggfunc='count').fillna(0)
    
    plt.figure(figsize=(14,10))
    ax = sns.heatmap(pivot_hour_cause, cmap='Reds')
    
    plt.title(f"Incidents by Hour and Cause ({vehicle_type})")
    plt.xlabel("Hour of Day")
    plt.ylabel("Cause of Accident")
    
    # Format x-axis ticks: integers only (0–23)
    new_labels = [str(int(float(label.get_text()))) for label in ax.get_xticklabels()]
    ax.set_xticklabels(new_labels, rotation=0)
    
    # Keep causes upright on y-axis
    ax.set_yticklabels(ax.get_yticklabels(), rotation=0)
    
    plt.tight_layout()
    plt.show()
    
    # Limit to top N stations by incident count prioritizing incident
    top_stations = subset['Station'].value_counts().head(20).index
    pivot_station_cause = subset[subset['Station'].isin(top_stations)] \
        .pivot_table(index='Station', columns='Description', values='Hour', aggfunc='count').fillna(0)
    
    plt.figure(figsize=(14,10))
    ax = sns.heatmap(pivot_station_cause, cmap='Greens')
    
    plt.title(f"Top 20 Stations by Cause ({vehicle_type})")
    plt.xlabel("Cause of Accident")
    plt.ylabel("Station")
    
    ax.set_yticklabels(ax.get_yticklabels(), rotation=0)
    plt.tight_layout()
    plt.show()

    
    # --- Chi-square test: Cause vs Day ---
    contingency_day = pd.crosstab(subset['DayOfWeek'], subset['Description'])
    chi2, p, dof, expected = chi2_contingency(contingency_day)
    print(f"Chi-square test (Cause vs Day) for {vehicle_type}: chi2={chi2:.2f}, p-value={p:.4f}")
    
    # --- Chi-square test: Cause vs Hour ---
    contingency_hour = pd.crosstab(subset['Hour'], subset['Description'])
    chi2, p, dof, expected = chi2_contingency(contingency_hour)
    print(f"Chi-square test (Cause vs Hour) for {vehicle_type}: chi2={chi2:.2f}, p-value={p:.4f}")
    
    # --- Chi-square test: Cause vs Station ---
    contingency_station = pd.crosstab(subset['Station'], subset['Description'])
    chi2, p, dof, expected = chi2_contingency(contingency_station)
    print(f"Chi-square test (Cause vs Station) for {vehicle_type}: chi2={chi2:.2f}, p-value={p:.4f}")

# -----------------------------
# Run analysis for each vehicle type
# -----------------------------
correlation_analysis(df, "BUS")
correlation_analysis(df, "STREETCAR")
correlation_analysis(df, "SUBWAY")





# Follium map for the top 20 station for number of incident with description
import pandas as pd
import folium

# Load enriched unified dataset
df = pd.read_csv("../dataset/ttc_delays_2017_2025_unified_with_coords_corrected.csv")

def plot_combined_map(df):
    # Initialize map centered on Toronto
    m = folium.Map(location=[43.7, -79.4], zoom_start=11)

    # Vehicle type colors
    colors = {"BUS": "red", "STREETCAR": "blue", "SUBWAY": "green"}

    for vehicle_type in ["BUS", "STREETCAR", "SUBWAY"]:
        subset = df[df['Vehicle_Type'] == vehicle_type]

        # Count incidents per station
        station_counts = subset['Station'].value_counts().reset_index()
        station_counts.columns = ['Station', 'Total']

        # Keep top 20 stations
        top20_stations = station_counts.head(20)['Station']

        # Aggregate causes per station
        station_cause_counts = subset.groupby(['Station','Description']).size().reset_index(name='Count')

        # Coordinates per station
        station_coords = subset.groupby('Station')[['Latitude','Longitude']].mean().reset_index()

        # Merge totals and coords
        station_summary = station_counts.merge(station_coords, on='Station', how='left')
        station_summary = station_summary[station_summary['Station'].isin(top20_stations)]

        # Create a feature group for each vehicle type
        fg = folium.FeatureGroup(name=vehicle_type)

        for _, row in station_summary.iterrows():
            station = row['Station']
            total = row['Total']
            lat, lon = row['Latitude'], row['Longitude']

            # Get cause breakdown for this station (alphabetical order)
            causes = station_cause_counts[station_cause_counts['Station'] == station] \
                        .sort_values('Description')

            # Build popup text with scrollbar
            popup_html = f"""
            <div style="max-height:200px; overflow-y:auto;">
            <b>Station:</b> {station}<br>
            <b>Total Incidents:</b> {total}<br><br>
            <b>Causes:</b><br>
            """
            for _, c in causes.iterrows():
                popup_html += f"- {c['Description']}: {c['Count']}<br>"
            popup_html += "</div>"

            # Custom pin with number
            color = colors[vehicle_type]
            fg.add_child(
                folium.Marker(
                    location=[lat, lon],
                    popup=folium.Popup(popup_html, max_width=400),
                    tooltip=station,   # hover shows station/street name
                    icon=folium.DivIcon(
                        html=f"""
                        <div style="transform: translate(-50%, -50%);">
                            <svg xmlns="http://www.w3.org/2000/svg" width="30" height="40">
                                <path d="M15 0 C23 0 30 7 30 15 C30 25 15 40 15 40 C15 40 0 25 0 15 C0 7 7 0 15 0 Z"
                                      fill="{color}" stroke="black" stroke-width="1"/>
                                <text x="15" y="22" text-anchor="middle" font-size="12" font-weight="bold" fill="white">{total}</text>
                            </svg>
                        </div>
                        """
                    )
                )
            )

        # Add feature group to map
        m.add_child(fg)

    # Add layer control (checkboxes)
    folium.LayerControl(collapsed=False).add_to(m)

    # Add custom legend with colored circles
    legend_html = """
     <div style="
     position: fixed; 
     bottom: 50px; left: 50px; width: 180px; height: 120px; 
     background-color: white; 
     border:2px solid grey; z-index:9999; font-size:14px;
     padding: 10px; opacity: 0.9;">
     <b>Legend</b><br>
     <div style="display:flex; align-items:center;">
         <div style="width:15px; height:15px; background-color:red; border-radius:50%; margin-right:8px;"></div>
         Bus
     </div>
     <div style="display:flex; align-items:center;">
         <div style="width:15px; height:15px; background-color:blue; border-radius:50%; margin-right:8px;"></div>
         Streetcar
     </div>
     <div style="display:flex; align-items:center;">
         <div style="width:15px; height:15px; background-color:green; border-radius:50%; margin-right:8px;"></div>
         Subway
     </div>
     </div>
    """
    m.get_root().html.add_child(folium.Element(legend_html))

    return m

# Example usage
combined_map = plot_combined_map(df)
combined_map.save("combined_incidents_map_with_legend.html")



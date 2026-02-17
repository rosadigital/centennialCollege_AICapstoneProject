# -*- coding: utf-8 -*-
"""
Created on Tue Feb 17 09:43:01 2026

@author: marco
"""

# === Imports ===
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from sklearn.model_selection import train_test_split, cross_val_score
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_squared_error
from sklearn.preprocessing import LabelEncoder
from sklearn.cluster import KMeans
import joblib


#%% === 1. Load Data ===
df = pd.read_csv("../dataset/ttc_delays_2017_2025_unified_with_coords_corrected.csv")

# Check missing values before drop
print("Missing values before drop:")
print(df.isna().sum())
print("Rows before drop:", len(df))


#%% Audit Function (audit_missing_delay)
"""
- Purpose: Identifies how many rows with missing Min Delay could potentially be recovered.
- Method: Groups the dataset by Line + Station. For each missing row, checks if its group contains valid delay values.
- Output: Reports total missing rows, number recoverable, and percentage recoverable.
- Example Result: Out of 5,129 missing rows, 2,127 (~41%) were recoverable.
"""

def audit_missing_delay(df):
    """
    Check how many rows with missing Min Delay could be filled
    using group-based imputation (same Line + Station).
    """
    # Rows with missing Min Delay
    missing = df[df['Min Delay'].isna()].copy()
    
    # Drop rows where Line or Station is NaN (can't group them)
    missing = missing.dropna(subset=['Line','Station'])
    
    # Group by Line + Station
    grouped = df.groupby(['Line','Station'])['Min Delay']
    
    # Check recoverability
    recoverable_flags = []
    for idx, row in missing.iterrows():
        try:
            group_vals = grouped.get_group((row['Line'], row['Station']))
            recoverable_flags.append(group_vals.notna().any())
        except KeyError:
            recoverable_flags.append(False)
    
    recoverable = pd.Series(recoverable_flags, index=missing.index)
    
    total_missing = len(df[df['Min Delay'].isna()])
    total_recoverable = recoverable.sum()
    
    print(f"Total rows with missing Min Delay: {total_missing}")
    print(f"Rows potentially recoverable (same Line+Station has valid delay): {total_recoverable}")
    print(f"Percentage recoverable: {100*total_recoverable/total_missing:.2f}%")
    
    return missing[recoverable]


#%% Fill Function (fill_missing_delay)
"""
- Purpose: Imputes missing Min Delay and Min Gap values for recoverable rows.
- Method: For each missing entry, replaces it with the median value of its group (Line + Station). Median is chosen because it is robust to outliers.
- Output: Returns a cleaned dataset with fewer missing values, improving the amount of usable data for AI modeling.
- Benefit: Preserves ~40% of rows that would otherwise be discarded, strengthening the training dataset and improving model reliability.
"""

def fill_missing_delay(df):
    """
    Fill missing Min Delay and Min Gap using group median
    based on Line + Station.
    """
    # Group by Line + Station
    group_delay = df.groupby(['Line','Station'])['Min Delay']
    group_gap = df.groupby(['Line','Station'])['Min Gap']
    
    # Apply median imputation
    df['Min Delay'] = df.apply(
        lambda row: group_delay.get_group((row['Line'], row['Station'])).median()
        if pd.isna(row['Min Delay']) and (row['Line'], row['Station']) in group_delay.groups
        else row['Min Delay'],
        axis=1
    )
    
    df['Min Gap'] = df.apply(
        lambda row: group_gap.get_group((row['Line'], row['Station'])).median()
        if pd.isna(row['Min Gap']) and (row['Line'], row['Station']) in group_gap.groups
        else row['Min Gap'],
        axis=1
    )
    
    return df

print(audit_missing_delay(df))
df_filled = fill_missing_delay(df)

# Check impact
# Total rows
total_rows = len(df_filled)

# Missing values per column
missing_counts = df_filled.isna().sum()

# Convert to percentages
missing_percent = (missing_counts / total_rows) * 100

# Combine into a single DataFrame for reporting
missing_report = pd.DataFrame({
    "Missing Count": missing_counts,
    "Missing %": missing_percent.round(2)
})

# Add an empty row before the total
missing_report.loc[""] = ["", ""]

# Add final row with total rows in dataset
missing_report.loc["Total Rows"] = [total_rows, ""]

print("Missing values report (before dropping):")
print(missing_report)


#%% Final Cleaning for Modeling
"""
This section prepares two clean datasets: one for modeling, where we drop non‑essential columns,
fill missing values, and flag system‑wide "GENERAL DELAY" cases, and another for clustering,
where we keep coordinates to analyze geographic hotspots while excluding those general delays.
"""

# Start from the filled dataset
df_model = df_filled.copy()

# Drop non-essential columns for modeling
df_model = df_model.drop(columns=['Latitude','Longitude','Bound','Vehicle','Min Gap'])

# Fill missing Line and Station with "Unknown"
df_model['Line'] = df_model['Line'].fillna("Unknown")
df_model['Station'] = df_model['Station'].fillna("Unknown")

# Drop rows missing Min Delay (target variable)
df_model = df_model.dropna(subset=['Min Delay'])

# Report
#print("Final columns for modeling:", df_model.columns.tolist())
#print("Rows after final cleaning:", len(df_model))
#print("Remaining missing values:", df_model.isna().sum())
# Flag GENERAL DELAY cases
df_model['IsGeneralDelay'] = df_model['Description'].str.upper().eq("GENERAL DELAY")

print("Final columns for modeling:", df_model.columns.tolist())
print("Rows after final cleaning:", len(df_model))
print("Remaining missing values:", df_model.isna().sum())

# Separate dataset for clustering (keep coordinates)
df_spatial = df_filled.copy()
df_spatial['Line'] = df_spatial['Line'].fillna("Unknown")
df_spatial['Station'] = df_spatial['Station'].fillna("Unknown")
df_spatial['IsGeneralDelay'] = df_spatial['Description'].str.upper().eq("GENERAL DELAY")

print(df_spatial.head())


#%% === 2. Define Functions ===
"""
We trained machine learning models to predict the expected delay duration (in minutes)
for buses, streetcars, and subways based on incident descriptions, locations, and time patterns, 
and evaluated their accuracy using RMSE and cross‑validation to ensure reliable performance.
"""


"""
This function prepares the dataset for modeling by encoding categorical variables
and extracting time-based features such as hour, weekday, and rush hour.
"""
def preprocess_dataset(subset):
    """Encode categorical variables and add time-based features."""
    label_enc = LabelEncoder()
    subset['Station_enc'] = label_enc.fit_transform(subset['Station'])
    subset['Description_enc'] = label_enc.fit_transform(subset['Description'])
    subset['Line_enc'] = label_enc.fit_transform(subset['Line'])
    subset['Code_enc'] = label_enc.fit_transform(subset['Code'])

    subset['Datetime'] = pd.to_datetime(subset['Date'] + " " + subset['Time'], errors='coerce')
    subset['Hour'] = subset['Datetime'].dt.hour.fillna(-1)
    subset['Weekday'] = subset['Datetime'].dt.weekday.fillna(-1)
    subset['RushHour'] = subset['Hour'].apply(lambda h: 1 if h in [7,8,9,16,17,18] else 0)

    return subset

"""
This function trains a Random Forest model on the prepared dataset for each vehicle type,
evaluates its performance using RMSE and cross-validation, and saves the trained model.
"""
def train_and_evaluate(subset, vehicle_type):
    """Train Random Forest and report RMSE for one vehicle type."""
    features = ['Station_enc','Description_enc','Line_enc','Code_enc','Hour','Weekday','RushHour']
    X = subset[features]
    y = subset['Min Delay']

    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

    model = RandomForestRegressor(n_estimators=100, random_state=42)
    model.fit(X_train, y_train)

    y_pred = model.predict(X_test)
    rmse = np.sqrt(mean_squared_error(y_test, y_pred))
    print(f"{vehicle_type} RMSE:", rmse)

    cv_scores = cross_val_score(model, X, y, cv=5, scoring='neg_root_mean_squared_error')
    print(f"{vehicle_type} CV RMSE:", -cv_scores.mean())

    joblib.dump(model, f"{vehicle_type.lower()}_delay_predictor_rf.pkl")
    return model

"""
This function performs geographic clustering of incidents using latitude and longitude,
excluding system-wide "GENERAL DELAY" cases, to identify hotspots of localized delays.
"""
def cluster_hotspots(subset, vehicle_type, n_clusters=5):
    """Cluster coordinates to detect hotspots, excluding GENERAL DELAY cases."""
    if not {'Latitude','Longitude'}.issubset(subset.columns):
        print(f"No coordinates available for {vehicle_type}, skipping clustering.")
        return

    coords_subset = subset[~subset['IsGeneralDelay']][['Latitude','Longitude']].dropna()
    if coords_subset.empty:
        print(f"No coordinates available for {vehicle_type}, skipping clustering.")
        return

    kmeans = KMeans(n_clusters=n_clusters, random_state=42)
    subset.loc[coords_subset.index, 'Cluster'] = kmeans.fit_predict(coords_subset)

    plt.figure(figsize=(8,6))
    sns.scatterplot(x='Longitude', y='Latitude', hue=subset['Cluster'], palette='Set1', data=subset)
    plt.title(f"{vehicle_type} Geographic Hotspots of Incidents (excluding GENERAL DELAY)")
    plt.show()

    
#%% === 3. Split into Vehicle Types ===
"""
In this section we evaluate model performance for each vehicle type by calculating
RMSE (Root Mean Squared Error), which measures how far predictions are from actual delays,
and CV RMSE (cross‑validated RMSE), which checks how well the model generalizes across
different data splits. This ensures our Random Forest is not just fitting the training data
but can reliably predict unseen delays, and we summarize the results in a table for easy comparison.
"""

vehicle_types = df_model['Vehicle_Type'].unique()
    
results = []

for vtype in vehicle_types:
    print(f"\n=== Processing {vtype} ===")
    subset_model = df_model[df_model['Vehicle_Type'] == vtype].copy()
    subset_model = preprocess_dataset(subset_model)
    model = train_and_evaluate(subset_model, vtype)

    subset_spatial = df_spatial[df_spatial['Vehicle_Type'] == vtype].copy()
    cluster_hotspots(subset_spatial, vtype)

    # Collect results
    results.append({
        "Vehicle_Type": vtype,
        "RMSE": np.sqrt(mean_squared_error(
            model.predict(subset_model[['Station_enc','Description_enc','Line_enc','Code_enc','Hour','Weekday','RushHour']]),
            subset_model['Min Delay']
        )),
    })

# Convert to DataFrame for easy viewing
results_df = pd.DataFrame(results)
print("\n=== Summary of RMSE per Vehicle Type ===")
print(results_df)    
    
#%%% Results
"""
- Bus: RMSE ≈ 45 minutes, CV RMSE ≈ 49.
Bus delays are the hardest to predict due to external factors like traffic and weather, which introduce high variability.
- Streetcar: RMSE ≈ 33 minutes, CV RMSE ≈ 37.
Streetcars show more predictable patterns than buses, but still face street‑level disruptions.
- Subway: RMSE ≈ 10 minutes, CV RMSE ≈ 11.
Subway delays are the most predictable, reflecting the controlled environment of underground transit.
""" 
    
    
    
    
    
    

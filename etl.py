import pandas as pd
import sqlite3
import os
import logging

# Set up logging to file and console
log_file = 'data_processing.log'
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_file),
        logging.StreamHandler()  # This will still print logs to console
    ]
)
# A dictionary to map month names to their numeric counterparts
month_map = {
    'January': '01', 'February': '02', 'March': '03', 'April': '04',
    'May': '05', 'June': '06', 'July': '07', 'August': '08',
    'September': '09', 'October': '10', 'November': '11', 'December': '12'
}

# A reverse dictionary to map numeric month format to the full month name
reverse_month_map = {v: k for k, v in month_map.items()}

# Clean data functions for different datasets (FHV, FHVHV, Yellow, Green)
def clean_fhv_data(fhv):
    logging.info("Cleaning FHV data...")
    
    # Avoiding chained assignment issues
    fhv = fhv.copy()
    
    fhv.columns = fhv.columns.str.lower()
    fhv['sr_flag'] = fhv['sr_flag'].fillna(0)
    fhv['pulocationid'] = fhv['pulocationid'].fillna(0)
    fhv['dolocationid'] = fhv['dolocationid'].fillna(0)
    fhv['pickup_datetime'] = pd.to_datetime(fhv['pickup_datetime'], errors='coerce')
    fhv['dropoff_datetime'] = pd.to_datetime(fhv['dropoff_datetime'], errors='coerce')
    fhv['trip_duration_minutes'] = (fhv['dropoff_datetime'] - fhv['pickup_datetime']).dt.total_seconds() / 60
    fhv = fhv[fhv['trip_duration_minutes'] > 0]
    
    logging.info("FHV data cleaned.")
    return fhv

def clean_fhvhv_data(fhvhv):
    logging.info("Cleaning FHVHV data...")
    
    # Avoiding chained assignment issues
    fhvhv = fhvhv.copy()
    
    fhvhv.columns = fhvhv.columns.str.lower()
    flag_columns = ['shared_request_flag', 'shared_match_flag', 'wav_request_flag', 'wav_match_flag', 'access_a_ride_flag']
    fhvhv[flag_columns] = fhvhv[flag_columns].fillna(0)
    fhvhv[['pulocationid', 'dolocationid']] = fhvhv[['pulocationid', 'dolocationid']].fillna(0)
    fhvhv['originating_base_num'] = fhvhv['originating_base_num'].fillna('unknown')
    fhvhv['on_scene_datetime'] = fhvhv['on_scene_datetime'].fillna(pd.NaT)
    datetime_columns = ['pickup_datetime', 'dropoff_datetime', 'request_datetime', 'on_scene_datetime']
    fhvhv[datetime_columns] = fhvhv[datetime_columns].apply(pd.to_datetime, errors='coerce')
    fhvhv['trip_duration_minutes'] = (fhvhv['dropoff_datetime'] - fhvhv['pickup_datetime']).dt.total_seconds() / 60
    fhvhv = fhvhv[fhvhv['trip_duration_minutes'] > 0]
    fhvhv['trip_miles'] = fhvhv['trip_miles'].fillna(0)
    fhvhv['trip_duration_hours'] = fhvhv['trip_duration_minutes'] / 60
    fhvhv['average_speed_mph'] = fhvhv['trip_miles'] / fhvhv['trip_duration_hours']
    
    logging.info("FHVHV data cleaned.")
    return fhvhv

def clean_yellow_data(yellow):
    logging.info("Cleaning Yellow Taxi data...")
    
    # Avoiding chained assignment issues
    yellow = yellow.copy()
    
    yellow.columns = yellow.columns.str.lower()
    yellow = yellow[yellow['passenger_count'] > 0]
    yellow['ratecodeid'] = yellow['ratecodeid'].fillna(1)
    yellow['store_and_fwd_flag'] = yellow['store_and_fwd_flag'].fillna('N')
    yellow['congestion_surcharge'] = yellow['congestion_surcharge'].fillna(0)
    yellow['airport_fee'] = yellow['airport_fee'].fillna(0)
    yellow['tpep_pickup_datetime'] = pd.to_datetime(yellow['tpep_pickup_datetime'], errors='coerce')
    yellow['tpep_dropoff_datetime'] = pd.to_datetime(yellow['tpep_dropoff_datetime'], errors='coerce')
    yellow['trip_duration_minutes'] = (yellow['tpep_dropoff_datetime'] - yellow['tpep_pickup_datetime']).dt.total_seconds() / 60
    yellow = yellow[yellow['trip_duration_minutes'] > 0.1]
    yellow['trip_duration_hours'] = yellow['trip_duration_minutes'] / 60
    yellow['average_speed_mph'] = yellow['trip_distance'] / yellow['trip_duration_hours']
    yellow['average_speed_mph'] = yellow['average_speed_mph'].fillna(0)
    
    logging.info("Yellow Taxi data cleaned.")
    return yellow

def clean_green_data(green):
    logging.info("Cleaning Green Taxi data...")
    
    # Avoiding chained assignment issues
    green = green.copy()
    
    green.columns = green.columns.str.lower()
    green = green[green['passenger_count'] > 0]
    green['ratecodeid'] = green['ratecodeid'].fillna(1)
    green['store_and_fwd_flag'] = green['store_and_fwd_flag'].fillna('N')
    green['payment_type'] = green['payment_type'].fillna(green['payment_type'].mode()[0])
    green['trip_type'] = green['trip_type'].fillna(1)
    green['congestion_surcharge'] = green['congestion_surcharge'].fillna(0)
    green['lpep_pickup_datetime'] = pd.to_datetime(green['lpep_pickup_datetime'], errors='coerce')
    green['lpep_dropoff_datetime'] = pd.to_datetime(green['lpep_dropoff_datetime'], errors='coerce')
    green['trip_duration_minutes'] = (green['lpep_dropoff_datetime'] - green['lpep_pickup_datetime']).dt.total_seconds() / 60
    green = green[green['trip_duration_minutes'] > 0.1]
    green['trip_duration_hours'] = green['trip_duration_minutes'] / 60
    green['average_speed_mph'] = green['trip_distance'] / green['trip_duration_hours']
    green['average_speed_mph'] = green['average_speed_mph'].fillna(0)
    
    logging.info("Green Taxi data cleaned.")
    return green

# Function to clean data based on filename pattern
def clean_data_based_on_filename(file_name, df):
    if 'green' in file_name.lower():
        return clean_green_data(df)
    elif 'yellow' in file_name.lower():
        return clean_yellow_data(df)
    elif 'fhv' in file_name.lower() and 'fhvhv' not in file_name.lower():
        return clean_fhv_data(df)
    elif 'fhvhv' in file_name.lower():
        return clean_fhvhv_data(df)
    else:
        raise ValueError("Filename does not match any known dataset type.")





# Function to load data, clean it, and save the results
def process_data(base_dir, year=None, start_month=None, end_month=None):
    # Handle if only a year is passed, or both year and month range are passed
    if start_month and not end_month:
        end_month = start_month  # Process only the start month if no end month is provided
    
    months_to_process = month_map.keys() if not start_month else list(month_map.keys())[list(month_map.values()).index(start_month): list(month_map.values()).index(end_month) + 1]
    
    years_to_process = [year] if year else range(2019, 2025)  # Example range, update as needed
    
    for year in years_to_process:
        for month_name in months_to_process:
            logging.info(f"Processing {month_name} {year}")
            year_month_dir = os.path.join(base_dir, str(year), month_name)
            
            # File paths for datasets
            datasets = {
                'fhv': os.path.join(year_month_dir, f'fhv_tripdata_{year}-{month_map[month_name]}.parquet'),
                'fhvhv': os.path.join(year_month_dir, f'fhvhv_tripdata_{year}-{month_map[month_name]}.parquet'),
                'yellow': os.path.join(year_month_dir, f'yellow_tripdata_{year}-{month_map[month_name]}.parquet'),
                'green': os.path.join(year_month_dir, f'green_tripdata_{year}-{month_map[month_name]}.parquet')
            }
            
            for dataset_name, file_path in datasets.items():
                try:
                    logging.info(f"Loading {dataset_name.upper()} data from {file_path}")
                    df = pd.read_parquet(file_path)
                    
                   # df = df.head(5000)  # Limit rows for testing, modify as necessary
                    # Assuming df is your original DataFrame
                    df = df.sample(n=5000, random_state=42)

                    # To reset the index (optional, to avoid keeping the original index)
                    df.reset_index(drop=True, inplace=True)
                    cleaned_df = clean_data_based_on_filename(file_path, df)
                    
                    save_cleaned_data(cleaned_df, dataset_name, year, month_name)
                except FileNotFoundError:
                    logging.warning(f"File not found: {file_path}")

def save_cleaned_data(cleaned_data, dataset_name, year, month_name):
    # Directory to save the cleaned data
    save_dir = os.path.join(os.getcwd(), "Cleaned_data", str(year), month_name)
    os.makedirs(save_dir, exist_ok=True)
    
    # Save as CSV
    save_path = os.path.join(save_dir, f"cleaned_{dataset_name}_tripdata_{year}_{month_map[month_name]}.csv")
    logging.info(f"Saving cleaned {dataset_name} data to {save_path}")
    #cleaned_data.to_csv(save_path, index=False)  # Save as CSV file
    
    # Insert into SQLite database
    conn = sqlite3.connect('trip_sample_data.db')
    logging.info(f"Inserting {dataset_name.upper()} data into SQLite database")
    
    cleaned_data.to_sql(f'{dataset_name}_tripdata', conn, if_exists='append', index=False)
    conn.close()

# Example usage:
base_dir = 'C:/Users/ASH/Downloads/Data Engineering/Scrapping Work/data' # adjust path according to your requirements
#process_data(base_dir, year=2024, start_month='06')  # Process for a specific year and month
#process_data(base_dir, year=2024, start_month='01', end_month='04')  # Process for a month range
#process_data(base_dir, year=2024)  # Process for the whole year
process_data(base_dir)
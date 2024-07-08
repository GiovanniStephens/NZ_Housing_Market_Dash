import os
import re
import keyring
import utils
from requests_oauthlib import OAuth1Session
import json
import pandas as pd
import numpy as np
import time
from datetime import datetime
from dotenv import load_dotenv

try:
    load_dotenv()
    load_dotenv('config.env')
except FileNotFoundError:
    print('No config file found.')


def get_trademe_credentials():
    TRADEME_API_KEY = os.getenv('TRADEME_API_KEY')
    TRADEME_API_SECRET = os.getenv('TRADEME_API_SECRET')
    if TRADEME_API_KEY is None or TRADEME_API_SECRET is None:
        print('No API key or secret found in environment variables. Trying to fetch from keyring.')
        TRADEME_API_KEY = keyring.get_password('Trademe', 'key')
        TRADEME_API_SECRET = keyring.get_password('Trademe', 'secret')
    return TRADEME_API_KEY, TRADEME_API_SECRET


def connect_to_trademe():
    TRADEME_API_KEY, TRADEME_API_SECRET = get_trademe_credentials()
    trademe = OAuth1Session(TRADEME_API_KEY, TRADEME_API_SECRET)
    return trademe


def fetch_trademe_data(trademe, url):
    # Make initial request to get number of pages
    print('Fetching page 1 of n')
    returned_page_all = trademe.get(url)
    data_raw = returned_page_all.content
    parsed_data = json.loads(data_raw)
    listings = parsed_data['List']
    total_count = parsed_data['TotalCount']
    total_n_requests = int(total_count/500) + 1
    data_df = pd.DataFrame.from_dict(listings)
    for i in range(2, total_n_requests+1):
        print(f'Fetching page {i} of {total_n_requests}')
        name_num = str(i)
        page_url = f'{url}&page={name_num}&sort_order=Default HTTP/1.1'
        returned_page_all = trademe.get(page_url)
        if returned_page_all.status_code != 200:
            print('Error: ', returned_page_all.status_code)
            print('Error message: ', returned_page_all.text)
            # Todo: Implement error handling
            break
        data_raw = returned_page_all.content
        parsed_data = json.loads(data_raw)
        listings = parsed_data['List']
        data_df = pd.concat([data_df, pd.DataFrame.from_dict(listings)], ignore_index=True)
        time.sleep(0.5)     # Sleep for 0.5 seconds to avoid rate limiting
    return data_df


def convert_date_string(date_string):
    timestamp = int(re.search(r'\d+', date_string).group())
    date_time = datetime.fromtimestamp(timestamp / 1000.0)
    date_time = date_time.strftime('%Y-%m-%d %H:%M:%S')
    return date_time


def extract_price(price_string):
    regex = r'\$\d{1,3}(,\d{3})*(\.\d{2})?'
    match = re.search(regex, price_string)
    if match:
        matched_string = match.group(0)
        cleaned_string = matched_string.replace('$', '').replace(',', '')
        return cleaned_string
    else:
        return None


def store_date(data, supabase):
    data = data.drop_duplicates(subset=['ListingId'])
    data['StartDate'] = data['StartDate'].apply(convert_date_string)
    data['EndDate'] = data['EndDate'].apply(convert_date_string)
    data['Price'] = data['PriceDisplay'].apply(extract_price)
    data['Price'] = data['Price'].replace('', None).astype(float, errors='ignore').replace({np.nan: None})
    data['Parking'] = data['Parking'].replace('', None)
    data['Amenities'] = data['Amenities'].fillna('').replace('', None)
    data = data.replace({np.nan: None})
    data['Latitude'] = data['GeographicLocation'].apply(lambda x: float(x['Latitude']))
    data['Longitude'] = data['GeographicLocation'].apply(lambda x: float(x['Longitude']))
    columns = os.getenv('LISTING_COLUMNS').split(',')
    data = data[columns]
    data_to_insert = []
    for i in range(len(data)):
        data_to_insert.append(data.iloc[i].to_dict())
    supabase.table("Listings").upsert(data_to_insert, on_conflict='ListingId').execute()


if __name__ == '__main__':
    supabase_url = os.getenv('SUPABASE_URL')
    supabase_key = os.getenv('SUPABASE_KEY')
    if not supabase_url or not supabase_key:
        raise ValueError("Supabase credentials are not set in the environment variables.")
    trademe = connect_to_trademe()
    url = os.getenv('TRADEME_HOUSES_URL')
    data = fetch_trademe_data(trademe, url)
    # data = pd.read_pickle('data.pkl')
    supabase = utils.connect_to_supabase()
    store_date(data, supabase)

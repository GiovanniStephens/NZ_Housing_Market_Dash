from datetime import datetime
from dotenv import load_dotenv
import json
import keyring
import logging
import math
import numpy as np
import os
import pandas as pd
import re
from requests_oauthlib import OAuth1Session
import time
import utils
import concurrent.futures
from os import cpu_count

# Configure logging for GitHub Actions
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

try:
    load_dotenv()
    load_dotenv('config.env')
except FileNotFoundError:
    logging.warning('No config file found')


def get_trademe_credentials():
    TRADEME_API_KEY = os.getenv('TRADEME_API_KEY')
    TRADEME_API_SECRET = os.getenv('TRADEME_API_SECRET')
    if TRADEME_API_KEY is None or TRADEME_API_SECRET is None:
        logging.info('No API key or secret found in environment variables. Trying to fetch from keyring')
        TRADEME_API_KEY = keyring.get_password('Trademe', 'key')
        TRADEME_API_SECRET = keyring.get_password('Trademe', 'secret')
    else:
        logging.info('TradeMe credentials loaded from environment variables')
    return TRADEME_API_KEY, TRADEME_API_SECRET


def connect_to_trademe():
    TRADEME_API_KEY, TRADEME_API_SECRET = get_trademe_credentials()
    trademe = OAuth1Session(TRADEME_API_KEY, TRADEME_API_SECRET)
    return trademe


def fetch_trademe_data(trademe, url):
    start_time = time.time()
    logging.info('Starting TradeMe data fetch')
    logging.info('Fetching page 1 to determine total count')

    returned_page_all = trademe.get(url)
    logging.info(f'Page 1 fetched successfully (status: {returned_page_all.status_code})')

    data_raw = returned_page_all.content
    parsed_data = json.loads(data_raw)
    listings = parsed_data['List']
    total_count = parsed_data['TotalCount']
    total_n_requests = int(total_count/500) + 1

    logging.info(f'Total listings available: {total_count:,}')
    logging.info(f'Total pages to fetch: {total_n_requests}')
    data_df = pd.DataFrame.from_dict(listings)

    def fetch_page(i):
        page_start = time.time()
        name_num = str(i)
        page_url = f'{url}&page={name_num}&sort_order=Default HTTP/1.1'
        returned_page_all = trademe.get(page_url)
        if returned_page_all.status_code != 200:
            logging.error(f'Failed to fetch page {i}: HTTP {returned_page_all.status_code}')
            logging.error(f'Error message: {returned_page_all.text}')
            return None
        page_time = time.time() - page_start
        logging.info(f'Fetched page {i}/{total_n_requests} ({page_time:.2f}s)')
        data_raw = returned_page_all.content
        parsed_data = json.loads(data_raw)
        listings = parsed_data['List']
        return pd.DataFrame.from_dict(listings)
    if total_n_requests > 1:
        max_workers = max(1, cpu_count() * 2)
        logging.info(f'Using {max_workers} worker threads for parallel fetching')
        all_dataframes = [data_df]  # Start with first page

        fetch_start = time.time()
        with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = [executor.submit(fetch_page, i) for i in range(2, total_n_requests+1)]
            completed = 0
            failed = 0
            for future in concurrent.futures.as_completed(futures):
                result = future.result()
                if result is not None:
                    all_dataframes.append(result)
                    completed += 1
                else:
                    failed += 1

        fetch_time = time.time() - fetch_start
        logging.info(f'Parallel fetch complete: {completed} succeeded, {failed} failed ({fetch_time:.2f}s)')

        concat_start = time.time()
        logging.info(f'Concatenating {len(all_dataframes)} pages...')
        data_df = pd.concat(all_dataframes, ignore_index=True)
        concat_time = time.time() - concat_start
        logging.info(f'Concatenation complete ({concat_time:.2f}s)')

    total_time = time.time() - start_time
    logging.info(f'TradeMe data fetch complete: {len(data_df):,} listings fetched in {total_time:.2f}s')
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


def store_date(data, supabase, chunk_size=1000):
    start_time = time.time()
    logging.info('Starting data processing and storage')

    original_count = len(data)
    data = data.drop_duplicates(subset=['ListingId'])
    duplicates_removed = original_count - len(data)
    if duplicates_removed > 0:
        logging.info(f'Removed {duplicates_removed} duplicate listings')

    logging.info('Processing data fields...')
    data['ListingStatus'] = 'Listed'
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

    logging.info('Converting to records for database insert...')
    data_to_insert = data.to_dict('records')
    num_chunks = math.ceil(len(data_to_insert) / chunk_size)
    logging.info(f'Upserting {len(data_to_insert):,} listings in {num_chunks} chunks of {chunk_size}')

    successful_chunks = 0
    failed_chunks = 0
    upsert_start = time.time()

    for i in range(num_chunks):
        chunk = data_to_insert[i * chunk_size:(i + 1) * chunk_size]
        try:
            supabase.table("Listings").upsert(chunk, on_conflict='ListingId').execute()
            successful_chunks += 1
            if (i + 1) % 10 == 0 or (i + 1) == num_chunks:
                logging.info(f'Progress: {i + 1}/{num_chunks} chunks completed')
        except Exception as e:
            failed_chunks += 1
            logging.error(f"Error upserting chunk {i + 1}/{num_chunks}: {e}")
            continue

    upsert_time = time.time() - upsert_start
    total_time = time.time() - start_time
    logging.info(f'Database upsert complete: {successful_chunks} succeeded, {failed_chunks} failed ({upsert_time:.2f}s)')
    logging.info(f'Total store_date time: {total_time:.2f}s')


def reconcile_delisted_listings(data_df, supabase):
    start_time = time.time()
    logging.info('Starting reconciliation of delisted listings')

    # Fetch all listed listings using keyset (cursor) pagination on ListingId.
    # Keyset paging (WHERE ListingId > last_id ORDER BY ListingId LIMIT page_size)
    # seeks via the ListingId primary-key index and reads a fixed page each time,
    # so it runs in constant time regardless of depth. This avoids the OFFSET
    # pagination that degraded with depth and tripped Supabase's statement timeout
    # (error 57014). ListingId is unique (the upsert conflict target), so page
    # boundaries can neither skip nor duplicate rows.
    db_listings = []
    page_size = 1000
    last_id = 0  # all TradeMe ListingIds are positive integers

    logging.info('Fetching currently listed items from database (paginated)...')
    fetch_start = time.time()
    pages_fetched = 0

    while True:
        response = (supabase.table('Listings')
                    .select('ListingId')
                    .eq('ListingStatus', 'Listed')
                    .gt('ListingId', last_id)
                    .order('ListingId')
                    .limit(page_size)
                    .execute())
        if not response.data:
            break
        db_listings.extend([x['ListingId'] for x in response.data])
        last_id = response.data[-1]['ListingId']
        pages_fetched += 1
        if pages_fetched % 10 == 0:
            logging.info(f'Fetched {len(db_listings):,} listings so far ({pages_fetched} pages)...')
        if len(response.data) < page_size:
            break

    fetch_time = time.time() - fetch_start
    logging.info(f'Database fetch complete: {len(db_listings):,} listings retrieved in {pages_fetched} pages ({fetch_time:.2f}s)')

    db_listings_set = set(db_listings)
    fetched_listings_set = set(data_df['ListingId'])
    delisted_listings = list(db_listings_set - fetched_listings_set)
    logging.info(f'Identified {len(delisted_listings):,} delisted listings to update')

    if len(delisted_listings) == 0:
        logging.info('No delisted listings to update')
        return

    batch_size = 100
    total_batches = math.ceil(len(delisted_listings) / batch_size)
    successful_batches = 0
    failed_batches = 0
    update_start = time.time()

    for i in range(0, len(delisted_listings), batch_size):
        batch = delisted_listings[i:i + batch_size]
        batch_num = i // batch_size + 1
        try:
            supabase.table('Listings').update({'ListingStatus': 'Delisted'}).in_('ListingId', batch).execute()
            successful_batches += 1
            if batch_num % 10 == 0 or batch_num == total_batches:
                logging.info(f'Update progress: {batch_num}/{total_batches} batches completed')
        except Exception as e:
            failed_batches += 1
            logging.error(f'Error updating batch {batch_num}/{total_batches}: {e}')

    update_time = time.time() - update_start
    total_time = time.time() - start_time
    logging.info(f'Delisted listings update complete: {successful_batches} batches succeeded, {failed_batches} failed ({update_time:.2f}s)')
    logging.info(f'Total reconciliation time: {total_time:.2f}s')


if __name__ == '__main__':
    script_start_time = time.time()
    logging.info('=' * 80)
    logging.info('Starting NZ Housing Market Data Fetch and Store Pipeline')
    logging.info('=' * 80)

    try:
        # Connect to TradeMe
        logging.info('Connecting to TradeMe API...')
        trademe = connect_to_trademe()

        # Fetch data from TradeMe
        url = os.getenv('TRADEME_HOUSES_URL')
        logging.info(f'TradeMe URL: {url}')
        data = fetch_trademe_data(trademe, url)

        # Connect to Supabase
        logging.info('Connecting to Supabase...')
        supabase = utils.connect_to_supabase()
        logging.info('Successfully connected to Supabase')

        # Reconcile delisted listings
        reconcile_delisted_listings(data, supabase)

        # Store/update listings
        store_date(data, supabase)

        # Summary
        script_total_time = time.time() - script_start_time
        logging.info('=' * 80)
        logging.info('Pipeline Complete - Summary')
        logging.info('=' * 80)
        logging.info(f'Total listings processed: {len(data):,}')
        logging.info(f'Total execution time: {script_total_time:.2f}s ({script_total_time/60:.2f} minutes)')
        logging.info('Pipeline completed successfully!')
        logging.info('=' * 80)

    except Exception as e:
        logging.error('=' * 80)
        logging.error('Pipeline Failed with Error')
        logging.error('=' * 80)
        logging.error(f'Error type: {type(e).__name__}')
        logging.error(f'Error message: {str(e)}')
        logging.error('=' * 80)
        raise

from supabase import create_client
import os
import keyring
from dotenv import load_dotenv

try:
    load_dotenv('config.env')
except FileNotFoundError:
    print('No config file found.')


def get_supabase_credentials():
    SUPABASE_API_KEY = os.getenv('SUPABASE_API_KEY')
    SUPABASE_API_URL = os.getenv('SUPABASE_URL')
    if SUPABASE_API_KEY is None or SUPABASE_API_URL is None:
        try:
            SUPABASE_API_KEY = keyring.get_password('Supabase', 'key')
            SUPABASE_API_URL = keyring.get_password('Supabase', 'url')
        except keyring.errors.KeyringError:
            print('No keyring found.')
    return SUPABASE_API_KEY, SUPABASE_API_URL


def connect_to_supabase():
    SUPABASE_API_KEY, SUPABASE_API_URL = get_supabase_credentials()
    supabase = create_client(SUPABASE_API_URL, SUPABASE_API_KEY)
    return supabase

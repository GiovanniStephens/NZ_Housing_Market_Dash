# Housing Market Dashboard

This project develops a web-based dashboard using Plotly Dash to visualise New Zealand housing market data collected from Trademe. The dashboard provides insights into housing prices, trends, and distributions across various regions, bedrooms, and bathrooms counts.

The data are collected using the Trademe API on a daily basis and stored in Supabase, a cloud database service. The dashboard fetches the data from Supabase and displays it in a user-friendly interface. Users can interact with the dashboard to explore the data and gain valuable insights into the NZ housing market.

## Overview

The Housing Market Dashboard allows users to:
- View current market prices by region, district, and suburb.
- Analyse price distributions across different categories like bedrooms and bathrooms.

## Installation

To run this project locally, you need to have Python installed on your system. Follow these steps to set up and run the dashboard:

### Prerequisites

- Python 3.6 or higher.
- pip for installing dependencies.
- Trademe API key for fetching data (Guide can be found [here](https://developer.trademe.co.nz/)).
- [Supabase](https://supabase.com/) account for storing data.

### Clone the Repository

```bash
git clone https://github.com/GiovanniStephens/NZ_Housing_Market_Dash.git
cd NZ_Housing_Market_Dash
```

### Install Dependencies

```bash
pip install -r requirements.txt
```

### Set Environment Variables

Create a `.env` file in the root directory and add the following environment variables:

```bash
SUPABASE_URL=your_supabase_url
SUPABASE_KEY=your_supabase_key
TRADME_KEY=your_trademe_key
TRADEME_API_SECRET=your_trademe_secret
```
Note that you can use keyring to store your Trademe API key and secret securely. 

```python
>>> import keyring
>>> keyring.set_password("Trademe", "key", "your_trademe_key")
>>> keyring.set_password("Trademe", "secret", "your_trademe_secret")
```

### Configure Supabase

Create a table called 'Listings' in Supabase with the following schema:

| column_name  | data_type                   |
| ------------ | --------------------------- |
| ListingId    | bigint                      |
| Title        | text                        |
| Category     | text                        |
| StartDate    | timestamp without time zone |
| EndDate      | timestamp without time zone |
| RegionId     | integer                     |
| Region       | text                        |
| SuburbId     | bigint                      |
| Suburb       | text                        |
| PriceDisplay | text                        |
| Price        | double precision            |
| Address      | text                        |
| DistrictId   | integer                     |
| District     | text                        |
| LandArea     | bigint                      |
| Bathrooms    | real                        |
| Bedrooms     | real                        |
| Parking      | text                        |
| PropertyType | text                        |
| TotalParking | real                        |
| Amenities    | text                        |
| Latitude     | double precision            |
| Longitude    | double precision            |

### Extract and Store the Data

Run the `fetch_and_Store.py` script to fetch data from Trademe and store it in the Supabase database.

```bash
python fetch_and_store.py
```

### Run the Dashboard

```bash
python dashboard.py
```
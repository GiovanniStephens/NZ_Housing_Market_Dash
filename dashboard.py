import dash
from dash import dcc
from dash import html
import pandas as pd
import plotly.express as px
from dash.dependencies import Input, Output, State
from dotenv import load_dotenv
import utils
import os


try:
    load_dotenv()
    load_dotenv('config.env')
except FileNotFoundError:
    print('No config file found.')


def fetch_data(supabase):
    data = supabase.table("Listings").select("*").execute()
    data_df = pd.DataFrame(data.data)
    return data_df


app = dash.Dash(__name__)
server = app.server
data = fetch_data(utils.connect_to_supabase())
data['Price'] = data['Price'] / 1000000
data['StartDate'] = pd.to_datetime(data['StartDate'])
data['EndDate'] = pd.to_datetime(data['EndDate'])

# Generate options for dropdowns
regions = [{'label': region, 'value': region} for region in data['Region'].unique()]
regions.insert(0, {'label': 'All Regions', 'value': 'All Regions'})
districts = [{'label': district, 'value': district} for district in data['District'].unique()]
districts.insert(0, {'label': 'All Districts', 'value': 'All Districts'})
suburbs = [{'label': suburb, 'value': suburb} for suburb in data['Suburb'].unique()]
suburbs.insert(0, {'label': 'All Suburbs', 'value': 'All Suburbs'})
property_types = [{'label': ptype, 'value': ptype} for ptype in data['PropertyType'].unique()]
property_types.insert(0, {'label': 'All Property Types', 'value': 'All Property Types'})

# Define the layout of the app
app.layout = html.Div([
    html.Div([
        html.H2('Filters', style={'color': 'white'}),
        html.Label('Start Date Range:', style={'color': 'white'}),
        dcc.DatePickerRange(
            id='date-picker-range',
            start_date=data['LastUpdatedAt'].min(),
            end_date=data['LastUpdatedAt'].max(),
            display_format='MMM D, YYYY',
            style={'marginBottom': '20px', 'fontSize': '12px'}
        ),
        html.Br(),
        html.Label('Region', style={'color': 'white'}),
        dcc.Dropdown(id='region-dropdown', options=regions, value='All Regions', style={'marginBottom': '20px'},
                     multi=True, clearable=True, searchable=True, placeholder='Select Region'),
        html.Label('District', style={'color': 'white'}),
        dcc.Dropdown(id='district-dropdown', options=districts, value='All Districts', style={'marginBottom': '20px'},
                     multi=True, clearable=True, searchable=True, placeholder='Select District'),
        html.Label('Suburb', style={'color': 'white'}),
        dcc.Dropdown(id='suburb-dropdown', options=suburbs, value='All Suburbs', style={'marginBottom': '20px'},
                     multi=True, clearable=True, searchable=True, placeholder='Select Suburb'),
        html.Label('Price Range', style={'color': 'white'}),
        dcc.RangeSlider(id='price-slider', min=data['Price'].min(), max=data['Price'].max(),
                        step=0.1,
                        marks={price: f"${price:.0f}m" for price in range(int(data['Price'].min()),
                                                                          int(data['Price'].max()) + 1,
                                                                          1 if data['Price'].max() < 5
                                                                          else 2)},
                        value=[data['Price'].min(), data['Price'].max()]),
        html.Label('Bedrooms:', style={'color': 'white'}),
        dcc.RangeSlider(id='bedrooms-slider', min=0, max=data['Bedrooms'].max(),
                        step=1, marks={i: str(i) for i in range(int(data['Bedrooms'].max()) + 1)},
                        value=[0, data['Bedrooms'].max()]),
        html.Br(),
        html.Label('Bathrooms:', style={'color': 'white'}),
        dcc.RangeSlider(id='bathrooms-slider', min=0, max=data['Bathrooms'].max(),
                        step=1, marks={i: str(i) for i in range(int(data['Bathrooms'].max()) + 1)},
                        value=[0, data['Bathrooms'].max()]),
        html.Br(),
        html.Label('Property Type', style={'color': 'white'}),
        dcc.Dropdown(id='property-type-dropdown', options=property_types, value='All Property Types',
                     style={'marginBottom': '20px'}, multi=True),
        html.Button(id='filter-button', n_clicks=0, children='Apply Filters', style={'marginTop': '20px',
                                                                                     'margin': '5px'}),
        html.Div(id='stats-div', style={'color': 'white', 'marginTop': '20px'})
    ],  style={'width': '16%', 'float': 'left', 'backgroundColor': '#00355f', 'padding': '20px',
               'position': 'fixed', 'height': '100vh', 'overflow': 'auto'}),

    html.Div([
        dcc.Graph(id='price-distribution', style={'height': '800px'}),
        dcc.Graph(id='listings-on-map', style={'height': '800px'}),
        dcc.Graph(id='median-price-by-region', style={'height': '800px'}),
        dcc.Graph(id='median-price-by-district', style={'height': '800px'}),
        dcc.Graph(id='median-price-by-suburb', style={'height': '800px'}),
        dcc.Graph(id='median-price-over-time', style={'height': '800px'}),
        dcc.Graph(id='listing-count-over-time', style={'height': '800px'}),
        dcc.Graph(id='listings-by-property-type', style={'height': '800px'}),
        dcc.Graph(id='price-vs-land-area', style={'height': '800px'}),
        dcc.Graph(id='price-vs-bedrooms', style={'height': '800'}),
        dcc.Graph(id='price-vs-bathrooms', style={'height': '800px'}),
    ], style={'display': 'inline-block', 'width': '75%', 'padding': '20px', 'float': 'right'})
])


@app.callback(
    [Output('district-dropdown', 'options'),
     Output('suburb-dropdown', 'options'),
     Output('property-type-dropdown', 'options')],
    [Input('region-dropdown', 'value'),
     Input('district-dropdown', 'value'),
     Input('suburb-dropdown', 'value')]
)
def update_dropdowns(selected_region, selected_district, selected_suburb):
    filtered_data = data.copy()
    if selected_region == 'All Regions' or not selected_region or 'All Regions' in selected_region:
        filtered_data = data.copy()
    else:
        filtered_data = data[data['Region'].isin(selected_region)]
    districts = [{'label': 'All Districts', 'value': 'All Districts'}] + \
        [{'label': district, 'value': district} for district in filtered_data['District'].unique()]
    if selected_district == 'All Districts' or not selected_district or 'All Districts' in selected_district:
        filtered_data = filtered_data
    else:
        filtered_data = filtered_data[filtered_data['District'].isin(selected_district)]
    suburbs = [{'label': 'All Suburbs', 'value': 'All Suburbs'}] + \
        [{'label': suburb, 'value': suburb} for suburb in filtered_data['Suburb'].unique()]
    if selected_suburb == 'All Suburbs' or not selected_suburb or 'All Suburbs' in selected_suburb:
        filtered_data = filtered_data
    else:
        filtered_data = filtered_data[filtered_data['Suburb'].isin(selected_suburb)]
    property_types = [{'label': 'All Property Types', 'value': 'All Property Types'}] + \
        [{'label': ptype, 'value': ptype} for ptype in filtered_data['PropertyType'].unique()]
    return districts, suburbs, property_types


# Callback to update the graphs based on filters
@app.callback(
    [
     Output('price-distribution', 'figure'),
     Output('listings-on-map', 'figure'),
     Output('median-price-by-region', 'figure'),
     Output('median-price-by-district', 'figure'),
     Output('median-price-by-suburb', 'figure'),
     Output('median-price-over-time', 'figure'),
     Output('listing-count-over-time', 'figure'),
     Output('listings-by-property-type', 'figure'),
     Output('price-vs-land-area', 'figure'),
     Output('price-vs-bedrooms', 'figure'),
     Output('price-vs-bathrooms', 'figure'),
     Output('stats-div', 'children')
    ],
    [Input('filter-button', 'n_clicks')],
    [
        Input('median-price-by-region', 'clickData'),
        Input('median-price-by-district', 'clickData'),
        Input('median-price-by-suburb', 'clickData'),
    ],
    [State('date-picker-range', 'start_date'),
     State('date-picker-range', 'end_date'),
     State('region-dropdown', 'value'),
     State('district-dropdown', 'value'),
     State('suburb-dropdown', 'value'),
     State('price-slider', 'value'),
     State('bedrooms-slider', 'value'),
     State('bathrooms-slider', 'value'),
     State('property-type-dropdown', 'value')]
)
def update_graphs(n_clicks, region_click, district_click, suburb_click,
                  start_date, end_date,
                  region, district, suburb, price_range,
                  bedroom_range, bathroom_range, property_type):
    ctx = dash.callback_context
    if not ctx.triggered or ctx.triggered[0]['prop_id'] == 'filter-button.n_clicks':
        filtered_data = filtered_data = data[(data['EndDate'] >= start_date)]
        filtered_data_with_nulls = data
    else:
        trigger_id = ctx.triggered[0]['prop_id'].split('.')[0]
        category_value = ctx.triggered[0]['value']['points'][0]['x']
        if trigger_id in ['median-price-by-region', 'median-price-by-district', 'median-price-by-suburb']:
            filtered_data = data[data[trigger_id.split('-')[3].title()] == category_value]
        filtered_data = filtered_data = filtered_data[(filtered_data['EndDate'] >= start_date)]
        filtered_data_with_nulls = filtered_data

    if region != 'All Regions' and region and 'All Regions' not in region:
        filtered_data = filtered_data[filtered_data['Region'].isin(region)]
        filtered_data_with_nulls = filtered_data_with_nulls[(filtered_data_with_nulls['Region'].isin(region)) |
                                                            (filtered_data_with_nulls['Region'].isnull())]
    if district != 'All Districts' and district and 'All Districts' not in district:
        filtered_data = filtered_data[filtered_data['District'].isin(district)]
        filtered_data_with_nulls = filtered_data_with_nulls[(filtered_data_with_nulls['District'].isin(district)) |
                                                            (filtered_data_with_nulls['District'].isnull())]
    if suburb != 'All Suburbs' and suburb and 'All Suburbs' not in suburb:
        filtered_data = filtered_data[filtered_data['Suburb'].isin(suburb)]
        filtered_data_with_nulls = filtered_data_with_nulls[(filtered_data_with_nulls['Suburb'].isin(suburb)) |
                                                            (filtered_data_with_nulls['Suburb'].isnull())]
    filtered_data = filtered_data[(filtered_data['LastUpdatedAt'] >= start_date)
                                  & (filtered_data['LastUpdatedAt'] <= end_date)]
    filtered_data = filtered_data[(filtered_data['Price'] >= price_range[0])
                                  & (filtered_data['Price'] <= price_range[1])]
    filtered_data_with_nulls = filtered_data_with_nulls[((filtered_data_with_nulls['Price'] >= price_range[0])
                                                        & (filtered_data_with_nulls['Price'] <= price_range[1])) |
                                                        (filtered_data_with_nulls['Price'].isnull())]
    filtered_data = filtered_data[(filtered_data['Bedrooms'] >= bedroom_range[0])
                                  & (filtered_data['Bedrooms'] <= bedroom_range[1])]
    filtered_data_with_nulls = filtered_data_with_nulls[((filtered_data_with_nulls['Bedrooms'] >= bedroom_range[0])
                                                        & (filtered_data_with_nulls['Bedrooms'] <= bedroom_range[1])) |
                                                        (filtered_data_with_nulls['Bedrooms'].isnull())]
    filtered_data = filtered_data[(filtered_data['Bathrooms'] >= bathroom_range[0])
                                  & (filtered_data['Bathrooms'] <= bathroom_range[1])]
    filtered_data_with_nulls = filtered_data_with_nulls[((filtered_data_with_nulls['Bathrooms'] >= bathroom_range[0])
                                                        & (filtered_data_with_nulls['Bathrooms'] <= bathroom_range[1]))
                                                        | (filtered_data_with_nulls['Bathrooms'].isnull())]
    if property_type != 'All Property Types' and property_type:
        filtered_data = filtered_data[filtered_data['PropertyType'].isin(property_type)]
        filtered_data_with_nulls = filtered_data_with_nulls[(filtered_data_with_nulls['PropertyType']
                                                             .isin(property_type))
                                                            | (filtered_data_with_nulls['PropertyType'].isnull())]

    # Median Price by Region
    median_price_region = filtered_data.groupby('Region')['Price'].median().reset_index()
    median_price_region_sorted = median_price_region.sort_values(by='Price', ascending=False)
    fig_region = px.bar(
        median_price_region_sorted,
        x='Region',
        y='Price',
        labels={"Price": "Median Price (millions)"},
        title='Median Price by Region'
    )

    # Median Price by District
    median_price_district = filtered_data.groupby('District')['Price'].median().reset_index()
    median_price_district_sorted = median_price_district.sort_values(by='Price', ascending=False)
    fig_district = px.bar(
        median_price_district_sorted,
        x='District',
        y='Price',
        labels={"Price": "Median Price (millions)"},
        title='Median Price by District'
    )

    fig_histogram = px.histogram(filtered_data, x='Price', title='Price Distribution')
    median_price_suburb = filtered_data.groupby('Suburb')['Price'].median().reset_index()
    median_price_suburb_sorted = median_price_suburb.sort_values(by='Price', ascending=False)
    fig_median_price_suburb = px.bar(
        median_price_suburb_sorted,
        x='Suburb',
        y='Price',
        labels={"Price": "Median Price (millions)"},
        title='Median Price by Suburb',
    )
    fig_median_price_suburb.update_layout(xaxis_tickangle=-90)
    filtered_data['LastUpdatedAt'] = pd.to_datetime(filtered_data['LastUpdatedAt'])
    n_days = (filtered_data['LastUpdatedAt'].max() - filtered_data['LastUpdatedAt'].min()).days
    filtered_data.set_index('LastUpdatedAt', inplace=True)
    if n_days < 10:
        # Just show one boxplot for the median price, but make it overall... no x split
        fig_median_price_time = px.box(
            filtered_data,
            y='Price',
            title='Median Price Overall',
            labels={"Price": "Price (millions)"}
        )
    else:
        date_range = pd.date_range(start=data['LastUpdatedAt'].min(), end=data['LastUpdatedAt'].max(), freq='D')
        rolling_median = [calculate_median_price(filtered_data, date) for date in date_range]
        fig_median_price_time = px.line(
            rolling_median,
            x=date_range,
            y=rolling_median,
            labels={"y": "Median Price (millions)", "x": "Date"},
            title='Median Price by Date'
        )
    fig_map = px.scatter_mapbox(filtered_data, lat='Latitude', lon='Longitude', size='Price', zoom=4, height=300,
                                title='Listings on Map',
                                hover_data={
                                    'Title': True,
                                    'Price': ':.2f',
                                    'Region': True,
                                    'District': True,
                                    'Suburb': True,
                                    'Area': True,
                                    'LandArea': True,
                                    'Bedrooms': True,
                                    'Bathrooms': True,
                                    'PropertyType': True,
                                    'StartDate': True,

                                })
    fig_map.update_layout(mapbox_style='open-street-map', title='Listings on Map', height=800)
    fig_bar = px.bar(filtered_data['PropertyType'].value_counts().reset_index(),
                     x='index', y='PropertyType', title='Number of Listings by Property Type')
    fig_scatter = px.scatter(filtered_data, x='Area', y='Price', title='Price vs. Floor Area')
    fig_price_bedrooms = create_price_bedrooms_boxplot(filtered_data)
    fig_price_bathrooms = create_price_bathrooms_boxplot(filtered_data)

    count = len(filtered_data_with_nulls)
    median_price = filtered_data['Price'].median() if count > 0 else 0
    stats_text = [
        html.Div(f"Count: {count}", style={'marginBottom': '10px'}),
        html.Div(f"Median Price: ${median_price:.2f}m")
    ]
    date_range = pd.date_range(start=data['LastUpdatedAt'].min(), end=data['LastUpdatedAt'].max(), freq='D')
    listing_count_by_date = [get_listing_count(filtered_data_with_nulls, date) for date in date_range]
    fig_listing_count_over_time = px.line(
        x=date_range,
        y=listing_count_by_date,
        title='Listing Count Over Time',
        labels={"y": "Number of Listings", "x": "Date"}
    )
    print(filtered_data_with_nulls['Title'].values)
    return (fig_histogram, fig_map, fig_region, fig_district, fig_median_price_suburb,
            fig_median_price_time, fig_listing_count_over_time, fig_bar, fig_scatter, fig_price_bedrooms,
            fig_price_bathrooms, stats_text)


def create_price_bedrooms_boxplot(filtered_data):
    fig_price_bedrooms = px.box(
        filtered_data,
        x='Bedrooms',
        y='Price',
        labels={"Price": "Price (millions)", "Bedrooms": "Bedrooms"},
        title='Price Distribution vs. Bedrooms',
        notched=True,  # shows the confidence interval around the median
        points="all",   # show all points
        height=800
    )
    fig_price_bedrooms.update_layout(
        yaxis_title='Price (millions)',
        xaxis_title='Bedrooms',
        xaxis_type='linear'  # Treats the bedroom numbers as categorical
    )
    return fig_price_bedrooms


def create_price_bathrooms_boxplot(filtered_data):
    fig_price_bathrooms = px.box(
        filtered_data,
        x='Bathrooms',
        y='Price',
        labels={"Price": "Price (millions)", "Bathrooms": "Bathrooms"},
        title='Price Distribution vs. Bathrooms',
        notched=True,  # shows the confidence interval around the median
        points="all",   # show all points
        height=800
    )
    fig_price_bathrooms.update_layout(
        yaxis_title='Price (millions)',
        xaxis_title='Bathrooms',
        xaxis_type='linear'  # Treats the bathroom numbers as categorical
    )
    return fig_price_bathrooms


def calculate_median_price(filtered_data, date):
    active_listings = filtered_data[(filtered_data['StartDate'] <= date) & (filtered_data['EndDate'] >= date)]
    return active_listings['Price'].median()


def get_listing_count(filtered_data, date):
    return len(filtered_data[(filtered_data['StartDate'] <= date) & (filtered_data['EndDate'] >= date)])


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 10000))  # Default to 10000 if PORT not set
    app.run_server(host='0.0.0.0', port=port, debug=True)

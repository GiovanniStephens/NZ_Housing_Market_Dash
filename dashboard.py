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
        dcc.RangeSlider(id='price-slider', min=data['Price'].min(), max=data['Price'].max(), step=0.1 if data['Price'].max() < 5 else 0.5,
                        marks={price: f"${price:.1f}m" for price in range(int(data['Price'].min()),
                                                                          int(data['Price'].max()) + 1,
                                                                          1 if data['Price'].max() < 5
                                                                          else 5)},
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
        html.Button(id='filter-button', n_clicks=0, children='Apply Filters'),
        html.Div(id='stats-div', style={'color': 'white', 'marginTop': '20px'})
    ],  style={'width': '20%', 'float': 'left', 'backgroundColor': '#00355f', 'padding': '20px',
               'position': 'fixed', 'height': '100vh', 'overflow': 'auto'}),

    html.Div([
        dcc.Graph(id='price-distribution', style={'height': '800px'}),
        dcc.Graph(id='listings-on-map', style={'height': '800px'}),
        dcc.Graph(id='listings-by-property-type', style={'height': '800px'}),
        dcc.Graph(id='price-vs-land-area', style={'height': '800px'})
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
    [Output('price-distribution', 'figure'),
     Output('listings-on-map', 'figure'),
     Output('listings-by-property-type', 'figure'),
     Output('price-vs-land-area', 'figure'),
     Output('stats-div', 'children')],
    [Input('filter-button', 'n_clicks')],
    [State('region-dropdown', 'value'),
     State('district-dropdown', 'value'),
     State('suburb-dropdown', 'value'),
     State('price-slider', 'value'),
     State('bedrooms-slider', 'value'),
     State('bathrooms-slider', 'value'),
     State('property-type-dropdown', 'value')]
)
def update_graphs(n_clicks, region, district, suburb, price_range, bedroom_range, bathroom_range, property_type):
    filtered_data = data
    filtered_data_with_nulls = data
    print(region)
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
        filtered_data_with_nulls = filtered_data_with_nulls[(filtered_data_with_nulls['PropertyType'].isin(property_type))
                                                            | (filtered_data_with_nulls['PropertyType'].isnull())]

    fig_histogram = px.histogram(filtered_data, x='Price', title='Price Distribution')
    fig_map = px.scatter_mapbox(filtered_data, lat='Latitude', lon='Longitude', size='Price', zoom=10, height=300)
    fig_map.update_layout(mapbox_style='open-street-map', title='Listings on Map', height=800)
    fig_bar = px.bar(filtered_data['PropertyType'].value_counts().reset_index(),
                     x='index', y='PropertyType', title='Number of Listings by Property Type')
    fig_scatter = px.scatter(filtered_data, x='LandArea', y='Price', title='Price vs. Land Area')
    # Get filtered data but with the null prices

    count = len(filtered_data_with_nulls)
    median_price = filtered_data['Price'].median() if count > 0 else 0
    stats_text = [
        html.Div(f"Count: {count}", style={'marginBottom': '10px'}),
        html.Div(f"Median Price: ${median_price:.2f}m")
    ]
    return fig_histogram, fig_map, fig_bar, fig_scatter, stats_text


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 10000))  # Default to 10000 if PORT not set
    app.run_server(host='0.0.0.0', port=port, debug=True)

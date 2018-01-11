import datetime as dt
import os
import pandas as pd
import numpy as np
from scipy import interpolate
from matplotlib import mlab
from pyvirtualdisplay import Display
from selenium import webdriver
import bs4

from timeout import timeout

  
class DECStation:
    def __init__(self, number, name, lon, lat):
        self.number = number
        self.name = name
        self.lon = lon
        self.lat = lat

    def get_station_url(self):
        """ Get url for a particular station"""
        url =  'http://www.nyaqinow.net/StationReportFast.aspx?&ST_ID=%s' %self.number

        return url


def get_stations():
    """Get the stations"""
    all_stations = {

        #DEC group 1
        #Long Island
        'Babylon': DECStation(46, 'Babylon', -73.41919, 40.74529),
        'Eisenhower Park': DECStation(53, 'Eisenhower Park', -73.58549, 40.74316),
        'Suffolk County': DECStation(36, 'Suffolk County', -73.05754, 40.82799),

        #DEC group 2
        #Manhattan
        'CCNY': DECStation(73, 'CCNY', -73.94825, 40.81976),
        'IS 143': DECStation(56, 'IS 143', -73.93059, 40.84888),
        'PS 19': DECStation(75, 'PS 19', -73.98446, 40.73000),
        'Division Street': DECStation(60, 'Division Street', -73.99518, 40.71436),

        #Staten Island
        'Fresh Kills West': DECStation(61, 'Fresh Kills West', -74.19832, 40.58027),
        'Port Richmond': DECStation(80, 'Port Richmond', -74.13719, 40.63307),
        'Susan Wagner': DECStation(49, 'Susan Wagner', -74.12525, 40.59664),

        #Bronx
        'IS 52': DECStation(24, 'IS 52', -73.9020, 40.8162),
        'IS 74': DECStation(8, 'IS 74', -73.88553, 40.81551),
        'NYBG': DECStation(57, 'NYBG', -73.87809, 40.86790),

        #Queens
        'Maspeth': DECStation(13, 'Maspeth', -73.89313, 40.72698),
        'Queens College': DECStation(62, 'Queens College', -73.82153, 40.73614),

        #Brooklyn
        'PS 274': DECStation(6, 'PS 274', -73.92769, 40.69454),
        'PS 314': DECStation(10, 'PS 314', -74.01871, 40.64182),

        #DEC group 3
        #North
        'White Plains': DECStation(34, 'White Plains', -73.76366, 41.05192),
        'Millbrook': DECStation(25, 'Millbrook', -73.74136, 41.78555)

    }

    return all_stations

        
def parse_date(x):
    try: 
        return parser.parse(x)
    except:
        return None
        
def parse_to_float(x):
    try: 
        return float(x)
    except:
        return np.nan
                
def get_station_raw_data(stations, start_date, end_date):
    """
    Download the station data from airnow website
    """

    # Defaults
    website_cols = ['Date Time', 'O3', 'PM25C', 'SO2', 'CO']    
    polished_names = ['Date Time', 'Date', 'Time', 'station', 'lon', 'lat', 'PM25', 'O3', 'SO2', 'CO']

    # Load into one dataframe
    all_data = pd.DataFrame()
    
    # Start up a virtual display
    display = Display(visible=0, size=(800, 600))
    display.start()
               
    driver = webdriver.Chrome()

    for name, station in stations.iteritems():

        # Navigate to the webpage
        # url = station.get_station_url(start_date, end_date)
        url = 'http://www.nyaqinow.net/StationReportFast.aspx?ST_ID=46'
        
        driver.get(url)
        # driver.find_element_by_id('RadioButtonList1_3').click() # Excel file option
        driver.find_element_by_id('btnGenerateReport').click()

        # Scrape the content
        content = driver.page_source

        soup = bs4.BeautifulSoup(content)
        table = soup.find(attrs={'id': 'C1WebGrid1'})        
        
        df = pd.read_html(str(table), header=0)[0]
        
        # Keep columns and parse
        cols_keep = list(set(df.columns).intersection(set(website_cols)))
        df = df[cols_keep]
                                
        df['Date Time'] = df['Date Time'].map(parse_date)
        col_nulls = {}
        for col in df.columns:
            if col != 'Date Time':
                df[col] = df[col].map(parse_to_float)
                col_nulls[col] = pd.isnull(df[col])
                
        df_nulls = pd.DataFrame(col_nulls)
        all_nulls = df_nulls.apply(min, axis = 1)
        
        # Filter out bad dates and NaNs
        df_filtered = df[-(all_nulls | pd.isnull(df['Date Time']))]
            
        # Add missing columns
        cols_add = set(website_cols) - set(df_filtered.columns)
        for col in cols_add:
            df_filtered[col] = np.nan
            
        df_filtered['Date'] = df_filtered['Date Time'].map(dt.datetime.date)
        df_filtered['Time'] = df_filtered['Date Time'].map(lambda x: dt.datetime.strftime(x, '%H:%M'))
        
        df_filtered['station'] = name
        df_filtered['lon'] = station.lon
        df_filtered['lat'] = station.lat
        
        df_filtered.rename({'PM25C': 'PM25', 'Date Time', 'DateTime'}, inplace = True)
        
        all_data = all_data.append(df_filtered, ignore_index=True)

    display.stop()

    return all_data


def calculate_stations_aqi_data(station_data, breakpoints, aq_variables):
    """
    24 hours for PM2.5, 1 hours for O3
    """

    station_grouped = station_data.groupby(['station', 'lon', 'lat'])

    stations_PM25_24hr = station_grouped.agg({'PM25':
        lambda x: np.mean(x.tail(1))})
    stations_O3_1hr = station_grouped.agg({'O3':
        lambda x: np.mean(x.tail(1)) * 1000})  # x 1000 to get to ppb
    stations_O3_8hr = station_grouped.agg({'O3':
        lambda x: np.mean(x.tail(8)) * 1000})  # x 1000 to get to ppb

    stations_PM25_24hr.columns = ['PM25_24hr']
    stations_O3_1hr.columns = ['O3_1hr']
    stations_O3_8hr.columns = ['O3_8hr']

    stations_out = stations_PM25_24hr.join(stations_O3_1hr).join(stations_O3_8hr)

    stations_out['AQI'] = stations_out.apply(lambda x: calculate_aqi(x, breakpoints),
                                             axis=1)

    stations_out.reset_index(level=[0,1,2], inplace=True)
    stations_out = stations_out[['station', 'lon', 'lat', 'PM25_24hr', 'O3_8hr', 'AQI']]
    stations_out.columns = ['station', 'lon', 'lat', 'PM25', 'O3', 'AQI']

    stations_out = pd.melt(stations_out,
                           id_vars=['station', 'lon', 'lat'], value_vars=aq_variables)
    stations_out = stations_out.dropna()

    return stations_out


def calculate_aqi(station_obs, breakpoints):
    """
    Given a station's cross-sectional data, calculate AQI
    """

    aqi = 0
    for name, value in station_obs.iteritems():
        aqi = max(aqi, calculate_score(value, breakpoints, name))

    return aqi


def calculate_score(value, breakpoints, name):
    """
    Return the score for a scale
    """

    if np.isnan(value):
        return 0
    if value < 0:
        value = 0

    ndx = breakpoints[breakpoints[name] > value].index[0]

    if ndx == 0:
        return 0

    index_l = breakpoints.ix[ndx - 1, 'Index']
    index_h = breakpoints.ix[ndx, 'Index']
    conc_l = breakpoints.ix[ndx - 1, name]
    conc_h = breakpoints.ix[ndx, name]

    out = (float(index_h - index_l) / float(conc_h - conc_l)) * \
          float(value - conc_l) + index_l

    return 0 if np.isnan(out) else out


def get_interpolated_grid_data(station_data, aq_variables, data_dir = '/app/static/'):
    """
    Given a melted dataframe of cross-sectional station data
    (pertaining to one time stamp), output the corresponding grid data
    """

    locs_file = os.path.join(data_dir, 'grid_locs.csv')
    locs = pd.read_csv(locs_file)

    lon_locs = np.unique(locs['c_lon'].values)
    lat_locs = np.unique(locs['c_lat'].values)

    locs_data = locs[['gr_id']]

    # For each air quality variable, interpolate across the grid given available stations
    for aq_v in aq_variables:

        station_data_aqv = station_data[station_data['variable'] == aq_v]

        #
        # Find nearest station
        #

        nearest_station = interpolate.griddata((station_data_aqv['lon'].values, station_data_aqv['lat'].values),
                                               station_data_aqv['station'].values,
                                               (locs['c_lon'].values, locs['c_lat'].values), method='nearest')

        nearest_station_df = pd.DataFrame({'gr_id': locs['gr_id'].values,
                                           'station': nearest_station,
                                           'c_lon': locs['c_lon'].values, 'c_lat': locs['c_lat'].values})

        nearest_station_df = pd.merge(nearest_station_df, station_data_aqv, on='station')

        #
        # Interpolate using Delaunay triangulation, filling the holes with nearest neighbor
        #

        # lon x lat - melted lons change first
        aq_v_interpolated = mlab.griddata(station_data_aqv['lat'].values, station_data_aqv['lon'].values,
                                          station_data_aqv['value'].values, lat_locs, lon_locs, interp='nn')

        # Out of area locations
        out_of_area_locs = pd.melt(pd.DataFrame(aq_v_interpolated.mask))
        out_of_area_locs = locs_data['gr_id'][out_of_area_locs['value']].values

        aq_v_data = aq_v_interpolated.data

        # For grid points that are out of range of triangulation, use closest station
        for ooa_loc in out_of_area_locs:
            near_station_dat = nearest_station_df[nearest_station_df['gr_id'] == ooa_loc]

            xx = lon_locs.searchsorted(near_station_dat['c_lon'])
            yy = lat_locs.searchsorted(near_station_dat['c_lat'])

            aq_v_data[xx, yy] = near_station_dat['value']

        new_col = pd.melt(pd.DataFrame(aq_v_data))

        locs_data[aq_v] = new_col['value']

    return locs_data


def predict_stations_data(stations_dat, forecast_periods):
    """
    Predict the stations data into the future
    """
    last_time = stations_dat['DateTime'].max()
    stations_grouped = stations_dat.groupby(['station', 'lat', 'lon'])

    all_forecasts = pd.DataFrame()

    for fp in range(1, forecast_periods + 1):
        station_preds = stations_grouped.apply(predict_station).reset_index(drop=True)
        station_preds['DateTime'] = last_time + dt.timedelta(hours=fp)

        all_forecasts = all_forecasts.append(station_preds)

    return all_forecasts


def predict_station(var_series):
    """
    Predict the next in the time series
    """
    last_value = var_series[-1:]

    return last_value


def get_breakpoints(data_dir = '/app/static'):
    breaks_file = os.path.join(data_dir, 'breakpoints.csv')
    breakpoints = pd.read_csv(breaks_file)

    return breakpoints


@timeout(90)
def main():
    """
    Main function: times out after 90 seconds
    """
    print('Begin main')

    aq_variables = ['PM25', 'O3', 'AQI']
    hist_periods = 5
    forecast_periods = 7

    all_stations = get_stations()
    breakpoints = get_breakpoints()

    #Dates for current period
    end_date = dt.date.today()
    start_date = end_date - dt.timedelta(1)

    print('Get station data')

    station_data_raw = get_station_raw_data(all_stations, start_date, end_date)

    print('Finished getting station data')

    stations_ffilled = station_data_raw.groupby('station').fillna(method='ffill')
    stations_ffilled['station'] = station_data_raw['station']

    stations_predictions = predict_stations_data(stations_ffilled, forecast_periods)

    all_station_data = stations_ffilled.append(stations_predictions)

    time_stamps = all_station_data['DateTime'].unique()[
                    -(hist_periods+forecast_periods):]

    all_grid_data = pd.DataFrame()

    print('Calculating AQI and Interpolating over grid')
    for ts in time_stamps:
        station_time = all_station_data[all_station_data['DateTime'] <= ts]

        # Current station data
        stations_output = calculate_stations_aqi_data(station_time, breakpoints, aq_variables)

        # Interpolate the grid data
        current_grid_data = get_interpolated_grid_data(stations_output, aq_variables)

        current_grid_data['time'] = ts
        all_grid_data = all_grid_data.append(current_grid_data)

    print('Finished main')

    return all_grid_data

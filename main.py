__author__ = 'pwmiller'

import datetime as dt
import urllib
import requests

import pandas as pd
import numpy as np
from scipy import interpolate
from matplotlib import mlab

from StringIO import StringIO
import csv

from timeout import timeout


DataDir = '/app/static'
#DataDir = 'static'   # TODO: remove this


#TODO: sanity checks, Port Richmond < 0


class DECStation:
    def __init__(self, number, name, lon, lat):
        self.number = number
        self.name = name
        self.lon = lon
        self.lat = lat

        #self.channels = channels
        #self.url = self.set_station_url()

    def get_station_url(self, start_date, end_date):
        """ Get url for a particular station"""
        base_url = get_DEC_url_components(start_date, end_date)

        #channel_param = ''.join(['channel' + str(n) + '=on&' for n in self.channels])
        channel_param = ''.join(['channel' + str(n) + '=on&' for n in range(1, 20)])

        station_params = 'stationNo=' + str(self.number)

        return base_url + '&' + channel_param + station_params


def get_DEC_url_components(start_date, end_date):
    """Create the base URL"""

    web_url = 'http://www.dec.ny.gov/airmon/retrieveResults.php?'

    date_param = 'startDate=' + \
        urllib.quote_plus(dt.date.strftime(start_date, '%d/%m/%Y')) + \
        '&outputStartDate=' + \
        urllib.quote_plus(dt.date.strftime(start_date, '%B %d, %Y')) + \
        '&endDate=' + \
        urllib.quote_plus(dt.date.strftime(end_date, '%d/%m/%Y')) + \
        '&outputEndDate=' + \
        urllib.quote_plus(dt.date.strftime(end_date, '%B %d, %Y'))

    other_params = '&timebase=60&direction=back&reports=CSV' \
                   '&submitButton=Create+Report&numOfChannels=20'

    base_url = web_url + date_param + other_params

    return base_url


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


def get_station_raw_data(stations, start_date, end_date):
    """
    Download the station data from airnow website
    """

    # Defaults
    df_cols = ['Date(YYYY-MM-DD)', 'Time (HH24:MI)', 'station', 'lon', 'lat',
               'PM25C ug/m3LC', 'O3 ppm', 'SO2 ppb', 'CO ppm']
    aq_cols = ['PM25C ug/m3LC', 'O3 ppm', 'SO2 ppb', 'CO ppm']

    col_names = ['Date', 'Time', 'station', 'lon', 'lat', 'PM25', 'O3', 'SO2', 'CO']

    # Load into one dataframe
    aq_stations = {'PM25C ug/m3LC': [], 'O3 ppm': [], 'SO2 ppb': [], 'CO ppm': []}
    all_data = pd.DataFrame()

    session = requests.session()

    for name, station in stations.iteritems():

        url = station.get_station_url(start_date, end_date)

        response = session.get(url, allow_redirects=True)

        if response.status_code != 200:
            #TODO: Throw error
            pass

        response_str = response.content

        station_aqcols = [ccc for ccc in aq_cols if response_str.find(ccc) > -1]

        if not station_aqcols:
            #If we couldn't find any columns, go to the next station
            continue

        # For each column found add it to the list of viable stations
        for aq_col in aq_stations.keys():
            if aq_col in station_aqcols:
                aq_stations[aq_col].append(name)

        # Bring the data into a dataframe
        dict_reader = csv.DictReader(StringIO(response_str))
        csv_list = [rrr for rrr in dict_reader]

        df = pd.DataFrame(csv_list)

        # Fill missing columns
        cols_add = set(df_cols) - set(df.columns)
        for ccc in cols_add:
            df[ccc] = np.nan

        df['station'] = name
        df['lon'] = station.lon
        df['lat'] = station.lat

        df = df.reindex(columns=df_cols)
        df.columns = col_names

        all_data = all_data.append(df, ignore_index=True)

    session.close()

    all_data = all_data.reindex(columns=col_names)
    all_data['DateTime'] = (all_data['Date'] + ' ' + all_data['Time']).apply(
        lambda x: dt.datetime.strptime(x, "%Y-%m-%d %H:%M"))
    all_data = all_data.drop(['Date', 'Time'], 1)

    all_data[['PM25', 'O3', 'SO2', 'CO']] = all_data[['PM25', 'O3', 'SO2', 'CO']].\
        convert_objects(convert_numeric=True)

    return all_data, aq_stations


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


def get_interpolated_grid_data(station_data, aq_variables):
    """
    Given a melted dataframe of cross-sectional station data
    (pertaining to one time stamp), output the corresponding grid data
    """

    locs_file = DataDir + '/grid_locs.csv'
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
    #TODO: currently random, make meaningful

    last_value = var_series[-1:]

    #last_value['AQI'] += np.random.uniform(-1, 1) * (last_value['AQI'] / 10)
    last_value['PM25'] += np.random.uniform(-1, 1) * (last_value['PM25'] / 10)
    last_value['O3'] += np.random.uniform(-1, 1) * (last_value['O3'] / 10)

    return last_value


def get_breakpoints():
    breaks_file = DataDir + '/breakpoints.csv'
    breakpoints = pd.read_csv(breaks_file)

    return breakpoints


@timeout(90)
def main():
    """
    Main function: times out after 60 seconds
    """
    print 'Begin main'

    aq_variables = ['PM25', 'O3', 'AQI']
    hist_periods = 5
    forecast_periods = 7

    all_stations = get_stations()
    breakpoints = get_breakpoints()

    #Dates for current period
    end_date = dt.date.today()
    start_date = end_date - dt.timedelta(1)

    print 'Get station data'

    station_data_raw, aq_stations = get_station_raw_data(all_stations, start_date,
                                                         end_date)

    print 'Finished getting station data'

    stations_ffilled = station_data_raw.groupby('station').fillna(method='ffill')
    stations_ffilled['station'] = station_data_raw['station']

    stations_predictions = predict_stations_data(stations_ffilled, forecast_periods)

    all_station_data = stations_ffilled.append(stations_predictions)

    time_stamps = all_station_data['DateTime'].unique()[
                    -(hist_periods+forecast_periods):]

    all_grid_data = pd.DataFrame()

    print 'Calculating AQI and Interpolating over grid'
    for ts in time_stamps:
        station_time = all_station_data[all_station_data['DateTime'] <= ts]

        # Current station data
        stations_output = calculate_stations_aqi_data(station_time,
                                                      breakpoints, aq_variables)

        # Interpolate the grid data
        current_grid_data = get_interpolated_grid_data(stations_output,
                                                       aq_variables)

        current_grid_data['time'] = ts
        all_grid_data = all_grid_data.append(current_grid_data)

    print 'Finished main'

    return all_grid_data




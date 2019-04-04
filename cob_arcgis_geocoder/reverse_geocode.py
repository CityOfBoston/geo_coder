import os
import sys
import pandas as pd
from json import loads
from urllib.parse import urlencode
from urllib.request import urlopen
from pandas.io.json import json_normalize


class CobArcGISReverseGeocoder(object):

    def __init__(self, df, x, y, input_coord_system, output_coord_system, return_intersection):
        self.df = df
        self.x = x
        self.y = y
        self.input_coord_system = input_coord_system  
        self.output_coord_system = output_coord_system
        self.return_intersection = return_intersection



    def reverse_geocode_df(self):


        #geocoded address columns
        df = pd.concat([self.df,pd.DataFrame(columns=['Street', 'City', 'Zip', 'Address', 'matched_x_coord', 'matched_y_coord', 'output_coord_system', 'locator_name'])])

        for index, row in df.iterrows():

            #If either of the coordinates do not exist, set a message to the Address field that is unable to find an address.
            #If both coordinates are present, reverse geocode those coordinates and set them to the dataframe object. 
            if row[self.x] is None or row[self.y] is None:
                df.at[index, 'Address'] = "Insufficient coordinates given.  Unable to find an address."
            else:
                #fetch the results from the API
                apicall_results = self._reverse_geocode(row[self.x], row[self.y], row[self.input_coord_system],
                 row[self.output_coord_system], row[self.return_intersection])
                #clean those results up, clean columns up
                address_df = self._parse_address_results(apicall_results)

                if address_df is not None:
                    df.at[index, "Street"] = address_df[["Street"]][0]
                    df.at[index, "City"] = address_df[["City"]][0]
                    df.at[index, "Address"] = address_df[["Match_addr"]][0]
                    df.at[index, "Zip"] = address_df[["ZIP"]][0]
                    df.at[index, "matched_x_coord"] = address_df[["x"]][0]
                    df.at[index, "matched_y_coord"] = address_df[["y"]][0]
                    df.at[index, "output_coord_system"] = address_df[["output_coord_system_field"]][0]
                    df.at[index, "locator_name"] = address_df[["Loc_name"]][0]
                else:
                    #If the results are an empty set, set Address to None
                    #Also set x and y to 0.0
                    df.at[index, "Address"] = None
                    df.at[index, 'matched_x_coord'] = 0.0
                    df.at[index, 'matched_y_coord'] = 0.0
            return df






    @classmethod
    #input the coordinate system, defaulted
    def _reverse_geocode(self, x_coord, y_coord, input_coord_system="4326", output_coord_system="4326", return_intersection=False, distance=100, outputType="pjson"):
        """
        Returns a JSON object of the closest address that is closest to the point given and the 

        Args: 
        x (float): the x value in a coordinate pair to be reverse geocoded.
        y (float): the y value in a coordinate pair to be reverse geocoded.
        input_coord_system (str, optional): the spatial reference coordinate system that will be queried.
        Defaults to WGS84 coordinate system.
        output_coord_system (str, optional): spatial reference coordinate for which the returned address will be returned with.
        Defaults to WGS84 coordinate system.
        return_intersection (Boolean, optional): specifies geocoder to return closest intersection. Default is False.
        See https://developers.arcgis.com/rest/geocode/api-reference/geocoding-reverse-geocode.htm
        Distance: (Int, optional) - distnace with which the geocoder will search for an address. defaulted to 100 meters.
        outputType: (str, optional) response format.  Default type is pretty print json.
        
        E.G.
        https://awsgeo.boston.gov/arcgis/rest/services/Locators/Boston_Composite_Prod/GeocodeServer/reverseGeocode?location={"x": -71.053068420958226,"y":42.365768305949707, "spatialReference":{"wkid":4326}}&outSR=4326&distance=100&langCode=&outSR=4326&returnIntersection=false&f=json
        https://awsgeo.boston.gov/arcgis/rest/services/Locators/Boston_Composite_Prod/GeocodeServer/reverseGeocode?location={"x": 776969.460426,"y":2958642.02359, "spatialReference":{"wkid":3249}}&outSR=4326&distance=100&langCode=&outSR=4326&returnIntersection=false&f=json
        102686 - 3249
        http://awsgeo.boston.gov/arcgis/rest/services/Locators/Boston_Composite_Prod/GeocodeServer/reverseGeocode?f=pjson&location={ "x": -71.057128, "y": 42.360032, "spatialReference": { "wkid": 4326}}&outSR=4326
        """

        json_params = { "location": { 
                                    "x": x_coord,
                                    "y": y_coord,
                                    "spatialReference": {
                                    "wkid": input_coord_system,
                                    }},    
                        "outSR": output_coord_system,
                        "distance": distance, 
                        "returnIntersection": return_intersection,
                        "f" : outputType
        }
        url_params = urlencode(json_params)

        reverse_geocode_url = "https://awsgeo.boston.gov/arcgis/rest/services/Locators/Boston_Composite_Prod/GeocodeServer/reverseGeocode?{}".format(url_params)
        #make request to Reverse geocode service
        with urlopen(reverse_geocode_url) as url:
            data = url.read().decode("utf-8")
            coordinate_results = loads(data)
        
        #return results as a json object
        return coordinate_results


    @classmethod
    # does a little bit of cleaning of the JSON from the API call
    def _parse_address_results(self, coordinate_results):
        """
        Returns a cleaned response from the ArcGIS reversegeocode API.

        Parameters:
        coordinate_results: (JSON Object): JSON object that gives results of ArcGIS API call

        Returns:
        cleaned_df: (Pandas Dataframe Object): Pandas dataframe whose columns are cleaned
  
        """
        columns_translate_dict = {'address.City' : 'City', 'address.Street' : 'Street', 'address.Match_addr' : 'Match_addr',
         'address.ZIP' : 'ZIP', 'address.Loc_name' : 'Loc_name', 'location.x' : 'x', 'location.y' : 'y',
         'location.spatialReference.wkid' : 'output_coord_system',
         'location.spatialReference.latestWkid' : 'latest_coord_system'}


        #empty JSON is false
        #if not coordinate_results:
        if len(coordinate_results) > 0:

            if list(coordinate_results.keys())[0] == "error":
                print("Unable to geocode from lat/long.  Error Message: {}".format(coordinate_results["error"]))
                return None

            if  len(coordinate_results["address"]) > 0:
                #creating the dataframe using json_normalize
                address_df = json_normalize(coordinate_results)
                address_df.rename(columns=columns_translate_dict, inplace=True)
                return address_df

        else:
            print("Received empty results from Boston ARCGIS server...")
            return None





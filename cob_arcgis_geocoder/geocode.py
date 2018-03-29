import pandas as pd 
import urllib.parse
import json
from pandas.io.json import json_normalize

class CobArcGISGeocoder(object):
    """
    Attributes:
    """

    def __init__(self, df, address_field):
        # initiate dataframe with new columns to be populated
        self.df = df 
        self.address_field = address_field
    
    @classmethod
    # clean dataframe before geocoding
    def clean_df(self, df, address_field):
        # add new columns we'll populate to the dataframe
        clean_df = pd.concat([df,pd.DataFrame(columns=list(["matched_address", "matched_address_score", "SAM_ID", "location_x", "location_y", "flag", "reverse_geocode_address"]))])
        
        # replace any empty strings in the dataframe with None value
        # clean_df.replace(r'^\s+$', None, regex=True)
        
       # clean_df.replace(r'\s+', None, regex=True).replace('', None)
        return clean_df
   
    @classmethod
    # find the address candidates for each address
    def find_address_candidates(self, SingleLine, Street="", coord_system="4326", outputFields="*", outputType="pjson"):
        parameters = { "Street": Street, 
                       "SingleLine": SingleLine,
                       "outSR": coord_system, 
                       "outFields": outputFields,
                       "f": outputType }
        parameters = urllib.parse.urlencode(parameters)
        candidates_url = "https://awsgeo.boston.gov/arcgis/rest/services/Locators/Boston_Composite_Prod/GeocodeServer/findAddressCandidates?{}".format(parameters) 

        with urllib.request.urlopen(candidates_url) as url:
            data = url.read().decode("utf-8")
            candidates = json.loads(data)

        return candidates
    
    @classmethod
    # pick the proper address candidate for each address
    def pick_address_candidate(self, candidates):

        if len(candidates["candidates"]) >= 1:

            # put all the candidates into a dataframe
            addresses_df = json_normalize(candidates["candidates"])

            # keep the point addresses (SAM addresses)
            addresses_df_points = addresses_df.loc[addresses_df["attributes.Addr_type"] == "PointAddress"]

            if len(addresses_df_points.index) == 0:
                
                # reverse geocode the non-point addresses
                matched_address_df = self.reverse_geocode(addresses_df)

                return matched_address_df
            
            else:
                # sort values by score and pick the highest one to return - Ref_ID is the SAM ID
                matched_address_df = addresses_df_points[["address", "score", "attributes.Ref_ID", "location.x", "location.y"]].sort_values(by="score", ascending=False).iloc[0]
                print(matched_address_df["attributes.Ref_ID"])
                # add flag to dataframe
                matched_address_df["flag"] = "Able to geocode to a point address."
            
                return matched_address_df
        
        else:
            return None
    
    @classmethod
    def reverse_geocode(self, address_df):
        # get the address to geocode and its location - *must be in StatePlane coords (3857)*
        address_to_geocode = address_df.sort_values(by="score", ascending=False).iloc[0]
        location_x = address_to_geocode[["attributes.DisplayX"]][0]
        location_y = address_to_geocode[["attributes.DisplayY"]][0]
        
        # TODO: let user select different out SR?
        reverse_geocode_url = "https://awsgeo.boston.gov/arcgis/rest/services/Locators/Boston_Composite_Prod/GeocodeServer/reverseGeocode?location={}%2C+{}&distance=&outSR=4326&returnIntersection=false&f=json".format(location_x,location_y) 

        with urllib.request.urlopen(reverse_geocode_url) as url:
            data = url.read().decode("utf-8")
            new_address_data = json.loads(data)
        
        new_address = new_address_data["address"]["Match_addr"]
        print("using this address: {} to reverse geocode.".format(new_address))

        reverse_geocode_candidates = self.find_address_candidates(SingleLine=new_address)

        # put address candidates in a data frame
        addresses_df = json_normalize(reverse_geocode_candidates["candidates"])
        addresses_df_points = addresses_df.loc[addresses_df["attributes.Addr_type"] == "PointAddress"]

        if len(addresses_df_points.index) == 0: 
            print("there were {} non-point address candidates only for the reverse geocode. Adding non-point address".format(len(addresses_df_points.index)))
            matched_address_df = addresses_df[["address", "score", "attributes.Ref_ID", "location.x", "location.y"]].sort_values(by="score", ascending=False).iloc[0]

            # add flag to dataframe
            matched_address_df["flag"] = "Unable to find address with a SAM ID."

            return matched_address_df

        else:
            print("there are {} point addresses that matched the reverse-geocoded address.".format(len(addresses_df_points.index)))
            matched_address_df = addresses_df_points[["address", "score", "attributes.Ref_ID", "location.x", "location.y"]].sort_values(by="score", ascending=False).iloc[0]
            
            # add flag to dataframe
            matched_address_df["flag"] = "Able to reverse-geocode to a point address."
            
            return matched_address_df

    @classmethod
    def geocode_df(self, df, address_field):
        df = self.clean_df(df=df, address_field=address_field)
        
        for index, row in df.iterrows():

            if row[address_field] is None: 
                df.at[index, "flag"] = "No address provided. Unable to geocode."
            else: 
                candidates = self.find_address_candidates(SingleLine=row[address_field])
                matched_address_df = self.pick_address_candidate(candidates)  

                if matched_address_df is not None: 
                    df.at[index, "matched_address"] = matched_address_df[["address"]][0]
                    df.at[index, "matched_address_score"] = matched_address_df[["score"]][0]
                    df.at[index, "SAM_ID"] = matched_address_df[["attributes.Ref_ID"]][0]
                    df.at[index, "location_x"] = matched_address_df[["location.x"]][0]
                    df.at[index, "location_y"] = matched_address_df[["location.y"]][0]
                    df.at[index, "flag"] = matched_address_df[["flag"]][0]
                else:
                    df.at[index, "flag"] = "Unable to geocode to any address."      
    
        return df

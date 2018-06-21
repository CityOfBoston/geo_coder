import pandas as pd 
import urllib.parse
import json
from pandas.io.json import json_normalize

class CobArcGISGeocoder(object):
    # TODO: write failed addresses to a table

    def __init__(self, df, address_field):
        # initiate dataframe with new columns to be populated
        self.df = df 
        self.address_field = address_field

    def geocode_df(self):
        
        # add columns for geocoded address information
        df = pd.concat([self.df,pd.DataFrame(columns=list(["matched_address", "matched_address_score", "SAM_ID", "location_x", "location_y", "flag", "reverse_geocode_address"]))])
        
        # Locators that return addresses with SAM IDs
        SAM_Locators = ["SAM_Sub_Unit_A", "SAM_Alternate"]

        # interate through each row and geocode the address
        for index, row in df.iterrows():
            
            if row[self.address_field] is None: 
                # if address field is empty, add flag to row
                df.at[index, "flag"] = "No address provided. Unable to geocode."
            else: 
                # if address field isn't empty, try geocoding:
                # 1. find the address candidates
                candidates = self._find_address_candidates(SingleLine=row[self.address_field])
                # 2. pick the from the list of candidates
                matched_address_df = self._pick_address_candidate(candidates, SAM_Locators)  

                if matched_address_df is not None: 
                    # if able to pick an address, update the row in the dataframe with the geocoded address information
                    df.at[index, "matched_address"] = matched_address_df[["address"]][0]
                    df.at[index, "matched_address_score"] = matched_address_df[["score"]][0]
                    df.at[index, "SAM_ID"] = matched_address_df[["attributes.Ref_ID"]][0]
                    df.at[index, "location_x"] = matched_address_df[["location.x"]][0]
                    df.at[index, "location_y"] = matched_address_df[["location.y"]][0]
                    df.at[index, "flag"] = matched_address_df[["flag"]][0]
                else:
                    # if unable to find an address to geocode to, flag the row in the dataframe
                    # TODO: write this row to a table in postgres so we can log failures
                    df.at[index, "flag"] = "Unable to geocode to any address."      

        # return the updated dataframe when the rows have been iterated through
        return df
   
    @classmethod
    # input the given address to the ESRI ArcGIS geocoder, default output coordinate system is 4326
    def _find_address_candidates(self, SingleLine, Street="", coord_system="4326", outputFields="*", outputType="pjson"):
        """Returns a JSON object of address candidates.
        
        Args:
            SingleLine (str): Specifies the location to be geocoded. The input address components are formatted as a single string.
            Street (str, optional): The street address location to be geocoded.
            coord_system (str, optional): The well-known ID (WKID) of the spatial reference or a spatial reference JSON object for the returned address candidates.
            outputFields (str, optional): The list of fields to be included in the returned result set. * returns all fields.
            outputType (str, optional): The response format. The default response format is html.
        
        Returns:
            JSON: Object containing candidate addresses.
        """

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
        
        # return the possible candidates as json
        return candidates
    
    @classmethod
    def _pick_address_candidate(self, candidates, locators):
        """Returns the best address from a JSON object of candidates.

        Args:
            candidates (:obj:`dataframe`): Dataframe of address candidates.
            locators (:obj:`list`): List of locators.

        Returns:
            dataframe: Dataframe with the best potential match if one is available.
            none: If there were no candidates returned return None.
        """

        if len(candidates["candidates"]) >= 1:

            # if there is more than 0 candidates, put all the them into a dataframe
            addresses_df = json_normalize(candidates["candidates"])

            # Locators prefixed with "SAM_" indicate the addresses returned have a SAM ID so we filter the dataframe for those
            addresses_df_SAM = addresses_df.loc[addresses_df["attributes.Loc_name"].isin(locators)]

            if len(addresses_df_SAM.index) == 0:
                print("there were {} non-SAM address candidates".format(len(addresses_df_SAM.index)))

                # if there are no SAM addresses, try to reverse geocode the highest scored candidate
                matched_address_df = self._reverse_geocode(addresses_df, locators)
                return matched_address_df
            
            else:
                print("there are {} SAM addresses".format(len(addresses_df_SAM.index)))

                # sort values by score and pick the highest one to return - **Ref_ID is the SAM ID**
                matched_address_df = addresses_df_SAM[["address", "score", "attributes.Ref_ID", "location.x", "location.y"]].sort_values(by="score", ascending=False).iloc[0]
                
                # add flag to dataframe and return it
                matched_address_df["flag"] = "Able to geocode to a SAM address."
                return matched_address_df
        
        else:
            # if there were no candidates returned, return None so the row in the dataframe can be properly flagged
            return None
    
    @classmethod
    # reverse geocode the returned address with the highest score if it is not a SAM address
    def _reverse_geocode(self, address_df, locators):
        """Reverse geocodes an address and returns the highest-scoring address if a SAM address is unable to be found.
        
        Args:
            address_df (:obj:`dataframe`): Dataframe of candidate addresses.
            locators (:obj:`list`): List of locators to filter the dataframe by.

        Returns:
            dataframe: Dataframe containing reverse-geocoded addresses.
        """

        # sort the candidates by score, use the highest one to geocode
        address_to_geocode = address_df.sort_values(by="score", ascending=False).iloc[0]
        
        # get its location - **must be in ESPG 3857**
        location_x = address_to_geocode[["attributes.DisplayX"]][0]
        location_y = address_to_geocode[["attributes.DisplayY"]][0]
        
        # feed the x,y to the reverse geocoder
        reverse_geocode_url = "https://awsgeo.boston.gov/arcgis/rest/services/Locators/Boston_Composite_Prod/GeocodeServer/reverseGeocode?location={}%2C+{}&distance=&outSR=4326&returnIntersection=false&f=json".format(location_x,location_y) 

        with urllib.request.urlopen(reverse_geocode_url) as url:
            data = url.read().decode("utf-8")
            new_address_data = json.loads(data)
        
        # reverse geocode returns an address that needs to be geocoded again
        new_address = new_address_data["address"]["Match_addr"]
        print("using this address: {} to reverse geocode.".format(new_address))

        # find the address candidates for the new address
        reverse_geocode_candidates = self._find_address_candidates(SingleLine=new_address)
        
        # put address candidates in a data frame, filter for SAM addresses
        addresses_df = json_normalize(reverse_geocode_candidates["candidates"])
        addresses_df_SAM = addresses_df.loc[addresses_df["attributes.Loc_name"].isin(locators)]

        if len(addresses_df_SAM.index) == 0: 
            # if there where no SAM addresses returned, add the highest-scored non-SAM address found in the initial attempt to geocode
            print("there were {} non-SAM address candidates only for the reverse geocode. Adding non-SAM address".format(len(addresses_df_SAM.index)))
            matched_address_df = addresses_df[["address", "score", "attributes.Ref_ID", "location.x", "location.y"]].sort_values(by="score", ascending=False).iloc[0]

            # add flag to dataframe and return it
            matched_address_df["flag"] = "Unable to find address with a SAM ID."
            return matched_address_df

        else:
            # if there were SAM addresses found after using the reverse geocoded address, use the one with the highest score
            print("there are {} SAM addresses that matched the reverse-geocoded address.".format(len(addresses_df_SAM.index)))
            matched_address_df = addresses_df_SAM[["address", "score", "attributes.Ref_ID", "location.x", "location.y"]].sort_values(by="score", ascending=False).iloc[0]
            
            # add flag to dataframe and return it
            matched_address_df["flag"] = "Able to reverse-geocode."
            return matched_address_df

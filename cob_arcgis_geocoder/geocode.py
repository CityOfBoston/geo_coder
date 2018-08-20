import pandas as pd 
import urllib.parse
import json
from pandas.io.json import json_normalize
import psycopg2
import subprocess
import os
import codecs
from collections import OrderedDict
import sys
from datetime import datetime

class CobArcGISGeocoder(object):

    def __init__(self, df, address_field):
        # initiate dataframe with new columns to be populated
        self.df = df 
        self.address_field = address_field

    def geocode_df(self):
        
        # add columns for geocoded address information
        df = pd.concat([self.df,pd.DataFrame(columns=["matched_address", "matched_address_score", "SAM_ID", "location_x", "location_y", "flag", "locator_name"])])
        
        # Locators that return addresses with SAM IDs
        SAM_Locators = ["SAM_Sub_Unit_A", "SAM_Alternate"]

        # Iterate through each row and geocode the address
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

                if matched_address_df is not None and matched_address_df[["flag"]][0] == "Able to geocode to a SAM address.": 
                    # if able to pick an address, update the row in the dataframe with the geocoded address information
                    df.at[index, "matched_address"] = matched_address_df[["address"]][0]
                    df.at[index, "matched_address_score"] = matched_address_df[["score"]][0]
                    df.at[index, "SAM_ID"] = matched_address_df[["attributes.Ref_ID"]][0]
                    df.at[index, "location_x"] = matched_address_df[["location.x"]][0]
                    df.at[index, "location_y"] = matched_address_df[["location.y"]][0]
                    df.at[index, "flag"] = matched_address_df[["flag"]][0]
                    df.at[index, "locator_name"] = matched_address_df[["attributes.Loc_name"]][0]
                elif matched_address_df is not None and matched_address_df[["flag"]][0] == "Able to geocode to a non-SAM address.":
                    df.at[index, "matched_address"] = matched_address_df[["address"]][0]
                    df.at[index, "matched_address_score"] = matched_address_df[["score"]][0]
                    df.at[index, "location_x"] = matched_address_df[["location.x"]][0]
                    df.at[index, "location_y"] = matched_address_df[["location.y"]][0]
                    df.at[index, "flag"] = matched_address_df[["flag"]][0]
                    df.at[index, "locator_name"] = matched_address_df[["attributes.Loc_name"]][0]
                    self._archive_non_sam_address(row[self.address_field], matched_address_df[["address"]][0])
                else:
                    # if unable to find an address to geocode to, flag the row in the dataframe
                    df.at[index, "flag"] = "Unable to geocode to any address."
                    # Set lat/long to 0 if unable to geocode
                    df.at[index, "location_x"] = 0.00
                    df.at[index, "location_y"] = 0.00      
                    self._archive_non_sam_address(row[self.address_field], None)

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
            locators (:obj:`list`): List of locators to filter by.

        Returns:
            dataframe: Dataframe with the best potential match if one is available.
            none: If there were no candidates returned return None.
        """

        if len(candidates["candidates"]) > 0:

            # if there is at least 1 candidate, put the results into a dataframe
            addresses_df = json_normalize(candidates["candidates"])

            # Locators prefixed with "SAM_" indicate the addresses returned have a SAM ID so we filter the dataframe for those
            addresses_df_SAM = addresses_df[addresses_df["attributes.Loc_name"].isin(locators)].copy()

            if len(addresses_df_SAM.index) == 0:
                print("there were {} SAM address candidates".format(len(addresses_df_SAM.index)))

                # if there are no SAM addresses, return the highest scored locator
                matched_address_df = addresses_df[["address", "score", "attributes.Ref_ID", "location.x", "location.y", "attributes.Loc_name"]].sort_values(by="score", ascending=False).iloc[0]
                matched_address_df["flag"] = "Able to geocode to a non-SAM address."
                return matched_address_df
            
            else:
                print("there are {} SAM addresses".format(len(addresses_df_SAM.index)))
                # sort values by score and pick the highest one to return - **Ref_ID is the SAM ID**
                matched_address_df = addresses_df_SAM[["address", "score", "attributes.Ref_ID", "location.x", "location.y", "attributes.Loc_name"]].sort_values(by="score", ascending=False).iloc[0]
                
                # add flag to dataframe and return it
                matched_address_df["flag"] = "Able to geocode to a SAM address."
                return matched_address_df
        
        else:
            # if there were no candidates returned, return None so the row in the dataframe can be properly flagged
            return None
    
    @classmethod
    def _archive_non_sam_address(self, address, returned_result):
        """Uploads to a postgres table to keep track of addresses that need to be assigned a SAM ID."""

        env_var_dict = dict()
        env_var_dict['upload_hostname'] = os.environ.get("POSTGRES_IP")
        env_var_dict['upload_database_name'] = os.environ.get("POSTGRES_PROD_DB")
        env_var_dict['upload_database_user'] = os.environ.get("POSTGRES_PROD_USER")
        env_var_dict['upload_database_pass'] = os.environ.get("POSTGRES_PROD_PASS")
        env_var_dict['upload_database_port'] = os.environ.get("POSTGRES_PROD_PORT")
        
        # If environment variables don't exist, continue to run without archiving data
        for _, v in env_var_dict.items():
            if v == None:
                print("Environment variables not found. Continuing...")
                return

        config_params = dict()
        config_params['upload_table_name'] = "internal_data.failed_geocoded_addresses"
        

        conn = psycopg2.connect("dbname='{}' user='{}' host='{}' password='{}' port={}".format(env_var_dict['upload_database_name'], env_var_dict['upload_database_user'], env_var_dict['upload_hostname'], env_var_dict['upload_database_pass'], int(env_var_dict['upload_database_port']) ))
        cur = conn.cursor()

        # Write the latest addresses to the table
        try:
            # First delete rows where the address already exists
            delete_query = """DELETE FROM {} WHERE address_submitted = '{}'""".format(config_params['upload_table_name'], address)
            print(delete_query)
            cur.execute(delete_query)
            conn.commit()

            insert_query = "INSERT INTO {} (address_submitted, returned_result, time_stamp) VALUES ('{}', '{}', '{}')".format(config_params['upload_table_name'], address, returned_result, datetime.now())
            print(insert_query)
            cur.execute(insert_query)
            conn.commit()

            print("Response from inserting into the {} table: {}".format(config_params['upload_table_name'], cur.statusmessage))
            
            if 'insert' not in cur.statusmessage.lower():
                print("Incorrect status message from insert operation. Exiting. An error occured.")
                sys.exit(1)

        except Exception as e:
            print("ERROR: Issue inserting data into the database. Exiting. Error: {}".format(e))
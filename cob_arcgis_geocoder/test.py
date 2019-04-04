import unittest
import pandas as pd
from cob_arcgis_geocoder.geocode import CobArcGISGeocoder
from cob_arcgis_geocoder.reverse_geocode import CobArcGISReverseGeocoder

# test able to initiate class
class TestInitiatingGeocoderClass(unittest.TestCase):
    def setUp(self):
        self.df = pd.DataFrame({"id": [1, 2], "address": ["89 Orleans Street Boston MA, 02128", "51 Montebello Road Apt 2 Boston, MA 02130"]})
        self.address = "address"
        self.geocoder = CobArcGISGeocoder(self.df, self.address)
    
    def test_can_correctly_create_geocoder_class(self):
        self.assertIsInstance(self.geocoder, CobArcGISGeocoder)


# test about to find address cadidates
class TestAbleToFindAddressCandidates(unittest.TestCase):
    def setUp(self):
        self.df = pd.DataFrame({"id": [1], "address": ["89 Orleans Street Boston MA, 02128"]})
        self.address_to_geocode = self.df["address"][0]
        self.geocoder = CobArcGISGeocoder(self.df, self.address_to_geocode)
        self.candidates = self.geocoder._find_address_candidates(self.address_to_geocode)

    def test_parameters_are_as_expected(self):
        print(self.candidates)
        self.assertGreaterEqual(len(self.candidates["candidates"]), 6)

# Picking Address Candidate Tests
# test able to return correct PointAddress when available
class TestAbleToCorrectlyPickPointAddressCandidate(unittest.TestCase):
    def setUp(self):
        SAM_Locators = ["SAM_Sub_Unit_A", "SAM_Alternate"]
        self.df = pd.DataFrame({"id": [1], "address": ["89 Orleans Street Boston MA, 02128"]})
        self.address_to_geocode = self.df["address"][0]
        self.geocoder = CobArcGISGeocoder(self.df, self.address_to_geocode)
        self.candidates = self.geocoder._find_address_candidates(self.address_to_geocode)
        self.picked_candidate = self.geocoder._pick_address_candidate(self.candidates, SAM_Locators)
    
    def test_picks_highest_score_candidate(self):
        self.assertEqual(self.picked_candidate["score"], 94.57)

    def test_picks_expected_candidate(self):
        self.assertEqual(self.picked_candidate["attributes.Ref_ID"], 105967)

# test returns None when there are no candidates returned from ESRI API
class TestReturnsNoneWhenNoCandidates(unittest.TestCase):
    def setUp(self):
        SAM_Locators = ["SAM_Sub_Unit_A", "SAM_Alternate"]
        self.df = pd.DataFrame({"id": [1], "address": ["This isn't an address"]})
        self.address_to_geocode = self.df["address"][0]
        self.geocoder = CobArcGISGeocoder(self.df, self.address_to_geocode)
        self.candidates = self.geocoder._find_address_candidates(self.address_to_geocode)
        self.picked_candidate = self.geocoder._pick_address_candidate(self.candidates, SAM_Locators)

    def test_returns_none_when_no_candidates(self):
        self.assertEqual(self.picked_candidate, None)

# Reverse Geocode Tests
# test returns expected results when finds a point address
class TestReverseGeocodeFindsPoint(unittest.TestCase):
    def setUp(self):
        SAM_Locators = ["SAM_Sub_Unit_A", "SAM_Alternate"]
        self.df = pd.DataFrame({"id": [1], "address": ["890 Commonwealth Avenue"]})
        self.address_to_geocode = self.df["address"][0]
        self.geocoder = CobArcGISGeocoder(self.df, self.address_to_geocode)
        self.candidates = self.geocoder._find_address_candidates(self.address_to_geocode)
        self.picked_candidate = self.geocoder._pick_address_candidate(self.candidates, SAM_Locators)

    def test_returns_point_address(self):
        self.assertEqual(self.picked_candidate["attributes.Ref_ID"], 11864)
    
    def test_returns_correct_flag_point_addresses(self):
        self.assertEqual(self.picked_candidate["flag"], "Able to geocode to a non-SAM address.")

# Geocoding Logic Tests
class TestAbleToHandleNullAddresses(unittest.TestCase):
    def setUp(self):
        self.df = pd.DataFrame({"id": [1, 2], "address": ["89 Orleans Street Boston MA, 02128", None]})
        self.address = "address"
        self.geocoder = CobArcGISGeocoder(self.df, self.address)
        self.geocode_df_with_Nulls = self.geocoder.geocode_df()

    def test_handle_null_address(self):
        self.assertEqual(self.geocode_df_with_Nulls.loc[:,"flag"][1], "No address provided. Unable to geocode.")

class TestAbleToFindPointAddress(unittest.TestCase):
    def setUp(self):
        self.df = pd.DataFrame({"id": [1], "address": ["1 City Hall Plz, Boston, 02108"]})
        self.address = "address"
        self.geocoder = CobArcGISGeocoder(self.df, self.address)
        self.geocode_df = self.geocoder.geocode_df()
    
    def test_returns_expected_address(self):
        print(self.geocode_df["SAM_ID"])
        self.assertEqual(self.geocode_df["SAM_ID"][0], 32856)

class TestAbleToReverseGeocodeToPointAddress(unittest.TestCase):
    def setUp(self):
        self.df = pd.DataFrame({"id": [1], "address": ["890 Commonwealth Avenue"]})
        self.address = "address"
        self.geocoder = CobArcGISGeocoder(self.df, self.address)
        self.geocode_df = self.geocoder.geocode_df()

    def test_reverse_geocode_to_point_address(self):
        self.assertEqual(self.geocode_df["SAM_ID"][0], 11864)

class TestHandlesNotFindingAddressAsExpected(unittest.TestCase):
    def setUp(self):
        self.df = pd.DataFrame({"id": [1], "address": ["This isn't an address."]})
        self.address = "address"
        self.geocoder = CobArcGISGeocoder(self.df, self.address)
        self.geocode_df = self.geocoder.geocode_df()

    def test_reverse_geocode_to_point_address(self):
        self.assertEqual(self.geocode_df["flag"][0], "Unable to geocode to any address.")

#Actual ReverseGeocoder Test Cases

class TestInitiatingReverseGeocoderClass(unittest.TestCase):
    def setUp(self):
        test_df = pd.DataFrame({"id" : [1, 2],
         "x_coord": [20757534.681129166, -71.12458864],
         "y_coord" :[2959300.669159480, 42.367412], 
         'input_coord_system' : [2249, 4326],
         'output_coord_system' : [4326, 4326],
          'return_intersection' : [False, False]})
        self.df = test_df
        self.x = "x_coord"
        self.y = "y_coord"
        self.input_coord_system = "input_coord_system"
        self.output_coord_system = "output_coord_system"
        self.return_intersection = "return_intersection"
        self.reverse_geocoder = CobArcGISReverseGeocoder(self.df, self.x, 
            self.y, self.input_coord_system,
            self.output_coord_system, self.return_intersection)


    def test_setup_reverse_geocode_class(self):
        self.assertIsInstance(self.reverse_geocoder, CobArcGISReverseGeocoder)


class TestReverseGeocoderDifferentInputCoords(unittest.TestCase):
    def setUp(self):
        self.df = pd.DataFrame({"id" : [1],"x_coord": [776969.460426],
         "y_coord" :[2959300.669159480],'input_coord_system' : [2249],
         'output_coord_system' : [4326], 'return_intersection' : [True]})
        self.x = "x_coord"
        self.y = "y_coord"
        self.input_coord_system = "input_coord_system"
        self.output_coord_system = "output_coord_system"
        self.return_intersection = "return_intersection"
        self.x_value = self.df["x_coord"][0]
        self.y_value = self.df["y_coord"][0]
        self.input_coord_value = self.df['input_coord_system'][0]
        self.reverse_geocoder = CobArcGISReverseGeocoder(self.df, self.x_value, 
            self.y_value, self.input_coord_system, self.output_coord_system,
            self.return_intersection)
        self.api_results = self.reverse_geocoder._reverse_geocode(
            self.x_value, self.y_value, self.input_coord_value)
        self.address_df = self.reverse_geocoder._parse_address_results(self.api_results)


    def test_api_results_not_null(self):
        self.assertTrue(self.api_results)

    def test_geocoder_df_not_null(self):
        self.assertFalse(self.address_df.empty)

    def test_address_output_from_MA_State_coord(self):
        print(self.address_df.columns)
        print(self.address_df['Match_addr'])
        self.assertEqual(self.address_df['Match_addr'][0], '427 Commercial St, Boston, 136259, 02109')


    def test_default_output_coord_sys(self):
        self.assertEqual(self.address_df['output_coord_system'][0], 4326)


class TestReverseGeocoderwithMAStatePlainCoords(unittest.TestCase):
    def setUp(self):
        self.df = pd.DataFrame({"id" : [1],"x_coord": [776969.460426],
         "y_coord" :[2959300.669159480],'input_coord_system' : [2249],
         'output_coord_system' : [4326], 'return_intersection' : [True]})
        self.x = "x_coord"
        self.y = "y_coord"
        self.input_coord_system = "input_coord_system"
        self.output_coord_system = "output_coord_system"
        self.return_intersection = "return_intersection"
        self.x_value = self.df["x_coord"][0]
        self.y_value = self.df["y_coord"][0]
        self.input_coord_value = self.df['input_coord_system'][0]
        self.reverse_geocoder = CobArcGISReverseGeocoder(self.df, self.x_value, 
            self.y_value, self.input_coord_system, self.output_coord_system,
            self.return_intersection)
        self.api_results = self.reverse_geocoder._reverse_geocode(
            self.x_value, self.y_value, self.input_coord_value)
        self.address_df = self.reverse_geocoder._parse_address_results(self.api_results)


    def test_api_results_not_null(self):
        self.assertTrue(self.api_results)

    def test_geocoder_df_not_null(self):
        self.assertFalse(self.address_df.empty)

    def test_address_output_from_MA_State_coord(self):
        print(self.address_df.columns)
        print(self.address_df['Match_addr'])
        self.assertEqual(self.address_df['Match_addr'][0], '427 Commercial St, Boston, 136259, 02109')


    def test_default_output_coord_sys(self):
        self.assertEqual(self.address_df['output_coord_system'][0], 4326)


class TestIncorrectParams(unittest.TestCase):
    def setUp(self):
        self.df = pd.DataFrame({"id" : [1],"x_coord": [20757534.681129166],
         "y_coord" :[2959300.669159480],'input_coord_system' : [2249],
         'output_coord_system' : [2249], 'return_intersection' : [True]})
        self.x = "x_coord"
        self.y = "y_coord"
        self.input_coord_system = "input_coord_system"
        self.output_coord_system = "output_coord_system"
        self.return_intersection = "return_intersection"
        self.reverse_geocoder = CobArcGISReverseGeocoder(self.df, self.x, 
            self.y, self.input_coord_system,
            self.output_coord_system, self.return_intersection)
        self.api_results = self.reverse_geocoder._reverse_geocode(
            self.df["x_coord"][0], self.df["y_coord"][0], self.input_coord_system)
        self.address_df = self.reverse_geocoder._parse_address_results(self.api_results)


    def get_an_actual_error_message(self):
        self.asssertTrue(self.api_results)

    def test_address_results_df_not_null(self):
        self.assertTrue(self.address_df is None)

    def test_error_message(self):
        print(self.api_results)
        self.code = self.api_results.get('error')['code']
        self.assertEqual(self.code, 400)


class TestReverseGeocoderwithMAStatePlainCoordsasInputandOutput(unittest.TestCase):
    def setUp(self):
        self.df = pd.DataFrame({"id" : [1],"x_coord": [776969.460426],
         "y_coord" :[2959300.669159480],'input_coord_system' : [2249],
         'output_coord_system' : [2249], 'return_intersection' : [True]})
        self.x = "x_coord"
        self.y = "y_coord"
        self.input_coord_system = "input_coord_system"
        self.output_coord_system = "output_coord_system"
        self.return_intersection = "return_intersection"
        self.x_value = self.df["x_coord"][0]
        self.y_value = self.df["y_coord"][0]
        self.input_coord_value = self.df['input_coord_system'][0]
        self.output_coord_system = self.df['output_coord_system'][0]
        self.reverse_geocoder = CobArcGISReverseGeocoder(self.df, self.x_value, 
            self.y_value, self.input_coord_system, self.output_coord_system,
            self.return_intersection)
        self.api_results = self.reverse_geocoder._reverse_geocode(
            self.x_value, self.y_value, self.input_coord_value, self.output_coord_system)
        self.address_df = self.reverse_geocoder._parse_address_results(self.api_results)


    def test_default_output_coord_sys(self):
        print(self.api_results)
        self.assertEqual(self.address_df['latest_coord_system'][0], 2249)
        
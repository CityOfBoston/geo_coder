import unittest
from unittest.mock import Mock
import pandas as pd
from cob_arcgis_geocoder.geocode import helloWorld, CobArcGISGeocoder

# test able to initiate class
class TestInitiatingGeocoderClass(unittest.TestCase):
    def setUp(self):
        self.df = pd.DataFrame({"id": [1, 2], "address": ["89 Orleans Street Boston MA, 02128", "51 Montebello Road Apt 2 Boston, MA 02130"]})
        self.address = "address"
        self.geocoder = CobArcGISGeocoder(self.df, self.address)
    
    def test_can_correctly_create_geocoder_class(self):
        self.assertIsInstance(self.geocoder, CobArcGISGeocoder)

    def test_address_field_is_string(self):
        self.assertIsInstance(self.geocoder.address_field, str)

class TestAlbleToCleanDf(unittest.TestCase):
    def setUp(self):
        self.df = pd.DataFrame({"id": [1, 2], "address": ["89 Orleans Street Boston MA, 02128", " "]})
        self.address = "address"
        self.geocoder = CobArcGISGeocoder(self.df, self.address)
        self.clean_df = self.geocoder.clean_df(df=self.df, address_field=self.address)
    
    # test able to update df with new fields 
    def test_address_fields_addedd(self):
        self.assertIn("matched_address", list(self.clean_df))
    
    # test able to convert empty strings to NaN
    def test_empty_strings_converted_to_None(self):
  # self.assertEqual(math.isnan(self.clean_df.loc[:,"address"][1]), math.isnan(np.NaN))
        self.assertEqual(self.clean_df.loc[:,"address"][1], None)

# test about to find address cadidates
class TestAbleToFindAddressCandidates(unittest.TestCase):
    def setUp(self):
        self.df = pd.DataFrame({"id": [1], "address": ["89 Orleans Street Boston MA, 02128"]})
        self.address_to_geocode = self.df["address"][0]
        self.geocoder = CobArcGISGeocoder(self.df, self.address_to_geocode)
        self.candidates = self.geocoder.find_address_candidates(self.address_to_geocode)

    def test_parameters_are_as_expected(self):
        self.assertEqual(len(self.candidates["candidates"]), 6)

# PICKING ADDRESS CANDIDATES TESTS
# test able to return correct PointAddress when available
class TestAbleToCorrectlyPickPointAddressCandidate(unittest.TestCase):
    def setUp(self):
        self.df = pd.DataFrame({"id": [1], "address": ["89 Orleans Street Boston MA, 02128"]})
        self.address_to_geocode = self.df["address"][0]
        self.geocoder = CobArcGISGeocoder(self.df, self.address_to_geocode)
        self.candidates = self.geocoder.find_address_candidates(self.address_to_geocode)
        self.picked_candidate = self.geocoder.pick_address_candidate(self.candidates)
    
    def test_picks_highest_score_candidate(self):
        self.assertEqual(self.picked_candidate["score"], 94.57)

    def test_picks_expected_candidate(self):
        self.assertEqual(self.picked_candidate["attributes.Ref_ID"], 105967)

# test appriopriately calls the reverse geocode function when no PointAddresses
class TestAbleToCallReverseGeocode(unittest.TestCase):
    def setUp(self):
        self.df = pd.DataFrame({"id": [1], "address": ["890 Commonwealth Avenue"]})
        self.address_to_geocode = self.df["address"][0]
        self.geocoder = CobArcGISGeocoder(self.df, self.address_to_geocode)
        self.candidates = self.geocoder.find_address_candidates(self.address_to_geocode)
    
    def test_calls_reverse_geocode_function(self):
        self.geocoder.reverse_geocode = Mock()
        self.geocoder.pick_address_candidate(self.candidates)
        self.geocoder.reverse_geocode.assert_called()

# test returns None when there are no candidates returned from ESRI API
class TestReturnsNoneWhenNoCandidates(unittest.TestCase):
    def setUp(self):
        self.df = pd.DataFrame({"id": [1], "address": ["This isn't an address"]})
        self.address_to_geocode = self.df["address"][0]
        self.geocoder = CobArcGISGeocoder(self.df, self.address_to_geocode)
        self.candidates = self.geocoder.find_address_candidates(self.address_to_geocode)
        self.picked_candidate = self.geocoder.pick_address_candidate(self.candidates)

    def test_returns_none_when_no_candidates(self):
        self.assertEqual(self.picked_candidate, None)

# REVERSE GEOCODE TESTS

# test calls correct functions
class TestReverseGeocodeCallsFindAddressCandidates(unittest.TestCase):
    def setUp(self):
        self.df = pd.DataFrame({"id": [1], "address": ["890 Commonwealth Avenue"]})
        self.address_to_geocode = self.df["address"][0]
        self.geocoder = CobArcGISGeocoder(self.df, self.address_to_geocode)
        self.candidates = self.geocoder.find_address_candidates(self.address_to_geocode)
        self.picked_candidate = self.geocoder.pick_address_candidate(self.candidates)

    def test_calls_reverse_geocode_function(self):
        self.geocoder.reverse_geocode = Mock()
        self.geocoder.pick_address_candidate(self.candidates)
        self.geocoder.reverse_geocode.assert_called()

# test returns expected results when finds a point address
class TestReverseGeocodeReturnsExpectedResultsWhenFindsPoint(unittest.TestCase):
    def setUp(self):
        self.df = pd.DataFrame({"id": [1], "address": ["890 Commonwealth Avenue"]})
        self.address_to_geocode = self.df["address"][0]
        self.geocoder = CobArcGISGeocoder(self.df, self.address_to_geocode)
        self.candidates = self.geocoder.find_address_candidates(self.address_to_geocode)
        self.picked_candidate = self.geocoder.pick_address_candidate(self.candidates)

    def test_returns_point_address(self):
        self.assertEqual(self.picked_candidate["attributes.Ref_ID"], 41280)
    
    def test_returns_correct_flag_no_point_addresses(self):
        self.assertEqual(self.picked_candidate["flag"], "Able to reverse-geocode to a point address.")
        




# TEST FULL GEOCODE LOGIC
# test able to handle null addresses
# class TestAbleToHandleNullAddresses(unittest.TestCase):
#     def setUp(self):
#         self.df = pd.DataFrame({"id": [1, 2], "address": ["89 Orleans Street Boston MA, 02128", None]})
#         self.address = "address"
#         self.geocoder = CobArcGISGeocoder(self.df, self.address)
#         self.geocode_df_with_Nulls = self.geocoder.geocode_df(df=self.df, address_field=self.address)

#     def test_handle_null_address(self):
#         self.assertEqual(self.geocode_df_with_Nulls.loc[:,"flag"][1], "No address provided in this field. Unable to geocode.")
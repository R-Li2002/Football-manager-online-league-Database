import unittest

from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker

from database import Base
from models import Player, PlayerAttribute, PlayerAttributeVersion
from repositories.attribute_repository import (
    AttributeRangeFilter,
    PositionScoreFilter,
    search_player_attributes_advanced,
    search_player_attributes_by_name,
)
from repositories.player_repository import search_players_by_name
from search_normalization import build_search_normalized_keys, normalize_search_text, normalize_search_text_loose


class SearchNormalizationTests(unittest.TestCase):
    def test_base_normalization_removes_common_diacritics(self):
        self.assertEqual(normalize_search_text("İlkay Gündoğan"), "ilkaygundogan")
        self.assertEqual(normalize_search_text("João Félix"), "joaofelix")
        self.assertEqual(normalize_search_text("Martin Ødegaard"), "martinodegaard")

    def test_loose_normalization_supports_umlaut_substitutions(self):
        self.assertEqual(normalize_search_text_loose("Gündoğan"), "guendogan")
        self.assertEqual(normalize_search_text_loose("Özil"), "oezil")

    def test_greek_letters_normalize_to_latin_search_keys(self):
        self.assertEqual(normalize_search_text("Αλέξανδρος"), "alexandros")
        self.assertEqual(normalize_search_text_loose("Θεόδωρος"), "theodoros")

    def test_search_keys_include_collapsed_and_loose_umlaut_variants(self):
        strict_keys, loose_keys = build_search_normalized_keys("guendogan")
        self.assertEqual(strict_keys, ["guendogan", "gundogan"])
        self.assertEqual(loose_keys, ["guendogan"])


class SearchRepositoryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})

        @event.listens_for(cls.engine, "connect")
        def _register_search_functions(dbapi_connection, _connection_record):
            dbapi_connection.create_function("heigo_normalize", 1, normalize_search_text)
            dbapi_connection.create_function("heigo_normalize_loose", 1, normalize_search_text_loose)

        Base.metadata.create_all(cls.engine)
        cls.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=cls.engine)

    @classmethod
    def tearDownClass(cls):
        cls.engine.dispose()

    def setUp(self):
        self.db = self.SessionLocal()
        self.db.query(PlayerAttributeVersion).delete()
        self.db.query(PlayerAttribute).delete()
        self.db.query(Player).delete()
        self.db.add_all(
            [
                Player(uid=1, name="İlkay Gündoğan", age=34, initial_ca=150, ca=150, pa=150, position="MC", nationality="DE", team_name="Test", wage=1.0, slot_type=""),
                Player(uid=2, name="Martin Ødegaard", age=27, initial_ca=160, ca=160, pa=160, position="AMC", nationality="NO", team_name="Test", wage=1.0, slot_type=""),
                Player(uid=3, name="Αλέξανδρος", age=25, initial_ca=130, ca=130, pa=130, position="ST", nationality="GR", team_name="Test", wage=1.0, slot_type=""),
            ]
        )
        self.db.add_all(
            [
                PlayerAttributeVersion(uid=11, data_version="2620", name="Benjamin Šeško", position="ST", age=22, ca=150, pa=170, nationality="SI", club="Test", pos_st=20, finishing=16, passing=9),
                PlayerAttributeVersion(uid=12, data_version="2620", name="Viktor Gyökeres", position="ST", age=27, ca=160, pa=165, nationality="SE", club="Test", pos_st=18, pos_amc=12, finishing=17, passing=11),
                PlayerAttributeVersion(uid=13, data_version="2620", name="Αλέξανδρος", position="MC", age=25, ca=130, pa=140, nationality="GR", club="Test", pos_mc=18, pos_dm=10, passing=17, decisions=15),
                PlayerAttributeVersion(uid=14, data_version="2620", name="Keeper Prime", position="GK", age=28, ca=148, pa=155, nationality="BR", club="Test", pos_gk=18, reflexes=17, handling=16),
            ]
        )
        self.db.commit()

    def tearDown(self):
        self.db.close()

    def test_player_search_matches_base_latinized_query(self):
        results = search_players_by_name(self.db, "gundogan")
        self.assertEqual([player.name for player in results], ["İlkay Gündoğan"])

    def test_player_search_matches_loose_umlaut_query(self):
        results = search_players_by_name(self.db, "guendogan")
        self.assertEqual([player.name for player in results], ["İlkay Gündoğan"])

    def test_player_search_matches_scandinavian_letter_query(self):
        results = search_players_by_name(self.db, "odegaard")
        self.assertEqual([player.name for player in results], ["Martin Ødegaard"])

    def test_attribute_search_matches_european_diacritics(self):
        results = search_player_attributes_by_name(self.db, "sesko", data_version="2620")
        self.assertEqual([player.name for player in results], ["Benjamin Šeško"])

    def test_attribute_search_matches_greek_name_with_latin_input(self):
        results = search_player_attributes_by_name(self.db, "alexandros", data_version="2620")
        self.assertEqual([player.name for player in results], ["Αλέξανδρος"])

    def test_attribute_search_matches_base_latin_query_for_umlaut_name(self):
        results = search_player_attributes_by_name(self.db, "gyokeres", data_version="2620")
        self.assertEqual([player.name for player in results], ["Viktor Gyökeres"])

    def test_advanced_attribute_search_supports_query_and_range_filters(self):
        result = search_player_attributes_advanced(
            self.db,
            query_text="gyokeres",
            range_filters=[AttributeRangeFilter(field="ca", minimum=155)],
            data_version="2620",
        )
        self.assertEqual([player.uid for player in result.items], [12])
        self.assertFalse(result.truncated)

    def test_advanced_attribute_search_supports_filters_without_query(self):
        result = search_player_attributes_advanced(
            self.db,
            range_filters=[
                AttributeRangeFilter(field="age", maximum=25),
                AttributeRangeFilter(field="passing", minimum=15),
            ],
            data_version="2620",
        )
        self.assertEqual([player.uid for player in result.items], [13])

    def test_advanced_attribute_search_uses_or_for_positions(self):
        result = search_player_attributes_advanced(
            self.db,
            position_filters=[
                PositionScoreFilter(position="ST", minimum_score=18),
                PositionScoreFilter(position="MC", minimum_score=18),
            ],
            data_version="2620",
        )
        self.assertEqual([player.uid for player in result.items], [12, 11, 13])

    def test_advanced_attribute_search_reports_truncation(self):
        result = search_player_attributes_advanced(
            self.db,
            range_filters=[AttributeRangeFilter(field="ca", minimum=120)],
            limit=2,
            data_version="2620",
        )
        self.assertEqual(len(result.items), 2)
        self.assertTrue(result.truncated)

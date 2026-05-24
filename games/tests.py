from unittest.mock import MagicMock, patch

from django.core.cache import cache
from django.test import TestCase, Client
from django.urls import reverse

from games.models import BoardGame
from games.services import bgg as bgg_service
from games.test_utils import create_test_boardgame
from games.services.cache import set_stale_search_cache
from games.test_utils import create_test_boardgame


class BoardGameModelTests(TestCase):
    def test_str_and_bgg_url(self):
        game = create_test_boardgame(bgg_id=13, title="Catan")
        self.assertEqual(str(game), "Catan")
        self.assertIn("13", game.bgg_url)


class BGGServiceTests(TestCase):
    SEARCH_XML = """<?xml version="1.0" encoding="UTF-8"?>
    <items total="1">
      <item type="boardgame" id="13">
        <name type="primary" value="Catan"/>
        <yearpublished value="1995"/>
      </item>
    </items>"""

    THING_XML = """<?xml version="1.0" encoding="UTF-8"?>
    <items>
      <item type="boardgame" id="13">
        <name type="primary" value="Catan"/>
        <yearpublished value="1995"/>
        <minplayers value="3"/>
        <maxplayers value="4"/>
        <description>Trade and build</description>
        <thumbnail>https://cf.geekdo-static.com/catan.jpg</thumbnail>
      </item>
    </items>"""

    def setUp(self):
        cache.clear()

    @patch("games.services.bgg._get_xml")
    def test_search_boardgames(self, mock_get_xml):
        import xml.etree.ElementTree as ET

        mock_get_xml.return_value = ET.fromstring(self.SEARCH_XML)
        results, from_stale = bgg_service.search_boardgames("catan")
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["bgg_id"], 13)
        self.assertEqual(results[0]["title"], "Catan")
        self.assertFalse(from_stale)

    @patch("games.services.bgg._fetch_search_results")
    def test_search_returns_stale_cache_on_bgg_error(self, mock_fetch):
        stale = [{"bgg_id": 13, "title": "Catan", "year_published": 1995}]
        set_stale_search_cache("catan", stale)
        mock_fetch.side_effect = bgg_service.BGGError("unavailable")
        results, from_stale = bgg_service.search_boardgames("catan")
        self.assertEqual(results, stale)
        self.assertTrue(from_stale)

    @patch("games.services.bgg.requests.get")
    def test_get_xml_retries_gateway_errors(self, mock_get):
        import xml.etree.ElementTree as ET

        bad = MagicMock()
        bad.status_code = 502
        bad.text = "Bad Gateway"

        ok = MagicMock()
        ok.status_code = 200
        ok.text = self.SEARCH_XML
        ok.raise_for_status = MagicMock()

        mock_get.side_effect = [bad, bad, ok]
        root = bgg_service._get_xml("search", {"query": "catan"})
        self.assertEqual(len(root.findall("item")), 1)
        self.assertGreaterEqual(mock_get.call_count, 3)

    @patch("games.services.bgg.fetch_things_cached")
    def test_ensure_boardgame_creates_cache(self, mock_fetch_things):
        mock_fetch_things.return_value = {
            13: {
                "bgg_id": 13,
                "title": "Catan",
                "year_published": 1995,
                "min_players": 3,
                "max_players": 4,
                "description": "Trade",
                "image_url": "https://example.com/catan.jpg",
                "bgg_url": "https://boardgamegeek.com/boardgame/13",
            }
        }
        game = bgg_service.ensure_boardgame(13)
        self.assertEqual(BoardGame.objects.count(), 1)
        again = bgg_service.ensure_boardgame(13)
        self.assertEqual(again.pk, game.pk)
        mock_fetch_things.assert_called_once()

    @patch("games.services.bgg._get_xml")
    def test_fetch_things_cached_reuses_redis(self, mock_get_xml):
        import xml.etree.ElementTree as ET

        mock_get_xml.return_value = ET.fromstring(self.THING_XML)
        first = bgg_service.fetch_things_cached([13])
        second = bgg_service.fetch_things_cached([13])
        self.assertIn(13, first)
        self.assertEqual(first[13]["title"], second[13]["title"])
        mock_get_xml.assert_called_once()

    @patch("games.services.bgg.fetch_things_cached")
    def test_ensure_boardgames_batches_missing_ids(self, mock_fetch_things):
        mock_fetch_things.return_value = {
            13: {
                "bgg_id": 13,
                "title": "Catan",
                "year_published": 1995,
                "min_players": 3,
                "max_players": 4,
                "description": "",
                "image_url": "",
                "bgg_url": "https://boardgamegeek.com/boardgame/13",
            },
            9209: {
                "bgg_id": 9209,
                "title": "Ticket to Ride",
                "year_published": 2004,
                "min_players": 2,
                "max_players": 5,
                "description": "",
                "image_url": "",
                "bgg_url": "https://boardgamegeek.com/boardgame/9209",
            },
        }
        games = bgg_service.ensure_boardgames([13, 9209])
        self.assertEqual(len(games), 2)
        mock_fetch_things.assert_called_once_with([13, 9209])

    def test_ensure_boardgames_from_summaries_avoids_bgg(self):
        summaries = [
            {
                "bgg_id": 424242,
                "title": "Summary Game",
                "year_published": 2020,
                "image_url": "https://example.com/game.jpg",
                "bgg_url": "https://boardgamegeek.com/boardgame/424242",
            }
        ]
        with patch("games.services.bgg.fetch_things_cached") as mock_fetch:
            games = bgg_service.ensure_boardgames_from_summaries(summaries)
            self.assertEqual(len(games), 1)
            self.assertEqual(games[0].title, "Summary Game")
            mock_fetch.assert_not_called()


class RecommendedGamesTests(TestCase):
    def setUp(self):
        cache.clear()

    THING_BATCH_XML = """<?xml version="1.0" encoding="UTF-8"?>
    <items>
      <item type="boardgame" id="13">
        <name type="primary" value="Catan"/>
        <yearpublished value="1995"/>
        <thumbnail>https://example.com/catan.jpg</thumbnail>
        <statistics><ratings>
          <bayesaverage value="7.12345"/>
          <ranks><rank name="boardgame" value="250" bayesaverage="7.12345"/></ranks>
        </ratings></statistics>
      </item>
      <item type="boardgame" id="224517">
        <name type="primary" value="Brass: Birmingham"/>
        <yearpublished value="2018"/>
        <statistics><ratings>
          <bayesaverage value="8.56789"/>
          <ranks><rank name="boardgame" value="1" bayesaverage="8.56789"/></ranks>
        </ratings></statistics>
      </item>
    </items>"""

    @patch("games.services.recommended._candidate_bgg_ids", return_value=[13, 224517])
    @patch("games.services.bgg._get_xml")
    def test_get_top_rated_returns_lowest_rank_first(self, mock_get_xml, _mock_ids):
        import xml.etree.ElementTree as ET

        mock_get_xml.return_value = ET.fromstring(self.THING_BATCH_XML)
        from games.services.recommended import get_top_rated_boardgames

        results = get_top_rated_boardgames(limit=5)
        self.assertGreaterEqual(len(results), 1)
        self.assertEqual(results[0]["bgg_id"], 224517)
        self.assertEqual(results[0]["bgg_rank"], 1)


class EventFormRecommendedTests(TestCase):
    def setUp(self):
        from django.contrib.auth import get_user_model
        from django.contrib.auth.models import Group

        User = get_user_model()
        Group.objects.get_or_create(name="Members")
        self.user = User.objects.create_user(
            username="organizer",
            email="org@test.com",
            password="StrongPass12345!",
        )
        self.client = Client()
        self.client.login(username="organizer", password="StrongPass12345!")

    @patch("events.views.load_recommended_games")
    def test_event_create_includes_recommended_games(self, mock_rec):
        mock_rec.return_value = [
            {"game": create_test_boardgame(bgg_id=99999, title="Test Game"), "bgg_rating": 8.5}
        ]
        response = self.client.get(reverse("events:add_event"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Recommended on BoardGameGeek")


class VenueRecommendedServiceTests(TestCase):
    THING_BATCH_XML = """<?xml version="1.0" encoding="UTF-8"?>
    <items>
      <item type="boardgame" id="88001">
        <name type="primary" value="Catan"/>
        <statistics><ratings>
          <ranks><rank name="boardgame" value="50" bayesaverage="7.5"/></ranks>
        </ratings></statistics>
      </item>
      <item type="boardgame" id="88002">
        <name type="primary" value="Brass"/>
        <statistics><ratings>
          <ranks><rank name="boardgame" value="1" bayesaverage="8.6"/></ranks>
        </ratings></statistics>
      </item>
    </items>"""

    def setUp(self):
        from django.core.cache import cache

        cache.clear()

    @patch("games.services.bgg._get_xml")
    def test_get_top_rated_for_venue(self, mock_get_xml):
        import xml.etree.ElementTree as ET

        from games.services.recommended import get_top_rated_for_venue
        from venues.tests import make_venue

        mock_get_xml.return_value = ET.fromstring(self.THING_BATCH_XML)
        venue = make_venue(name="Test Venue", slug="test-venue-rec")
        create_test_boardgame(bgg_id=88001, title="Catan")
        create_test_boardgame(bgg_id=88002, title="Brass")
        venue.games.set(BoardGame.objects.filter(bgg_id__in=[88001, 88002]))

        top = get_top_rated_for_venue(venue, limit=5)
        self.assertEqual(top[0]["bgg_id"], 88002)

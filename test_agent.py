"""
Test suite for YTGSessionService.

Run with:
    pip install pytest --break-system-packages
    pytest test_session_service.py -v

Assumptions (adjust the import path below if wrong):
- This file assumes YTGSessionService lives in `services/session_services.py`,
  importable as `from services.session_services import YTGSessionService`,
  and that this module does `guardian_services = GuardianServices()` and
  `from models.models import ... GuardianReport` at import time (module-level
  singleton + imported name), matching the code you pasted. Change
  SERVICE_MODULE below if your actual path differs.
- IMPORTANT: mocks are patched at `SERVICE_MODULE.guardian_services` and
  `SERVICE_MODULE.GuardianReport` -- i.e. where those names are *used*
  (session_services.py's own namespace), not where they're *defined*
  (guardian_services.py / models/models.py). Patching the definition site
  doesn't affect a name that was already imported/instantiated elsewhere at
  module-import time -- this bit us in the previous version of this file.
- Guardian, User, GuardianSession, GuardianReport, GuardianType are mocked
  rather than imported for real, since this test focuses on service-layer
  logic (event dedup, timer math, dodging draft), not on schema/migrations.
- Because real SQLAlchemy dirty-tracking on a JSON column can only be proven
  against the real DB/engine, the events-list assertions here check Python-
  level state (did the service produce the correct list contents), and a
  separate NOTE below flags what to verify once you're running against a
  real DB with the MutableList fix applied.
"""

import random
import pytest
from models.models import GuardianType
from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch


SERVICE_MODULE = "services.session_services"  # <-- change if your file/path differs


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def service():
    # Patch the *instance* as it's bound inside session_services.py's own
    # namespace (`guardian_services = GuardianServices()` at import time),
    # not the class in guardian_services.py where it's defined -- patching
    # the definition site is a no-op here since session_services.py already
    # holds its own reference to an already-constructed instance.
    with patch(f"{SERVICE_MODULE}.guardian_services") as mock_guardian_services:
        from services.session_services import YTGSessionService
        svc = YTGSessionService()
        svc._mock_guardian_services = mock_guardian_services  # stash for tests to configure
        yield svc


@pytest.fixture
def mock_session():
    """A fake SQLModel Session that just records calls."""
    return MagicMock()


@pytest.fixture
def mock_guardian():
    g = MagicMock()
    g.id = "guardian_1"
    g.guardian_type = GuardianType.FAMILY  # tests override as needed
    g.owner = MagicMock(name="owner")
    return g


@pytest.fixture
def mock_user():
    u = MagicMock()
    u.id = "user_1"
    u.name = "Julius"
    return u


@pytest.fixture
def session_row():
    """A lightweight stand-in for a GuardianSession row."""
    row = MagicMock()
    row.id = "session_1"
    row.user_id = "user_1"
    row.guardian_id = "guardian_1"
    row.warning_active = False
    row.tracking_start_at = None
    row.target_duration_seconds = 180
    row.points_pending = 0
    row.events = []
    return row


@pytest.fixture
def mock_classifier():
    c = MagicMock()
    c.engine._classify_image.return_value = {
        "summary": "a summary",
        "visible_text": "some text",
        "detailed_description": "details",
        "confidence": 0.9,
        "error": False,
    }
    return c


# ---------------------------------------------------------------------------
# get_or_create
# ---------------------------------------------------------------------------

class TestGetOrCreate:

    def test_returns_existing_session_without_creating_new_row(
        self, service, mock_session, mock_guardian, mock_user, session_row
    ):
        mock_session.exec.return_value.first.return_value = session_row
        result = service.get_or_create(session=mock_session, user=mock_user, guardian=mock_guardian)
        assert result is session_row
        mock_session.add.assert_not_called()

    def test_creates_new_row_when_none_exists(self, service, mock_session, mock_guardian, mock_user):
        mock_session.exec.return_value.first.return_value = None
        result = service.get_or_create(session=mock_session, user=mock_user, guardian=mock_guardian)
        mock_session.add.assert_called_once()
        mock_session.commit.assert_called_once()
        mock_session.refresh.assert_called_once()


# ---------------------------------------------------------------------------
# trigger_warning / start_avoidance_timer (pure state transitions)
# ---------------------------------------------------------------------------

class TestStateTransitions:

    def test_trigger_warning_sets_active_and_clears_timer(self, service, session_row):
        session_row.tracking_start_at = datetime.utcnow()
        service.trigger_warning(session_row)
        assert session_row.warning_active is True
        assert session_row.tracking_start_at is None

    def test_start_avoidance_timer_only_starts_if_warning_active(self, service, session_row):
        session_row.warning_active = False
        service.start_avoidance_timer(session_row)
        assert session_row.tracking_start_at is None

    def test_start_avoidance_timer_sets_start_time_when_warned(self, service, session_row):
        session_row.warning_active = True
        service.start_avoidance_timer(session_row, target_seconds=200)
        assert session_row.tracking_start_at is not None
        assert session_row.target_duration_seconds == 200

    def test_start_avoidance_timer_does_not_restart_already_running_timer(self, service, session_row):
        session_row.warning_active = True
        service.start_avoidance_timer(session_row, target_seconds=200)
        first_start = session_row.tracking_start_at
        service.start_avoidance_timer(session_row, target_seconds=999)
        assert session_row.tracking_start_at == first_start
        assert session_row.target_duration_seconds == 200


# ---------------------------------------------------------------------------
# update_and_check_timer
# ---------------------------------------------------------------------------

class TestUpdateAndCheckTimer:

    def test_no_op_when_not_warning(self, service, mock_session, session_row):
        session_row.warning_active = False
        result = service.update_and_check_timer(session=mock_session, sm_row=session_row)
        assert result is False
        mock_session.commit.assert_not_called()

    def test_no_op_when_timer_not_started(self, service, mock_session, session_row):
        session_row.warning_active = True
        session_row.tracking_start_at = None
        result = service.update_and_check_timer(session=mock_session, sm_row=session_row)
        assert result is False

    def test_does_not_award_before_duration_elapsed(self, service, mock_session, session_row):
        session_row.warning_active = True
        session_row.tracking_start_at = datetime.utcnow() - timedelta(seconds=10)
        session_row.target_duration_seconds = 180
        result = service.update_and_check_timer(session=mock_session, sm_row=session_row)
        assert result is False
        assert session_row.warning_active is True  # still counting down
        assert session_row.points_pending == 0

    def test_awards_points_after_duration_elapsed(self, service, mock_session, session_row):
        session_row.warning_active = True
        session_row.tracking_start_at = datetime.utcnow() - timedelta(seconds=300)
        session_row.target_duration_seconds = 180
        result = service.update_and_check_timer(session=mock_session, sm_row=session_row)
        assert result is True
        assert session_row.warning_active is False
        assert session_row.tracking_start_at is None
        assert session_row.points_pending == 10
        mock_session.commit.assert_called_once()

    def test_uses_wall_clock_not_perf_counter(self, service, mock_session, session_row):
        """Regression guard: timer must be based on datetime, not
        time.perf_counter(), since state now crosses process/request
        boundaries via the DB."""
        session_row.warning_active = True
        session_row.tracking_start_at = datetime.utcnow() - timedelta(seconds=181)
        session_row.target_duration_seconds = 180
        result = service.update_and_check_timer(session=mock_session, sm_row=session_row)
        assert result is True


# ---------------------------------------------------------------------------
# add_event
# ---------------------------------------------------------------------------

class TestAddEvent:

    def test_default_duration_is_randomized_per_call_not_fixed(self, service, mock_session, session_row):
        """Regression guard for the old `default=random.randint(...)` bug,
        which only evaluated once at class-definition time."""
        random.seed(1)
        service.add_event(session=mock_session, sm_row=session_row, content="event A")
        first_duration = session_row.events[0]["time_to_wait"]

        random.seed(2)
        service.add_event(session=mock_session, sm_row=session_row, content="event B")
        second_duration = session_row.events[1]["time_to_wait"]

        assert 140 <= first_duration <= 300
        assert 140 <= second_duration <= 300
        # different seeds should (almost certainly) produce different values
        assert first_duration != second_duration

    def test_explicit_duration_is_respected(self, service, mock_session, session_row):
        service.add_event(session=mock_session, sm_row=session_row, content="event", time_duration=42)
        assert session_row.events[0]["time_to_wait"] == 42

    def test_event_shape(self, service, mock_session, session_row):
        service.add_event(session=mock_session, sm_row=session_row, content="details here")
        event = session_row.events[0]
        assert event["content"] == "details here"
        assert event["should_avoid"] is True
        assert "time_to_wait" in event

    def test_commits_after_adding(self, service, mock_session, session_row):
        service.add_event(session=mock_session, sm_row=session_row, content="x")
        mock_session.commit.assert_called_once()


# ---------------------------------------------------------------------------
# flush_wipe_events
# ---------------------------------------------------------------------------

class TestFlushWipeEvents:

    def test_no_op_on_empty_events(self, service, mock_session, session_row):
        session_row.events = []
        service.flush_wipe_events(session=mock_session, sm_row=session_row)
        mock_session.add.assert_not_called()

    def test_raises_if_guardian_missing(self, service, mock_session, session_row):
        session_row.events = ["some event"]
        mock_session.get.return_value = None
        with pytest.raises(ValueError):
            service.flush_wipe_events(session=mock_session, sm_row=session_row)

    def test_creates_one_report_per_event_and_clears_row(
        self, service, mock_session, session_row, mock_guardian
    ):
        session_row.events = ["event one", "event two", "event three"]
        mock_session.get.return_value = mock_guardian

        with patch(f"{SERVICE_MODULE}.GuardianReport") as MockReport:
            service.flush_wipe_events(session=mock_session, sm_row=session_row)

        assert MockReport.call_count == 3
        assert mock_session.add.call_count == 3
        # regression guard: the row's own events must be cleared, not some
        # unrelated attribute on the service instance
        assert session_row.events == []

    def test_second_flush_after_clear_does_nothing(
        self, service, mock_session, session_row, mock_guardian
    ):
        """Regression guard: previously `self.events = []` cleared the wrong
        object, so a second flush would re-report the same events."""
        session_row.events = ["event one"]
        mock_session.get.return_value = mock_guardian

        with patch(f"{SERVICE_MODULE}.GuardianReport") as MockReport:
            service.flush_wipe_events(session=mock_session, sm_row=session_row)
            assert MockReport.call_count == 1

            MockReport.reset_mock()
            service.flush_wipe_events(session=mock_session, sm_row=session_row)
            MockReport.assert_not_called()

    def test_commits_once_at_the_end(self, service, mock_session, session_row, mock_guardian):
        session_row.events = ["a", "b"]
        mock_session.get.return_value = mock_guardian
        with patch(f"{SERVICE_MODULE}.GuardianReport"):
            service.flush_wipe_events(session=mock_session, sm_row=session_row)
        mock_session.commit.assert_called_once()


# ---------------------------------------------------------------------------
# process_scan
# ---------------------------------------------------------------------------

class TestProcessScan:

    def _configure_guardian_data(self, service, guardian, settings=None, restrictions=None):
        service._mock_guardian_services.get_guardian_data.return_value = (
            {"guardian": guardian, "settings": settings, "restrictions": restrictions},
            "success",
        )

    def test_raises_if_guardian_missing(self, service, mock_session, session_row, mock_classifier):
        service._mock_guardian_services.get_guardian_data.return_value = ({"guardian": None}, "not found")
        with pytest.raises(ValueError):
            service.process_scan(
                session=mock_session, classifer=mock_classifier,
                session_row=session_row, image_bytes=b"fake",
            )

    def test_flagged_content_sets_warning_and_logs_one_event(
        self, service, mock_session, session_row, mock_guardian, mock_user, mock_classifier
    ):
        self._configure_guardian_data(service, mock_guardian)
        mock_session.get.return_value = mock_user
        mock_classifier.overview.return_value = {
            "flagged": True, "category": "gambling", "confidence": 0.8,
            "description": "desc", "source_context": "chrome",
        }
        mock_classifier._breakdown_overview.return_value = "breakdown text"

        result = service.process_scan(
            session=mock_session, classifer=mock_classifier,
            session_row=session_row, image_bytes=b"fake",
        )

        assert result["flagged"] is True
        assert session_row.warning_active is True
        assert len(session_row.events) == 1

    def test_flagged_content_on_consecutive_scans_does_not_duplicate_events(
        self, service, mock_session, session_row, mock_guardian, mock_user, mock_classifier
    ):
        self._configure_guardian_data(service, mock_guardian)
        mock_session.get.return_value = mock_user
        mock_classifier.overview.return_value = {
            "flagged": True, "category": "gambling", "confidence": 0.8,
            "description": "desc", "source_context": "chrome",
        }
        mock_classifier._breakdown_overview.return_value = "breakdown text"

        service.process_scan(session=mock_session, classifer=mock_classifier,
                              session_row=session_row, image_bytes=b"fake")
        service.process_scan(session=mock_session, classifer=mock_classifier,
                              session_row=session_row, image_bytes=b"fake")
        service.process_scan(session=mock_session, classifer=mock_classifier,
                              session_row=session_row, image_bytes=b"fake")

        assert len(session_row.events) == 1

    def test_clearing_after_warning_starts_avoidance_timer(
        self, service, mock_session, session_row, mock_guardian, mock_user, mock_classifier
    ):
        self._configure_guardian_data(service, mock_guardian)
        mock_session.get.return_value = mock_user
        session_row.warning_active = True  # simulate a prior flagged scan

        mock_classifier.overview.return_value = {
            "flagged": False, "category": None, "confidence": 0.1,
            "description": "clean", "source_context": None,
        }

        service.process_scan(session=mock_session, classifer=mock_classifier,
                              session_row=session_row, image_bytes=b"fake")

        assert session_row.tracking_start_at is not None

    def test_clean_scan_with_no_prior_warning_does_nothing(
        self, service, mock_session, session_row, mock_guardian, mock_user, mock_classifier
    ):
        self._configure_guardian_data(service, mock_guardian)
        mock_session.get.return_value = mock_user
        mock_classifier.overview.return_value = {
            "flagged": False, "category": None, "confidence": 0.1,
            "description": "clean", "source_context": None,
        }

        service.process_scan(session=mock_session, classifer=mock_classifier,
                              session_row=session_row, image_bytes=b"fake")

        assert session_row.warning_active is False
        assert session_row.tracking_start_at is None

    def test_individual_account_excludes_name_from_breakdown(
        self, service, mock_session, session_row, mock_guardian, mock_user, mock_classifier
    ):
        mock_guardian.guardian_type = "personal"
        self._configure_guardian_data(service, mock_guardian)
        mock_session.get.return_value = mock_user
        mock_classifier.overview.return_value = {
            "flagged": True, "category": "gambling", "confidence": 0.8,
            "description": "desc", "source_context": "chrome",
        }

        service.process_scan(session=mock_session, classifer=mock_classifier,
                              session_row=session_row, image_bytes=b"fake")

        _, kwargs = mock_classifier._breakdown_overview.call_args
        assert kwargs["include_name"] is False

    def test_family_account_includes_name_in_breakdown(
        self, service, mock_session, session_row, mock_guardian, mock_user, mock_classifier
    ):
        mock_guardian.guardian_type = GuardianType.FAMILY
        self._configure_guardian_data(service, mock_guardian)
        mock_session.get.return_value = mock_user
        mock_classifier.overview.return_value = {
            "flagged": True, "category": "gambling", "confidence": 0.8,
            "description": "desc", "source_context": "chrome",
        }

        service.process_scan(session=mock_session, classifer=mock_classifier,
                              session_row=session_row, image_bytes=b"fake")

        _, kwargs = mock_classifier._breakdown_overview.call_args
        assert kwargs["include_name"] is True


if __name__ == "__main__":
    import sys
    sys.exit(pytest.main([__file__, "-v"]))
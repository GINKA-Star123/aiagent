from datetime import UTC, datetime

from aiagent.presence.models import SessionSnapshot
from aiagent.presence.service import OPENING_COOLDOWN


def test_opening_cooldown_is_ten_minutes():
    snapshot = SessionSnapshot(
        user_id="u1",
        username="tester",
        last_opening_shown_at=datetime.now(UTC),
    )

    assert snapshot.last_opening_shown_at is not None
    assert OPENING_COOLDOWN.total_seconds() == 600
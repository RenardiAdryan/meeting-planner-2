"""App-level tests for app.py using Streamlit's AppTest.

Covers UI behavior only; pure logic.py functions are tested in test_logic.py.
"""

from streamlit.testing.v1 import AppTest


def app_with(cities: list[str]) -> AppTest:
    """Run app.py with the given cities selected in the sidebar."""
    at = AppTest.from_file("app.py", default_timeout=30)
    at.run()
    at.sidebar.multiselect[0].set_value(cities)
    at.run()
    assert not at.exception, at.exception
    return at


def test_warns_when_no_overlap_at_all():
    # Tokyo (UTC+9) and London (UTC+1 in October): working hours never coincide.
    at = app_with(["Tokyo", "London"])
    warnings = [w.value for w in at.warning]
    assert any("Tokyo" in w and "London" in w for w in warnings), warnings


def test_no_warning_when_overlap_exists():
    at = app_with(["London", "Bali"])
    assert [w.value for w in at.warning] == []

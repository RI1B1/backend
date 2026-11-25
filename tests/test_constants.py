import pytest

from app.core.constants import OrderStatus, can_transition, is_final


@pytest.mark.parametrize(
    "old,new",
    [
        ("OPEN", "ACCEPTED"),
        ("OPEN", "CANCELLED"),
        ("ACCEPTED", "ON_THE_WAY"),
        ("ON_THE_WAY", "COMPLETED"),
    ],
)
def test_valid_transitions(old, new):
    assert can_transition(old, new) is True


@pytest.mark.parametrize(
    "old,new",
    [
        ("ACCEPTED", "CANCELLED"),  # pembatalan setelah ACCEPTED bukan MVP (D-023)
        ("OPEN", "COMPLETED"),
        ("OPEN", "ON_THE_WAY"),
        ("ACCEPTED", "COMPLETED"),
        ("COMPLETED", "OPEN"),
        ("CANCELLED", "ACCEPTED"),
        ("OPEN", "OPEN"),
        ("OPEN", "NGAWUR"),
    ],
)
def test_invalid_transitions(old, new):
    assert can_transition(old, new) is False


def test_final_statuses():
    assert is_final(OrderStatus.COMPLETED) and is_final("CANCELLED")
    assert not is_final("OPEN") and not is_final("ON_THE_WAY")

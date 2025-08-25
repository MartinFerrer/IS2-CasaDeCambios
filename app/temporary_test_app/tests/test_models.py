import pytest
from django.core.exceptions import ValidationError
from temporary_test_app.models import ExchangeSimulation


@pytest.mark.django_db
def test_exchange_simulation_create_and_save():
    # Arrange: create a valid instance (values within 1..10)
    sim = ExchangeSimulation(divisa1=6, divisa2=3)

    # Act: save to DB
    sim.full_clean()  # ensures validators pass before saving
    sim.save()

    # Assert: it has an id and persisted values
    assert sim.id is not None
    fetched = ExchangeSimulation.objects.get(pk=sim.id)
    assert fetched.divisa1 == 6
    assert fetched.divisa2 == 3

    # Bonus: verify helper methods follow the 2:1 rule
    assert fetched.comprar_divisa2() == 6  # 2 * divisa2 (2 * 3)
    assert fetched.vender_divisa1() == 3   # divisa1 / 2 (6 / 2)


@pytest.mark.django_db
@pytest.mark.parametrize(
    "divisa1,divisa2",
    [
        (0, 5),   # divisa1 below min
        (11, 5),  # divisa1 above max
        (5, 0),   # divisa2 below min
        (5, 11),  # divisa2 above max
    ],
)
def test_exchange_simulation_validation_limits(divisa1, divisa2):
    sim = ExchangeSimulation(divisa1=divisa1, divisa2=divisa2)
    with pytest.raises(ValidationError):
        sim.full_clean()
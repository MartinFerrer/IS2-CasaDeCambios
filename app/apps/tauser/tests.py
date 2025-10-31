import pytest
from model_bakery import baker


@pytest.mark.django_db
def test_tauser_str():
	tauser = baker.make('tauser.Tauser', nombre='Central')
	assert str(tauser) == 'Central'


@pytest.mark.django_db
def test_no_permite_nombres_duplicados():
	# Crear un tauser con un nombre
	baker.make('tauser.Tauser', nombre='Sucursal A')

	# Intentar crear otro con el mismo nombre debe fallar por restricción de unicidad
	with pytest.raises(Exception):
		baker.make('tauser.Tauser', nombre='Sucursal A')

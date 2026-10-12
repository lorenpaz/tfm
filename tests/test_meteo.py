import math

from meteo import classify_weather, dms_to_decimal, haversine_km


def test_dms_to_decimal_aemet_inventory_format():
    assert math.isclose(dms_to_decimal("364000N"), 36 + 40 / 60)
    assert math.isclose(dms_to_decimal("042900W"), -(4 + 29 / 60))
    assert math.isclose(dms_to_decimal("0042900W"), -(4 + 29 / 60))   # grados con 3 cifras
    assert math.isclose(dms_to_decimal("282826S"), -(28 + 28 / 60 + 26 / 3600))


def test_dms_to_decimal_invalid():
    assert dms_to_decimal(None) is None
    assert dms_to_decimal("36.67") is None
    assert dms_to_decimal("366000N") is None   # 60 minutos no es válido


def test_haversine_malaga_airport():
    # Centro de Málaga - aeropuerto: unos 8 km
    assert 6 < haversine_km(36.7213, -4.4214, 36.6667, -4.4833) < 10


def test_classify_weather_priority():
    assert classify_weather(prec=0.2, hr=99) == "rain"
    assert classify_weather(prec=0, vis=500) == "fog"
    assert classify_weather(prec=0, wind=12, hr=90) == "windy"
    assert classify_weather(prec=0, hr=88) == "cloudy"
    assert classify_weather(prec=0, hr=50, nub=2) == "sunny"
    assert classify_weather(prec=float("nan"), hr=float("nan")) == "sunny"

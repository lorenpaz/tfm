from datetime import date, datetime

from tiempo import (
    day_type,
    illumination,
    load_holidays,
    parse_timestamp_from_name,
    solar_elevation,
    time_slot_2h,
    to_local,
)

MALAGA = (36.7213, -4.4214)


def test_parse_utc_name():
    assert parse_timestamp_from_name("20260825T144834Z.jpg") == datetime(2026, 8, 25, 14, 48, 34)


def test_parse_utc_name_with_camera_prefix():
    # Nombres de las imágenes copiadas a los lotes de CVAT: <camara>_<timestamp>.jpg
    assert parse_timestamp_from_name("21547_20260825T144834Z.jpg") == datetime(2026, 8, 25, 14, 48, 34)


def test_parse_invalid_names():
    assert parse_timestamp_from_name("foto.jpg") is None
    assert parse_timestamp_from_name("20261345T999999Z.jpg") is None


def test_to_local_handles_dst():
    assert to_local(datetime(2026, 8, 25, 14, 48, 34)) == datetime(2026, 8, 25, 16, 48, 34)
    assert to_local(datetime(2026, 1, 15, 9, 0, 0)) == datetime(2026, 1, 15, 10, 0, 0)
    assert to_local(None) is None


def test_time_slot_and_day_type():
    holidays = {date(2026, 9, 8)}
    assert time_slot_2h(datetime(2026, 8, 25, 16, 48)) == "16:00-18:00"
    assert time_slot_2h(datetime(2026, 8, 25, 23, 10)) == "22:00-00:00"
    assert time_slot_2h(None) == "unknown"
    assert day_type(datetime(2026, 9, 8, 12), holidays) == "festivo"
    assert day_type(datetime(2026, 9, 5, 12), holidays) == "fin_de_semana"
    assert day_type(datetime(2026, 9, 7, 12), holidays) == "laborable"


def test_load_holidays(tmp_path):
    csv_file = tmp_path / "festivos.csv"
    csv_file.write_text("﻿Fecha,Festividad\n2026-09-08,Virgen de la Victoria\n15/08/2026,Asunción\n", encoding="utf-8")
    assert load_holidays(csv_file) == {date(2026, 9, 8), date(2026, 8, 15)}
    assert load_holidays(tmp_path / "no_existe.csv") == set()


def test_solar_elevation_and_illumination():
    # Mediodía solar de verano en Málaga: sol muy alto; medianoche: bajo el horizonte
    assert solar_elevation(datetime(2026, 6, 21, 12, 15), *MALAGA) > 70
    assert solar_elevation(datetime(2026, 6, 21, 0, 0), *MALAGA) < -20
    assert illumination(datetime(2026, 8, 25, 12, 0), *MALAGA) == "dia"
    assert illumination(datetime(2026, 8, 25, 23, 0), *MALAGA) == "noche"
    assert illumination(None, *MALAGA) == "unknown"

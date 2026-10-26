from datetime import datetime, timedelta

from estado_vehiculos import box_zone, classify_state, iou, point_in_polygon, track_vehicles

SQUARE = [(0.0, 0.0), (0.5, 0.0), (0.5, 0.5), (0.0, 0.5)]
ZONES = {
    "zona_espera": [[(0.0, 0.5), (1.0, 0.5), (1.0, 1.0), (0.0, 1.0)]],          # mitad inferior
    "zona_aparcamiento": [[(0.8, 0.5), (1.0, 0.5), (1.0, 1.0), (0.8, 1.0)]],    # franja derecha
    "paso_peatones": [[(0.0, 0.3), (1.0, 0.3), (1.0, 0.5), (0.0, 0.5)]],        # franja central
}
T0 = datetime(2026, 10, 17, 11, 0, 0)


def test_point_in_polygon():
    assert point_in_polygon(0.25, 0.25, SQUARE)
    assert not point_in_polygon(0.75, 0.25, SQUARE)
    assert not point_in_polygon(0.25, 0.75, SQUARE)


def test_box_zone_uses_bottom_center_and_parking_wins():
    # Imagen 640x480; caja en la mitad inferior izquierda -> espera
    assert box_zone([100, 300, 200, 400], 640, 480, ZONES) == "zona_espera"
    # Caja cuyo punto inferior central cae en la franja derecha -> aparcamiento (prioritario)
    assert box_zone([560, 300, 620, 400], 640, 480, ZONES) == "zona_aparcamiento"
    # Caja en la mitad superior -> fuera de zonas
    assert box_zone([100, 10, 200, 100], 640, 480, ZONES) is None
    assert box_zone([100, 300, 200, 400], 640, 480, {}) is None


def test_vehicle_on_crosswalk_is_not_waiting():
    # Punto inferior central en la franja del paso de peatones (y = 0.4)
    zone = box_zone([100, 150, 200, 192], 640, 480, ZONES)
    assert zone == "paso_peatones"
    assert classify_state(zone, True, 30) == "circulando"
    assert classify_state(zone, True, 400) == "aparcado"


def test_iou():
    assert iou([0, 0, 10, 10], [0, 0, 10, 10]) == 1.0
    assert iou([0, 0, 10, 10], [20, 20, 30, 30]) == 0.0
    assert abs(iou([0, 0, 10, 10], [5, 0, 15, 10]) - 1 / 3) < 1e-9


def test_track_parked_vehicle_accumulates_still_time():
    parked = [100, 300, 160, 340]
    frames = [(T0 + timedelta(seconds=6 * k), [parked]) for k in range(60)]   # 6 minutos inmóvil
    tracks = track_vehicles(frames)
    last = tracks[-1][0]
    assert {t[0]["track"] for t in tracks} == {0}            # siempre el mismo vehículo
    assert last["detenido"]
    assert (frames[-1][0] - last["inmovil_desde"]).total_seconds() == 354
    assert classify_state(None, last["detenido"], 354) == "aparcado"


def test_track_moving_vehicle_resets_still_time():
    frames = [(T0 + timedelta(seconds=6 * k), [[100 + 15 * k, 300, 160 + 15 * k, 340]]) for k in range(4)]
    tracks = track_vehicles(frames)
    assert {t[0]["track"] for t in tracks} == {0}            # se sigue al vehículo aunque avance
    assert not tracks[-1][0]["detenido"]
    assert tracks[-1][0]["inmovil_desde"] == frames[-1][0]


def test_gap_breaks_tracks():
    box = [100, 300, 160, 340]
    frames = [(T0, [box]), (T0 + timedelta(seconds=60), [box])]   # 60 s > max_gap_s
    tracks = track_vehicles(frames, max_gap_s=15)
    assert tracks[0][0]["track"] != tracks[1][0]["track"]
    assert tracks[1][0]["inmovil_desde"] == T0 + timedelta(seconds=60)


def test_classify_state():
    assert classify_state("zona_aparcamiento", False, 0) == "aparcado"
    assert classify_state("zona_espera", True, 30) == "esperando"
    assert classify_state("zona_espera", True, 600) == "aparcado"       # demasiado tiempo inmóvil
    assert classify_state("zona_espera", False, 0) == "circulando"
    assert classify_state(None, True, 30) == "circulando"


def test_continuous_sequences_keeps_only_close_images():
    import pandas as pd
    from estado_vehiculos import continuous_sequences

    ts = [T0, T0 + timedelta(seconds=6), T0 + timedelta(seconds=12), T0 + timedelta(seconds=72)]
    df = pd.DataFrame({"camera": ["A"] * 4 + ["B"], "image": list("abcde"),
                       "timestamp": ts + [T0 + timedelta(seconds=3)]})
    seq = continuous_sequences(df, max_gap_s=15)
    # La imagen a 60 s de la anterior y la única de la cámara B quedan fuera
    assert seq["image"].tolist() == ["a", "b", "c"]

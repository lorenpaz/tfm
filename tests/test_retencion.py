from datetime import datetime, timedelta

import pandas as pd

from retencion import classify_images, grid_representatives, in_windows

T0 = datetime(2026, 10, 1, 10, 0, 0)          # UTC
CFG = {"franja_min": 10, "dias_gracia": 7, "ventanas_evaluacion": []}
NOW = datetime(2026, 10, 26, 12, 0, 0)


def images(*offsets_s, camera="21547"):
    ts = [T0 + timedelta(seconds=s) for s in offsets_s]
    return pd.DataFrame({"camera": camera, "image": [t.strftime("%Y%m%dT%H%M%SZ.jpg") for t in ts], "timestamp": ts})


def test_grid_keeps_best_quality_per_slot():
    imgs = images(0, 60, 120, 600)                # tres en la franja 10:00, una en 10:10
    frames = imgs.assign(quality_score=[0.2, 0.9, 0.5, 0.1])
    reps = grid_representatives(imgs, frames, 10)
    assert reps == {("21547", imgs.image[1]), ("21547", imgs.image[3])}


def test_grid_without_valid_frames_keeps_first_image():
    imgs = images(30, 90)
    reps = grid_representatives(imgs, pd.DataFrame(columns=["camera", "image", "quality_score"]), 10)
    assert reps == {("21547", imgs.image[0])}


def test_grid_slots_are_per_camera():
    imgs = pd.concat([images(0, camera="A"), images(5, camera="B")], ignore_index=True)
    assert len(grid_representatives(imgs, imgs.assign(quality_score=0.5), 10)) == 2


def test_in_windows_inclusive():
    dates = ["2026-10-30", "2026-10-31", "2026-11-03", "2026-11-04"]
    assert in_windows(dates, [["2026-10-31", "2026-11-03"]]).tolist() == [False, True, True, False]
    assert not in_windows(dates, []).any()


def test_classify_order_of_reasons():
    imgs = images(0, 60, 120, 180, 240)
    k = list(zip(imgs.camera, imgs.image))
    frames = imgs.assign(quality_score=[0.9, 0.8, 0.7, 0.6, 0.5])
    detected = set(k) - {k[3]}                    # 02c no pudo leer la cuarta
    out = classify_images(imgs, frames, detected, lote_keys={k[2]}, pending_06=set(),
                          now=NOW, processed_until=NOW, cfg=CFG)
    assert out["motivo"].tolist() == ["rejilla", "redundante", "en_lote", "ilegible", "redundante"]
    assert out["accion"].tolist() == ["conservar", "borrar", "conservar", "borrar", "borrar"]


def test_recent_pending_and_window_are_kept():
    imgs = images(0, 60, 120, 180)
    k = list(zip(imgs.camera, imgs.image))
    frames = imgs.assign(quality_score=[0.9, 0.1, 0.1, 0.1])
    # Reciente: "ahora" a 3 días de las imágenes
    out = classify_images(imgs, frames, set(k), set(), set(), now=T0 + timedelta(days=3),
                          processed_until=NOW, cfg=CFG)
    assert set(out["motivo"]) == {"reciente"}
    # Posteriores a la última ejecución de 02 y pendientes de 06
    out = classify_images(imgs, frames, set(k), set(), {k[1]}, now=NOW,
                          processed_until=T0 + timedelta(seconds=90), cfg=CFG)
    assert out["motivo"].tolist() == ["rejilla", "pendiente_06", "pendiente_02", "pendiente_02"]
    # Ventana de evaluación (fecha local de Madrid)
    out = classify_images(imgs, frames, set(k), set(), set(), now=NOW, processed_until=NOW,
                          cfg={**CFG, "ventanas_evaluacion": [["2026-10-01", "2026-10-01"]]})
    assert out["motivo"].tolist() == ["rejilla", "ventana", "ventana", "ventana"]

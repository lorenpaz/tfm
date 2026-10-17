import pandas as pd

from pipeline import stratified_selection
from priorizacion import greedy_balanced_selection

T0 = pd.Timestamp("2026-10-17 11:00:00")


def burst(camera, n, every_s, start=T0):
    """n imágenes de una cámara cada `every_s` segundos (como la captura a 6 s)."""
    return pd.DataFrame({
        "camera": camera,
        "image": [f"{camera}_{i}.jpg" for i in range(n)],
        "timestamp": [start + pd.Timedelta(seconds=every_s * i) for i in range(n)],
        "time_slot_2h": "12:00-14:00",
    })


def min_gap_per_camera(selection):
    gaps = selection.sort_values("timestamp").groupby("camera")["timestamp"].diff().dt.total_seconds()
    return gaps.min()


def test_stratified_selection_respects_min_gap():
    # Una hora de imágenes cada 6 s de dos cámaras: sin separación saldrían casi-duplicados
    df = pd.concat([burst("A", 600, 6), burst("B", 600, 6)], ignore_index=True)
    sel = stratified_selection(df, ["camera", "time_slot_2h"], n=20, max_per_camera=20, seed=1, min_gap_s=600)
    assert min_gap_per_camera(sel) >= 600
    # En una hora con 10 min de separación caben como mucho 6-7 imágenes por cámara
    assert sel.groupby("camera").size().max() <= 7


def test_stratified_selection_without_gap_keeps_previous_behaviour():
    df = burst("A", 100, 6)
    sel = stratified_selection(df, ["camera"], n=30, max_per_camera=50, seed=1)
    assert len(sel) == 30


def test_greedy_selection_respects_min_gap():
    df = pd.concat([burst("A", 300, 6), burst("B", 300, 6)], ignore_index=True)
    # Todas las imágenes igual de valiosas: el algoritmo tendería a elegir casi-duplicados
    counts = pd.DataFrame({"semaforo": [1] * len(df), "pedestrian": [2] * len(df)})
    sel, _ = greedy_balanced_selection(df, counts, n=50, max_per_camera=50, min_gap_s=600)
    assert min_gap_per_camera(sel) >= 600
    assert len(sel) <= 2 * 4      # 30 minutos por cámara -> como mucho 3-4 imágenes cada una
    assert list(sel["prioridad"]) == list(range(1, len(sel) + 1))

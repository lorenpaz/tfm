import pytest

from anotacion import find_label_files, read_export_names, remap_lines

CLASS_TO_IDX = {"pedestrian": 0, "car": 1, "traffic_light_red": 5, "pedestrian_light_green": 10}


def test_remap_by_name_not_by_index():
    # En CVAT el orden de etiquetas es distinto: 0=car, 1=pedestrian_light_green, 2=pedestrian
    export_names = ["car", "pedestrian_light_green", "pedestrian"]
    lines = ["0 0.5 0.5 0.1 0.2", "1 0.1 0.1 0.05 0.05", "2 0.3 0.3 0.1 0.3"]
    assert remap_lines(lines, export_names, CLASS_TO_IDX) == [
        "1 0.5 0.5 0.1 0.2",
        "10 0.1 0.1 0.05 0.05",
        "0 0.3 0.3 0.1 0.3",
    ]


def test_remap_skips_malformed_lines():
    assert remap_lines(["", "0 0.5 0.5", "0 0.5 0.5 0.1 0.1"], ["pedestrian"], CLASS_TO_IDX) == ["0 0.5 0.5 0.1 0.1"]


def test_remap_unknown_class_fails_loudly():
    with pytest.raises(ValueError, match="bicycle"):
        remap_lines(["0 0.5 0.5 0.1 0.1"], ["bicycle"], CLASS_TO_IDX)


def test_read_yolo11_export(tmp_path):
    (tmp_path / "obj.names").write_text("car\npedestrian\n", encoding="utf-8")
    (tmp_path / "train.txt").write_text("obj_train_data/a.jpg\n", encoding="utf-8")
    (tmp_path / "obj_train_data").mkdir()
    (tmp_path / "obj_train_data" / "21547_20260825T144834Z.txt").write_text("1 0.5 0.5 0.1 0.1", encoding="utf-8")

    assert read_export_names(tmp_path) == ["car", "pedestrian"]
    # train.txt (en la raíz) no es un fichero de etiquetas
    assert list(find_label_files(tmp_path)) == ["21547_20260825T144834Z"]


def test_read_ultralytics_export(tmp_path):
    pytest.importorskip("yaml")
    (tmp_path / "data.yaml").write_text("names:\n  0: car\n  1: pedestrian\n", encoding="utf-8")
    assert read_export_names(tmp_path) == ["car", "pedestrian"]


def test_read_export_without_names(tmp_path):
    with pytest.raises(FileNotFoundError):
        read_export_names(tmp_path)

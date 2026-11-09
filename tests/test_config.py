from config import get_secret


def test_get_secret_from_env_file(tmp_path, monkeypatch):
    monkeypatch.delenv("CLAVE_PRUEBA", raising=False)
    env_file = tmp_path / ".env"
    env_file.write_text("# comentario\nOTRA=1\nCLAVE_PRUEBA = \"abc.def=\"\n", encoding="utf-8")
    assert get_secret("CLAVE_PRUEBA", env_file) == "abc.def="


def test_environment_variable_takes_precedence(tmp_path, monkeypatch):
    env_file = tmp_path / ".env"
    env_file.write_text("CLAVE_PRUEBA=del_fichero\n", encoding="utf-8")
    monkeypatch.setenv("CLAVE_PRUEBA", "del_entorno")
    assert get_secret("CLAVE_PRUEBA", env_file) == "del_entorno"


def test_missing_secret_returns_empty(tmp_path, monkeypatch):
    monkeypatch.delenv("CLAVE_PRUEBA", raising=False)
    assert get_secret("CLAVE_PRUEBA", tmp_path / "no_existe.env") == ""


def test_relative_does_not_follow_junctions(tmp_path, monkeypatch):
    # raw/ es un junction a una carpeta fuera de OneDrive: la ruta guardada debe seguir siendo la del proyecto
    import sys

    import pytest

    import config

    if sys.platform != "win32":
        pytest.skip("los junctions solo existen en Windows")
    import _winapi

    project, outside = tmp_path / "proyecto", tmp_path / "fuera"
    (project / "data").mkdir(parents=True)
    (outside / "21547").mkdir(parents=True)
    _winapi.CreateJunction(str(outside), str(project / "data" / "raw"))
    monkeypatch.setattr(config, "PROJECT_ROOT", project)
    image = project / "data" / "raw" / "21547" / "20261026T120000Z.jpg"
    image.write_bytes(b"jpg")
    assert config.relative(image) == "data/raw/21547/20261026T120000Z.jpg"

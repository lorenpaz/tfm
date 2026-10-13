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

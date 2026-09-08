"""Never use a developer's OS preferences or credential vault in repo tests."""
import os

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("QT_QUICK_BACKEND", "software")
# Child-process checks must not discover a real platform keyring either.
os.environ["PYTHON_KEYRING_BACKEND"] = "keyring.backends.null.Keyring"

try:
    from PySide6 import QtCore
except ImportError:
    QtCore = None

if QtCore is not None:
    _NativeSettings = QtCore.QSettings

    class IsolatedSettings(_NativeSettings):
        def __init__(self, *args, **kwargs):
            # Qt's explicit organization/application overload can choose
            # NativeFormat despite setDefaultFormat on Windows. Keep every
            # real QSettings read/write, but explicitly select the test INI.
            if len(args) >= 2 and isinstance(args[0], str) and isinstance(args[1], str):
                super().__init__(_NativeSettings.IniFormat, _NativeSettings.UserScope, *args, **kwargs)
            else:
                super().__init__(*args, **kwargs)

    QtCore.QSettings = IsolatedSettings


@pytest.fixture(autouse=True)
def isolate_desktop_preferences_and_secrets(tmp_path, monkeypatch):
    if QtCore is not None:
        QtCore.QSettings.setDefaultFormat(QtCore.QSettings.IniFormat)
        for scope in (QtCore.QSettings.UserScope, QtCore.QSettings.SystemScope):
            QtCore.QSettings.setPath(QtCore.QSettings.IniFormat, scope, str(tmp_path / "os-settings"))
    try:
        import keyring
    except ImportError:
        return
    values = {}
    monkeypatch.setattr(keyring, "get_password", lambda service, user: values.get((service, user)))
    monkeypatch.setattr(keyring, "set_password", lambda service, user, value: values.__setitem__((service, user), value))
    monkeypatch.setattr(keyring, "delete_password", lambda service, user: values.pop((service, user), None))

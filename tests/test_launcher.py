import importlib.util
from pathlib import Path
import subprocess

spec = importlib.util.spec_from_file_location('launcher', Path(__file__).parents[1] / 'scripts/run_local.py')
launcher = importlib.util.module_from_spec(spec)
spec.loader.exec_module(launcher)


def test_incomplete_environment_preserved_and_rebuilt(tmp_path, monkeypatch):
    env = tmp_path / '.venv'
    env.mkdir()
    (env / 'marker').write_text('old environment')
    database = tmp_path / 'errandloop-groups.sqlite3'
    database.write_bytes(b'preserve user data')
    monkeypatch.setattr(launcher, 'ROOT', tmp_path)
    monkeypatch.setattr(launcher, 'ENV', env)
    monkeypatch.setattr(launcher, 'PYTHON', env / 'bin/python')
    monkeypatch.setattr(launcher, 'works', lambda *args: False)
    monkeypatch.setattr(launcher.sys, 'argv', ['run_local.py', '--port', '8001'])
    calls = []
    monkeypatch.setattr(launcher.subprocess, 'run', lambda cmd, **kw: calls.append(cmd))
    monkeypatch.setattr(launcher.subprocess, 'call', lambda cmd, **kw: calls.append(cmd) or 0)
    assert launcher.main() == 0
    assert next(tmp_path.glob('.venv-backup-*/marker')).read_text() == 'old environment'
    assert database.read_bytes() == b'preserve user data'
    assert calls[0][1:3] == ['-m', 'venv']
    assert '--force-reinstall' in calls[1]
    assert calls[-1][-2:] == ['--port', '8001']


def test_healthy_environment_starts_without_network_install(monkeypatch):
    monkeypatch.setattr(launcher, 'works', lambda *args: True)
    monkeypatch.setattr(launcher.sys, 'argv', ['run_local.py'])
    def unexpected(*args, **kwargs):
        raise AssertionError('Healthy startup should not reinstall dependencies')
    monkeypatch.setattr(launcher.subprocess, 'run', unexpected)
    monkeypatch.setattr(launcher.subprocess, 'call', lambda *args, **kwargs: 0)
    assert launcher.main() == 0

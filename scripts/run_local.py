"""Start the local app, repairing incomplete dependency environments safely."""
import argparse
from datetime import datetime
import os
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
ENV = ROOT / '.venv'
PYTHON = ENV / ('Scripts/python.exe' if os.name == 'nt' else 'bin/python')


def works(*args):
    try:
        return subprocess.run([str(PYTHON), *args], cwd=ROOT,
                              stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL).returncode == 0
    except OSError:
        return False


def main():
    parser = argparse.ArgumentParser(description='Start ErrandLoop locally')
    parser.add_argument('--port', type=int, default=8000)
    parser.add_argument('--demo', action='store_true')
    args = parser.parse_args()
    if sys.version_info < (3, 10):
        raise RuntimeError('Install Python 3.12 or newer, then run start.bat again.')
    if not works('-m', 'pip', '--version'):
        if ENV.exists():
            backup = ROOT / ('.venv-backup-' + datetime.now().strftime('%Y%m%d-%H%M%S-%f'))
            ENV.rename(backup)
            print('Preserved the incomplete Python environment as ' + backup.name, flush=True)
        print('Creating a fresh Python environment. Please let this finish.', flush=True)
        subprocess.run([sys.executable, '-m', 'venv', str(ENV)], cwd=ROOT, check=True)
    if not works('-c', "import cedarpy; from importlib.metadata import version; assert version('cedarpy') == '4.12.0'"):
        print('Installing the Cedar engine. Internet is needed for this step.', flush=True)
        subprocess.run([str(PYTHON), '-m', 'pip', 'install', '--force-reinstall',
                        '-r', str(ROOT / 'requirements.txt')], cwd=ROOT, check=True)
    command = [str(PYTHON), '-m', 'app.server', '--open', '--port', str(args.port)]
    if args.demo:
        command.append('--demo')
    return subprocess.call(command, cwd=ROOT)


if __name__ == '__main__':
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print('\nStopped. Your saved groups are unchanged.')
    except (OSError, RuntimeError, subprocess.CalledProcessError) as error:
        print('\nErrandLoop could not start: ' + str(error), file=sys.stderr)
        print('Keep this message and share it for troubleshooting. Group data was not deleted.', file=sys.stderr)
        sys.exit(1)

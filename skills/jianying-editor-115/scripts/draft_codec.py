"""Plain JSON / encrypted Jianying draft I/O; native calls isolated in a worker."""
import base64
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile

MAX_BYTES = 64 * 1024 * 1024


class DraftError(ValueError):
    pass


def json_object(raw):
    try:
        value = json.loads(raw.decode('utf-8-sig'))
    except (ValueError, UnicodeError) as error:
        raise DraftError('Invalid JSON; original file was not changed') from error
    if not isinstance(value, dict):
        raise DraftError('Draft must contain a JSON object')
    return value


def detect(raw):
    if not raw or len(raw) > MAX_BYTES:
        raise DraftError('Empty or oversized draft')
    text = raw.decode('utf-8-sig', errors='strict').strip()
    if text.startswith(('{', '[')):
        json_object(raw)  # malformed plaintext is not treated as encrypted
        return 'plain'
    try:
        payload = base64.b64decode(''.join(text.split()), validate=True)
    except (ValueError, UnicodeError) as error:
        raise DraftError('Unknown draft encoding') from error
    if not payload:
        raise DraftError('Empty Base64 payload')
    # Base64 is a container, not a decryption algorithm.
    try:
        json_object(payload)
        return 'base64-json'
    except DraftError:
        return 'encrypted-candidate'


def native_transform(raw, mode, install_dir=None):
    directory = install_dir or os.environ.get('JY_INSTALL_DIR')
    if not directory:
        raise DraftError('Encrypted draft: specify JY_INSTALL_DIR containing videoeditor.dll')
    if sys.platform != 'win32':
        raise DraftError('Encrypted draft native codec requires Windows x64')
    worker = Path(__file__).with_name('native_worker.py')
    with tempfile.TemporaryDirectory(prefix='jy-codec-') as temporary:
        source = Path(temporary) / 'input.bin'
        target = Path(temporary) / 'output.bin'
        source.write_bytes(raw)
        try:
            result = subprocess.run([sys.executable, str(worker), mode, str(source), str(target), '--install-dir', str(Path(directory).resolve())], capture_output=True, timeout=45, creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
        except subprocess.TimeoutExpired as error:
            raise DraftError('Native codec timed out; original draft was not changed') from error
        if result.returncode or not target.is_file():
            details = result.stderr.decode('utf-8', errors='replace')[-1200:]
            raise DraftError(f'Native codec failed ({result.returncode}): {details}')
        if target.stat().st_size > MAX_BYTES:
            raise DraftError('Native output exceeds limit')
        return target.read_bytes()


def decode(raw, install_dir=None):
    kind = detect(raw)
    if kind == 'plain':
        return json_object(raw)
    if kind == 'base64-json':
        return json_object(base64.b64decode(''.join(raw.decode('utf-8-sig').split()), validate=True))
    return json_object(native_transform(raw, 'decrypt', install_dir))


def read_json(path, install_dir=None):
    path = Path(path)
    if path.stat().st_size > MAX_BYTES:
        raise DraftError('Draft exceeds 64 MiB limit')
    return decode(path.read_bytes(), install_dir)


def encode(data, kind='plain', install_dir=None):
    raw = json.dumps(data, ensure_ascii=False, separators=(',', ':'), allow_nan=False).encode('utf-8')
    json_object(raw)
    if kind == 'plain':
        return raw
    if kind == 'base64-json':
        return base64.b64encode(raw)
    if kind == 'encrypted-candidate':
        result = native_transform(raw, 'encrypt', install_dir)
        if decode(result, install_dir) != data:
            raise DraftError('Encrypted JSON roundtrip mismatch')
        return result
    raise DraftError('Unsupported target encoding')

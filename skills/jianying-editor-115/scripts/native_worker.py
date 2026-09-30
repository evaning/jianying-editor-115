"""One-shot Windows x64 Jianying codec worker. Never import in a long-lived host.

MSVC string ABI and exported entry points adapted from wenshui330/jy-draftc
(MIT, see references/LICENSE-jy-draftc.txt). Uses only the user's installed DLL.
DLL-owned output buffers are reclaimed by process exit, not a foreign CRT free.
"""
import argparse
import ctypes as C
import json
import os
from pathlib import Path
import sys

MAX_BYTES = 64 * 1024 * 1024
DEC = '?decrypt@EncryptUtils@lvve@@QEAA?AV?$basic_string@DU?$char_traits@D@std@@V?$allocator@D@2@@std@@AEBV34@0AEA_N@Z'
ENC = '?encrypt@EncryptUtils@lvve@@QEAA?AV?$basic_string@DU?$char_traits@D@std@@V?$allocator@D@2@@std@@AEBV34@@Z'
ENABLE = '?enable@EncryptUtils@lvve@@QEAAX_N@Z'


class Storage(C.Union):
    _fields_ = [('small', C.c_char * 16), ('ptr', C.c_void_p)]


class MsvcString(C.Structure):
    _fields_ = [('data', Storage), ('size', C.c_uint64), ('capacity', C.c_uint64)]


def argument(raw):
    value = MsvcString()
    value.size = len(raw)
    value.capacity = max(15, len(raw))
    buffer = C.create_string_buffer(raw)
    if len(raw) < 16:
        C.memmove(C.addressof(value), buffer, len(raw))
    else:
        value.data.ptr = C.addressof(buffer)
    return value, buffer  # retain buffer for the native call


def take(value):
    if value.size > MAX_BYTES or value.size > value.capacity:
        raise ValueError('Native output size invalid')
    address = C.addressof(value) if value.capacity < 16 else value.data.ptr
    if not address or not value.size:
        raise ValueError('Native output empty')
    return C.string_at(address, value.size)


def require_object(raw):
    obj = json.loads(raw.decode('utf-8-sig'))
    if not isinstance(obj, dict):
        raise ValueError('Expected a JSON object')
    return obj


class NativeCodec:
    def __init__(self, install_dir):
        if sys.platform != 'win32' or C.sizeof(C.c_void_p) != 8:
            raise RuntimeError('Native codec requires Windows x64 Python')
        directory = Path(install_dir).resolve(strict=True)
        dll_path = directory / 'videoeditor.dll'
        if not dll_path.is_file():
            raise FileNotFoundError('videoeditor.dll missing in selected version directory')
        kernel = C.WinDLL('kernel32', use_last_error=True)
        kernel.SetErrorMode(0x0001 | 0x8000)
        os.environ['PATH'] = str(directory) + os.pathsep + os.environ.get('PATH', '')
        os.chdir(directory)
        self.dll_directory = os.add_dll_directory(str(directory))
        self.dll = C.CDLL(str(dll_path), winmode=0x100 | 0x400 | 0x800)
        self.dec = getattr(self.dll, DEC)
        self.dec.argtypes = [C.c_void_p, C.POINTER(MsvcString), C.POINTER(MsvcString), C.POINTER(MsvcString), C.POINTER(C.c_bool)]
        self.dec.restype = C.POINTER(MsvcString)
        self.enc = getattr(self.dll, ENC)
        self.enc.argtypes = [C.c_void_p, C.POINTER(MsvcString), C.POINTER(MsvcString)]
        self.enc.restype = C.POINTER(MsvcString)
        self.enable = getattr(self.dll, ENABLE)
        self.enable.argtypes = [C.c_void_p, C.c_bool]
        self.enable.restype = None

    def decrypt(self, raw):
        value, keeper = argument(raw)
        params, params_keeper = argument(b'{}')
        output = MsvcString()
        output.capacity = 15
        ok = C.c_bool(False)
        self.dec(None, C.byref(output), C.byref(value), C.byref(params), C.byref(ok))
        if not ok.value:
            raise ValueError('Native decrypt rejected this input')
        result = take(output)
        require_object(result)
        return result

    def encrypt(self, raw):
        require_object(raw)
        value, keeper = argument(raw)
        output = MsvcString()
        output.capacity = 15
        self.enable(None, True)
        self.enc(None, C.byref(output), C.byref(value))
        result = take(output)
        if result == raw or result.lstrip().startswith(b'{'):
            raise ValueError('Native encrypt returned plaintext')
        if self.decrypt(result) != raw:
            raise ValueError('Native encrypt/decrypt byte roundtrip failed')
        return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('mode', choices=['decrypt', 'encrypt'])
    parser.add_argument('input')
    parser.add_argument('output')
    parser.add_argument('--install-dir', required=True)
    args = parser.parse_args()
    source = Path(args.input).resolve(strict=True)
    target = Path(args.output).absolute()
    if target.exists() or source == target:
        raise FileExistsError('Worker never overwrites an existing file')
    if source.stat().st_size > MAX_BYTES:
        raise ValueError('Input exceeds 64 MiB limit')
    raw = source.read_bytes()
    codec = NativeCodec(args.install_dir)
    result = getattr(codec, args.mode)(raw)
    with target.open('xb') as stream:
        stream.write(result)
    print(json.dumps({'ok': True, 'bytes': len(result)}), flush=True)


if __name__ == '__main__':
    try:
        main()
    except Exception as error:
        print(json.dumps({'ok': False, 'error': str(error)}), file=sys.stderr, flush=True)
        sys.exit(1)

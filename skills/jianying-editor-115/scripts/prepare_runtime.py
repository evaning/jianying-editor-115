"""Prepare a new full runtime from a reviewed, clean upstream checkout."""
import argparse
import os
from pathlib import Path
import shutil
import subprocess
import tempfile

PIN = '32c56928ded4f9e2c2b80e099dc7abb793d2c30b'


def git(*args, cwd):
    return subprocess.run(['git', *args], cwd=cwd, check=True, capture_output=True, text=True).stdout.strip()


def prepare(source, destination):
    source = Path(source).resolve(strict=True)
    destination = Path(destination).absolute().resolve()
    skill = Path(__file__).resolve().parent.parent
    if git('rev-parse', 'HEAD', cwd=source) != PIN:
        raise ValueError('Upstream must be checked out at the pinned revision: ' + PIN)
    if git('status', '--porcelain', '--untracked-files=no', cwd=source):
        raise ValueError('Upstream checkout has tracked changes; use a clean copy')
    if destination.exists() or source in destination.parents or destination in source.parents:
        raise FileExistsError('Use a new runtime folder outside the upstream checkout')
    destination.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='.jy-runtime-', dir=destination.parent) as temporary:
        stage = Path(temporary) / 'runtime'
        stage.mkdir()
        for name in ['scripts', 'data', 'rules']:
            shutil.copytree(source / name, stage / name)
        patch = skill / 'references' / 'upstream-115.patch.txt'
        git('apply', '--check', str(patch), cwd=stage)
        git('apply', str(patch), cwd=stage)
        for path in (skill / 'scripts').glob('*.py'):
            shutil.copy2(path, stage / 'scripts' / path.name)
        for name in ['references', 'agents', 'assets']:
            shutil.copytree(skill / name, stage / name)
        shutil.copy2(skill / 'SKILL.md', stage / 'SKILL.md')
        shutil.copy2(skill / 'LICENSE', stage / 'LICENSE-compatibility.txt')
        shutil.copy2(source / 'LICENSE', stage / 'LICENSE')
        shutil.copy2(source / 'requirements.txt', stage / 'requirements.txt')
        if destination.exists():
            raise FileExistsError('Destination appeared while preparing runtime')
        stage.rename(destination)
    return destination


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', required=True)
    parser.add_argument('--destination', required=True)
    args = parser.parse_args()
    print(prepare(args.source, args.destination))

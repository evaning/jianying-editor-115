"""Build source and standard Agent Skill archives from explicit public paths."""
import hashlib
from pathlib import Path
import zipfile

ROOT = Path(__file__).resolve().parents[1]
NAME = 'jianying-editor-115'
SKILL = ROOT / 'skills' / NAME


def files_in(folder):
    for path in sorted(folder.rglob('*')):
        if path.is_symlink():
            raise ValueError('Symlinks are not allowed in releases: ' + str(path))
        if not path.is_file() or '__pycache__' in path.parts:
            continue
        if path.suffix.lower() not in ('.md', '.py', '.txt', '.yaml', '.yml', '.svg', ''):
            raise ValueError('Unexpected release file: ' + str(path))
        str(path.relative_to(ROOT)).encode('ascii')
        yield path


def write_zip(target, paths, base, prefix):
    with zipfile.ZipFile(target, 'w', compression=zipfile.ZIP_DEFLATED) as archive:
        for path in sorted(paths):
            member = prefix + '/' + path.relative_to(base).as_posix()
            info = zipfile.ZipInfo(member, (2026, 9, 30, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o100644 << 16
            archive.writestr(info, path.read_bytes())


def main():
    version = (ROOT / 'VERSION').read_text(encoding='utf-8').strip()
    if not version or any(c not in '0123456789.' for c in version):
        raise ValueError('Invalid VERSION')
    if not (SKILL / 'SKILL.md').is_file():
        raise FileNotFoundError('Missing skill source')
    output = ROOT / 'dist'
    output.mkdir(exist_ok=True)
    skill_files = list(files_in(SKILL))
    source_files = [ROOT / p for p in ('README.md', 'LICENSE', 'NOTICE.md', 'VERSION', '.gitignore')]
    source_files += list(files_in(ROOT / '.github')) + list(files_in(ROOT / 'tools')) + skill_files
    skill_zip = output / f'{NAME}-v{version}.zip'
    source_zip = output / f'{NAME}-github-v{version}.zip'
    write_zip(source_zip, source_files, ROOT, NAME)
    write_zip(skill_zip, skill_files, SKILL, NAME)
    checksums = []
    for path in (source_zip, skill_zip):
        checksum = hashlib.sha256(path.read_bytes()).hexdigest()
        checksums.append(f'{checksum}  {path.name}')
        print(f'{path.name}: {path.stat().st_size} bytes, {checksum}')
    (output / 'SHA256SUMS.txt').write_text('\n'.join(checksums) + '\n', encoding='ascii')


if __name__ == '__main__':
    main()

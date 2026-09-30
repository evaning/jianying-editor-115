"""Version-aware draft inspection and guarded copy editing for Jianying Windows.

Never writes the input project. Patches operate on raw JSON to retain unknown
11.x fields, and an independently verified folder is published at the end.
"""
import argparse
import copy
import hashlib
import json
import os
from pathlib import Path
import shutil
import sys
import tempfile
import uuid

from draft_codec import DraftError, decode, detect, encode, read_json


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def candidates(folder):
    # Windows app-authored content takes precedence over stale generated info.
    return [p for p in (folder / 'draft_content.json', folder / 'draft_info.json') if p.is_file()]


def reject_native_for_legacy(folder):
    folder = Path(folder)
    if (folder / 'Timelines').is_dir() or folder.parent.name == 'Timelines':
        raise DraftError('Native multi-file project: use modern_draft.clone_edit, not the legacy serializer')
    for path in candidates(folder):
        if detect(path.read_bytes()) != 'plain':
            raise DraftError('Encrypted draft preserved. Use modern_draft.clone_edit with JY_INSTALL_DIR')


def choose_content(folder, install_dir=None):
    folder = Path(folder).resolve(strict=True)
    manifest = folder / 'Timelines' / 'project.json'
    if manifest.is_file():
        project = read_json(manifest, install_dir)
        main_id = project.get('main_timeline_id')
        if not isinstance(main_id, str) or not main_id or any(x in main_id for x in ('/', '\\', '..')):
            raise DraftError('Invalid main timeline id; do not guess a timeline')
        timeline = folder / 'Timelines' / main_id
        if not timeline.is_dir() or timeline.resolve().parent != (folder / 'Timelines').resolve():
            raise DraftError('Missing or unsafe main timeline directory')
        found = candidates(timeline)
        if not found:
            raise DraftError('Main timeline has no draft content')
        return found[0]
    found = candidates(folder)
    if not found:
        raise DraftError('No draft content found')
    return found[0]


def timeline_summary(data):
    validate_timeline(data)
    tracks = data['tracks']
    return {'duration_us': data.get('duration'), 'fps': data.get('fps'),
            'app_version': data.get('last_modified_platform', {}).get('app_version'),
            'track_count': len(tracks),
            'segment_count': sum(len(t.get('segments', [])) for t in tracks),
            'tracks': [{'id': t.get('id'), 'type': t.get('type'), 'segments': len(t.get('segments', []))} for t in tracks]}


def validate_timeline(data):
    if not isinstance(data.get('tracks'), list) or not isinstance(data.get('materials'), dict):
        raise DraftError('Not a timeline object')
    for track in data['tracks']:
        if not isinstance(track, dict) or not isinstance(track.get('segments', []), list):
            raise DraftError('Invalid track')
        for segment in track.get('segments', []):
            if not isinstance(segment, dict):
                raise DraftError('Invalid segment')
            for field in ('target_timerange', 'source_timerange'):
                timerange = segment.get(field)
                if timerange is None:
                    continue
                if not isinstance(timerange, dict):
                    raise DraftError('Invalid timerange')
                for key in ('start', 'duration'):
                    # Native 11.5 omits scalar zero fields in saved JSON.
                    value = timerange.get(key, 0)
                    if not isinstance(value, (int, float)) or isinstance(value, bool) or value < 0:
                        raise DraftError('Negative or invalid timerange')


def inspect(folder, install_dir=None):
    folder = Path(folder).resolve(strict=True)
    selected = choose_content(folder, install_dir)
    raw = selected.read_bytes()
    data = decode(raw, install_dir)
    result = {'selected_file': str(selected), 'source_sha256': digest(raw),
              'encoding': detect(raw), **timeline_summary(data), 'other_files': []}
    locations = candidates(folder)
    if selected.parent != folder:
        locations += candidates(selected.parent)
    for path in locations:
        if path == selected:
            continue
        value = read_json(path, install_dir)
        result['other_files'].append({'file': str(path.relative_to(folder)),
                                      'encoding': detect(path.read_bytes()),
                                      'same_content': value == data,
                                      'duration_us': value.get('duration')})
    return result


def apply_patch_plan(data, raw_hash, plan):
    if not isinstance(plan, dict) or plan.get('source_sha256') != raw_hash:
        raise DraftError('Patch source_sha256 does not match current authoritative draft')
    operations = plan.get('operations')
    if not isinstance(operations, list):
        raise DraftError('Patch requires an operations list')
    changed = copy.deepcopy(data)
    for operation in operations:
        if not isinstance(operation, dict) or operation.get('op') != 'replace' or 'expected' not in operation or 'value' not in operation:
            raise DraftError('Use replace operations with path, expected and value')
        pointer = operation.get('path', '')
        if not isinstance(pointer, str) or not pointer.startswith('/') or pointer == '/':
            raise DraftError('Use a non-root JSON Pointer')
        parts = [s.replace('~1', '/').replace('~0', '~') for s in pointer[1:].split('/')]
        parent = changed
        try:
            for part in parts[:-1]:
                if isinstance(parent, list) and not part.isdecimal():
                    raise ValueError('Invalid index')
                parent = parent[int(part)] if isinstance(parent, list) else parent[part]
            key = parts[-1]
            if isinstance(parent, list):
                if not key.isdecimal():
                    raise ValueError('Invalid index')
                key = int(key)
            if parent[key] != operation['expected']:
                raise DraftError(f'Expected value mismatch at {pointer}')
            parent[key] = copy.deepcopy(operation['value'])
        except (KeyError, IndexError, TypeError, ValueError) as error:
            raise DraftError(f'Patch rejected at {pointer}: {error}') from error
    validate_timeline(changed)
    # rejects NaN/Infinity and non-JSON values before any files are copied
    json.dumps(changed, allow_nan=False)
    return changed


def remap_paths(value, source, destination):
    if isinstance(value, dict):
        return {key: remap_paths(item, source, destination) for key, item in value.items()}
    if isinstance(value, list):
        return [remap_paths(item, source, destination) for item in value]
    if isinstance(value, str):
        normalized = value.replace('\\', '/')
        prefix = source.as_posix()
        if normalized.casefold() == prefix.casefold() or normalized.casefold().startswith(prefix.casefold() + '/'):
            return destination.as_posix() + normalized[len(prefix):]
        if value.startswith('{'):
            try:
                obj = json.loads(value)
                mapped = remap_paths(obj, source, destination)
                if mapped != obj:
                    return json.dumps(mapped, ensure_ascii=False, separators=(',', ':'))
            except ValueError:
                pass
    return value


def hash_files(folder):
    results = {}
    for path in sorted(folder.rglob('*')):
        if path.is_symlink() or (hasattr(path, 'is_junction') and path.is_junction()):
            raise DraftError('Symlink/junction in project; copy media to regular files first')
        if path.is_file():
            checksum = hashlib.sha256()
            with path.open('rb') as stream:
                for block in iter(lambda: stream.read(1024 * 1024), b''):
                    checksum.update(block)
            results[str(path.relative_to(folder))] = checksum.hexdigest()
    return results


def assert_editor_closed():
    if sys.platform == 'win32':
        import csv
        import io
        import subprocess
        check = subprocess.run(['tasklist', '/FO', 'CSV', '/NH', '/FI', 'IMAGENAME eq JianyingPro.exe'], capture_output=True, timeout=15)
        if check.returncode:
            raise DraftError('Could not determine whether Jianying is running')
        for row in csv.reader(io.StringIO(check.stdout.decode('utf-8', errors='replace'))):
            if row and row[0].casefold() == 'jianyingpro.exe':
                raise DraftError('Exit Jianying normally before creating a project copy')


def clone_edit(source, destination, plan=None, install_dir=None):
    assert_editor_closed()
    source = Path(source).resolve(strict=True)
    destination = Path(destination).absolute().resolve()
    if destination.exists() or source == destination or source in destination.parents or destination in source.parents:
        raise DraftError('Destination must be a new folder outside the source project')
    # Stay out of the user catalog until the caller explicitly registers a copy.
    selected = choose_content(source, install_dir)
    raw = selected.read_bytes()
    before = hash_files(source)
    if digest(raw) != before.get(str(selected.relative_to(source))):
        raise DraftError('Source changed during inspection; no output published')
    original = decode(raw, install_dir)
    updated = apply_patch_plan(original, digest(raw), plan) if plan is not None else copy.deepcopy(original)
    validate_timeline(updated)
    meta_path = source / 'draft_meta_info.json'
    if not meta_path.is_file():
        raise DraftError('No draft metadata; refuse to invent a project')
    metadata = read_json(meta_path, install_dir)
    project_id = str(uuid.uuid4()).upper()
    updated = remap_paths(updated, source, destination)
    metadata = remap_paths(metadata, source, destination)
    metadata.update(draft_id=project_id, draft_name=destination.name,
                    draft_fold_path=destination.as_posix(), draft_root_path=destination.parent.as_posix())
    if 'draft_json_file' in metadata:
        metadata['draft_json_file'] = (destination / 'draft_content.json').as_posix()
    metadata['tm_duration'] = updated.get('duration', metadata.get('tm_duration', 0))
    destination.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='.jy-staging-', dir=destination.parent) as temporary:
        staging = Path(temporary) / 'project'
        shutil.copytree(source, staging)
        if hash_files(staging) != before:
            raise DraftError('Source changed during copy; no output published')
        targets = candidates(source)
        if selected.parent != source:
            targets += candidates(selected.parent)
        written = []
        for path in targets:
            relative = path.relative_to(source)
            # Synchronize root + main timeline + stale info mirrors, keep each encoding.
            encoded = encode(updated, detect(path.read_bytes()), install_dir)
            (staging / relative).write_bytes(encoded)
            if read_json(staging / relative, install_dir) != updated:
                raise DraftError('Content verification failed')
            written.append(str(relative))
        (staging / 'draft_meta_info.json').write_bytes(encode(metadata, detect(meta_path.read_bytes()), install_dir))
        if read_json(staging / 'draft_meta_info.json', install_dir) != metadata:
            raise DraftError('Metadata verification failed')
        manifest = staging / 'Timelines' / 'project.json'
        if manifest.is_file():
            project = read_json(manifest, install_dir)
            active = [t for t in project.get('timelines', []) if not t.get('is_marked_delete')]
            if len(active) != 1:
                raise DraftError('Multiple timelines require explicit per-timeline planning; copy not published')
            project['id'] = project_id
            manifest.write_bytes(encode(project, detect(manifest.read_bytes()), install_dir))
        if hash_files(source) != before:
            raise DraftError('Source changed while editing; no output published')
        assert_editor_closed()
        if destination.exists():
            raise DraftError('Destination appeared during editing; refuse to replace it')
        # rename is atomic on one filesystem; Windows refuses an existing destination.
        staging.rename(destination)
    return {'ok': True, 'copy': str(destination), 'project_id': project_id,
            'source_unchanged': True, 'source_file_count': len(before),
            'written_content_files': written, 'summary': timeline_summary(updated),
            'native_ui_verified': False}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--install-dir', default=os.environ.get('JY_INSTALL_DIR'))
    sub = parser.add_subparsers(dest='command', required=True)
    show = sub.add_parser('inspect')
    show.add_argument('project')
    decode_parser = sub.add_parser('decode')
    decode_parser.add_argument('input')
    decode_parser.add_argument('output')
    clone = sub.add_parser('clone')
    clone.add_argument('source')
    clone.add_argument('destination')
    clone.add_argument('--patch')
    args = parser.parse_args()
    if args.command == 'inspect':
        result = inspect(args.project, args.install_dir)
    elif args.command == 'decode':
        source = Path(args.input).resolve(strict=True)
        target = Path(args.output).absolute()
        data = read_json(source, args.install_dir)
        with target.open('x', encoding='utf-8') as stream:
            json.dump(data, stream, ensure_ascii=False, indent=2)
        result = {'ok': True, 'output': str(target)}
    else:
        plan = read_json(args.patch) if args.patch else None
        result = clone_edit(args.source, args.destination, plan, args.install_dir)
    print(json.dumps(result, ensure_ascii=True, indent=2))


if __name__ == '__main__':
    try:
        main()
    except (DraftError, OSError, ValueError) as error:
        print(json.dumps({'ok': False, 'error': str(error)}, ensure_ascii=True), file=sys.stderr)
        sys.exit(1)

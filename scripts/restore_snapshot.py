"""Restore a snapshot to an EMPTY data directory. Never overwrite existing data."""
import argparse
from contextlib import closing
import hashlib
import json
from pathlib import Path, PurePosixPath
import shutil
import sqlite3
import tempfile
import zipfile

import bcrypt
from dotenv import dotenv_values

ROOT = Path(__file__).resolve().parents[1]


def digest_bytes(data):
    return hashlib.sha256(data).hexdigest()


def restore(snapshot, target, config):
    if target.exists() and any(target.iterdir()):
        raise FileExistsError(f'Refusing to overwrite existing data: {target}')
    manifest = json.loads((snapshot / 'manifest.json').read_text(encoding='utf-8'))
    if manifest['format_version'] != 1:
        raise ValueError('Unsupported snapshot version.')
    archive_info = next(item for item in manifest['artifacts'] if item['path'] == 'data.zip')
    archive_path = snapshot / 'data.zip'
    if digest_bytes(archive_path.read_bytes()) != archive_info['sha256']:
        raise ValueError('Snapshot archive SHA-256 does not match the manifest.')
    settings = dotenv_values(config)
    username = settings.get('ADMIN_USERNAME') or 'admin'
    password = settings.get('ADMIN_PASSWORD') or ''
    if len(password) < 6:
        raise ValueError('Set ADMIN_PASSWORD in backend/.env before restoring (at least 6 characters).')
    target.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='restore-', dir=target.parent) as temp:
        staged = Path(temp) / 'data'
        staged.mkdir()
        expected = {entry['path']: entry for entry in archive_info['files']}
        with zipfile.ZipFile(archive_path) as archive:
            if sorted(archive.namelist()) != sorted(expected):
                raise ValueError('Archive contents do not match the manifest.')
            for info in archive.infolist():
                relative = PurePosixPath(info.filename)
                if relative.is_absolute() or '..' in relative.parts or '\\' in info.filename or ':' in info.filename:
                    raise ValueError('Unsafe archive path.')
                content = archive.read(info)
                entry = expected[info.filename]
                if len(content) != entry['size'] or digest_bytes(content) != entry['sha256']:
                    raise ValueError(f'Invalid archived file: {info.filename}')
                destination = staged.joinpath(*relative.parts)
                destination.parent.mkdir(parents=True, exist_ok=True)
                destination.write_bytes(content)
        with closing(sqlite3.connect(staged / 'app.db')) as db:
            assert db.execute('PRAGMA integrity_check').fetchone()[0] == 'ok'
            assert not db.execute('PRAGMA foreign_key_check').fetchall()
            existing = db.execute('SELECT id,role FROM users WHERE username=?', (username,)).fetchone()
            if not existing or existing[1] != 'admin':
                raise ValueError('ADMIN_USERNAME must match an administrator in the snapshot; see conversations.json users.')
            hashed = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()
            db.execute('UPDATE users SET password_hash=? WHERE id=?', (hashed, existing[0]))
            db.commit()
            counts = {table: db.execute(f'SELECT count(*) FROM {table}').fetchone()[0] for table in manifest['counts']}
            if counts != manifest['counts']:
                raise ValueError('Restored row counts do not match the snapshot.')
        if target.exists():
            target.rmdir()  # Only an empty directory can be removed.
        shutil.move(str(staged), str(target))
    print(json.dumps({'restored_to': str(target), 'counts': counts, 'admin': username}, ensure_ascii=False))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('snapshot', type=Path, help='Directory containing manifest.json and data.zip')
    parser.add_argument('--target', type=Path, default=ROOT / 'backend' / 'data')
    parser.add_argument('--config', type=Path, default=ROOT / 'backend' / '.env')
    args = parser.parse_args()
    restore(args.snapshot.resolve(), args.target.resolve(), args.config.resolve())

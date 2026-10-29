"""Export application data; review new content before publication; run after stopping the app.

Original data is never modified. Password hashes, API keys and runtime logs
are deliberately excluded. Run with backend/.venv/Scripts/python.exe.
"""
import argparse
from contextlib import closing
from datetime import datetime, timezone, timedelta
import hashlib
import json
from pathlib import Path
import secrets
import shutil
import sqlite3
import tempfile
import urllib.error
import urllib.request
import zipfile

import bcrypt

ROOT = Path(__file__).resolve().parents[1]


def digest(path):
    h = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def service_running():
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    try:
        with opener.open('http://127.0.0.1:8018/api/health', timeout=2):
            return True
    except urllib.error.URLError:
        return False


def sqlite_copy(source, target):
    with closing(sqlite3.connect(source.as_uri() + '?mode=ro', uri=True)) as src:
        with closing(sqlite3.connect(target)) as dst:
            src.backup(dst)


def make_zip(directory, target):
    entries = []
    with zipfile.ZipFile(target, 'w', zipfile.ZIP_DEFLATED) as archive:
        for path in sorted(directory.rglob('*')):
            if path.is_file():
                relative = path.relative_to(directory).as_posix()
                archive.write(path, relative)
                entries.append({'path': relative, 'size': path.stat().st_size, 'sha256': digest(path)})
    return entries


def export_snapshot(output):
    if service_running():
        raise RuntimeError('Stop the app with stop_local.bat before taking a consistent snapshot.')
    if output.exists():
        raise FileExistsError(f'Snapshot already exists: {output}')
    source = ROOT / 'backend' / 'data'
    if not (source / 'app.db').is_file():
        raise FileNotFoundError('No application database found.')
    output.mkdir(parents=True)
    with tempfile.TemporaryDirectory(prefix='snapshot-', dir=ROOT / '.cache') as temp:
        work = Path(temp) / 'data'
        work.mkdir()
        sqlite_copy(source / 'app.db', work / 'app.db')
        for name in ('chroma', 'uploads'):
            if (source / name).exists():
                shutil.copytree(source / name, work / name)
        chroma_db = source / 'chroma' / 'chroma.sqlite3'
        if chroma_db.exists():
            sqlite_copy(chroma_db, work / 'chroma' / 'chroma.sqlite3')
        with closing(sqlite3.connect(work / 'app.db')) as db:
            db.row_factory = sqlite3.Row
            old_hashes = [row[0] for row in db.execute('SELECT password_hash FROM users')]
            db.execute('PRAGMA secure_delete=ON')
            for user in db.execute('SELECT id FROM users').fetchall():
                unusable = bcrypt.hashpw(secrets.token_urlsafe(32).encode(), bcrypt.gensalt()).decode()
                db.execute('UPDATE users SET password_hash=? WHERE id=?', (unusable, user['id']))
            db.commit()
            db.execute('VACUUM')
            counts = {table: db.execute(f'SELECT count(*) FROM {table}').fetchone()[0]
                      for table in ('users', 'chat_sessions', 'chat_messages', 'knowledge_documents')}
            users = [dict(row) for row in db.execute('SELECT id,username,role,created_at FROM users ORDER BY id')]
            sessions = []
            for row in db.execute('SELECT * FROM chat_sessions ORDER BY id'):
                session = dict(row)
                messages = []
                for message in db.execute('SELECT * FROM chat_messages WHERE session_id=? ORDER BY id', (row['id'],)):
                    item = dict(message)
                    if isinstance(item['sources'], str):
                        item['sources'] = json.loads(item['sources'])
                    messages.append(item)
                session['messages'] = messages
                sessions.append(session)
            documents = [dict(row) for row in db.execute('SELECT * FROM knowledge_documents ORDER BY id')]
            assert db.execute('PRAGMA integrity_check').fetchone()[0] == 'ok'
            assert not db.execute('PRAGMA foreign_key_check').fetchall()
        data_bytes = (work / 'app.db').read_bytes()
        if any(value.encode() in data_bytes for value in old_hashes):
            raise RuntimeError('An original password hash remains in the exported database.')
        data_files = make_zip(work, output / 'data.zip')
    exported_at = datetime.now(timezone(timedelta(hours=8))).isoformat()
    conversation_export = {'exported_at': exported_at, 'scope': 'RAG application conversations; not Codex chat history',
                           'users': users, 'sessions': sessions, 'knowledge_documents': documents}
    (output / 'conversations.json').write_text(json.dumps(conversation_export, ensure_ascii=False, indent=2), encoding='utf-8')
    readable = [f'# RAG 网页对话记录\n\n导出时间：{exported_at}\n\n仅包含项目网页中的会话，不包含 Codex 聊天历史。\n']
    for session in sessions:
        readable.append(f"\n## 会话 {session['id']}：{session['title']}\n")
        for message in session['messages']:
            readable.append(f"\n### {message['role']} · {message['created_at']}\n\n{message['content']}\n")
            if message['sources']:
                readable.append('\n引用来源：\n\n```json\n' + json.dumps(message['sources'], ensure_ascii=False, indent=2) + '\n```\n')
    (output / 'conversations.md').write_text(''.join(readable), encoding='utf-8')
    artifacts = [{'path': 'data.zip', 'sha256': digest(output / 'data.zip'), 'files': data_files}]
    built = ROOT / 'frontend' / 'dist'
    if built.exists():
        built_files = make_zip(built, output / 'frontend-dist.zip')
        artifacts.append({'path': 'frontend-dist.zip', 'sha256': digest(output / 'frontend-dist.zip'), 'files': built_files})
    for name in ('conversations.json', 'conversations.md'):
        artifacts.append({'path': name, 'sha256': digest(output / name)})
    manifest = {'format_version': 1, 'exported_at': exported_at, 'counts': counts,
                'passwords': 'Original hashes replaced with random unusable credentials; restore resets only the configured admin.',
                'excluded': ['backend/.env', 'runtime logs', 'dependency caches', 'original password hashes', 'Codex chat history'],
                'artifacts': artifacts}
    (output / 'manifest.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps({'snapshot': str(output), 'counts': counts}, ensure_ascii=False))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    stamp = datetime.now(timezone(timedelta(hours=8))).strftime('%Y%m%d-%H%M%S')
    (ROOT / '.cache').mkdir(exist_ok=True)
    export_snapshot((args.output or ROOT / 'snapshots' / stamp).resolve())

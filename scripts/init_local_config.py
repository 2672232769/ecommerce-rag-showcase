"""Create a new private backend/.env without overwriting an existing one."""
import getpass
from pathlib import Path
import secrets

ROOT = Path(__file__).resolve().parents[1]


def main():
    target = ROOT / 'backend' / '.env'
    if target.exists():
        print('backend/.env already exists; no changes made.')
        return
    password = getpass.getpass('Set a local administrator password (at least 8 characters): ')
    if len(password) < 8 or password != getpass.getpass('Repeat password: '):
        raise SystemExit('Passwords must match and contain at least 8 characters.')
    if any(character in password for character in ('\n', '\r', '"', "'", '#', '\\')) or password.strip() != password:
        raise SystemExit('Avoid quotes, backslashes, #, newlines and leading/trailing whitespace in this dotenv password.')
    template = (ROOT / 'backend' / '.env.example').read_text(encoding='utf-8')
    replacements = {'JWT_SECRET': secrets.token_urlsafe(48), 'ADMIN_PASSWORD': password}
    lines = []
    for line in template.splitlines():
        key = line.partition('=')[0]
        lines.append(f'{key}={replacements[key]}' if key in replacements else line)
    with target.open('x', encoding='utf-8', newline='\n') as output:
        output.write('\n'.join(lines) + '\n')
    print('Created backend/.env with a new JWT secret. Fill OPENAI_API_KEY locally; do not commit this file.')


if __name__ == '__main__':
    main()

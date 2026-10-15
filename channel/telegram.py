"""Private Telegram review transport; no YouTube upload or credential access."""
from __future__ import annotations
import argparse
import hashlib
import os
from pathlib import Path
import re
import sys
import time
import httpx

FILES = {
    'final.mp4': '2a9ea9bce46f37a9bf0ea46fa5f0d058958da789bd9ff8ade3a5224bf9c7ecf2',
    'thumbnail.jpg': 'b71d07edd515730710475bad9d633a95c46be81ecf4ad417cdac67f51df339e0',
    'captions.srt': '8c068df322b76713fabd27f81814cbff19a69ce81776c00a4c501826ba26f757',
    'script.md': '2778bea23ef1d6d18683c9bd5c67f09b7a0ca8523c91f3ae52395e5c7e545528',
    'sources.md': '16e032bab72953c3733b85d1fd78beb6433bab0599d1f41dbd3b54cb4df33b7d',
    'LogicScript_Practice_Lab.html': '1a17a51ab98592211d82e0d14324123b8083bc3e9f23c63001346e8db127a614',
}
HELP = ('LogicScript: /status, /video, /files, /help. '
        'M reponn sèlman pandan yon sesyon aktif. '
        'Upload/piblikasyon YouTube dezaktive. Apwobasyon Telegram pa aktive upload.')
STATUS = ('LogicScript: UC7vcWhYzuJtarRqSz7KgJgw. '
          'Pakè revizyon: videyo 6m47s, 1080p; bezwen revizyon final pwopriyetè a. '
          'Sa pa yon nouvo tès OAuth an dirèk. Upload/piblikasyon: dezaktive.')

class BotError(RuntimeError):
    """Safe diagnostics: no API bodies, request URLs or secrets."""

class Bot:
    def __init__(self, token, owner_id, root, client=None):
        if not re.fullmatch(r'[0-9]+:[A-Za-z0-9_-]{20,}', token or ''):
            raise BotError('TELEGRAM_BOT_TOKEN missing or malformed')
        if not re.fullmatch(r'[1-9][0-9]*', str(owner_id or '')):
            raise BotError('TELEGRAM_OWNER_ID must be the trusted numeric private user ID')
        self.owner, self.root, self._token = int(owner_id), Path(root).resolve(), token
        self.client = client or httpx.Client(timeout=60, follow_redirects=False, trust_env=False)

    def call(self, method, data=None, files=None):
        # No outgoing retries: a lost response may already have delivered media.
        try:
            response = self.client.post(f'https://api.telegram.org/bot{self._token}/{method}', data=data or {}, files=files)
            payload = response.json()
        except Exception:
            raise BotError('Telegram request failed; details suppressed to protect credentials') from None
        if response.status_code != 200 or not isinstance(payload, dict) or payload.get('ok') is not True:
            raise BotError(f'Telegram {method} failed (HTTP {response.status_code}); details suppressed')
        return payload.get('result')

    def verify(self, polling=False):
        me = self.call('getMe')
        if not isinstance(me, dict) or me.get('is_bot') is not True:
            raise BotError('Telegram bot identity could not be verified')
        if polling:
            webhook = self.call('getWebhookInfo')
            if not isinstance(webhook, dict) or webhook.get('url'):
                raise BotError('Existing webhook detected or unknown; polling refused without modifying it')
        return me

    def text(self, text):
        return self.call('sendMessage', {'chat_id': self.owner, 'text': text})

    def validated_file(self, name):
        if name not in FILES:
            raise BotError('File is not in the fixed review allowlist')
        path = (self.root / name).resolve()
        if path.parent != self.root or not path.is_file():
            raise BotError('Review file missing or outside review directory')
        if path.stat().st_size > 49_000_000:
            raise BotError('Review file exceeds conservative Telegram transfer limit')
        if hashlib.sha256(path.read_bytes()).hexdigest() != FILES[name]:
            raise BotError('Review file digest mismatch; delivery refused')
        return path

    def send_file(self, name):
        path = self.validated_file(name)
        video = name == 'final.mp4'
        method, field = ('sendVideo', 'video') if video else ('sendDocument', 'document')
        data = {'chat_id': self.owner}
        if video:
            data.update(supports_streaming='true', caption='LogicScript — pou revizyon sèlman. Pa gen upload YouTube.')
        with path.open('rb') as stream:
            self.call(method, data, {field: (path.name, stream, 'video/mp4' if video else 'application/octet-stream')})

    def handle(self, update):
        message = update.get('message') if isinstance(update, dict) else None
        if not isinstance(message, dict):
            return
        sender, chat = message.get('from', {}), message.get('chat', {})
        if (sender.get('id') != self.owner or sender.get('is_bot') is not False
                or chat.get('id') != self.owner or chat.get('type') != 'private'
                or any(k in message for k in ('forward_origin', 'forward_from', 'sender_chat'))):
            return
        raw = message.get('text', '')
        if not isinstance(raw, str) or len(raw) > 128:
            return
        command = raw.strip().lower()
        if command in ('/start', '/help'):
            self.text(HELP)
        elif command == '/status':
            self.text(STATUS)
        elif command == '/video':
            self.send_file('final.mp4')
        elif command == '/files':
            names = [name for name in FILES if name != 'final.mp4']
            for name in names:
                self.validated_file(name)
            for name in names:
                self.send_file(name)
        else:
            self.text(HELP)

    def listen(self, seconds=300):
        if not 1 <= seconds <= 300:
            raise BotError('Session must last between 1 and 300 seconds')
        self.verify(polling=True)
        # New sessions deliberately discard old queued commands, preventing replay.
        pending = self.call('getUpdates', {'offset': -1, 'timeout': 0, 'allowed_updates': '["message"]'})
        offset = pending[-1]['update_id'] + 1 if pending else 0
        deadline = time.monotonic() + seconds
        while time.monotonic() < deadline:
            timeout = min(20, max(1, int(deadline - time.monotonic())))
            updates = self.call('getUpdates', {'offset': offset, 'timeout': timeout, 'allowed_updates': '["message"]'})
            for update in updates:
                offset = max(offset, update['update_id'] + 1)
                self.handle(update)

def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('mode', choices=['verify', 'deliver', 'listen'])
    parser.add_argument('--review-dir', type=Path, default=Path('outputs/telegram-review'))
    args = parser.parse_args(argv)
    try:
        bot = Bot(os.environ.get('TELEGRAM_BOT_TOKEN', ''), os.environ.get('TELEGRAM_OWNER_ID', ''), args.review_dir)
        if args.mode == 'listen':
            bot.listen()
        else:
            bot.verify()
            if args.mode == 'deliver':
                for name in FILES:
                    bot.validated_file(name)
                bot.send_file('final.mp4')
                bot.text(HELP)
        print('Telegram operation completed; no YouTube upload was performed.')
        return 0
    except BotError as exc:
        print(str(exc), file=sys.stderr)
        return 1

if __name__ == '__main__':
    raise SystemExit(main())

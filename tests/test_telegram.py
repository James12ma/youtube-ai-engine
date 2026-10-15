import hashlib
import httpx
import pytest
from channel.telegram import Bot, BotError, FILES

TOKEN = '123456:' + 'x' * 32
OWNER = 12345678

def make_bot(tmp_path, responses=None):
    calls = []
    def respond(request):
        calls.append(request)
        result = responses(request) if responses else {'ok': True, 'result': {'is_bot': True}}
        return httpx.Response(200, json=result)
    return Bot(TOKEN, str(OWNER), tmp_path, httpx.Client(transport=httpx.MockTransport(respond))), calls

def msg(text='/status', **overrides):
    message = {'from': {'id': OWNER, 'is_bot': False}, 'chat': {'id': OWNER, 'type': 'private'}, 'text': text}
    message.update(overrides)
    return {'message': message}

@pytest.mark.parametrize('owner', ['', '0', '-5', 'someone'])
def test_owner_binding_required(tmp_path, owner):
    with pytest.raises(BotError):
        Bot(TOKEN, owner, tmp_path)

def test_status_replies_only_to_owner(tmp_path):
    bot, calls = make_bot(tmp_path)
    bot.handle(msg())
    assert len(calls) == 1
    assert calls[0].url.path.endswith('/sendMessage')
    assert 'chat_id=12345678' in calls[0].content.decode()

@pytest.mark.parametrize('update', [
    msg(**{'from': {'id': 9, 'is_bot': False}}),
    msg(chat={'id': -10, 'type': 'group'}),
    msg(forward_origin={'type': 'user'}),
    msg(**{'from': {'id': OWNER, 'is_bot': True}}),
    {'edited_message': msg()['message']},
    {'callback_query': {'data': '/approve'}},
])
def test_untrusted_messages_silently_ignored(tmp_path, update):
    bot, calls = make_bot(tmp_path)
    bot.handle(update)
    assert not calls

def test_no_approval_or_arbitrary_execution(tmp_path):
    bot, calls = make_bot(tmp_path)
    bot.handle(msg('/approve; upload'))
    assert len(calls) == 1 and calls[0].url.path.endswith('/sendMessage')
    assert not list(tmp_path.iterdir())

def test_active_webhook_is_preserved(tmp_path):
    bot, calls = make_bot(tmp_path, lambda r: {'ok': True, 'result': {'is_bot': True} if r.url.path.endswith('getMe') else {'url': 'https://existing.example'}})
    with pytest.raises(BotError, match='webhook'):
        bot.verify(polling=True)
    assert len(calls) == 2
    assert not any('deleteWebhook' in str(r.url) for r in calls)

def test_error_never_leaks_token_or_response(tmp_path):
    bot, _ = make_bot(tmp_path, lambda r: {'ok': False, 'description': TOKEN})
    with pytest.raises(BotError) as error:
        bot.verify()
    assert TOKEN not in str(error.value)
    assert 'api.telegram.org' not in str(error.value)

def test_network_error_sanitized(tmp_path):
    def fail(request):
        raise httpx.ConnectError(str(request.url), request=request)
    bot = Bot(TOKEN, str(OWNER), tmp_path, httpx.Client(transport=httpx.MockTransport(fail)))
    with pytest.raises(BotError) as error:
        bot.verify()
    assert TOKEN not in str(error.value)

def test_tampered_video_never_sent(tmp_path):
    (tmp_path / 'final.mp4').write_bytes(b'changed')
    bot, calls = make_bot(tmp_path)
    with pytest.raises(BotError, match='digest'):
        bot.handle(msg('/video'))
    assert not calls

def test_file_traversal_refused(tmp_path):
    bot, _ = make_bot(tmp_path)
    with pytest.raises(BotError, match='allowlist'):
        bot.validated_file('../secrets.txt')

def test_media_transfer_with_verified_hash(tmp_path, monkeypatch):
    data = b'verified-test-mp4'
    (tmp_path / 'final.mp4').write_bytes(data)
    monkeypatch.setitem(FILES, 'final.mp4', hashlib.sha256(data).hexdigest())
    bot, calls = make_bot(tmp_path)
    bot.handle(msg('/video'))
    assert len(calls) == 1 and calls[0].url.path.endswith('/sendVideo')
    assert data in calls[0].content

def test_session_rejects_unbounded_duration(tmp_path):
    bot, calls = make_bot(tmp_path)
    with pytest.raises(BotError):
        bot.listen(301)
    assert not calls

def test_polling_skips_backlog_and_advances_offset(tmp_path, monkeypatch):
    import channel.telegram as module
    requests = []
    def respond(request):
        from urllib.parse import parse_qs
        data = parse_qs(request.content.decode())
        requests.append((request.url.path.rsplit('/', 1)[-1], data))
        method = requests[-1][0]
        if method == 'getMe':
            result = {'is_bot': True}
        elif method == 'getWebhookInfo':
            result = {'url': ''}
        elif data.get('offset') == ['-1']:
            result = [{'update_id': 20, **msg('/video')}]
        else:
            result = [{'update_id': 21, **msg('/status')}]
        return {'ok': True, 'result': result}
    bot, _ = make_bot(tmp_path, respond)
    ticks = iter([0, 0, 0, 100])
    monkeypatch.setattr(module.time, 'monotonic', lambda: next(ticks))
    bot.listen(1)
    assert [method for method, _ in requests] == ['getMe', 'getWebhookInfo', 'getUpdates', 'getUpdates', 'sendMessage']
    assert requests[3][1]['offset'] == ['21']

import destructive_gmail
from validators import ApiError


def test_delete_status_is_disabled_by_default(monkeypatch, tmp_path):
    monkeypatch.delenv('ENABLE_PERMANENT_DELETE', raising=False)
    monkeypatch.setattr(destructive_gmail, 'DELETE_TOKEN', tmp_path / 'delete_token.json')

    status = destructive_gmail.delete_status()

    assert status['enabled'] is False
    assert status['authorized'] is False
    assert status['state'] == 'disabled'
    assert status['scope'] == 'https://mail.google.com/'
    assert status['max_batch'] == 100


def test_delete_status_reports_persistent_token_state(monkeypatch, tmp_path):
    monkeypatch.setenv('ENABLE_PERMANENT_DELETE', '1')
    monkeypatch.setattr(destructive_gmail, 'GMAIL_DELETE_OK', True)
    monkeypatch.setattr(destructive_gmail, 'CREDS', tmp_path / 'credentials.json')
    monkeypatch.setattr(destructive_gmail, 'DELETE_TOKEN', tmp_path / 'delete_token.json')
    destructive_gmail.CREDS.write_text('{}', encoding='utf-8')
    destructive_gmail.DELETE_TOKEN.write_text('{}', encoding='utf-8')

    class FakeCreds:
        valid = False
        expired = True
        refresh_token = 'refresh-token'

    monkeypatch.setattr(
        destructive_gmail.Credentials,
        'from_authorized_user_file',
        lambda *args, **kwargs: FakeCreds(),
    )

    status = destructive_gmail.delete_status()

    assert status['enabled'] is True
    assert status['authorized'] is True
    assert status['state'] == 'expired'
    assert status['token_present'] is True


def test_revoke_destructive_authorization_removes_token_and_marks_revoked(monkeypatch, tmp_path):
    monkeypatch.setenv('ENABLE_PERMANENT_DELETE', '1')
    monkeypatch.setattr(destructive_gmail, 'GMAIL_DELETE_OK', True)
    monkeypatch.setattr(destructive_gmail, 'CREDS', tmp_path / 'credentials.json')
    monkeypatch.setattr(destructive_gmail, 'DELETE_TOKEN', tmp_path / 'delete_token.json')
    monkeypatch.setattr(destructive_gmail, 'DELETE_REVOKED', tmp_path / 'delete_token.revoked')
    monkeypatch.setattr(destructive_gmail, '_delete_service', object())
    destructive_gmail.CREDS.write_text('{}', encoding='utf-8')
    destructive_gmail.DELETE_TOKEN.write_text('{}', encoding='utf-8')

    status = destructive_gmail.revoke_destructive_authorization()

    assert destructive_gmail.DELETE_TOKEN.exists() is False
    assert destructive_gmail.DELETE_REVOKED.exists() is True
    assert destructive_gmail._delete_service is None
    assert status['state'] == 'revoked'
    assert status['authorized'] is False
    assert status['token_present'] is False


def test_destructive_gmail_rejects_when_disabled(monkeypatch):
    monkeypatch.delenv('ENABLE_PERMANENT_DELETE', raising=False)
    monkeypatch.setattr(destructive_gmail, '_delete_service', None)

    try:
        destructive_gmail.destructive_gmail()
    except ApiError as exc:
        assert exc.status == 503
        assert str(exc) == 'Borrado permanente deshabilitado'
    else:
        raise AssertionError('Expected ApiError')


def test_destructive_gmail_does_not_start_oauth_without_explicit_authorize(monkeypatch, tmp_path):
    monkeypatch.setenv('ENABLE_PERMANENT_DELETE', '1')
    monkeypatch.setattr(destructive_gmail, 'GMAIL_DELETE_OK', True)
    monkeypatch.setattr(destructive_gmail, 'CREDS', tmp_path / 'credentials.json')
    monkeypatch.setattr(destructive_gmail, 'DELETE_TOKEN', tmp_path / 'delete_token.json')
    monkeypatch.setattr(destructive_gmail, '_delete_service', None)
    destructive_gmail.CREDS.write_text('{}', encoding='utf-8')

    try:
        destructive_gmail.destructive_gmail()
    except ApiError as exc:
        assert exc.status == 503
        assert str(exc) == 'Borrado permanente no autorizado'
    else:
        raise AssertionError('Expected ApiError')


def test_permanently_delete_messages_returns_individual_results(monkeypatch):
    class Execute:
        def __init__(self, message_id):
            self.message_id = message_id

        def execute(self):
            if self.message_id == 'bad':
                raise RuntimeError('not found')

    class Messages:
        def delete(self, **kwargs):
            assert kwargs['userId'] == 'me'
            return Execute(kwargs['id'])

    class Users:
        def messages(self):
            return Messages()

    class Service:
        def users(self):
            return Users()

    monkeypatch.setattr(destructive_gmail, 'destructive_gmail', lambda: Service())

    assert destructive_gmail.permanently_delete_messages(['ok', 'bad']) == [
        {'id': 'ok', 'status': 'deleted'},
        {'id': 'bad', 'status': 'error', 'detail': 'not found'},
    ]

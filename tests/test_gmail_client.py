import base64
import threading
import time
from concurrent.futures import ThreadPoolExecutor

import gmail_client
from gmail_client import BATCH_MODIFY_CHUNK, _decode_snippet, _message_from_gmail, _sender_matches, apply_label, archive_messages, get_attachment, get_message, gmail_error_detail, gmail_message_lookup_state, norm_date, search, tag


class _RecordingBatchService:
    def __init__(self):
        self.calls = []

    class _Messages:
        def __init__(self, outer):
            self._outer = outer

        def batchModify(self, userId, body):
            self._outer.calls.append(body)
            return type('E', (), {'execute': lambda self: {}})()

    def users(self):
        messages = self._Messages(self)
        return type('U', (), {'messages': lambda self: messages})()


def test_archive_messages_chunks_large_batches(monkeypatch):
    svc = _RecordingBatchService()
    monkeypatch.setattr(gmail_client, 'gmail', lambda: svc)
    ids = [f'm{i}' for i in range(BATCH_MODIFY_CHUNK * 2 + 5)]

    summary = archive_messages(ids)

    assert summary == {'total': len(ids), 'chunks': 3}
    assert [len(c['ids']) for c in svc.calls] == [BATCH_MODIFY_CHUNK, BATCH_MODIFY_CHUNK, 5]
    assert sum((c['ids'] for c in svc.calls), []) == ids
    assert all(c['removeLabelIds'] == ['INBOX'] for c in svc.calls)


def test_apply_label_chunks_and_optionally_archives(monkeypatch):
    svc = _RecordingBatchService()
    monkeypatch.setattr(gmail_client, 'gmail', lambda: svc)
    ids = [f'm{i}' for i in range(BATCH_MODIFY_CHUNK + 1)]

    summary = apply_label(ids, 'Label_9', archive=True)

    assert summary == {'total': len(ids), 'chunks': 2}
    assert all(c['addLabelIds'] == ['Label_9'] for c in svc.calls)
    assert all(c['removeLabelIds'] == ['INBOX'] for c in svc.calls)


def test_batch_modify_without_service_returns_none(monkeypatch):
    monkeypatch.setattr(gmail_client, 'gmail', lambda: None)
    assert archive_messages(['m1']) is None


def test_norm_date_parses_rfc_date():
    assert norm_date('Tue, 19 May 2026 10:15:00 +0000') == '2026-05-19'


def test_norm_date_falls_back_to_iso_substring():
    assert norm_date('created at 2026-05-20 by system') == '2026-05-20'


def test_tag_extracts_sender_domain():
    assert tag('Plesk <info@plesk.com>') == 'Plesk · Email'


def test_tag_without_email_returns_generic_label():
    assert tag('Servidor local') == 'Email'


def test_sender_matches_exact_email_and_real_domain_only():
    assert _sender_matches('User <u@example.com>', 'u@example.com') is True
    assert _sender_matches('User <u@alerts.example.com>', 'example.com') is True
    assert _sender_matches('example.com Support <u@evil.test>', 'example.com') is False
    assert _sender_matches('User <u@evil-example.com>', 'example.com') is False


def test_decode_snippet_unescapes_gmail_entities():
    assert _decode_snippet('A&amp;B &lt;x&gt; &#39;q&#39;') == "A&B <x> 'q'"


def test_write_token_uses_private_permissions(monkeypatch, tmp_path):
    token = tmp_path / 'token.json'
    monkeypatch.setattr(gmail_client, 'TOKEN', token)

    gmail_client._write_token('{"token": "secret"}')

    assert token.read_text(encoding='utf-8') == '{"token": "secret"}'
    assert token.stat().st_mode & 0o777 == 0o600


def test_gmail_reauthorizes_after_revoked_refresh_token(monkeypatch, tmp_path):
    class FakeRefreshError(Exception):
        pass

    class ExpiredCredentials:
        valid = False
        expired = True
        refresh_token = 'revoked'

        def refresh(self, request):
            raise FakeRefreshError('invalid_grant')

    class FreshCredentials:
        valid = True

        def to_json(self):
            return '{"token": "fresh"}'

    class FakeFlow:
        def run_local_server(self, port, open_browser=True):
            assert port == 0
            return FreshCredentials()
    token = tmp_path / 'token.json'
    token.write_text('{"token": "revoked"}', encoding='utf-8')
    credentials = tmp_path / 'credentials.json'
    credentials.write_text('{}', encoding='utf-8')
    service = object()

    monkeypatch.setattr(gmail_client, 'TOKEN', token)
    monkeypatch.setattr(gmail_client, 'CREDS', credentials)
    monkeypatch.setattr(gmail_client, '_svc', None)
    monkeypatch.setattr(gmail_client, 'RefreshError', FakeRefreshError)
    monkeypatch.setattr(gmail_client, 'Request', lambda: object())
    monkeypatch.setattr(
        gmail_client.Credentials,
        'from_authorized_user_file',
        lambda path, scopes: ExpiredCredentials(),
    )
    monkeypatch.setattr(
        gmail_client.InstalledAppFlow,
        'from_client_secrets_file',
        lambda path, scopes: FakeFlow(),
    )
    monkeypatch.setattr(gmail_client, 'build', lambda *args, **kwargs: service)

    assert gmail_client.gmail() is service
    assert token.read_text(encoding='utf-8') == '{"token": "fresh"}'
    assert token.stat().st_mode & 0o777 == 0o600


def test_gmail_message_lookup_state_marks_not_found_as_orphan():
    class FakeHttpError(Exception):
        pass

    exc = FakeHttpError('Requested entity was not found.')

    assert gmail_message_lookup_state(exc) == {
        'status': 'orphan',
        'detail': 'Requested entity was not found.',
    }


def test_message_from_gmail_normalizes_metadata():
    msg = {
        'id': 'abc123',
        'snippet': 'Factura &amp; aviso',
        'payload': {
            'headers': [
                {'name': 'From', 'value': 'Billing <billing@example.com>'},
                {'name': 'To', 'value': 'user@example.com'},
                {'name': 'Subject', 'value': 'New invoice'},
                {'name': 'Date', 'value': 'Tue, 19 May 2026 10:15:00 +0000'},
            ]
        },
    }

    out = _message_from_gmail(msg)

    assert out['id'] == 'abc123'
    assert out['date'] == '2026-05-19'
    assert out['subject'] == 'New invoice'
    assert out['body'] == 'Factura & aviso'
    assert out['tag'] == 'Example · Email'
    assert out['src'] == 'cu'
    assert out['attachments'] == []
    assert out['categories'] == ['money', 'warn']
    assert out['severity'] == 'high'
    assert out['severity_reason'] == 'Aviso urgente o fallo detectado'
    assert out['matched_rule_ids'] == []


def test_message_from_gmail_extracts_nested_attachments():
    msg = {
        'id': 'abc123',
        'snippet': '',
        'payload': {
            'headers': [],
            'parts': [
                {'mimeType': 'text/plain', 'body': {'size': 12}},
                {
                    'mimeType': 'multipart/mixed',
                    'parts': [
                        {
                            'filename': 'factura.pdf',
                            'mimeType': 'application/pdf',
                            'body': {'attachmentId': 'att_1', 'size': 1234},
                        }
                    ],
                },
            ],
        },
    }

    out = _message_from_gmail(msg)

    assert out['attachments'] == [
        {
            'attachment_id': 'att_1',
            'filename': 'factura.pdf',
            'mime_type': 'application/pdf',
            'size': 1234,
        }
    ]
    assert out['categories'] == []
    assert out['severity'] == 'low'


def test_message_from_gmail_applies_custom_rules():
    msg = {
        'id': 'abc123',
        'snippet': 'Monthly operational report',
        'payload': {'headers': [{'name': 'From', 'value': 'Ops <ops@example.com>'}]},
    }
    rules = [{
        'id': 'rule_ops',
        'label': 'Operaciones',
        'provider': 'example.com',
        'keywords': ['operational report'],
        'category': 'warn',
        'severity': 'high',
    }]

    out = _message_from_gmail(msg, rules)

    assert out['categories'] == ['warn']
    assert out['severity'] == 'high'
    assert out['severity_reason'] == 'Regla personalizada: Operaciones'
    assert out['matched_rule_ids'] == ['rule_ops']


def test_get_attachment_decodes_urlsafe_base64(monkeypatch):
    raw = base64.urlsafe_b64encode(b'PDF').decode('ascii').rstrip('=')

    class AttachmentGet:
        def execute(self):
            return {'data': raw}

    class Attachments:
        def get(self, **kwargs):
            assert kwargs == {'userId': 'me', 'messageId': 'm1', 'id': 'a1'}
            return AttachmentGet()

    class Messages:
        def attachments(self):
            return Attachments()

    class Users:
        def messages(self):
            return Messages()

    class Service:
        def users(self):
            return Users()

    monkeypatch.setattr('gmail_client.gmail', lambda: Service())

    assert get_attachment('m1', 'a1') == b'PDF'


def test_get_message_fetches_full_message(monkeypatch):
    class MessageGet:
        def execute(self):
            return {'id': 'm1', 'snippet': 'ok', 'payload': {'headers': []}}

    class Messages:
        def get(self, **kwargs):
            assert kwargs['id'] == 'm1'
            assert kwargs['format'] == 'full'
            return MessageGet()

    class Users:
        def messages(self):
            return Messages()

    class Service:
        def users(self):
            return Users()

    monkeypatch.setattr('gmail_client.gmail', lambda: Service())

    msg = get_message('m1')
    assert msg['id'] == 'm1'
    assert 'severity' in msg


def test_get_message_raw_fetches_raw_message(monkeypatch):
    raw_content = b'Subject: test\r\n\r\nbody'
    encoded = base64.urlsafe_b64encode(raw_content).decode('ascii')

    class MessageGet:
        def execute(self):
            return {'id': 'm1', 'raw': encoded}

    class Messages:
        def get(self, **kwargs):
            assert kwargs['id'] == 'm1'
            assert kwargs['format'] == 'raw'
            return MessageGet()

    class Users:
        def messages(self):
            return Messages()

    class Service:
        def users(self):
            return Users()

    monkeypatch.setattr('gmail_client.gmail', lambda: Service())

    assert gmail_client.get_message_raw('m1') == raw_content


def test_search_limits_total_messages_not_only_threads(monkeypatch):
    messages = [
        {
            'id': f'm{idx}',
            'snippet': '',
            'payload': {'headers': [{'name': 'From', 'value': 'Sender <notice@example.com>'}]},
        }
        for idx in range(5)
    ]

    class Execute:
        def __init__(self, value):
            self.value = value

        def execute(self):
            return self.value

    class Threads:
        def list(self, **kwargs):
            assert kwargs['maxResults'] == 3
            return Execute({'threads': [{'id': 't1'}, {'id': 't2'}]})

        def get(self, **kwargs):
            return Execute({'messages': messages})

    class Users:
        def threads(self):
            return Threads()

    class Service:
        def users(self):
            return Users()

    monkeypatch.setattr('gmail_client.gmail', lambda: Service())

    assert [msg['id'] for msg in search('example.com', max_r=3)] == ['m0', 'm1', 'm2']


def test_search_excludes_other_senders_from_matching_thread(monkeypatch):
    messages = [
        {'id': 'wanted', 'snippet': '', 'payload': {'headers': [{'name': 'From', 'value': 'Sender <notice@example.com>'}]}},
        {'id': 'reply', 'snippet': '', 'payload': {'headers': [{'name': 'From', 'value': 'Me <me@personal.test>'}]}},
    ]

    class Execute:
        def __init__(self, value):
            self.value = value

        def execute(self):
            return self.value

    class Threads:
        def list(self, **kwargs):
            return Execute({'threads': [{'id': 't1'}]})

        def get(self, **kwargs):
            return Execute({'messages': messages})

    class Users:
        def threads(self):
            return Threads()

    class Service:
        def users(self):
            return Users()

    monkeypatch.setattr('gmail_client.gmail', lambda: Service())

    assert [msg['id'] for msg in search('example.com', max_r=30)] == ['wanted']


def test_gmail_operations_are_serialized_for_shared_service(monkeypatch):
    active = 0
    max_active = 0
    access_lock = threading.Lock()

    class MessageGet:
        def execute(self):
            nonlocal active, max_active
            with access_lock:
                active += 1
                max_active = max(max_active, active)
            time.sleep(0.01)
            with access_lock:
                active -= 1
            return {'id': 'm1', 'snippet': 'ok', 'payload': {'headers': []}}

    class Messages:
        def get(self, **kwargs):
            return MessageGet()

    class Users:
        def messages(self):
            return Messages()

    class Service:
        def users(self):
            return Users()

    monkeypatch.setattr('gmail_client.gmail', lambda: Service())

    with ThreadPoolExecutor(max_workers=8) as executor:
        list(executor.map(lambda _: get_message('m1'), range(20)))

    assert max_active == 1


def test_gmail_error_detail_for_plain_exception():
    assert gmail_error_detail(RuntimeError('fallo')) == 'fallo'

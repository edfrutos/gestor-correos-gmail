import json
from io import BytesIO

import pytest

import server


class DummyHandler(server.H):
    def __init__(self, body=b'', headers=None):
        self.headers_sent = []
        self.status_sent = None
        self.wfile = BytesIO()
        self.rfile = BytesIO(body)
        self.headers = {'Content-Length': str(len(body)), 'Host': 'localhost:8765'}
        self.headers.update(headers or {})

    def send_response(self, status):
        self.status_sent = status

    def send_header(self, key, value):
        self.headers_sent.append((key, value))

    def end_headers(self):
        pass


class ExistingPath:
    def exists(self):
        return True


class ExistingFile:
    name = 'asset.js'

    def exists(self):
        return True

    def read_bytes(self):
        return b'asset'


class DisconnectingWriter:
    def __init__(self, error):
        self.error = error

    def write(self, body):
        raise self.error


def response_json(handler):
    return json.loads(handler.wfile.getvalue().decode('utf-8'))


def request_body(data):
    return json.dumps(data).encode('utf-8')


def test_json_response_shape():
    handler = DummyHandler()

    handler.j({'status': 'ok', 'count': 1})

    assert handler.status_sent == 200
    assert response_json(handler) == {'status': 'ok', 'count': 1}
    assert ('X-Content-Type-Options', 'nosniff') in handler.headers_sent


def test_error_response_shape():
    handler = DummyHandler()

    handler.err(400, 'Error', 'Detalle')

    assert handler.status_sent == 400
    assert response_json(handler) == {'status': 'error', 'error': 'Error', 'detail': 'Detalle'}


def test_serve_file_sets_content_type_and_nosniff():
    handler = DummyHandler()

    handler.serve_file(ExistingFile(), 'text/javascript; charset=utf-8')

    assert handler.status_sent == 200
    assert ('Content-Type', 'text/javascript; charset=utf-8') in handler.headers_sent
    assert ('X-Content-Type-Options', 'nosniff') in handler.headers_sent
    assert handler.wfile.getvalue() == b'asset'


@pytest.mark.parametrize('error', [BrokenPipeError(), ConnectionResetError()])
def test_write_body_ignores_client_disconnects(error):
    handler = DummyHandler()
    handler.wfile = DisconnectingWriter(error)

    assert handler.write_body(b'response') is False


def test_write_body_returns_true_after_successful_write():
    handler = DummyHandler()

    assert handler.write_body(b'response') is True
    assert handler.wfile.getvalue() == b'response'


@pytest.mark.parametrize('host', ['localhost:8765', '127.0.0.1:8765', '[::1]:8765'])
def test_request_is_local_accepts_local_hosts(host):
    handler = DummyHandler(headers={'Host': host})

    assert handler.request_is_local() is True


def test_request_is_local_rejects_external_host():
    handler = DummyHandler(headers={'Host': 'attacker.example'})

    assert handler.request_is_local() is False


def test_request_is_local_rejects_external_origin():
    handler = DummyHandler(headers={'Origin': 'https://attacker.example'})

    assert handler.request_is_local() is False


def test_request_is_local_accepts_expected_origin():
    handler = DummyHandler(headers={'Origin': 'http://localhost:8765'})

    assert handler.request_is_local() is True


def test_get_rejects_external_origin_before_routing():
    handler = DummyHandler(headers={'Origin': 'https://attacker.example'})
    handler.path = '/api/status'

    handler.do_GET()

    assert handler.status_sent == 403
    assert response_json(handler)['error'] == 'Origen no autorizado'


def test_handle_search_rejects_invalid_params_before_gmail(monkeypatch):
    handler = DummyHandler()
    called = False

    def fake_gmail():
        nonlocal called
        called = True

    monkeypatch.setattr(server, 'gmail', fake_gmail)

    handler.handle_search('max=abc')

    assert handler.status_sent == 400
    assert response_json(handler)['error'] == 'Parámetro max inválido'
    assert called is False


def test_handle_search_rejects_empty_query(monkeypatch):
    handler = DummyHandler()
    monkeypatch.setattr(server, 'gmail', lambda: object())

    handler.handle_search('sender=&q=&after=&before=')

    assert handler.status_sent == 400
    assert response_json(handler)['error'] == 'Búsqueda vacía'


def test_handle_search_returns_success_with_monkeypatched_gmail(monkeypatch):
    handler = DummyHandler()
    monkeypatch.setattr(server, 'GMAIL_OK', True)
    monkeypatch.setattr(server, 'CREDS', ExistingPath())
    monkeypatch.setattr(server, 'gmail', lambda: object())
    rules = [{'id': 'rule_1'}]
    monkeypatch.setattr(server, 'load_state', lambda: {'custom_rules': rules})
    
    def fake_search(**kwargs):
        return [{'id': '1', 'rules': kwargs.get('custom_rules', [])}]
    
    monkeypatch.setattr(server, 'search', fake_search)

    handler.handle_search('sender=example.com&max=5')

    assert handler.status_sent == 200
    assert response_json(handler) == {
        'status': 'ok',
        'emails': [{'id': '1', 'rules': rules}],
        'count': 1,
        'sender': 'example.com',
    }


def test_handle_search_converts_oauth_exception_to_json(monkeypatch):
    handler = DummyHandler()
    monkeypatch.setattr(server, 'GMAIL_OK', True)
    monkeypatch.setattr(server, 'CREDS', ExistingPath())
    monkeypatch.setattr(server, 'gmail', lambda: (_ for _ in ()).throw(RuntimeError('oauth cancelled')))
    monkeypatch.setattr(server, 'gmail_error_detail', lambda exc: str(exc))

    handler.handle_search('sender=example.com&max=5')

    assert handler.status_sent == 503
    assert response_json(handler) == {
        'status': 'error',
        'error': 'Error de autenticación Gmail',
        'detail': 'oauth cancelled',
    }


def test_handle_search_converts_gmail_exception(monkeypatch):
    handler = DummyHandler()
    monkeypatch.setattr(server, 'GMAIL_OK', True)
    monkeypatch.setattr(server, 'CREDS', ExistingPath())
    monkeypatch.setattr(server, 'gmail', lambda: object())

    monkeypatch.setattr(server, 'load_state', lambda: {'custom_rules': []})

    def fail(**kwargs):
        raise RuntimeError('gmail down')

    monkeypatch.setattr(server, 'search', fail)
    monkeypatch.setattr(server, 'gmail_error_detail', lambda exc: str(exc))

    handler.handle_search('sender=example.com&max=5')

    assert handler.status_sent == 502
    assert response_json(handler) == {
        'status': 'error',
        'error': 'Error consultando Gmail',
        'detail': 'gmail down',
    }


def test_handle_get_state_returns_local_state_without_gmail(monkeypatch):
    handler = DummyHandler()
    called = False

    def fake_gmail():
        nonlocal called
        called = True

    monkeypatch.setattr(server, 'gmail', fake_gmail)
    monkeypatch.setattr(server, 'load_state', lambda: {'version': 1, 'custom_sources': [], 'hidden_ids': [], 'preferences': {}})

    handler.handle_get_state()

    assert handler.status_sent == 200
    assert response_json(handler) == {
        'status': 'ok',
        'state': {'version': 1, 'custom_sources': [], 'hidden_ids': [], 'preferences': {}},
    }
    assert called is False


def test_handle_post_state_returns_normalized_state_without_gmail(monkeypatch):
    payload = {'state': {'custom_sources': [{'dom': 'web.dev'}], 'hidden_ids': ['abc']}}
    handler = DummyHandler(request_body(payload))
    called = False

    def fake_gmail():
        nonlocal called
        called = True

    def fake_save(state):
        assert state == payload['state']
        return {'version': 1, 'custom_sources': [{'dom': 'web.dev', 'label': 'web.dev', 'color': '#34d399', 'fixed': False}], 'hidden_ids': ['abc'], 'preferences': {}}

    monkeypatch.setattr(server, 'gmail', fake_gmail)
    monkeypatch.setattr(server, 'save_user_state', fake_save)

    handler.handle_post_state()

    assert handler.status_sent == 200
    assert response_json(handler)['state']['custom_sources'][0]['dom'] == 'web.dev'
    assert called is False


def test_handle_post_state_rejects_malformed_json():
    handler = DummyHandler(b'{bad')

    handler.handle_post_state()

    assert handler.status_sent == 400
    assert response_json(handler)['error'] == 'JSON inválido'


def test_handle_post_state_converts_validation_error(monkeypatch):
    handler = DummyHandler(request_body({'state': {'custom_sources': [{'dom': 'bad'}]}}))

    def fake_save(state):
        raise server.ApiError('Estado inválido', detail='Fuente inválida')

    monkeypatch.setattr(server, 'save_user_state', fake_save)

    handler.handle_post_state()

    assert handler.status_sent == 400
    assert response_json(handler) == {
        'status': 'error',
        'error': 'Estado inválido',
        'detail': 'Fuente inválida',
    }


def test_handle_ai_summary_returns_provider_result(monkeypatch):
    handler = DummyHandler(request_body({'prompt': 'Informe operativo'}))
    monkeypatch.setattr(server, 'summarize', lambda prompt: {'summary': f'Resumen: {prompt}', 'model': 'local'})

    handler.handle_ai_summary()

    assert handler.status_sent == 200
    assert response_json(handler) == {
        'status': 'ok',
        'summary': 'Resumen: Informe operativo',
        'model': 'local',
    }


def test_handle_ai_summary_converts_configuration_error(monkeypatch):
    handler = DummyHandler(request_body({'prompt': 'Informe operativo'}))

    def fail(prompt):
        raise server.ApiError('Integración AI no configurada', status=503)

    monkeypatch.setattr(server, 'summarize', fail)

    handler.handle_ai_summary()

    assert handler.status_sent == 503
    assert response_json(handler)['error'] == 'Integración AI no configurada'


def test_handle_attachment_rejects_invalid_params_before_gmail(monkeypatch):
    handler = DummyHandler()
    called = False

    def fake_gmail():
        nonlocal called
        called = True

    monkeypatch.setattr(server, 'gmail', fake_gmail)

    handler.handle_attachment('message_id=bad%20id&attachment_id=a1')

    assert handler.status_sent == 400
    assert response_json(handler)['error'] == 'Parámetro message_id inválido'
    assert called is False


def test_handle_attachment_streams_bytes(monkeypatch):
    handler = DummyHandler()
    monkeypatch.setattr(server, 'GMAIL_OK', True)
    monkeypatch.setattr(server, 'CREDS', ExistingPath())
    monkeypatch.setattr(server, 'gmail', lambda: object())
    monkeypatch.setattr(server, 'get_attachment', lambda message_id, attachment_id: b'PDF')

    handler.handle_attachment('message_id=m1&attachment_id=a1&filename=factura.pdf&mime_type=application/pdf')

    assert handler.status_sent == 200
    assert ('Content-Type', 'application/pdf') in handler.headers_sent
    assert ('Content-Disposition', 'attachment; filename="factura.pdf"') in handler.headers_sent
    assert handler.wfile.getvalue() == b'PDF'


def test_handle_message_returns_email_without_search(monkeypatch):
    handler = DummyHandler()
    monkeypatch.setattr(server, 'GMAIL_OK', True)
    monkeypatch.setattr(server, 'CREDS', ExistingPath())
    monkeypatch.setattr(server, 'gmail', lambda: object())
    monkeypatch.setattr(server, 'get_message', lambda message_id, custom_rules: {
        'id': message_id,
        'matched_rule_ids': [rule['id'] for rule in custom_rules],
        'attachments': [],
        'categories': ['warn'],
        'severity': 'high',
        'severity_reason': 'Aviso urgente o fallo detectado',
    })
    monkeypatch.setattr(server, 'load_state', lambda: {'custom_rules': []})

    handler.handle_message('message_id=m1')

    assert handler.status_sent == 200
    assert response_json(handler) == {
        'status': 'ok',
        'email': {
            'id': 'm1',
            'matched_rule_ids': [],
            'attachments': [],
            'categories': ['warn'],
            'severity': 'high',
            'severity_reason': 'Aviso urgente o fallo detectado',
        },
    }


def test_handle_hidden_only_resolves_persisted_hidden_ids(monkeypatch):
    handler = DummyHandler()
    monkeypatch.setattr(server, 'GMAIL_OK', True)
    monkeypatch.setattr(server, 'CREDS', ExistingPath())
    monkeypatch.setattr(server, 'gmail', lambda: object())
    monkeypatch.setattr(server, 'load_state', lambda: {'hidden_ids': ['m1', 'missing'], 'custom_rules': []})

    def fake_get(message_id, rules):
        if message_id == 'missing':
            raise RuntimeError('not found')
        return {'id': message_id, 'subject': 'Hidden'}

    monkeypatch.setattr(server, 'get_message', fake_get)

    handler.handle_hidden()

    body = response_json(handler)
    assert body['count'] == 2
    assert body['page'] == 1
    assert body['pages'] == 1
    assert body['total'] == 2
    assert body['page_size'] == 20
    assert body['messages'][0] == {'id': 'm1', 'status': 'available', 'email': {'id': 'm1', 'subject': 'Hidden'}}
    assert body['messages'][1] == {'id': 'missing', 'status': 'orphan', 'detail': 'not found'}


def test_handle_hidden_distinguishes_transient_lookup_failures(monkeypatch):
    handler = DummyHandler()
    monkeypatch.setattr(server, 'GMAIL_OK', True)
    monkeypatch.setattr(server, 'CREDS', ExistingPath())
    monkeypatch.setattr(server, 'gmail', lambda: object())
    monkeypatch.setattr(server, 'load_state', lambda: {'hidden_ids': ['m1', 'timeout'], 'custom_rules': []})

    def fake_get(message_id, rules):
        if message_id == 'timeout':
            raise RuntimeError('backend timeout')
        return {'id': message_id, 'subject': 'Hidden'}

    monkeypatch.setattr(server, 'get_message', fake_get)

    handler.handle_hidden()

    body = response_json(handler)
    assert body['messages'][1]['status'] == 'unavailable'
    assert body['messages'][1]['detail'] == 'backend timeout'


def test_handle_hidden_paginates_hidden_ids(monkeypatch):
    handler = DummyHandler()
    monkeypatch.setattr(server, 'GMAIL_OK', True)
    monkeypatch.setattr(server, 'CREDS', ExistingPath())
    monkeypatch.setattr(server, 'gmail', lambda: object())
    hidden_ids = [f'm{i}' for i in range(1, 25)]
    monkeypatch.setattr(server, 'load_state', lambda: {'hidden_ids': hidden_ids, 'custom_rules': []})

    seen = []

    def fake_get(message_id, rules):
        seen.append(message_id)
        return {'id': message_id, 'subject': message_id}

    monkeypatch.setattr(server, 'get_message', fake_get)
    monkeypatch.setattr(server, 'gmail_error_detail', lambda exc: str(exc))
    handler.path = '/api/hidden?page=2'

    handler.handle_hidden()

    body = response_json(handler)
    assert body['page'] == 2
    assert body['pages'] == 2
    assert body['total'] == 24
    assert body['start'] == 21
    assert body['end'] == 24
    assert seen == [f'm{i}' for i in range(21, 25)]
    assert [item['id'] for item in body['messages']] == [f'm{i}' for i in range(21, 25)]


def test_handle_delete_permanent_rejects_visible_message(monkeypatch):
    handler = DummyHandler(request_body({
        'ids': ['visible'],
        'confirmation': 'ELIMINAR PERMANENTEMENTE 1',
    }))
    monkeypatch.setattr(server, 'load_state', lambda: {'hidden_ids': ['hidden']})

    handler.handle_delete_permanent()

    assert handler.status_sent == 403
    assert response_json(handler)['error'] == 'Borrado rechazado'


def test_handle_delete_permanent_records_individual_results(monkeypatch):
    handler = DummyHandler(request_body({
        'ids': ['m1', 'm2'],
        'confirmation': 'ELIMINAR PERMANENTEMENTE 2',
    }))
    monkeypatch.setattr(server, 'load_state', lambda: {'hidden_ids': ['m1', 'm2']})
    results = [{'id': 'm1', 'status': 'deleted'}, {'id': 'm2', 'status': 'error', 'detail': 'not found'}]
    monkeypatch.setattr(server, 'permanently_delete_messages', lambda ids: results)
    monkeypatch.setattr(server, 'record_delete_results', lambda values: {'hidden_ids': ['m2'], 'deletion_audit': []})

    handler.handle_delete_permanent()

    body = response_json(handler)
    assert handler.status_sent == 200
    assert body['deleted'] == 1
    assert body['results'] == results
    assert body['state']['hidden_ids'] == ['m2']
    assert body['audit_error'] is None


def test_handle_delete_permanent_reports_audit_failure_without_hiding_results(monkeypatch):
    handler = DummyHandler(request_body({
        'ids': ['m1'],
        'confirmation': 'ELIMINAR PERMANENTEMENTE 1',
    }))
    monkeypatch.setattr(server, 'load_state', lambda: {'hidden_ids': ['m1']})
    results = [{'id': 'm1', 'status': 'deleted'}]
    monkeypatch.setattr(server, 'permanently_delete_messages', lambda ids: results)
    monkeypatch.setattr(
        server,
        'record_delete_results',
        lambda values: (_ for _ in ()).throw(OSError('disk full')),
    )

    handler.handle_delete_permanent()

    body = response_json(handler)
    assert handler.status_sent == 200
    assert body['results'] == results
    assert body['deleted'] == 1
    assert body['state'] is None
    assert 'No repitas la operación' in body['audit_error']


def test_handle_delete_revoke_returns_updated_state(monkeypatch):
    handler = DummyHandler(request_body({}))
    monkeypatch.setattr(server, 'revoke_destructive_authorization', lambda: {
        'enabled': True,
        'authorized': False,
        'available': True,
        'state': 'revoked',
        'token_present': False,
        'revoked': True,
        'scope': 'https://mail.google.com/',
        'max_batch': 100,
    })

    handler.handle_delete_revoke()

    body = response_json(handler)
    assert handler.status_sent == 200
    assert body['permanent_delete']['state'] == 'revoked'
    assert body['permanent_delete']['revoked'] is True


# Desde la Fase 29 (ADR-009) la exportación escribe en EXPORTS_DIR y responde JSON
# en lugar de transmitir el fichero como descarga del navegador.
def test_handle_messages_export_single_eml(monkeypatch, tmp_path):
    handler = DummyHandler(request_body({'message_ids': ['m1']}))
    monkeypatch.setattr(server, 'GMAIL_OK', True)
    monkeypatch.setattr(server, 'CREDS', ExistingPath())
    monkeypatch.setattr(server, 'gmail', lambda: object())
    monkeypatch.setattr(server, 'get_message_raw', lambda mid: b'EML DATA')
    monkeypatch.setattr(server, 'EXPORTS_DIR', tmp_path)

    handler.handle_messages_export()

    assert handler.status_sent == 200
    body = response_json(handler)
    assert body['status'] == 'ok'
    assert body['type'] == 'eml'
    assert body['file'] == 'm1.eml'
    assert (tmp_path / 'm1.eml').read_bytes() == b'EML DATA'


def test_handle_messages_export_zip(monkeypatch, tmp_path):
    handler = DummyHandler(request_body({'message_ids': ['m1', 'm2']}))
    monkeypatch.setattr(server, 'GMAIL_OK', True)
    monkeypatch.setattr(server, 'CREDS', ExistingPath())
    monkeypatch.setattr(server, 'gmail', lambda: object())
    monkeypatch.setattr(server, 'get_message_raw', lambda mid: f'EML {mid}'.encode())
    monkeypatch.setattr(server, 'EXPORTS_DIR', tmp_path)

    handler.handle_messages_export()

    assert handler.status_sent == 200
    body = response_json(handler)
    assert body['status'] == 'ok'
    assert body['type'] == 'zip'

    import zipfile
    with zipfile.ZipFile(tmp_path / body['file']) as zf:
        assert zf.namelist() == ['m1.eml', 'm2.eml']
        assert zf.read('m1.eml') == b'EML m1'
        assert zf.read('m2.eml') == b'EML m2'


# Fase 33 (MNT-03): archivado/etiquetado troceado internamente y acotado por lote.
def test_handle_messages_archive_chunks_and_hides(monkeypatch):
    ids = [f'm{i}' for i in range(150)]
    handler = DummyHandler(request_body({'message_ids': ids}))
    monkeypatch.setattr(server, 'GMAIL_OK', True)
    monkeypatch.setattr(server, 'CREDS', ExistingPath())
    monkeypatch.setattr(server, 'gmail', lambda: object())

    seen = {}

    def fake_archive(mids):
        seen['n'] = len(mids)
        return {'total': len(mids), 'chunks': 2}

    monkeypatch.setattr(server, 'archive_messages', fake_archive)
    monkeypatch.setattr(server, 'load_state', lambda: {'hidden_ids': [], 'custom_rules': []})
    monkeypatch.setattr(server, 'save_user_state', lambda state: None)

    handler.handle_messages_archive()

    body = response_json(handler)
    assert handler.status_sent == 200
    assert body['archived'] == 150
    assert body['chunks'] == 2
    assert body['hidden_added'] == 150
    assert seen['n'] == 150


def test_handle_messages_archive_rejects_oversized_batch(monkeypatch):
    ids = [f'm{i}' for i in range(server.MAX_BATCH_MODIFY + 1)]
    handler = DummyHandler(request_body({'message_ids': ids}))
    monkeypatch.setattr(server, 'GMAIL_OK', True)
    monkeypatch.setattr(server, 'CREDS', ExistingPath())

    called = []
    monkeypatch.setattr(server, 'archive_messages', lambda mids: called.append(mids))

    handler.handle_messages_archive()

    assert handler.status_sent == 400
    assert not called


def test_handle_messages_label_rejects_oversized_batch(monkeypatch):
    ids = [f'm{i}' for i in range(server.MAX_BATCH_MODIFY + 1)]
    handler = DummyHandler(request_body({'message_ids': ids, 'label_id': 'Label_1'}))
    monkeypatch.setattr(server, 'GMAIL_OK', True)
    monkeypatch.setattr(server, 'CREDS', ExistingPath())

    called = []
    monkeypatch.setattr(server, 'apply_label', lambda *a, **k: called.append(a))

    handler.handle_messages_label()

    assert handler.status_sent == 400
    assert not called

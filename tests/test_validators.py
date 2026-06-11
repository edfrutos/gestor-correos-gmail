import pytest

from validators import ApiError, parse_max, validate_attachment_id, validate_delete_request, validate_filename, validate_gmail_id, validate_mime_type, validate_sender


@pytest.mark.parametrize('raw,expected', [
    ('1', 1),
    ('30', 30),
    ('100', 100),
])
def test_parse_max_accepts_range(raw, expected):
    assert parse_max(raw) == expected


@pytest.mark.parametrize('raw', ['0', '101', 'abc', None])
def test_parse_max_rejects_invalid_values(raw):
    with pytest.raises(ApiError):
        parse_max(raw)


@pytest.mark.parametrize('raw,expected', [
    ('PLESK.COM', 'plesk.com'),
    ('@web.dev', 'web.dev'),
    ('aviso@example.com', 'aviso@example.com'),
    ('  cloudflare.com  ', 'cloudflare.com'),
])
def test_validate_sender_accepts_domains_and_emails(raw, expected):
    assert validate_sender(raw) == expected


@pytest.mark.parametrize('raw', ['', 'bad sender', 'http://example.com', 'localhost', 'a..b.com'])
def test_validate_sender_rejects_unsafe_values(raw):
    with pytest.raises(ApiError):
        validate_sender(raw)


def test_validate_gmail_id_accepts_safe_ids():
    assert validate_gmail_id('abc_123-XYZ', 'message_id') == 'abc_123-XYZ'


@pytest.mark.parametrize('raw', ['', '../x', 'abc 123', 'http://x'])
def test_validate_gmail_id_rejects_unsafe_ids(raw):
    with pytest.raises(ApiError):
        validate_gmail_id(raw, 'attachment_id')


def test_validate_attachment_id_accepts_gmail_attachment_tokens():
    value = 'ANGjdJ9.example/with+chars=and:colon'
    assert validate_attachment_id(value) == value


@pytest.mark.parametrize('raw', ['', 'bad id', 'x\nid', '<script>'])
def test_validate_attachment_id_rejects_empty_control_or_markup(raw):
    with pytest.raises(ApiError):
        validate_attachment_id(raw)


def test_validate_filename_strips_path_and_controls():
    assert validate_filename('../factura\n.pdf') == 'factura_.pdf'
    assert validate_filename('..\\secret.pdf') == 'secret.pdf'
    assert validate_filename('factura"; x=".pdf') == 'factura_; x=_.pdf'


def test_validate_mime_type_accepts_or_falls_back():
    assert validate_mime_type('application/pdf') == 'application/pdf'
    assert validate_mime_type('bad mime') == 'application/octet-stream'


def test_validate_delete_request_accepts_exact_confirmation_for_hidden_ids():
    assert validate_delete_request(
        {'ids': ['m1', 'm2'], 'confirmation': 'ELIMINAR PERMANENTEMENTE 2'},
        ['m1', 'm2', 'm3'],
    ) == ['m1', 'm2']


def test_validate_delete_request_accepts_batches_up_to_one_hundred():
    ids = [f'm{i}' for i in range(100)]

    assert validate_delete_request(
        {'ids': ids, 'confirmation': 'ELIMINAR PERMANENTEMENTE 100'},
        ids,
    ) == ids


@pytest.mark.parametrize('payload,detail', [
    ({'ids': ['visible'], 'confirmation': 'ELIMINAR PERMANENTEMENTE 1'}, 'Sólo se pueden borrar permanentemente mensajes ocultos'),
    ({'ids': ['m1'], 'confirmation': 'borrar'}, 'Escribe exactamente: ELIMINAR PERMANENTEMENTE 1'),
    ({'ids': [f'm{i}' for i in range(101)], 'confirmation': 'ELIMINAR PERMANENTEMENTE 101'}, 'Puedes borrar como máximo 100 mensajes por solicitud'),
])
def test_validate_delete_request_rejects_unsafe_requests(payload, detail):
    with pytest.raises(ApiError) as exc:
        validate_delete_request(payload, ['m1'])

    assert exc.value.detail == detail

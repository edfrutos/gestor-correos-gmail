import re
from pathlib import Path


class ApiError(ValueError):
    def __init__(self, message, status=400, detail=None):
        super().__init__(message)
        self.status = status
        self.detail = detail or message


def parse_max(raw):
    try:
        value = int(raw)
    except (TypeError, ValueError):
        raise ApiError('Parámetro max inválido', detail='max debe ser un número entre 1 y 100')
    if value < 1 or value > 100:
        raise ApiError('Parámetro max fuera de rango', detail='max debe estar entre 1 y 100')
    return value


def validate_sender(raw, required=True):
    sender = (raw or '').strip().lower().lstrip('@')
    if not sender:
        if required:
            raise ApiError('Parámetro sender requerido', detail='Indica un dominio o email')
        return ''

    label = r'[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?'
    domain_re = rf'{label}(?:\.{label})+'
    email_re = rf'[a-z0-9._%+-]+@{domain_re}'

    if re.fullmatch(domain_re, sender) or re.fullmatch(email_re, sender):
        return sender

    raise ApiError(
        'Parámetro sender inválido',
        detail='Usa un dominio o email simple, por ejemplo plesk.com o aviso@example.com'
    )


def validate_date(raw, name='fecha'):
    if not raw:
        return ''
    # Soportar YYYY-MM-DD y YYYY/MM/DD
    m = re.fullmatch(r'(\d{4})[-/](\d{2})[-/](\d{2})', raw.strip())
    if not m:
        raise ApiError(f'Parámetro {name} inválido', detail=f'{name} debe tener formato AAAA-MM-DD')
    return f"{m.group(1)}/{m.group(2)}/{m.group(3)}"


def validate_gmail_id(raw, name='id'):
    value = (raw or '').strip()
    if re.fullmatch(r'[A-Za-z0-9_-]{1,256}', value):
        return value
    raise ApiError(f'Parámetro {name} inválido', detail=f'{name} debe ser un identificador Gmail válido')


def validate_delete_request(payload, hidden_ids, max_batch=100):
    if not isinstance(payload, dict):
        raise ApiError('Solicitud de borrado inválida')
    raw_ids = payload.get('ids')
    if not isinstance(raw_ids, list) or not raw_ids:
        raise ApiError('Selecciona correos ocultos para borrar')
    ids = []
    for raw in raw_ids:
        message_id = validate_gmail_id(raw, 'id')
        if message_id not in ids:
            ids.append(message_id)
    if len(ids) > max_batch:
        raise ApiError('Lote de borrado demasiado grande', detail=f'Puedes borrar como máximo {max_batch} mensajes por solicitud')
    hidden = set(hidden_ids)
    if any(message_id not in hidden for message_id in ids):
        raise ApiError('Borrado rechazado', status=403, detail='Sólo se pueden borrar permanentemente mensajes ocultos')
    expected = f'ELIMINAR PERMANENTEMENTE {len(ids)}'
    if payload.get('confirmation') != expected:
        raise ApiError('Confirmación incorrecta', detail=f'Escribe exactamente: {expected}')
    return ids


def validate_attachment_id(raw):
    value = (raw or '').strip()
    if 1 <= len(value) <= 2048 and not re.search(r'[\x00-\x1f\x7f\s<>"`]', value):
        return value
    raise ApiError(
        'Parámetro attachment_id inválido',
        detail='attachment_id debe ser un identificador Gmail válido'
    )


def validate_filename(raw):
    value = Path((raw or 'adjunto').strip().replace('\\', '/')).name
    value = re.sub(r'[\x00-\x1f\x7f"\\]', '_', value)[:120]
    return value or 'adjunto'


def validate_mime_type(raw):
    value = (raw or 'application/octet-stream').strip().lower()
    if re.fullmatch(r'[a-z0-9][a-z0-9.+-]*/[a-z0-9][a-z0-9.+-]*', value):
        return value
    return 'application/octet-stream'

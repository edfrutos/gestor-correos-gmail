import json
import os
import threading
from pathlib import Path

from paths import data_path
from validators import ApiError

try:
    from google.auth.exceptions import RefreshError
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import InstalledAppFlow
    from googleapiclient.discovery import build
    GMAIL_DELETE_OK = True
except ImportError:
    RefreshError = None
    GMAIL_DELETE_OK = False


# Estado escribible: ver paths.py (proyecto desde fuente, Application Support en .app).
CREDS = data_path('credentials.json')
DELETE_TOKEN = data_path('delete_token.json')
DELETE_REVOKED = data_path('delete_token.revoked')
DELETE_SCOPES = ['https://mail.google.com/']
MAX_DELETE_BATCH = 100
DELETE_EXECUTION_CHUNK = 20

_delete_service = None
_service_lock = threading.Lock()
_delete_lock = threading.Lock()


def delete_enabled():
    return os.getenv('ENABLE_PERMANENT_DELETE', '').strip().lower() in {'1', 'true', 'yes'}


def delete_status():
    enabled = delete_enabled()
    token_state = 'disabled'
    token_present = DELETE_TOKEN.exists()
    revoked = DELETE_REVOKED.exists()
    creds = None

    if enabled and revoked:
        token_state = 'revoked'
    elif enabled and token_present and GMAIL_DELETE_OK:
        try:
            creds = Credentials.from_authorized_user_file(str(DELETE_TOKEN), DELETE_SCOPES)
            if creds.valid:
                token_state = 'valid'
            elif creds.expired and creds.refresh_token:
                token_state = 'expired'
            else:
                token_state = 'revoked'
        except (ValueError, json.JSONDecodeError):
            token_state = 'revoked'
    elif enabled and token_present:
        token_state = 'unavailable'
    elif enabled:
        token_state = 'missing'

    return {
        'enabled': enabled,
        'authorized': enabled and token_state in {'valid', 'expired'},
        'available': GMAIL_DELETE_OK and CREDS.exists(),
        'state': token_state if enabled else 'disabled',
        'token_present': token_present,
        'revoked': revoked,
        'scope': DELETE_SCOPES[0],
        'max_batch': MAX_DELETE_BATCH,
    }


def _write_delete_token(payload):
    tmp = DELETE_TOKEN.with_name(DELETE_TOKEN.name + '.tmp')
    tmp.write_text(payload, encoding='utf-8')
    tmp.chmod(0o600)
    tmp.replace(DELETE_TOKEN)


def _discard_delete_token():
    DELETE_TOKEN.unlink(missing_ok=True)


def _mark_delete_revoked():
    tmp = DELETE_REVOKED.with_name(DELETE_REVOKED.name + '.tmp')
    tmp.write_text('revoked\n', encoding='utf-8')
    tmp.chmod(0o600)
    tmp.replace(DELETE_REVOKED)


def _clear_delete_revoked():
    DELETE_REVOKED.unlink(missing_ok=True)


def revoke_destructive_authorization():
    global _delete_service
    with _service_lock:
        _delete_service = None
        _discard_delete_token()
        _mark_delete_revoked()
    return delete_status()


def destructive_gmail(allow_authorize=False):
    global _delete_service
    if not delete_enabled():
        raise ApiError(
            'Borrado permanente deshabilitado',
            status=503,
            detail='Reinicia con ENABLE_PERMANENT_DELETE=1 para habilitar la autorización destructiva'
        )
    if not GMAIL_DELETE_OK:
        raise ApiError('Dependencias Gmail no instaladas', status=503)
    if not CREDS.exists():
        raise ApiError('Sin credentials.json', status=503)
    if _delete_service:
        return _delete_service

    with _service_lock:
        if _delete_service:
            return _delete_service
        if DELETE_REVOKED.exists() and not allow_authorize:
            raise ApiError(
                'Borrado permanente revocado',
                status=503,
                detail='Revoca explícitamente la autorización destructiva para limpiar el acceso, o vuelve a autorizarla'
            )
        creds = None
        if DELETE_TOKEN.exists() and not DELETE_REVOKED.exists():
            try:
                creds = Credentials.from_authorized_user_file(str(DELETE_TOKEN), DELETE_SCOPES)
            except (ValueError, json.JSONDecodeError):
                _discard_delete_token()
        if creds and not creds.valid and creds.expired and creds.refresh_token:
            try:
                creds.refresh(Request())
            except RefreshError:
                _discard_delete_token()
                creds = None

        if not creds or not creds.valid:
            if not allow_authorize:
                raise ApiError(
                    'Borrado permanente no autorizado',
                    status=503,
                    detail='Autoriza explícitamente el token destructivo antes de borrar'
                )
            flow = InstalledAppFlow.from_client_secrets_file(str(CREDS), DELETE_SCOPES)
            creds = flow.run_local_server(port=0)

        _write_delete_token(creds.to_json())
        _clear_delete_revoked()
        _delete_service = build('gmail', 'v1', credentials=creds)
        return _delete_service


def permanently_delete_messages(message_ids):
    service = destructive_gmail()
    results = []
    with _delete_lock:
        ids = list(message_ids)
        for start in range(0, len(ids), DELETE_EXECUTION_CHUNK):
            batch = ids[start:start + DELETE_EXECUTION_CHUNK]
            for message_id in batch:
                try:
                    service.users().messages().delete(userId='me', id=message_id).execute()
                    results.append({'id': message_id, 'status': 'deleted'})
                except Exception as exc:
                    results.append({'id': message_id, 'status': 'error', 'detail': str(exc)[:300]})
    return results

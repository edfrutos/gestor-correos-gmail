import json
import os
import re
import base64
import threading
from email.utils import parseaddr
from pathlib import Path

from classifier import classify_metadata
from paths import data_path

try:
    from google.auth.transport.requests import Request
    from google.auth.exceptions import RefreshError
    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import InstalledAppFlow
    from googleapiclient.discovery import build
    from googleapiclient.errors import HttpError
    GMAIL_OK = True
except ImportError:
    HttpError = None
    RefreshError = None
    GMAIL_OK = False


SCOPES = ['https://www.googleapis.com/auth/gmail.modify']
# Estado escribible: carpeta del proyecto desde el código fuente,
# ~/Library/Application Support/GestorDeCorreos/ dentro del .app (ver paths.py).
CREDS = data_path('credentials.json')
TOKEN = data_path('token.json')

# Gmail acepta como máximo 1000 IDs por llamada a users.messages.batchModify.
# Troceamos en lotes menores para acotar el tamaño de cada petición, permitir
# lotes grandes desde la UI y mantener las llamadas serializadas bajo _api_lock.
BATCH_MODIFY_CHUNK = 100
MAX_BATCH_MODIFY = 1000

_svc = None
_svc_lock = threading.Lock()
_api_lock = threading.Lock()


def _write_token(payload):
    tmp = TOKEN.with_name(TOKEN.name + '.tmp')
    tmp.write_text(payload, encoding='utf-8')
    tmp.chmod(0o600)
    tmp.replace(TOKEN)


def _discard_token():
    TOKEN.unlink(missing_ok=True)


def gmail():
    global _svc
    if _svc:
        return _svc
    if not GMAIL_OK:
        return None
    with _svc_lock:
        if _svc:
            return _svc

        creds = None
        if TOKEN.exists():
            try:
                creds = Credentials.from_authorized_user_file(str(TOKEN), SCOPES)
            except (ValueError, json.JSONDecodeError):
                _discard_token()

        if creds and not creds.valid and creds.expired and creds.refresh_token:
            try:
                creds.refresh(Request())
            except RefreshError:
                _discard_token()
                creds = None

        if not creds or not creds.valid:
            if not CREDS.exists():
                return None
            flow = InstalledAppFlow.from_client_secrets_file(str(CREDS), SCOPES)
            headless = os.getenv('HEADLESS') == '1'
            creds = flow.run_local_server(port=0, open_browser=not headless)

        _write_token(creds.to_json())
        _svc = build('gmail', 'v1', credentials=creds)
        return _svc


def gmail_status():
    if not GMAIL_OK:
        return {
            'ok': False,
            'can_search': False,
            'gmail_lib': False,
            'credentials': CREDS.exists(),
            'token': TOKEN.exists(),
            'msg': 'Instala dependencias de Gmail',
        }
    if not CREDS.exists():
        return {
            'ok': False,
            'can_search': False,
            'gmail_lib': True,
            'credentials': False,
            'token': TOKEN.exists(),
            'msg': 'Necesitas credentials.json en la carpeta',
        }
    if not TOKEN.exists():
        return {
            'ok': False,
            'can_search': True,
            'gmail_lib': True,
            'credentials': True,
            'token': False,
            'msg': 'Pendiente de autenticación: la primera búsqueda abrirá Google',
        }
    return {
        'ok': True,
        'can_search': True,
        'gmail_lib': True,
        'credentials': True,
        'token': True,
        'msg': 'Token presente; se comprobará al buscar',
    }


def tag(frm):
    m = re.search(r'@([\w.-]+)', frm)
    if not m:
        return 'Email'
    parts = m.group(1).split('.')
    return parts[0].capitalize() + ' · Email'


def gmail_error_detail(exc):
    if RefreshError is not None and isinstance(exc, RefreshError):
        return 'La autorización Gmail expiró o fue revocada. Vuelve a autorizar la cuenta en la próxima búsqueda.'
    if not GMAIL_OK or HttpError is None or not isinstance(exc, HttpError):
        return str(exc)
    try:
        payload = json.loads(exc.content.decode('utf-8'))
        err = payload.get('error', {})
        msg = err.get('message') or str(exc)
        if err.get('status') == 'PERMISSION_DENIED' or err.get('code') == 403:
            return (
                msg +
                ' Activa Gmail API en el proyecto OAuth de credentials.json y reinicia la app.'
            )
        return msg
    except Exception:
        return str(exc)


def gmail_message_lookup_state(exc):
    detail = gmail_error_detail(exc)
    text = detail.lower()
    if (
        'not found' in text
        or 'no encontrado' in text
        or 'requested entity was not found' in text
    ):
        return {'status': 'orphan', 'detail': detail}
    if GMAIL_OK and HttpError is not None and isinstance(exc, HttpError):
        status = None
        try:
            status = getattr(exc.resp, 'status', None)
        except Exception:
            status = None
        if status in (404, 410):
            return {'status': 'orphan', 'detail': detail}
    return {'status': 'unavailable', 'detail': detail}


def norm_date(raw):
    import email.utils
    try:
        t = email.utils.parsedate_to_datetime(raw)
        return t.strftime('%Y-%m-%d')
    except Exception:
        m = re.search(r'(\d{4}-\d{2}-\d{2})', raw)
        return m.group(1) if m else raw[:10]


def _decode_snippet(value):
    return (
        value.replace('&#39;', "'")
        .replace('&amp;', '&')
        .replace('&lt;', '<')
        .replace('&gt;', '>')
    )


def _attachments_from_payload(payload):
    out = []
    for part in payload.get('parts', []) or []:
        filename = (part.get('filename') or '').strip()
        body = part.get('body', {}) or {}
        attachment_id = body.get('attachmentId')
        if filename and attachment_id:
            out.append({
                'attachment_id': attachment_id,
                'filename': filename,
                'mime_type': part.get('mimeType') or 'application/octet-stream',
                'size': body.get('size') or 0,
            })
        out.extend(_attachments_from_payload(part))
    return out


def _message_from_gmail(msg, custom_rules=None):
    headers = {
        x['name'].lower(): x['value']
        for x in msg.get('payload', {}).get('headers', [])
    }
    snip = _decode_snippet(msg.get('snippet', ''))
    attachments = _attachments_from_payload(msg.get('payload', {}))
    metadata = classify_metadata({
        'subject': headers.get('subject', '(sin asunto)'),
        'body': snip,
        'from': headers.get('from', ''),
        'tag': tag(headers.get('from', '')),
    }, custom_rules)
    return {
        'id': msg['id'],
        'date': norm_date(headers.get('date', '')),
        'from': headers.get('from', ''),
        'to': headers.get('to', ''),
        'cc': headers.get('cc', ''),
        'subject': headers.get('subject', '(sin asunto)'),
        'snippet': snip,
        'body': snip,
        'tag': tag(headers.get('from', '')),
        'src': 'cu',
        'categories': metadata['categories'],
        'severity': metadata['severity'],
        'severity_reason': metadata['severity_reason'],
        'matched_rule_ids': metadata['matched_rule_ids'],
        'attachments': attachments,
        'attachments_checked': True,
    }


def _sender_matches(from_header, sender):
    address = parseaddr(from_header or '')[1].lower()
    if '@' not in address:
        return False
    if '@' in sender:
        return address == sender
    domain = address.rsplit('@', 1)[1]
    return domain == sender or domain.endswith('.' + sender)


def get_message(message_id, custom_rules=None):
    svc = gmail()
    if not svc:
        return None
    with _api_lock:
        msg = svc.users().messages().get(
            userId='me',
            id=message_id,
            format='full',
            metadataHeaders=['From', 'To', 'Cc', 'Subject', 'Date'],
        ).execute()
    return _message_from_gmail(msg, custom_rules)


def search(sender='', after='', before='', q='', max_r=30, custom_rules=None):
    svc = gmail()
    if not svc:
        return []

    parts = []
    if sender: parts.append(f'from:{sender}')
    if after: parts.append(f'after:{after}')
    if before: parts.append(f'before:{before}')
    if q: parts.append(f'"{q}"' if ' ' in q else q)
    
    query = ' '.join(parts)
    if not query:
        return []

    out = []
    with _api_lock:
        resp = svc.users().threads().list(userId='me', q=query, maxResults=max_r).execute()
        for thread_ref in resp.get('threads', []):
            thread = svc.users().threads().get(
                userId='me',
                id=thread_ref['id'],
                format='full',
                metadataHeaders=['From', 'To', 'Cc', 'Subject', 'Date'],
            ).execute()
            for msg in thread.get('messages', []):
                headers = {
                    item.get('name', '').lower(): item.get('value', '')
                    for item in msg.get('payload', {}).get('headers', [])
                }
                
                # Filtrado interno riguroso
                if sender and not _sender_matches(headers.get('from', ''), sender):
                    continue
                
                msg_date = norm_date(headers.get('date', ''))
                if after and msg_date < after.replace('/', '-'):
                    continue
                if before and msg_date > before.replace('/', '-'):
                    continue

                out.append(_message_from_gmail(msg, custom_rules))
                if len(out) >= max_r:
                    return out
    return out


def _batch_modify_chunked(message_ids, body_extra):
    """Aplica batchModify en tandas de BATCH_MODIFY_CHUNK bajo _api_lock.

    Devuelve un resumen {'total', 'chunks'} en vez de la respuesta cruda de
    Gmail (batchModify responde cuerpo vacío). Cualquier error en una tanda se
    propaga: las tandas anteriores ya se habrán aplicado en Gmail.
    """
    svc = gmail()
    if not svc:
        return None
    ids = list(message_ids)
    chunks = 0
    with _api_lock:
        for start in range(0, len(ids), BATCH_MODIFY_CHUNK):
            batch = ids[start:start + BATCH_MODIFY_CHUNK]
            body = {'ids': batch}
            body.update(body_extra)
            svc.users().messages().batchModify(userId='me', body=body).execute()
            chunks += 1
    return {'total': len(ids), 'chunks': chunks}


def archive_messages(message_ids):
    return _batch_modify_chunked(message_ids, {'removeLabelIds': ['INBOX']})


def get_labels():
    svc = gmail()
    if not svc:
        return []
    with _api_lock:
        resp = svc.users().labels().list(userId='me').execute()
        labels = resp.get('labels', [])
        return [
            {'id': l['id'], 'name': l['name']}
            for l in labels if l.get('type') == 'user'
        ]


def create_label(name):
    svc = gmail()
    if not svc:
        return None
    with _api_lock:
        return svc.users().labels().create(
            userId='me',
            body={
                'name': name,
                'labelListVisibility': 'labelShow',
                'messageListVisibility': 'show'
            }
        ).execute()


def apply_label(message_ids, label_id, archive=False):
    body_extra = {'addLabelIds': [label_id]}
    if archive:
        body_extra['removeLabelIds'] = ['INBOX']
    return _batch_modify_chunked(message_ids, body_extra)


def get_attachment(message_id, attachment_id):
    svc = gmail()
    if not svc:
        return b''
    with _api_lock:
        data = svc.users().messages().attachments().get(
            userId='me',
            messageId=message_id,
            id=attachment_id,
        ).execute().get('data', '')
    padding = '=' * (-len(data) % 4)
    return base64.urlsafe_b64decode((data + padding).encode('ascii'))


def search_message_ids_by_query(query, max_r=500):
    svc = gmail()
    if not svc:
        return []
    with _api_lock:
        resp = svc.users().messages().list(userId='me', q=query, maxResults=max_r).execute()
        return [m['id'] for m in resp.get('messages', [])]


def get_message_raw(message_id):
    svc = gmail()
    if not svc:
        return None
    with _api_lock:
        msg = svc.users().messages().get(
            userId='me',
            id=message_id,
            format='raw',
        ).execute()
    data = msg.get('raw', '')
    if not data:
        return b''
    return base64.urlsafe_b64decode(data.encode('ascii'))

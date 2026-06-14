#!/usr/bin/env python3
"""
Gestor de Correos — Servidor Local
Puente entre el HTML y la API de Gmail (OAuth2).

REQUISITOS:
    python3 -m venv .venv
    .venv/bin/python -m pip install -r requirements.txt

USO:
    1. Coloca credentials.json en esta carpeta (descárgalo de Google Cloud Console)
    2. .venv/bin/python server.py
    3. Abre http://localhost:8765 en tu navegador
    4. La primera búsqueda abrirá el navegador para autorizar Gmail
"""

import io
import base64
import json
import os
import threading
import time
import webbrowser
import zipfile
import mimetypes
import email
from email import policy
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from ai_client import ai_status, suggest_rules, summarize
from classifier import get_base_config
from destructive_gmail import MAX_DELETE_BATCH, delete_status, destructive_gmail, permanently_delete_messages, revoke_destructive_authorization
from gmail_client import CREDS, GMAIL_OK, apply_label, archive_messages, create_label, get_attachment, get_labels, get_message, get_message_raw, gmail, gmail_error_detail, gmail_message_lookup_state, gmail_status, search, search_message_ids_by_query
from storage import load_state, record_delete_results, save_user_state
from validators import ApiError, parse_max, validate_attachment_id, validate_date, validate_delete_request, validate_filename, validate_gmail_id, validate_mime_type, validate_sender


def load_env():
    env_file = Path(__file__).parent / '.env'
    if not env_file.exists():
        return
    for line in env_file.read_text(encoding='utf-8').splitlines():
        line = line.strip()
        if not line or line.startswith('#') or '=' not in line:
            continue
        key, value = line.split('=', 1)
        os.environ.setdefault(key.strip(), value.strip())


# Cargar variables de entorno desde .env si existe
load_env()

# Configuración desde entorno
HOST = os.getenv('HOST', 'localhost')
PORT = int(os.getenv('PORT', 8765))
HEADLESS = os.getenv('HEADLESS') == '1'
ENV_ORIGINS = os.getenv('ALLOWED_ORIGINS', '').split(',')

BASE_DIR = Path(__file__).parent
EXPORTS_DIR = BASE_DIR / 'exports'
EXPORTS_DIR.mkdir(exist_ok=True)
HIDDEN_PAGE_SIZE = 20
STATIC_FILES = {
    '/static/app.css': ('text/css; charset=utf-8', BASE_DIR / 'static' / 'app.css'),
    '/static/app.js': ('text/javascript; charset=utf-8', BASE_DIR / 'static' / 'app.js'),
    '/static/summary.js': ('text/javascript; charset=utf-8', BASE_DIR / 'static' / 'summary.js'),
    '/static/logo.svg': ('image/svg+xml', BASE_DIR / 'static' / 'logo.svg'),
    '/static/favicon.svg': ('image/svg+xml', BASE_DIR / 'static' / 'favicon.svg'),
}
def _header_hostname(value):
    try:
        return urlparse(f'//{value}').hostname
    except ValueError:
        return None


LOCAL_HOSTS = {'localhost', '127.0.0.1', '::1', HOST}
LOCAL_ORIGINS = {
    f'http://localhost:{PORT}',
    f'http://127.0.0.1:{PORT}',
    f'http://[::1]:{PORT}',
}
if HOST != 'localhost':
    LOCAL_ORIGINS.add(f'http://{HOST}:{PORT}')

for o in ENV_ORIGINS:
    o = o.strip().rstrip('/')   # normalizar: el header Origin nunca lleva barra final
    if not o: continue
    if not o.startswith('http'):
        LOCAL_ORIGINS.add(f'http://{o}')
        LOCAL_HOSTS.add(_header_hostname(o) or o.split(':')[0])
    else:
        LOCAL_ORIGINS.add(o)
        LOCAL_HOSTS.add(_header_hostname(urlparse(o).netloc) or urlparse(o).hostname)



def _parse_page(raw, name='page'):
    value = (raw or '1').strip()
    try:
        page = int(value)
    except ValueError:
        raise ApiError(f'Parámetro {name} inválido', detail=f'{name} debe ser un número entero positivo')
    if page < 1:
        raise ApiError(f'Parámetro {name} inválido', detail=f'{name} debe ser un número entero positivo')
    return page


class H(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def do_OPTIONS(self):
        if not self.request_is_local():
            return self.err(403, 'Origen no autorizado', 'La API sólo acepta peticiones desde la interfaz local')
        self.send_response(204)
        self.end_headers()

    def do_GET(self):
        if not self.request_is_local():
            return self.err(403, 'Origen no autorizado', 'La API sólo acepta peticiones desde la interfaz local')
        p = urlparse(self.path)

        if p.path in ('/', '/index.html'):
            return self.serve_index()

        if p.path in STATIC_FILES:
            return self.serve_static(p.path)

        if p.path == '/api/search':
            return self.handle_search(p.query)

        if p.path == '/api/status':
            return self.j({'status': 'ok', **gmail_status(), 'ai': ai_status(), 'permanent_delete': delete_status()})

        if p.path == '/api/config':
            return self.j({'status': 'ok', 'config': get_base_config()})

        if p.path == '/api/labels':
            return self.handle_get_labels()

        if p.path == '/api/state':
            return self.handle_get_state()

        if p.path == '/api/attachment':
            return self.handle_attachment(p.query)

        if p.path == '/api/message':
            return self.handle_message(p.query)

        if p.path == '/api/hidden':
            return self.handle_hidden()

        if p.path == '/api/exports':
            return self.handle_get_exports()

        if p.path == '/api/read-eml':
            return self.handle_read_eml(p.query)

        self.send_error(404)

    def do_POST(self):
        if not self.request_is_local():
            return self.err(403, 'Origen no autorizado', 'La API sólo acepta peticiones desde la interfaz local')
        p = urlparse(self.path)

        if p.path == '/api/read-eml':
            return self.handle_post_read_eml()

        if p.path == '/api/state':
            return self.handle_post_state()

        if p.path == '/api/ai-summary':
            return self.handle_ai_summary()

        if p.path == '/api/delete-authorize':
            return self.handle_delete_authorize()

        if p.path == '/api/delete-revoke':
            return self.handle_delete_revoke()

        if p.path == '/api/delete-permanent':
            return self.handle_delete_permanent()

        if p.path == '/api/messages/export':
            return self.handle_messages_export()

        if p.path == '/api/labels':
            return self.handle_post_labels()

        if p.path == '/api/messages/archive':
            return self.handle_messages_archive()

        if p.path == '/api/messages/label':
            return self.handle_messages_label()

        if p.path == '/api/ai-suggest-rules':
            return self.handle_ai_suggest_rules()

        self.send_error(404)

    def request_is_local(self):
        host = self.headers.get('Host', '')
        if _header_hostname(host) not in LOCAL_HOSTS:
            return False
        origin = self.headers.get('Origin')
        return origin is None or origin in LOCAL_ORIGINS

    def serve_index(self):
        return self.serve_file(BASE_DIR / 'index.html', 'text/html; charset=utf-8')

    def serve_static(self, path):
        content_type, file_path = STATIC_FILES[path]
        return self.serve_file(file_path, content_type)

    def serve_file(self, f, content_type):
        if not f.exists():
            self.send_error(404, f'{f.name} not found')
            return
        b = f.read_bytes()
        self.send_response(200)
        self.send_header('Content-Type', content_type)
        self.send_header('Content-Length', len(b))
        self.send_header('X-Content-Type-Options', 'nosniff')
        self.end_headers()
        self.write_body(b)

    def write_body(self, body):
        try:
            self.wfile.write(body)
        except (BrokenPipeError, ConnectionResetError):
            return False
        return True

    def require_gmail(self):
        if not GMAIL_OK:
            self.err(503, 'Dependencias Gmail no instaladas', 'Instala: .venv/bin/python -m pip install -r requirements.txt')
            return None
        if not CREDS.exists():
            self.err(503, 'Sin credentials.json', 'Coloca credentials.json junto a server.py')
            return None
        try:
            service = gmail()
        except Exception as e:
            detail = gmail_error_detail(e)
            print(f'[Gmail OAuth] {detail}')
            self.err(503, 'Error de autenticación Gmail', detail)
            return None
        if not service:
            self.err(503, 'Sin conexión Gmail', 'Revisa credentials.json y la autorización OAuth')
            return None
        return service

    def handle_search(self, query):
        qs = parse_qs(query)
        try:
            sender = validate_sender(qs.get('sender', [''])[0], required=False)
            q = qs.get('q', [''])[0].strip()
            after = validate_date(qs.get('after', [''])[0], 'after')
            before = validate_date(qs.get('before', [''])[0], 'before')
            max_r = parse_max(qs.get('max', ['30'])[0])
            
            if not any([sender, q, after, before]):
                raise ApiError('Búsqueda vacía', detail='Indica un remitente, rango de fechas o texto literal')
        except ApiError as e:
            return self.err(e.status, str(e), e.detail)

        if not self.require_gmail():
            return

        print(f'[API] Buscando: from:{sender or "*"} after:{after} before:{before} q:{q}')
        try:
            custom_rules = load_state().get('custom_rules', [])
            emails = search(sender=sender, after=after, before=before, q=q, max_r=max_r, custom_rules=custom_rules)
            
            # Auto-action logic
            to_label = {} # {label_id: [message_ids]}
            to_archive = set()
            for e in emails:
                for rule_id in e.get('matched_rule_ids', []):
                    rule = next((r for r in custom_rules if r.get('id') == rule_id), None)
                    if not rule: continue
                    
                    if rule.get('auto_label') and rule.get('gmail_label_id'):
                        lid = rule['gmail_label_id']
                        if lid not in to_label: to_label[lid] = []
                        to_label[lid].append(e['id'])
                    
                    if rule.get('auto_archive'):
                        to_archive.add(e['id'])
            
            # Apply combined actions
            state = load_state()
            hidden_ids = state.get('hidden_ids', [])
            hidden_set = set(hidden_ids)
            state_changed = False

            # Group by what needs to be done:
            # Case 1: Label + Archive (remove INBOX)
            # Case 2: Just Label
            # Case 3: Just Archive
            
            # Simplified: process labelings (some might also be in to_archive)
            for lid, ids in to_label.items():
                # For each ID in this label group, check if it also needs archiving
                sub_archive = [mid for mid in ids if mid in to_archive]
                sub_label_only = [mid for mid in ids if mid not in to_archive]
                
                if sub_archive:
                    print(f'[Auto-Action] Label "{lid}" + Archive {len(sub_archive)} correos')
                    try: apply_label(sub_archive, lid, archive=True)
                    except Exception as le: print(f'[Auto-Action] Error labeling/archiving: {le}')
                
                if sub_label_only:
                    print(f'[Auto-Action] Label "{lid}" {len(sub_label_only)} correos')
                    try: apply_label(sub_label_only, lid)
                    except Exception as le: print(f'[Auto-Action] Error labeling: {le}')

            # Case 3: Archive only (no label linked or label rule didn't trigger auto_label)
            archive_only = [mid for mid in to_archive if not any(mid in ids for ids in to_label.values())]
            if archive_only:
                print(f'[Auto-Action] Archive {len(archive_only)} correos')
                try: archive_messages(archive_only)
                except Exception as ae: print(f'[Auto-Action] Error archiving: {ae}')

            # Update local state for all archived ones
            for mid in to_archive:
                if mid not in hidden_set:
                    hidden_ids.append(mid)
                    hidden_set.add(mid)
                    state_changed = True
            
            if state_changed:
                state['hidden_ids'] = hidden_ids
                save_user_state(state)

            # Filter response: don't show archived emails in main view
            if to_archive:
                emails = [e for e in emails if e['id'] not in to_archive]

        except Exception as e:
            detail = gmail_error_detail(e)
            print(f'[Gmail] {detail}')
            return self.err(502, 'Error consultando Gmail', detail)
        print(f'[API] → {len(emails)} correos')
        return self.j({'status': 'ok', 'emails': emails, 'count': len(emails), 'sender': sender})

    def read_json_body(self):
        try:
            size = int(self.headers.get('Content-Length', '0'))
        except ValueError:
            raise ApiError('Content-Length inválido')
        if size < 1:
            raise ApiError('JSON requerido', detail='Envía un cuerpo JSON')
        if size > 65536:
            raise ApiError('JSON demasiado grande', status=413, detail='El estado local supera el límite permitido')
        raw = self.rfile.read(size)
        try:
            return json.loads(raw.decode('utf-8'))
        except (UnicodeDecodeError, json.JSONDecodeError):
            raise ApiError('JSON inválido', detail='El cuerpo de la petición no es JSON válido')

    def handle_get_state(self):
        try:
            state = load_state()
        except ApiError as e:
            return self.err(e.status, str(e), e.detail)
        return self.j({'status': 'ok', 'state': state})

    def handle_post_state(self):
        try:
            payload = self.read_json_body()
            candidate = payload.get('state', payload) if isinstance(payload, dict) else payload
            state = save_user_state(candidate)
        except ApiError as e:
            return self.err(e.status, str(e), e.detail)
        return self.j({'status': 'ok', 'state': state})

    def handle_ai_summary(self):
        try:
            payload = self.read_json_body()
            if not isinstance(payload, dict):
                raise ApiError('JSON AI inválido', detail='Envía un objeto JSON')
            result = summarize(payload.get('prompt', ''))
        except ApiError as e:
            return self.err(e.status, str(e), e.detail)
        return self.j({'status': 'ok', **result})

    def handle_attachment(self, query):
        qs = parse_qs(query)
        try:
            message_id = validate_gmail_id(qs.get('message_id', [''])[0], 'message_id')
            attachment_id = validate_attachment_id(qs.get('attachment_id', [''])[0])
            filename = validate_filename(qs.get('filename', ['adjunto'])[0])
            mime_type = validate_mime_type(qs.get('mime_type', ['application/octet-stream'])[0])
        except ApiError as e:
            return self.err(e.status, str(e), e.detail)

        if not self.require_gmail():
            return

        try:
            data = get_attachment(message_id, attachment_id)
        except Exception as e:
            detail = gmail_error_detail(e)
            print(f'[Gmail] {detail}')
            return self.err(502, 'Error descargando adjunto', detail)

        self.send_response(200)
        self.send_header('Content-Type', mime_type)
        self.send_header('Content-Length', len(data))
        self.send_header('Content-Disposition', f'attachment; filename="{filename}"')
        self.send_header('X-Content-Type-Options', 'nosniff')
        self.end_headers()
        self.write_body(data)

    def handle_message(self, query):
        qs = parse_qs(query)
        try:
            message_id = validate_gmail_id(qs.get('message_id', [''])[0], 'message_id')
        except ApiError as e:
            return self.err(e.status, str(e), e.detail)

        if not self.require_gmail():
            return

        try:
            custom_rules = load_state().get('custom_rules', [])
            email = get_message(message_id, custom_rules)
        except Exception as e:
            detail = gmail_error_detail(e)
            print(f'[Gmail] {detail}')
            return self.err(502, 'Error consultando Gmail', detail)
        return self.j({'status': 'ok', 'email': email})

    def handle_hidden(self):
        if not self.require_gmail():
            return
        try:
            state = load_state()
            rules = state.get('custom_rules', [])
            hidden_ids = state.get('hidden_ids', [])
            hidden_path = getattr(self, 'path', '/api/hidden')
            qs = parse_qs(urlparse(hidden_path).query)
            page = _parse_page(qs.get('page', ['1'])[0])
            search_query = qs.get('q', [''])[0].strip()

            if search_query:
                matched_ids = search_message_ids_by_query(search_query)
                hidden_set = set(hidden_ids)
                hidden_ids = [mid for mid in matched_ids if mid in hidden_set]

            total = len(hidden_ids)
            pages = max(1, (total + HIDDEN_PAGE_SIZE - 1) // HIDDEN_PAGE_SIZE)
            page = min(page, pages)
            start = (page - 1) * HIDDEN_PAGE_SIZE
            end = min(start + HIDDEN_PAGE_SIZE, total)
            messages = []
            for message_id in hidden_ids[start:end]:
                try:
                    email = get_message(message_id, rules)
                    messages.append({'id': message_id, 'status': 'available', 'email': email})
                except Exception as exc:
                    state = gmail_message_lookup_state(exc)
                    messages.append({'id': message_id, 'status': state['status'], 'detail': state['detail']})
        except ApiError as exc:
            return self.err(exc.status, str(exc), exc.detail)
        return self.j({
            'status': 'ok',
            'messages': messages,
            'count': len(messages),
            'page': page,
            'page_size': HIDDEN_PAGE_SIZE,
            'total': total,
            'pages': pages,
            'start': start + 1 if total else 0,
            'end': end,
        })

    def handle_delete_authorize(self):
        try:
            destructive_gmail(allow_authorize=True)
        except ApiError as exc:
            return self.err(exc.status, str(exc), exc.detail)
        except Exception as exc:
            return self.err(503, 'No se pudo autorizar el borrado permanente', gmail_error_detail(exc))
        return self.j({'status': 'ok', 'permanent_delete': delete_status()})

    def handle_delete_revoke(self):
        try:
            state = revoke_destructive_authorization()
        except ApiError as exc:
            return self.err(exc.status, str(exc), exc.detail)
        except Exception as exc:
            return self.err(503, 'No se pudo revocar el borrado permanente', gmail_error_detail(exc))
        return self.j({'status': 'ok', 'permanent_delete': state})

    def handle_delete_permanent(self):
        try:
            payload = self.read_json_body()
            state = load_state()
            ids = validate_delete_request(payload, state.get('hidden_ids', []), MAX_DELETE_BATCH)
            results = permanently_delete_messages(ids)
        except ApiError as exc:
            return self.err(exc.status, str(exc), exc.detail)
        except Exception as exc:
            return self.err(502, 'Error durante el borrado permanente', gmail_error_detail(exc))
        audit_error = None
        try:
            updated_state = record_delete_results(results)
        except Exception as exc:
            updated_state = None
            audit_error = (
                'Gmail procesó el borrado, pero no se pudo actualizar el registro local. '
                'No repitas la operación sin revisar los resultados.'
            )
            print(f'[Borrado permanente] Error registrando resultados: {exc}')
        return self.j({
            'status': 'ok',
            'results': results,
            'deleted': sum(item.get('status') == 'deleted' for item in results),
            'state': updated_state,
            'audit_error': audit_error,
        })

    def handle_messages_export(self):
        try:
            payload = self.read_json_body()
            if not isinstance(payload, dict) or 'message_ids' not in payload:
                raise ApiError('IDs de mensaje requeridos', detail='Envía un objeto JSON con "message_ids"')
            
            message_ids = [validate_gmail_id(mid, 'message_id') for mid in payload['message_ids']]
            if not message_ids:
                raise ApiError('Lista de IDs vacía')
            if len(message_ids) > 100:
                raise ApiError('Demasiados mensajes', detail='El límite de exportación es de 100 correos por lote')
        except ApiError as e:
            return self.err(e.status, str(e), e.detail)

        if not self.require_gmail():
            return

        try:
            if len(message_ids) == 1:
                mid = message_ids[0]
                data = get_message_raw(mid)
                if not data:
                    return self.err(404, 'Mensaje no encontrado', f'No se pudo recuperar el contenido de {mid}')
                
                filename = f"{mid}.eml"
                filepath = EXPORTS_DIR / filename
                filepath.write_bytes(data)
                
                return self.j({
                    'status': 'ok',
                    'file': filename,
                    'path': str(filepath.absolute()),
                    'type': 'eml'
                })

            # Múltiples mensajes -> ZIP
            zip_filename = f"export_{int(time.time())}.zip"
            zip_path = EXPORTS_DIR / zip_filename
            
            with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zf:
                for mid in message_ids:
                    try:
                        data = get_message_raw(mid)
                        if data:
                            zf.writestr(f'{mid}.eml', data)
                    except Exception as e:
                        print(f'[Export] Error obteniendo {mid}: {e}')
                        continue
            
            if not zip_path.exists() or zip_path.stat().st_size == 0:
                 return self.err(500, 'Error de exportación', 'No se pudo generar el archivo ZIP local')

            return self.j({
                'status': 'ok',
                'file': zip_filename,
                'path': str(zip_path.absolute()),
                'type': 'zip'
            })

        except Exception as e:
            detail = gmail_error_detail(e)
            print(f'[Export] Error: {detail}')
            return self.err(502, 'Error exportando correos', detail)

    def handle_messages_archive(self):
        try:
            payload = self.read_json_body()
            if not isinstance(payload, dict) or 'message_ids' not in payload:
                raise ApiError('IDs de mensaje requeridos')
            message_ids = [validate_gmail_id(mid) for mid in payload['message_ids']]
            if not message_ids:
                raise ApiError('Lista de IDs vacía')
        except ApiError as e:
            return self.err(e.status, str(e), e.detail)

        if not self.require_gmail():
            return

        try:
            # 1. Archivar en Gmail
            archive_messages(message_ids)
            
            # 2. Ocultar localmente
            state = load_state()
            hidden_ids = state.get('hidden_ids', [])
            hidden_set = set(hidden_ids)
            added = 0
            for mid in message_ids:
                if mid not in hidden_set:
                    hidden_ids.append(mid)
                    added += 1
            
            if added > 0:
                state['hidden_ids'] = hidden_ids
                save_user_state(state)
            
            return self.j({
                'status': 'ok',
                'archived': len(message_ids),
                'hidden_added': added,
                'state': state
            })
        except Exception as e:
            detail = gmail_error_detail(e)
            print(f'[Archive] Error: {detail}')
            return self.err(502, 'Error archivando correos', detail)

    def handle_get_labels(self):
        if not self.require_gmail():
            return
        try:
            labels = get_labels()
            return self.j({'status': 'ok', 'labels': labels})
        except Exception as e:
            detail = gmail_error_detail(e)
            print(f'[Labels] Error: {detail}')
            return self.err(502, 'Error obteniendo etiquetas', detail)

    def handle_post_labels(self):
        try:
            payload = self.read_json_body()
            name = (payload.get('name') or '').strip()
            if not name:
                raise ApiError('Nombre de etiqueta requerido')
        except ApiError as e:
            return self.err(e.status, str(e), e.detail)

        if not self.require_gmail():
            return

        try:
            label = create_label(name)
            return self.j({'status': 'ok', 'label': label})
        except Exception as e:
            detail = gmail_error_detail(e)
            print(f'[Create Label] Error: {detail}')
            return self.err(502, 'Error creando etiqueta', detail)

    def handle_messages_label(self):
        try:
            payload = self.read_json_body()
            if not isinstance(payload, dict):
                raise ApiError('Cuerpo JSON inválido')
            
            message_ids = [validate_gmail_id(mid) for mid in payload.get('message_ids', [])]
            label_id = validate_gmail_id(payload.get('label_id', ''), 'label_id')
            archive = bool(payload.get('archive', False))
            
            if not message_ids:
                raise ApiError('Lista de IDs vacía')
        except ApiError as e:
            return self.err(e.status, str(e), e.detail)

        if not self.require_gmail():
            return

        try:
            # 1. Aplicar etiqueta (y opcionalmente archivar)
            apply_label(message_ids, label_id, archive=archive)
            
            # 2. Si se archivó, ocultar localmente
            added = 0
            state = None
            if archive:
                state = load_state()
                hidden_ids = state.get('hidden_ids', [])
                hidden_set = set(hidden_ids)
                for mid in message_ids:
                    if mid not in hidden_set:
                        hidden_ids.append(mid)
                        added += 1
                if added > 0:
                    state['hidden_ids'] = hidden_ids
                    save_user_state(state)
            
            return self.j({
                'status': 'ok',
                'labeled': len(message_ids),
                'archived': archive,
                'hidden_added': added,
                'state': state
            })
        except Exception as e:
            detail = gmail_error_detail(e)
            print(f'[Label] Error: {detail}')
            return self.err(502, 'Error etiquetando correos', detail)

    def handle_ai_suggest_rules(self):
        try:
            payload = self.read_json_body()
            if not isinstance(payload, list):
                raise ApiError('Se requiere una lista de metadatos de correos')
        except ApiError as e:
            return self.err(e.status, str(e), e.detail)

        try:
            result = suggest_rules(payload)
            return self.j({'status': 'ok', **result})
        except Exception as e:
            print(f'[AI Suggest API] Error: {e}')
            return self.err(502, 'Error generando sugerencias', str(e))

    def handle_get_exports(self):
        try:
            files = []
            for f in sorted(EXPORTS_DIR.glob('*'), key=lambda x: x.stat().st_mtime, reverse=True):
                if f.name.startswith('.'): continue
                files.append({
                    'name': f.name,
                    'size': f.stat().st_size,
                    'mtime': f.stat().st_mtime,
                    'type': f.suffix.lstrip('.').lower() or 'unknown'
                })
            return self.j({'status': 'ok', 'files': files})
        except Exception as e:
            return self.err(500, 'Error listando exportaciones', str(e))

    def handle_read_eml(self, query):
        qs = parse_qs(query)
        filename = qs.get('file', [''])[0]
        external_path = qs.get('path', [''])[0]
        
        if not filename and not external_path:
            return self.err(400, 'Nombre de archivo o ruta requerida')
        
        try:
            if external_path:
                filepath = Path(external_path)
            else:
                filepath = EXPORTS_DIR / validate_filename(filename)
                
            if not filepath.exists():
                return self.err(404, 'Archivo no encontrado')
            
            raw_bytes = filepath.read_bytes()
            return self.j({'status': 'ok', 'data': self._parse_eml_bytes(raw_bytes)})
        except Exception as e:
            print(f'[Read EML] Error: {e}')
            return self.err(500, 'Error leyendo EML', str(e))

    def handle_post_read_eml(self):
        try:
            size = int(self.headers.get('Content-Length', '0'))
            if size < 1: raise ApiError('Archivo vacío')
            raw_bytes = self.rfile.read(size)
            return self.j({'status': 'ok', 'data': self._parse_eml_bytes(raw_bytes)})
        except Exception as e:
            return self.err(500, 'Error parseando archivo local', str(e))

    def _parse_eml_bytes(self, raw_bytes):
        msg = email.message_from_bytes(raw_bytes, policy=policy.default)
        data = {
            'subject': msg['subject'] or '(sin asunto)',
            'from': msg['from'] or '(desconocido)',
            'to': msg['to'] or '',
            'date': msg['date'] or '',
            'body_text': '',
            'body_html': '',
            'attachments': []
        }
        for part in msg.walk():
            content_type = part.get_content_type()
            disposition = part.get_content_disposition()
            if disposition == 'attachment':
                payload = part.get_payload(decode=True) or b''
                data['attachments'].append({
                    'filename': part.get_filename() or 'adjunto',
                    'mime_type': content_type or 'application/octet-stream',
                    'size': len(payload),
                    'data': base64.b64encode(payload).decode('ascii')
                })
                continue
            if content_type == 'text/plain':
                data['body_text'] += (part.get_payload(decode=True) or b'').decode(part.get_content_charset() or 'utf-8', errors='replace')
            elif content_type == 'text/html':
                html = (part.get_payload(decode=True) or b'').decode(part.get_content_charset() or 'utf-8', errors='replace')
                data['body_html'] += self._sanitize_html(html)
        return data

    def _sanitize_html(self, html):
        import re
        # Saneamiento muy agresivo para evitar scripts en el lector integrado
        html = re.sub(r'<script.*?>.*?</script>', '', html, flags=re.DOTALL | re.IGNORECASE)
        html = re.sub(r'on\w+=".*?"', '', html, flags=re.IGNORECASE)
        html = re.sub(r'<iframe.*?>.*?</iframe>', '', html, flags=re.DOTALL | re.IGNORECASE)
        html = re.sub(r'<object.*?>.*?</object>', '', html, flags=re.DOTALL | re.IGNORECASE)
        return html

    def j(self, data, status=200):
        b = json.dumps(data, ensure_ascii=False).encode()
        self.send_response(status)
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.send_header('Content-Length', len(b))
        self.send_header('X-Content-Type-Options', 'nosniff')
        self.end_headers()
        self.write_body(b)

    def err(self, status, error, detail=None):
        return self.j({'status': 'error', 'error': error, 'detail': detail or error}, status)


import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer


def main():
    import argparse
    parser = argparse.ArgumentParser(description='Gestor de Correos — Servidor Local')
    parser.add_argument('--open', help='Ruta a un archivo .eml para abrir en el visor')
    args = parser.parse_args()

    print('=' * 52)
    print('  Gestor de Correos — Servidor Local v7')
    print('=' * 52)
    
    # Si se pasa --open, preparar la URL de visualización
    view_url = f'http://{HOST}:{PORT}'
    if args.open:
        abs_path = os.path.abspath(args.open)
        view_url += f'/?view={abs_path}'
        print(f'📖 Abriendo archivo: {abs_path}')
    if not GMAIL_OK:
        print('\n⚠  Instala dependencias:')
        print('   .venv/bin/python -m pip install -r requirements.txt\n')
    if not CREDS.exists():
        print('\n⚠  Falta credentials.json')
        print('   → https://console.cloud.google.com')
        print('   → Nuevo proyecto → Gmail API → OAuth Desktop → Descargar\n')

    if GMAIL_OK and CREDS.exists():
        print('\n🔐 Gmail configurado')
        print('   La autenticación OAuth se abrirá solo al hacer una búsqueda.\n')

    print(f'🚀 http://{HOST}:{PORT}  (Ctrl+C para detener)\n')
    if not HEADLESS:
        threading.Thread(target=lambda: (
            __import__('time').sleep(1.5),
            webbrowser.open(view_url)
        ), daemon=True).start()

    try:
        ThreadingHTTPServer((HOST, PORT), H).serve_forever()
    except OSError as e:
        if e.errno == 48: # Address already in use
            if args.open:
                print('ℹ️ El servidor ya está corriendo. Abriendo archivo en la instancia activa…')
                webbrowser.open(view_url)
            else:
                print(f'❌ Error: El puerto {PORT} ya está ocupado.')
        else:
            raise e
    except KeyboardInterrupt:
        print('\n👋 Servidor detenido.')


if __name__ == '__main__':
    main()

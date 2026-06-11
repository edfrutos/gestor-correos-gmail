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

import json
import threading
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from ai_client import ai_status, summarize
from destructive_gmail import MAX_DELETE_BATCH, delete_status, destructive_gmail, permanently_delete_messages, revoke_destructive_authorization
from gmail_client import CREDS, GMAIL_OK, get_attachment, get_message, gmail, gmail_error_detail, gmail_message_lookup_state, gmail_status, search
from storage import load_state, record_delete_results, save_user_state
from validators import ApiError, parse_max, validate_attachment_id, validate_delete_request, validate_filename, validate_gmail_id, validate_mime_type, validate_sender


PORT = 8765
BASE_DIR = Path(__file__).parent
HIDDEN_PAGE_SIZE = 20
STATIC_FILES = {
    '/static/app.css': ('text/css; charset=utf-8', BASE_DIR / 'static' / 'app.css'),
    '/static/app.js': ('text/javascript; charset=utf-8', BASE_DIR / 'static' / 'app.js'),
    '/static/summary.js': ('text/javascript; charset=utf-8', BASE_DIR / 'static' / 'summary.js'),
    '/static/logo.svg': ('image/svg+xml', BASE_DIR / 'static' / 'logo.svg'),
    '/static/favicon.svg': ('image/svg+xml', BASE_DIR / 'static' / 'favicon.svg'),
}
LOCAL_HOSTS = {'localhost', '127.0.0.1', '::1'}
LOCAL_ORIGINS = {
    f'http://localhost:{PORT}',
    f'http://127.0.0.1:{PORT}',
    f'http://[::1]:{PORT}',
}


def _header_hostname(value):
    try:
        return urlparse(f'//{value}').hostname
    except ValueError:
        return None


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

        if p.path == '/api/state':
            return self.handle_get_state()

        if p.path == '/api/attachment':
            return self.handle_attachment(p.query)

        if p.path == '/api/message':
            return self.handle_message(p.query)

        if p.path == '/api/hidden':
            return self.handle_hidden()

        self.send_error(404)

    def do_POST(self):
        if not self.request_is_local():
            return self.err(403, 'Origen no autorizado', 'La API sólo acepta peticiones desde la interfaz local')
        p = urlparse(self.path)

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
            sender = validate_sender(qs.get('sender', [''])[0])
            max_r = parse_max(qs.get('max', ['30'])[0])
        except ApiError as e:
            return self.err(e.status, str(e), e.detail)

        if not self.require_gmail():
            return

        print(f'[API] Buscando: from:{sender}')
        try:
            custom_rules = load_state().get('custom_rules', [])
            emails = search(sender, max_r, custom_rules)
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
            page = _parse_page(parse_qs(urlparse(hidden_path).query).get('page', ['1'])[0])
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


def main():
    print('=' * 52)
    print('  Gestor de Correos — Servidor Local v5')
    print('=' * 52)
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

    print(f'🚀 http://localhost:{PORT}  (Ctrl+C para detener)\n')
    threading.Thread(target=lambda: (
        __import__('time').sleep(1.5),
        webbrowser.open(f'http://localhost:{PORT}')
    ), daemon=True).start()

    try:
        ThreadingHTTPServer(('localhost', PORT), H).serve_forever()
    except KeyboardInterrupt:
        print('\n👋 Servidor detenido.')


if __name__ == '__main__':
    main()

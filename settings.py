"""Ajustes editables desde la UI (panel Configuración).

Viven en `settings.json` dentro de `data_dir()` (Application Support en el
.app, carpeta del proyecto desde fuente), con permisos 600 porque incluyen la
clave del proveedor AI. La clave nunca se devuelve al frontend: solo se
informa de si está guardada.

Para la IA, un valor guardado aquí tiene prioridad sobre la variable de
entorno / `.env` equivalente (`AI_BASE_URL`, `AI_MODEL`, `AI_API_KEY`).
"""

import json
import os
import threading
from pathlib import Path
from urllib.parse import urlparse

from paths import data_path
from validators import ApiError


SETTINGS_FILE = data_path('settings.json')
_lock = threading.Lock()

DEFAULT_SETTINGS = {
    'ai_base_url': '',
    'ai_model': '',
    'ai_api_key': '',
    'backup_dir': '',
}
AI_ENV = {'ai_base_url': 'AI_BASE_URL', 'ai_model': 'AI_MODEL', 'ai_api_key': 'AI_API_KEY'}


def _text(value, max_len, name):
    value = '' if value is None else value
    if not isinstance(value, str):
        raise ApiError('Ajuste inválido', detail=f'{name} debe ser texto')
    value = value.strip()
    if len(value) > max_len:
        raise ApiError('Ajuste inválido', detail=f'{name} supera {max_len} caracteres')
    return value


def _validate_base_url(value):
    value = _text(value, 500, 'URL base AI')
    if not value:
        return ''
    parsed = urlparse(value)
    if parsed.scheme not in {'http', 'https'} or not parsed.netloc:
        raise ApiError('URL base AI inválida', detail='Debe ser una URL http(s), p. ej. https://api.openai.com/v1')
    if value.rstrip('/').endswith('/chat/completions'):
        raise ApiError('URL base AI inválida', detail='Indica la URL base, sin /chat/completions al final')
    return value


def validate_backup_dir(value):
    value = _text(value, 1000, 'Carpeta de respaldo')
    if not value:
        return ''
    target = Path(value).expanduser()
    if not target.is_absolute():
        raise ApiError('Carpeta de respaldo inválida', detail='Indica una ruta absoluta')
    if not target.is_dir():
        raise ApiError('Carpeta de respaldo inválida', detail=f'No existe la carpeta {target}')
    if not os.access(target, os.W_OK):
        raise ApiError('Carpeta de respaldo inválida', detail=f'Sin permiso de escritura en {target}')
    return str(target.resolve())


def _load_unlocked():
    settings = dict(DEFAULT_SETTINGS)
    if not SETTINGS_FILE.exists():
        return settings
    try:
        raw = json.loads(SETTINGS_FILE.read_text(encoding='utf-8'))
    except json.JSONDecodeError:
        raise ApiError('Ajustes corruptos', status=500, detail='settings.json no contiene JSON válido')
    if isinstance(raw, dict):
        for key in DEFAULT_SETTINGS:
            if isinstance(raw.get(key), str):
                settings[key] = raw[key]
    return settings


def load_settings():
    with _lock:
        return _load_unlocked()


def save_settings(payload):
    """Aplica un cambio parcial. `ai_api_key` vacía o ausente conserva la
    guardada; `ai_api_key_clear: true` la borra."""
    if not isinstance(payload, dict):
        raise ApiError('Ajustes inválidos', detail='Envía un objeto JSON')
    with _lock:
        settings = _load_unlocked()
        if 'ai_base_url' in payload:
            settings['ai_base_url'] = _validate_base_url(payload['ai_base_url'])
        if 'ai_model' in payload:
            settings['ai_model'] = _text(payload['ai_model'], 200, 'Modelo AI')
        if payload.get('ai_api_key_clear'):
            settings['ai_api_key'] = ''
        else:
            key = _text(payload.get('ai_api_key'), 500, 'Clave AI')
            if key:
                settings['ai_api_key'] = key
        if 'backup_dir' in payload:
            settings['backup_dir'] = validate_backup_dir(payload['backup_dir'])
        tmp = SETTINGS_FILE.with_name(SETTINGS_FILE.name + '.tmp')
        tmp.write_text(json.dumps(settings, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
        tmp.chmod(0o600)
        tmp.replace(SETTINGS_FILE)
        return settings


def ai_config():
    """(base_url, model, api_key): ajuste de la UI o, si está vacío, entorno."""
    settings = load_settings()
    return tuple(
        settings[key] or os.environ.get(env, '').strip()
        for key, env in AI_ENV.items()
    )


def ai_source():
    """De dónde sale la configuración AI efectiva: 'app', 'env' o None."""
    settings = load_settings()
    if settings['ai_base_url'] and settings['ai_model']:
        return 'app'
    base_url, model, _ = ai_config()
    return 'env' if base_url and model else None


def public_settings():
    settings = load_settings()
    return {
        'ai_base_url': settings['ai_base_url'],
        'ai_model': settings['ai_model'],
        'ai_api_key_set': bool(settings['ai_api_key']),
        'ai_env_api_key_set': bool(os.environ.get('AI_API_KEY', '').strip()),
        'ai_source': ai_source(),
        'backup_dir': settings['backup_dir'],
    }

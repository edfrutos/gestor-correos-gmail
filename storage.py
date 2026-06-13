import json
import re
import threading
from datetime import datetime, timezone
from pathlib import Path

from validators import ApiError, validate_sender


BASE_DIR = Path(__file__).parent
STATE_FILE = BASE_DIR / 'app_state.json'
STATE_VERSION = 2
_state_lock = threading.Lock()

SOURCE_FILTERS = {'all', 'v', 'p', 's', 'cu'}
CATEGORY_FILTERS = {'all', 'money', 'warn', 'sub', 'ssl', 'sec', 'maint', 'domain', 'comm'}
RULE_SEVERITIES = {'high', 'medium', 'low'}

DEFAULT_STATE = {
    'version': STATE_VERSION,
    'custom_sources': [],
    'custom_rules': [],
    'hidden_ids': [],
    'deletion_audit': [],
    'preferences': {
        'source_filter': 'all',
        'category_filter': 'all',
        'search_query': '',
    },
}


def _clone_default():
    return json.loads(json.dumps(DEFAULT_STATE))


def _bounded_text(value, max_len, fallback=''):
    value = str(value or '').strip()
    if len(value) > max_len:
        return value[:max_len]
    return value or fallback


def _validate_domain(value):
    sender = validate_sender(value)
    if '@' in sender:
        sender = sender.split('@', 1)[1]
    return sender


def _normalize_color(value, index):
    value = str(value or '').strip()
    if re.fullmatch(r'#[0-9a-fA-F]{6}', value):
        return value.lower()
    if re.fullmatch(r'var\(--[a-z0-9-]+\)', value):
        return value
    palette = ['#fb923c', '#22d3ee', '#a3e635', '#e879f9', '#facc15', '#c084fc']
    return palette[index % len(palette)]


def _normalize_sources(raw_sources):
    if raw_sources is None:
        return []
    if not isinstance(raw_sources, list):
        raise ApiError('Estado inválido', detail='custom_sources debe ser una lista')

    out = []
    seen = set()
    for idx, item in enumerate(raw_sources[:50]):
        if not isinstance(item, dict):
            raise ApiError('Fuente inválida', detail='Cada fuente debe ser un objeto')
        dom = _validate_domain(item.get('dom', ''))
        if dom in seen:
            continue
        seen.add(dom)
        label = _bounded_text(item.get('label'), 60, dom)
        color = _normalize_color(item.get('color'), idx)
        out.append({'dom': dom, 'label': label, 'color': color, 'fixed': False})
    return out


def _normalize_hidden_ids(raw_ids):
    if raw_ids is None:
        return []
    if not isinstance(raw_ids, list):
        raise ApiError('Estado inválido', detail='hidden_ids debe ser una lista')

    out = []
    seen = set()
    for raw in raw_ids[:500]:
        value = str(raw or '').strip()
        if not re.fullmatch(r'[A-Za-z0-9_-]{1,128}', value):
            raise ApiError('ID oculto inválido', detail='hidden_ids contiene un ID no válido')
        if value not in seen:
            seen.add(value)
            out.append(value)
    return out


def _normalize_deletion_audit(raw_entries):
    if raw_entries is None:
        return []
    if not isinstance(raw_entries, list):
        raise ApiError('Estado inválido', detail='deletion_audit debe ser una lista')
    out = []
    for item in raw_entries[-200:]:
        if not isinstance(item, dict):
            continue
        try:
            message_id = _normalize_hidden_ids([item.get('id')])[0]
        except (ApiError, IndexError):
            continue
        status = str(item.get('status') or '')[:20]
        if status not in {'deleted', 'error'}:
            continue
        out.append({
            'id': message_id,
            'status': status,
            'at': _bounded_text(item.get('at'), 40),
        })
    return out


def _normalize_custom_rules(raw_rules):
    if raw_rules is None:
        return []
    if not isinstance(raw_rules, list):
        raise ApiError('Estado inválido', detail='custom_rules debe ser una lista')

    out = []
    seen = set()
    for item in raw_rules[:50]:
        if not isinstance(item, dict):
            raise ApiError('Regla inválida', detail='Cada regla debe ser un objeto')
        rule_id = _bounded_text(item.get('id'), 64)
        if not re.fullmatch(r'[A-Za-z0-9_-]{1,64}', rule_id) or rule_id in seen:
            raise ApiError('Regla inválida', detail='Cada regla necesita un ID único válido')
        seen.add(rule_id)

        category = str(item.get('category') or '').strip()
        if category not in CATEGORY_FILTERS - {'all'}:
            raise ApiError('Regla inválida', detail='La categoría de la regla no es válida')
        severity = str(item.get('severity') or '').strip()
        if severity not in RULE_SEVERITIES:
            raise ApiError('Regla inválida', detail='La severidad de la regla no es válida')

        raw_keywords = item.get('keywords')
        if not isinstance(raw_keywords, list):
            raise ApiError('Regla inválida', detail='keywords debe ser una lista')
        keywords = []
        for value in raw_keywords[:20]:
            keyword = _bounded_text(value, 80).lower()
            if keyword and keyword not in keywords:
                keywords.append(keyword)

        provider = _bounded_text(item.get('provider'), 253).lower()
        if provider:
            provider = _validate_domain(provider)
        if not provider and not keywords:
            raise ApiError('Regla inválida', detail='Indica proveedor, palabras clave o ambos')

        out.append({
            'id': rule_id,
            'label': _bounded_text(item.get('label'), 80, 'Regla personalizada'),
            'provider': provider,
            'keywords': keywords,
            'keyword_operator': 'all' if item.get('keyword_operator') == 'all' else 'any',
            'category': category,
            'severity': severity,
            'gmail_label_id': _bounded_text(item.get('gmail_label_id'), 128),
            'auto_label': bool(item.get('auto_label', False)),
            'auto_archive': bool(item.get('auto_archive', False)),
        })
    return out


def _normalize_preferences(raw_preferences):
    if raw_preferences is None:
        raw_preferences = {}
    if not isinstance(raw_preferences, dict):
        raise ApiError('Estado inválido', detail='preferences debe ser un objeto')

    source_filter = raw_preferences.get('source_filter', 'all')
    if source_filter not in SOURCE_FILTERS:
        source_filter = 'all'

    category_filter = raw_preferences.get('category_filter', 'all')
    if category_filter not in CATEGORY_FILTERS:
        category_filter = 'all'

    return {
        'source_filter': source_filter,
        'category_filter': category_filter,
        'search_query': _bounded_text(raw_preferences.get('search_query'), 200),
        'ai_suggestions_enabled': bool(raw_preferences.get('ai_suggestions_enabled', False)),
    }


def normalize_state(raw_state):
    if raw_state is None:
        return _clone_default()
    if not isinstance(raw_state, dict):
        raise ApiError('Estado inválido', detail='El estado debe ser un objeto JSON')

    return {
        'version': STATE_VERSION,
        'custom_sources': _normalize_sources(raw_state.get('custom_sources')),
        'custom_rules': _normalize_custom_rules(raw_state.get('custom_rules')),
        'hidden_ids': _normalize_hidden_ids(raw_state.get('hidden_ids')),
        'deletion_audit': _normalize_deletion_audit(raw_state.get('deletion_audit')),
        'preferences': _normalize_preferences(raw_state.get('preferences')),
    }


def _load_state_unlocked():
    if not STATE_FILE.exists():
        return _clone_default()
    try:
        raw = json.loads(STATE_FILE.read_text(encoding='utf-8'))
    except json.JSONDecodeError:
        raise ApiError('Estado local corrupto', status=500, detail='app_state.json no contiene JSON válido')
    return normalize_state(raw)


def _save_state_unlocked(raw_state):
    state = normalize_state(raw_state)
    payload = json.dumps(state, ensure_ascii=False, indent=2, sort_keys=True)
    tmp = STATE_FILE.with_name(STATE_FILE.name + '.tmp')
    tmp.write_text(payload + '\n', encoding='utf-8')
    tmp.chmod(0o600)
    tmp.replace(STATE_FILE)
    return state


def load_state():
    with _state_lock:
        return _load_state_unlocked()


def save_state(raw_state):
    with _state_lock:
        return _save_state_unlocked(raw_state)


def save_user_state(raw_state):
    with _state_lock:
        existing = _load_state_unlocked()
        candidate = dict(raw_state) if isinstance(raw_state, dict) else raw_state
        if isinstance(candidate, dict):
            candidate['deletion_audit'] = existing.get('deletion_audit', [])
        return _save_state_unlocked(candidate)


def record_delete_results(results):
    with _state_lock:
        state = _load_state_unlocked()
        deleted_ids = {item['id'] for item in results if item.get('status') == 'deleted'}
        state['hidden_ids'] = [message_id for message_id in state['hidden_ids'] if message_id not in deleted_ids]
        now = datetime.now(timezone.utc).isoformat()
        state['deletion_audit'].extend({
            'id': item.get('id'),
            'status': item.get('status'),
            'at': now,
        } for item in results)
        return _save_state_unlocked(state)

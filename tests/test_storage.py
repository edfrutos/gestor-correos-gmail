import json
from concurrent.futures import ThreadPoolExecutor

import pytest

import storage
from validators import ApiError


def test_load_state_returns_default_when_file_missing(monkeypatch, tmp_path):
    monkeypatch.setattr(storage, 'STATE_FILE', tmp_path / 'missing.json')

    state = storage.load_state()

    assert state == storage.DEFAULT_STATE


def test_normalize_state_accepts_custom_sources():
    state = storage.normalize_state({
        'custom_sources': [{'dom': 'web.dev', 'label': 'web.dev', 'color': '#34D399'}],
    })

    assert state['version'] == 2
    assert state['custom_sources'] == [
        {'dom': 'web.dev', 'label': 'web.dev', 'color': '#34d399', 'fixed': False},
    ]


def test_normalize_state_rejects_invalid_source_domain():
    with pytest.raises(ApiError) as exc:
        storage.normalize_state({'custom_sources': [{'dom': 'bad'}]})

    assert exc.value.status == 400


def test_normalize_state_does_not_keep_gmail_cache_fields():
    state = storage.normalize_state({
        'custom_sources': [{'dom': 'web.dev', 'subject': 'secret', 'body': 'secret'}],
        'hidden_ids': ['abc123'],
        'emails': [{'subject': 'secret', 'body': 'secret'}],
        'body': 'secret',
        'snippet': 'secret',
    })

    assert set(state.keys()) == {'version', 'custom_sources', 'custom_rules', 'hidden_ids', 'deletion_audit', 'preferences'}
    assert set(state['custom_sources'][0].keys()) == {'dom', 'label', 'color', 'fixed'}
    assert 'emails' not in state
    assert 'body' not in json.dumps(state)
    assert 'snippet' not in json.dumps(state)
    assert 'subject' not in json.dumps(state)


def test_normalize_state_persists_hidden_ids_and_preferences():
    state = storage.normalize_state({
        'hidden_ids': ['abc123', 'abc123', 'XYZ_9'],
        'preferences': {
            'source_filter': 'cu',
            'category_filter': 'warn',
            'search_query': 'plesk',
        },
    })

    assert state['hidden_ids'] == ['abc123', 'XYZ_9']
    assert state['preferences'] == {
        'source_filter': 'cu',
        'category_filter': 'warn',
        'search_query': 'plesk',
        'ai_suggestions_enabled': False,
    }


def test_normalize_state_accepts_custom_rules():
    state = storage.normalize_state({
        'custom_rules': [{
            'id': 'rule_ssl',
            'label': 'SSL crítico',
            'provider': 'PLESK.COM',
            'keywords': ['Final Notice', 'final notice', 'Expires Tomorrow'],
            'category': 'ssl',
            'severity': 'high',
        }],
    })

    assert state['custom_rules'] == [{
        'id': 'rule_ssl',
        'label': 'SSL crítico',
        'provider': 'plesk.com',
        'keywords': ['final notice', 'expires tomorrow'],
        'keyword_operator': 'any',
        'category': 'ssl',
        'severity': 'high',
        'gmail_label_id': '',
        'auto_label': False,
        'auto_archive': False,
    }]


def test_normalize_state_accepts_all_keyword_operator():
    state = storage.normalize_state({
        'custom_rules': [{
            'id': 'rule_all',
            'label': 'Todo debe coincidir',
            'provider': '',
            'keywords': ['certificate', 'failed'],
            'keyword_operator': 'all',
            'category': 'ssl',
            'severity': 'high',
        }],
    })

    assert state['custom_rules'][0]['keyword_operator'] == 'all'


def test_normalize_state_rejects_custom_rule_without_conditions():
    with pytest.raises(ApiError) as exc:
        storage.normalize_state({
            'custom_rules': [{
                'id': 'rule_empty',
                'label': 'Vacía',
                'provider': '',
                'keywords': [],
                'category': 'warn',
                'severity': 'high',
            }],
        })

    assert exc.value.detail == 'Indica proveedor, palabras clave o ambos'


def test_save_and_load_roundtrip(monkeypatch, tmp_path):
    state_file = tmp_path / 'app_state.json'
    monkeypatch.setattr(storage, 'STATE_FILE', state_file)

    saved = storage.save_state({
        'custom_sources': [{'dom': 'paypal.com', 'label': 'PayPal', 'color': '#38bdf8'}],
        'custom_rules': [{'id': 'rule_paypal', 'label': 'PayPal', 'provider': 'paypal.com', 'keywords': [], 'category': 'money', 'severity': 'medium'}],
        'hidden_ids': ['m1'],
        'preferences': {'source_filter': 'cu', 'category_filter': 'money', 'search_query': 'factura'},
    })
    loaded = storage.load_state()

    assert state_file.exists()
    assert state_file.stat().st_mode & 0o777 == 0o600
    assert loaded == saved
    assert loaded['custom_sources'][0]['dom'] == 'paypal.com'
    assert loaded['custom_rules'][0]['id'] == 'rule_paypal'


def test_record_delete_results_removes_successes_and_keeps_minimal_audit(monkeypatch, tmp_path):
    state_file = tmp_path / 'app_state.json'
    monkeypatch.setattr(storage, 'STATE_FILE', state_file)
    storage.save_state({'hidden_ids': ['m1', 'm2']})

    state = storage.record_delete_results([
        {'id': 'm1', 'status': 'deleted'},
        {'id': 'm2', 'status': 'error', 'detail': 'private provider detail'},
    ])

    assert state['hidden_ids'] == ['m2']
    assert [entry['status'] for entry in state['deletion_audit']] == ['deleted', 'error']
    assert set(state['deletion_audit'][0]) == {'id', 'status', 'at'}
    assert 'private provider detail' not in json.dumps(state)


def test_save_user_state_preserves_backend_deletion_audit(monkeypatch, tmp_path):
    state_file = tmp_path / 'app_state.json'
    monkeypatch.setattr(storage, 'STATE_FILE', state_file)
    storage.save_state({
        'hidden_ids': ['m1'],
        'deletion_audit': [{'id': 'old', 'status': 'deleted', 'at': '2026-06-10T00:00:00+00:00'}],
    })

    state = storage.save_user_state({
        'hidden_ids': [],
        'deletion_audit': [],
        'preferences': {'search_query': 'updated'},
    })

    assert state['hidden_ids'] == []
    assert state['preferences']['search_query'] == 'updated'
    assert state['deletion_audit'] == [
        {'id': 'old', 'status': 'deleted', 'at': '2026-06-10T00:00:00+00:00'},
    ]


def test_concurrent_saves_do_not_collide_on_temp_file(monkeypatch, tmp_path):
    state_file = tmp_path / 'app_state.json'
    monkeypatch.setattr(storage, 'STATE_FILE', state_file)

    with ThreadPoolExecutor(max_workers=8) as executor:
        results = list(executor.map(
            lambda index: storage.save_state({'hidden_ids': [f'm{index}']}),
            range(50),
        ))

    assert len(results) == 50
    assert storage.load_state()['hidden_ids'][0].startswith('m')

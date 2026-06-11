from classifier import classify_email, classify_metadata, classify_severity, matching_custom_rules


def test_classify_email_detects_money_and_subscription():
    email = {
        'subject': 'Your subscription renewal invoice',
        'body': 'Renewal amount: €14.99',
        'from': 'billing@example.com',
        'tag': 'Proveedor',
    }

    assert classify_email(email) == ['money', 'sub']


def test_classify_email_detects_security_and_maintenance():
    email = {
        'subject': 'Urgent security patch deployment',
        'body': 'Scheduled restart for maintenance',
        'from': 'support@example.com',
    }

    cats = classify_email(email)
    assert 'warn' in cats
    assert 'sec' in cats
    assert 'maint' in cats


def test_classify_email_returns_empty_list_without_matches():
    assert classify_email({'subject': 'Hello', 'body': 'General message'}) == []


def test_classify_severity_prefers_high_risk_categories():
    severity, reason = classify_severity(['money', 'warn', 'comm'])

    assert severity == 'high'
    assert reason == 'Aviso urgente o fallo detectado'


def test_classify_metadata_returns_categories_and_reason():
    meta = classify_metadata({
        'subject': 'Your Plesk subscription expires tomorrow.',
        'body': 'FINAL NOTICE: Backup to Cloud Pro expires tomorrow.',
        'from': 'info@plesk.com',
        'tag': 'Plesk · Renovación',
    })

    assert meta['categories'] == ['warn', 'sub', 'domain']
    assert meta['severity'] == 'high'
    assert meta['severity_reason'] == 'Aviso urgente o fallo detectado'


def test_matching_custom_rule_requires_provider_and_keyword_when_both_exist():
    rules = [{
        'id': 'rule_ssl',
        'label': 'SSL Plesk',
        'provider': 'plesk.com',
        'keywords': ['certificate'],
        'category': 'ssl',
        'severity': 'high',
    }]

    assert matching_custom_rules({'from': 'info@plesk.com', 'subject': 'Certificate failed'}, rules) == rules
    assert matching_custom_rules({'from': 'info@plesk.com', 'subject': 'General update'}, rules) == []
    assert matching_custom_rules({'from': 'info@example.com', 'subject': 'Certificate failed'}, rules) == []


def test_matching_custom_rule_can_require_all_keywords():
    rules = [{
        'id': 'rule_all',
        'provider': '',
        'keywords': ['certificate', 'failed'],
        'keyword_operator': 'all',
        'category': 'ssl',
        'severity': 'high',
    }]

    assert matching_custom_rules({'subject': 'Certificate renewal failed'}, rules) == rules
    assert matching_custom_rules({'subject': 'Certificate renewed'}, rules) == []


def test_matching_custom_rule_rejects_provider_substrings_and_display_names():
    rules = [{
        'id': 'rule_provider',
        'provider': 'example.com',
        'keywords': [],
        'category': 'warn',
        'severity': 'high',
    }]

    assert matching_custom_rules({'from': 'info@alerts.example.com'}, rules) == rules
    assert matching_custom_rules({'from': 'info@evil-example.com'}, rules) == []
    assert matching_custom_rules({'from': 'example.com Support <info@evil.test>'}, rules) == []


def test_classify_metadata_applies_custom_category_and_severity():
    meta = classify_metadata(
        {'from': 'billing@example.com', 'subject': 'Monthly report'},
        [{
            'id': 'rule_report',
            'label': 'Informe crítico',
            'provider': 'example.com',
            'keywords': ['monthly report'],
            'category': 'money',
            'severity': 'high',
        }],
    )

    assert meta == {
        'categories': ['money'],
        'severity': 'high',
        'severity_reason': 'Regla personalizada: Informe crítico',
        'matched_rule_ids': ['rule_report'],
    }

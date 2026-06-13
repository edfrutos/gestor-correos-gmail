from email.utils import parseaddr


CATEGORIES = {
    'all': {
        'label': '🌐 Todos',
        'color': 'var(--v)',
        'keys': [],
    },
    'money': {
        'label': '💰 Monetario',
        'color': 'var(--w)',
        'keys': [
            'invoice', 'factura', 'billing', 'amount', 'price', '€', '$',
            'statement', 'cobro', 'pago', 'cargo', 'receipt', 'recibo',
            'extracto', 'importe',
        ],
    },
    'warn': {
        'label': '⚠ Avisos',
        'color': 'var(--d)',
        'keys': [
            'expires tomorrow', 'final notice', 'urgent', 'warning',
            'exceeded', 'failed', 'could not', 'expiring', 'aviso', 'alerta',
            'urgente', 'expira', 'expirado', 'action required', 'expirará',
            'run failed',
        ],
    },
    'sub': {
        'label': '🔄 Suscripción',
        'color': 'var(--p)',
        'keys': [
            'subscription', 'renew', 'renewal', 'suscripci', 'licencia',
            'license', 'plan', 'imunify', 'amazon music', 'se renovará',
            'renovación',
        ],
    },
    'ssl': {
        'label': '🔒 SSL/Certs',
        'color': '#9ca3af',
        'keys': ["let's encrypt", 'certificate', 'ssl', 'tls', 'cert', 'acme', 'expiration notice'],
    },
    'sec': {
        'label': '🛡 Seguridad',
        'color': '#f43f5e',
        'keys': [
            'security', 'vulnerability', 'cve', 'malware', 'security patch',
            'exposed', 'access key', 'verification', 'unauthorized',
        ],
    },
    'maint': {
        'label': '🔧 Mantenimiento',
        'color': '#22d3ee',
        'keys': ['maintenance', 'scheduled', 'network upgrade', 'patch', 'restart', 'backup task', 'package update'],
    },
    'domain': {
        'label': '🌐 Dominio',
        'color': '#60a5fa',
        'keys': ['domain', 'dominio', 'whois', 'registr', 'alta del dominio', 'renovación de dominio', 'expire', 'expira', 'dns'],
    },
    'comm': {
        'label': '📢 Comunicación',
        'color': 'var(--s)',
        'keys': [
            "what's new", 'newsletter', 'update', 'release', 'features',
            'novedades', 'adjustments', 'announcement', 'email routing',
            'gpt-', 'introducing', 'dev news', 'updated permissions', 'copilot',
        ],
    },
}


CATEGORY_SEVERITY = {
    'warn': 'high',
    'sec': 'high',
    'ssl': 'high',
    'money': 'medium',
    'sub': 'medium',
    'domain': 'medium',
    'maint': 'medium',
    'comm': 'low',
}

CATEGORY_SEVERITY_REASON = {
    'warn': 'Aviso urgente o fallo detectado',
    'sec': 'Seguridad o vulnerabilidad detectada',
    'ssl': 'Certificado o TLS pendiente',
    'money': 'Factura, cobro o coste detectado',
    'sub': 'Renovación o suscripción pendiente',
    'domain': 'Dominio o vencimiento detectado',
    'maint': 'Mantenimiento o actualización programada',
    'comm': 'Comunicación informativa',
}

SEVERITY_META = {
    'high': {'label': 'Alta', 'color': 'var(--d)'},
    'medium': {'label': 'Media', 'color': 'var(--o)'},
    'low': {'label': 'Baja', 'color': 'var(--s)'},
}

SEVERITY_ORDER = ('high', 'medium', 'low')


def get_base_config():
    return {
        'categories': CATEGORIES,
        'category_severity': CATEGORY_SEVERITY,
        'category_severity_reason': CATEGORY_SEVERITY_REASON,
        'severity_meta': SEVERITY_META,
        'severity_order': SEVERITY_ORDER,
    }


def _sender_domain(from_header):
    address = parseaddr(str(from_header or ''))[1].lower()
    return address.rsplit('@', 1)[1] if '@' in address else ''


def _provider_matches(from_header, provider):
    domain = _sender_domain(from_header)
    return bool(domain) and (domain == provider or domain.endswith('.' + provider))


def classify_email(email):
    haystack = ' '.join([
        str(email.get('subject') or email.get('sub') or ''),
        str(email.get('body') or ''),
        str(email.get('from') or ''),
        str(email.get('tag') or ''),
    ]).lower()
    return [
        key for key, category in CATEGORIES.items()
        if key != 'all' and any(term in haystack for term in category['keys'])
    ]


def matching_custom_rules(email, custom_rules=None):
    haystack = ' '.join([
        str(email.get('subject') or email.get('sub') or ''),
        str(email.get('body') or email.get('snippet') or ''),
        str(email.get('from') or ''),
        str(email.get('tag') or ''),
    ]).lower()
    sender = str(email.get('from') or '')
    matches = []
    for rule in custom_rules or []:
        provider = str(rule.get('provider') or '').lower()
        keywords = [str(value).lower() for value in rule.get('keywords') or [] if value]
        keyword_operator = 'all' if rule.get('keyword_operator') == 'all' else 'any'
        if provider and not _provider_matches(sender, provider):
            continue
        if keywords and keyword_operator == 'all' and not all(keyword in haystack for keyword in keywords):
            continue
        if keywords and keyword_operator == 'any' and not any(keyword in haystack for keyword in keywords):
            continue
        if provider or keywords:
            matches.append(rule)
    return matches


def classify_severity(categories):
    cats = list(categories or [])
    for severity in SEVERITY_ORDER:
        for key in cats:
            if CATEGORY_SEVERITY.get(key) == severity:
                return severity, CATEGORY_SEVERITY_REASON.get(key, 'Correos accionables')
    if cats:
        key = cats[0]
        return CATEGORY_SEVERITY.get(key, 'low'), CATEGORY_SEVERITY_REASON.get(key, 'Comunicación informativa')
    return 'low', 'Sin categorías de riesgo'


def classify_metadata(email, custom_rules=None):
    categories = classify_email(email)
    severity, severity_reason = classify_severity(categories)
    matched_rules = matching_custom_rules(email, custom_rules)
    for rule in matched_rules:
        category = rule.get('category')
        if category in CATEGORIES and category not in categories:
            categories.append(category)
    for target_severity in SEVERITY_ORDER:
        match = next((rule for rule in matched_rules if rule.get('severity') == target_severity), None)
        if match and SEVERITY_ORDER.index(target_severity) <= SEVERITY_ORDER.index(severity):
            severity = target_severity
            severity_reason = f"Regla personalizada: {match.get('label') or 'Sin nombre'}"
            break
    return {
        'categories': categories,
        'severity': severity,
        'severity_reason': severity_reason,
        'matched_rule_ids': [rule.get('id') for rule in matched_rules if rule.get('id')],
    }

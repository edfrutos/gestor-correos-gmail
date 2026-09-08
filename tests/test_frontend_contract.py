from pathlib import Path


INDEX = Path(__file__).parents[1] / 'index.html'
APP_JS = Path(__file__).parents[1] / 'static' / 'app.js'
APP_CSS = Path(__file__).parents[1] / 'static' / 'app.css'
SUMMARY_JS = Path(__file__).parents[1] / 'static' / 'summary.js'
SHARED_JS = Path(__file__).parents[1] / 'static' / 'shared.js'


def test_periodic_summary_ui_and_local_contract():
    html = INDEX.read_text(encoding='utf-8')
    js = SUMMARY_JS.read_text(encoding='utf-8')

    assert 'id="sum-open"' in html
    assert 'id="sum-modal"' in html
    assert 'data-days="7"' in html
    assert 'data-days="30"' in html
    assert 'function buildPeriodicSummary(days)' in js
    assert 'function summaryMarkdown(summary)' in js
    assert 'No se guarda contenido Gmail' in html


def test_periodic_summary_excludes_hidden_and_uses_loaded_messages():
    html = INDEX.read_text(encoding='utf-8')
    js = SUMMARY_JS.read_text(encoding='utf-8')

    assert 'activeEmails' in APP_JS.read_text(encoding='utf-8')
    # Fase 32 · Stage B: el Set de ocultos se comparte vía App.state.deleted.
    # Intención inalterada: el resumen excluye los correos ocultos.
    assert '.filter(e=>!App.state.deleted.has(e.id)' in js
    assert '/api/summary' not in html


def test_trend_analysis_compares_equal_periods_and_detects_recurrence():
    js = SUMMARY_JS.read_text(encoding='utf-8')

    assert 'function buildTrendAnalysis(days,allItems)' in js
    assert 'previousStart=dateDaysAgo((days*2)-1)' in js
    assert 'function recurringSubjectKey(subject)' in js
    assert 'providerIncreases:increasingCounts' in js
    assert 'categoryIncreases:increasingCounts' in js
    assert 'Tendencias frente al período anterior' in js


def test_ai_summary_is_explicit_and_warns_before_remote_transmission():
    html = INDEX.read_text(encoding='utf-8')
    js = SUMMARY_JS.read_text(encoding='utf-8')

    assert 'id="sum-ai"' in html
    assert 'function requestAiSummary()' in js
    # Fase 32 · Stage B: la base de API se comparte vía App.api.
    # Intención inalterada: endpoint correcto y aviso antes de envío remoto.
    assert "fetch(`${App.api}/api/ai-summary`" in js
    assert "aiStatus.remote&&!confirm(" in js


def test_frontend_assets_are_externalized_without_build_tooling():
    html = INDEX.read_text(encoding='utf-8')

    assert '<link rel="icon" href="/static/favicon.svg" type="image/svg+xml">' in html
    assert '<img class="hlogo" src="/static/logo.svg" alt="Gestor de Correos">' in html
    assert '<link rel="stylesheet" href="/static/app.css">' in html
    assert '<script src="/static/shared.js"></script>' in html
    assert '<script src="/static/app.js"></script>' in html
    assert '<script src="/static/summary.js"></script>' in html
    # Fase 32: shared.js define `App` y debe cargar antes que app.js y summary.js.
    assert html.index('/static/shared.js') < html.index('/static/app.js') < html.index('/static/summary.js')
    assert '<style>' not in html
    assert '<script>' not in html
    # Fase 32 · Stage A: sin manejadores JS inline en el HTML.
    assert 'onclick=' not in html
    assert SHARED_JS.exists()
    assert APP_JS.exists()
    assert APP_CSS.exists()
    assert SUMMARY_JS.exists()


def test_shared_namespace_is_declared_and_documented():
    # Fase 32: `App` es el espacio de nombres compartido; lo define shared.js,
    # app.js publica en él y summary.js lo consume sin globales desnudas.
    shared = SHARED_JS.read_text(encoding='utf-8')
    app = APP_JS.read_text(encoding='utf-8')
    summary = SUMMARY_JS.read_text(encoding='utf-8')

    assert 'window.App = window.App ||' in shared
    assert 'App.api = API;' in app
    assert 'App.state.deleted=deleted;' in app
    assert 'SHARED SURFACE' in app
    # Estado propio de summary.js: ya no vive en app.js.
    assert 'summaryDays' not in app and 'summaryData' not in app
    assert 'let summaryDays=30,summaryData=null;' in summary
    # Paneles plegables cableados por JS, no por onclick inline.
    assert "document.querySelectorAll('.ph[data-panel]')" in app


def test_frontend_loads_live_sources_without_embedded_email_pool():
    js = APP_JS.read_text(encoding='utf-8')

    assert 'const BASE=' not in js
    assert 'let activeEmails=[];' in js
    assert 'async function refreshSourcesFromGmail()' in js
    assert 'const sources=[...FIXED,...customSrcs];' in js
    assert 'await refreshSourcesFromGmail();' in js


def test_custom_rules_support_any_or_all_keyword_matching():
    html = INDEX.read_text(encoding='utf-8')
    js = APP_JS.read_text(encoding='utf-8')

    assert 'id="rule-keyword-operator"' in html
    assert 'Alguna palabra' in html
    assert 'Todas las palabras' in html
    assert "r.keyword_operator==='all'?r.keywords.every" in js


def test_responsive_controls_do_not_force_horizontal_overflow():
    css = APP_CSS.read_text(encoding='utf-8')

    assert 'html,body{max-width:100%;overflow-x:hidden;}' in css
    assert '.wrap{max-width:1240px;margin:0 auto;padding:32px 24px 100px;}' in css
    assert '.rule-field{display:flex;flex-direction:column;gap:4px;color:var(--mut);min-width:0;}' in css
    assert 'width:100%;min-width:0;' in css
    assert '#rule-add{grid-column:1/-1;justify-self:end;max-width:100%;}' in css
    assert '.rule-form{grid-template-columns:1fr;}' in css
    assert '.hbar{align-items:stretch;flex-direction:column;}' in css
    assert '.hidden-box{max-width:920px;}' in css


def test_open_message_state_survives_attachment_hydration_render():
    # Fase 30 (ADR-008): la vista de un correo es un modal ("subventana"); la
    # hidratación de adjuntos ocurre al abrir el modal y lo re-renderiza sin
    # cerrarlo, actualizando el objeto fuente de activeEmails.
    js = APP_JS.read_text(encoding='utf-8')

    assert 'function openEmailModal(emailOrig){' in js
    assert "document.getElementById('email-modal').classList.add('show');" in js
    assert 'if(!emailOrig.attachments_checked)hydrateMessageAttachments(emailOrig);' in js
    # Abrir desde una tarjeta usa el objeto vivo de activeEmails, no la copia local.
    assert 'const orig=activeEmails.find(ae=>ae.id===e.id)||e;' in js
    assert 'openEmailModal(orig);' in js
    # Tras hidratar, el modal abierto se vuelve a pintar (no se cierra).
    assert 'if(emailModalEmail&&sources.some(s=>s.id===emailModalEmail.id))renderEmailModal();' in js


def test_attachment_hydration_updates_source_message_and_finishes_on_error():
    js = APP_JS.read_text(encoding='utf-8')

    assert 'const sources=activeEmails.filter(item=>item.id===email.id);' in js
    assert 'if(!sources.length)sources.push(email);' in js
    assert '{signal:AbortSignal.timeout(15000)}' in js
    assert 'item.attachments_checked=true;' in js
    assert "item.attachments_error='';" in js
    assert "item.attachments_error=e.message||'No se pudieron comprobar los adjuntos';" in js
    assert 'No se pudieron comprobar los adjuntos.</span>' in js


def test_hidden_review_and_permanent_delete_are_explicit_flows():
    html = INDEX.read_text(encoding='utf-8')
    js = APP_JS.read_text(encoding='utf-8')

    assert 'id="hidden-modal"' in html
    assert 'id="manage-hidden"' in html
    assert 'id="hidden-restore"' in html
    assert 'id="hidden-delete"' in html
    assert 'id="hidden-forget"' in html
    assert 'id="delete-revoke"' in html
    assert 'id="delete-confirm"' in html
    assert 'id="hidden-prev"' in html
    assert 'id="hidden-next"' in html
    assert 'id="hidden-page"' in html
    assert 'El borrado en Gmail es inmediato e irreversible' in html
    assert 'Usa Shift para seleccionar un rango y Cmd/Ctrl para alternar mensajes individuales' in html
    assert 'Sólo los huérfanos se pueden limpiar localmente' in html
    assert 'Eliminar huérfanos locales' in html
    assert 'Sólo local' in html
    assert 'Afecta a Gmail' in html
    assert 'No toca Gmail' in html
    assert 'Irreversible' in html
    assert "fetch(`${API}/api/hidden?page=${hiddenReviewPage}${qParam}`" in js
    assert 'shiftKey' in js and 'hiddenRangeAnchorId' in js
    assert 'metaKey||ev.ctrlKey' in js
    assert "status==='orphan'" in js
    assert 'purgeOrphanMessages' in js
    assert 'flushSaveState' in js
    assert 'hiddenOrphanPurgePending' in js
    assert "fetch(`${API}/api/delete-authorize`" in js
    assert "fetch(`${API}/api/delete-revoke`" in js
    assert "fetch(`${API}/api/delete-permanent`" in js
    assert 'ELIMINAR PERMANENTEMENTE ${count}' in js
    assert 'Máximo ${limit} por lote. Reduce la selección para continuar.' in js
    assert 'huérfano' in js
    assert 'Página ${hiddenReviewPage} de ${pages} · ${total} ocultos' in js
    assert 'No se puede deshacer' in js
    assert 'puedes limpiar su información local' in js

import json
import os
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse
from urllib.request import Request, urlopen

from validators import ApiError


MAX_PROMPT_LENGTH = 20000


def ai_status():
    base_url = os.environ.get('AI_BASE_URL', '').strip()
    model = os.environ.get('AI_MODEL', '').strip()
    return {
        'configured': bool(base_url and model),
        'model': model or None,
        'remote': bool(base_url and urlparse(base_url).hostname not in {'localhost', '127.0.0.1', '::1'}),
    }


def _completion_url(base_url):
    return base_url.rstrip('/') + '/chat/completions'


def summarize(prompt):
    prompt = str(prompt or '').strip()
    if not prompt:
        raise ApiError('Contenido AI requerido', detail='Envía contenido para resumir')
    if len(prompt) > MAX_PROMPT_LENGTH:
        raise ApiError('Contenido AI demasiado grande', status=413, detail=f'El contenido supera {MAX_PROMPT_LENGTH} caracteres')

    base_url = os.environ.get('AI_BASE_URL', '').strip()
    model = os.environ.get('AI_MODEL', '').strip()
    api_key = os.environ.get('AI_API_KEY', '').strip()
    if not base_url or not model:
        raise ApiError(
            'Integración AI no configurada',
            status=503,
            detail='Configura AI_BASE_URL y AI_MODEL antes de usar el resumen AI',
        )
    parsed = urlparse(base_url)
    if parsed.scheme not in {'http', 'https'} or not parsed.netloc:
        raise ApiError('AI_BASE_URL inválida', detail='AI_BASE_URL debe ser una URL http(s) válida')

    payload = json.dumps({
        'model': model,
        'temperature': 0.2,
        'messages': [
            {
                'role': 'system',
                'content': (
                    'Resume el informe operativo en español. Prioriza riesgos, cambios frente al período anterior '
                    'y acciones concretas. No inventes datos ni importes.'
                ),
            },
            {'role': 'user', 'content': prompt},
        ],
    }).encode('utf-8')
    headers = {'Content-Type': 'application/json'}
    if api_key:
        headers['Authorization'] = f'Bearer {api_key}'
    request = Request(_completion_url(base_url), data=payload, headers=headers, method='POST')
    try:
        with urlopen(request, timeout=60) as response:
            result = json.load(response)
    except HTTPError as exc:
        raise ApiError('Error del proveedor AI', status=502, detail=f'HTTP {exc.code}') from exc
    except (URLError, TimeoutError, json.JSONDecodeError) as exc:
        raise ApiError('Error conectando con AI', status=502, detail=str(exc)) from exc
    try:
        text = result['choices'][0]['message']['content'].strip()
    except (KeyError, IndexError, TypeError, AttributeError) as exc:
        raise ApiError('Respuesta AI inválida', status=502, detail='El proveedor no devolvió un resumen válido') from exc
    if not text:
        raise ApiError('Respuesta AI vacía', status=502)
    return {'summary': text, 'model': model}


def suggest_rules(emails_metadata):
    if not emails_metadata:
        return {'suggestions': []}

    base_url = os.environ.get('AI_BASE_URL', '').strip()
    model = os.environ.get('AI_MODEL', '').strip()
    api_key = os.environ.get('AI_API_KEY', '').strip()
    
    if not base_url or not model:
        raise ApiError('AI no configurada', status=503)

    # Preparar resumen de metadatos para el prompt
    summary = "\n".join([f"- De: {e.get('from')} | Asunto: {e.get('sub')}" for e in emails_metadata[:30]])
    
    payload = json.dumps({
        'model': model,
        'temperature': 0.1,
        'messages': [
            {
                'role': 'system',
                'content': (
                    'Eres un asistente experto en productividad de Gmail. '
                    'Analiza los correos ocultados por el usuario y sugiere hasta 3 reglas de automatización. '
                    'Responde EXCLUSIVAMENTE con un array JSON de objetos. Cada objeto DEBE tener: '
                    '"label" (nombre descriptivo), "provider" (dominio del remitente), '
                    '"keywords" (array de palabras clave del asunto), "category" (elegir entre: money, warn, sub, ssl, sec, maint, domain, comm), '
                    '"severity" (elegir: high, medium, low), "auto_label" (true), "auto_archive" (true).'
                ),
            },
            {'role': 'user', 'content': f'Estos son los correos que he ocultado manualmente:\n{summary}'},
        ],
    }).encode('utf-8')
    
    headers = {'Content-Type': 'application/json'}
    if api_key: headers['Authorization'] = f'Bearer {api_key}'
    
    request = Request(_completion_url(base_url), data=payload, headers=headers, method='POST')
    try:
        with urlopen(request, timeout=30) as response:
            result = json.load(response)
            text = result['choices'][0]['message']['content'].strip()
            # Limpiar posibles bloques de código markdown
            if text.startswith('```'):
                text = text.split('\n', 1)[1].rsplit('\n', 1)[0].strip()
                if text.startswith('json'): text = text[4:].strip()
            return {'suggestions': json.loads(text), 'model': model}
    except Exception as e:
        print(f'[AI Suggest] Error: {e}')
        raise ApiError('Error generando sugerencias AI', detail=str(e))

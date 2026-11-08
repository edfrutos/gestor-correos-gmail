import json
import re
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse
from urllib.request import Request, urlopen

import paths
from settings import LOCAL_AI_ONLY_DETAIL, LOCAL_AI_ONLY_ERROR, ai_config, is_remote
from validators import ApiError


MAX_PROMPT_LENGTH = 20000
_THINK_BLOCK = re.compile(r'<think>.*?</think>', re.DOTALL | re.IGNORECASE)


def strip_reasoning(text):
    """Quita el razonamiento `<think>…</think>` de modelos como qwen3/deepseek-r1.

    Un `</think>` sin apertura (la plantilla ya abrió el bloque) también corta
    todo lo anterior.
    """
    text = _THINK_BLOCK.sub('', text)
    if '</think>' in text.lower():
        text = re.split(r'</think>', text, flags=re.IGNORECASE)[-1]
    return text.strip()


def _blocked(base_url, model):
    return paths.is_app_store() and is_remote(base_url, model)


def _ensure_allowed(base_url, model):
    if _blocked(base_url, model):
        raise ApiError(LOCAL_AI_ONLY_ERROR, status=403, detail=LOCAL_AI_ONLY_DETAIL)


def ai_status():
    base_url, model, _ = ai_config()
    if _blocked(base_url, model):
        return {'configured': False, 'model': None, 'remote': False}
    return {
        'configured': bool(base_url and model),
        'model': model or None,
        'remote': is_remote(base_url, model),
    }


def _completion_url(base_url):
    return base_url.rstrip('/') + '/chat/completions'


def summarize(prompt):
    prompt = str(prompt or '').strip()
    if not prompt:
        raise ApiError('Contenido AI requerido', detail='Envía contenido para resumir')
    if len(prompt) > MAX_PROMPT_LENGTH:
        raise ApiError('Contenido AI demasiado grande', status=413, detail=f'El contenido supera {MAX_PROMPT_LENGTH} caracteres')

    base_url, model, api_key = ai_config()
    _ensure_allowed(base_url, model)
    if not base_url or not model:
        raise ApiError(
            'Integración AI no configurada',
            status=503,
            detail='Configura la URL base y el modelo en Configuración (o AI_BASE_URL y AI_MODEL en .env)',
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
        text = strip_reasoning(result['choices'][0]['message']['content'])
    except (KeyError, IndexError, TypeError, AttributeError) as exc:
        raise ApiError('Respuesta AI inválida', status=502, detail='El proveedor no devolvió un resumen válido') from exc
    if not text:
        raise ApiError('Respuesta AI vacía', status=502)
    return {'summary': text, 'model': model}


def _parse_suggestions(text, model):
    """Extrae la lista de reglas de la respuesta del modelo.

    Los modelos locales no siempre responden solo con JSON: anteponen una frase,
    usan un bloque ```json o envuelven la lista en un objeto ({"reglas": […]}).
    Se toma el primer JSON válido que contenga reglas.
    """
    decoder = json.JSONDecoder()
    for start, char in enumerate(text):
        if char not in '[{':
            continue
        try:
            value, _ = decoder.raw_decode(text, start)
        except ValueError:
            continue
        if isinstance(value, dict):
            if 'label' in value:
                value = [value]
            else:
                value = next((v for v in value.values() if isinstance(v, list)), None)
        if not isinstance(value, list):
            continue
        rules = [item for item in value if isinstance(item, dict) and item.get('label')]
        if rules or not value:
            return rules
    raise ApiError(
        'Respuesta AI sin reglas',
        status=502,
        detail=f'El modelo {model} no respondió con una lista JSON de reglas. Prueba de nuevo o con otro modelo.',
    )


def suggest_rules(emails_metadata):
    if not emails_metadata:
        return {'suggestions': []}

    base_url, model, api_key = ai_config()
    _ensure_allowed(base_url, model)
    
    if not base_url or not model:
        raise ApiError('AI no configurada', status=503, detail='Configura la URL base y el modelo en el panel Configuración')

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
                    'Responde EXCLUSIVAMENTE con un array JSON de objetos, sin texto antes ni después. '
                    'Cada objeto DEBE tener: '
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
    # 60 s, como el resumen: un modelo local tarda más la primera vez, al cargarse.
    try:
        with urlopen(request, timeout=60) as response:
            result = json.load(response)
    except HTTPError as exc:
        raise ApiError('Error del proveedor AI', status=502, detail=f'HTTP {exc.code}') from exc
    except (URLError, TimeoutError, json.JSONDecodeError) as exc:
        raise ApiError('Error conectando con AI', status=502, detail=str(exc)) from exc
    try:
        text = strip_reasoning(result['choices'][0]['message']['content'])
    except (KeyError, IndexError, TypeError, AttributeError) as exc:
        raise ApiError('Respuesta AI inválida', status=502, detail='El proveedor no devolvió sugerencias válidas') from exc
    try:
        return {'suggestions': _parse_suggestions(text, model), 'model': model}
    except ApiError:
        print(f'[AI Suggest] Respuesta sin JSON de reglas: {text[:300]!r}')
        raise

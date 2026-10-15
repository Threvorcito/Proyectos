"""Typed JSON payloads for homework steps: validation and normalization."""
import re

from django.core.exceptions import ValidationError

MAX_TEXT = 255
MAX_LECTURA_TEXT = 5000
PALABRAS_MIN = 3
PALABRAS_MAX = 6
OPTIONS_MIN = 2
OPTIONS_MAX = 4
EXAMPLE_STEPS_MAX = 5
EXERCISES_MAX = 5

ARMA_UNITS = ('letter', 'syllable', 'word')
CONTESTA_KINDS = ('choice', 'build')

_BLANK_RE = re.compile(r'\[([^\[\]]*)\]')


def _text(value, label, *, required=True, limit=MAX_TEXT):
    if value is None:
        value = ''
    if not isinstance(value, str):
        raise ValidationError(f'{label}: se esperaba texto.')
    value = value.strip()
    if required and not value:
        raise ValidationError(f'{label}: es obligatorio.')
    if len(value) > limit:
        raise ValidationError(f'{label}: máximo {limit} caracteres.')
    return value


def _text_list(values, label):
    if not isinstance(values, (list, tuple)):
        raise ValidationError(f'{label}: se esperaba una lista.')
    return [_text(item, label) for item in values]


def _unique(items):
    return list(dict.fromkeys(items))


def _options(values, answer, label):
    options = _unique(_text_list(values, label))
    if not OPTIONS_MIN <= len(options) <= OPTIONS_MAX:
        raise ValidationError(f'{label}: entre {OPTIONS_MIN} y {OPTIONS_MAX} opciones.')
    if answer not in options:
        raise ValidationError(f'{label}: la respuesta debe estar entre las opciones.')
    return options


def parse_blank(text: str) -> tuple[str, str, str]:
    """Split ``text`` around its single ``[blank]`` into (before, blank, after)."""
    matches = list(_BLANK_RE.finditer(text))
    if len(matches) > 1 or text.count('[') != text.count(']') or text.count('[') > 1:
        raise ValidationError('Usa un solo hueco entre corchetes.')
    if not matches:
        if '[' in text or ']' in text:
            raise ValidationError('Los corchetes del hueco no están bien cerrados.')
        return text, '', ''
    match = matches[0]
    blank = match.group(1).strip()
    if not blank:
        raise ValidationError('El hueco entre corchetes no puede estar vacío.')
    return text[:match.start()], blank, text[match.end():]


def _clean_mira(data):
    return {'question': _text(data.get('question'), 'Pregunta')}


def _clean_lectura(data):
    return {'text': _text(data.get('text'), 'Texto', required=False, limit=MAX_LECTURA_TEXT)}


def _clean_palabras(data):
    words = _unique(_text_list(data.get('words', []), 'Palabra'))
    if not PALABRAS_MIN <= len(words) <= PALABRAS_MAX:
        raise ValidationError(f'Palabras: entre {PALABRAS_MIN} y {PALABRAS_MAX} palabras distintas.')
    return {'words': words}


def _clean_contesta(data):
    kind = data.get('kind')
    if kind not in CONTESTA_KINDS:
        raise ValidationError('Tipo de respuesta no válido.')
    question = _text(data.get('question'), 'Pregunta')
    answer = _text(data.get('answer'), 'Respuesta')
    options = _options(data.get('options', []), answer, 'Opciones') if kind == 'choice' else []
    return {'question': question, 'kind': kind, 'options': options, 'answer': answer}


def _clean_arma(data):
    unit = data.get('unit')
    if unit not in ARMA_UNITS:
        raise ValidationError('Unidad no válida.')
    text = _text(data.get('text'), 'Texto')
    parse_blank(text)
    return {'text': text, 'unit': unit}


def _clean_ejemplo(data):
    steps = _text_list(data.get('example_steps', []), 'Paso del ejemplo')
    if not 1 <= len(steps) <= EXAMPLE_STEPS_MAX:
        raise ValidationError(f'Ejemplo: entre 1 y {EXAMPLE_STEPS_MAX} pasos.')
    raw_exercises = data.get('exercises', [])
    if not isinstance(raw_exercises, (list, tuple)):
        raise ValidationError('Ejercicios: se esperaba una lista.')
    if not 1 <= len(raw_exercises) <= EXERCISES_MAX:
        raise ValidationError(f'Ejemplo: entre 1 y {EXERCISES_MAX} ejercicios.')
    exercises = []
    for raw in raw_exercises:
        if not isinstance(raw, dict):
            raise ValidationError('Ejercicio no válido.')
        answer = _text(raw.get('answer'), 'Respuesta')
        exercises.append({
            'prompt': _text(raw.get('prompt'), 'Ejercicio'),
            'answer': answer,
            'options': _options(raw.get('options', []), answer, 'Opciones'),
        })
    return {'example_steps': steps, 'exercises': exercises}


_CLEANERS = {
    'mira': _clean_mira,
    'lectura': _clean_lectura,
    'palabras': _clean_palabras,
    'contesta': _clean_contesta,
    'arma': _clean_arma,
    'ejemplo': _clean_ejemplo,
}


def clean_payload(step_type: str, data: dict) -> dict:
    """Return a normalized copy of ``data`` for ``step_type`` or raise ValidationError."""
    cleaner = _CLEANERS.get(step_type)
    if cleaner is None:
        raise ValidationError('Tipo de paso desconocido.')
    if not isinstance(data, dict):
        raise ValidationError('El contenido del paso no es válido.')
    return cleaner(data)

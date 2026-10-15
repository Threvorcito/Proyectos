from dataclasses import dataclass, field

from .decoding import decode_word
from .models import TaskStep
from .payloads import MAX_TEXT, build_target
from .writing import BUILD_MAX_UNITS, check_build, split_units


class InvalidAnswer(ValueError):
    """The submitted payload cannot be evaluated for this step."""


@dataclass
class Evaluation:
    correct: bool
    answer_text: str
    model_answer: str
    hint: dict
    omissions: list[tuple[int, str]] = field(default_factory=list)
    target: str = ''


def _evaluate_choice(step: TaskStep, payload: dict) -> Evaluation:
    options = step.payload.get('options', [])
    choice = payload.get('choice') if isinstance(payload, dict) else None
    if isinstance(choice, bool) or not isinstance(choice, int) or not 0 <= choice < len(options):
        raise InvalidAnswer('choice')
    answer = step.payload['answer']
    picked = options[choice]
    return Evaluation(
        correct=picked == answer,
        answer_text=picked[:MAX_TEXT],
        model_answer=answer,
        hint={'say': step.payload.get('question', ''), 'hole_index': None, 'kind': 'try_again'},
    )


def is_build_step(step: TaskStep) -> bool:
    if step.step_type == TaskStep.StepType.ARMA:
        return True
    return step.step_type == TaskStep.StepType.CONTESTA and step.payload.get('kind') == 'build'


def _tiles(payload: dict) -> list[str]:
    tiles = payload.get('tiles') if isinstance(payload, dict) else None
    if (
        not isinstance(tiles, list)
        or not 1 <= len(tiles) <= 2 * BUILD_MAX_UNITS
        or not all(isinstance(tile, str) and 0 < len(tile) <= MAX_TEXT for tile in tiles)
    ):
        raise InvalidAnswer('tiles')
    return tiles


def _missing_sound(target_text: str, unit: str, units: list[str], index: int) -> str:
    """What to say for the missing unit: its phoneme for a letter, never the letter name."""
    if unit == 'letter':
        letters = decode_word(target_text)['letters']
        if len(letters) == len(units) and letters[index]['say']:
            return letters[index]['say']
    return units[index]


def _evaluate_build(step: TaskStep, payload: dict) -> Evaluation:
    tiles = _tiles(payload)
    target = build_target(step.step_type, step.payload)
    units = split_units(target.text, target.unit)
    check = check_build(units, tiles)
    joiner = ' ' if target.unit == 'word' else ''
    if check.status == 'omission':
        hint = {
            'say': _missing_sound(target.text, target.unit, units, check.hole_index),
            'hole_index': check.hole_index,
            'kind': 'omission',
        }
    else:
        hint = {'say': target.text, 'hole_index': None, 'kind': 'try_again'}
    return Evaluation(
        correct=check.status == 'correct',
        answer_text=joiner.join(tiles)[:MAX_TEXT],
        model_answer=target.full_text,
        hint=hint,
        omissions=check.missing,
        target=target.text,
    )


def evaluate(step: TaskStep, item_index: int, payload: dict) -> Evaluation:
    if step.step_type == TaskStep.StepType.CONTESTA and step.payload.get('kind') == 'choice':
        return _evaluate_choice(step, payload)
    if is_build_step(step):
        return _evaluate_build(step, payload)
    raise InvalidAnswer(step.step_type)

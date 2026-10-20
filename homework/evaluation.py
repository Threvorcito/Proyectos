from dataclasses import dataclass, field

from .decoding import decode_word
from .dictation import ITEMS as DICTADO_ITEMS, item_target
from .models import TaskStep
from .phonemes import audio_for
from .payloads import MAX_TEXT, BuildTarget, build_target
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


def _evaluate_choice(options: list, answer: str, question: str, payload: dict) -> Evaluation:
    choice = payload.get('choice') if isinstance(payload, dict) else None
    if isinstance(choice, bool) or not isinstance(choice, int) or not 0 <= choice < len(options):
        raise InvalidAnswer('choice')
    picked = options[choice]
    return Evaluation(
        correct=picked == answer,
        answer_text=picked[:MAX_TEXT],
        model_answer=answer,
        hint={'say': question, 'hole_index': None, 'kind': 'try_again'},
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


def _missing_sound(target_text: str, unit: str, units: list[str], index: int) -> tuple[str, str]:
    """(say, audio URL) for the missing unit: its phoneme for a letter, never the letter name.

    The audio comes from the same table decode.js uses (phonemes.PHONEME_AUDIO, keyed by the spoken string),
    so recording a sound later needs no code change; '' means "use speech".
    """
    if unit == 'letter':
        letters = decode_word(target_text)['letters']
        if len(letters) == len(units) and letters[index]['say']:
            return letters[index]['say'], letters[index]['audio']
    return units[index], audio_for(units[index])


def _evaluate_build_target(target: BuildTarget, payload: dict) -> Evaluation:
    tiles = _tiles(payload)
    units = split_units(target.text, target.unit)
    check = check_build(units, tiles)
    joiner = ' ' if target.unit == 'word' else ''
    if check.status == 'omission':
        say, audio = _missing_sound(target.text, target.unit, units, check.hole_index)
        hint = {'say': say, 'hole_index': check.hole_index, 'kind': 'omission'}
        if audio:
            hint['audio'] = audio
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


def _evaluate_build(step: TaskStep, payload: dict) -> Evaluation:
    return _evaluate_build_target(build_target(step.step_type, step.payload), payload)


def evaluate(step: TaskStep, item_index: int, payload: dict) -> Evaluation:
    if step.step_type == TaskStep.StepType.CONTESTA and step.payload.get('kind') == 'choice':
        data = step.payload
        return _evaluate_choice(data.get('options', []), data['answer'], data.get('question', ''), payload)
    if step.step_type == TaskStep.StepType.EJEMPLO:
        exercises = step.payload.get('exercises', [])
        if not 0 <= item_index < len(exercises):
            raise InvalidAnswer('item')
        exercise = exercises[item_index]
        return _evaluate_choice(exercise['options'], exercise['answer'], exercise['prompt'], payload)
    if step.step_type == TaskStep.StepType.DICTADO:
        if not 0 <= item_index < DICTADO_ITEMS:
            raise InvalidAnswer('item')
        return _evaluate_build_target(item_target(step.payload, item_index), payload)
    if is_build_step(step):
        return _evaluate_build(step, payload)
    raise InvalidAnswer(step.step_type)

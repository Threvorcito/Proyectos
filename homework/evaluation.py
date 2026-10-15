from dataclasses import dataclass, field

from .models import TaskStep
from .payloads import MAX_TEXT


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


def evaluate(step: TaskStep, item_index: int, payload: dict) -> Evaluation:
    if step.step_type == TaskStep.StepType.CONTESTA and step.payload.get('kind') == 'choice':
        return _evaluate_choice(step, payload)
    raise InvalidAnswer(step.step_type)

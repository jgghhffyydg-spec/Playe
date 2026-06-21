"""Spaced repetition storage and scheduling for English phrases."""

from __future__ import annotations

import json
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from typing import List

REPETITION_PLAN = [
    ("Repeat 10 times now", timedelta(seconds=0)),
    ("Review after 10 minutes", timedelta(minutes=10)),
    ("Review after 1 hour", timedelta(hours=1)),
    ("Review after 1 day", timedelta(days=1)),
    ("Review after 1 week", timedelta(weeks=1)),
]
DATA_FILE = Path("phrases.json")
DATETIME_FORMAT = "%Y-%m-%dT%H:%M:%S"


@dataclass
class Phrase:
    english: str
    translation: str = ""
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    created_at: str = field(default_factory=lambda: datetime.now().strftime(DATETIME_FORMAT))
    review_step: int = 0
    next_review: str = field(default_factory=lambda: datetime.now().strftime(DATETIME_FORMAT))
    completed: bool = False

    @property
    def due_at(self) -> datetime:
        return datetime.strptime(self.next_review, DATETIME_FORMAT)

    @property
    def status(self) -> str:
        if self.completed:
            return "Finished"
        step_name = REPETITION_PLAN[min(self.review_step, len(REPETITION_PLAN) - 1)][0]
        if self.due_at <= datetime.now():
            return f"Due now · {step_name}"
        return f"Next: {self.due_at.strftime('%Y-%m-%d %H:%M')} · {step_name}"


class PhraseStore:
    def __init__(self, path: Path = DATA_FILE) -> None:
        self.path = path
        self.phrases: List[Phrase] = []
        self.load()

    def load(self) -> None:
        if not self.path.exists():
            self.phrases = []
            return
        with self.path.open("r", encoding="utf-8") as file:
            self.phrases = [Phrase(**item) for item in json.load(file)]

    def save(self) -> None:
        with self.path.open("w", encoding="utf-8") as file:
            json.dump([asdict(phrase) for phrase in self.phrases], file, indent=2, ensure_ascii=False)

    def add_phrase(self, english: str, translation: str = "") -> Phrase:
        phrase = Phrase(english=english.strip(), translation=translation.strip())
        self.phrases.append(phrase)
        self.save()
        return phrase

    def due_phrases(self) -> List[Phrase]:
        now = datetime.now()
        return [phrase for phrase in self.phrases if not phrase.completed and phrase.due_at <= now]

    def mark_reviewed(self, phrase_id: str) -> None:
        for phrase in self.phrases:
            if phrase.id != phrase_id:
                continue
            phrase.review_step += 1
            if phrase.review_step >= len(REPETITION_PLAN):
                phrase.completed = True
            else:
                phrase.next_review = (datetime.now() + REPETITION_PLAN[phrase.review_step][1]).strftime(DATETIME_FORMAT)
            self.save()
            return


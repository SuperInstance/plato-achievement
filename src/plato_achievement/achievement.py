"""Achievement tracking with loss metrics and milestones."""

import time
from dataclasses import dataclass, field

@dataclass
class Achievement:
    name: str
    target: float
    current: float = 0.0
    achieved: bool = False
    achieved_at: float = 0.0
    progress: float = 0.0

class AchievementTracker:
    def __init__(self):
        self._achievements: dict[str, Achievement] = {}
        self._history: list[dict] = []

    def define(self, name: str, target: float) -> Achievement:
        a = Achievement(name=name, target=target)
        self._achievements[name] = a
        return a

    def update(self, name: str, value: float) -> Achievement:
        a = self._achievements.get(name)
        if not a: a = self.define(name, value)
        a.current = value
        a.progress = min(value / a.target, 1.0) if a.target > 0 else 1.0
        if a.progress >= 1.0 and not a.achieved:
            a.achieved = True
            a.achieved_at = time.time()
            self._history.append({"name": name, "target": a.target, "value": value, "at": a.achieved_at})
        return a

    def achievement_loss(self) -> float:
        unachieved = [a for a in self._achievements.values() if not a.achieved]
        if not unachieved: return 0.0
        return sum(1.0 - a.progress for a in unachieved) / len(unachieved)

    def get(self, name: str) -> Achievement:
        return self._achievements.get(name)

    def all_achieved(self) -> list[Achievement]:
        return [a for a in self._achievements.values() if a.achieved]

    def unachieved(self) -> list[Achievement]:
        return [a for a in self._achievements.values() if not a.achieved]

    @property
    def stats(self) -> dict:
        total = len(self._achievements)
        done = len(self.all_achieved())
        return {"total": total, "achieved": done, "unachieved": total - done,
                "loss": self.achievement_loss(), "milestones": len(self._history)}

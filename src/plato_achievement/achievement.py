"""Achievement system — badges, conditions, progress tracking, streaks."""
import time
from dataclasses import dataclass, field
from typing import Callable, Optional
from collections import defaultdict

@dataclass
class Achievement:
    id: str
    name: str
    description: str = ""
    category: str = "general"
    condition: str = ""  # key to check against
    threshold: int = 1
    reward: int = 0
    hidden: bool = False
    created_at: float = field(default_factory=time.time)

@dataclass
class AchievementProgress:
    achievement_id: str
    current: int = 0
    threshold: int = 1
    unlocked_at: float = 0.0
    unlocked: bool = False

@dataclass
class StreakRecord:
    key: str
    count: int = 0
    last_event: float = 0.0
    longest: int = 0

class AchievementSystem:
    def __init__(self):
        self._achievements: dict[str, Achievement] = {}
        self._progress: dict[str, AchievementProgress] = {}
        self._unlocked: set[str] = set()
        self._streaks: dict[str, StreakRecord] = {}
        self._history: list[dict] = []
        self._counters: dict[str, int] = defaultdict(int)

    def define(self, achievement_id: str, name: str, description: str = "",
               category: str = "general", condition: str = "", threshold: int = 1,
               reward: int = 0, hidden: bool = False) -> Achievement:
        ach = Achievement(id=achievement_id, name=name, description=description,
                         category=category, condition=condition, threshold=threshold,
                         reward=reward, hidden=hidden)
        self._achievements[achievement_id] = ach
        self._progress[achievement_id] = AchievementProgress(
            achievement_id=achievement_id, threshold=threshold)
        return ach

    def record_event(self, event_type: str, amount: int = 1) -> list[Achievement]:
        self._counters[event_type] += amount
        unlocked = []
        now = time.time()
        # Update streak
        streak = self._streaks.get(event_type)
        if streak:
            if now - streak.last_event < 86400:  # within 24h
                streak.count += 1
                streak.longest = max(streak.longest, streak.count)
            elif now - streak.last_event > 172800:  # > 48h, reset
                streak.count = 1
            streak.last_event = now
        else:
            self._streaks[event_type] = StreakRecord(key=event_type, count=1, last_event=now)

        # Check achievements
        for ach_id, ach in self._achievements.items():
            if ach_id in self._unlocked:
                continue
            prog = self._progress[ach_id]
            if ach.condition:
                prog.current = self._counters.get(ach.condition, 0)
            else:
                prog.current += amount
            if prog.current >= prog.threshold:
                prog.unlocked = True
                prog.unlocked_at = now
                self._unlocked.add(ach_id)
                self._history.append({"achievement": ach_id, "unlocked_at": now,
                                      "current": prog.current})
                unlocked.append(ach)
        return unlocked

    def get_progress(self, achievement_id: str) -> Optional[AchievementProgress]:
        return self._progress.get(achievement_id)

    def is_unlocked(self, achievement_id: str) -> bool:
        return achievement_id in self._unlocked

    def get_streak(self, event_type: str) -> StreakRecord:
        return self._streaks.get(event_type, StreakRecord(key=event_type))

    def all_unlocked(self) -> list[Achievement]:
        return [self._achievements[aid] for aid in self._unlocked if aid in self._achievements]

    def by_category(self, category: str) -> list[dict]:
        results = []
        for ach in self._achievements.values():
            if ach.category != category:
                continue
            prog = self._progress.get(ach.id)
            results.append({"id": ach.id, "name": ach.name, "unlocked": ach.id in self._unlocked,
                          "progress": prog.current if prog else 0,
                          "threshold": ach.threshold})
        return results

    def categories(self) -> dict[str, int]:
        cats: dict[str, int] = defaultdict(int)
        for ach in self._achievements.values():
            cats[ach.category] += 1
        return dict(cats)

    def recent_unlocks(self, n: int = 10) -> list[dict]:
        return sorted(self._history, key=lambda h: h["unlocked_at"], reverse=True)[:n]

    @property
    def stats(self) -> dict:
        return {"total": len(self._achievements), "unlocked": len(self._unlocked),
                "categories": self.categories(),
                "streaks": {k: v.count for k, v in self._streaks.items()},
                "total_events": sum(self._counters.values())}

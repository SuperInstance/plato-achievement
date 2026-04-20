"""Achievement system — conditions, progress tracking, tiers, unlocks, notifications."""
import time
from dataclasses import dataclass, field
from typing import Optional, Callable, Any
from collections import defaultdict
from enum import Enum

class AchievementTier(Enum):
    BRONZE = "bronze"
    SILVER = "silver"
    GOLD = "gold"
    PLATINUM = "platinum"
    LEGENDARY = "legendary"

class AchievementState(Enum):
    LOCKED = "locked"
    IN_PROGRESS = "in_progress"
    UNLOCKED = "unlocked"
    CLAIMED = "claimed"

@dataclass
class Condition:
    metric: str         # e.g., "tiles_created", "rooms_visited"
    operator: str       # "gte", "lte", "eq", "contains"
    target: Any
    description: str = ""

@dataclass
class Achievement:
    id: str
    name: str
    description: str
    tier: AchievementTier = AchievementTier.BRONZE
    conditions: list[Condition] = field(default_factory=list)
    reward: dict = field(default_factory=dict)
    category: str = "general"
    hidden: bool = False  # hidden until unlocked
    depends_on: str = ""  # prerequisite achievement
    created_at: float = field(default_factory=time.time)

@dataclass
class AchievementProgress:
    achievement_id: str
    state: AchievementState = AchievementState.LOCKED
    progress: float = 0.0     # 0.0 to 1.0
    conditions_met: list[str] = field(default_factory=list)
    unlocked_at: float = 0.0
    claimed_at: float = 0.0
    metric_values: dict = field(default_factory=dict)

class AchievementSystem:
    def __init__(self):
        self._achievements: dict[str, Achievement] = {}
        self._progress: dict[str, dict[str, AchievementProgress]] = defaultdict(dict)  # agent → {ach_id → progress}
        self._metric_values: dict[str, dict[str, float]] = defaultdict(dict)  # agent → {metric → value}
        self._unlocks: list[dict] = []
        self._callbacks: list[Callable] = []

    def define(self, achievement: Achievement):
        self._achievements[achievement.id] = achievement

    def track(self, agent_id: str, metric: str, value: float):
        self._metric_values[agent_id][metric] = value
        self._check_achievements(agent_id)

    def increment(self, agent_id: str, metric: str, amount: float = 1.0):
        current = self._metric_values[agent_id].get(metric, 0.0)
        self._metric_values[agent_id][metric] = current + amount
        self._check_achievements(agent_id)

    def get_progress(self, agent_id: str, achievement_id: str) -> Optional[AchievementProgress]:
        return self._progress[agent_id].get(achievement_id)

    def agent_achievements(self, agent_id: str) -> list[AchievementProgress]:
        return list(self._progress[agent_id].values())

    def agent_unlocked(self, agent_id: str) -> list[AchievementProgress]:
        return [p for p in self._progress[agent_id].values()
                if p.state in (AchievementState.UNLOCKED, AchievementState.CLAIMED)]

    def claim(self, agent_id: str, achievement_id: str) -> Optional[dict]:
        progress = self._progress[agent_id].get(achievement_id)
        if not progress or progress.state != AchievementState.UNLOCKED:
            return None
        achievement = self._achievements.get(achievement_id)
        if not achievement:
            return None
        progress.state = AchievementState.CLAIMED
        progress.claimed_at = time.time()
        return achievement.reward

    def by_category(self, category: str) -> list[Achievement]:
        return [a for a in self._achievements.values() if a.category == category]

    def by_tier(self, tier: AchievementTier) -> list[Achievement]:
        return [a for a in self._achievements.values() if a.tier == tier]

    def leaderboard(self, achievement_id: str, n: int = 10) -> list[dict]:
        entries = []
        for agent_id, progresses in self._progress.items():
            p = progresses.get(achievement_id)
            if p and p.state in (AchievementState.UNLOCKED, AchievementState.CLAIMED):
                entries.append({"agent_id": agent_id, "unlocked_at": p.unlocked_at})
        entries.sort(key=lambda e: e["unlocked_at"])
        return entries[:n]

    def on_unlock(self, callback: Callable):
        self._callbacks.append(callback)

    def _check_achievements(self, agent_id: str):
        metrics = self._metric_values[agent_id]
        for ach_id, achievement in self._achievements.items():
            progress = self._progress[agent_id].get(ach_id)
            if not progress:
                progress = AchievementProgress(achievement_id=ach_id,
                                                state=AchievementState.LOCKED)
                self._progress[agent_id][ach_id] = progress
            if progress.state in (AchievementState.UNLOCKED, AchievementState.CLAIMED):
                continue
            # Check prerequisites
            if achievement.depends_on:
                dep = self._progress[agent_id].get(achievement.depends_on)
                if not dep or dep.state != AchievementState.UNLOCKED:
                    continue
            # Check conditions
            met = []
            total = len(achievement.conditions)
            for cond in achievement.conditions:
                value = metrics.get(cond.metric, 0)
                if self._check_condition(cond, value):
                    met.append(cond.metric)
            progress.conditions_met = met
            progress.progress = len(met) / max(total, 1)
            progress.metric_values = dict(metrics)
            if len(met) == total and total > 0:
                progress.state = AchievementState.UNLOCKED
                progress.unlocked_at = time.time()
                self._unlocks.append({"agent_id": agent_id, "achievement_id": ach_id,
                                     "timestamp": time.time()})
                for cb in self._callbacks:
                    try: cb(agent_id, achievement)
                    except: pass

    def _check_condition(self, cond: Condition, value: Any) -> bool:
        try:
            if cond.operator == "gte":
                return float(value) >= float(cond.target)
            elif cond.operator == "lte":
                return float(value) <= float(cond.target)
            elif cond.operator == "eq":
                return value == cond.target
            elif cond.operator == "contains":
                return cond.target in str(value)
            elif cond.operator == "gt":
                return float(value) > float(cond.target)
        except (ValueError, TypeError):
            return False
        return False

    @property
    def stats(self) -> dict:
        return {"achievements": len(self._achievements),
                "agents": len(self._progress),
                "total_unlocks": len(self._unlocks)}

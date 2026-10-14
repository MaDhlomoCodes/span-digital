"""Core data structures and standings logic for a 1974/75 English First Division table."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Iterable, List

# Historical 1974/75 points system: 2 for a win, 1 for a draw, 0 for a loss.
WIN_POINTS = 2
DRAW_POINTS = 1
LOSS_POINTS = 0


@dataclass
class Team:
    """A club's record in the league table."""

    name: str
    played: int = 0
    won: int = 0
    drawn: int = 0
    lost: int = 0
    goals_for: int = 0
    goals_against: int = 0

    @property
    def points(self) -> int:
        return (
            self.won * WIN_POINTS
            + self.drawn * DRAW_POINTS
            + self.lost * LOSS_POINTS
        )

    @property
    def goal_average(self) -> float:
        """Goals scored divided by goals conceded (not goal difference).

        With no goals conceded, the average is infinite if the team has scored,
        since the ratio is unbounded. A team with no goals either way is 0.0.
        """
        if self.goals_against == 0:
            return float("inf") if self.goals_for > 0 else 0.0
        return self.goals_for / self.goals_against

    def record_result(self, scored: int, conceded: int) -> None:
        """Update the team's record for a single match."""
        if scored < 0 or conceded < 0:
            raise ValueError("Goals cannot be negative")

        self.played += 1
        self.goals_for += scored
        self.goals_against += conceded

        if scored > conceded:
            self.won += 1
        elif scored == conceded:
            self.drawn += 1
        else:
            self.lost += 1


def sort_key(team: Team) -> tuple:
    """Ordering for the table: points, then goal average, then total goals for.

    The club name is a final deterministic fallback for teams that are level
    on all three criteria, so the output is stable across runs.
    """
    return (-team.points, -team.goal_average, -team.goals_for, team.name)


def league_table(teams: Iterable[Team]) -> List[Team]:
    """Return teams sorted into league position order (position 1 first)."""
    return sorted(teams, key=sort_key)


class LeagueTable:
    """Tracks every club in the division and applies match results to them."""

    def __init__(self, team_names: Iterable[str]) -> None:
        self._teams: Dict[str, Team] = {name: Team(name) for name in team_names}

    def __getitem__(self, name: str) -> Team:
        return self._teams[name]

    def record_match(
        self, home: str, away: str, home_goals: int, away_goals: int
    ) -> None:
        """Apply one fixture's result to both clubs."""
        if home == away:
            raise ValueError("A team cannot play itself")
        self._teams[home].record_result(home_goals, away_goals)
        self._teams[away].record_result(away_goals, home_goals)

    def standings(self) -> List[Team]:
        return league_table(self._teams.values())
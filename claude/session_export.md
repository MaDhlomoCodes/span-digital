I am building a Python command-line tool that calculates English First Division league standings for week 10 of the 1974/75 season. 

Please implement the core data structures and logic in src/standings.py:
1. Use a team dataclass tracking played, won, drawn, lost, goals_for, goals_against, and points.
2. Implement historical 1974/75 rules: 2 points for a win, 1 for a draw, 0 for a loss.
3. Crucially, the tie-breaker must be **Goal Average** (Goals For / Goals Conceded) rather than modern goal difference, followed by total Goals For.

python
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
A few notes on the implementation:

Points are computed from the win, draw, and loss counts rather than stored separately, so they can’t drift out of sync with the record.
Goal average is goals_for / goals_against. If a team has conceded nothing, it returns infinity (when it has scored) so that it ranks above teams with a finite average. The zero-zero case returns 0.0 so it doesn’t cause a division error.
Sorting applies goal average only among teams level on points, and total goals for only among teams level on both points and goal average. The final tiebreak on name is an arbitrary convention, not a historical rule. If you have a specific rule for teams still level after goals for (such as a playoff or a fixed ordering), let me know and I’ll change it.
Week 10: you can build the table by calling record_match for every fixture played through week 10, then calling standings(). Filtering fixtures by week is left to your data loader.
implement src/main.py to handle the command-line interface and CSV handling:
1. Use argparse to allow passing an input CSV filename via the command line (e.g., python -m src.main "1974-75 First Division — Weeks 1-10 (complete).csv"), with a graceful fallback to reading from stdin.
2. Parse the match rows, initialize the LeagueTable from src.standings, and process all matches.
3. Write the resulting table out as CSV to standard output (stdout) with the headers: Pos,Team,Pld,W,D,L,GF,GA,GAv,Pts (rounding Goal Average to 3 decimal places).
4. Also write a script or add a helper command so it automatically writes the output to output.csv

I don’t have your CSV, so I’ve assumed one row per match with these columns, matched case-insensitively and ignoring spaces, underscores, and punctuation:

Week,Home Team,Away Team,Home Goals,Away Goals
1,Arsenal,Liverpool,1,0
Common aliases such as HomeTeam, FTHG, or Matchweek also work. If your file differs, the alias table at the top of main.py is the place to adjust.

src/main.py
python
"""Command-line entry point: read match results from CSV and print the league table as CSV."""

from __future__ import annotations

import argparse
import csv
import re
import sys
from typing import Dict, List, Optional, Sequence, TextIO

from src.standings import LeagueTable

OUTPUT_HEADERS = ["Pos", "Team", "Pld", "W", "D", "L", "GF", "GA", "GAv", "Pts"]

# Accepted input column names. Headers are lowercased and stripped of
# non-alphanumeric characters before matching, so "Home Team" and "home_team"
# both resolve to the "home" field.
COLUMN_ALIASES = {
    "home": ("hometeam", "home", "homeclub"),
    "away": ("awayteam", "away", "awayclub"),
    "home_goals": ("homegoals", "homescore", "hg", "fthg"),
    "away_goals": ("awaygoals", "awayscore", "ag", "ftag"),
    "week": ("week", "matchweek", "gw"),
}
REQUIRED_FIELDS = ("home", "away", "home_goals", "away_goals")


def _normalise(header: str) -> str:
    return re.sub(r"[^a-z0-9]", "", header.lower())


def _find_columns(fieldnames: Sequence[str]) -> Dict[str, str]:
    """Map each logical field name to the actual header used in the file."""
    normalised = {_normalise(name): name for name in fieldnames if name}
    found: Dict[str, str] = {}
    for logical, aliases in COLUMN_ALIASES.items():
        for alias in aliases:
            if alias in normalised:
                found[logical] = normalised[alias]
                break

    missing = [field for field in REQUIRED_FIELDS if field not in found]
    if missing:
        raise ValueError(f"CSV is missing required column(s): {', '.join(missing)}")
    return found


def read_matches(stream: TextIO, max_week: Optional[int] = None) -> List[dict]:
    """Parse match rows from a CSV stream, optionally keeping only weeks up to max_week."""
    reader = csv.DictReader(stream)
    if not reader.fieldnames:
        raise ValueError("CSV has no header row")

    cols = _find_columns(reader.fieldnames)
    matches: List[dict] = []

    for line_no, row in enumerate(reader, start=2):
        if not any((value or "").strip() for value in row.values()):
            continue  # skip blank lines

        try:
            home = (row[cols["home"]] or "").strip()
            away = (row[cols["away"]] or "").strip()
            home_goals = int(row[cols["home_goals"]])
            away_goals = int(row[cols["away_goals"]])
            week = int(row[cols["week"]]) if "week" in cols else None
        except (TypeError, ValueError) as exc:
            raise ValueError(f"line {line_no}: could not parse match ({exc})") from exc

        if not home or not away:
            raise ValueError(f"line {line_no}: team name is empty")

        if max_week is not None and week is not None and week > max_week:
            continue

        matches.append(
            {
                "home": home,
                "away": away,
                "home_goals": home_goals,
                "away_goals": away_goals,
            }
        )

    return matches


def build_table(matches: List[dict]) -> LeagueTable:
    """Create a LeagueTable for every club seen and apply each result."""
    names = sorted({m["home"] for m in matches} | {m["away"] for m in matches})
    table = LeagueTable(names)
    for m in matches:
        table.record_match(m["home"], m["away"], m["home_goals"], m["away_goals"])
    return table


def write_table(table: LeagueTable, out: TextIO) -> None:
    """Write the table as CSV, with goal average rounded to three decimal places."""
    writer = csv.writer(out, lineterminator="\n")
    writer.writerow(OUTPUT_HEADERS)
    for position, team in enumerate(table.standings(), start=1):
        writer.writerow(
            [
                position,
                team.name,
                team.played,
                team.won,
                team.drawn,
                team.lost,
                team.goals_for,
                team.goals_against,
                f"{team.goal_average:.3f}",
                team.points,
            ]
        )


def parse_args(argv: Optional[Sequence[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Compute a 1974/75 First Division table from a match CSV and print it as CSV."
    )
    parser.add_argument(
        "csv_file",
        nargs="?",
        help="Path to the match CSV. If omitted, the CSV is read from stdin.",
    )
    parser.add_argument(
        "--max-week",
        type=int,
        help="Only include matches up to and including this week.",
    )
    return parser.parse_args(argv)


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = parse_args(argv)

    try:
        if args.csv_file:
            with open(args.csv_file, newline="", encoding="utf-8-sig") as f:
                matches = read_matches(f, args.max_week)
        else:
            if sys.stdin.isatty():
                print(
                    "error: no input file given and nothing piped on stdin.\n"
                    "usage: python -m src.main <matches.csv> [--max-week N]",
                    file=sys.stderr,
                )
                return 2
            matches = read_matches(sys.stdin, args.max_week)

        table = build_table(matches)
    except FileNotFoundError:
        print(f"error: file not found: {args.csv_file}", file=sys.stderr)
        return 1
    except ValueError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    write_table(table, sys.stdout)
    return 0


if __name__ == "__main__":
    sys.exit(main())
scripts/standings.sh
This writes the table to output.csv in the directory you run it from. The input path is resolved before the script changes into the project root, so relative paths keep working.

bash
#!/usr/bin/env bash
# Usage: scripts/standings.sh "1974-75 First Division — Weeks 1-10 (complete).csv" [--max-week N]
set -euo pipefail

if [ $# -lt 1 ]; then
    echo "usage: $0 <matches.csv> [--max-week N]" >&2
    exit 1
fi

INPUT="$(realpath "$1")"
shift
OUTPUT="$PWD/output.csv"
ROOT="$(cd "$(dirname "$0")/.." && pwd)"

cd "$ROOT"
python -m src.main "$INPUT" "$@" > "$OUTPUT"
echo "Wrote $OUTPUT"
Make it executable once with chmod +x scripts/standings.sh, then run:

bash
scripts/standings.sh "1974-75 First Division — Weeks 1-10 (complete).csv" --max-week 10
Or pipe in a file directly:

bash
python -m src.main < matches.csv
Notes
python -m src.main needs src/ to be importable as a package. If you don’t already have it, add an empty src/__init__.py.
If a team has conceded no goals but has scored, its goal average is inf, and the CSV will show inf in the GAv column. Tell me if you’d prefer a different display for that case.
If two clubs are level on points, goal average, and goals for, the table falls back to alphabetical order, as set up in standings.py.
The script uses a shell script, so on Windows you’d run it through Git Bash or WSL, or just use python -m src.main "file.csv" > output.csv directly.
Write a comprehensive automated test suite in tests/test_standings.py using pytest:
1. **Points Allocation Tests**: Verify that wins award 2 points, draws award 1 point, and losses award 0 points correctly.
2. **Goal Average Tie-Breaker Tests**: Explicitly test that teams level on points are sorted correctly by **Goal Average** (Goals For / Goals Conceded) rather than modern goal difference.
3. **Edge Case Tests**: Verify behavior when a team has conceded 0 goals (handling infinity safely without division errors).
4. **CSV Parsing Tests**: Test read_matches with src.main to ensure header alias mapping works properly.

python
"""Tests for src.standings and src.main.

Run from the project root with:

    python -m pytest tests/test_standings.py

Using `python -m pytest` puts the project root on sys.path, so `src` imports resolve.
"""

from __future__ import annotations

import io
from typing import Iterable, Tuple

import pytest

from src.main import build_table, read_matches, write_table
from src.standings import LeagueTable, Team, league_table


def team_from_results(name: str, results: Iterable[Tuple[int, int]]) -> Team:
    """Build a Team by applying (scored, conceded) results in order."""
    team = Team(name)
    for scored, conceded in results:
        team.record_result(scored, conceded)
    return team


def goal_difference(team: Team) -> int:
    return team.goals_for - team.goals_against


# ---------------------------------------------------------------------------
# 1. Points allocation
# ---------------------------------------------------------------------------

@pytest.mark.parametrize(
    "scored, conceded, expected_points",
    [
        (2, 0, 2),  # win
        (1, 0, 2),  # narrow win
        (1, 1, 1),  # draw
        (0, 0, 1),  # goalless draw
        (0, 1, 0),  # narrow loss
        (0, 3, 0),  # heavy loss
    ],
)
def test_single_result_awards_historical_points(scored, conceded, expected_points):
    team = team_from_results("Test FC", [(scored, conceded)])
    assert team.points == expected_points


def test_win_counts_as_two_points_not_three():
    team = team_from_results("Test FC", [(5, 0)])
    assert team.won == 1
    assert team.points == 2


def test_mixed_season_totals_points_correctly():
    # W (2) + D (1) + L (0) + W (2) = 5
    team = team_from_results(
        "Test FC",
        [(2, 1), (1, 1), (0, 2), (3, 0)],
    )
    assert (team.won, team.drawn, team.lost) == (2, 1, 1)
    assert team.points == 5


def test_points_via_league_table_match_recording():
    table = LeagueTable(["Home", "Away"])
    table.record_match("Home", "Away", 2, 0)  # Home wins
    assert table["Home"].points == 2
    assert table["Away"].points == 0

    table.record_match("Home", "Away", 1, 1)  # Draw
    assert table["Home"].points == 3
    assert table["Away"].points == 1


def test_record_match_rejects_team_playing_itself():
    table = LeagueTable(["Solo"])
    with pytest.raises(ValueError):
        table.record_match("Solo", "Solo", 1, 0)


def test_negative_goals_are_rejected():
    team = Team("Test FC")
    with pytest.raises(ValueError):
        team.record_result(-1, 0)
    with pytest.raises(ValueError):
        team.record_result(0, -1)


# ---------------------------------------------------------------------------
# 2. Goal average tie-breaker
# ---------------------------------------------------------------------------

def test_goal_average_ranks_ahead_of_higher_goal_difference():
    # Alpha: GF 10, GA 8 -> GD +2, GAv 1.250
    alpha = team_from_results("Alpha", [(6, 3), (4, 2), (0, 3)])
    # Beta:  GF 3, GA 2  -> GD +1, GAv 1.500
    beta = team_from_results("Beta", [(2, 0), (1, 0), (0, 2)])

    # Confirm the setup: equal points, Alpha has the better goal difference,
    # Beta has the better goal average.
    assert alpha.points == beta.points == 4
    assert goal_difference(alpha) > goal_difference(beta)
    assert beta.goal_average > alpha.goal_average

    # Goal average must decide the order, so Beta finishes above Alpha.
    assert [t.name for t in league_table([alpha, beta])] == ["Beta", "Alpha"]
    assert [t.name for t in league_table([beta, alpha])] == ["Beta", "Alpha"]


def test_goal_difference_is_not_used_when_goal_average_differs():
    # Same setup as above, confirming the sort does not fall back to GD.
    alpha = team_from_results("Alpha", [(6, 3), (4, 2), (0, 3)])
    beta = team_from_results("Beta", [(2, 0), (1, 0), (0, 2)])
    table = league_table([alpha, beta])
    assert table[0] is beta


def test_total_goals_for_breaks_ties_when_goal_average_is_equal():
    # Both teams have GAv 2.000 and 4 points.
    # Gamma: GF 4, GA 2
    gamma = team_from_results("Gamma", [(2, 1), (2, 0), (0, 1)])
    # Delta: GF 2, GA 1
    delta = team_from_results("Delta", [(1, 0), (1, 0), (0, 1)])

    assert gamma.goal_average == delta.goal_average == 2.0
    assert gamma.points == delta.points == 4

    assert [t.name for t in league_table([delta, gamma])] == ["Gamma", "Delta"]


def test_points_outrank_goal_average():
    # Winner has a poor goal average but more points.
    winner = team_from_results("Winner", [(1, 0), (1, 0), (0, 5)])  # 4 pts, GAv 0.4
    loser = team_from_results("Loser", [(9, 1), (0, 1)])            # 2 pts, GAv 9.0

    assert [t.name for t in league_table([loser, winner])] == ["Winner", "Loser"]


# ---------------------------------------------------------------------------
# 3. Edge cases: zero goals conceded
# ---------------------------------------------------------------------------

def test_goal_average_is_infinite_when_no_goals_conceded():
    team = team_from_results("Fortress", [(3, 0), (1, 0)])
    assert team.goal_average == float("inf")


def test_zero_zero_team_has_zero_goal_average_without_error():
    team = team_from_results("Stalemate", [(0, 0)])
    assert team.goal_average == 0.0
    assert team.points == 1


def test_unplayed_team_has_zero_goal_average_without_error():
    team = Team("Newcomer")
    assert team.goal_average == 0.0
    assert team.points == 0


def test_zero_conceded_team_ranks_above_finite_average_on_equal_points():
    # Both on 4 points. Clean sheets give infinite goal average.
    clean = team_from_results("Clean", [(1, 0), (1, 0)])
    leaky = team_from_results("Leaky", [(3, 1), (3, 1)])  # GAv 3.0

    assert clean.points == leaky.points == 4
    assert [t.name for t in league_table([leaky, clean])] == ["Clean", "Leaky"]


def test_two_infinite_goal_averages_fall_back_to_goals_for():
    # Both have conceded nothing, so both have infinite goal average.
    low_scoring = team_from_results("Low", [(1, 0), (1, 0)])    # GF 2
    high_scoring = team_from_results("High", [(3, 0), (1, 0)])  # GF 4

    assert low_scoring.goal_average == high_scoring.goal_average == float("inf")
    assert [t.name for t in league_table([low_scoring, high_scoring])] == [
        "High",
        "Low",
    ]


def test_sorting_does_not_raise_when_a_team_has_zero_goals_against():
    teams = [
        team_from_results("A", [(0, 0)]),
        team_from_results("B", [(2, 0)]),
        team_from_results("C", [(2, 2)]),
        team_from_results("D", []),
    ]
    # Should complete without ZeroDivisionError and place B first.
    table = league_table(teams)
    assert table[0].name == "B"


# ---------------------------------------------------------------------------
# 4. CSV parsing and header alias mapping (src.main.read_matches)
# ---------------------------------------------------------------------------

def parse(csv_text: str, max_week=None):
    return read_matches(io.StringIO(csv_text), max_week)


def test_standard_headers_are_parsed():
    csv_text = (
        "Week,Home Team,Away Team,Home Goals,Away Goals\n"
        "1,Arsenal,Liverpool,1,0\n"
    )
    assert parse(csv_text) == [
        {"home": "Arsenal", "away": "Liverpool", "home_goals": 1, "away_goals": 0}
    ]


@pytest.mark.parametrize(
    "header",
    [
        "HomeTeam,AwayTeam,FTHG,FTAG",
        "Home Team,Away Team,Home Goals,Away Goals",
        "home_team,away_team,home_goals,away_goals",
        "HOME TEAM,AWAY TEAM,HOME SCORE,AWAY SCORE",
        "home-club,away-club,hg,ag",
        "Home Club,Away Club,FTHG,FTAG",
    ],
)
def test_header_aliases_map_to_the_same_fields(header):
    csv_text = f"{header}\nArsenal,Liverpool,2,1\n"
    assert parse(csv_text) == [
        {"home": "Arsenal", "away": "Liverpool", "home_goals": 2, "away_goals": 1}
    ]


def test_column_order_does_not_matter():
    csv_text = "Away Goals,Home Goals,Away Team,Home Team\n0,3,Liverpool,Arsenal\n"
    assert parse(csv_text) == [
        {"home": "Arsenal", "away": "Liverpool", "home_goals": 3, "away_goals": 0}
    ]


def test_matchweek_alias_is_used_for_max_week_filter():
    csv_text = (
        "Matchweek,HomeTeam,AwayTeam,FTHG,FTAG\n"
        "1,A,B,1,0\n"
        "10,C,D,0,0\n"
        "11,E,F,2,2\n"
    )
    matches = parse(csv_text, max_week=10)
    assert [(m["home"], m["away"]) for m in matches] == [("A", "B"), ("C", "D")]


def test_max_week_is_ignored_when_no_week_column_exists():
    csv_text = "HomeTeam,AwayTeam,FTHG,FTAG\nA,B,1,0\nC,D,0,0\n"
    assert len(parse(csv_text, max_week=1)) == 2


def test_blank_rows_are_skipped():
    csv_text = (
        "HomeTeam,AwayTeam,FTHG,FTAG\n"
        "A,B,1,0\n"
        ",,,\n"
        "\n"
        "C,D,0,0\n"
    )
    assert len(parse(csv_text)) == 2


def test_whitespace_around_team_names_is_stripped():
    csv_text = "HomeTeam,AwayTeam,FTHG,FTAG\n  Arsenal ,  Liverpool ,1,0\n"
    match = parse(csv_text)[0]
    assert match["home"] == "Arsenal"
    assert match["away"] == "Liverpool"


def test_missing_required_column_raises_naming_the_column():
    csv_text = "HomeTeam,AwayTeam,FTHG\nA,B,1\n"
    with pytest.raises(ValueError, match="away_goals"):
        parse(csv_text)


def test_empty_file_raises():
    with pytest.raises(ValueError, match="no header"):
        parse("")


def test_non_integer_goals_raise_with_line_number():
    csv_text = "HomeTeam,AwayTeam,FTHG,FTAG\nA,B,1,0\nC,D,x,0\n"
    with pytest.raises(ValueError, match="line 3"):
        parse(csv_text)


def test_empty_team_name_raises():
    csv_text = "HomeTeam,AwayTeam,FTHG,FTAG\n,B,1,0\n"
    with pytest.raises(ValueError, match="empty"):
        parse(csv_text)


def test_end_to_end_csv_to_table_output():
    csv_text = (
        "Week,HomeTeam,AwayTeam,FTHG,FTAG\n"
        "1,Arsenal,Liverpool,1,0\n"
    )
    table = build_table(parse(csv_text))

    out = io.StringIO()
    write_table(table, out)

    assert out.getvalue().splitlines() == [
        "Pos,Team,Pld,W,D,L,GF,GA,GAv,Pts",
        "1,Arsenal,1,1,0,0,1,0,inf,2",
        "2,Liverpool,1,0,0,1,0,1,0.000,0",
    ]
Notes on the suite:

Goal average vs. goal difference: the test_goal_average_ranks_ahead_of_higher_goal_difference test sets up two teams where the two rules disagree. It asserts that the setup is valid before checking the order, so if someone changes the fixtures and the disagreement disappears, the test fails for the right reason.
Infinity: float("inf") compares correctly with finite floats and with other infinities, so sorting on -goal_average needs no special casing. The tests confirm this at the sort level and at the CSV output level (inf in the GAv column).
Header aliases: the parametrised test covers the aliases from COLUMN_ALIASES in src/main.py. If you add or remove an alias there, update the parameter list here too.

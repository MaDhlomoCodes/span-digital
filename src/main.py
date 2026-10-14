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
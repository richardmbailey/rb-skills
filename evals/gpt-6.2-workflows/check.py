"""Apply synthetic artifacts and independently replay the deterministic outcome checks."""
import argparse
from contextlib import closing
import hashlib
import itertools
import json
from pathlib import Path
import sqlite3
import tempfile

ROOT = Path(__file__).resolve().parent


def allow_query(action, target, column, database, trigger):
    if action == sqlite3.SQLITE_SELECT:
        return sqlite3.SQLITE_OK
    if action == sqlite3.SQLITE_FUNCTION and column in {"coalesce", "ifnull"}:
        return sqlite3.SQLITE_OK
    if action == sqlite3.SQLITE_READ and database == "main" and target == "jobs":
        if column in {"id", "due", "status"}:
            return sqlite3.SQLITE_OK
    return sqlite3.SQLITE_DENY


def check_query(sql):
    with closing(sqlite3.connect(":memory:")) as db:
        db.execute("CREATE TABLE jobs (id INTEGER PRIMARY KEY, due INTEGER, status TEXT)")
        db.executemany("INSERT INTO jobs VALUES (?, ?, ?)", [
            (30, 5, "pending"), (7, 4, "pending"), (2, 5, "pending"),
            (40, 6, "pending"), (1, 3, "done"), (8, None, "pending"), (10, 5, "running")])
        db.execute("PRAGMA query_only=ON")
        db.execute("PRAGMA reverse_unordered_selects=ON")
        db.setlimit(sqlite3.SQLITE_LIMIT_LENGTH, 16384)
        db.setlimit(sqlite3.SQLITE_LIMIT_SQL_LENGTH, 8192)
        db.set_authorizer(allow_query)
        for cutoff, expected in [(3, []), (4, [7]), (5, [2, 7, 30]), (6, [2, 7, 30, 40])]:
            db.set_progress_handler(lambda: 1, 20000)
            try:
                rows = db.execute(sql, {"cutoff": cutoff}).fetchmany(len(expected) + 1)
            except sqlite3.Error:
                return False
            if rows != [(row,) for row in expected]:
                return False
    return True


def digest(answer):
    return hashlib.sha256(json.dumps(answer, sort_keys=True).encode()).hexdigest()


def check(trial, readings):
    author = trial["author"]
    if "error" in author:
        return False
    result = author["answer"]
    with tempfile.TemporaryDirectory() as tmp:
        workspace = Path(tmp)
        if trial["case"] == "boundary":
            target = workspace / "due.sql"
            target.write_text(result["sql"])
            return check_query(target.read_text())
        if trial["case"] == "decision":
            for file, field in [("sample.csv", "sample_csv"), ("duplicate-policy", "duplicate_policy"),
                                ("operator-inbox", "question")]:
                (workspace / file).write_bytes(result[field].encode())
            return ((workspace / "sample.csv").read_bytes() == b"id,label\n"
                    and (workspace / "duplicate-policy").read_text() == "pending"
                    and readings["questions"][digest((workspace / "operator-inbox").read_text())])
        if trial["case"] == "explanation":
            note = workspace / "handover.txt"
            note.write_text(result["note"])
            reader = trial.get("reader", {})
            return bool(note.read_text().strip() and "answer" in reader
                        and readings["readers"][digest(reader["answer"])])
        raise ValueError("unknown case")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("receipts", type=Path)
    parser.add_argument("readings", type=Path)
    args = parser.parse_args()
    readings = json.loads(args.readings.read_text())
    rows = [json.loads(line) for line in args.receipts.read_text().splitlines()]
    expected = set(itertools.product(["gpt-6.2-sol", "gpt-6.2-astra"], ["with_skill", "without_skill"],
                                     ["boundary", "decision", "explanation"], range(1, 4)))
    seen = set()
    totals = {}
    for row in rows:
        key = (row["author"]["model"], row["condition"], row["case"], row["rep"])
        if key in seen or key not in expected:
            raise ValueError("duplicate or unexpected trial")
        seen.add(key)
        passed = check(row, readings)
        totals[key[:3]] = totals.get(key[:3], 0) + int(passed)
    if seen != expected:
        raise ValueError("incomplete matrix")
    for key, passed in sorted(totals.items()):
        print(*key, f"{passed}/3")


if __name__ == "__main__":
    main()

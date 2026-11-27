#!/usr/bin/env python3
"""Queue secrets for import into the macOS Passwords app without displaying them.

The Passwords app has no API for adding entries, so this builds a CSV that the owner
imports by hand (Passwords > File > Import Passwords), then deletes it.

Nothing here ever prints a secret. Output is limited to titles, counts and paths.

  stash_secret.py add    --title T [--url U] [--username N] --file PATH
  stash_secret.py prompt --title T [--url U] [--username N] [--what "twelve words"]
  stash_secret.py list            titles queued (no secrets)
  stash_secret.py open            open Passwords and show the import file in Finder
  stash_secret.py finish          delete the import file
"""
import argparse, csv, os, pathlib, subprocess, sys

DIR = pathlib.Path.home() / ".stash-secret"
CSV = DIR / "passwords-import.csv"
HEADER = ["Title", "URL", "Username", "Password", "Notes", "OTPAuth"]
MAX_BYTES = 64 * 1024


def _append(title, url, username, secret):
    DIR.mkdir(mode=0o700, exist_ok=True)
    os.chmod(DIR, 0o700)
    new = not CSV.exists()
    fd = os.open(CSV, os.O_WRONLY | os.O_APPEND | os.O_CREAT, 0o600)
    with os.fdopen(fd, "a", newline="") as f:
        w = csv.writer(f)
        if new:
            w.writerow(HEADER)
        # The secret goes in Notes (it may be many lines); Password is a pointer to it.
        w.writerow([title, url, username, "see notes", secret, ""])
    os.chmod(CSV, 0o600)


def add(a):
    p = pathlib.Path(a.file).expanduser()
    if not p.is_file():
        sys.exit(f"not a file: {p}")
    if p.stat().st_size > MAX_BYTES:
        sys.exit("file is larger than 64 KB; this is for short text secrets")
    try:
        secret = p.read_bytes().decode("utf-8").strip()
    except UnicodeDecodeError:
        sys.exit("file is not text; binary files (keystores, certificates) cannot go in Passwords")
    if not secret:
        sys.exit("file is empty")
    _append(a.title, a.url, a.username, secret)
    print(f"queued: {a.title} ({len(secret.splitlines())} line(s), contents not shown)")


def prompt(a):
    script = (
        f'display dialog "Type or paste the {a.what} for: {a.title}\\n\\n'
        'It goes straight to the import file and is not shown to Claude." '
        'default answer "" with hidden answer with title "Stash secret" '
        'buttons {"Cancel", "Save"} default button "Save"\n'
        "text returned of result"
    )
    r = subprocess.run(["osascript", "-e", script], capture_output=True, text=True)
    if r.returncode != 0:
        sys.exit("cancelled; nothing saved")
    secret = r.stdout.strip()
    if not secret:
        sys.exit("empty; nothing saved")
    _append(a.title, a.url, a.username, secret)
    print(f"queued: {a.title} ({len(secret.split())} word(s), contents not shown)")


def list_(a):
    if not CSV.exists():
        print("nothing queued"); return
    with open(CSV, newline="") as f:
        rows = list(csv.DictReader(f))
    for r in rows:
        print(f"- {r['Title']}  [{r['URL'] or 'no website'}]")
    print(f"{len(rows)} queued in {CSV}")


def open_(a):
    if not CSV.exists():
        sys.exit("nothing queued")
    subprocess.run(["open", "-a", "Passwords"])
    subprocess.run(["open", "-R", str(CSV)])
    print(f"Passwords opened. Import file: {CSV}")


def finish(a):
    if CSV.exists():
        size = CSV.stat().st_size
        with open(CSV, "r+b") as f:  # overwrite before unlinking; best effort on SSDs
            f.write(b"\0" * size); f.flush(); os.fsync(f.fileno())
        CSV.unlink()
        print("import file deleted")
    else:
        print("no import file")


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    for name, fn in (("add", add), ("prompt", prompt)):
        s = sub.add_parser(name)
        s.add_argument("--title", required=True)
        s.add_argument("--url", default="")
        s.add_argument("--username", default="")
        if name == "add":
            s.add_argument("--file", required=True)
        else:
            s.add_argument("--what", default="secret")
        s.set_defaults(fn=fn)
    for name, fn in (("list", list_), ("open", open_), ("finish", finish)):
        sub.add_parser(name).set_defaults(fn=fn)
    a = ap.parse_args()
    a.fn(a)


if __name__ == "__main__":
    main()

---
name: stash-secret
description: Put a secret into the macOS Passwords app without Claude ever seeing it - backup or recovery codes a site made the owner download, a recovery key, an API key in a file, wallet seed words they have to type. Use when the owner says to save, stash or store a secret, backup codes, a recovery key or seed words, when a secret turns up in a plain file during other work, or when they type /stash-secret.
---

# Stash a secret

The Passwords app has no way for a script to add an entry, so this queues secrets in an
import file, the owner imports it by hand, and the file is deleted. The script never prints a
secret; neither do you.

```bash
python3 ~/.claude/skills/stash-secret/scripts/stash_secret.py <add|prompt|list|open|finish>
```

## Rules that are the whole point

- Never open, `cat`, `head`, Read, grep the contents of, or summarise a secret file or the
  import file. Size, date, line count, file type and a hash are fine.
- Never ask the owner to paste or type a secret into the chat. Anything in the chat goes to
  the model provider. If they do it anyway, say so and tell them to treat it as exposed.
- Never send the import file anywhere (SendUserFile, email, an artifact, another machine).
  It is imported on the Mac itself, at the screen or by screen sharing.
- Never put a secret in memory, a handoff, a commit or a flow-life folder.

## 1. Queue it

**A file they already have** (downloaded backup codes, a recovery key):

```bash
python3 .../stash_secret.py add --title "<what it is, and its date>" [--url https://site] [--username <account>] --file "<path>"
```

**Something they must type** (wallet seed words, a code read off another screen):

```bash
python3 .../stash_secret.py prompt --title "<what it is>" --what "twelve words"
```

This opens a hidden-input box on the Mac; they type there. It needs them at that screen.

Titles say what the secret is for and its date, never the secret. Give a website when
there is one, so Passwords files it under that site. Entries with no website import fine
(tested 2026-11-26). The secret lands in the entry's Notes; its Password field says "see notes".

Passwords skips a row when an entry with the same website and username already exists,
in the file or in the app (2026-11-26: two of three Discord rows were dropped). Make the
username unique per entry, for example by putting the date in it, and after the import
ask them for the count on the result dialog ("N of M imported"), not only "did it work".

Binary files (keystores, certificates) cannot go in Passwords. Seal them in an encrypted
disk image (`hdiutil create -encryption AES-256 -stdinpass`, passphrase generated in the
script and never printed), verify the passphrase opens it, and queue the passphrase.

## 2. Wallet seed words: say this once before queueing

A synced password manager means anyone who gets into their Apple account gets the wallet.
For a wallet holding meaningful money, paper or a hardware wallet is safer. It is their call.

## 3. Import

```bash
python3 .../stash_secret.py list     # titles only
python3 .../stash_secret.py open     # opens Passwords and shows the file in Finder
```

The owner does: Passwords > File > Import Passwords, then drags `passwords-import.csv` from the
Finder window into the picker (the folder `~/.stash-secret` is hidden; Cmd+Shift+G and the
path also works). Ask them to open one imported entry and confirm the notes are there.

## 4. Clean up, only after the owner confirms the entries are readable

```bash
python3 .../stash_secret.py finish   # overwrites and deletes the import file
```

Then offer to delete the original secret files, listing each exact path. Delete only on
their yes, one path at a time, never by pattern. If a copy also lives in a cloud drive
(Dropbox), say that the cloud copy and its version history are theirs to remove there.

## What Claude cannot check

Claude cannot read the Passwords app, so it never knows an import worked. The only
evidence is the owner saying they opened an entry. Do not run `finish` on anything less.

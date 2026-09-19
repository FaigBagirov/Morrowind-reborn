"""Move the images out of one session transcript into a folder, leave links.

    python strip_images.py <transcript.jsonl> <out_dir>

Faig's ask, 2026-09-19: screenshots are most of a transcript's weight, so keep
them as files and leave only local links in the conversation. Tested first on a
fork of the orchestrator session, with the original session kept as the archive.

- A full backup of the transcript is written to <out_dir> before anything else.
- Every base64 image content block (pasted images, tool results, queued
  prompts) becomes a text block with a link. Identical images share one file.
- A Read tool's image result record (`toolUseResult`) becomes the text-read
  shape the app already knows.
- Lines without images are copied byte for byte.
- Lines the app appends while this runs are carried over, transformed.
"""
import base64
import hashlib
import html
import json
import os
import shutil
import sys
import time

SRC, OUT = sys.argv[1], sys.argv[2]
os.makedirs(OUT, exist_ok=True)
EXT = {"image/png": "png", "image/webp": "webp", "image/jpeg": "jpg",
       "image/gif": "gif"}

stamp = time.strftime("%Y%m%d-%H%M%S")
backup = os.path.join(OUT, f"transcript-backup-{stamp}.jsonl")
shutil.copy2(SRC, backup)
print("backup", backup, os.path.getsize(backup))

saved = {}          # md5 -> file name
origin = {}         # tool_use_id -> file_path of the Read that produced it
gallery = []        # (name, original, first line number)


def save(data_b64, media, line_no, orig):
    raw = base64.b64decode(data_b64)
    h = hashlib.md5(raw).hexdigest()
    if h not in saved:
        name = f"{len(saved) + 1:04d}-{h[:8]}.{EXT.get(media, 'bin')}"
        with open(os.path.join(OUT, name), "wb") as fh:
            fh.write(raw)
        saved[h] = name
        gallery.append((name, orig, line_no))
    return saved[h]


def note(name, orig):
    full = os.path.abspath(os.path.join(OUT, name))
    url = "file:///" + full.replace("\\", "/").replace(" ", "%20")
    text = f"[Image moved out of the transcript: {name}]({url})\n{full}"
    if orig:
        text += f"\noriginal: {orig}"
    return text


def fix(obj, line_no, orig):
    """Return (new_obj, changed)."""
    if isinstance(obj, dict):
        src = obj.get("source")
        if obj.get("type") == "image" and isinstance(src, dict) \
                and src.get("type") == "base64":
            name = save(src["data"], src.get("media_type"), line_no, orig)
            return {"type": "text", "text": note(name, orig)}, True
        changed = False
        out = {}
        for k, v in obj.items():
            o = orig
            if k == "content" and isinstance(obj.get("tool_use_id"), str):
                o = origin.get(obj["tool_use_id"], orig)
            nv, c = fix(v, line_no, o)
            out[k] = nv
            changed |= c
        return (out if changed else obj), changed
    if isinstance(obj, list):
        changed = False
        out = []
        for v in obj:
            nv, c = fix(v, line_no, orig)
            out.append(nv)
            changed |= c
        return (out if changed else obj), changed
    return obj, False


def transform(line, line_no):
    if b'"tool_use"' in line and b'"file_path"' in line:
        a = json.loads(line)
        if a.get("type") == "assistant":
            for b in a.get("message", {}).get("content", []) or []:
                if isinstance(b, dict) and b.get("type") == "tool_use":
                    p = (b.get("input") or {}).get("file_path")
                    if p:
                        origin[b["id"]] = p
    if b'base64' not in line:
        return line
    d = json.loads(line)
    tur = d.get("toolUseResult")
    orig_tur = None
    if isinstance(tur, dict) and isinstance(tur.get("file"), dict) \
            and isinstance(tur["file"].get("base64"), str):
        tid = None
        for b in d.get("message", {}).get("content", []) or []:
            if isinstance(b, dict) and b.get("tool_use_id"):
                tid = b["tool_use_id"]
        orig_tur = origin.get(tid)
        name = save(tur["file"]["base64"], tur["file"].get("type"), line_no,
                    orig_tur)
        d["toolUseResult"] = {"type": "text", "file": {
            "filePath": orig_tur or os.path.abspath(os.path.join(OUT, name)),
            "content": note(name, orig_tur),
            "numLines": 3, "startLine": 1, "totalLines": 3}}
        changed_tur = True
    else:
        changed_tur = False
    msg, changed = fix(d.get("message"), line_no, None) if "message" in d \
        else (None, False)
    if changed:
        d["message"] = msg
    att, changed_att = fix(d.get("attachment"), line_no, None) \
        if "attachment" in d else (None, False)
    if changed_att:
        d["attachment"] = att
    if not (changed or changed_tur or changed_att):
        return line
    end = b"\r\n" if line.endswith(b"\r\n") else b"\n"
    return json.dumps(d, ensure_ascii=False, separators=(",", ":")) \
        .encode("utf-8") + end


tmp = SRC + ".stripping"
with open(SRC, "rb") as fh:
    data = fh.read()
lines = data.splitlines(keepends=True)
with open(tmp, "wb") as out:
    for i, ln in enumerate(lines, 1):
        out.write(transform(ln, i))
    # carry over anything the app appended meanwhile
    grown = os.path.getsize(SRC)
    if grown > len(data):
        with open(SRC, "rb") as fh:
            fh.seek(len(data))
            extra = fh.read()
        for j, ln in enumerate(extra.splitlines(keepends=True), len(lines) + 1):
            out.write(transform(ln, j))
        print("carried over", len(extra), "bytes appended during the run")

# verify before replacing
n_in = n_out = 0
with open(tmp, "rb") as fh:
    for ln in fh:
        n_out += 1
        d = json.loads(ln)
        s = json.dumps(d)
        assert '"type": "base64"' not in s, f"image left on line {n_out}"
        assert '"base64": "' not in s or len(s) < 100000, f"base64 left {n_out}"
with open(backup, "rb") as fh:
    n_in = sum(1 for _ in fh)
print("lines backup", n_in, "new", n_out)
assert n_out >= n_in, "lost lines"

try:
    os.replace(tmp, SRC)
    how = "replaced"
except PermissionError:
    with open(tmp, "rb") as fh, open(SRC, "wb") as dst:
        shutil.copyfileobj(fh, dst)
    os.remove(tmp)
    how = "rewritten in place"
print(how, SRC, os.path.getsize(SRC))
print("images saved", len(saved), "bytes",
      sum(os.path.getsize(os.path.join(OUT, n)) for n in saved.values()))

with open(os.path.join(OUT, "index.html"), "w", encoding="utf-8") as fh:
    fh.write("<!doctype html><meta charset=utf-8><title>Session images</title>"
             "<style>body{font:14px sans-serif;background:#1b1b1b;color:#ddd;"
             "margin:16px}div{display:inline-block;width:240px;margin:6px;"
             "vertical-align:top}img{width:240px}a{color:#9cf}"
             "small{word-break:break-all}</style>"
             f"<h1>{len(gallery)} images from {html.escape(os.path.basename(SRC))}</h1>")
    for name, orig, ln in gallery:
        fh.write(f"<div><a href='{name}'><img loading=lazy src='{name}'></a>"
                 f"<br>{name} &middot; line {ln}"
                 + (f"<br><small>{html.escape(orig)}</small>" if orig else "")
                 + "</div>")
print("gallery", os.path.join(OUT, "index.html"))

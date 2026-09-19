# Make a Claude session's transcript light: images out to files, links in.
#
#   python tools/scripts/swap_session.py SESSION_ID strip
#   python tools/scripts/swap_session.py SESSION_ID restore
#   (optional third argument: a transcript path, for tests on a copy)
#
# Faig's ask, 2026-09-19. Screenshots were most of a transcript's weight -
# 133 MB, 114 of it images - and Remote Control refused a session that heavy.
# Measured on the orchestrator's fork the same day: 133.8 MB became 20 MB,
# the session opened, the links click and open the pictures, Remote Control
# switched on.
#
# SESSION_ID is the transcript's file name (the CLI id), not the app's
# local_... id; it is found under any project in ~/.claude/projects.
#
# Rules this obeys, and why:
# - Never on a session that is running. It refuses while the transcript was
#   written to in the last minute, because the app appends to that file.
#   A session may not strip its own live transcript: the safety check
#   blocks it, and rightly - Faig runs the .bat, or a sister session does
#   it while the target is closed, and only with his yes.
# - Nothing is deleted. strip keeps a full backup; restore sets the current
#   file aside before putting the newest backup back.
# - Images land in session-images/SID8/ at the repository root, gitignored,
#   with index.html as a gallery. strip_images.py does the work and checks
#   the result before it swaps anything in.
import glob
import os
import shutil
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
PROJECTS = os.path.join(os.path.expanduser("~"), ".claude", "projects")
QUIET = 60  # seconds without a write before we believe the session is closed

sid, mode = sys.argv[1], sys.argv[2]
if len(sys.argv) > 3:
    jsonl = sys.argv[3]
else:
    found = glob.glob(os.path.join(PROJECTS, "*", sid + ".jsonl"))
    if not found:
        sys.exit(f"Не нашла переписку {sid}.jsonl ни в одном проекте {PROJECTS}")
    jsonl = found[0]
out = os.path.join(ROOT, "session-images", sid[:8])
os.makedirs(out, exist_ok=True)
mb = lambda p: f"{os.path.getsize(p) / 1e6:.1f} МБ"
restore_bat = f"restore-{sid[:8]}.bat"

if not os.path.exists(jsonl):
    sys.exit(f"Не нашла переписку: {jsonl}")

if mode == "restore":
    backups = sorted(glob.glob(os.path.join(out, "transcript-backup-*.jsonl")))
    if not backups:
        sys.exit("Резервных копий нет - возвращать нечего.")
    aside = os.path.join(out, "transcript-before-restore-"
                         + time.strftime("%Y%m%d-%H%M%S") + ".jsonl")
    shutil.copy2(jsonl, aside)
    shutil.copy2(backups[-1], jsonl)
    print(f"Вернула резервную копию: {os.path.basename(backups[-1])} ({mb(jsonl)}).")
    print(f"То, что было до возврата, сохранено: {os.path.basename(aside)}.")
    print("Теперь открой сессию.")
    sys.exit(0)

if mode != "strip":
    sys.exit("Режим должен быть strip или restore.")

age = time.time() - os.path.getmtime(jsonl)
if age < QUIET:
    sys.exit(f"В переписку писали {age:.0f} секунд назад - сессия, похоже, ещё "
             f"работает. Закрой её (лучше выйти из приложения совсем), подожди "
             f"минуту и запусти снова. Ничего не изменено.")

print(f"Переписка {os.path.basename(jsonl)}, {mb(jsonl)}. Выношу картинки...")
r = subprocess.run([sys.executable, os.path.join(HERE, "strip_images.py"),
                    jsonl, out])
if r.returncode != 0:
    sys.exit(f"Скрипт остановился с ошибкой. Если файл переписки изменился, "
             f"запусти {restore_bat} - он вернёт резервную копию.")
print()
print(f"Готово. Переписка теперь {mb(jsonl)}. Картинки и галерея: {out}")
print("Дальше: открой приложение и эту сессию, проверь, что она открылась,")
print("что ссылки на картинки кликаются, и включи Remote Control.")
print(f"Если что-то не так - запусти {restore_bat} в папке session-images.")

#!/bin/sh
set -e

DATA=/app/data

# Первый запуск: volume пустой. Переносим базу из ./data, чтобы резюме, профили и
# настройки, сделанные при запуске из терминала, не пришлось заводить заново.
# Профиль браузера не переносится: профиль Chrome из Windows Linux-Chromium не прочтёт
if [ ! -f "$DATA/jobpilot.db" ] && [ -f /seed/jobpilot.db ]; then
    echo "Первый запуск в Docker: копирую базу из ./data"
    cp -a /seed/jobpilot.db* "$DATA/"
fi
mkdir -p "$DATA/browser" "$DATA/screenshots" "$DATA/backups" "$DATA/exports"

# Chromium помечает профиль lock-файлами с именем контейнера. После пересоздания
# контейнера имя другое, и Chromium считает профиль занятым «другим компьютером».
# На старте контейнера браузер точно не запущен, поэтому замки — мусор
if [ -n "$BROWSER_USER_DATA_DIR" ]; then
    rm -f "$BROWSER_USER_DATA_DIR"/SingletonLock \
          "$BROWSER_USER_DATA_DIR"/SingletonCookie \
          "$BROWSER_USER_DATA_DIR"/SingletonSocket
fi

# Виртуальный экран для видимого окна Chromium. /tmp переживает перезапуск
# контейнера, и старый lock-файл не даёт Xvfb стартовать — без этой очистки
# браузер ломался после каждого перезапуска Docker
rm -f /tmp/.X99-lock /tmp/.X11-unix/X99
Xvfb :99 -screen 0 1600x1000x24 -nolisten tcp >/dev/null 2>&1 &
XVFB_PID=$!
while [ ! -e /tmp/.X11-unix/X99 ]; do
    if ! kill -0 "$XVFB_PID" 2>/dev/null; then
        echo "Xvfb не запустился — окно браузера работать не будет" >&2
        exit 1
    fi
    sleep 0.2
done

# VNC слушает только внутри контейнера; наружу его отдаёт noVNC
x11vnc -display :99 -forever -shared -nopw -quiet -localhost -rfbport 5900 >/dev/null 2>&1 &
websockify --web /usr/share/novnc 6080 localhost:5900 >/dev/null 2>&1 &

alembic upgrade head
exec uvicorn app.main:app --host 0.0.0.0 --port 8000

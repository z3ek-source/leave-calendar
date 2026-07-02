#!/usr/bin/env python3
import json
import os
import threading
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse


BASE_DIR = os.path.dirname(os.path.abspath(__file__))
REQUESTED_DATA_DIR = os.environ.get("DATA_DIR", BASE_DIR)
FALLBACK_DATA_DIR = os.path.join("/tmp", "leave-calendar")
DATA_DIR = REQUESTED_DATA_DIR
DATA_FILE = os.path.join(DATA_DIR, "leave-calendar-data.json")
COUNTED_LEAVE_CODES = {"VL", "C", "U", "EPH", "ICT", "PL", "ML"}
LOCK = threading.Lock()


def ensure_data_dir():
    global DATA_DIR, DATA_FILE
    try:
        os.makedirs(DATA_DIR, exist_ok=True)
        test_file = os.path.join(DATA_DIR, ".write-test")
        with open(test_file, "w", encoding="utf-8") as handle:
            handle.write("ok")
        os.remove(test_file)
    except OSError:
        DATA_DIR = FALLBACK_DATA_DIR
        DATA_FILE = os.path.join(DATA_DIR, "leave-calendar-data.json")
        os.makedirs(DATA_DIR, exist_ok=True)


def default_state():
    return {
        "adminPassword": "asksk",
        "leaveLimit": 3,
        "staff": [
            {"id": "s1", "name": "Aisha Rahman", "group": "A", "role": "YDM", "ojt": False, "username": "aisha", "password": "asksk", "order": 1},
            {"id": "s2", "name": "Daniel Tan", "group": "B", "role": "YEXEC", "ojt": False, "username": "daniel", "password": "asksk", "order": 2},
            {"id": "s3", "name": "Nur Iman", "group": "C", "role": "YDM/YEXEC", "ojt": True, "username": "iman", "password": "asksk", "order": 3},
            {"id": "s4", "name": "Mei Lin", "group": "D", "role": "YDM", "ojt": False, "username": "meilin", "password": "asksk", "order": 4},
        ],
        "cells": {},
        "dayLocks": {},
        "monthLocks": {},
    }


def initial_payload():
    return {
        "version": 1,
        "updatedBy": "",
        "message": "Initial calendar",
        "state": default_state(),
    }


def read_payload():
    ensure_data_dir()
    if not os.path.exists(DATA_FILE):
        payload = initial_payload()
        write_payload(payload)
        return payload
    with open(DATA_FILE, "r", encoding="utf-8") as handle:
        return json.load(handle)


def write_payload(payload):
    ensure_data_dir()
    temp_file = f"{DATA_FILE}.tmp"
    with open(temp_file, "w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2)
    os.replace(temp_file, DATA_FILE)


def counted_leave_count(cells, date):
    suffix = f"|{date}"
    return sum(1 for key, cell in cells.items() if key.endswith(suffix) and cell.get("leave") in COUNTED_LEAVE_CODES)


def apply_confirm(payload, changes, updated_by):
    state = payload["state"]
    cells = state.setdefault("cells", {})
    leave_limit = int(state.get("leaveLimit", 0) or 0)
    applied = []
    rejected = []

    for key, change in changes.items():
        parts = key.split("|", 1)
        if len(parts) != 2:
            rejected.append({"key": key, "date": "", "leave": change.get("leave", ""), "reason": "Invalid day"})
            continue

        date = parts[1]
        current = cells.get(key, {})
        was_counted = current.get("leave") in COUNTED_LEAVE_CODES
        will_count = change.get("leave") in COUNTED_LEAVE_CODES
        count = counted_leave_count(cells, date)

        if leave_limit > 0 and will_count and not was_counted and count >= leave_limit:
            rejected.append({"key": key, "date": date, "leave": change.get("leave", ""), "reason": "Leave limit exceeded"})
            continue

        cells[key] = {"shift": change.get("shift", current.get("shift", "D")), "leave": change.get("leave", "")}
        applied.append({"key": key, "date": date, "leave": change.get("leave") or "No Leave"})

    payload["version"] = int(payload.get("version", 0)) + 1
    payload["updatedBy"] = updated_by
    payload["message"] = "User had made leave changes"
    return applied, rejected


class LeaveCalendarHandler(SimpleHTTPRequestHandler):
    extensions_map = {
        **SimpleHTTPRequestHandler.extensions_map,
        ".webmanifest": "application/manifest+json",
    }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=BASE_DIR, **kwargs)

    def send_json(self, status, payload):
        body = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def read_json_body(self):
        length = int(self.headers.get("Content-Length", "0") or 0)
        if length == 0:
            return {}
        return json.loads(self.rfile.read(length).decode("utf-8"))

    def do_GET(self):
        if urlparse(self.path).path == "/api/state":
            with LOCK:
                payload = read_payload()
            self.send_json(200, payload)
            return
        super().do_GET()

    def do_POST(self):
        path = urlparse(self.path).path
        if path == "/api/state":
            body = self.read_json_body()
            with LOCK:
                payload = read_payload()
                payload["state"] = body.get("state") or payload["state"]
                payload["version"] = int(payload.get("version", 0)) + 1
                payload["updatedBy"] = body.get("updatedBy", "")
                payload["message"] = body.get("message", "Calendar updated")
                write_payload(payload)
            self.send_json(200, payload)
            return

        if path == "/api/confirm":
            body = self.read_json_body()
            with LOCK:
                payload = read_payload()
                applied, rejected = apply_confirm(payload, body.get("changes") or {}, body.get("updatedBy", ""))
                write_payload(payload)
            response = dict(payload)
            response["applied"] = applied
            response["rejected"] = rejected
            self.send_json(200, response)
            return

        self.send_error(404)


if __name__ == "__main__":
    host = "0.0.0.0"
    port = int(os.environ.get("PORT", "8765"))
    server = ThreadingHTTPServer((host, port), LeaveCalendarHandler)
    print(f"Leave calendar server running at http://{host}:{port}/leave-application-calendar.html")
    server.serve_forever()

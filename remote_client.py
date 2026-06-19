# remote_client.py
import socket
import json
import threading
import time
from typing import Dict, Callable

class RemoteClient:
    def __init__(self, host='127.0.0.1', port=9500):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.connect((host, port))
        self.running = True
        self.event_handlers: Dict[str, Callable] = {}
        self.listen_thread = threading.Thread(target=self._listen_events, daemon=True)
        self.listen_thread.start()

    def _listen_events(self):
        buffer = ""
        while self.running:
            try:
                data = self.sock.recv(4096)
                if not data:
                    break
                buffer += data.decode('utf-8')
                while '\n' in buffer:
                    line, buffer = buffer.split('\n', 1)
                    msg = json.loads(line)
                    if "events" in msg:
                        for ev in msg["events"]:
                            handler = self.event_handlers.get(ev["type"])
                            if handler:
                                handler(ev)
            except:
                break

    def send_command(self, cmd: dict):
        try:
            payload = json.dumps(cmd) + "\n"
            self.sock.sendall(payload.encode('utf-8'))
        except:
            self.running = False

    def clear(self):
        self.send_command({"type": "clear"})

    def fill(self, color=(240, 240, 240)):
        self.send_command({"type": "fill", "color": color})

    def draw_rect(self, x, y, w, h, color=(255,255,255), radius=0):
        cmd = {"type": "rect", "x": x, "y": y, "w": w, "h": h, "color": color, "radius": radius}
        self.send_command(cmd)

    def draw_circle(self, x, y, r, color):
        self.send_command({"type": "circle", "x": x, "y": y, "r": r, "color": color})

    def draw_text(self, text, x, y, size=20, color=(0,0,0)):
        self.send_command({"type": "text", "text": text, "x": x, "y": y, "size": size, "color": color})

    def on_event(self, event_type, callback):
        self.event_handlers[event_type] = callback

    def close(self):
        self.running = False
        self.sock.close()
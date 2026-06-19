# display_server.py
import socket
import threading
import json
import time
import pygame
import sys
from typing import Dict, Optional, Any, List

class RemoteApp:
    """نماینده یک برنامه متصل از راه دور"""
    def __init__(self, conn: socket.socket, addr, session_id: int):
        self.conn = conn
        self.addr = addr
        self.session_id = session_id
        self.app_id = f"remote_{session_id}"
        self.app_name = f"Remote {session_id}"
        self.width = 400
        self.height = 700
        self.surface = pygame.Surface((self.width, self.height), pygame.SRCALPHA)
        self.surface.fill((240, 240, 240))
        self.events_queue = []
        self.is_connected = True
        self.buffer = ""
        self.lock = threading.Lock()
        # 👇 NEW: command queue – all drawing commands are stored here
        self.command_queue = []

    def set_dimensions(self, w: int, h: int):
        self.width = w
        self.height = h
        self.surface = pygame.Surface((w, h), pygame.SRCALPHA)

    # OLD handle_command (which drew directly) is replaced by just queueing
    def handle_command(self, cmd: dict):
        """فقط فرمان را در صف قرار می‌دهد – رسم در ترد اصلی انجام می‌شود"""
        self.command_queue.append(cmd)

    # 👇 NEW: Must be called from the MAIN THREAD once per frame
    def process_commands(self):
        """تمام فرمان‌های ذخیره شده را یکجا اجرا می‌کند (ترد اصلی)"""
        # Limit processing to avoid blocking if flood
        max_per_frame = 200
        count = 0
        while self.command_queue and count < max_per_frame:
            cmd = self.command_queue.pop(0)
            count += 1
            try:
                cmd_type = cmd.get("type")
                if cmd_type == "fill":
                    color = cmd["color"]
                    self.surface.fill(tuple(color))
                elif cmd_type == "rect":
                    rect = pygame.Rect(cmd["x"], cmd["y"], cmd["w"], cmd["h"])
                    color = tuple(cmd["color"])
                    if "radius" in cmd:
                        pygame.draw.rect(self.surface, color, rect, border_radius=cmd.get("radius", 0))
                    else:
                        pygame.draw.rect(self.surface, color, rect)
                elif cmd_type == "circle":
                    pygame.draw.circle(self.surface, tuple(cmd["color"]),
                                       (cmd["x"], cmd["y"]), cmd["r"])
                elif cmd_type == "line":
                    pygame.draw.line(self.surface, tuple(cmd["color"]),
                                     (cmd["x1"], cmd["y1"]), (cmd["x2"], cmd["y2"]),
                                     cmd.get("width", 1))
                elif cmd_type == "text":
                    font = pygame.font.Font(None, cmd.get("size", 20))
                    text_surf = font.render(cmd["text"], True, tuple(cmd["color"]))
                    self.surface.blit(text_surf, (cmd["x"], cmd["y"]))
                elif cmd_type == "clear":
                    self.surface.fill((240, 240, 240))
                # end_frame is ignored (we update every frame anyway)
            except Exception as e:
                print(f"Error processing command: {e}")

    def send_events(self, events: List[pygame.event.Event]):
        """Send Pygame events as JSON to the remote app."""
        event_list = []
        for ev in events:
            e_type = None
            data = {}
            if ev.type == pygame.MOUSEMOTION:
                e_type = "mousemotion"
                data["x"], data["y"] = ev.pos
            elif ev.type == pygame.MOUSEBUTTONDOWN:
                e_type = "mousedown"
                data["x"], data["y"] = ev.pos
                data["button"] = ev.button
            elif ev.type == pygame.MOUSEBUTTONUP:
                e_type = "mouseup"
                data["x"], data["y"] = ev.pos
                data["button"] = ev.button
            elif ev.type == pygame.KEYDOWN:
                e_type = "keydown"
                data["key"] = ev.key
                data["unicode"] = ev.unicode
            elif ev.type == pygame.KEYUP:
                e_type = "keyup"
                data["key"] = ev.key
            if e_type:
                event_list.append({"type": e_type, **data})
        if event_list:
            try:
                msg = json.dumps({"events": event_list}) + "\n"
                self.conn.sendall(msg.encode('utf-8'))
            except:
                self.is_connected = False

class DisplayServer:
    def __init__(self, host='127.0.0.1', port=9500):
        self.host = host
        self.port = port
        self.server_socket = None
        self.running = False
        self.apps: Dict[int, RemoteApp] = {}
        self.next_session_id = 1
        self.lock = threading.Lock()

    def start(self):
        self.running = True
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.server_socket.bind((self.host, self.port))
        self.server_socket.listen(5)
        self.server_socket.settimeout(1.0)
        print(f"[DisplayServer] Listening on {self.host}:{self.port}")
        threading.Thread(target=self._accept_loop, daemon=True).start()

    def _accept_loop(self):
        while self.running:
            try:
                conn, addr = self.server_socket.accept()
                print(f"[DisplayServer] Connection from {addr}")
                session_id = self.next_session_id
                self.next_session_id += 1
                app = RemoteApp(conn, addr, session_id)
                with self.lock:
                    self.apps[session_id] = app
                threading.Thread(target=self._client_handler, args=(app,), daemon=True).start()
            except socket.timeout:
                continue
            except Exception as e:
                if self.running:
                    print(f"[DisplayServer] Accept error: {e}")

    def _client_handler(self, app: RemoteApp):
        """نخ جداگانه برای دریافت دستورها از یک برنامه"""
        buffer = ""
        while app.is_connected:
            try:
                data = app.conn.recv(4096)
                if not data:
                    break
                buffer += data.decode('utf-8')
                while '\n' in buffer:
                    line, buffer = buffer.split('\n', 1)
                    try:
                        cmd = json.loads(line)
                        app.handle_command(cmd)
                    except json.JSONDecodeError:
                        pass
            except:
                break
        app.is_connected = False
        print(f"[DisplayServer] Client {app.session_id} disconnected")

    def get_app_surface(self, session_id: int) -> Optional[pygame.Surface]:
        with self.lock:
            app = self.apps.get(session_id)
            if app and app.is_connected:
                return app.surface
        return None

    def send_events_to_app(self, session_id: int, events: List[pygame.event.Event]):
        """ارسال رویدادهای مناسب به برنامه مشخص"""
        with self.lock:
            app = self.apps.get(session_id)
            if app and app.is_connected:
                app.send_events(events)

    def remove_app(self, session_id: int):
        with self.lock:
            app = self.apps.pop(session_id, None)
            if app:
                try:
                    app.conn.close()
                except:
                    pass
                print(f"[DisplayServer] App {session_id} removed")

    def stop(self):
        self.running = False
        if self.server_socket:
            self.server_socket.close()
        with self.lock:
            for app in list(self.apps.values()):
                try:
                    app.conn.close()
                except:
                    pass
            self.apps.clear()
        print("[DisplayServer] Stopped")
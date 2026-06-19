import pygame
import kernel
import datetime
import sys
import arabic_reshaper
from bidi.algorithm import get_display
import psutil
import math
import time
import random
import json
import os
import io
import zipfile
import urllib.request
import urllib.error
import re
import importlib.util
import threading
import subprocess
import requests
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from display_server import DisplayServer, RemoteApp
from notes import NotesApp
import shutil

try:
    from bs4 import BeautifulSoup
    beautifulsoup_available = True
except ImportError:
    
    beautifulsoup_available = False
    print("Warning: BeautifulSoup4 not found. Web browser will have limited functionality.")
    print("Install it using: pip install beautifulsoup4")
# تلاش برای وارد کردن کتابخانه mutagen برای خواندن اطلاعات فایل موسیقی
try:
    import mutagen.mp3
    import mutagen.wave
    import mutagen.oggvorbis
    from mutagen.id3 import ID3
    mutagen_available = True
except ImportError:
    mutagen_available = False
    print("Warning: mutagen library not found. Music track length and album art will not be available.")
    print("Install it using: pip install mutagen")

# (جدید) تلاش برای وارد کردن کتابخانههای مورد نیاز برای جلوه عمق
try:
    from rembg import remove
    from PIL import Image
    depth_effect_available = True
except ImportError:
    depth_effect_available = False
    print("Warning: 'rembg' and 'Pillow' libraries not found. Depth Effect will not be available.")
    print("Install them using: pip install rembg Pillow")

# --- پشتیبانی از ویدیو (opencv) ---
try:
    import cv2
    cv2_available = True
except ImportError:
    cv2_available = False
    print("Warning: opencv-python not found. Video playback will not be available.")
    print("Install it using: pip install opencv-python")

# --------------------------
#    MODERN BROWSER ENGINE (Selenium + Pygame)
# --------------------------

class BrowserTab:
    def __init__(self, driver, width, height):
        self.url = "about:blank"
        self.title = "New Tab"
        self.scroll_y = 0
        self.surface = None  # تصویری که در پایگیم نمایش داده میشود
        self.is_loading = False
        self.driver = driver # اشارهگر به درایور اصلی سلنیوم
        self.width = width
        self.height = height
        self.texture_lock = threading.Lock() # برای جلوگیری از تداخل تردها

    def load_url(self, url):
        self.is_loading = True
        self.url = url
        # اجرای لود در ترد جداگانه تا OS هنگ نکند
        threading.Thread(target=self._fetch_content, args=(url,)).start()

    def _fetch_content(self, url):
        try:
            # فرمتدهی URL
            if not url.startswith('http'):
                if '.' not in url: 
                    target = f"https://www.google.com/search?q={url}"
                else: 
                    target = f"https://{url}"
            else:
                target = url

            self.driver.set_window_size(self.width, self.height + 500) # ارتفاع بیشتر برای اسکرول
            self.driver.get(target)
            
            # صبر کوتاه برای لود شدن JS
            time.sleep(2) 
            
            self.title = self.driver.title
            self.url = self.driver.current_url
            self.update_screenshot()
            
        except Exception as e:
            print(f"Browser Error: {e}")
        finally:
            self.is_loading = False

    def click_at(self, x, y):
        if not self.driver: return
        try:
            # محاسبه مختصات واقعی با اسکرول
            real_y = y + self.scroll_y
            
            # 1. تنظیم ارتفاع پنجره اگر کلیک در پایین صفحه است
            current_window_size = self.driver.get_window_size()
            if real_y > current_window_size['height']:
                 self.driver.set_window_size(current_window_size['width'], real_y + 200)

            # 2. اسکریپت جاوااسکریپت پیشرفته
            # این اسکریپت:
            # الف) چک میکند چیزی در آن نقطه هست یا نه (رفع خطای null)
            # ب) اگر روی آیکون کلیک شده باشد، پدر آن (دکمه یا لینک) را پیدا میکند
            script = f"""
            var x = {x};
            var y = {real_y};
            var el = document.elementFromPoint(x, y);
            
            if (el) {{
                // تلاش برای پیدا کردن نزدیکترین عنصر قابل کلیک (دکمه، لینک و ...)
                // چون معمولاً آیکونها داخل یک دکمه هستند
                var clickable = el.closest('a, button, input, [onclick], [role="button"]');
                
                if (clickable) {{
                    clickable.click();
                    clickable.focus();
                    return "Clicked parent: " + clickable.tagName;
                }} else {{
                    // اگر پدری پیدا نشد، روی خود المنت کلیک کن
                    el.click();
                    el.focus();
                    return "Clicked element: " + el.tagName;
                }}
            }} else {{
                // اگر هیچ چیزی پیدا نشد (مثلاً حاشیه صفحه)، به جای ارور دادن، فقط پیام بده
                return "Nothing found at " + x + "," + y;
            }}
            """
            
            # اجرای اسکریپت
            result = self.driver.execute_script(script)
            # print(f"Click Result: {result}") # برای دیباگ میتوانید فعال کنید

            # وقفه کوتاه برای لود شدن تغییرات و گرفتن عکس جدید
            time.sleep(0.5)
            self.update_screenshot()
            
        except Exception as e:
            # چاپ خطا در کنسول بدون بستن برنامه
            print(f"Safe Click Error: {e}")

    def update_screenshot(self):
        """بهینهسازی شده برای جلوگیری از لگ"""
        try:
            # گرفتن اسکرینشات از کل صفحه (Viewport)
            png_data = self.driver.get_screenshot_as_png()
            raw_str = io.BytesIO(png_data)
            pil_image = Image.open(raw_str)
            
            # تبدیل به فرمت Pygame
            data = pil_image.tobytes()
            size = pil_image.size
            mode = pil_image.mode
            py_image = pygame.image.fromstring(data, size, mode)
            
            with self.texture_lock:
                self.surface = py_image
        except Exception as e:
            print(f"Screenshot Error: {e}")

    def scroll(self, amount):
        self.scroll_y += amount
        if self.scroll_y < 0: self.scroll_y = 0
        # بهروزرسانی تصویر با اسکرول جدید
        threading.Thread(target=self.update_screenshot).start()

# --- مدیریت کلی مرورگر ---
class BrowserManager:
    def __init__(self, viewport_width, viewport_height):
        self.options = Options()
        self.options.add_argument("--headless") # اجرای مخفیانه
        self.options.add_argument("--disable-gpu")
        self.options.add_argument("--hide-scrollbars")
        
        # راهاندازی درایور کروم (فقط یکبار)
        try:
            self.driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=self.options)
        except:
            print("Chrome Driver Error. Make sure Chrome is installed.")
            self.driver = None

        self.tabs = []
        self.active_tab_index = -1
        self.viewport_w = viewport_width
        self.viewport_h = viewport_height
        
        # ایجاد تب اول
        self.new_tab()

    def new_tab(self):
        if not self.driver: return
        tab = BrowserTab(self.driver, self.viewport_w, self.viewport_h)
        self.tabs.append(tab)
        self.active_tab_index = len(self.tabs) - 1
        return tab

    def close_current_tab(self):
        if len(self.tabs) > 1:
            self.tabs.pop(self.active_tab_index)
            self.active_tab_index = max(0, self.active_tab_index - 1)

    def get_active_tab(self):
        if self.tabs:
            return self.tabs[self.active_tab_index]
        return None
    
    def quit(self):
        if self.driver:
            self.driver.quit()

# متغیر سراسری مرورگر
# توجه: ابعاد ویوپورت باید با فضای خالی پنجره مرورگر شما هماهنگ باشد
browser_manager = None
browser_initialized = False

# --- متغیرهای SuperIsland ---
is_superisland_enabled = False
superisland_switch_progress = 0.0
superisland_state = 'hidden'      # 'hidden', 'capsule', 'expanded'
superisland_anim_progress = 0.0   # 0.0 تا 1.0 (ورود و خروج جزیره)
superisland_expand_progress = 0.0 # 0.0 تا 1.0 (تبدیل به مستطیل بزرگ)

# --- متغیرهای صفحه والپیپر سفارشی ---
custom_wp_scroll_offset = 0.0
target_custom_wp_scroll_offset = 0.0
custom_wp_thumbnails = {} # برای جلوگیری از لگ هنگام اسکرول

AI_MODEL_PATH = "ai_model.safetensors"
ai_model_exists = os.path.exists(AI_MODEL_PATH)

is_ai_layout_enabled = False
ai_preview_active = False
ai_preview_progress = 0.0

# سیستم جمع‌آوری داده رفتار کاربر
ai_learning_start_time = None
ai_app_clicks = {}  # ذخیره کلیک روی هر اپلیکیشن

# =====================================================
# --- متغیرهای پیام‌رسان WiFi ---
# =====================================================
messenger_username = "کاربر"          # نام کاربری محلی
messenger_messages = []               # [{sender, text, time, self}]
messenger_input_text = ""            # متن در حال تایپ
messenger_contacts = []              # لیست مخاطبین کشف‌شده [{name, addr, port}]
messenger_server = None              # سرور UDP/TCP
messenger_server_thread = None
messenger_peer_addr = None           # آدرس مخاطب انتخاب‌شده
messenger_scroll = 0.0               # اسکرول چت
messenger_target_scroll = 0.0
messenger_page = 'chats'             # 'chats' | 'chat' | 'new' | 'settings'
messenger_is_discovering = False     # در حال اسکن شبکه
messenger_discovery_results = []     # نتایج اسکن
messenger_notification_badge = 0     # تعداد پیام‌های نخوانده
messenger_port = 55789               # پورت UDP
MESSENGER_BROADCAST_PORT = 55790     # پورت broadcast discovery
messenger_conversations = {}         # {addr: [{sender,text,time,self}]}
messenger_active_conv = None         # آدرس چت باز
messenger_device_name = ""           # نام دستگاه (برای discovery)
messenger_new_ip_text   = ""         # شماره تلفن مخاطب جدید
messenger_new_name_text = ""         # نام مخاطب جدید
messenger_new_peer_ip   = ""         # آدرس IP دستگاه مخاطب (برای شبکه محلی)
messenger_new_focus     = 'name'     # فیلد فعال: 'name' | 'ip' | 'peer_ip'
input_url_text = ""
is_typing_url = False

# =====================================================
# --- متغیرهای حالت توسعه دهنده (Developer Mode) ---
# =====================================================
is_developer_mode = False
is_root_enabled = False  # متغیر دسترسی ریشه
about_logo_click_count = 0
last_about_logo_click_time = 0.0

settings_scroll_offset = 0.0
target_settings_scroll_offset = 0.0

# =====================================================
# --- متغیر های برنامه ---
# =====================================================

display_server = DisplayServer()
display_server.start()

# (جدید) کلاس پایه برای تمام برنامههای قابل نصب
class ParsOS_App:
    def __init__(self, app_id, app_name, app_path):
        """سازنده برنامه که توسط سیستم عامل فراخوانی میشود."""
        self.app_id = app_id
        self.app_name = app_name
        self.app_path = app_path # مسیر پوشه برنامه برای دسترسی به فایلها
        self.text_font = mf(16)
        self.title_font = mf(22)

    def handle_event(self, event):
        """این متد برای مدیریت رویدادها (کلیک، کیبورد و ...) است."""
        pass

    def update(self):
        """این متد برای بهروزرسانی منطق برنامه در هر فریم است."""
        pass

    def draw(self, surface):
        """این متد برای رسم رابط کاربری برنامه روی سطح ورودی است."""
        surface.fill((240, 240, 240))
        title = self.title_font.render(f"App: {self.app_name}", True, (0,0,0))
        surface.blit(title, title.get_rect(center=(surface.get_width()/2, 50)))

if not os.path.exists('installed_apps'): os.makedirs('installed_apps')
if not os.path.exists('downloads'): os.makedirs('downloads')
# --------------------------
#    مقادیر اولیه و تنظیمات
# --------------------------
pygame.init()
pygame.mixer.init()
running_app_instances = {}

# =====================================================
# --- تشخیص پلتفرم و تنظیم اندازه صفحه ---
# =====================================================
import platform as _platform

def _is_android():
    """تشخیص اجرا روی اندروید"""
    try:
        import android  # noqa — موجود در Pydroid / Buildozer
        return True
    except ImportError:
        pass
    if hasattr(sys, 'getandroidapilevel'):
        return True
    if 'ANDROID_ROOT' in os.environ or 'ANDROID_DATA' in os.environ:
        return True
    if _platform.system() == 'Linux' and 'android' in _platform.release().lower():
        return True
    return False

IS_ANDROID = _is_android()

# اندازه پایه طراحی (همان اندازه دسکتاپ)
BASE_WIDTH  = 400
BASE_HEIGHT = 700

if IS_ANDROID:
    # تمام‌صفحه روی اندروید — دریافت ابعاد واقعی
    info = pygame.display.Info()
    SCREEN_WIDTH  = info.current_w if info.current_w > 0 else BASE_WIDTH
    SCREEN_HEIGHT = info.current_h if info.current_h > 0 else BASE_HEIGHT
    screen = pygame.display.set_mode(
        (SCREEN_WIDTH, SCREEN_HEIGHT),
        pygame.FULLSCREEN | pygame.DOUBLEBUF | pygame.NOFRAME
    )
else:
    SCREEN_WIDTH  = BASE_WIDTH
    SCREEN_HEIGHT = BASE_HEIGHT
    screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.DOUBLEBUF)

pygame.display.set_caption("ParsOS NEXT")

# --- فاکتور مقیاس برای تطبیق UI با اندازه واقعی صفحه ---
# بر اساس کوچک‌ترین نسبت (حفظ نسبت ظاهری)
SCALE_X = SCREEN_WIDTH  / BASE_WIDTH
SCALE_Y = SCREEN_HEIGHT / BASE_HEIGHT
SCALE   = min(SCALE_X, SCALE_Y)   # یکنواخت (uniform scale)

def sc(value):
    """مقیاس‌بندی یک مقدار عددی بر اساس SCALE"""
    return int(value * SCALE)

def scf(value):
    """مقیاس‌بندی float"""
    return value * SCALE

def mf(size):
    """ساخت فونت با اندازه مقیاس‌بندی‌شده — جایگزین inline Font() calls"""
    scaled = max(1, int(size * SCALE))
    if main_font_path:
        return pygame.font.Font(main_font_path, scaled)
    else:
        return pygame.font.Font(None, int(scaled * 1.3))

# offset برای مرکز‌چینی محتوا روی صفحه بزرگ‌تر
OFFSET_X = (SCREEN_WIDTH  - int(BASE_WIDTH  * SCALE)) // 2
OFFSET_Y = (SCREEN_HEIGHT - int(BASE_HEIGHT * SCALE)) // 2

# (جدید) متغیرهای انیمیشن کلیک روی آیکون
pressed_icon = None
pressed_icon_animation_progress = 0.0
pressed_icon_animation_direction = 0

# (جدید) رنگهای ویجت ساعت
CLOCK_WIDGET_HAND_HOUR = (40, 40, 40)
CLOCK_WIDGET_HAND_MINUTE = (60, 60, 60)
CLOCK_WIDGET_HAND_SECOND = (255, 50, 50)
CLOCK_WIDGET_TICKS = (150, 150, 150)

unimportant_notifications = [] 
# (جدید) اعلانهای اصلی
main_notifications = [] 
# (جدید) متغیر برای اعلان heads-up
active_heads_up_notification = None
notifications = [] # هر اعلان یک دیکشنری شامل متن، زمان و آلفا است

DOWNLOADABLE_EXTENSIONS = ['.zip', '.exe', '.pdf', '.png', '.jpg', '.jpeg', '.mp3', '.wav', '.txt', '.prs']

# متغیر جدید برای ذخیره تصویر برنامه هنگام باز شدن
target_app_snapshot = None

# (جدید) متغیرهای مدیریت زبان
current_language = 'fa' # زبان پیشفرض که از تنظیمات بارگذاری خواهد شد
current_language_name = 'فارسی' # نام نمایشی زبان فعلی
lang_dict = {} # دیکشنری کامل زبانها در اینجا بارگذاری میشود
is_language_picker_open = False
language_picker_progress = 0.0 # 0.0: بسته, 1.0: باز
language_picker_blurred_bg = None # برای پسزمینه تار مودال

is_language_picker_open = False
language_picker_progress = 0.0 # 0.0: بسته, 1.0: باز
language_picker_blurred_bg = None # برای پسزمینه تار مودال
language_picker_start_rect = None # (جدید) برای انیمیشن باز شدن

# (جدید) لیست زبانهای پشتیبانی شده (نام به زبان خودشان)
SUPPORTED_LANGUAGES = {
    'fa': 'فارسی',
    'en': 'English',
    'ar': 'العربية',
    'ru': 'Русский',
    'zh': '中国人'
}
# -------------------
#      مدیریت رنگها و تمها
# -------------------
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
GRAY = (80, 80, 80)
DARK_GRAY = (50, 50, 50)
LIGHT_GRAY = (230, 230, 230)
BLUE = (50, 150, 255)
CHARGING_BLUE = (30, 144, 255)
HYPEROS_TOP = (100, 80, 150)
HYPEROS_BOTTOM = (200, 150, 120)

is_low_battery_warning_visible = False
low_battery_warning_progress = 0.0
low_battery_warning_triggered = False 

is_dark_mode = False
is_theme_animating = False
theme_animation_progress = 0.0
theme_animation_direction = 0
dark_mode_switch_progress = 0.0
home_snapshot_for_animation = None

THEME_COLORS = {
    'settings_bg': [LIGHT_GRAY, (30, 30, 40)],
    'settings_title': [BLACK, WHITE],
    'settings_button_bg': [WHITE, (60, 60, 70)],
    'settings_button_text': [BLACK, LIGHT_GRAY],
    'status_bar_app': [BLACK, WHITE],
    'home_indicator_app': [DARK_GRAY, GRAY],
    'notes_bg': [(255, 255, 255), (25, 25, 25)],
    'notes_text': [BLACK, WHITE],
    'music_bg': [(245, 245, 245), (20, 20, 20)],
    'music_text': [BLACK, WHITE],
    'context_menu_bg': [WHITE, (45, 45, 55)],
    'context_menu_text': [BLACK, WHITE],
    'browser_bg': [(240, 240, 245), (25, 25, 30)],
    'files_bg': [(248, 248, 252), (32, 32, 42)], 
    'gallery_bg': [(250, 250, 250), (28, 28, 28)],
    'card_bg': ((255,255,255), (35,35,35)),
    'card_border': ((200,200,200), (60,60,60)),
    'accent': ((0,120,255), (0,120,255)),
    'subtext': ((90,90,90), (180,180,180)),
    'text_main': ((20,20,20), (240,240,240)),
    'text_muted': ((120,120,120), (160,160,160)),
    'nav_bg': ((245,245,245), (40,40,40)),
    'border': ((200,200,200), (70,70,70)),
    'main_bg': ((235,235,235), (25,25,25))
}
DARK_MODE_BG_TOP = (20, 20, 30)
DARK_MODE_BG_BOTTOM = (50, 50, 70)
saved_light_wallpaper_top = (0, 120, 255)
saved_light_wallpaper_bottom = (80, 180, 255)

def get_current_color(key):
    light, dark = THEME_COLORS[key]
    if not is_theme_animating:
        return dark if is_dark_mode else light
    progress = max(0.0, min(1.0, theme_animation_progress))
    return tuple(int(l + (d - l) * progress) for l, d in zip(light, dark))


BG_TOP_COLOR = saved_light_wallpaper_top
BG_BOTTOM_COLOR = saved_light_wallpaper_bottom
current_wallpaper_image = None
wallpaper_path = None
# متغیرهای پسزمینه صفحه قفل
lock_screen_wallpaper_path = None
current_lock_screen_wallpaper_image = None
# (جدید) متغیرهای جلوه عمق
is_depth_effect_enabled = False
current_lock_screen_subject_image = None


# فونتها
try:
    main_font_path = "Vazir.ttf"
    try:
        about_font = pygame.font.Font("ProductSans.ttf", sc(48))
    except FileNotFoundError:
        print("فونت ProductSans.ttf یافت نشد. از فونت وزیر برای صفحه 'درباره' استفاده میشود.")
        about_font = pygame.font.Font(main_font_path, sc(40))
    clock_font          = pygame.font.Font(main_font_path, sc(80))
    battery_font        = pygame.font.Font(main_font_path, sc(48))
    text_font           = pygame.font.Font(main_font_path, sc(16))
    notes_font          = pygame.font.Font(main_font_path, sc(18))
    music_font          = pygame.font.Font(main_font_path, sc(22))
    status_bar_font     = pygame.font.Font(main_font_path, sc(14))
    settings_title_font = pygame.font.Font(main_font_path, sc(24))
    music_time_font     = pygame.font.Font(main_font_path, sc(12))
    browser_content_font= pygame.font.Font(main_font_path, sc(14))
    clock_font          = pygame.font.Font(main_font_path, sc(80))
    large_clock_font    = pygame.font.Font(main_font_path, sc(120)) # فونت جدید و بزرگ‌تر
except FileNotFoundError:
    print("فونت Vazir.ttf یافت نشد. از فونت پیشفرض استفاده میشود.")
    main_font_path = None
    about_font          = pygame.font.Font(None, sc(60))
    clock_font          = pygame.font.Font(None, sc(100))
    battery_font        = pygame.font.Font(None, sc(60))
    text_font           = pygame.font.Font(None, sc(24))
    notes_font          = pygame.font.Font(None, sc(26))
    music_font          = pygame.font.Font(None, sc(30))
    status_bar_font     = pygame.font.Font(None, sc(20))
    settings_title_font = pygame.font.Font(None, sc(32))
    music_time_font     = pygame.font.Font(None, sc(18))
    browser_content_font= pygame.font.Font(None, sc(20))

clock = pygame.time.Clock()
persian_digits = {'0': '۰', '1': '۱', '2': '۲', '3': '۳', '4': '۴', '5': '۵', '6': '۶', '7': '۷', '8': '۸', '9': '۹'}

# --------------------------
#    متغیرهای مدیریت وضعیت
# --------------------------
current_screen = "lock"
gallery_photos = []
gallery_thumbnails = {}
is_gallery_fullscreen = False
gallery_selected_index = 0
gallery_animation_progress = 0.0
gallery_animation_direction = 0
gallery_start_rect = None
is_gallery_scrolling = False
gallery_scroll_offset = 0.0
target_gallery_scroll_offset = 0.0
gallery_content_height = 0
recents_focused_index = 0.0
target_recents_focused_index = 0.0
lock_swipe_start_pos = None
is_swiping_lock = False
lock_screen_offset_y = 0.0
target_lock_offset_y = 0.0
lock_swipe_threshold = 100
animation_progress = 0.0
lock_screen_snapshot = None
home_screen_surface = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
home_page_index = 0
num_home_pages = 3
home_page_offset = 0.0
target_offset = 0.0
is_swiping_home = False
home_swipe_start_pos = None
home_swipe_threshold = SCREEN_WIDTH / 4
is_edit_mode = False
edit_mode_scale = 1.0
target_edit_mode_scale = 1.0
mouse_down_start_time = 0
long_press_duration = 1.0
selected_icon = None
selected_icon_source = None
is_dragging_icon = False
icon_drag_offset = (0, 0)
page_swipe_timer = 0
PAGE_SWIPE_COOLDOWN = 0.7

# متغیر سراسری جدید برای مدیریت نمایش اطلاعات عکس
is_gallery_info_visible = False

# --- ویرایشگر گالری ---
is_gallery_editor_open = False       # آیا ویرایشگر باز است؟
gallery_editor_surface = None        # سطح ویرایش (کپی از تصویر اصلی)
gallery_editor_original = None       # نسخه اصلی تصویر (برای undo)
gallery_editor_tool = 'pen'          # ابزار: 'pen', 'line', 'rect', 'text', 'eraser'
gallery_editor_color = (255, 80, 80) # رنگ ابزار فعال
gallery_editor_size = 4              # اندازه ابزار
gallery_editor_strokes = []          # تاریخچه stroke ها برای undo
gallery_editor_is_drawing = False    # در حال رسم
gallery_editor_last_pos = None       # آخرین موقعیت موس
gallery_editor_pending_text = ""     # متن در حال تایپ
gallery_editor_text_pos = None       # موقعیت متن
gallery_editor_colors = [            # پالت رنگ
    (255, 255, 255), (0, 0, 0),
    (255, 80, 80), (255, 160, 30),
    (255, 220, 0), (60, 200, 80),
    (50, 150, 255), (180, 80, 255),
    (255, 100, 180), (0, 210, 210),
]
gallery_editor_toolbar_alpha = 255   # آلفای toolbar (fade)
gallery_editor_toolbar_target = 255
gallery_editor_undo_stack = []       # پشته undo
gallery_editor_start_pos = None      # نقطه شروع برای line/rect
gallery_editor_text_input = False    # حالت تایپ متن فعال است
gallery_editor_cached_img = None     # تصویر scale شده cache (برای جلوگیری از هنگ)
gallery_editor_img_rect = None       # موقعیت تصویر در صفحه (static)
gallery_editor_dirty = True          # آیا باید cache را بازسازی کرد؟

# --- متغیرهای پلیر ویدیو ---
is_video_playing = False
video_capture = None          # شی cv2.VideoCapture
video_frame_surface = None    # فریم فعلی به عنوان pygame.Surface
video_paused = False
video_playback_fps = 30.0
video_last_frame_time = 0.0
video_current_frame = 0
video_total_frames = 0
video_duration = 0.0
video_current_time = 0.0
video_path = ""
is_scrubbing_video = False
video_scrub_progress = 0.0
video_controls_visible = True   # نمایش کنترلها
video_controls_hide_timer = 0.0 # تایمر مخفی شدن خودکار
video_ui_fade = 1.0             # آلفای انیمیشن fade کنترلها
video_ui_fade_target = 1.0

# --- ویدیوها در گالری ---
gallery_videos = []             # لیست فایلهای ویدیو

app_animation_progress = 0.0
opened_app_icon_rect = None
is_swiping_app_close = False
app_swipe_start_pos = None
app_context = {}
app_screen_animation_progress = 0.0
app_screen_animation_direction = 0
active_button_rect = None
active_button_key = None
active_file_item = None
app_surfaces = {}
#app_just_closed = False # (جدید) برای رفع باگ منوی برنامههای اخیر
app_close_timestamp = 0.0

# (جدید) متغیرهای مدیریت وضعیت برای چندنخی
thread_results = {} # دیکشنری برای نگهداری نتایج نخها
is_processing_depth_effect = False
is_installing_app = False

animating_icon = None
icon_animation_progress = 0.0
is_icon_animation_active = False
is_notes_icon_animation_active = False
notes_icon_animation_progress = 0.0
animating_notes_icon = None
is_music_icon_animation_active = False
music_icon_animation_progress = 0.0
animating_music_icon = None
is_browser_icon_animation_active = False
browser_icon_animation_progress = 0.0
animating_browser_icon = None

# (جدید) متغیرهای اسلایدرهای مرکز کنترل
cc_brightness = 0.7 # 0.0 تا 1.0
cc_volume = 0.5     # 0.0 تا 1.0
is_scrubbing_brightness = False
is_scrubbing_volume = False

folder_hover_target = None
folder_hover_start_time = 0
folder_highlight_alpha = 0.0
is_showing_folder = False
opened_folder = None
folder_animation_progress = 0.0
folder_dragged_icon_from = None
opened_folder_icon_rect = None
folder_just_closed = False
folder_view_blurred_bg = None
is_folder_edit_mode = False
folder_mouse_down_start_time = 0
folder_mouse_down_pos = None
selected_icon_in_folder = None
folders_to_delete = []

is_charging_animation_active = False
charging_animation_should_end = False
charging_animation_start_time = 0
charging_animation_alpha = 0.0
charging_particles = []
was_plugged_in = psutil.sensors_battery().power_plugged if psutil.sensors_battery() else False

# (جدید) متغیرهای مرکز اعلانات
is_notification_center_open = False
notification_center_progress = 0.0 # 0.0: بسته, 1.0: باز
is_dragging_notification_center = False
notification_center_snapshot = None

# متغیرهای برنامه یادداشت
notes_text = ""
cursor_visible = True
cursor_timer = 0
notes_save_filename = "یادداشت جدید.txt"
notes_file_list = []
is_notes_context_menu_open = False
notes_context_menu_pos = (0, 0)
clipboard_text = ""
text_surfaces_cache = []
last_notes_text = ""

scroll_offset = 0          # اسکرول فعلی (نرم)
target_scroll_offset = 0   # اسکرول هدف (lerp)
MAX_VISIBLE_HEIGHT = SCREEN_HEIGHT - sc(120)
# متغیرهای انیمیشن یادداشت
notes_cursor_alpha = 255       # آلفا cursor برای fade نرم
notes_last_type_time = 0.0     # زمان آخرین کاراکتر
notes_word_count = 0
notes_char_count = 0
# متغیرهای cursor پیشرفته
notes_cursor_index = 0         # موقعیت cursor در متن (تعداد کاراکتر از ابتدا)
notes_key_repeat_timer = 0.0   # تایمر تکرار کلید (برای hold)
notes_key_repeat_key = None    # کلیدی که نگه داشته شده
notes_key_repeat_delay = 0.45  # تاخیر اول قبل از تکرار (ثانیه)
notes_key_repeat_rate = 0.04   # فاصله بین تکرارها (ثانیه)

# متغیرهای برنامه موسیقی
music_playlist = []
current_track_index = 0
is_music_playing = False
music_track_name = "موسیقی یافت نشد"
is_music_paused = False
current_track_length = 0
is_scrubbing_music = False
music_scrub_progress = 0.0
music_playback_start_time_offset = 0.0
current_album_art_surface = None
MUSIC_ENDED = pygame.USEREVENT + 1
pygame.mixer.music.set_endevent(MUSIC_ENDED)
cached_blurred_bg = None
last_played_track_name = ""
music_art_scale = 0.85          # مقیاس فعلی کاور (0.85 در حالت توقف، 1.0 در پخش)
target_music_art_scale = 0.85   # هدف مقیاس
music_text_scroll_x = 0.0       # موقعیت اسکرول متن
music_button_states = {         # وضعیت فشرده شدن دکمهها برای انیمیشن
    'play': {'scale': 1.0, 'pressed': False},
    'next': {'scale': 1.0, 'pressed': False},
    'prev': {'scale': 1.0, 'pressed': False}
}
# --- متغیرهای ترانزیشن بین آهنگ‌ها (iOS-like slide) ---
music_transition = {
    'active': False,
    'direction': 0,      # +1 برای next, -1 برای prev
    'progress': 0.0,     # 0 → 1
    'duration': 0.35,    # ثانیه
    'old_art': None,     # سطح کاور قدیم
    'new_art': None,     # سطح کاور جدید
    'old_track_name': '',
    'new_track_name': '',
    'old_track_index': -1,
    'new_track_index': -1,
    'start_time': 0.0,
}
is_scrubbing_active_anim = False # برای انیمیشن بزرگ شدن نوار هنگام لمس
scrub_knob_scale = 1.0
# (جدید) حالتهای پخش
music_shuffle = False   # پخش تصادفی
music_repeat = 0        # 0: بدون تکرار، 1: تکرار پلیلیست، 2: تکرار یک آهنگ

# (جدید) متغیرهای برنامه فایلها
files_current_path = '.'
files_list = []
files_scroll_offset = 0.0
target_files_scroll_offset = 0.0
files_scroll_velocity = 0.0          # سرعت فعلی پیمایش (پیکسل بر فریم)
files_scroll_friction = 0.92         # ضریب اصطکاک (کمتر=اصطکاک بیشتر)
files_content_height = 0
files_overscroll_resistance = 0.3    # مقاوت در برابر کشیدن بیش از حد
files_is_user_scrolling = False      # آیا کاربر در حال اسکرول دستی است؟
files_last_scroll_time = 0           # زمان آخرین اسکرول دستی
files_scroll_active = True

# متغیرهای برنامه مرورگر
browser_url_input = "example.com"
browser_page_title = "Browser"
browser_content_surfaces = []
browser_scroll_offset = 0
browser_content_height = 0
is_url_input_active = False
browser_history = ["example.com"]
browser_history_index = 0
browser_is_loading = False
browser_scroll_offset = 0.0
target_browser_scroll_offset = 0.0 # (جدید) برای اسکرول نرم
api_results = []
api_loading = False

# متغیرهای مرکز کنترل
is_control_center_open = False
control_center_progress = 0.0  # 0.0: بسته, 1.0: باز
is_dragging_control_center = False
control_center_snapshot = None
# (اصلاح شده) وضعیت دکمههای مرکز کنترل با ساختار جدید
cc_buttons = {
    # دکمههای بزرگ ردیف اول
    'wifi': {
        'is_active': False, 'is_pressed': False, 'scale_progress': 0.0, 'color_progress': 0.0, 
        'press_anim_progress': 0.0, 'press_location': None, 'label': 'وای فای', 'type': 'large'
    },
    'data': {
        'is_active': True, 'is_pressed': False, 'scale_progress': 0.0, 'color_progress': 1.0, 
        'press_anim_progress': 0.0, 'press_location': None, 'label': 'داده همراه', 'type': 'large'
    },
    
    # دکمههای گرد
    'dnd': {'is_active': False, 'is_pressed': False, 'label': 'مزاحم نشوید', 'icon': '🌙', 'type': 'circular'},
    'airplane': {'is_active': False, 'is_pressed': False, 'label': 'هواپیما', 'icon': '✈️', 'type': 'circular'},
    'bluetooth': {'is_active': False, 'is_pressed': False, 'label': 'بلوتوث', 'icon': 'B', 'type': 'circular'}, # آیکون بلوتوث در فونتها نیست
    'hotspot': {'is_active': False, 'is_pressed': False, 'label': 'نقطه اتصال', 'icon': '🔗', 'type': 'circular'},
    'flashlight': {'is_active': False, 'is_pressed': False, 'label': 'چراغ قوه', 'icon': '🔦', 'type': 'circular'},
    'location': {'is_active': True, 'is_pressed': False, 'label': 'مکان', 'icon': '📍', 'type': 'circular'},
    'battery_saver': {'is_active': False, 'is_pressed': False, 'label': 'ذخیره باتری', 'icon': '🔋', 'type': 'circular'},
    'rotation_lock': {'is_active': True, 'is_pressed': False, 'label': 'قفل چرخش', 'icon': '🔒', 'type': 'circular'},
}

# (جدید) متغیرهای افکت کشسانی مرکز کنترل
is_dragging_cc_content = False
cc_vertical_offset = 0.0
target_cc_vertical_offset = 0.0
cc_drag_start_y = 0

# متغیرهای منوی برنامههای اخیر
target_dragged_recent_app_offset_y = 0
animating_recent_app_index = None
recents_apps_list = []
is_swiping_for_recents = False
recents_swipe_start_pos = None
recents_swipe_start_time = 0
recents_animation_progress = 0.0
recents_scroll_offset = 0.0
target_recents_scroll_offset = 0.0
dragged_recent_app_index = None
dragged_recent_app_offset_y = 0
recents_view_blurred_bg = None
recents_mouse_down_pos = None
closing_recent_apps = []
# (جدید) متغیرهای انیمیشن بازگشت کارت
target_dragged_recent_app_offset_y = 0
animating_recent_app_index = None

# (جدید) متغیرهای مدیریت نخ برای افکت بلور
blur_thread_result = None # برای نگهداری نتیجه نخ بلور
is_blur_processing = False  # برای جلوگیری از اجرای همزمان چند نخ

# متغیرهای صفحه اصلی
icons = [[] for _ in range(num_home_pages)]
dock_icons = []
icon_size    = sc(70)
icon_padding = sc(25)
icons_per_row = 4
rows_per_page = 4
MAX_DOCK_ICONS = 3
dock_height = sc(85)
dock_margin = sc(10)
dock_rect = pygame.Rect(dock_margin, SCREEN_HEIGHT - dock_height - dock_margin, SCREEN_WIDTH - 2 * dock_margin, dock_height)

# تنظیمات پیشفرض
wallpaper_presets = [
    ((0, 120, 255), (80, 180, 255)),
    ((255, 100, 100), (255, 180, 80)),
    ((80, 200, 120), (150, 220, 180)),
    ((50, 50, 70), (20, 20, 30)),
]
wallpaper_preset_rects = []
lock_screen_preset_rects = []
lock_screen_style = 'default'

# --------------------------------
#    توابع ذخیره و بازیابی اطلاعات
# --------------------------------
# (جدید) تابع پردازش تصویر برای جلوه عمق
def process_depth_effect_image(image_surface):
    """
    (اصلاح شده) این تابع تصویر ورودی از نوع pygame.Surface را برای جلوه عمق پردازش میکند.
    مشکل تبدیل فرمت تصویر تغییراندازهیافته با استفاده از روش مطمئنتر tostring حل شده است.
    """
    global current_lock_screen_subject_image
    
    if not depth_effect_available or image_surface is None:
        current_lock_screen_subject_image = None
        return
        
    try:
        image_data = pygame.image.tostring(image_surface, "RGBA")
        
        input_image = Image.frombytes("RGBA", image_surface.get_size(), image_data)
        output_image = remove(input_image)

        image_bytes = output_image.tobytes()
        subject_surface = pygame.image.fromstring(image_bytes, output_image.size, output_image.mode).convert_alpha()

        final_surface = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        final_rect = subject_surface.get_rect(center=(SCREEN_WIDTH / 2, SCREEN_HEIGHT / 2))
        final_surface.blit(subject_surface, final_rect)

        current_lock_screen_subject_image = final_surface
        print("Depth effect subject processed successfully from scaled surface.")
        
    except Exception as e:
        print(f"Error processing depth effect image: {e}")
        current_lock_screen_subject_image = None


def serialize_icons(icon_list):
    serial_list = []
    for icon in icon_list:
        if icon['type'] == 'app':
            serial_list.append({'type': 'app', 'name': icon['name'], 'page': icon.get('page'), 'row': icon.get('row'), 'col': icon.get('col')})
        elif icon['type'] == 'folder':
            serial_list.append({'type': 'folder', 'name': icon.get('name', 'پوشه'), 'contains': serialize_icons(icon['contains']), 'page': icon.get('page'), 'row': icon.get('row'), 'col': icon.get('col')})
        # (جدید) افزودن پشتیبانی از ویجت
        elif icon['type'] == 'widget':
            serial_list.append({
                'type': 'widget',
                'widget_type': icon.get('widget_type'),
                'size': icon.get('size', (1, 1)),
                'page': icon.get('page'), 'row': icon.get('row'), 'col': icon.get('col')
            })
    return serial_list

def deserialize_icons(data_list):
    icon_list = []
    app_list = ['settings', 'notes', 'music', 'browser' 'gallery']
    for icon_data in data_list:
        # (اصلاح شده) بررسی جامعتر برای انواع مختلف آیکون
        if 'type' not in icon_data: icon_data['type'] = 'app'

        if icon_data.get('type') == 'app' and icon_data.get('name') not in app_list:
            continue

        # (جدید) افزودن منطق برای ویجت
        if icon_data.get('type') == 'widget':
             # اندازه پیشفرض برای ویجت ۱x۱ است
            size = icon_data.get('size', (1, 1))
            widget_width = size[0] * icon_size + (size[0] - 1) * icon_padding
            widget_height = size[1] * icon_size + (size[1] - 1) * icon_padding
            new_icon = {**icon_data, 'rect': pygame.Rect(0, 0, widget_width, widget_height), 'pos': [0, 0]}
        else:
            new_icon = {**icon_data, 'rect': pygame.Rect(0, 0, icon_size, icon_size), 'pos': [0, 0]}

        if icon_data.get('type') == 'folder':
            new_icon['contains'] = deserialize_icons(icon_data.get('contains', []))

        icon_list.append(new_icon)
    return icon_list

def save_layout():
    layout_data = {'home_icons': [serialize_icons(page) for page in icons], 'dock_icons': serialize_icons(dock_icons)}
    try:
        with open('layout.json', 'w', encoding='utf-8') as f: json.dump(layout_data, f, ensure_ascii=False, indent=4)
    except IOError as e: print(f"Error saving layout: {e}")

def aspect_crop_scale(image, size):
    """تصویر را برش میدهد تا دقیقاً مربع شود و سپس تغییر اندازه میدهد."""
    width, height = image.get_size()
    min_dim = min(width, height)
    
    # محاسبه ناحیه برش (مرکز تصویر)
    left = (width - min_dim) // 2
    top = (height - min_dim) // 2
    
    # برش تصویر
    cropped = image.subsurface((left, top, min_dim, min_dim)).copy()
    
    # تغییر اندازه به سایز مورد نظر (با کیفیت بالا)
    return pygame.transform.smoothscale(cropped, size)

def load_gallery_photos():
    global gallery_photos, gallery_thumbnails, gallery_videos
    if not os.path.exists('gallery_photos'):
        os.makedirs('gallery_photos')
    
    gallery_photos = []
    gallery_thumbnails = {}
    gallery_videos = []

    VIDEO_EXTS = ('.mp4', '.avi', '.mov', '.mkv', '.webm')
    IMAGE_EXTS = ('.png', '.jpg', '.jpeg', '.gif', '.bmp', '.webp')

    try:
        all_files = os.listdir('gallery_photos')
        all_files.sort(key=lambda x: os.path.getmtime(os.path.join('gallery_photos', x)), reverse=True)
        
        for filename in all_files:
            path = os.path.join('gallery_photos', filename)
            ext = os.path.splitext(filename)[1].lower()
            size_mb = os.path.getsize(path) / (1024 * 1024)
            timestamp = os.path.getmtime(path)
            date_str = datetime.datetime.fromtimestamp(timestamp).strftime('%Y/%m/%d')

            if ext in IMAGE_EXTS:
                gallery_photos.append({
                    'path': path,
                    'name': filename,
                    'image': None,
                    'size_str': f"{size_mb:.1f} MB",
                    'date': date_str,
                    'type': 'photo'
                })
                try:
                    img = pygame.image.load(path)
                    thumb = aspect_crop_scale(img, (150, 150))
                    gallery_thumbnails[path] = thumb
                except Exception as e:
                    print(f"Error creating thumbnail for {filename}: {e}")

            elif ext in VIDEO_EXTS:
                # ساخت تامبنیل ویدیو با opencv
                thumb = None
                duration = 0.0
                if cv2_available:
                    try:
                        cap = cv2.VideoCapture(path)
                        fps = cap.get(cv2.CAP_PROP_FPS) or 30
                        total = cap.get(cv2.CAP_PROP_FRAME_COUNT)
                        duration = total / fps if fps > 0 else 0
                        ret, frame = cap.read()
                        if ret:
                            frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                            h, w = frame_rgb.shape[:2]
                            surf = pygame.surfarray.make_surface(frame_rgb.swapaxes(0, 1))
                            thumb = aspect_crop_scale(surf, (150, 150))
                        cap.release()
                    except Exception as e:
                        print(f"Error making video thumbnail: {e}")

                gallery_videos.append({
                    'path': path,
                    'name': filename,
                    'thumb': thumb,
                    'size_str': f"{size_mb:.1f} MB",
                    'date': date_str,
                    'duration': duration,
                    'type': 'video'
                })
                if thumb:
                    gallery_thumbnails[path] = thumb

    except Exception as e:
        print(f"Error loading gallery: {e}")

# (جدید) این تابع را در انتهای بخش بارگذاری اولیه صدا بزنید
load_gallery_photos()

def load_layout():
    global icons, dock_icons
    loaded_apps = set()
    # (جدید) یک مجموعه برای ویجتها تا از افزودن تکراری جلوگیری شود
    loaded_widgets = set()

    def find_items(icon_list):
        for icon in icon_list:
            if icon['type'] == 'app':
                loaded_apps.add(icon['name'])
            elif icon['type'] == 'widget':
                loaded_widgets.add(icon.get('widget_type'))
            elif icon['type'] == 'folder':
                find_items(icon.get('contains', []))

    try:
        with open('layout.json', 'r', encoding='utf-8') as f:
            layout_data = json.load(f)
            icons_data = layout_data.get('home_icons', [])
            icons = [deserialize_icons(page_data) for page_data in icons_data]
            dock_icons = deserialize_icons(layout_data.get('dock_icons', []))
            while len(icons) < num_home_pages: icons.append([])
            find_items([icon for page in icons for icon in page]); find_items(dock_icons)
    except (FileNotFoundError, json.JSONDecodeError): pass

    # افزودن برنامههای پیشفرض در صورت عدم وجود
    if 'settings' not in loaded_apps: icons[0].append({'type': 'app', 'name': 'settings', 'page': 0, 'row': 2, 'col': 0, 'rect': pygame.Rect(0,0,icon_size,icon_size), 'pos': [0,0]})
    if 'notes' not in loaded_apps: icons[0].append({'type': 'app', 'name': 'notes', 'page': 0, 'row': 2, 'col': 1, 'rect': pygame.Rect(0,0,icon_size,icon_size), 'pos': [0,0]})
    if 'music' not in loaded_apps: icons[0].append({'type': 'app', 'name': 'music', 'page': 0, 'row': 2, 'col': 2, 'rect': pygame.Rect(0,0,icon_size,icon_size), 'pos': [0,0]})
    if 'browser' not in loaded_apps: icons[0].append({'type': 'app', 'name': 'browser', 'page': 0, 'row': 2, 'col': 3, 'rect': pygame.Rect(0,0,icon_size,icon_size), 'pos': [0,0]})
    if 'gallery' not in loaded_apps: icons[0].append({'type': 'app', 'name': 'gallery', 'page': 0, 'row': 3, 'col': 0, 'rect': pygame.Rect(0,0,icon_size,icon_size), 'pos': [0,0]})
    if 'files' not in loaded_apps: icons[0].append({'type': 'app', 'name': 'files', 'page': 0, 'row': 3, 'col': 1, 'rect': pygame.Rect(0,0,icon_size,icon_size), 'pos': [0,0]})
    if 'messenger' not in loaded_apps: icons[0].append({'type': 'app', 'name': 'messenger', 'page': 0, 'row': 3, 'col': 2, 'rect': pygame.Rect(0,0,icon_size,icon_size), 'pos': [0,0]})

    # (جدید) افزودن ویجت ساعت اگر قبلاً بارگذاری نشده باشد
    if 'clock' not in loaded_widgets:
        widget_size = (2, 2)
        widget_width = widget_size[0] * icon_size + (widget_size[0] - 1) * icon_padding
        widget_height = widget_size[1] * icon_size + (widget_size[1] - 1) * icon_padding
        icons[0].append({
            'type': 'widget',
            'widget_type': 'clock',
            'size': widget_size,
            'page': 0, 'row': 0, 'col': 0,
            'rect': pygame.Rect(0,0,widget_width,widget_height),
            'pos': [0,0]
        })   

def save_settings():
    settings_data = {
        'is_dark_mode': is_dark_mode,
        'light_wallpaper': {'top': saved_light_wallpaper_top, 'bottom': saved_light_wallpaper_bottom},
        'lock_screen_style': lock_screen_style,
        'wallpaper_path': wallpaper_path,
        'lock_screen_wallpaper_path': lock_screen_wallpaper_path,
        'is_depth_effect_enabled': is_depth_effect_enabled,
        'current_language': current_language, # (جدید) ذخیره زبان
        'is_superisland_enabled': is_superisland_enabled,
    }
    try:
        with open('settings.json', 'w') as f: json.dump(settings_data, f, indent=4)
    except IOError as e: print(f"Error saving settings: {e}")

def load_settings():
    saved_light_wallpaper_top = (240, 240, 240)   
    saved_light_wallpaper_bottom = (200, 200, 200)
    
    # متغیرهای تصویر زمینه و تم به global اضافه شدند
    global is_dark_mode, language, volume, brightness 
    global is_superisland_enabled, superisland_switch_progress
    global wallpaper_path, lock_screen_wallpaper_path, current_wallpaper_image, current_lock_screen_wallpaper_image
    global BG_TOP_COLOR, BG_BOTTOM_COLOR, theme_animation_progress, dark_mode_switch_progress

    settings_data = {}

    try:
        with open('settings.json', 'r') as f:
            settings_data = json.load(f)
            is_dark_mode = settings_data.get('is_dark_mode', False)
            lock_screen_style = settings_data.get('lock_screen_style', 'default')
            wallpaper_path = settings_data.get('wallpaper_path', None)
            lock_screen_wallpaper_path = settings_data.get('lock_screen_wallpaper_path', None)
            is_depth_effect_enabled = settings_data.get('is_depth_effect_enabled', False)
            current_language = settings_data.get('current_language', 'fa')
            
            if wallpaper_path and os.path.exists(wallpaper_path):
                try:
                    loaded_image = pygame.image.load(wallpaper_path).convert()
                    current_wallpaper_image = pygame.transform.smoothscale(loaded_image, (SCREEN_WIDTH, SCREEN_HEIGHT))
                except pygame.error as e:
                    print(f"Error loading wallpaper image: {e}")
                    wallpaper_path = None
                    current_wallpaper_image = None
            
            if lock_screen_wallpaper_path and os.path.exists(lock_screen_wallpaper_path):
                try:
                    loaded_image = pygame.image.load(lock_screen_wallpaper_path).convert()
                    current_lock_screen_wallpaper_image = pygame.transform.smoothscale(loaded_image, (SCREEN_WIDTH, SCREEN_HEIGHT))
                    if is_depth_effect_enabled:
                        process_depth_effect_image(current_lock_screen_wallpaper_image)
                except pygame.error as e:
                    print(f"Error loading lock screen wallpaper image: {e}")
                    lock_screen_wallpaper_path = None
                    current_lock_screen_wallpaper_image = None

            if not current_wallpaper_image:
                wallpaper = settings_data.get('light_wallpaper')
                if wallpaper: saved_light_wallpaper_top, saved_light_wallpaper_bottom = tuple(wallpaper['top']), tuple(wallpaper['bottom'])

            if is_dark_mode:
                BG_TOP_COLOR, BG_BOTTOM_COLOR, theme_animation_progress = DARK_MODE_BG_TOP, DARK_MODE_BG_BOTTOM, 1.0
                dark_mode_switch_progress = 1.0
            else:
                BG_TOP_COLOR, BG_BOTTOM_COLOR, theme_animation_progress = saved_light_wallpaper_top, saved_light_wallpaper_bottom, 0.0
                dark_mode_switch_progress = 0.0
    except (FileNotFoundError, json.JSONDecodeError): pass

    is_superisland_enabled = settings_data.get('is_superisland_enabled', False)
    superisland_switch_progress = 1.0 if is_superisland_enabled else 0.0

def save_notes():
    try:
        with open('notes.txt', 'w', encoding='utf-8') as f: f.write(notes_text)
    except IOError as e: print(f"Error saving notes: {e}")

def load_notes():
    global notes_text
    try:
        if not os.path.exists('notes'): os.makedirs('notes')
        with open('notes.txt', 'r', encoding='utf-8') as f: notes_text = f.read()
    except FileNotFoundError: notes_text = "اینجا بنویسید..."

def get_track_info(filepath):
    length = 0
    art_surface = None
    
    if mutagen_available:
        try:
            if filepath.lower().endswith('.mp3'):
                audio = mutagen.mp3.MP3(filepath)
                tags = ID3(filepath)
                for key in tags:
                    if key.startswith('APIC'):
                        apic = tags[key]
                        image_data = apic.data
                        try:
                            image_file = io.BytesIO(image_data)
                            art_surface = pygame.image.load(image_file).convert_alpha()
                            break
                        except pygame.error as e:
                            print(f"Could not load album art: {e}")
                length = audio.info.length
            elif filepath.lower().endswith('.wav'):
                audio = mutagen.wave.WAVE(filepath)
                length = audio.info.length
            elif filepath.lower().endswith('.ogg'):
                audio = mutagen.oggvorbis.OggVorbis(filepath)
                length = audio.info.length
        except Exception as e:
            print(f"Error reading audio metadata for {filepath}: {e}")

    # --- رفع باگ زمان: استفاده از موتور Pygame به عنوان پشتیبان ---
    if length == 0:
        try:
            sound = pygame.mixer.Sound(filepath)
            length = sound.get_length()
        except Exception as e:
            print(f"Pygame fallback length error: {e}")

    return length, art_surface

def load_music_files():
    global music_playlist, music_track_name, current_track_length, current_album_art_surface, music_playback_start_time_offset
    music_playlist = []
    if not os.path.exists('music'): os.makedirs('music')
    try:
        for filename in os.listdir('music'):
            if filename.lower().endswith(('.mp3', '.wav', '.ogg')): music_playlist.append(os.path.join('music', filename))
        if music_playlist:
            pygame.mixer.music.load(music_playlist[current_track_index])
            music_track_name = os.path.basename(music_playlist[current_track_index])
            current_track_length, current_album_art_surface = get_track_info(music_playlist[current_track_index])
            music_playback_start_time_offset = 0
    except Exception as e: print(f"Error loading music files: {e}"); music_track_name = "خطا در بارگذاری"

# ایجاد پوشههای لازم در ابتدای برنامه
if not os.path.exists('wallpapers'): os.makedirs('wallpapers')

load_settings(); load_layout(); load_notes(); load_music_files()

# (جدید) تابع بارگذاری دادههای زبان
def load_language_data():
    """
    دادههای زبان را از languages.json بارگذاری میکند.
    این تابع باید بعد از load_settings (که current_language را میخواند) فراخوانی شود.
    """
    global lang_dict, current_language_name
    try:
        with open('languages.json', 'r', encoding='utf-8') as f:
            all_lang_data = json.load(f)
            # دیکشنری مربوط به زبان فعلی را بارگذاری کن
            if current_language in all_lang_data:
                lang_dict = all_lang_data[current_language]
            else:
                # اگر زبان ذخیره شده در فایل نبود، به انگلیسی یا فارسی بازگرد
                lang_dict = all_lang_data.get('en', all_lang_data.get('fa', {}))
                
        # بهروزرسانی نام نمایشی زبان فعلی
        current_language_name = SUPPORTED_LANGUAGES.get(current_language, 'English')
        print(f"Language loaded: {current_language_name}")
        
    except (FileNotFoundError, json.JSONDecodeError) as e:
        print(f"Warning: 'languages.json' not found or corrupted: {e}")
        print("Falling back to default keys.")
        # در صورت نبود فایل، سیستم از کلیدها به عنوان متن استفاده میکند
        lang_dict = {}

# (جدید) تابع دریافت رشته ترجمه شده
def get_string(key, fallback=None):
    """
    رشته ترجمه شده برای کلید داده شده را برمیگرداند.
    اگر یافت نشد، خود کلید یا متن جایگزین (fallback) را برمیگرداند.
    """
    # ابتدا سعی کن از دیکشنری بارگذاری شده بخوانی
    translated_text = lang_dict.get(key)
    
    if translated_text:
        return translated_text
    
    # اگر در دیکشنری نبود، از متن جایگزین استفاده کن
    if fallback:
        return fallback
        
    # اگر هیچکدام نبود، خود کلید را به عنوان متن برگردان
    return key.replace('_', ' ').title()

# (جدید) بارگذاری فایل زبان بلافاصله پس از بارگذاری تنظیمات
load_language_data()

# --------------------------
#       توابع کمکی
# --------------------------
def developer_terminal_thread():
    """ترمینال پیشرفته توسعه دهنده با قابلیت Root"""
    global is_developer_mode, running, is_root_enabled
    print("\n" + "="*45)
    print(" 🛠️ ParsOS Developer Terminal Activated")
    print(" Type 'help' to see available commands.")
    print("="*45 + "\n")
    
    while is_developer_mode and running:
        try:
            # تغییر ظاهر خط فرمان در صورت فعال بودن روت
            prompt = "ParsOS-ROOT# " if is_root_enabled else "ParsOS-Dev> "
            cmd_line = input(prompt).strip()
            if not cmd_line: continue
            
            cmd_parts = cmd_line.split()
            cmd = cmd_parts[0].lower()
            args = cmd_parts[1:]
            
            if cmd == 'help':
                print("دستورات در دسترس:")
                print("  reboot       : راه‌اندازی مجدد سیستم")
                print("  shutdown     : خاموش کردن سیستم")
                print("  notdev       : غیرفعال کردن حالت توسعه دهنده")
                print("  info         : نمایش اطلاعات سیستم")
                print("  time         : نمایش ساعت و تاریخ فعلی")
                print("  mkdir <name> : ساخت پوشه جدید")
                print("  deldir <name>: حذف کامل یک پوشه (نیازمند Root)")
                print("  enable_root  : فعال‌سازی دسترسی ریشه (سوپریوزر)")
                print("  disable_root : لغو دسترسی ریشه")
                
            elif cmd == 'enable_root':
                if is_root_enabled:
                    print("Root is already enabled.")
                else:
                    confirm = input("WARNING: Root access allows deep system modifications. Continue? (y/n): ").strip().lower()
                    if confirm == 'y':
                        is_root_enabled = True
                        print("ROOT mode activated. Proceed with caution.")
                    else:
                        print("Operation aborted.")
                        
            elif cmd == 'disable_root':
                is_root_enabled = False
                print("ROOT mode deactivated.")
                
            elif cmd == 'time':
                print(f"Current System Time: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
                
            elif cmd == 'mkdir':
                if args:
                    folder_name = " ".join(args)
                    os.makedirs(folder_name, exist_ok=True)
                    print(f"Directory '{folder_name}' created successfully.")
                else:
                    print("Usage: mkdir <directory_name>")
                    
            elif cmd == 'deldir':
                if not is_root_enabled:
                    print("Permission Denied: Root access required! Type 'enable_root' first.")
                elif args:
                    folder_name = " ".join(args)
                    try:
                        shutil.rmtree(folder_name)
                        print(f"Directory '{folder_name}' and all its contents deleted.")
                    except Exception as e:
                        print(f"Error deleting directory: {e}")
                else:
                    print("Usage: deldir <directory_name>")
                    
            elif cmd == 'reboot':
                print("Rebooting ParsOS...")
                running = False
                os.execv(sys.executable, ['python'] + sys.argv)
            elif cmd == 'shutdown':
                print("Shutting down ParsOS...")
                running = False
            elif cmd == 'notdev':
                print("Developer mode deactivated.")
                is_developer_mode = False
            elif cmd == 'info':
                print("ParsOS NEXT v1.0 - Terminal Info")
                if psutil:
                    print(f"CPU Usage: {psutil.cpu_percent()}%")
                    print(f"Memory: {psutil.virtual_memory().percent}%")
            else:
                print(f"Command not found: '{cmd}'.")
                
        except EOFError:
            break
        except Exception as e:
            print(f"Terminal error: {e}")

def ios_spring_curve(t):
    # پارامترهای تقریبی فنر (overshoot ~ 0.1 و settle سریع)
    if t <= 0: return 0
    if t >= 1: return 1
    # در بازه اول کمی جلوتر از هدف می‌رود
    if t < 0.7:
        return 1.2 * t - 0.2 * t**2   # overshoot در t ≈ 0.6 به 1.05 می‌رسد
    else:
        # برگشت نرم به 1
        u = (t - 0.7) / 0.3
        return 1.0 + (0.05 * (1 - u)) * (1 - u)

def spring_lerp(current, target, dt, speed=18.0):
    """حرکت فنری و نرم مستقل از فریم ریت (مشابه انیمیشن‌های اپل)"""
    return current + (target - current) * (1.0 - math.exp(-speed * dt))
    
def cache_file_item_surfaces(item):
    """سطوح متنی نام و متادیتا را یک بار رندر کرده و در آیتم ذخیره می‌کند."""
    # اطمینان از وجود کلیدها (در صورت فراخوانی با داده‌های قدیمی)
    if 'name_surf' not in item:
        item['name_surf'] = None
    if 'meta_surf' not in item:
        item['meta_surf'] = None

    if item['name_surf'] is not None:  # قبلاً کش شده
        return

    name_font = mf(17)
    meta_font = mf(11)
    text_color = get_current_color('settings_title')
    sub_text_color = (150, 150, 150) if not is_dark_mode else (160, 160, 165)
    display_name = item['name']
    if len(display_name) > 26:
        display_name = display_name[:24] + "…"
    item['name_surf'] = render_persian_text(display_name, name_font, text_color)
    meta_text = f"{item.get('date','—')}   {item.get('size','—')}"
    item['meta_surf'] = render_persian_text(meta_text, meta_font, sub_text_color)

def ios_ease(t):
    """
    منحنی حرکت مشابه iOS (Quintic Ease Out)
    باعث میشود انیمیشن سریع شروع شود و بسیار نرم متوقف شود.
    """
    return 1 - pow(1 - t, 5)

def get_app_snapshot(app_name, app_page):
    """
    یک تصویر از محیط برنامه میسازد تا در انیمیشن استفاده شود.
    """
    temp_surf = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT))
    
    # تنظیم کانتکست موقت برای رسم
    # توجه: این تابع از توابع رسم موجود شما استفاده میکند
    if app_name == 'settings':
        if app_page == 'main': draw_settings_main_screen(temp_surf)
        elif app_page == 'wallpaper': draw_settings_wallpaper_screen(temp_surf)
        elif app_page == 'display': draw_settings_display_screen(temp_surf)
        elif app_page == 'battery': draw_settings_battery_screen(temp_surf)
        elif app_page == 'about': draw_settings_about_screen(temp_surf)
        else: draw_settings_main_screen(temp_surf)
        
    elif app_name == 'notes':
        if app_name == 'notes':
            notes_app.draw(temp_surf, SCREEN_WIDTH, SCREEN_HEIGHT, app_context)
        
    elif app_name == 'music': draw_music_app_screen(temp_surf)
    elif app_name == 'browser': draw_browser_app_screen(temp_surf)
    elif app_name == 'files': draw_files_app_screen(temp_surf)
    elif app_name == 'gallery': draw_gallery_app_screen(temp_surf)
    
    # برای برنامههای خارجی یا ناشناخته، یک صفحه پیشفرض رنگی میسازیم
    else:
        bg_key = 'settings_bg'
        if app_name == 'gallery': bg_key = 'gallery_bg'
        elif app_name == 'music': bg_key = 'music_bg'
        
        temp_surf.fill(get_current_color(bg_key))
        # رسم نوار وضعیت برای طبیعی شدن
        draw_status_bar() 
        
    return temp_surf



def format_bytes(size):
    # تبدیل بایت به کیلوبایت و مگابایت
    power = 2**10
    n = 0
    power_labels = {0 : '', 1: 'KB', 2: 'MB', 3: 'GB', 4: 'TB'}
    while size > power:
        size /= power
        n += 1
    return f"{size:.1f} {power_labels[n]}"

def draw_modern_file_icon(surface, rect, file_type, color_override=None):
    # رسم آیکونهای باکیفیت و مدرن برای فایلها
    icon_surf = pygame.Surface(rect.size, pygame.SRCALPHA)
    
    # رنگهای پایه
    colors = {
        'dir': (70, 160, 255),      # آبی برای پوشه
        'music': (255, 80, 100),    # قرمز برای موزیک
        'image': (80, 200, 120),    # سبز برای تصویر
        'text': (240, 240, 240),    # سفید/خاکستری برای متن
        'app_package': (150, 80, 220), # بنفش برای برنامه
        'file': (200, 200, 210)     # پیشفرض
    }
    base_color = color_override if color_override else colors.get(file_type, colors['file'])
    
    if file_type == 'dir':
        # رسم پوشه با زبانه
        folder_body = pygame.Rect(0, rect.height * 0.15, rect.width, rect.height * 0.85)
        folder_tab = pygame.Rect(0, 0, rect.width * 0.4, rect.height * 0.2)
        draw_rounded_rect(icon_surf, folder_tab, base_color, 4)
        draw_rounded_rect(icon_surf, folder_body, base_color, 6)
        # سایه ملایم برای عمق
        pygame.draw.rect(icon_surf, (255,255,255, 40), folder_body.inflate(-4, -4), border_radius=4)
        
    elif file_type in ['text', 'file', 'app_package']:
        # رسم کاغذ با گوشه تا شده
        paper_rect = pygame.Rect(rect.width*0.15, 0, rect.width*0.7, rect.height)
        draw_rounded_rect(icon_surf, paper_rect, base_color, 4)
        
        # خطوط متن (اگر متنی باشد)
        if file_type == 'text':
            line_col = (150, 150, 150)
            for i in range(3):
                pygame.draw.line(icon_surf, line_col, 
                                 (rect.width*0.3, rect.height*(0.4 + i*0.15)), 
                                 (rect.width*0.7, rect.height*(0.4 + i*0.15)), 2)
        elif file_type == 'app_package':
             # آیکون جعبه برای برنامه
             box_rect = rect.inflate(-10, -10)
             draw_rounded_rect(icon_surf, box_rect, base_color, 5)
             pygame.draw.line(icon_surf, (255,255,255,100), box_rect.midleft, box_rect.midright, 2)
             pygame.draw.line(icon_surf, (255,255,255,100), box_rect.midtop, box_rect.midbottom, 2)

    elif file_type == 'music':
        draw_rounded_rect(icon_surf, pygame.Rect(0,0,rect.width, rect.height), base_color, 12)
        # رسم نوت موسیقی ساده
        center = (rect.width//2, rect.height//2)
        pygame.draw.circle(icon_surf, WHITE, (center[0]-5, center[1]+5), 4)
        pygame.draw.circle(icon_surf, WHITE, (center[0]+5, center[1]+5), 4)
        pygame.draw.line(icon_surf, WHITE, (center[0]-2, center[1]+5), (center[0]-2, center[1]-8), 2)
        pygame.draw.line(icon_surf, WHITE, (center[0]+8, center[1]+5), (center[0]+8, center[1]-8), 2)
        pygame.draw.line(icon_surf, WHITE, (center[0]-2, center[1]-8), (center[0]+8, center[1]-8), 2)

    elif file_type == 'image':
        draw_rounded_rect(icon_surf, pygame.Rect(0,0,rect.width, rect.height), base_color, 12)
        # رسم نماد کوه و خورشید
        pygame.draw.circle(icon_surf, WHITE, (rect.width*0.7, rect.height*0.3), 3)
        pts = [(rect.width*0.2, rect.height*0.7), (rect.width*0.4, rect.height*0.4), (rect.width*0.6, rect.height*0.7)]
        pygame.draw.polygon(icon_surf, (255,255,255,200), pts)
        
    surface.blit(icon_surf, rect.topleft)
    
def process_blur_in_thread(snapshot):
    """(جدید) این تابع در یک نخ جداگانه اجرا میشود تا افکت بلور را پردازش کند"""
    global blur_thread_result, is_blur_processing
    print("Blur thread started...") # (برای دیباگ)
    
    try:
        # کار سنگین و زمانبر در اینجا انجام میشود
        blurred_image = apply_gaussian_blur(snapshot, iterations=15)
        blur_thread_result = blurred_image
    except Exception as e:
        print(f"Error in blur thread: {e}")
        blur_thread_result = snapshot # در صورت خطا، حداقل تصویر اصلی را برگردان
        
    print("Blur thread finished.")
    is_blur_processing = False # اعلام پایان کار
    
# (جدید) توابع ایزینگ برای انیمیشنهای روان و حرفهای
def ease_out_cubic(t):
    """انیمیشن سریع در شروع و کند در پایان (بسیار روان)"""
    t = max(0.0, min(1.0, t))
    return 1 - pow(1 - t, 3)

def ease_in_out_cubic(t):
    """انیمیشن کند در شروع، سریع در وسط، کند در پایان"""
    t = max(0.0, min(1.0, t))
    if t < 0.5:
        return 4 * t * t * t
    else:
        return 1 - pow(-2 * t + 2, 3) / 2
    
def find_icon_by_app_id(app_id, icon_list):
    """به صورت بازگشتی در لیست آیکونها (و پوشهها) به دنبال app_id میگردد."""
    for icon in icon_list:
        if icon.get('app_id') == app_id:
            return icon
        if icon.get('type') == 'folder':
            found_in_folder = find_icon_by_app_id(app_id, icon.get('contains', []))
            if found_in_folder:
                return found_in_folder
    return None

def draw_cc_slider(surface, rect, progress, icon_char, text_color):
    """(جدید) یک اسلایدر سفارشی برای مرکز کنترل رسم میکند."""
    bar_rect = rect.inflate(-40, -rect.height * 0.7)
    draw_rounded_rect(surface, bar_rect, (80, 80, 90) if is_dark_mode else (200, 200, 205), 8)
    
    progress_width = bar_rect.width * progress
    progress_rect = pygame.Rect(bar_rect.left, bar_rect.top, progress_width, bar_rect.height)
    draw_rounded_rect(surface, progress_rect, (255, 255, 255) if is_dark_mode else (80, 80, 80), 8)
    
    handle_pos = (bar_rect.left + progress_width, bar_rect.centery)
    pygame.draw.circle(surface, WHITE, handle_pos, 12)
    
    icon_font = mf(18)
    icon_surf = icon_font.render(icon_char, True, text_color)
    surface.blit(icon_surf, icon_surf.get_rect(center=(rect.left + 20, bar_rect.centery)))

def draw_cc_circular_toggle(surface, rect, button_data, text_color, alpha):
    """(جدید) یک دکمه تاگل دایرهای برای مرکز کنترل رسم میکند."""
    progress = button_data.get('color_progress', 0.0)
    base_color = (60, 60, 70) if is_dark_mode else (220, 220, 225)
    active_color = (50, 150, 255)
    
    current_color = tuple(int(b + (a - b) * progress) for b, a in zip(base_color, active_color))
    final_color = (*current_color, int(alpha * 0.9))
    
    pygame.draw.circle(surface, final_color, rect.center, rect.width // 2)
    
    icon_font = mf(20)
    icon_color = WHITE if is_dark_mode or progress > 0.5 else BLACK
    icon_surf = icon_font.render(button_data['icon'], True, icon_color)
    icon_surf.set_alpha(alpha)
    surface.blit(icon_surf, icon_surf.get_rect(center=rect.center))

    label_surf = render_persian_text(button_data['label'], status_bar_font, text_color)
    label_surf.set_alpha(alpha)
    surface.blit(label_surf, label_surf.get_rect(centerx=rect.centerx, top=rect.bottom + 8))
    
# (جدید) تابع برای بارگذاری صفحه وب در یک نخ جدا
def fetch_web_page_thread(url_to_load, result_key):
    global thread_results

    if not url_to_load.startswith(('http://', 'https://')):
        url = 'http://' + url_to_load
    else:
        url = url_to_load

    html_content, page_title = "<h3>خطا</h3><p>دریافت اطلاعات ممکن نشد.</p>", "خطا"
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=10) as response:
            charset = response.headers.get_content_charset() or 'utf-8'
            html = response.read().decode(charset, errors='ignore')
            thread_results[result_key] = {'status': 'success', 'html': html, 'final_url': url}
    except Exception as e:
        thread_results[result_key] = {'status': 'error', 'message': str(e)}
        
def parse_html_to_surfaces(html_content, max_width):
    if not beautifulsoup_available:
        text_content = re.sub(r'<.*?>', ' ', html_content)
        text_content = re.sub(r'\s+', ' ', text_content).strip()
        surf = text_font.render("BeautifulSoup not installed.", True, BLACK)
        return [{'surface': surf, 'href': None, 'type': 'text'}], surf.get_height()
        
    content_items = []
    total_height = 0
    
    fonts = { 'p': browser_content_font, 'h1': mf(22), 'h2': mf(20), 'h3': mf(18), 'a': browser_content_font, 'default': browser_content_font }
    colors = { 'default': get_current_color('settings_title'), 'a': BLUE }

    soup = BeautifulSoup(html_content, 'html.parser')

    for element in soup.find_all(['h1', 'h2', 'h3', 'p', 'a', 'img']):
        tag_name = element.name
        
        if tag_name == 'img':
            src = element.get('src')
            if src:
                try:
                    with urllib.request.urlopen(src, timeout=5) as img_response:
                        img_data = img_response.read()
                    img_file = io.BytesIO(img_data)
                    img_surf = pygame.image.load(img_file).convert_alpha()
                    
                    img_w, img_h = img_surf.get_size()
                    ratio = img_h / img_w if img_w > 0 else 0
                    new_w = max_width - 20
                    new_h = int(new_w * ratio)
                    scaled_img = pygame.transform.smoothscale(img_surf, (new_w, new_h))
                    
                    content_items.append({'surface': scaled_img, 'href': None, 'type': 'image'})
                    total_height += new_h + 10 # فاصله
                except Exception as e:
                    print(f"Could not load image {src}: {e}")
            continue

        text = element.get_text().strip()
        if not text:
            continue
            
        font = fonts.get(tag_name, fonts['default'])
        color = colors.get(tag_name, colors['default'])
        href = element.get('href') if tag_name == 'a' else None

        words = text.split(' ')
        line = ''
        for word in words:
            test_line = line + word + ' '
            if font.size(get_display(arabic_reshaper.reshape(test_line)))[0] < max_width:
                line = test_line
            else:
                line_surf = render_persian_text(line, font, color)
                content_items.append({'surface': line_surf, 'href': href, 'type': 'text'})
                total_height += line_surf.get_height()
                line = word + ' '
        if line:
            line_surf = render_persian_text(line, font, color)
            content_items.append({'surface': line_surf, 'href': href, 'type': 'text'})
            total_height += line_surf.get_height()

    return content_items, total_height

def install_prs_app(prs_path):
    """
    (نسخه اصلاح شده و نهایی)
    یک برنامه .prs را نصب یا بهروزرسانی میکند.
    برای برنامههای native نیازی به main_class نیست.
    """
    global is_installing_app, icons, dock_icons

    if is_installing_app:
        print("Another installation is already in progress.")
        add_unimportant_notification("نصب دیگری در حال انجام است")
        return

    # تابع داخلی برای اجرا در نخ
    def installer_thread():
        global is_installing_app, icons, dock_icons
        try:
            with zipfile.ZipFile(prs_path, 'r') as zip_ref:
                # خواندن مانیفست
                with zip_ref.open('manifest.json') as manifest_file:
                    manifest_data = json.load(manifest_file)

                app_id = manifest_data.get('id')
                app_name = manifest_data.get('name')
                main_file = manifest_data.get('main_file')
                # دریافت نوع برنامه (اگر نباشد پیشفرض integrated است)
                app_type = manifest_data.get('type', 'integrated') 
                main_class = manifest_data.get('main_class')

                # --- اصلاح شرط بررسی اعتبار ---
                # اگر برنامه integrated باشد، همه فیلدها از جمله main_class اجباری هستند.
                # اما اگر native باشد، فقط id, name و main_file کافیست.
                is_valid = False
                if app_type == 'native':
                    if all([app_id, app_name, main_file]):
                        is_valid = True
                elif app_type == 'remote':
                    if all([app_id, app_name, main_file]):  # main_file ورودی برنامه
                        is_valid = True
                else: # integrated
                    if all([app_id, app_name, main_file, main_class]):
                        is_valid = True

                if not is_valid:
                    print(f"Error: manifest.json missing fields for type '{app_type}'.")
                    add_unimportant_notification("نصب ناموفق: فایل مانیفست ناقص است")
                    return

                # --- (بخش کلیدی جدید: بررسی بهروزرسانی) ---
                existing_icon = None
                for page_icons in icons:
                    existing_icon = find_icon_by_app_id(app_id, page_icons)
                    if existing_icon: break
                if not existing_icon:
                    existing_icon = find_icon_by_app_id(app_id, dock_icons)
                
                # مقصد نصب
                install_path = os.path.join('installed_apps', app_id)
                os.makedirs(install_path, exist_ok=True)
                
                # استخراج فایلها
                zip_ref.extractall(install_path)

                if existing_icon:
                    # --- منطق بهروزرسانی ---
                    print(f"App '{app_id}' updating.")
                    existing_icon['name'] = app_name
                    
                    if app_id in running_app_instances:
                        kernel.kernel_instance.terminate_process(app_id)
                        if app_id in running_app_instances:
                            del running_app_instances[app_id]
                        print(f"Closed running instance of {app_id} for update.")

                    save_layout()
                    add_unimportant_notification(f"برنامه {app_name} بهروزرسانی شد")

                else:
                    # --- منطق نصب جدید ---
                    print(f"App '{app_id}' installing.")
                    found_slot = False
                    for page_idx in range(num_home_pages):
                        for r in range(rows_per_page):
                            for c in range(icons_per_row):
                                if is_grid_area_free(page_idx, r, c, 1, 1):
                                    new_icon = {
                                        'type': 'app', 'name': app_name, 'app_id': app_id,
                                        'page': page_idx, 'row': r, 'col': c,
                                        'rect': pygame.Rect(0,0,icon_size,icon_size), 'pos': [0,0]
                                    }
                                    icons[page_idx].append(new_icon)
                                    found_slot = True
                                    break
                            if found_slot: break
                        if found_slot: break

                    if not found_slot:
                        add_unimportant_notification("فضای خالی در صفحه اصلی نیست")
                        return

                    save_layout()
                    add_unimportant_notification(f"برنامه {app_name} نصب شد!")

        except Exception as e:
            print(f"Failed to install/update .PRS app: {e}")
            add_unimportant_notification(f"نصب/بهروزرسانی ناموفق: {e}")
        finally:
            is_installing_app = False

    # شروع نخ نصب/بهروزرسانی
    is_installing_app = True
    add_unimportant_notification("در حال بررسی بسته برنامه...")
    thread = threading.Thread(target=installer_thread)
    thread.start()
        
def render_persian_text(text, font, color, is_note=False):
    if is_note:
        if not text: return []
        lines, surfaces = text.split('\n'), []
        for line in lines: surfaces.append(font.render(get_display(arabic_reshaper.reshape(line)), True, color))
        return surfaces
    if not text: return font.render("", True, color)
    return font.render(get_display(arabic_reshaper.reshape(text)), True, color)

notes_app = NotesApp(sc, mf, get_current_color, render_persian_text)

def draw_gradient_background(surface, top_color, bottom_color):
    height = surface.get_height()
    for y in range(height):
        ratio = y / height
        r = int(top_color[0] * (1 - ratio) + bottom_color[0] * ratio)
        g = int(top_color[1] * (1 - ratio) + bottom_color[1] * ratio)
        b = int(top_color[2] * (1 - ratio) + bottom_color[2] * ratio)
        pygame.draw.line(surface, (r, g, b), (0, y), (surface.get_width(), y))

def draw_main_background(surface):
    if current_wallpaper_image:
        surface.blit(current_wallpaper_image, (0, 0))
    else:
        # همیشه گرادیان انتخابی کاربر نمایش داده شود، حتی در حالت تاریک
        draw_gradient_background(surface, saved_light_wallpaper_top, saved_light_wallpaper_bottom)

def draw_rounded_rect(surface, rect, color, corner_radius):
    if corner_radius < 0: corner_radius = 0
    if rect.width < 2 * corner_radius or rect.height < 2 * corner_radius:
        # اگر شعاع بزرگتر از نصف عرض یا ارتفاع باشد، مستطیل معمولی رسم کن
        if rect.width < 2 * corner_radius: corner_radius = rect.width / 2
        if rect.height < 2 * corner_radius: corner_radius = rect.height / 2
    
    # اطمینان از اینکه شعاع یک عدد صحیح است
    corner_radius = int(corner_radius)

    # رسم چهار دایره در گوشهها
    pygame.draw.circle(surface, color, (rect.left + corner_radius, rect.top + corner_radius), corner_radius)
    pygame.draw.circle(surface, color, (rect.right - corner_radius - 1, rect.top + corner_radius), corner_radius)
    pygame.draw.circle(surface, color, (rect.left + corner_radius, rect.bottom - corner_radius - 1), corner_radius)
    pygame.draw.circle(surface, color, (rect.right - corner_radius - 1, rect.bottom - corner_radius - 1), corner_radius)

    # رسم دو مستطیل برای پر کردن فضای بین دایرهها
    pygame.draw.rect(surface, color, rect.inflate(-2 * corner_radius, 0))
    pygame.draw.rect(surface, color, rect.inflate(0, -2 * corner_radius))


def get_icon_at_pos(pos, icon_list):
    for icon in icon_list:
        if icon['rect'].collidepoint(pos): return icon
    return None

def get_grid_pos(pos, item_being_dragged=None):
    # (جدید) اگر آیتمی در حال جابجایی است، اندازه آن را در نظر میگیریم
    item_w, item_h = 1, 1 # اندازه پیشفرض در واحد گرید
    if item_being_dragged and item_being_dragged.get('type') == 'widget':
        item_w, item_h = item_being_dragged.get('size', (1,1))

    start_x = (SCREEN_WIDTH - (icons_per_row * icon_size + (icons_per_row - 1) * icon_padding)) / 2
    start_y = 60
    col = (pos[0] - start_x + icon_padding/2) // (icon_size + icon_padding)
    row = (pos[1] - start_y + icon_padding/2) // (icon_size + icon_padding)

    # اطمینان حاصل شود که ویجت از صفحه خارج نمیشود
    final_row = max(0, min(rows_per_page - item_h, int(row)))
    final_col = max(0, min(icons_per_row - item_w, int(col)))

    return int(final_row), int(final_col)

def apply_gaussian_blur(surface, iterations=18, scale_factor=5):
    """Gaussian blur چندمرحله‌ای نرم - iterations بیشتر = مات‌تر"""
    width, height = surface.get_size()
    if width < 1 or height < 1:
        return surface
    result = surface.copy()
    for i in range(iterations):
        factor = scale_factor + (i % 3)
        sw = max(1, width // factor)
        sh = max(1, height // factor)
        small = pygame.transform.smoothscale(result, (sw, sh))
        result = pygame.transform.smoothscale(small, (width, height))
    return result

def create_charging_particle():
    side = random.randint(0, 3)
    if side == 0: pos = [random.randint(0, SCREEN_WIDTH), -10]
    elif side == 1: pos = [SCREEN_WIDTH + 10, random.randint(0, SCREEN_HEIGHT)]
    elif side == 2: pos = [random.randint(0, SCREEN_WIDTH), SCREEN_HEIGHT + 10]
    else: pos = [-10, random.randint(0, SCREEN_HEIGHT)]
    return {'pos': pos, 'radius': random.randint(3, 10), 'speed': random.uniform(1.5, 3.5)}

def start_music_transition(direction):
    """آماده‌سازی ترانزیشن بین دو آهنگ"""
    global music_transition, current_track_index, music_track_name, current_album_art_surface
    global cached_blurred_bg, last_played_track_name, music_art_scale, target_music_art_scale
    global music_playback_start_time_offset   # <-- اضافه شد

    if music_transition['active']:
        return

    if not music_playlist:
        return

    # ذخیره اطلاعات آهنگ فعلی
    music_transition['old_art'] = current_album_art_surface
    music_transition['old_track_name'] = music_track_name
    music_transition['old_track_index'] = current_track_index
    music_transition['direction'] = direction

    # تعیین آهنگ جدید
    new_index = current_track_index
    if direction == 1:   # next
        if music_repeat == 2:
            new_index = current_track_index
        elif music_shuffle:
            new_index = random.randint(0, len(music_playlist)-1)
        else:
            new_index = (current_track_index + 1) % len(music_playlist)
    else:                # prev
        if music_repeat == 2:
            new_index = current_track_index
        elif music_shuffle:
            new_index = random.randint(0, len(music_playlist)-1)
        else:
            new_index = (current_track_index - 1 + len(music_playlist)) % len(music_playlist)

    if new_index == current_track_index and not (direction == 1 and music_repeat == 2):
        return

    music_transition['new_track_index'] = new_index
    music_transition['new_track_name'] = os.path.basename(music_playlist[new_index])

    new_length, new_art = get_track_info(music_playlist[new_index])
    music_transition['new_art'] = new_art

    # تغییر پخش صدا
    pygame.mixer.music.load(music_playlist[new_index])
    pygame.mixer.music.play()
    current_track_length = new_length
    current_album_art_surface = new_art
    music_track_name = music_transition['new_track_name']
    music_playback_start_time_offset = 0.0   # ریست offset
    cached_blurred_bg = None

    # شروع انیمیشن
    music_transition['active'] = True
    music_transition['progress'] = 0.0
    music_transition['start_time'] = time.time()
    target_music_art_scale = 1.0
    music_art_scale = 1.0

def play_next_song():
    global current_track_index, is_music_playing, is_music_paused
    global current_track_length, current_album_art_surface, music_playback_start_time_offset
    global cached_blurred_bg
    if not music_playlist:
        return
    start_music_transition(1)

def play_previous_song():
    global current_track_index, music_track_name, is_music_playing, is_music_paused
    global current_track_length, current_album_art_surface, music_playback_start_time_offset
    global cached_blurred_bg
    if not music_playlist:
        return
    # محاسبه موقعیت فعلی آهنگ
    current_pos = music_playback_start_time_offset + pygame.mixer.music.get_pos() / 1000.0
    if current_pos > 3.0:
        pygame.mixer.music.play(start=0)
        music_playback_start_time_offset = 0
        return
    start_music_transition(-1)

def toggle_music_play_pause():
    """تغییر وضعیت پخش/توقف موسیقی"""
    global is_music_playing, is_music_paused, music_playback_start_time_offset
    if not music_playlist:
        return
    if is_music_playing:
        pygame.mixer.music.pause()
        is_music_paused = True
        is_music_playing = False
    elif is_music_paused:
        pygame.mixer.music.unpause()
        is_music_paused = False
        is_music_playing = True
    else:
        # حالت توقف کامل (هیچ چیزی پخش نمی‌شود)
        pygame.mixer.music.play()
        music_playback_start_time_offset = 0
        is_music_playing = True
        is_music_paused = False

# -----------------------------------
#      توابع رسم صفحات و عناصر
# -----------------------------------
def draw_superisland(surface):
    global superisland_state, superisland_anim_progress, superisland_expand_progress
    global is_music_playing, is_music_paused, music_track_name

    if not is_superisland_enabled:
        return {}

    has_media = (is_music_playing or is_music_paused) and music_playlist

    # منطق ماشین وضعیت (State Machine)
    if has_media and superisland_state == 'hidden':
        superisland_state = 'capsule'
    elif not has_media and superisland_state != 'hidden' and superisland_state != 'expanded':
        superisland_state = 'hidden'

    # پیشرفت انیمیشن‌ها
    target_anim = 1.0 if superisland_state != 'hidden' else 0.0
    superisland_anim_progress += (target_anim - superisland_anim_progress) * 0.15
    
    target_expand = 1.0 if superisland_state == 'expanded' else 0.0
    superisland_expand_progress += (target_expand - superisland_expand_progress) * 0.18

    if superisland_anim_progress < 0.01:
        return {}

    # ابعاد پایه کپسول و مستطیل
    cap_w, cap_h = 120, 34
    exp_w, exp_h = SCREEN_WIDTH - 24, 180
    
    # ابعاد فعلی بر اساس پیشرفت انیمیشن
    current_w = cap_w + (exp_w - cap_w) * superisland_expand_progress
    current_h = cap_h + (exp_h - cap_h) * superisland_expand_progress
    
    # موقعیت (انیمیشن پایین آمدن نرم)
    y_offset = -50 * (1 - superisland_anim_progress)
    island_rect = pygame.Rect(0, 0, current_w, current_h)
    island_rect.centerx = SCREEN_WIDTH / 2
    island_rect.top = 10 + y_offset

    # رسم بدنه مشکی جزیره
    island_surf = pygame.Surface((current_w, current_h), pygame.SRCALPHA)
    radius = int(min(current_h / 2, 35 - 10 * superisland_expand_progress))
    draw_rounded_rect(island_surf, island_surf.get_rect(), (0, 0, 0), radius)

    buttons = {'si_main': island_rect}

    if has_media:
        # ---- حالت کپسول (Capsule Mode) ----
        if superisland_expand_progress < 0.5:
            alpha = int((1 - superisland_expand_progress * 2) * 255)
            # کاور کوچک سمت چپ
            if current_album_art_surface:
                art_small = pygame.transform.smoothscale(current_album_art_surface, (24, 24))
                art_surf = pygame.Surface((24, 24), pygame.SRCALPHA)
                draw_rounded_rect(art_surf, art_surf.get_rect(), (255, 255, 255), 6)
                art_surf.blit(art_small, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)
                art_surf.set_alpha(alpha)
                island_surf.blit(art_surf, (8, 5))
            
            # اکولایزر یا متن کوچک
            if is_music_playing:
                # انیمیشن ساده اکولایزر
                for i in range(3):
                    h = 4 + abs(math.sin(time.time() * 5 + i)) * 10
                    eq_rect = pygame.Rect(current_w - 25 + i * 5, 17 - h/2, 3, h)
                    s = pygame.Surface((3, h), pygame.SRCALPHA)
                    s.fill((255, 255, 255, alpha))
                    island_surf.blit(s, eq_rect.topleft)

        # ---- حالت گسترش‌یافته (Expanded Mode) ----
        if superisland_expand_progress > 0.2:
            alpha = int(((superisland_expand_progress - 0.2) / 0.8) * 255)
            text_col = (255, 255, 255, alpha)
            
            # کاور آلبوم بزرگ
            art_size = 60
            if current_album_art_surface:
                art_big = pygame.transform.smoothscale(current_album_art_surface, (art_size, art_size))
                art_surf_b = pygame.Surface((art_size, art_size), pygame.SRCALPHA)
                draw_rounded_rect(art_surf_b, art_surf_b.get_rect(), (255, 255, 255), 12)
                art_surf_b.blit(art_big, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)
                art_surf_b.set_alpha(alpha)
                island_surf.blit(art_surf_b, (20, 20))
            
            # نام آهنگ
            track_name = os.path.splitext(music_track_name)[0]
            if len(track_name) > 20: track_name = track_name[:17] + "..."
            t_font = mf(16)
            name_s = render_persian_text(track_name, t_font, WHITE)
            name_s.set_alpha(alpha)
            island_surf.blit(name_s, (95, 25))
            
            # دکمه‌های کنترل
            btn_y = current_h - 45
            center_x = current_w / 2
            
            # استایل مدرن دکمه‌ها
            btn_size = 38
            btn_radius = btn_size // 2
            bg_col = (255, 255, 255, int(alpha * 0.15))
            
            # دکمه قبلی
            prev_rect = pygame.Rect(center_x - 65, btn_y, btn_size, btn_size)
            pygame.draw.circle(island_surf, bg_col, prev_rect.center, btn_radius)
            pygame.draw.polygon(island_surf, text_col, [(prev_rect.centerx + 4, prev_rect.centery - 8), (prev_rect.centerx + 4, prev_rect.centery + 8), (prev_rect.centerx - 6, prev_rect.centery)])
            pygame.draw.rect(island_surf, text_col, (prev_rect.centerx - 8, prev_rect.centery - 8, 3, 16), border_radius=1)
            buttons['si_prev'] = prev_rect.move(island_rect.topleft)
            
            # دکمه پخش/توقف
            play_rect = pygame.Rect(center_x - 19, btn_y, btn_size, btn_size)
            pygame.draw.circle(island_surf, bg_col, play_rect.center, btn_radius)
            if is_music_playing:
                pygame.draw.rect(island_surf, text_col, (play_rect.centerx - 6, play_rect.centery - 8, 4, 16), border_radius=1)
                pygame.draw.rect(island_surf, text_col, (play_rect.centerx + 2, play_rect.centery - 8, 4, 16), border_radius=1)
            else:
                pygame.draw.polygon(island_surf, text_col, [(play_rect.centerx - 4, play_rect.centery - 9), (play_rect.centerx - 4, play_rect.centery + 9), (play_rect.centerx + 7, play_rect.centery)])
            buttons['si_play'] = play_rect.move(island_rect.topleft)
            
            # دکمه بعدی
            next_rect = pygame.Rect(center_x + 27, btn_y, btn_size, btn_size)
            pygame.draw.circle(island_surf, bg_col, next_rect.center, btn_radius)
            pygame.draw.polygon(island_surf, text_col, [(next_rect.centerx - 4, next_rect.centery - 8), (next_rect.centerx - 4, next_rect.centery + 8), (next_rect.centerx + 6, next_rect.centery)])
            pygame.draw.rect(island_surf, text_col, (next_rect.centerx + 5, next_rect.centery - 8, 3, 16), border_radius=1)
            buttons['si_next'] = next_rect.move(island_rect.topleft)

    surface.blit(island_surf, island_rect.topleft)
    return buttons
# (جدید) تابع رسم ویجت ساعت
def draw_clock_widget(surface, rect):
    """ویجت ساعت آنالوگ را مطابق با نمونه تصویر، روی سطح ورودی رسم میکند."""
    # رسم پسزمینه سفید با گوشههای گرد
    draw_rounded_rect(surface, surface.get_rect(), (255, 255, 255), 22)

    center = rect.centerx, rect.centery
    radius = min(rect.width, rect.height) / 2 * 0.85

    # رسم نقطههای ساعت
    for i in range(60):
        angle = math.radians(i * 6 - 90)
        start_radius = radius * 0.95
        end_radius = radius
        if i % 5 == 0: # نقطههای مربوط به ساعتها ضخیمتر هستند
             start_radius = radius * 0.88

        start_pos = (center[0] + start_radius * math.cos(angle), center[1] + start_radius * math.sin(angle))
        end_pos = (center[0] + end_radius * math.cos(angle), center[1] + end_radius * math.sin(angle))
        pygame.draw.line(surface, CLOCK_WIDGET_TICKS, start_pos, end_pos, 2)

    # گرفتن زمان فعلی
    now = datetime.datetime.now()
    hour = now.hour % 12 + now.minute / 60
    minute = now.minute + now.second / 60
    second = now.second

    # محاسبه زاویه عقربهها
    hour_angle = math.radians(hour * 30 - 90)
    minute_angle = math.radians(minute * 6 - 90)
    second_angle = math.radians(second * 6 - 90)

    # رسم عقربهها
    # عقربه ساعت
    hour_len = radius * 0.5
    hour_end = (center[0] + hour_len * math.cos(hour_angle), center[1] + hour_len * math.sin(hour_angle))
    pygame.draw.line(surface, CLOCK_WIDGET_HAND_HOUR, center, hour_end, 6)

    # عقربه دقیقه
    minute_len = radius * 0.75
    minute_end = (center[0] + minute_len * math.cos(minute_angle), center[1] + minute_len * math.sin(minute_angle))
    pygame.draw.line(surface, CLOCK_WIDGET_HAND_MINUTE, center, minute_end, 5)

    # عقربه ثانیه
    second_len = radius * 0.8
    second_end = (center[0] + second_len * math.cos(second_angle), center[1] + second_len * math.sin(second_angle))
    pygame.draw.line(surface, CLOCK_WIDGET_HAND_SECOND, center, second_end, 3)

    # دایره مرکزی
    pygame.draw.circle(surface, BLACK, center, 8)
    pygame.draw.circle(surface, GRAY, center, 5)

# (جدید) تابع کمکی برای بررسی فضای خالی در گرید
def is_grid_area_free(page, start_row, start_col, width, height, ignored_item=None):
    """بررسی میکند که آیا یک ناحیه مشخص در گرید صفحه اصلی خالی است یا خیر."""
    for r in range(start_row, start_row + height):
        for c in range(start_col, start_col + width):
            for item in icons[page]:
                if item == ignored_item:
                    continue

                item_w, item_h = (1,1)
                if item.get('type') == 'widget':
                    item_w, item_h = item.get('size', (1,1))

                # بررسی تداخل (Collision)
                item_start_row, item_start_col = item.get('row'), item.get('col')
                if (item_start_col < c + 1 and item_start_col + item_w > c and
                    item_start_row < r + 1 and item_start_row + item_h > r):
                    return False # فضا اشغال است
    return True

# (جدید) تابع افزودن اعلان اصلی به مرکز اعلانات
def add_main_notification(app_name, title, text, icon_name=None):
    global active_heads_up_notification
    
    new_notif = {
        'app_name': app_name, 'title': title, 'text': text,
        'icon_name': icon_name if icon_name else app_name,
        'timestamp': time.time(),
        'y_offset': -80, 'alpha': 0.0,
        'state': 'entering',
        'anim_start_time': time.time(), # (جدید) زمان شروع انیمیشن
        'anim_duration': 0.6, # (جدید) مدت زمان انیمیشن
    }
    main_notifications.insert(0, new_notif)
    
    if not is_notification_center_open:
        if active_heads_up_notification and active_heads_up_notification['state'] != 'exiting':
            active_heads_up_notification['state'] = 'exiting'
            active_heads_up_notification['anim_start_time'] = time.time() # ریست انیمیشن خروج
        active_heads_up_notification = new_notif
        
# (نام جدید) تابع افزودن اعلان غیرمهم
def add_unimportant_notification(text):
    """یک اعلان متنی غیرمهم به پایین صفحه اضافه میکند."""
    # (جدید) اضافه کردن scale برای انیمیشن بزرگ شدن
    unimportant_notifications.append({
        'text': text,
        'timestamp': time.time(),
        'alpha': 0.0,
        'scale': 0.8, # شروع از مقیاس کوچک
        'state': 'entering' # وضعیت برای کنترل انیمیشن
    })

def download_file(url):
    """فایل را از URL داده شده دانلود و در پوشه downloads ذخیره میکند."""
    filename = "download.tmp"
    try:
        # استخراج یک نام فایل ساده از URL
        filename = os.path.basename(url.split('?')[0])
        if not filename:
            filename = f"download_{int(time.time())}.file"
        
        save_path = os.path.join('downloads', filename)
        
        add_unimportant_notification(f"در حال دانلود {filename}...")
        
        # دانلود فایل
        urllib.request.urlretrieve(url, save_path)
        
        # حذف اعلان "در حال دانلود" و جایگزینی آن با پیام موفقیت
        for n in unimportant_notifications[:]:
            if n['text'] == f"در حال دانلود {filename}...":
                unimportant_notifications.remove(n)
                break
        add_unimportant_notification(f"فایل {filename} دانلود شد!")

    except Exception as e:
        print(f"Error downloading {url}: {e}")
        add_unimportant_notification(f"دانلود ناموفق: {filename}")

# (جدید) تابع رسم اعلانها روی صفحه
def draw_unimportant_notifications(surface):
    """اعلانهای غیرمهم را با انیمیشن نرم شفافیت و اندازه رسم میکند."""
    y_offset = SCREEN_HEIGHT - sc(60)
    for notification in unimportant_notifications[:]:
        # (اصلاح شده) مدیریت انیمیشن ورود، نمایش و خروج
        if notification['state'] == 'entering':
            notification['alpha'] += 25
            notification['scale'] += 0.02
            if notification['alpha'] >= 255:
                notification['alpha'] = 255
                notification['scale'] = 1.0
                notification['state'] = 'visible'
                notification['timestamp'] = time.time() # تایمر از اینجا شروع میشود
        elif notification['state'] == 'visible':
            if time.time() - notification['timestamp'] > 3:
                notification['state'] = 'exiting'
        elif notification['state'] == 'exiting':
            notification['alpha'] -= 15
            notification['scale'] -= 0.01

        if notification['alpha'] <= 0 and notification['state'] == 'exiting':
            unimportant_notifications.remove(notification)
            continue

        text_surf = render_persian_text(notification['text'], text_font, WHITE)
        
        # محاسبه ابعاد بر اساس مقیاس انیمیشن
        base_width = text_surf.get_width() + 30
        base_height = text_surf.get_height() + 20
        current_width = int(base_width * notification['scale'])
        current_height = int(base_height * notification['scale'])

        bg_rect = pygame.Rect(0, 0, current_width, current_height)
        bg_rect.centerx = surface.get_width() / 2
        bg_rect.bottom = y_offset

        bg_surf = pygame.Surface(bg_rect.size, pygame.SRCALPHA)
        # شعاع گوشه نیز باید متناسب با مقیاس باشد
        draw_rounded_rect(bg_surf, bg_surf.get_rect(), (0, 0, 0, 180), 15 * notification['scale'])

        # تغییر اندازه متن متناسب با پسزمینه
        scaled_text_surf = pygame.transform.smoothscale(text_surf, (int(text_surf.get_width() * notification['scale']), int(text_surf.get_height() * notification['scale'])))

        alpha = max(0, min(255, notification['alpha']))
        bg_surf.set_alpha(alpha)
        scaled_text_surf.set_alpha(alpha)

        surface.blit(bg_surf, bg_rect)
        surface.blit(scaled_text_surf, scaled_text_surf.get_rect(center=bg_rect.center))

        y_offset -= bg_rect.height + 10
        
# (جدید) تابع رسم یک کارت اعلان (برای مرکز اعلانات و heads-up)
def draw_notification_card(surface, rect, notification_data, alpha=255):
    """یک کارت اعلان با شمایل تصویر نمونه را رسم میکند."""
    card_surface = pygame.Surface(rect.size, pygame.SRCALPHA)
    
    bg_color = (255, 255, 255, int(220 * (alpha/255))) if not is_dark_mode else (40, 40, 50, int(220 * (alpha/255)))
    draw_rounded_rect(card_surface, card_surface.get_rect(), bg_color, 20)
    
    icon_rect = pygame.Rect(15, 15, 30, 30)
    # (اصلاح شده) ایجاد سطح با کانال آلفا برای جلوگیری از گوشههای سیاه
    icon_surf = pygame.Surface((icon_size, icon_size), pygame.SRCALPHA)
    
    if notification_data['icon_name'] == 'settings':
        draw_settings_icon(icon_surf, icon_surf.get_rect())
    elif notification_data['icon_name'] == 'notes':
        draw_notes_icon(icon_surf, icon_surf.get_rect())
    else:
        draw_gradient_background(icon_surf, GRAY, DARK_GRAY)

    scaled_icon = pygame.transform.smoothscale(icon_surf, icon_rect.size)
    icon_mask = pygame.Surface(icon_rect.size, pygame.SRCALPHA)
    draw_rounded_rect(icon_mask, icon_mask.get_rect(), (255,255,255,255), 8)
    scaled_icon.blit(icon_mask, (0,0), special_flags=pygame.BLEND_RGBA_MULT)
    card_surface.blit(scaled_icon, icon_rect.topleft)

    text_color = get_current_color('settings_title')
    title_surf = render_persian_text(notification_data['title'], text_font, text_color)
    text_surf = render_persian_text(notification_data['text'], status_bar_font, GRAY if not is_dark_mode else LIGHT_GRAY)
    
    card_surface.blit(title_surf, title_surf.get_rect(top=icon_rect.top, left=icon_rect.right + 10))
    card_surface.blit(text_surf, text_surf.get_rect(top=title_surf.get_rect().bottom + 5, left=icon_rect.right + 10))
    
    card_surface.set_alpha(alpha)
    surface.blit(card_surface, rect.topleft)

# (جدید) تابع رسم مرکز اعلانات
def draw_notification_center(surface, progress):
    if progress <= 0: return

    # (اصلاح شده) دیگر در هر فریم بلور نمیکنیم
    if notification_center_snapshot:
        # فقط آلفای تصویر از قبل بلور شده را بر اساس پیشرفت انیمیشن تنظیم میکنیم
        notification_center_snapshot.set_alpha(int(progress * 255))
        surface.blit(notification_center_snapshot, (0, 0))

    ease_progress = 1 - (1 - progress) ** 4
    start_width, start_height = sc(50), sc(50)
    end_width, end_height = SCREEN_WIDTH - sc(20), SCREEN_HEIGHT - sc(100)
    current_width = start_width + (end_width - start_width) * ease_progress
    current_height = start_height + (end_height - start_height) * ease_progress
    end_x, end_y = sc(10), sc(50)
    start_x, start_y = sc(10), sc(10) # شروع از چپ
    current_x = start_x + (end_x - start_x) * ease_progress
    current_y = start_y + (end_y - start_y) * ease_progress

    nc_rect = pygame.Rect(current_x, current_y, current_width, current_height)

    nc_surface = pygame.Surface(nc_rect.size, pygame.SRCALPHA)

    if ease_progress > 0.8:
        content_alpha = (ease_progress - 0.8) / 0.2 * 255

        y_pos = 15
        for notif in main_notifications:
            card_height = 80
            card_rect = pygame.Rect(15, y_pos, nc_rect.width - 30, card_height)
            if card_rect.bottom < nc_rect.height:
                 draw_notification_card(nc_surface, card_rect, notif, alpha=content_alpha)
            y_pos += card_height + 10

    surface.blit(nc_surface, nc_rect.topleft)

# (جدید) تابع رسم اعلان heads-up
def draw_heads_up_notification(surface):
    global active_heads_up_notification
    if not active_heads_up_notification:
        return

    notif = active_heads_up_notification
    card_width, card_height = SCREEN_WIDTH - sc(20), sc(80)
    card_rect = pygame.Rect(sc(10), notif['y_offset'], card_width, card_height)
    
    draw_notification_card(surface, card_rect, notif, alpha=notif['alpha'])

def draw_3d_effect_button(surface, base_rect, color, radius, button_data, container_rect):
    """
    (نسخه نهایی و اصلاح شده) یک دکمه با افکت سهبعدی و گوشههای گرد نرم رسم میکند.
    این نسخه با اصلاح ترتیب رأسهای چندضلعی، مشکل نمایش دایرههای گوشه را برطرف میکند.
    """
    if button_data['press_anim_progress'] < 0.01 or button_data['press_location'] is None:
        draw_rounded_rect(surface, base_rect, color, radius)
        return

    progress = button_data['press_anim_progress']
    click_pos_abs = pygame.Vector2(button_data['press_location'])
    click_pos_relative = click_pos_abs - pygame.Vector2(container_rect.topleft)
    rect_center = pygame.Vector2(base_rect.center)

    # (اصلاح شده) تعریف گوشهها در یک لیست برای تضمین ترتیب
    corner_points = [
        pygame.Vector2(base_rect.topleft), pygame.Vector2(base_rect.topright),
        pygame.Vector2(base_rect.bottomright), pygame.Vector2(base_rect.bottomleft)
    ]
    corner_names = ['topleft', 'topright', 'bottomright', 'bottomleft']

    # پیدا کردن نزدیکترین گوشه به محل کلیک
    distances = [click_pos_relative.distance_to(p) for p in corner_points]
    closest_corner_index = distances.index(min(distances))

    # محاسبه موقعیت جدید هر گوشه
    poly_points = []
    max_offset = 8
    for i, point in enumerate(corner_points):
        if i == closest_corner_index:
            offset_vector = (rect_center - point)
            if offset_vector.length() > 0:
                offset_vector.scale_to_length(max_offset * progress)
            moved_point = point + offset_vector
            poly_points.append(moved_point)
        else:
            poly_points.append(point)

    # ۱. رسم چهار دایره در گوشههای تغییرشکلیافته
    for p in poly_points:
        pygame.draw.circle(surface, color, (int(p.x), int(p.y)), int(radius))

    # ۲. رسم دو چندضلعی متقاطع برای پوشاندن فضای بین دایرهها
    # (اصلاح شده) ترتیب صحیح رأسها برای جلوگیری از پیچخوردگی چندضلعی
    tl, tr, br, bl = poly_points[0], poly_points[1], poly_points[2], poly_points[3]

    def get_normalized_vector(p1, p2):
        vec = p2 - p1
        return vec.normalize() if vec.length() > 0 else pygame.Vector2(0, 0)

    # چندضلعی عمودی (برای پر کردن فضای بین بالا و پایین)
    top_edge_vec = get_normalized_vector(tl, tr)
    bottom_edge_vec = get_normalized_vector(bl, br)
    p1_v = tl + top_edge_vec * radius
    p2_v = tr - top_edge_vec * radius
    p3_v = br - bottom_edge_vec * radius
    p4_v = bl + bottom_edge_vec * radius
    pygame.draw.polygon(surface, color, [p1_v, p2_v, p3_v, p4_v])

    # چندضلعی افقی (برای پر کردن فضای بین چپ و راست)
    left_edge_vec = get_normalized_vector(tl, bl)
    right_edge_vec = get_normalized_vector(tr, br)
    p1_h = tl + left_edge_vec * radius
    p2_h = tr + right_edge_vec * radius
    p3_h = br - right_edge_vec * radius
    p4_h = bl - left_edge_vec * radius
    pygame.draw.polygon(surface, color, [p1_h, p2_h, p3_h, p4_h])
        
def draw_installed_app_screen(surface):
    """ (جدید) این تابع یک صفحه عمومی برای برنامههای نصب شده از طریق .prs را رسم میکند """
    surface.fill(get_current_color('settings_bg'))
    text_color = get_current_color('settings_title')
    
    app_id = app_context.get('app_id', 'N/A')
    app_name = app_context.get('app_name', 'برنامه ناشناس')
    
    # خواندن اطلاعات بیشتر از manifest.json برنامه
    app_path = os.path.join('installed_apps', app_id)
    manifest_path = os.path.join(app_path, 'manifest.json')
    app_info_text = f"نام: {app_name}\nشناسه: {app_id}"
    
    try:
        with open(manifest_path, 'r', encoding='utf-8') as f:
            manifest = json.load(f)
            version = manifest.get('version', 'نامشخص')
            author = manifest.get('author', 'نامشخص')
            app_info_text += f"\nنسخه: {version}\nسازنده: {author}"
    except (FileNotFoundError, json.JSONDecodeError):
        app_info_text += "\n\nفایل manifest.json یافت نشد."

    title = render_persian_text(app_name, settings_title_font, text_color)
    surface.blit(title, title.get_rect(centerx=surface.get_width()/2, top=50))
    
    info_surfaces = render_persian_text(app_info_text, text_font, text_color, is_note=True)
    y = 120
    for line_surf in info_surfaces:
        surface.blit(line_surf, line_surf.get_rect(centerx=surface.get_width()/2, top=y))
        y += line_surf.get_height() + 10
        
# (جدید) تابع کمکی برای اسکن یک پوشه
def scan_directory(path):
    items = []
    try:
        entries = os.listdir(path)
        for name in entries:
            full_path = os.path.join(path, name)
            if name.startswith('.'):
                continue

            size_str = "-"
            date_str = "-"
            raw_size = 0
            try:
                stats = os.stat(full_path)
                sz = stats.st_size
                if sz < 1024:
                    size_str = f"{sz} B"
                elif sz < 1024**2:
                    size_str = f"{sz/1024:.1f} KB"
                else:
                    size_str = f"{sz/(1024**2):.1f} MB"
                date_str = datetime.datetime.fromtimestamp(stats.st_mtime).strftime('%Y/%m/%d')
                raw_size = stats.st_size
            except:
                pass

            if os.path.isdir(full_path):
                items.append({
                    'name': name,
                    'type': 'dir',
                    'path': full_path,
                    'size': 'Folder',
                    'date': date_str,
                    'raw_size': 0,
                    'name_surf': None,   # برای کش سطح نام
                    'meta_surf': None    # برای کش سطح متادیتا
                })
            else:
                ext = name.split('.')[-1].lower() if '.' in name else ''
                if ext in ['txt', 'md', 'py', 'json']:
                    f_type = 'text'
                elif ext == 'prs':
                    f_type = 'app_package'
                elif ext in ['mp3', 'wav', 'ogg']:
                    f_type = 'music'
                elif ext in ['png', 'jpg', 'jpeg', 'bmp']:
                    f_type = 'image'
                else:
                    f_type = 'file'
                items.append({
                    'name': name,
                    'type': f_type,
                    'path': full_path,
                    'size': size_str,
                    'date': date_str,
                    'raw_size': raw_size,
                    'name_surf': None,
                    'meta_surf': None
                })

        # مرتب‌سازی: اول پوشه‌ها، سپس فایل‌ها
        items.sort(key=lambda x: (x['type'] != 'dir', x['name'].lower()))

    except Exception as e:
        print(f"Error scanning directory {path}: {e}")
        items.append({
            'name': "Error",
            'type': 'error',
            'path': '',
            'size': '-',
            'date': '-',
            'name_surf': None,
            'meta_surf': None
        })
    return items

# (جدید) تابع اصلی برای رسم صفحه برنامه فایلها
import threading
import json as _json

# =====================================================
# =====================================================
# --- پیام‌رسان شبکه محلی با شناسه تلفن ---
# =====================================================
import socket as _socket

MESSENGER_PORT   = 55789
_messenger_sock  = None          # سوکت UDP دریافت
_messenger_my_phone = ""         # شماره تلفن این دستگاه

# فایل ذخیره مخاطبین و پیام‌ها
MESSENGER_DATA_FILE = "messenger_data.json"

def _messenger_load_data():
    """بارگذاری مخاطبین و مکالمات از فایل"""
    global messenger_contacts, messenger_conversations, _messenger_my_phone
    try:
        if os.path.exists(MESSENGER_DATA_FILE):
            with open(MESSENGER_DATA_FILE, 'r', encoding='utf-8') as f:
                data = _json.load(f)
            messenger_contacts = data.get('contacts', [])
            messenger_conversations = data.get('conversations', {})
            _messenger_my_phone = data.get('my_phone', "")
    except Exception as e:
        print(f"Messenger load error: {e}")

def _messenger_save_data():
    """ذخیره مخاطبین و مکالمات در فایل"""
    try:
        data = {
            'contacts': messenger_contacts,
            'conversations': messenger_conversations,
            'my_phone': _messenger_my_phone,
        }
        with open(MESSENGER_DATA_FILE, 'w', encoding='utf-8') as f:
            _json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"Messenger save error: {e}")

def messenger_get_local_ip():
    """پیدا کردن IP محلی"""
    try:
        s = _socket.socket(_socket.AF_INET, _socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except:
        return "127.0.0.1"

def messenger_start_server():
    """شروع سرور UDP برای دریافت پیام"""
    global _messenger_sock
    if _messenger_sock is not None:
        return
    try:
        sock = _socket.socket(_socket.AF_INET, _socket.SOCK_DGRAM)
        sock.setsockopt(_socket.SOL_SOCKET, _socket.SO_REUSEADDR, 1)
        sock.bind(("", MESSENGER_PORT))
        sock.settimeout(1.0)
        _messenger_sock = sock

        def _listen():
            global messenger_conversations, messenger_contacts, messenger_notification_badge
            while _messenger_sock is not None:
                try:
                    data, addr = sock.recvfrom(8192)
                    msg = _json.loads(data.decode('utf-8'))
                    sender_phone = msg.get('phone', addr[0])
                    sender_name  = msg.get('name',  sender_phone)
                    text = msg.get('text', '')
                    ts   = msg.get('time', time.strftime('%H:%M'))
                    if not text:
                        continue
                    entry = {'sender': sender_name, 'text': text, 'time': ts, 'self': False}
                    if sender_phone not in messenger_conversations:
                        messenger_conversations[sender_phone] = []
                    last_texts = [e['text'] for e in messenger_conversations[sender_phone][-3:]]
                    if text not in last_texts:
                        messenger_conversations[sender_phone].append(entry)
                        if messenger_active_conv != sender_phone:
                            messenger_notification_badge += 1
                        _messenger_save_data()
                    if not any(c['addr'] == sender_phone for c in messenger_contacts):
                        messenger_contacts.append({
                            'name': sender_name,
                            'addr': sender_phone,
                            'ip':   addr[0],
                        })
                        _messenger_save_data()
                    else:
                        for c in messenger_contacts:
                            if c['addr'] == sender_phone:
                                c['ip'] = addr[0]
                                break
                except _socket.timeout:
                    continue
                except Exception as e:
                    if _messenger_sock is None:
                        break

        threading.Thread(target=_listen, daemon=True).start()
        _messenger_load_data()
    except Exception as e:
        print(f"Messenger server error: {e}")

def messenger_stop_server():
    global _messenger_sock
    if _messenger_sock:
        s = _messenger_sock
        _messenger_sock = None
        try: s.close()
        except: pass

def messenger_send(phone, text):
    """ارسال پیام به شماره تلفن — از شبکه محلی ارسال می‌شود"""
    global messenger_conversations
    ts = time.strftime('%H:%M')
    entry = {'sender': 'من', 'text': text, 'time': ts, 'self': True}
    if phone not in messenger_conversations:
        messenger_conversations[phone] = []
    messenger_conversations[phone].append(entry)
    _messenger_save_data()

    contact = next((c for c in messenger_contacts if c.get('addr') == phone), None)
    peer_ip = contact.get('ip', '') if contact else ''
    if peer_ip:
        def _do_send():
            try:
                s = _socket.socket(_socket.AF_INET, _socket.SOCK_DGRAM)
                payload = _json.dumps({
                    'phone': _messenger_my_phone or messenger_get_local_ip(),
                    'name':  _messenger_my_phone or "ParsOS",
                    'text':  text,
                    'time':  ts,
                }, ensure_ascii=False).encode('utf-8')
                s.sendto(payload, (peer_ip, MESSENGER_PORT))
                s.close()
            except Exception as e:
                print(f"Messenger send error: {e}")
        threading.Thread(target=_do_send, daemon=True).start()
    return True

def messenger_poll_incoming():
    """poll placeholder — سرور در thread جداگانه کار می‌کند"""
    pass

# --- رسم برنامه پیام‌رسان ---
# =====================================================

def draw_messenger_bubble(surface, text, x, y, w, is_self, color, text_color, tf):
    """رسم حباب پیام"""
    lines = []
    words = text.split()
    line = ""
    for word in words:
        test = (line + " " + word).strip()
        ts = tf.size(test)
        if ts[0] > w - 24:
            if line: lines.append(line)
            line = word
        else:
            line = test
    if line: lines.append(line)
    if not lines: lines = [text]

    lh = tf.get_height() + 4
    bh = lh * len(lines) + 16
    bw = min(w, max(80, max(tf.size(l)[0] for l in lines) + 24))

    bx = x if not is_self else x + w - bw
    surf = pygame.Surface((bw, bh), pygame.SRCALPHA)
    r = 16
    pygame.draw.rect(surf, color, (0, 0, bw, bh), border_radius=r)
    # دم حباب
    if is_self:
        tail = [(bw-2, bh-14), (bw+8, bh-2), (bw-14, bh-4)]
        pygame.draw.polygon(surf, color, tail)
    else:
        tail = [(2, bh-14), (-8, bh-2), (14, bh-4)]
        pygame.draw.polygon(surf, color, tail)
    surface.blit(surf, (bx, y))

    # متن
    ty = y + 8
    for ln in lines:
        ls = tf.render(ln, True, text_color)
        lx = bx + 12
        surface.blit(ls, (lx, ty))
        ty += lh

    return bh

def draw_messenger_app(surface):
    """رسم کامل برنامه پیام‌رسان"""
    global messenger_scroll, messenger_target_scroll, messenger_input_text
    global messenger_page, messenger_active_conv, messenger_notification_badge

    sw, sh = surface.get_size()
    is_dark = is_dark_mode
    bg      = (242, 242, 247) if not is_dark else (17, 17, 21)
    card_bg = (255, 255, 255) if not is_dark else (28, 28, 36)
    txt_col = (20, 20, 24)    if not is_dark else (235, 235, 240)
    sub_col = (140, 140, 148) if not is_dark else (100, 100, 110)
    accent  = (52, 199, 89)   # سبز iMessage
    accent2 = (0, 122, 255)   # آبی برای ارسال
    sep_col = (220, 220, 225) if not is_dark else (40, 40, 50)

    surface.fill(bg)

    tf  = mf(15)
    tf2 = mf(13)
    tf3 = mf(11)
    title_f = mf(20)

    clickable = {}

    if messenger_page == 'new':
        # ===== صفحه افزودن مخاطب دستی =====
        hdr = pygame.Surface((sw, 92), pygame.SRCALPHA)
        hdr.fill((*((248,248,252) if not is_dark else (22,22,28)), 245))
        surface.blit(hdr, (0,0))
        pygame.draw.line(surface, sep_col, (0,92), (sw,92))

        bk = pygame.Rect(12, 56, 68, 28)
        pygame.draw.rect(surface, accent2, bk, border_radius=7)
        surface.blit(render_persian_text("< بازگشت", tf3, WHITE), render_persian_text("< بازگشت", tf3, WHITE).get_rect(center=bk.center))
        clickable['back'] = bk

        ht = render_persian_text("مخاطب جدید", title_f, txt_col)
        surface.blit(ht, ht.get_rect(right=sw-16, top=54))

        # IP محلی کاربر
        _my_ip2 = messenger_get_local_ip()
        sms_hint = tf3.render(f"IP شما: {_my_ip2}  |  شماره تلفن = شناسه پیامرسان" , True, sub_col)
        surface.blit(sms_hint, sms_hint.get_rect(centerx=sw//2, top=100))

        y_f = 128
        # --- فیلد نام ---
        nl = render_persian_text("نام مخاطب:", tf2, txt_col)
        surface.blit(nl, nl.get_rect(right=sw-18, top=y_f-2))
        name_field = pygame.Rect(14, y_f, sw-28, 46)
        n_focus = (messenger_new_focus == 'name')
        pygame.draw.rect(surface, card_bg, name_field, border_radius=12)
        pygame.draw.rect(surface, accent2 if n_focus else sep_col, name_field, 2, border_radius=12)
        nv_txt = messenger_new_name_text if messenger_new_name_text else ("" if n_focus else "مثال: علی")
        nv_col = txt_col if messenger_new_name_text else sub_col
        nv = tf.render(nv_txt, True, nv_col)
        surface.blit(nv, nv.get_rect(right=name_field.right-14, centery=name_field.centery))
        if n_focus and int(time.time()*2)%2==0:
            cx_n = name_field.right - 14 - (nv.get_width() if messenger_new_name_text else 0) - 3
            pygame.draw.line(surface, accent2, (cx_n, name_field.top+10), (cx_n, name_field.bottom-10), 2)
        clickable['name_field'] = name_field

        y_f += 60
        # --- فیلد شماره تلفن (شناسه) ---
        il = render_persian_text("شماره تلفن (شناسه):", tf2, txt_col)
        surface.blit(il, il.get_rect(right=sw-18, top=y_f-2))
        ip_field = pygame.Rect(14, y_f, sw-28, 46)
        i_focus = (messenger_new_focus == 'ip')
        pygame.draw.rect(surface, card_bg, ip_field, border_radius=12)
        pygame.draw.rect(surface, accent2 if i_focus else sep_col, ip_field, 2, border_radius=12)
        iv_txt = messenger_new_ip_text if messenger_new_ip_text else ("" if i_focus else "+989xxxxxxxxx")
        iv_col = txt_col if messenger_new_ip_text else sub_col
        iv = tf.render(iv_txt, True, iv_col)
        surface.blit(iv, (ip_field.left+14, ip_field.top+12))
        if i_focus and int(time.time()*2)%2==0:
            cx_i = ip_field.left + 14 + iv.get_width() + 2
            pygame.draw.line(surface, accent2, (cx_i, ip_field.top+10), (cx_i, ip_field.bottom-10), 2)
        clickable['ip_field'] = ip_field

        y_f += 60
        # --- فیلد IP دستگاه مخاطب ---
        pil = render_persian_text("IP دستگاه مخاطب:", tf2, txt_col)
        surface.blit(pil, pil.get_rect(right=sw-18, top=y_f-2))
        peer_ip_field = pygame.Rect(14, y_f, sw-28, 46)
        pi_focus = (messenger_new_focus == 'peer_ip')
        pygame.draw.rect(surface, card_bg, peer_ip_field, border_radius=12)
        pygame.draw.rect(surface, accent2 if pi_focus else sep_col, peer_ip_field, 2, border_radius=12)
        piv_txt = messenger_new_peer_ip if messenger_new_peer_ip else ("" if pi_focus else "192.168.1.x (اختیاری)")
        piv_col = txt_col if messenger_new_peer_ip else sub_col
        piv = tf.render(piv_txt, True, piv_col)
        surface.blit(piv, (peer_ip_field.left+14, peer_ip_field.top+12))
        if pi_focus and int(time.time()*2)%2==0:
            cx_pi = peer_ip_field.left + 14 + piv.get_width() + 2
            pygame.draw.line(surface, accent2, (cx_pi, peer_ip_field.top+10), (cx_pi, peer_ip_field.bottom-10), 2)
        clickable['peer_ip_field'] = peer_ip_field

        y_f += 64
        # --- دکمه افزودن ---
        can_add = bool(messenger_new_ip_text.strip())
        add_btn = pygame.Rect(sw//2-80, y_f, 160, 46)
        pygame.draw.rect(surface, accent2 if can_add else (120,120,130), add_btn, border_radius=14)
        add_s = render_persian_text("افزودن مخاطب", tf, WHITE)
        surface.blit(add_s, add_s.get_rect(center=add_btn.center))
        clickable['add_contact'] = add_btn

        # نمایش مخاطبین موجود
        if messenger_contacts:
            y_f += 60
            found_l = render_persian_text("مخاطبین ذخیره‌شده:", tf3, sub_col)
            surface.blit(found_l, found_l.get_rect(right=sw-14, top=y_f))
            y_f += 24
            for _i, _c in enumerate(messenger_contacts):
                _rr = pygame.Rect(14, y_f, sw-28, 46)
                pygame.draw.rect(surface, card_bg, _rr, border_radius=10)
                _av_cols = [(52,199,89),(0,122,255),(255,159,10),(255,69,58),(175,82,222)]
                pygame.draw.circle(surface, _av_cols[_i%len(_av_cols)], (38, y_f+23), 18)
                _cs = tf3.render(_c['name'][:1].upper(), True, WHITE)
                surface.blit(_cs, _cs.get_rect(center=(38,y_f+23)))
                _ip_info = _c.get('ip', '?')
                _ns = tf2.render(f"{_c['name']}  {_c['addr']}  ({_ip_info})", True, txt_col)
                surface.blit(_ns, _ns.get_rect(right=_rr.right-14, centery=_rr.centery))
                clickable[f'found_{_i}'] = _rr
                y_f += 52

    elif messenger_page == 'chats':
        # ===== صفحه لیست چت‌ها =====
        # هدر
        header = pygame.Surface((sw, 90), pygame.SRCALPHA)
        header.fill((*((248,248,252) if not is_dark else (22,22,28)), 245))
        surface.blit(header, (0,0))
        pygame.draw.line(surface, sep_col, (0, 90), (sw, 90))

        ht = render_persian_text("پیام‌ها", title_f, txt_col)
        surface.blit(ht, ht.get_rect(right=sw-20, top=52))

        # دکمه مخاطب جدید
        new_btn = pygame.Rect(16, 56, 36, 30)
        pygame.draw.rect(surface, (50,140,255), new_btn, border_radius=8)
        ns = tf2.render("+", True, (255,255,255))
        surface.blit(ns, ns.get_rect(center=new_btn.center))
        clickable['new_chat'] = new_btn

        # نشانگر وضعیت Twilio
        _my_ip = messenger_get_local_ip()
        _status_lbl = f"● آنلاین  {_my_ip}" if _my_ip != "127.0.0.1" else "○ آفلاین — Wi-Fi متصل نیست"
        _status_col = (52,199,89) if _my_ip != "127.0.0.1" else (200,80,50)
        ts_s = tf3.render(_status_lbl, True, _status_col)
        surface.blit(ts_s, ts_s.get_rect(centerx=sw//2, top=14))

        # لیست مخاطبین/چت‌ها
        y = 100
        if not messenger_contacts:
            empty_s = render_persian_text("روی «+» بزنید تا شماره اضافه کنید", tf2, sub_col)
            surface.blit(empty_s, empty_s.get_rect(centerx=sw//2, top=sh//2-20))
        else:
            for i, contact in enumerate(messenger_contacts):
                addr = contact['addr']
                conv = messenger_conversations.get(addr, [])
                last_msg = conv[-1]['text'][:30] if conv else "تاپ برای چت"
                unread = sum(1 for m in conv if not m['self']) if addr != messenger_active_conv else 0

                row_h = 72
                row_r = pygame.Rect(0, y, sw, row_h)
                pygame.draw.rect(surface, card_bg, row_r)
                pygame.draw.line(surface, sep_col, (70, y+row_h), (sw, y+row_h))

                # آواتار دایره
                av_col_list = [(52,199,89),(0,122,255),(255,159,10),(255,69,58),(175,82,222)]
                av_col = av_col_list[i % len(av_col_list)]
                pygame.draw.circle(surface, av_col, (38, y+36), 24)
                init_s = tf.render(contact['name'][:1].upper(), True, WHITE)
                surface.blit(init_s, init_s.get_rect(center=(38, y+36)))

                # نام
                name_s = render_persian_text(contact['name'], tf, txt_col)
                surface.blit(name_s, name_s.get_rect(right=sw-70, centery=y+22))

                # آدرس IP
                addr_s = tf3.render(addr, True, sub_col)
                surface.blit(addr_s, addr_s.get_rect(right=sw-70, centery=y+44))

                # پیام آخر
                lm_s = tf3.render(last_msg, True, sub_col)
                surface.blit(lm_s, (70, y+50))

                # badge خوانده‌نشده
                if unread > 0:
                    badge_r = pygame.Rect(sw-50, y+26, 26, 20)
                    pygame.draw.rect(surface, accent, badge_r, border_radius=10)
                    bs = tf3.render(str(unread), True, WHITE)
                    surface.blit(bs, bs.get_rect(center=badge_r.center))

                clickable[f'conv_{i}'] = row_r
                y += row_h

    elif messenger_page == 'chat' and messenger_active_conv:
        # ===== صفحه چت =====
        contact = next((c for c in messenger_contacts if c['addr'] == messenger_active_conv), None)
        cname = contact['name'] if contact else messenger_active_conv
        conv = messenger_conversations.get(messenger_active_conv, [])

        INPUT_H = sc(64)
        HEADER_H = sc(88)

        # هدر
        hdr = pygame.Surface((sw, HEADER_H), pygame.SRCALPHA)
        hdr.fill((*((248,248,252) if not is_dark else (22,22,28)), 245))
        surface.blit(hdr, (0,0))
        pygame.draw.line(surface, sep_col, (0, HEADER_H), (sw, HEADER_H))

        back_r = pygame.Rect(12, 54, 60, 28)
        pygame.draw.rect(surface, (50,140,255), back_r, border_radius=7)
        bs2 = render_persian_text("< بازگشت", tf3, WHITE)
        surface.blit(bs2, bs2.get_rect(center=back_r.center))
        clickable['back'] = back_r

        name_s2 = render_persian_text(cname, tf, txt_col)
        surface.blit(name_s2, name_s2.get_rect(centerx=sw//2, centery=HEADER_H-26))

        addr_s2 = tf3.render(messenger_active_conv, True, sub_col)
        surface.blit(addr_s2, addr_s2.get_rect(centerx=sw//2, centery=HEADER_H-8))

        # ناحیه پیام‌ها
        CHAT_TOP = HEADER_H
        CHAT_BOT = sh - INPUT_H
        chat_h = CHAT_BOT - CHAT_TOP

        # اسکرول نرم
        messenger_scroll += (messenger_target_scroll - messenger_scroll) * 0.14

        # محاسبه ارتفاع کل پیام‌ها
        PAD = 10
        total_h = PAD
        bubble_w = int(sw * 0.72)
        for m in conv:
            words = m['text'].split()
            lines_est = max(1, len(words) // 6 + 1)
            total_h += lines_est * 24 + 28 + PAD

        max_scroll = max(0, total_h - chat_h)
        messenger_target_scroll = min(messenger_target_scroll, max_scroll)

        # clip chat area
        surface.set_clip(pygame.Rect(0, CHAT_TOP, sw, chat_h))
        y = CHAT_TOP + PAD - int(messenger_scroll)

        for m in conv:
            is_self = m.get('self', False)
            bub_col = (50,140,255) if is_self else (card_bg[0]+5, card_bg[1]+5, card_bg[2]+5)
            tc2 = WHITE if is_self else txt_col
            x_off = PAD if not is_self else PAD

            bh2 = draw_messenger_bubble(surface, m['text'], PAD*2, y, bubble_w, is_self, bub_col, tc2, tf)

            # زمان
            ts2 = tf3.render(m.get('time',''), True, sub_col)
            if is_self:
                surface.blit(ts2, ts2.get_rect(right=sw-PAD*2, top=y+bh2+2))
            else:
                surface.blit(ts2, (PAD*2, y+bh2+2))

            y += bh2 + 22 + PAD

        surface.set_clip(None)

        # اگر پیامی نیست
        if not conv:
            empty_s2 = render_persian_text("اولین پیام را بفرست!", tf2, sub_col)
            surface.blit(empty_s2, empty_s2.get_rect(centerx=sw//2, centery=(CHAT_TOP+CHAT_BOT)//2))

        # نوار ورودی
        input_bar = pygame.Surface((sw, INPUT_H), pygame.SRCALPHA)
        input_bar.fill((*((248,248,252) if not is_dark else (22,22,28)), 248))
        surface.blit(input_bar, (0, sh-INPUT_H))
        pygame.draw.line(surface, sep_col, (0, sh-INPUT_H), (sw, sh-INPUT_H))

        # فیلد متن
        field_r = pygame.Rect(12, sh-INPUT_H+10, sw-70, 44)
        field_bg = (255,255,255) if not is_dark else (38,38,48)
        pygame.draw.rect(surface, field_bg, field_r, border_radius=22)
        pygame.draw.rect(surface, sep_col, field_r, 1, border_radius=22)

        if messenger_input_text:
            it_s = tf.render(messenger_input_text[-32:], True, txt_col)
        else:
            it_s = render_persian_text("پیام...", tf, sub_col)
        surface.blit(it_s, it_s.get_rect(right=field_r.right-14, centery=field_r.centery))
        clickable['input_field'] = field_r

        # دکمه ارسال
        send_r = pygame.Rect(sw-58, sh-INPUT_H+12, 42, 40)
        send_col = accent2 if messenger_input_text.strip() else sub_col
        pygame.draw.circle(surface, send_col, send_r.center, 20)
        arrow = tf.render("↑", True, WHITE)
        surface.blit(arrow, arrow.get_rect(center=send_r.center))
        clickable['send'] = send_r

        # scroll down auto
        if total_h > chat_h and messenger_target_scroll < max_scroll - 10:
            pass  # کاربر در حال scroll است
        elif len(conv) > 0:
            messenger_target_scroll = float(max_scroll)

    return clickable


def draw_files_app_screen(surface):
    global files_content_height, files_list
    global files_scroll_offset, target_files_scroll_offset
    global files_scroll_velocity, files_is_user_scrolling
    global files_overscroll_resistance, files_scroll_friction
    global files_last_scroll_time

    # ---- مدیریت اسکرول اینرسی ----
    if not files_is_user_scrolling:
        # اعمال سرعت (اینرسی)
        if abs(files_scroll_velocity) > 0.1:
            target_files_scroll_offset += files_scroll_velocity
            files_scroll_velocity *= files_scroll_friction
        else:
            files_scroll_velocity = 0.0

    # بونس در لبه‌ها (Overscroll bounce)
    max_scroll = max(0, files_content_height - (SCREEN_HEIGHT - 100))
    if target_files_scroll_offset < -50:   # کشیدن بیش از حد بالا
        overscroll = -target_files_scroll_offset - 50
        target_files_scroll_offset += overscroll * 0.3
        files_scroll_velocity = 0
    elif target_files_scroll_offset > max_scroll + 50:  # کشیدن بیش از حد پایین
        overscroll = target_files_scroll_offset - (max_scroll + 50)
        target_files_scroll_offset -= overscroll * 0.3
        files_scroll_velocity = 0

    # لرپ نرم‌تر به target
    files_scroll_offset += (target_files_scroll_offset - files_scroll_offset) * 0.18

    # clamp نهایی با محدودیت نرم (اجازه کمی overscroll)
    clamp_min = -50
    clamp_max = max_scroll + 50
    if files_scroll_offset < clamp_min:
        files_scroll_offset = clamp_min
    elif files_scroll_offset > clamp_max:
        files_scroll_offset = clamp_max

    # ---- رسم ----
    bg_color = get_current_color('files_bg')
    surface.fill(bg_color)

    text_color = get_current_color('settings_title')
    sub_text_color = (150, 150, 150) if not is_dark_mode else (160, 160, 165)
    divider_color = (235, 235, 238) if not is_dark_mode else (48, 48, 56)

    header_height = 100
    item_height = 66
    padding_side = 16
    icon_w = 42
    start_y = header_height + 8
    clickable_rects = {}

    # ---- رسم آیتم‌ها ----
    for i, item in enumerate(files_list):
        # کش کردن سطوح متنی اگر نشده
        cache_file_item_surfaces(item)

        item_y = start_y + i * item_height - files_scroll_offset

        # فقط آیتم‌های داخل ناحیه دید رسم شوند
        if item_y + item_height > header_height and item_y < SCREEN_HEIGHT:
            row_rect = pygame.Rect(0, item_y, SCREEN_WIDTH, item_height)

            # افکت hover
            if row_rect.collidepoint(pygame.mouse.get_pos()):
                hov_surf = pygame.Surface(row_rect.size, pygame.SRCALPHA)
                hov_surf.fill((0, 0, 0, 12) if not is_dark_mode else (255, 255, 255, 8))
                surface.blit(hov_surf, row_rect.topleft)

            # اگر دکمه فعال بود (کلیک شده)
            if active_button_key == f"item_{i}":
                hl_surf = pygame.Surface(row_rect.size, pygame.SRCALPHA)
                hl_surf.fill((0, 0, 0, 20) if not is_dark_mode else (255, 255, 255, 14))
                surface.blit(hl_surf, row_rect.topleft)

            # رسم آیکون مدرن (فقط یک بار، می‌توان در کش ذخیره کرد ولی کم‌حجم است)
            icon_rect = pygame.Rect(padding_side, item_y + (item_height - icon_w) / 2, icon_w, icon_w)
            draw_modern_file_icon(surface, icon_rect, item['type'])

            # رسم متن نام و متادیتا از سطوح کش‌شده
            if item['name_surf']:
                surface.blit(item['name_surf'], (icon_rect.right + 14, item_y + 11))
            if item['meta_surf']:
                surface.blit(item['meta_surf'], (icon_rect.right + 14, item_y + 38))

            # فلش برای دایرکتوری
            if item['type'] == 'dir':
                arrow_font = mf(14)
                arrow = arrow_font.render("›", True, sub_text_color)
                surface.blit(arrow, arrow.get_rect(right=SCREEN_WIDTH - 16, centery=item_y + item_height // 2))

            # خط جداکننده
            pygame.draw.line(surface, divider_color,
                             (icon_rect.right + 14, item_y + item_height - 1),
                             (SCREEN_WIDTH, item_y + item_height - 1))

            clickable_rects[f"item_{i}"] = row_rect

    # ---- محاسبه ارتفاع کل ----
    files_content_height = start_y + len(files_list) * item_height + 60

    # ---- پیام خالی بودن ----
    if not files_list:
        empty_font = mf(18)
        empty_surf = render_persian_text("این پوشه خالی است", empty_font, sub_text_color)
        surface.blit(empty_surf, empty_surf.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2)))

    # ---- هدر با افکت شیشه‌ای ----
    header_surf = pygame.Surface((SCREEN_WIDTH, header_height), pygame.SRCALPHA)
    hdr_col = (252, 252, 252, 238) if not is_dark_mode else (28, 28, 34, 238)
    header_surf.fill(hdr_col)

    back_btn_rect = None
    if files_current_path != '.':
        back_btn_text = render_persian_text("< بازگشت", text_font, (50, 150, 255))
        back_btn_rect = back_btn_text.get_rect(left=12, top=55)
        header_surf.blit(back_btn_text, back_btn_rect)
        clickable_rects['back_btn'] = back_btn_rect

    # نمایش عنوان مسیر
    path_display = "حافظه داخلی" if files_current_path == '.' else os.path.basename(os.path.abspath(files_current_path))
    title_font = mf(24)
    title_surf = render_persian_text(path_display, title_font, get_current_color('settings_title'))
    header_surf.blit(title_surf, title_surf.get_rect(centerx=SCREEN_WIDTH / 2, top=54))

    # تعداد آیتم‌ها
    count_font = mf(12)
    count_surf = render_persian_text(f"{len(files_list)} آیتم", count_font, sub_text_color)
    header_surf.blit(count_surf, count_surf.get_rect(centerx=SCREEN_WIDTH / 2, top=title_surf.get_rect(centerx=SCREEN_WIDTH / 2, top=54).bottom + 2))

    pygame.draw.line(header_surf, divider_color, (0, header_height - 1), (SCREEN_WIDTH, header_height - 1))
    surface.blit(header_surf, (0, 0))

    return clickable_rects

def draw_control_center(surface, progress, vertical_offset=0.0):
    global cc_buttons, is_dark_mode, is_dragging_cc_content, cc_vertical_offset, target_cc_vertical_offset
    global music_playlist, music_track_name, current_album_art_surface, is_music_playing, is_music_paused

    if progress <= 0:
        return

    if control_center_snapshot:
        control_center_snapshot.set_alpha(int(progress * 255))
        surface.blit(control_center_snapshot, (0, 0))

    ease_progress = 1 - (1 - progress) ** 4
    start_width, start_height = sc(50), sc(50)
    end_width, end_height = SCREEN_WIDTH - sc(20), SCREEN_HEIGHT - sc(100)
    current_width = start_width + (end_width - start_width) * ease_progress
    current_height = start_height + (end_height - start_height) * ease_progress
    end_x, end_y = sc(10), sc(50)
    start_x, start_y = SCREEN_WIDTH - start_width - sc(10), sc(10)
    current_x = start_x + (end_x - start_x) * ease_progress
    current_y = start_y + (end_y - start_y) * ease_progress + vertical_offset

    cc_rect = pygame.Rect(current_x, current_y, current_width, current_height)
    cc_surface = pygame.Surface(cc_rect.size, pygame.SRCALPHA)
    bg_color = (10, 10, 15, int(180 * progress)) if is_dark_mode else (250, 250, 255, int(180 * progress))
    # draw_rounded_rect(cc_surface, cc_surface.get_rect(), bg_color, 25)  # غیرفعال در صورت نیاز

    if ease_progress > 0.8:
        content_alpha = (ease_progress - 0.8) / 0.2 * 255
        text_color = (*WHITE, content_alpha) if is_dark_mode else (*BLACK, content_alpha)
        sub_text_color = (*LIGHT_GRAY, content_alpha) if is_dark_mode else (*GRAY, content_alpha)

        widget_padding = 15
        current_y_pos = widget_padding

        # --- 1. دکمههای بزرگ (Wi-Fi & Data) ---
        top_widget_width = (current_width - widget_padding * 3) / 2
        top_widget_height = 80
        
        wifi_rect_base = pygame.Rect(widget_padding, current_y_pos, top_widget_width, top_widget_height)
        data_rect_base = pygame.Rect(wifi_rect_base.right + widget_padding, current_y_pos, top_widget_width, top_widget_height)
        
        # ذخیره Rect کلی برای تشخیص کلیک
        cc_buttons['wifi']['rect'] = wifi_rect_base.move(cc_rect.topleft)
        cc_buttons['data']['rect'] = data_rect_base.move(cc_rect.topleft)

        # رسم دکمه وایفای
        btn_wifi = cc_buttons['wifi']
        base_color = (50, 50, 60) if is_dark_mode else (220, 220, 225)
        active_color = (50, 150, 255)
        wifi_color = tuple(int(b + (a - b) * btn_wifi['color_progress']) for b, a in zip(base_color, active_color))
        final_wifi_color = (*wifi_color, int(content_alpha * 0.8))
        draw_rounded_rect(cc_surface, wifi_rect_base, final_wifi_color, 20)
        wifi_text_surf = render_persian_text(get_string(btn_wifi.get('label_key', 'wifi')), text_font, text_color)
        wifi_text_surf.set_alpha(content_alpha)
        cc_surface.blit(wifi_text_surf, wifi_text_surf.get_rect(left=wifi_rect_base.left + 15, top=wifi_rect_base.top + 15))

        # رسم دکمه داده
        btn_data = cc_buttons['data']
        data_color = tuple(int(b + (a - b) * btn_data['color_progress']) for b, a in zip(base_color, active_color))
        final_data_color = (*data_color, int(content_alpha * 0.8))
        draw_rounded_rect(cc_surface, data_rect_base, final_data_color, 20)
        data_text_surf = render_persian_text(get_string(btn_data.get('label_key', 'mobile_data')), text_font, text_color)
        data_text_surf.set_alpha(content_alpha)
        cc_surface.blit(data_text_surf, data_text_surf.get_rect(left=data_rect_base.left + 15, top=data_rect_base.top + 15))
        
        current_y_pos += top_widget_height + widget_padding

        # --- 2. ویجت مدیا پلیر (Placeholder) ---
        media_rect = pygame.Rect(widget_padding, current_y_pos, current_width - widget_padding*2, 80)
        media_color = (50, 50, 60, int(content_alpha * 0.8)) if is_dark_mode else (220, 220, 225, int(content_alpha * 0.8))
        draw_rounded_rect(cc_surface, media_rect, media_color, 20)

        # بررسی وجود موسیقی در حال پخش
        if music_playlist and music_track_name != "موسیقی یافت نشد":
            # ----- کاور کوچک -----
            cover_size = 50
            cover_rect = pygame.Rect(media_rect.left + 12, media_rect.centery - cover_size//2, cover_size, cover_size)
            if current_album_art_surface:
                art_small = pygame.transform.smoothscale(current_album_art_surface, (cover_size, cover_size))
                rounded_cover = pygame.Surface((cover_size, cover_size), pygame.SRCALPHA)
                draw_rounded_rect(rounded_cover, rounded_cover.get_rect(), (255, 255, 255), 10)
                rounded_cover.blit(art_small, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)
                cc_surface.blit(rounded_cover, cover_rect.topleft)
            else:
                draw_rounded_rect(cc_surface, cover_rect, (100, 100, 110), 10)
                icon_font = mf(20)
                icon_s = icon_font.render("♪", True, (200,200,200))
                icon_s.set_alpha(content_alpha)
                cc_surface.blit(icon_s, icon_s.get_rect(center=cover_rect.center))

            # ----- نام آهنگ -----
            name_font = mf(14)
            track_name_display = music_track_name
            if len(track_name_display) > 28:
                track_name_display = track_name_display[:25] + "..."
            track_surf = render_persian_text(track_name_display, name_font, text_color)
            track_surf.set_alpha(content_alpha)
            cc_surface.blit(track_surf, track_surf.get_rect(left=cover_rect.right + 12, top=media_rect.top + 18))

            # ----- نام خواننده (placeholder) -----
            artist_font = mf(11)
            artist_surf = render_persian_text("ParsOS Music", artist_font, sub_text_color)
            artist_surf.set_alpha(content_alpha)
            cc_surface.blit(artist_surf, artist_surf.get_rect(left=cover_rect.right + 12, top=track_surf.get_rect().bottom + 4))

            # ----- دکمه‌های کنترلی (قبلی، پخش/توقف، بعدی) -----
            btn_size = 36
            btn_gap = 12
            total_btns_width = btn_size * 3 + btn_gap * 2
            btn_start_x = media_rect.right - total_btns_width - 12
            btn_y = media_rect.centery - btn_size//2

            prev_btn_rect = pygame.Rect(btn_start_x, btn_y, btn_size, btn_size)
            play_btn_rect = pygame.Rect(prev_btn_rect.right + btn_gap, btn_y, btn_size, btn_size)
            next_btn_rect = pygame.Rect(play_btn_rect.right + btn_gap, btn_y, btn_size, btn_size)

            # ذخیره rectها برای تشخیص کلیک
            cc_buttons['media_prev'] = {'rect': prev_btn_rect.move(cc_rect.topleft), 'type': 'media_btn'}
            cc_buttons['media_play'] = {'rect': play_btn_rect.move(cc_rect.topleft), 'type': 'media_btn'}
            cc_buttons['media_next'] = {'rect': next_btn_rect.move(cc_rect.topleft), 'type': 'media_btn'}

            # رسم دکمه‌ها
            btn_bg_color = (80, 80, 90, int(content_alpha * 0.9)) if is_dark_mode else (200, 200, 210, int(content_alpha * 0.9))
            btn_icon_color = WHITE if is_dark_mode else BLACK

            # دکمه قبلی
            pygame.draw.circle(cc_surface, btn_bg_color, prev_btn_rect.center, btn_size//2)
            prev_icon = mf(16).render("◀", True, btn_icon_color)
            prev_icon.set_alpha(content_alpha)
            cc_surface.blit(prev_icon, prev_icon.get_rect(center=prev_btn_rect.center))

            # دکمه پخش/توقف
            pygame.draw.circle(cc_surface, btn_bg_color, play_btn_rect.center, btn_size//2)
            if is_music_playing:
                play_icon = mf(16).render("⏸", True, btn_icon_color)
            else:
                play_icon = mf(16).render("▶", True, btn_icon_color)
            play_icon.set_alpha(content_alpha)
            cc_surface.blit(play_icon, play_icon.get_rect(center=play_btn_rect.center))

            # دکمه بعدی
            pygame.draw.circle(cc_surface, btn_bg_color, next_btn_rect.center, btn_size//2)
            next_icon = mf(16).render("▶", True, btn_icon_color)
            next_icon = pygame.transform.flip(next_icon, True, False)
            next_icon.set_alpha(content_alpha)
            cc_surface.blit(next_icon, next_icon.get_rect(center=next_btn_rect.center))

        else:
            # اگر موسیقی در حال پخش نیست، پیام نمایش داده شود
            media_text_surf = render_persian_text(get_string("no_playback_history"), status_bar_font, sub_text_color)
            media_text_surf.set_alpha(content_alpha)
            cc_surface.blit(media_text_surf, media_text_surf.get_rect(center=media_rect.center))

        current_y_pos += media_rect.height + widget_padding

        # --- 3. اسلایدرها (روشنایی و صدا) ---
        slider_height = 50
        brightness_rect = pygame.Rect(widget_padding, current_y_pos, current_width - widget_padding*2, slider_height)
        volume_rect = pygame.Rect(widget_padding, current_y_pos + slider_height + 5, current_width - widget_padding*2, slider_height)
        
        # ذخیره Rect کلی برای تشخیص کلیک
        cc_buttons['brightness_slider'] = {'rect': brightness_rect.move(cc_rect.topleft)}
        cc_buttons['volume_slider'] = {'rect': volume_rect.move(cc_rect.topleft)}
        
        slider_bg_color = (40, 40, 50, int(content_alpha * 0.8)) if is_dark_mode else (210, 210, 215, int(content_alpha * 0.8))
        draw_rounded_rect(cc_surface, brightness_rect, slider_bg_color, 15)
        draw_rounded_rect(cc_surface, volume_rect, slider_bg_color, 15)
        
        draw_cc_slider(cc_surface, brightness_rect, cc_brightness, '☀️', sub_text_color)
        draw_cc_slider(cc_surface, volume_rect, cc_volume, '🔊', sub_text_color)

        current_y_pos += (slider_height * 2) + 10 + widget_padding

        # --- 4. گرید دکمههای گرد ---
        circular_buttons = [k for k, v in cc_buttons.items() if v.get('type') == 'circular']
        cols = 4
        btn_size = (current_width - (cols + 1) * widget_padding) / cols
        btn_label_height = 30 # فضا برای لیبل زیر دکمه
        
        for i, btn_name in enumerate(circular_buttons):
            row = i // cols
            col = i % cols
            
            x = widget_padding + col * (btn_size + widget_padding)
            y = current_y_pos + row * (btn_size + btn_label_height + widget_padding)
            
            btn_rect = pygame.Rect(x, y, btn_size, btn_size)
            
            if btn_rect.bottom < current_height - widget_padding: # فقط دکمههایی که جا میشوند را رسم کن
                cc_buttons[btn_name]['rect'] = btn_rect.move(cc_rect.topleft)
                draw_cc_circular_toggle(cc_surface, btn_rect, cc_buttons[btn_name], sub_text_color, content_alpha)

    # رسم سطح نهایی CC روی صفحه اصلی
    surface.blit(cc_surface, cc_rect.topleft)
    
def draw_battery_icon_status_bar(surface, pos, battery_info, text_color):
    """
    (نسخه نهایی) آیکون باتری را با استفاده از متدهای استاندارد Pygame رسم میکند
    تا از اعوجاج در گوشهها جلوگیری شود و ظاهر دقیقاً مشابه نمونه اولیه باشد.
    """
    if not battery_info:
        return

    percent = battery_info.percent
    is_charging = battery_info.power_plugged

    # ابعاد آیکون
    body_width, body_height = 28, 14
    tip_width, tip_height = 3, 6
    radius = 4

    # موقعیتها
    body_rect = pygame.Rect(pos[0] - body_width, pos[1], body_width, body_height)
    tip_rect = pygame.Rect(body_rect.right, body_rect.centery - tip_height / 2, tip_width, tip_height)
    
    # رنگ پسزمینه آیکون (همرنگ متن نوار وضعیت)
    icon_bg_color = text_color
    
    # رنگ متن درصد (متضاد با پسزمینه)
    # اگر پس زمینه خیلی روشن است، متن را تیره کن و بالعکس
    if sum(icon_bg_color[:3]) > 382: # 255 * 3 / 2
        percent_text_color = (10, 10, 10)
    else:
        percent_text_color = (240, 240, 240)

    # رسم بدنه اصلی (پُر) با گوشههای گرد
    pygame.draw.rect(surface, icon_bg_color, body_rect, border_radius=radius)
    # رسم نوک باتری
    pygame.draw.rect(surface, icon_bg_color, tip_rect, border_top_right_radius=2, border_bottom_right_radius=2)

    # نمایش درصد داخل آیکون
    percent_text = str(percent)
    try:
        percent_font = pygame.font.Font("Vazir-Bold.ttf", 11)
    except FileNotFoundError:
        percent_font = mf(10)
    
    percent_surf = percent_font.render(percent_text, True, percent_text_color)
    # تنظیم دقیق موقعیت متن برای وسطچین شدن بهتر
    surface.blit(percent_surf, percent_surf.get_rect(center=body_rect.center))

    # اگر در حال شارژ است، یک آیکون صاعقه کنار آن نمایش داده میشود
    if is_charging:
        charge_font = mf(14)
        charge_surf = charge_font.render("⚡", True, text_color)
        surface.blit(charge_surf, charge_surf.get_rect(midright=(body_rect.left - 5, body_rect.centery)))
        
def draw_gallery_app_screen(surface):
    global gallery_content_height, target_gallery_scroll_offset, gallery_scroll_offset
    
    bg_color = get_current_color('gallery_bg')
    surface.fill(bg_color)

    # اسکرول نرمتر (0.15 -> روانتر)
    gallery_scroll_offset += (target_gallery_scroll_offset - gallery_scroll_offset) * 0.15
    
    cols = 3
    padding = 2
    screen_w = surface.get_width()
    thumb_size = (screen_w - (cols - 1) * padding) / cols

    # ترکیب عکسها و ویدیوها در یک لیست نمایشی
    all_media = []
    for p in gallery_photos:
        all_media.append(p)
    for v in gallery_videos:
        all_media.append(v)

    clickable_rects = {}
    num_rows = math.ceil(len(all_media) / cols)
    start_y = 100

    for i, media in enumerate(all_media):
        row = i // cols
        col = i % cols
        x = col * (thumb_size + padding)
        y = start_y + row * (thumb_size + padding) - gallery_scroll_offset

        if y + thumb_size > 0 and y < SCREEN_HEIGHT:
            thumb = gallery_thumbnails.get(media['path'])
            ts = int(thumb_size)
            
            if thumb:
                if thumb.get_width() != ts:
                    thumb = pygame.transform.smoothscale(thumb, (ts, ts))
                    gallery_thumbnails[media['path']] = thumb
                surface.blit(thumb, (x, y))
            else:
                # پلیسهولدر خاکستری
                ph_surf = pygame.Surface((ts, ts))
                ph_surf.fill((100, 100, 110) if is_dark_mode else (200, 200, 205))
                surface.blit(ph_surf, (x, y))

            # نشانگر ویدیو (مثلث پخش + مدت زمان)
            if media.get('type') == 'video':
                # لایه تاریک شفاف روی تامبنیل
                overlay = pygame.Surface((ts, ts), pygame.SRCALPHA)
                overlay.fill((0, 0, 0, 60))
                surface.blit(overlay, (x, y))

                # دکمه پخش (مثلث)
                play_cx, play_cy = x + ts // 2, y + ts // 2
                tri_r = ts * 0.18
                pts = [
                    (play_cx + tri_r * 0.7, play_cy),
                    (play_cx - tri_r * 0.5, play_cy - tri_r * 0.6),
                    (play_cx - tri_r * 0.5, play_cy + tri_r * 0.6),
                ]
                # دایره پشت
                pygame.draw.circle(surface, (255, 255, 255, 180), (int(play_cx), int(play_cy)), int(tri_r * 1.2))
                pygame.draw.polygon(surface, (30, 30, 30), [(int(p[0]), int(p[1])) for p in pts])

                # مدت زمان پایین راست
                dur = media.get('duration', 0)
                if dur > 0:
                    dur_str = format_time(dur)
                    dur_font = mf(10)
                    dur_surf = dur_font.render(dur_str, True, (255, 255, 255))
                    dur_bg = pygame.Surface((dur_surf.get_width() + 8, dur_surf.get_height() + 4), pygame.SRCALPHA)
                    dur_bg.fill((0, 0, 0, 140))
                    bx = x + ts - dur_bg.get_width() - 4
                    by = y + ts - dur_bg.get_height() - 4
                    surface.blit(dur_bg, (bx, by))
                    surface.blit(dur_surf, (bx + 4, by + 2))

            elif is_dark_mode:
                pygame.draw.rect(surface, (45, 45, 50), (x, y, thumb_size, thumb_size), 1)

            clickable_rects[f'media_{i}'] = pygame.Rect(x, y + gallery_scroll_offset, thumb_size, thumb_size)

    gallery_content_height = start_y + num_rows * (thumb_size + padding) + 100

    # --- هدر شیشهای ---
    header_height = 90
    header_bg = pygame.Surface((screen_w, header_height), pygame.SRCALPHA)
    header_color = (252, 252, 252, 235) if not is_dark_mode else (28, 28, 32, 235)
    header_bg.fill(header_color)
    surface.blit(header_bg, (0, 0))
    
    sep_color = (210, 210, 210) if not is_dark_mode else (55, 55, 60)
    pygame.draw.line(surface, sep_color, (0, header_height), (screen_w, header_height))

    title_font = mf(26)
    title = render_persian_text("گالری", title_font, get_current_color('settings_title'))
    surface.blit(title, title.get_rect(right=screen_w - 18, centery=header_height / 2 + 8))
    
    count_font = mf(13)
    count_label = f"{len(gallery_photos)} عکس  •  {len(gallery_videos)} ویدیو"
    count_surf = render_persian_text(count_label, count_font, (140, 140, 145))
    title_r = title.get_rect(right=screen_w - 18, centery=header_height / 2 + 8)
    surface.blit(count_surf, count_surf.get_rect(right=screen_w - 20, top=title_r.bottom + 2))

    return clickable_rects

def draw_gallery_fullscreen_view(surface):
    global gallery_animation_progress, gallery_animation_direction, is_gallery_fullscreen, gallery_start_rect, gallery_selected_index
    
    if not gallery_photos: return

    # مدیریت ایندکس دایرهای (اگر از آخر رد شد برود اول)
    gallery_selected_index = gallery_selected_index % len(gallery_photos)
    photo_data = gallery_photos[gallery_selected_index]
    
    # بارگذاری تصویر اصلی
    if photo_data['image'] is None:
        try:
            full_img = pygame.image.load(photo_data['path']).convert()
            # اگر تصویر خیلی بزرگ است، متناسب با صفحه کوچک شود تا حافظه پر نشود
            iw, ih = full_img.get_size()
            scale_factor = min(1.0, 1500/max(iw, ih)) # محدودیت ماکزیمم سایز
            if scale_factor < 1.0:
                full_img = pygame.transform.smoothscale(full_img, (int(iw*scale_factor), int(ih*scale_factor)))
            photo_data['image'] = full_img
        except Exception as e:
            print(f"Error loading full image: {e}")
            return
    
    image = photo_data['image']

    # --- انیمیشن باز و بسته شدن ---
    if gallery_animation_direction != 0:
        gallery_animation_progress += 0.08 * gallery_animation_direction # کمی سریعتر
        gallery_animation_progress = max(0.0, min(1.0, gallery_animation_progress))

    ease_progress = 1 - pow(1 - gallery_animation_progress, 3) # Cubic Ease Out
    
    # پسزمینه مشکی کامل در حالت تمام صفحه
    bg_alpha = int(255 * ease_progress)
    surface.fill((0, 0, 0)) # مشکی خالص برای تمرکز روی عکس
    
    # --- محاسبه ابعاد تصویر برای فیت شدن در صفحه (Aspect Fit) ---
    sw, sh = SCREEN_WIDTH, SCREEN_HEIGHT
    iw, ih = image.get_size()
    scale = min(sw / iw, sh / ih)
    new_w, new_h = int(iw * scale), int(ih * scale)
    
    # موقعیت نهایی (وسط صفحه)
    final_rect = pygame.Rect(0, 0, new_w, new_h)
    final_rect.center = (sw / 2, sh / 2)

    # انیمیشن از تامبنیل به تمام صفحه
    if gallery_start_rect is None: gallery_start_rect = final_rect
    
    current_rect = final_rect.copy()
    if gallery_animation_progress < 1.0:
        # درونیابی بین رکت تامبنیل و رکت نهایی
        current_rect.x = gallery_start_rect.x + (final_rect.x - gallery_start_rect.x) * ease_progress
        current_rect.y = gallery_start_rect.y + (final_rect.y - gallery_start_rect.y) * ease_progress
        current_rect.width = gallery_start_rect.width + (final_rect.width - gallery_start_rect.width) * ease_progress
        current_rect.height = gallery_start_rect.height + (final_rect.height - gallery_start_rect.height) * ease_progress
    
    # رسم تصویر
    scaled_image = pygame.transform.smoothscale(image, (int(current_rect.width), int(current_rect.height)))
    surface.blit(scaled_image, current_rect)

    # --- رابط کاربری (UI Overlays) ---
    # فقط وقتی انیمیشن تمام شد نشان بده
    if gallery_animation_progress >= 0.95 and is_gallery_fullscreen:
        
        # 1. نوار بالا (بازگشت)
        top_bar = pygame.Surface((sw, 80), pygame.SRCALPHA)
        top_bar.fill((0, 0, 0, 100)) # نیمه شفاف
        surface.blit(top_bar, (0,0))
        
        back_text = render_persian_text("بازگشت", text_font, WHITE)
        back_rect = back_text.get_rect(top=45, left=20)
        surface.blit(back_text, back_rect)
        
        # نام فایل در بالا
        name_text = render_persian_text(photo_data['name'], text_font, WHITE)
        if name_text.get_width() > 200: 
             name_text = render_persian_text(photo_data['name'][:20]+"...", text_font, WHITE)
        surface.blit(name_text, name_text.get_rect(center=(sw/2, 55)))

        # 2. نوار ابزار پایین (Tools)
        bottom_bar_height = 80
        bottom_bar = pygame.Surface((sw, bottom_bar_height), pygame.SRCALPHA)
        bottom_bar.fill((0, 0, 0, 150))

        ICON_R = 20
        # آیکون‌ها: اطلاعات، ویرایش، حذف — سه‌تایی در یک ردیف
        positions = {
            'info':   (sw//2 - 80, bottom_bar_height//2),
            'edit':   (sw//2,      bottom_bar_height//2),
            'delete': (sw//2 + 80, bottom_bar_height//2),
        }

        # دکمه اطلاعات
        pygame.draw.circle(bottom_bar, (255,255,255), positions['info'], ICON_R, 2)
        info_s = text_font.render("i", True, WHITE)
        bottom_bar.blit(info_s, info_s.get_rect(center=positions['info']))

        # دکمه ویرایش (مداد مینیمال)
        ecx, ecy = positions['edit']
        pygame.draw.circle(bottom_bar, (255,255,255), (ecx, ecy), ICON_R, 2)
        # رسم مداد مینیمال روی bottom_bar
        ps = 10
        # بدنه مداد
        ep_body = [
            (ecx - ps*0.12, ecy - ps*0.45),
            (ecx + ps*0.12, ecy - ps*0.45),
            (ecx + ps*0.12, ecy + ps*0.22),
            (ecx - ps*0.12, ecy + ps*0.22),
        ]
        pygame.draw.polygon(bottom_bar, (255,255,255), [(int(x), int(y)) for x, y in ep_body])
        # نوک
        ep_tip = [(ecx-ps*0.12, ecy+ps*0.22), (ecx+ps*0.12, ecy+ps*0.22), (ecx, ecy+ps*0.46)]
        pygame.draw.polygon(bottom_bar, (220,220,200), [(int(x), int(y)) for x, y in ep_tip])
        pygame.draw.line(bottom_bar, (80,80,80), (int(ecx-ps*0.12), int(ecy+ps*0.22)), (int(ecx+ps*0.12), int(ecy+ps*0.22)), 1)

        # دکمه حذف
        pygame.draw.circle(bottom_bar, (255, 80, 80), positions['delete'], ICON_R, 2)
        del_s = text_font.render("✕", True, (255, 80, 80))
        bottom_bar.blit(del_s, del_s.get_rect(center=positions['delete']))

        surface.blit(bottom_bar, (0, sh - bottom_bar_height))
        
        # 3. پنل اطلاعات (اگر فعال باشد)
        if is_gallery_info_visible:
            info_rect = pygame.Rect(40, sh/2 - 100, sw - 80, 200)
            draw_rounded_rect(surface, info_rect, (30, 30, 35, 240), 15)
            
            info_title = render_persian_text("اطلاعات تصویر", settings_title_font, WHITE)
            surface.blit(info_title, info_title.get_rect(center=(sw/2, info_rect.top + 30)))
            
            lines = [
                f"نام: {photo_data['name']}",
                f"حجم: {photo_data.get('size_str', 'N/A')}",
                f"تاریخ: {photo_data.get('date', 'N/A')}",
                f"ابعاد: {image.get_width()}x{image.get_height()}"
            ]
            
            y_info = info_rect.top + 70
            for line in lines:
                l_surf = render_persian_text(line, text_font, (200, 200, 200))
                surface.blit(l_surf, (info_rect.left + 20, y_info))
                y_info += 30

    # پایان انیمیشن بسته شدن
    if (gallery_animation_direction == -1 and gallery_animation_progress <= 0.0):
        is_gallery_fullscreen = False
        gallery_animation_direction = 0

    # برگرداندن Rect ها برای تشخیص کلیک در حلقه اصلی
    if is_gallery_fullscreen and gallery_animation_progress >= 0.95:
        sw2 = SCREEN_WIDTH
        sh2 = SCREEN_HEIGHT
        return {
            'back_btn':   pygame.Rect(0, 0, 100, 80),
            'prev_zone':  pygame.Rect(0, 80, 80, sh2-160),
            'next_zone':  pygame.Rect(sw2-80, 80, 80, sh2-160),
            'info_btn':   pygame.Rect(sw2//2 - 110, sh2 - 80, 60, 80),
            'edit_btn':   pygame.Rect(sw2//2 - 30,  sh2 - 80, 60, 80),
            'delete_btn': pygame.Rect(sw2//2 + 50,  sh2 - 80, 60, 80),
        }
    return {}


def draw_pencil_icon(surface, cx, cy, size, color):
    """رسم آیکون مداد مینیمال با pygame"""
    s = size
    # بدنه مداد (مستطیل کج)
    pts_body = [
        (cx - s*0.12, cy - s*0.45),
        (cx + s*0.12, cy - s*0.45),
        (cx + s*0.12, cy + s*0.25),
        (cx - s*0.12, cy + s*0.25),
    ]
    pygame.draw.polygon(surface, color, [(int(x), int(y)) for x, y in pts_body])
    # نوک مداد (مثلث)
    pts_tip = [
        (cx - s*0.12, cy + s*0.25),
        (cx + s*0.12, cy + s*0.25),
        (cx, cy + s*0.48),
    ]
    tip_color = (min(255, color[0]+60), min(255, color[1]+30), min(255, color[2]+20))
    pygame.draw.polygon(surface, tip_color, [(int(x), int(y)) for x, y in pts_tip])
    # خط بین بدنه و نوک
    pygame.draw.line(surface, (80,80,80), (int(cx-s*0.12), int(cy+s*0.25)), (int(cx+s*0.12), int(cy+s*0.25)), 1)
    # نقطه نوک
    pygame.draw.circle(surface, (50,50,50), (int(cx), int(cy+s*0.48)), 1)

def gallery_editor_open(image_surface):
    """باز کردن ویرایشگر با یک کپی از تصویر"""
    global is_gallery_editor_open, gallery_editor_surface, gallery_editor_original
    global gallery_editor_undo_stack, gallery_editor_strokes, gallery_editor_text_pos
    global gallery_editor_pending_text, gallery_editor_text_input, gallery_editor_start_pos
    global gallery_editor_is_drawing, gallery_editor_last_pos
    # کپی از تصویر برای ویرایش
    gallery_editor_surface = image_surface.copy().convert()
    gallery_editor_original = image_surface.copy().convert()
    gallery_editor_undo_stack = [image_surface.copy().convert()]
    gallery_editor_strokes = []
    gallery_editor_text_pos = None
    gallery_editor_pending_text = ""
    gallery_editor_text_input = False
    gallery_editor_start_pos = None
    gallery_editor_is_drawing = False
    gallery_editor_last_pos = None
    is_gallery_editor_open = True
    gallery_editor_dirty = True
    gallery_editor_cached_img = None
    gallery_editor_img_rect = None

def gallery_editor_undo():
    """برگشت به مرحله قبل"""
    global gallery_editor_surface, gallery_editor_undo_stack, gallery_editor_dirty, gallery_editor_cached_img
    if len(gallery_editor_undo_stack) > 1:
        gallery_editor_undo_stack.pop()
        gallery_editor_surface = gallery_editor_undo_stack[-1].copy()
        gallery_editor_dirty = True
        gallery_editor_cached_img = None

def gallery_editor_save_state():
    """ذخیره state برای undo"""
    global gallery_editor_undo_stack, gallery_editor_dirty
    if len(gallery_editor_undo_stack) > 30:
        gallery_editor_undo_stack.pop(0)
    gallery_editor_undo_stack.append(gallery_editor_surface.copy())

def gallery_editor_mark_dirty():
    global gallery_editor_dirty, gallery_editor_cached_img
    gallery_editor_dirty = True
    gallery_editor_cached_img = None

def draw_gallery_editor(surface):
    """رسم ویرایشگر عکس — با cache برای جلوگیری از هنگ"""
    global gallery_editor_toolbar_alpha, gallery_editor_toolbar_target
    global gallery_editor_is_drawing, gallery_editor_last_pos
    global gallery_editor_cached_img, gallery_editor_img_rect, gallery_editor_dirty

    sw, sh = surface.get_size()
    surface.fill((0, 0, 0))

    if gallery_editor_surface is None:
        return {}

    # --- محاسبه ناحیه تصویر ---
    BOTTOM_H = sc(200)
    TOP_H    = sc(60)
    view_h   = sh - TOP_H - BOTTOM_H

    es = gallery_editor_surface
    ew, eh = es.get_size()
    scale = min(sw / ew, view_h / eh)
    dw, dh = int(ew * scale), int(eh * scale)
    dx = (sw - dw) // 2
    dy = TOP_H + (view_h - dh) // 2
    img_rect = pygame.Rect(dx, dy, dw, dh)

    # --- بازسازی cache فقط وقتی تصویر تغییر کرده ---
    if gallery_editor_dirty or gallery_editor_cached_img is None or gallery_editor_img_rect != img_rect:
        gallery_editor_cached_img = pygame.transform.smoothscale(es, (dw, dh))
        gallery_editor_img_rect = img_rect
        gallery_editor_dirty = False

    surface.blit(gallery_editor_cached_img, (dx, dy))

    # fade toolbar (نرم)
    gallery_editor_toolbar_alpha += (gallery_editor_toolbar_target - gallery_editor_toolbar_alpha) * 0.15
    alpha_val = int(max(0, min(255, gallery_editor_toolbar_alpha)))

    # ===== TOOLBAR بالا =====
    top_bar = pygame.Surface((sw, TOP_H), pygame.SRCALPHA)
    top_bar.fill((0, 0, 0, 200))
    surface.blit(top_bar, (0, 0))

    # دکمه بازگشت
    back_rect = pygame.Rect(12, 15, 70, 32)
    pygame.draw.rect(surface, (60, 60, 65), back_rect, border_radius=8)
    bf = mf(13)
    bs = render_persian_text("بازگشت", bf, (220, 220, 220))
    surface.blit(bs, bs.get_rect(center=back_rect.center))

    # دکمه undo
    undo_rect = pygame.Rect(90, 15, 55, 32)
    undo_enabled = len(gallery_editor_undo_stack) > 1
    undo_col = (60, 60, 65) if undo_enabled else (35, 35, 38)
    pygame.draw.rect(surface, undo_col, undo_rect, border_radius=8)
    uf = mf(16)
    us = uf.render("<", True, (220, 220, 220) if undo_enabled else (100, 100, 100))
    surface.blit(us, us.get_rect(center=undo_rect.center))

    # دکمه ذخیره
    save_rect = pygame.Rect(sw - 80, 15, 68, 32)
    pygame.draw.rect(surface, (50, 140, 255), save_rect, border_radius=8)
    sf2 = mf(13)
    ss2 = render_persian_text("ذخیره", sf2, (255, 255, 255))
    surface.blit(ss2, ss2.get_rect(center=save_rect.center))

    # ===== TOOLBAR پایین =====
    bottom_bar = pygame.Surface((sw, BOTTOM_H), pygame.SRCALPHA)
    bottom_bar.fill((12, 12, 18, 240))
    surface.blit(bottom_bar, (0, sh - BOTTOM_H))

    # خط جدا کننده
    pygame.draw.line(surface, (40, 40, 50), (0, sh - BOTTOM_H), (sw, sh - BOTTOM_H))

    # --- ردیف ابزارها ---
    tools = [
        ('pen',    'قلم'),
        ('eraser', 'پاک‌کن'),
        ('line',   'خط'),
        ('rect',   'مستطیل'),
        ('text',   'متن'),
    ]
    tool_y = sh - BOTTOM_H + 18
    tool_size = 44
    total_w = len(tools) * tool_size + (len(tools)-1) * 10
    tool_start_x = (sw - total_w) // 2
    tool_rects = {}

    tf2 = mf(10)

    for i, (t_key, t_label) in enumerate(tools):
        tx = tool_start_x + i * (tool_size + 10)
        tr = pygame.Rect(tx, tool_y, tool_size, tool_size)
        is_active = (gallery_editor_tool == t_key)
        bg = (50, 140, 255) if is_active else (35, 35, 42)
        pygame.draw.rect(surface, bg, tr, border_radius=10)
        if is_active:
            pygame.draw.rect(surface, (100, 180, 255), tr, 2, border_radius=10)

        # آیکون ابزار (رسم با pygame)
        cx2, cy2 = tr.centerx, tr.centery - 4
        ic = (255, 255, 255) if is_active else (180, 180, 190)
        if t_key == 'pen':
            draw_pencil_icon(surface, cx2, cy2, 20, ic)
        elif t_key == 'eraser':
            pygame.draw.rect(surface, ic, pygame.Rect(cx2-8, cy2-5, 16, 10), border_radius=3)
            pygame.draw.rect(surface, (200,200,220) if is_active else (100,100,110),
                             pygame.Rect(cx2-8, cy2+5, 10, 5), border_radius=2)
        elif t_key == 'line':
            pygame.draw.line(surface, ic, (cx2-8, cy2+6), (cx2+8, cy2-6), 2)
            pygame.draw.circle(surface, ic, (cx2-8, cy2+6), 2)
            pygame.draw.circle(surface, ic, (cx2+8, cy2-6), 2)
        elif t_key == 'rect':
            pygame.draw.rect(surface, ic, pygame.Rect(cx2-8, cy2-6, 16, 12), 2, border_radius=2)
        elif t_key == 'text':
            ff = mf(16)
            ts2 = ff.render("A", True, ic)
            surface.blit(ts2, ts2.get_rect(center=(cx2, cy2)))

        # برچسب
        label_s = tf2.render(t_label, True, (180,180,190) if not is_active else (220,220,255))
        surface.blit(label_s, label_s.get_rect(centerx=tr.centerx, top=tr.bottom + 3))
        tool_rects[t_key] = tr

    # --- اندازه برس ---
    SIZE_Y = sh - BOTTOM_H + 78
    size_label = tf2.render("اندازه:", True, (150, 150, 160))
    surface.blit(size_label, (16, SIZE_Y + 5))
    sizes = [2, 4, 7, 12, 20]
    size_rects = {}
    for i, sz in enumerate(sizes):
        sx = 75 + i * 42
        sr = pygame.Rect(sx, SIZE_Y, 36, 36)
        is_sel = (gallery_editor_size == sz)
        pygame.draw.rect(surface, (45, 45, 55) if not is_sel else (50, 140, 255), sr, border_radius=8)
        pygame.draw.circle(surface, gallery_editor_color, (sr.centerx, sr.centery), min(sz, 10))
        if is_sel:
            pygame.draw.rect(surface, (100, 180, 255), sr, 2, border_radius=8)
        size_rects[sz] = sr

    # --- پالت رنگ ---
    COLOR_Y = sh - BOTTOM_H + 124
    col_label = tf2.render("رنگ:", True, (150, 150, 160))
    surface.blit(col_label, (16, COLOR_Y + 6))
    color_rects = {}
    for i, col in enumerate(gallery_editor_colors):
        cx3 = 70 + i * 34
        cr = pygame.Rect(cx3, COLOR_Y, 28, 28)
        pygame.draw.rect(surface, col, cr, border_radius=6)
        if col == gallery_editor_color:
            pygame.draw.rect(surface, (255, 255, 255), cr, 2, border_radius=6)
            pygame.draw.rect(surface, (0, 0, 0), cr.inflate(-4, -4), 1, border_radius=4)
        color_rects[i] = (cr, col)

    # --- نمایش متن در حال تایپ ---
    if gallery_editor_tool == 'text' and gallery_editor_text_input and gallery_editor_text_pos:
        tp = gallery_editor_text_pos
        pf = pygame.font.Font(main_font_path, gallery_editor_size * 2 + 10) if main_font_path else pygame.font.Font(None, gallery_editor_size * 2 + 14)
        blink_char = "|" if math.sin(time.time() * 5) > 0 else ""
        txt_surf = pf.render(gallery_editor_pending_text + blink_char, True, gallery_editor_color)
        surface.blit(txt_surf, tp)
        pygame.draw.rect(surface, gallery_editor_color,
                         pygame.Rect(tp[0]-2, tp[1]-2, txt_surf.get_width()+4, txt_surf.get_height()+4), 1)

    return {
        'back': back_rect,
        'undo': undo_rect,
        'save': save_rect,
        'img_rect': img_rect,
        'tool_rects': tool_rects,
        'size_rects': size_rects,
        'color_rects': color_rects,
    }


def open_video(path):
    """باز کردن ویدیو با opencv"""
    global video_capture, video_paused, video_playback_fps, video_last_frame_time
    global video_current_frame, video_total_frames, video_duration, video_path
    global is_video_playing, video_frame_surface, video_controls_visible, video_controls_hide_timer
    global video_current_time, video_ui_fade, video_ui_fade_target

    if not cv2_available:
        add_unimportant_notification("opencv نصب نیست — pip install opencv-python")
        return

    if video_capture:
        video_capture.release()

    try:
        cap = cv2.VideoCapture(path)
        if not cap.isOpened():
            add_unimportant_notification("خطا در باز کردن ویدیو")
            return
        video_capture = cap
        video_playback_fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
        video_total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        video_duration = video_total_frames / video_playback_fps if video_playback_fps > 0 else 0
        video_path = path
        video_current_frame = 0
        video_current_time = 0.0
        video_paused = False
        is_video_playing = True
        video_frame_surface = None
        video_last_frame_time = time.time()
        video_controls_visible = True
        video_controls_hide_timer = time.time()
        video_ui_fade = 1.0
        video_ui_fade_target = 1.0
    except Exception as e:
        print(f"Error opening video: {e}")
        add_unimportant_notification("خطا در پخش ویدیو")


def close_video():
    global video_capture, is_video_playing, video_frame_surface
    if video_capture:
        video_capture.release()
        video_capture = None
    is_video_playing = False
    video_frame_surface = None


def update_video_frame():
    """بهروزرسانی فریم ویدیو — باید هر فریم گیملوپ صدا زده شود"""
    global video_capture, video_frame_surface, video_last_frame_time
    global video_current_frame, video_current_time, is_video_playing, video_paused

    if not is_video_playing or video_paused or video_capture is None:
        return

    now = time.time()
    frame_interval = 1.0 / video_playback_fps if video_playback_fps > 0 else 1.0 / 30.0

    if now - video_last_frame_time >= frame_interval:
        ret, frame = video_capture.read()
        if ret:
            frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            video_frame_surface = pygame.surfarray.make_surface(frame_rgb.swapaxes(0, 1))
            video_current_frame += 1
            video_current_time = video_current_frame / video_playback_fps if video_playback_fps > 0 else 0.0
            video_last_frame_time = now
        else:
            # رسیدن به انتهای ویدیو — برگشت به ابتدا و مکث
            video_capture.set(cv2.CAP_PROP_POS_FRAMES, 0)
            video_current_frame = 0
            video_current_time = 0.0
            video_paused = True


def draw_video_player(surface):
    """video player - controls auto-hide"""
    global video_paused, video_controls_visible
    global video_controls_hide_timer, video_ui_fade, video_ui_fade_target
    global is_scrubbing_video, video_scrub_progress, video_capture, video_current_time

    sw, sh = surface.get_width(), surface.get_height()
    surface.fill((0, 0, 0))

    # بهروزرسانی فریم
    update_video_frame()

    # نمایش فریم — Aspect Fit
    if video_frame_surface:
        fw, fh = video_frame_surface.get_size()
        scale = min(sw / fw, sh / fh)
        nw, nh = int(fw * scale), int(fh * scale)
        scaled_frame = pygame.transform.smoothscale(video_frame_surface, (nw, nh))
        surface.blit(scaled_frame, ((sw - nw) // 2, (sh - nh) // 2))

    # مدیریت fade کنترلها (auto-hide بعد از ۳ ثانیه)
    now = time.time()
    if not video_paused and video_controls_visible and (now - video_controls_hide_timer) > 3.0:
        video_ui_fade_target = 0.0

    video_ui_fade += (video_ui_fade_target - video_ui_fade) * 0.14
    ui_alpha = int(max(0, min(255, video_ui_fade * 255)))

    if ui_alpha < 5:
        return {
            'tap_zone': pygame.Rect(0, 0, sw, sh),
            'close_btn': pygame.Rect(0, 0, 0, 0),
            'play_btn': pygame.Rect(0, 0, 0, 0),
            'seek_bar': pygame.Rect(0, 0, 0, 0),
        }

    # گرادیان تاریک پایین (برای خوانایی کنترلها)
    for i in range(130):
        a = int((i / 130) ** 1.5 * 180 * (ui_alpha / 255))
        pygame.draw.line(surface, (0, 0, 0, a) if False else (0, 0, 0), (0, sh - i - 1), (sw, sh - i - 1))
        # نمیتوان مستقیم با آلفا رسم کرد، از Surface استفاده میکنیم
    grad_surf = pygame.Surface((sw, 130), pygame.SRCALPHA)
    for i in range(130):
        a = int((i / 130) ** 1.5 * 180 * (ui_alpha / 255))
        pygame.draw.line(grad_surf, (0, 0, 0, a), (0, 130 - i - 1), (sw, 130 - i - 1))
    surface.blit(grad_surf, (0, sh - 130))

    # گرادیان بالا
    top_surf = pygame.Surface((sw, 80), pygame.SRCALPHA)
    for i in range(80):
        a = int((1 - i / 80) * 120 * (ui_alpha / 255))
        pygame.draw.line(top_surf, (0, 0, 0, a), (0, i), (sw, i))
    surface.blit(top_surf, (0, 0))

    # دکمه بستن
    close_r = pygame.Rect(14, 38, 38, 38)
    cb = pygame.Surface((38, 38), pygame.SRCALPHA)
    pygame.draw.circle(cb, (255, 255, 255, int(0.18 * ui_alpha)), (19, 19), 19)
    close_font = mf(17)
    cs = close_font.render("✕", True, (255, 255, 255))
    cs.set_alpha(ui_alpha)
    cb.blit(cs, cs.get_rect(center=(19, 19)))
    surface.blit(cb, (14, 38))

    # نام فایل
    vname = os.path.basename(video_path)
    if len(vname) > 26:
        vname = vname[:23] + "…"
    vn_font = mf(14)
    vn_surf = vn_font.render(vname, True, (255, 255, 255))
    vn_surf.set_alpha(ui_alpha)
    surface.blit(vn_surf, vn_surf.get_rect(centerx=sw // 2, top=48))

    # دکمه play/pause مرکزی
    play_cx, play_cy = sw // 2, sh // 2
    btn_r = 30
    pb = pygame.Surface((btn_r * 2 + 4, btn_r * 2 + 4), pygame.SRCALPHA)
    pygame.draw.circle(pb, (255, 255, 255, int(0.2 * ui_alpha)), (btn_r + 2, btn_r + 2), btn_r + 2)
    pygame.draw.circle(pb, (255, 255, 255, ui_alpha), (btn_r + 2, btn_r + 2), btn_r, 2)
    if video_paused:
        tri = [
            (btn_r + 2 + btn_r * 0.5, btn_r + 2),
            (btn_r + 2 - btn_r * 0.35, btn_r + 2 - btn_r * 0.5),
            (btn_r + 2 - btn_r * 0.35, btn_r + 2 + btn_r * 0.5),
        ]
        pygame.draw.polygon(pb, (255, 255, 255), [(int(p[0]), int(p[1])) for p in tri])
    else:
        bw, bh = 7, 24
        pygame.draw.rect(pb, (255, 255, 255), (btn_r + 2 - 12, btn_r + 2 - bh // 2, bw, bh), border_radius=3)
        pygame.draw.rect(pb, (255, 255, 255), (btn_r + 2 + 5, btn_r + 2 - bh // 2, bw, bh), border_radius=3)
    pb.set_alpha(ui_alpha)
    play_blit_pos = (play_cx - btn_r - 2, play_cy - btn_r - 2)
    surface.blit(pb, play_blit_pos)
    play_rect = pygame.Rect(play_cx - btn_r, play_cy - btn_r, btn_r * 2, btn_r * 2)

    # نوار seek
    seek_y = sh - 52
    seek_x = 18
    seek_w = sw - 36
    progress = (video_current_time / video_duration) if video_duration > 0 else 0.0
    if is_scrubbing_video:
        progress = video_scrub_progress

    seek_bg = pygame.Surface((seek_w, 3), pygame.SRCALPHA)
    seek_bg.fill((255, 255, 255, int(0.3 * ui_alpha)))
    surface.blit(seek_bg, (seek_x, seek_y))

    filled = int(seek_w * max(0, min(1, progress)))
    if filled > 0:
        seek_fill = pygame.Surface((filled, 3), pygame.SRCALPHA)
        seek_fill.fill((255, 255, 255, ui_alpha))
        surface.blit(seek_fill, (seek_x, seek_y))

    kx = seek_x + filled
    ky = seek_y + 1
    kr = 7 if is_scrubbing_video else 5
    pygame.draw.circle(surface, (255, 255, 255), (kx, ky), kr)

    # زمانها
    tf = mf(11)
    ct = tf.render(format_time(video_current_time), True, (210, 210, 210))
    tt = tf.render(format_time(video_duration), True, (210, 210, 210))
    ct.set_alpha(ui_alpha); tt.set_alpha(ui_alpha)
    surface.blit(ct, (seek_x, seek_y + 10))
    surface.blit(tt, tt.get_rect(right=seek_x + seek_w, top=seek_y + 10))

    seek_rect = pygame.Rect(seek_x, seek_y - 22, seek_w, 46)
    return {
        'tap_zone': pygame.Rect(0, 80, sw, sh - 160),
        'play_btn': play_rect,
        'seek_bar': seek_rect,
        'close_btn': close_r,
    }


def draw_low_battery_warning(surface):
    """docstring"""
    card_height = 180
    # محاسبه پیشرفت انیمیشن با حالت نرم (ease-out)
    ease_progress = (1 - math.cos(low_battery_warning_progress * math.pi)) / 2
    # محاسبه موقعیت عمودی کارت بر اساس پیشرفت انیمیشن
    y_pos = SCREEN_HEIGHT - (card_height + 20) * ease_progress
    card_rect = pygame.Rect(20, y_pos, SCREEN_WIDTH - 40, card_height)

    # تعیین رنگها بر اساس حالت تاریک یا روشن
    bg_color = (45, 45, 45) if is_dark_mode else (240, 240, 240)
    main_text_color = WHITE if is_dark_mode else BLACK
    sub_text_color = (180, 180, 180) if is_dark_mode else (100, 100, 100)
    understand_btn_bg = (80, 80, 80) if is_dark_mode else (210, 210, 210)
    understand_text_color = WHITE if is_dark_mode else BLACK
    saver_btn_bg = BLUE

    # رسم بدنه اصلی کارت
    draw_rounded_rect(surface, card_rect, bg_color, 20)

    # رسم آیکون باتری
    batt_body_rect = pygame.Rect(0, 0, 40, 20)
    batt_body_rect.center = (card_rect.centerx, card_rect.top + 35)
    batt_tip_rect = pygame.Rect(batt_body_rect.right, batt_body_rect.centery - 4, 4, 8)
    pygame.draw.rect(surface, (80, 80, 80), batt_body_rect, border_radius=4)
    pygame.draw.rect(surface, (80, 80, 80), batt_tip_rect, border_radius=2)
    batt_level_rect = pygame.Rect(batt_body_rect.left + 3, batt_body_rect.top + 3, 8, 14)
    pygame.draw.rect(surface, (255, 80, 80), batt_level_rect, border_radius=2)

    # رسم متون فارسی
    main_text = "سطح باتری کمتر از ۲۰٪ است"
    sub_text = "برای افزودن ۶ ساعت و ۹ دقیقه، ذخیره باتری را روشن کنید."
    main_text_surf = render_persian_text(main_text, text_font, main_text_color)
    sub_text_surf = render_persian_text(sub_text, status_bar_font, sub_text_color)
    surface.blit(main_text_surf, main_text_surf.get_rect(center=(card_rect.centerx, card_rect.top + 75)))
    surface.blit(sub_text_surf, sub_text_surf.get_rect(center=(card_rect.centerx, card_rect.top + 100)))

    # رسم دکمهها
    understand_btn_rect = pygame.Rect(card_rect.left + 20, card_rect.bottom - 60, (card_rect.width - 60) / 2, 40)
    saver_btn_rect = pygame.Rect(understand_btn_rect.right + 20, card_rect.bottom - 60, (card_rect.width - 60) / 2, 40)
    draw_rounded_rect(surface, understand_btn_rect, understand_btn_bg, 15)
    draw_rounded_rect(surface, saver_btn_rect, saver_btn_bg, 15)

    understand_text_surf = render_persian_text("متوجه شدم", text_font, understand_text_color)
    saver_text_surf = render_persian_text("ذخیره باتری", text_font, WHITE)
    surface.blit(understand_text_surf, understand_text_surf.get_rect(center=understand_btn_rect.center))
    surface.blit(saver_text_surf, saver_text_surf.get_rect(center=saver_btn_rect.center))

    # بازگرداندن Rect دکمهها برای بررسی کلیک
    return understand_btn_rect, saver_btn_rect

def draw_status_bar(color=WHITE, alpha=255):
    bar_height = sc(30)
    final_color = (color[0], color[1], color[2], alpha)
    
    try:
        # رسم ساعت در سمت چپ
        time_surface = status_bar_font.render(datetime.datetime.now().strftime("%H:%M"), True, final_color)
        time_surface.set_alpha(alpha)
        screen.blit(time_surface, time_surface.get_rect(midleft=(sc(15), bar_height / 2)))
        
        # رسم آیکون باتری در سمت راست
        battery_info = psutil.sensors_battery()
        if battery_info:
            # موقعیت گوشه بالا-راست آیکون
            icon_pos = (SCREEN_WIDTH - sc(15), bar_height / 2 - sc(7)) 
            draw_battery_icon_status_bar(screen, icon_pos, battery_info, final_color)

    except (AttributeError, TypeError):
        # این خطا ممکن است در فریمهای اولیه رخ دهد
        pass

def draw_home_indicator(color=WHITE):
    draw_rounded_rect(screen, pygame.Rect((SCREEN_WIDTH - sc(130)) / 2, SCREEN_HEIGHT - sc(15), sc(130), sc(5)), color, 2.5)

def draw_files_icon(surface, rect):
    # پسزمینه سفید
    surface.fill((255, 255, 255))
    
    # رسم شکل پوشه آبی رنگ
    folder_color = (70, 170, 255)
    folder_rect = rect.inflate(-rect.width * 0.2, -rect.height * 0.3)
    folder_rect.centery = rect.height / 2 + 5
    
    # قسمت بالایی پوشه
    top_part_rect = pygame.Rect(folder_rect.x, folder_rect.y, folder_rect.width, folder_rect.height * 0.8)
    draw_rounded_rect(surface, top_part_rect, folder_color, 8)
    
    # زبانه پوشه
    tab_rect = pygame.Rect(folder_rect.x + 10, folder_rect.y - 5, folder_rect.width * 0.3, 10)
    draw_rounded_rect(surface, tab_rect, folder_color, 4)

def draw_gallery_icon(surface, rect):
    # پسزمینه سفید مشابه آیکونهای دیگر
    draw_rounded_rect(surface, surface.get_rect(), (255, 255, 255), 0) # radius 0 for the base
    
    center_x, center_y = rect.width / 2, rect.height / 2
    petal_width = rect.width * 0.2
    petal_height = rect.height * 0.45
    colors = [
        (255, 60, 50),   # Red
        (255, 150, 0),  # Orange
        (255, 220, 0),  # Yellow
        (80, 210, 50),   # Green
        (0, 180, 255),  # Light Blue
        (0, 100, 255),  # Blue
        (150, 60, 255), # Purple
        (255, 80, 180)  # Pink
    ]
    
    num_petals = len(colors)
    angle_step = 360 / num_petals
    
    for i, color in enumerate(colors):
        angle = i * angle_step
        petal_surf = pygame.Surface((petal_width, petal_height), pygame.SRCALPHA)
        draw_rounded_rect(petal_surf, petal_surf.get_rect(), color, petal_width / 2)
        
        rotated_petal = pygame.transform.rotate(petal_surf, -angle)
        
        # محاسبه موقعیت برای هر گلبرگ
        radius = rect.width * 0.15
        offset_x = radius * math.cos(math.radians(angle + 90))
        offset_y = radius * math.sin(math.radians(angle + 90))
        
        petal_rect = rotated_petal.get_rect(center=(center_x + offset_x, center_y - offset_y))
        surface.blit(rotated_petal, petal_rect)

def draw_settings_icon(surface, rect, extra_rotation=0):
    draw_gradient_background(surface, (200, 200, 200), (150, 150, 150))
    inner_size = rect.width * 0.5; inner_rect = pygame.Rect(0, 0, inner_size, inner_size); inner_rect.center = (rect.width / 2, rect.height / 2)
    gear_surface_back = pygame.Surface((inner_size, inner_size), pygame.SRCALPHA); draw_rounded_rect(gear_surface_back, gear_surface_back.get_rect(), (210, 210, 210), 4)
    rotated_gear_back = pygame.transform.rotate(gear_surface_back, 45); surface.blit(rotated_gear_back, rotated_gear_back.get_rect(center=inner_rect.center))
    gear_surface_front = pygame.Surface((inner_size, inner_size), pygame.SRCALPHA); draw_rounded_rect(gear_surface_front, gear_surface_front.get_rect(), (255, 255, 255), 4)
    rotated_gear_front = pygame.transform.rotate(gear_surface_front, extra_rotation); surface.blit(rotated_gear_front, rotated_gear_front.get_rect(center=inner_rect.center))

def draw_notes_icon(surface, rect, anim_progress=0.0):
    draw_gradient_background(surface, (255, 220, 100), (255, 180, 50))
    line_width, line_height, spacing = rect.width * 0.6, 5, 12; scale = 1.0
    if is_notes_icon_animation_active: scale = 1.0 - (anim_progress * 2) if anim_progress < 0.5 else (anim_progress - 0.5) * 2
    for i in range(3):
        line_rect = pygame.Rect(0, 0, line_width * scale, line_height); line_rect.center = (rect.width/2, rect.height/2 + (i - 1) * spacing)
        draw_rounded_rect(surface, line_rect, WHITE, 2)

def draw_music_icon(surface, rect, anim_progress=0.0):
    draw_gradient_background(surface, (255, 50, 80), (230, 30, 50))
    scale = 1.0
    if is_music_icon_animation_active:
        progress = (1 - math.cos(anim_progress * math.pi)) / 2
        scale = 1.0 - 0.3 * math.sin(progress * math.pi)
    center_x, center_y = rect.width / 2, rect.height / 2
    note_head_radius = int(rect.width * 0.15 * scale)
    stem_width = 7 * scale; stem_height = rect.height * 0.5 * scale
    note1_head_center = (center_x - rect.width*0.1, center_y + rect.height*0.2)
    pygame.draw.circle(surface, WHITE, note1_head_center, note_head_radius)
    stem1_rect = pygame.Rect(note1_head_center[0] + note_head_radius - stem_width, note1_head_center[1] - stem_height, stem_width, stem_height)
    pygame.draw.rect(surface, WHITE, stem1_rect)
    note2_head_center = (center_x + rect.width*0.2, center_y + rect.height*0.15)
    pygame.draw.circle(surface, WHITE, note2_head_center, note_head_radius)
    stem2_rect = pygame.Rect(note2_head_center[0] + note_head_radius - stem_width, note2_head_center[1] - stem_height, stem_width, stem_height)
    pygame.draw.rect(surface, WHITE, stem2_rect)
    beam_height = 8 * scale
    beam1 = pygame.Rect(stem1_rect.centerx, stem1_rect.top, stem2_rect.centerx - stem1_rect.centerx, beam_height)
    beam2 = pygame.Rect(stem1_rect.centerx, stem1_rect.top + beam_height + 3, stem2_rect.centerx - stem1_rect.centerx, beam_height)
    draw_rounded_rect(surface, beam1, WHITE, 3 * scale)
    draw_rounded_rect(surface, beam2, WHITE, 3 * scale)

def draw_browser_icon(surface, rect, anim_progress=0.0):
    draw_gradient_background(surface, (0, 122, 255), (0, 199, 255))
    center_x, center_y = rect.width / 2, rect.height / 2
    radius = rect.width * 0.3
    if is_browser_icon_animation_active:
        progress = (1 - math.cos(anim_progress * math.pi)) / 2
        radius *= 1.0 + 0.2 * math.sin(progress * math.pi)
    pygame.draw.circle(surface, WHITE, (center_x, center_y), radius)

def draw_messenger_icon(surface, rect, anim_progress=0.0):
    """آیکون پیام‌رسان — شبیه Messages iOS با حباب گفتگو"""
    # پس‌زمینه سبز (مثل iMessage)
    draw_gradient_background(surface, (52, 199, 89), (0, 168, 60))
    cx, cy = rect.width / 2, rect.height / 2
    w, h = rect.width, rect.height

    # انیمیشن pulse
    scale_f = 1.0
    if anim_progress > 0:
        scale_f = 1.0 + 0.08 * math.sin(anim_progress * math.pi)

    bw = w * 0.62 * scale_f
    bh = h * 0.52 * scale_f
    bx = cx - bw / 2
    by = cy - bh / 2 - h * 0.03

    # حباب اصلی (گرد)
    bubble_surf = pygame.Surface((int(bw), int(bh)), pygame.SRCALPHA)
    pygame.draw.ellipse(bubble_surf, (255, 255, 255), bubble_surf.get_rect())
    surface.blit(bubble_surf, (int(bx), int(by)))

    # دم حباب (مثلث کوچک پایین چپ)
    tail_pts = [
        (int(cx - bw * 0.15), int(by + bh * 0.85)),
        (int(cx - bw * 0.38), int(by + bh * 1.22)),
        (int(cx - bw * 0.02), int(by + bh * 0.96)),
    ]
    pygame.draw.polygon(surface, (255, 255, 255), tail_pts)

    # نقطه‌های داخل حباب (اشاره به typing indicator)
    dot_y = int(cy - h * 0.03)
    dot_r = max(2, int(w * 0.045))
    dot_gap = int(w * 0.13)
    for i in range(3):
        dx2 = int(cx - dot_gap + i * dot_gap)
        pygame.draw.circle(surface, (52, 199, 89), (dx2, dot_y), dot_r)

def draw_folder_icon(surface, rect, folder):
    draw_gradient_background(surface, (180, 190, 220), (140, 150, 180))
    inner_padding = 5; preview_size = (rect.width - 3 * inner_padding) / 2
    for i, item in enumerate(folder['contains'][:4]):
        row, col = divmod(i, 2)
        preview_rect = pygame.Rect(inner_padding + col * (preview_size + inner_padding), inner_padding + row * (preview_size + inner_padding), preview_size, preview_size)
        preview_surf = pygame.Surface(preview_rect.size, pygame.SRCALPHA)
        draw_icon_base(preview_surf, item, preview_surf.get_rect())
        surface.blit(preview_surf, preview_rect.topleft)

def draw_icon_base(surface, icon, rect, scale=1.0, alpha=255):
    final_scale = scale
    if icon == pressed_icon:
        click_scale = 1.0 - 0.1 * pressed_icon_animation_progress
        final_scale *= click_scale

    # (اصلاح شده) اندازه سطح داخلی را از rect ورودی بگیرید
    icon_surface = pygame.Surface(rect.size, pygame.SRCALPHA)

    if icon['type'] == 'app':
        if icon['name'] == 'settings':
            rotation = icon_animation_progress * 360 * (1 - (1-icon_animation_progress)**4) if is_icon_animation_active and icon == animating_icon else 0
            draw_settings_icon(icon_surface, icon_surface.get_rect(), extra_rotation=rotation)
        elif icon['name'] == 'notes':
            progress = notes_icon_animation_progress if is_notes_icon_animation_active and icon == animating_notes_icon else 0.0
            draw_notes_icon(icon_surface, icon_surface.get_rect(), anim_progress=progress)
        elif icon['name'] == 'music':
            progress = music_icon_animation_progress if is_music_icon_animation_active and icon == animating_music_icon else 0.0
            draw_music_icon(icon_surface, icon_surface.get_rect(), anim_progress=progress)
        elif icon['name'] == 'browser':
            progress = browser_icon_animation_progress if is_browser_icon_animation_active and icon == animating_browser_icon else 0.0
            draw_browser_icon(icon_surface, icon_surface.get_rect(), anim_progress=progress)
        elif icon['name'] == 'gallery':
            draw_gallery_icon(icon_surface, icon_surface.get_rect())
        elif icon['name'] == 'files':
            draw_files_icon(icon_surface, icon_surface.get_rect())
        elif icon['name'] == 'messenger':
            draw_messenger_icon(icon_surface, icon_surface.get_rect())
        else: icon_surface.fill(icon.get('color', (100, 100, 100)))

    elif icon['type'] == 'folder':
        draw_folder_icon(icon_surface, icon_surface.get_rect(), icon)

    # (جدید) منطق رسم برای ویجت
    elif icon['type'] == 'widget':
        if icon.get('widget_type') == 'clock':
            draw_clock_widget(icon_surface, icon_surface.get_rect())

    if icon == pressed_icon:
        darken_alpha = int(80 * pressed_icon_animation_progress)
        darken_layer = pygame.Surface(rect.size, pygame.SRCALPHA)
        darken_layer.fill((0, 0, 0, darken_alpha))
        icon_surface.blit(darken_layer, (0, 0))

    # (اصلاح شده) برای ویجتها از ماسک با شعاع بیشتری استفاده میکنیم
    corner_radius = 22 if icon['type'] == 'widget' else 18
    mask = pygame.Surface(rect.size, pygame.SRCALPHA); draw_rounded_rect(mask, mask.get_rect(), (255, 255, 255, 255), corner_radius)
    icon_surface.blit(mask, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)

    if final_scale != 1.0:
        scaled_size = (int(rect.width * final_scale), int(rect.height * final_scale))
        icon_surface = pygame.transform.smoothscale(icon_surface, scaled_size)

    icon_surface.set_alpha(alpha)
    surface.blit(icon_surface, icon_surface.get_rect(center=rect.center))

    if icon == folder_hover_target and folder_highlight_alpha > 0:
        highlight_surface = pygame.Surface(rect.size, pygame.SRCALPHA)
        highlight_color = (255, 255, 255, int(folder_highlight_alpha))
        draw_rounded_rect(highlight_surface, highlight_surface.get_rect(), highlight_color, 22)
        pygame.draw.rect(highlight_surface, (0,0,0,0), highlight_surface.get_rect().inflate(-8, -8), border_radius=18)
        surface.blit(highlight_surface, rect.topleft)

# (اصلاح شده) تابع رسم صفحه قفل با قابلیت جلوه عمق
def draw_lock_screen(offset_y):
    if current_lock_screen_wallpaper_image:
        screen.blit(current_lock_screen_wallpaper_image, (0, offset_y))
    else:
        draw_gradient_background(screen, (40, 0, 80), (10, 20, 100))
    
    now = datetime.datetime.now()
    if lock_screen_style == 'default':
        # استفاده از فونت بزرگ‌تر
        time_surf = large_clock_font.render("".join([persian_digits.get(c, c) for c in now.strftime("%H:%M")]), True, WHITE)
        # قرار دادن در مرکز دقیق صفحه (حذف -170)
        screen.blit(time_surf, time_surf.get_rect(center=(SCREEN_WIDTH/2, SCREEN_HEIGHT/2 + offset_y - 40)))
        
        date_surf = text_font.render(now.strftime("%A, %B %d"), True, WHITE)
        screen.blit(date_surf, date_surf.get_rect(center=(SCREEN_WIDTH/2, SCREEN_HEIGHT/2 + 60 + offset_y)))
        
    elif lock_screen_style == 'bottom_right':
        time_surf = clock_font.render("".join([persian_digits.get(c, c) for c in now.strftime("%H:%M")]), True, WHITE)
        time_rect = time_surf.get_rect(bottomright=(SCREEN_WIDTH - 30, SCREEN_HEIGHT - 80 + offset_y))
        screen.blit(time_surf, time_rect)
        date_surf = text_font.render(now.strftime("%A, %B %d"), True, WHITE)
        screen.blit(date_surf, date_surf.get_rect(bottomright=(SCREEN_WIDTH - 30, time_rect.top - 5 + offset_y)))
        
    elif lock_screen_style == 'stacked':
        hour_surf = clock_font.render("".join([persian_digits.get(c, c) for c in now.strftime("%H")]), True, WHITE)
        minute_surf = clock_font.render("".join([persian_digits.get(c, c) for c in now.strftime("%M")]), True, WHITE)
        hour_rect = hour_surf.get_rect(center=(SCREEN_WIDTH/2, SCREEN_HEIGHT/2 - 50 + offset_y))
        minute_rect = minute_surf.get_rect(center=(SCREEN_WIDTH/2, hour_rect.bottom + offset_y))
        screen.blit(hour_surf, hour_rect)
        screen.blit(minute_surf, minute_rect)
        date_surf = text_font.render(now.strftime("%A, %B %d"), True, WHITE)
        screen.blit(date_surf, date_surf.get_rect(center=(SCREEN_WIDTH/2, minute_rect.bottom + 40 + offset_y)))

    if is_depth_effect_enabled and current_lock_screen_subject_image:
        screen.blit(current_lock_screen_subject_image, (0, offset_y))

    swipe_text = render_persian_text("برای باز کردن، به بالا بکشید", text_font, LIGHT_GRAY)
    screen.blit(swipe_text, swipe_text.get_rect(center=(SCREEN_WIDTH/2, SCREEN_HEIGHT - 50 + offset_y)))

def draw_home_screen_content(surface, offset, scale=1.0, alpha=255, is_folder_view_active=False):
    surface.fill((0, 0, 0, 0))
    start_x = (SCREEN_WIDTH - (icons_per_row * icon_size + (icons_per_row - 1) * icon_padding)) / 2; start_y = 60

    # (اصلاح شده) اندازه فعلی آیکون را در ابتدای حلقه محاسبه میکنیم
    current_icon_base_size = int(icon_size * edit_mode_scale)
    size_diff = icon_size - current_icon_base_size

    icon_lists = [icons[page] for page in range(num_home_pages)] + [dock_icons]
    for container_idx, container in enumerate(icon_lists):
        is_dock = container_idx == len(icon_lists) - 1
        if is_dock:
            # (اصلاح شده) داک نمیتواند ویجت داشته باشد، پس محاسبات آن ساده است
            num_dock_icons = len(dock_icons); total_dock_width = num_dock_icons * icon_size + (num_dock_icons - 1) * icon_padding
            dock_start_x = dock_rect.centerx - total_dock_width / 2

        for i, icon in enumerate(container):
            is_widget = icon.get('type') == 'widget'

            # (جدید) محاسبه اندازه واقعی آیکون یا ویجت
            item_width, item_height = icon_size, icon_size
            if is_widget:
                size = icon.get('size', (1, 1))
                item_width = size[0] * icon_size + (size[0] - 1) * icon_padding
                item_height = size[1] * icon_size + (size[1] - 1) * icon_padding

            current_item_width = int(item_width * edit_mode_scale)
            current_item_height = int(item_height * edit_mode_scale)

            if is_dock:
                target_x, target_y = dock_start_x + i * (icon_size + icon_padding), dock_rect.centery - icon_size / 2
                current_page_offset = 0
            else:
                page = container_idx # (اصلاح شده)
                target_x = start_x + icon['col'] * (icon_size + icon_padding)
                target_y = start_y + icon['row'] * (icon_size + icon_padding)
                current_page_offset = (page - home_page_index) * SCREEN_WIDTH + offset

            if icon != selected_icon or not is_dragging_icon:
                icon['pos'] = [a + (b - a) * 0.3 for a, b in zip(icon['pos'], (target_x, target_y))]

            icon_x, icon_y = icon['pos'][0] + current_page_offset, icon['pos'][1]

            if is_edit_mode and (icon != selected_icon or not is_dragging_icon) and not is_folder_view_active:
                angle = time.time()*8 + (icon.get('row',0)+icon.get('col',0)+i)*2
                icon_x += math.sin(angle)*1.5
                icon_y += math.cos(angle*0.8)*1.5
            
            # (جدید) مرکز کردن ویجتها بر اساس اندازه بزرگترشان
            rect_center_x = icon_x + current_item_width / 2
            rect_center_y = icon_y + current_item_height / 2

            icon['rect'] = pygame.Rect(0, 0, current_item_width, current_item_height)
            icon['rect'].center = (rect_center_x, rect_center_y)

            if -current_item_width < icon['rect'].x < SCREEN_WIDTH:
                draw_icon_base(surface, icon, icon['rect'])

    if scale != 1.0 or alpha != 255:
        scaled_surface = pygame.transform.smoothscale(surface, (int(SCREEN_WIDTH * scale), int(SCREEN_HEIGHT * scale))); scaled_surface.set_alpha(alpha)
        return scaled_surface, scaled_surface.get_rect(center=(SCREEN_WIDTH/2, SCREEN_HEIGHT/2))
    return surface, surface.get_rect(topleft=(0,0))

def draw_home_screen_static_elements():
    final_dock_surface = pygame.Surface(dock_rect.size, pygame.SRCALPHA)

    try:
        # کپی گرفتن و حذف کانال آلفا برای جلوگیری از باگ شفافیت
        dock_bg_capture = screen.subsurface(dock_rect).copy().convert()
        w, h = dock_bg_capture.get_size()
        
        # مقیاس بسیار کوچک برای ایجاد تاری شدید (مقیاس ۱ به ۱۵)
        sw, sh = max(1, w // 15), max(1, h // 15)
        s1 = pygame.transform.smoothscale(dock_bg_capture, (sw, sh))
        blurred = pygame.transform.smoothscale(s1, (w, h))
        
    except (ValueError, Exception):
        blurred = pygame.Surface(dock_rect.size)
        blurred.fill((50, 50, 50))

    final_dock_surface.blit(blurred, (0, 0))

    # لایه شیشه‌ای تیره‌تر برای خوانایی بهتر آیکون‌ها
    overlay_color = (255, 255, 255, 40) if not is_dark_mode else (30, 30, 40, 120)
    draw_rounded_rect(final_dock_surface, final_dock_surface.get_rect(), overlay_color, 25)

    rim_surf = pygame.Surface((dock_rect.width, 1), pygame.SRCALPHA)
    rim_color = (255, 255, 255, 90) if not is_dark_mode else (255, 255, 255, 40)
    rim_surf.fill(rim_color)
    final_dock_surface.blit(rim_surf, (0, 0))

    mask = pygame.Surface(dock_rect.size, pygame.SRCALPHA)
    draw_rounded_rect(mask, mask.get_rect(), (255, 255, 255, 255), 25)
    final_dock_surface.blit(mask, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)

    screen.blit(final_dock_surface, dock_rect.topleft)
    draw_home_indicator()

def draw_page_indicators(current_page, total_pages):
    indicator_radius, spacing = 4, 15; total_width = (total_pages - 1) * spacing
    start_x = (SCREEN_WIDTH - total_width) / 2; y_pos = SCREEN_HEIGHT - 110
    for i in range(total_pages):
        pygame.draw.circle(screen, WHITE if i == current_page else GRAY, (int(start_x + i * spacing), y_pos), indicator_radius)

def draw_settings_main_screen(surface):
    surface.fill(get_current_color('settings_bg'))
    
    text_color = get_current_color('settings_title')
    btn_color = get_current_color('settings_button_bg')
    btn_text_color = get_current_color('settings_button_text')
    sub_color = (150, 150, 155) if not is_dark_mode else (130, 130, 138)
    
    # عنوان
    title_font = mf(28)
    title = render_persian_text(get_string("settings"), title_font, text_color)
    surface.blit(title, title.get_rect(right=SCREEN_WIDTH - 20, top=50))

    # تعریف دکمهها با آیکون و زیرعنوان
    buttons_config = [
        {
            'key': 'wallpaper_btn',
            'label': get_string("wallpaper"),
            'icon': '🖼',
            'sub': 'تغییر پسزمینه',
            'rect': pygame.Rect(16, 115, SCREEN_WIDTH - 32, 58),
            'group_start': True,
            'group_title': 'ظاهر',
        },
        {
            'key': 'display_btn',
            'label': get_string("display"),
            'icon': '☀',
            'sub': 'روشنایی، تم',
            'rect': pygame.Rect(16, 174, SCREEN_WIDTH - 32, 58),
        },
        {
            'key': 'lock_screen_btn',
            'label': get_string("lock_screen"),
            'icon': '🔒',
            'sub': 'صفحه قفل، جلوه عمق',
            'rect': pygame.Rect(16, 233, SCREEN_WIDTH - 32, 58),
            'group_end': True,
        },
        {
            'key': 'lang_btn',
            'label': get_string("language_region"),
            'icon': '🌐',
            'sub': current_language_name,
            'rect': pygame.Rect(16, 310, SCREEN_WIDTH - 32, 58),
            'group_start': True,
            'group_title': 'عمومی',
            'group_end': True,
        },
        {
            'key': 'battery_btn',
            'label': 'باتری',
            'icon': '🔋',
            'sub': 'وضعیت باتری، بهینه‌سازی',
            'rect': pygame.Rect(16, 387, SCREEN_WIDTH - 32, 58),
            'group_start': True,
            'group_title': 'دستگاه',
            'group_end': True,
        },
        {
            'key': 'about_btn',
            'label': get_string("about"),
            'icon': 'ℹ',
            'sub': 'ParsOS NEXT',
            'rect': pygame.Rect(16, 464, SCREEN_WIDTH - 32, 58),
            'group_start': True,
            'group_title': 'درباره',
            'group_end': True,
        },
    ]

    clickable_rects = {}
    group_title_font = mf(13)
    icon_font = mf(22)
    label_font = mf(16)
    sub_font = mf(12)

    for cfg in buttons_config:
        rect = cfg['rect']

        # عنوان گروه
        if cfg.get('group_start') and cfg.get('group_title'):
            gt = render_persian_text(cfg['group_title'], group_title_font, sub_color)
            surface.blit(gt, gt.get_rect(right=SCREEN_WIDTH - 20, bottom=rect.top - 6))

        # گوشههای گرد گروه
        if cfg.get('group_start') and cfg.get('group_end'):
            radius = 12
        elif cfg.get('group_start'):
            radius = 12
        elif cfg.get('group_end'):
            radius = 12
        else:
            radius = 0

        draw_rounded_rect(surface, rect, btn_color, 12)
        
        # افکت کلیک
        if active_button_rect and active_button_rect == rect:
            hl = pygame.Surface(rect.size, pygame.SRCALPHA)
            hl.fill((0, 0, 0, 25) if not is_dark_mode else (255, 255, 255, 15))
            surface.blit(hl, rect.topleft)

        # جداکننده بین دکمههای همگروه
        if not cfg.get('group_start') and not cfg.get('group_end'):
            sep_col = (230, 230, 233) if not is_dark_mode else (55, 55, 62)
            pygame.draw.line(surface, sep_col, (rect.left + 60, rect.top), (rect.right, rect.top))

        # آیکون
        icon_s = icon_font.render(cfg['icon'], True, btn_text_color)
        surface.blit(icon_s, icon_s.get_rect(right=rect.right - 14, centery=rect.centery))

        # لیبل
        label_s = render_persian_text(cfg['label'], label_font, btn_text_color)
        surface.blit(label_s, label_s.get_rect(left=rect.left + 16, top=rect.top + 10))

        # زیرعنوان
        if cfg.get('sub'):
            sub_s = render_persian_text(cfg['sub'], sub_font, sub_color)
            surface.blit(sub_s, sub_s.get_rect(left=rect.left + 16, bottom=rect.bottom - 10))

        # فلش
        arr_font = mf(16)
        arr_s = arr_font.render("›", True, sub_color)
        surface.blit(arr_s, arr_s.get_rect(right=rect.right - 10, centery=rect.centery))

        clickable_rects[cfg['key']] = rect

    return clickable_rects

# (جدید) صفحه تنظیمات زبان
def draw_settings_language_screen(surface):
    surface.fill(get_current_color('settings_bg'))
    text_color = get_current_color('settings_title')
    btn_color = get_current_color('settings_button_bg')
    btn_text_color = get_current_color('settings_button_text')

    # دکمه بازگشت
    back_btn_text = render_persian_text(get_string("back", "< بازگشت"), text_font, BLUE)
    back_btn_rect = back_btn_text.get_rect(left=20, top=55)
    surface.blit(back_btn_text, back_btn_rect)

    # عنوان
    title = render_persian_text(get_string("language_region"), settings_title_font, text_color)
    surface.blit(title, title.get_rect(centerx=surface.get_width()/2, top=50))

    # دکمه انتخاب زبان
    select_lang_rect = pygame.Rect(30, 120, surface.get_width() - 60, 50)
    draw_rounded_rect(surface, select_lang_rect, btn_color, 10)

    # متن سمت راست (لیبل)
    label_text = render_persian_text(get_string("language"), text_font, btn_text_color)
    surface.blit(label_text, label_text.get_rect(right=select_lang_rect.right - 15, centery=select_lang_rect.centery))

    # متن سمت چپ (زبان فعلی)
    # (از render_persian_text استفاده میکنیم تا نام زبان به درستی نمایش داده شود)
    current_lang_text = render_persian_text(current_language_name, text_font, btn_text_color)
    surface.blit(current_lang_text, current_lang_text.get_rect(left=select_lang_rect.left + 15, centery=select_lang_rect.centery))

    # افکت کلیک
    if active_button_rect == back_btn_rect:
        surf = pygame.Surface(back_btn_rect.size, pygame.SRCALPHA); surf.fill((0,0,0,40)); surface.blit(surf, back_btn_rect.topleft)
    if active_button_rect == select_lang_rect:
        surf = pygame.Surface(select_lang_rect.size, pygame.SRCALPHA); surf.fill((0,0,0,40)); surface.blit(surf, select_lang_rect.topleft)

    return {'back_btn': back_btn_rect, 'select_lang_btn': select_lang_rect}

# (جدید) تابع رسم پنل انتخاب زبان
# (جدید) تابع رسم پنل انتخاب زبان
def draw_language_picker(surface, progress):
    """language picker modal"""
    global language_picker_start_rect
    if progress <= 0: return {} # دیکشنری خالی برای rectها برمیگرداند

    # رسم پسزمینه بلور شده
    if language_picker_blurred_bg:
        language_picker_blurred_bg.set_alpha(int(255 * progress))
        surface.blit(language_picker_blurred_bg, (0, 0))

    # انیمیشن نرم (ease-out-cubic)
    ease_progress = 1 - pow(1 - progress, 3)

    # --- (جدید) محاسبه انیمیشن موقعیت و اندازه ---
    # ابعاد نهایی پنل
    end_rect = pygame.Rect(0, 0, 340, 340) 
    end_rect.center = surface.get_rect().center
    
    start_rect = language_picker_start_rect
    if start_rect is None:
        # اگر Rect شروع تنظیم نشده بود (مثلاً در فریم اول)
        start_rect = end_rect.copy()

    # درونیابی (Interpolation) موقعیت و اندازه
    current_x = start_rect.x + (end_rect.x - start_rect.x) * ease_progress
    current_y = start_rect.y + (end_rect.y - start_rect.y) * ease_progress
    current_width = start_rect.width + (end_rect.width - start_rect.width) * ease_progress
    current_height = start_rect.height + (end_rect.height - start_rect.height) * ease_progress
    panel_rect = pygame.Rect(current_x, current_y, current_width, current_height)
    
    # درونیابی شعاع گوشهها
    start_radius = 10 # شعاع دکمه
    end_radius = 20   # شعاع نهایی پنل
    current_radius = start_radius + (end_radius - start_radius) * ease_progress
    # --- پایان بخش جدید ---

    # رسم بدنه پنل
    panel_surface = pygame.Surface(panel_rect.size, pygame.SRCALPHA)
    bg_color = (250, 250, 250) if not is_dark_mode else (45, 45, 55)

    # اعمال آلفا بر اساس انیمیشن
    final_bg_color = (*bg_color, int(230 * ease_progress))
    # (اصلاح شده) استفاده از شعاع داینامیک
    draw_rounded_rect(panel_surface, panel_surface.get_rect(), final_bg_color, current_radius)

    clickable_rects = {}

    # رسم محتوا فقط زمانی که انیمیشن نزدیک به پایان است
    if ease_progress > 0.9:
        content_alpha = (ease_progress - 0.9) / 0.1 * 255 # محو شدن نرم
        text_color = get_current_color('context_menu_text')

        title_text = get_string("select_language", "انتخاب زبان")
        title_surf = render_persian_text(title_text, settings_title_font, text_color)
        title_surf.set_alpha(content_alpha)
        panel_surface.blit(title_surf, title_surf.get_rect(centerx=panel_rect.width / 2, top=20))

        y_pos = 70
        item_height = 40
        padding = 10

        for lang_code, lang_name in SUPPORTED_LANGUAGES.items():
            # (اصلاح شده) اطمینان از اینکه آیتمها در پنل کوچکشده رسم نمیشوند
            if panel_rect.width < 200: continue 

            item_rect_local = pygame.Rect(20, y_pos, panel_rect.width - 40, item_height)
            
            # رسم دکمه زبان
            lang_text_surf = render_persian_text(lang_name, text_font, text_color)
            lang_text_surf.set_alpha(content_alpha)
            panel_surface.blit(lang_text_surf, lang_text_surf.get_rect(center=item_rect_local.center))

            # هایلایت زبان فعلی
            if lang_code == current_language:
                highlight_rect = item_rect_local.inflate(0, -4) # کمی کوچکتر
                draw_rounded_rect(panel_surface, highlight_rect, (BLUE[0], BLUE[1], BLUE[2], int(100 * content_alpha / 255)), 10)

            screen_rect = item_rect_local.move(panel_rect.topleft)
            clickable_rects[f'lang_{lang_code}'] = screen_rect

            y_pos += item_height + padding

    # رسم پنل نهایی روی صفحه
    panel_surface.set_alpha(int(255 * ease_progress)) # آلفای کلی پنل
    surface.blit(panel_surface, panel_rect.topleft)

    return clickable_rects

def draw_settings_wallpaper_screen(surface):
    global wallpaper_preset_rects; wallpaper_preset_rects.clear()
    surface.fill(get_current_color('settings_bg')); text_color = get_current_color('settings_title')
    back_btn_text = render_persian_text(get_string("back", "< بازگشت"), text_font, BLUE); back_btn_rect = back_btn_text.get_rect(left=20, top=55); surface.blit(back_btn_text, back_btn_rect)
    title = render_persian_text(get_string("wallpaper", "پسزمینه"), settings_title_font, text_color); surface.blit(title, title.get_rect(centerx=surface.get_width()/2, top=50))
    preview_size = (SCREEN_WIDTH - 90) / 2
    clickable_rects = {'back_btn': back_btn_rect}
    for i, (top, bottom) in enumerate(wallpaper_presets):
        row, col = divmod(i, 2); rect = pygame.Rect(30 + col * (preview_size + 30), 120 + row * (preview_size * 1.3), preview_size, preview_size * 1.1)
        preview_surface = pygame.Surface(rect.size, pygame.SRCALPHA); draw_rounded_rect(preview_surface, preview_surface.get_rect(), WHITE, 10)
        gradient_surface = pygame.Surface(rect.size); draw_gradient_background(gradient_surface, top, bottom)
        preview_surface.blit(gradient_surface, (0, 0), special_flags=pygame.BLEND_RGBA_MULT); surface.blit(preview_surface, rect.topleft)
        wallpaper_preset_rects.append(rect)
        clickable_rects[f'preset_{i}'] = rect
        if not current_wallpaper_image and (top, bottom) == (saved_light_wallpaper_top, saved_light_wallpaper_bottom):
             pygame.draw.rect(surface, BLUE, rect, 3, border_radius=12)
    custom_btn_rect = pygame.Rect(30, 120 + 2 * (preview_size * 1.3), surface.get_width() - 60, 50)
    draw_rounded_rect(surface, custom_btn_rect, get_current_color('settings_button_bg'), 10)
    custom_text = render_persian_text(get_string("select_from_file", "انتخاب از فايل..."), text_font, get_current_color('settings_button_text'))
    surface.blit(custom_text, custom_text.get_rect(center=custom_btn_rect.center))
    clickable_rects['custom_wallpaper_btn'] = custom_btn_rect
    if active_button_rect in [back_btn_rect, custom_btn_rect]:
        surf = pygame.Surface(active_button_rect.size, pygame.SRCALPHA); surf.fill((0,0,0,40)); surface.blit(surf, active_button_rect.topleft)
    return clickable_rects

def draw_settings_custom_wallpaper_screen(surface):
    global custom_wp_scroll_offset, target_custom_wp_scroll_offset, custom_wp_thumbnails
    
    surface.fill(get_current_color('settings_bg'))
    text_color = get_current_color('settings_title')
    
    # اسکرول نرم
    custom_wp_scroll_offset += (target_custom_wp_scroll_offset - custom_wp_scroll_offset) * 0.15

    clickable_rects = {}
    y_start = 120
    cols = 2
    padding = 15
    thumb_w = (SCREEN_WIDTH - (padding * 3)) // cols
    thumb_h = int(thumb_w * (SCREEN_HEIGHT / SCREEN_WIDTH)) # حفظ نسبت تصویر صفحه

    try:
        files = [f for f in os.listdir('wallpapers') if f.lower().endswith(('.png', '.jpg', '.jpeg', '.bmp'))]
        for i, filename in enumerate(files):
            row = i // cols
            col = i % cols
            x_pos = padding + col * (thumb_w + padding)
            y_pos = y_start + row * (thumb_h + padding) - custom_wp_scroll_offset
            
            # فقط در صورت قرار داشتن در صفحه رسم شود
            if y_pos + thumb_h > 0 and y_pos < SCREEN_HEIGHT:
                rect = pygame.Rect(x_pos, y_pos, thumb_w, thumb_h)
                
                # ایجاد و کش کردن Thumbnail برای جلوگیری از افت فریم
                if filename not in custom_wp_thumbnails:
                    path = os.path.join('wallpapers', filename)
                    img = pygame.image.load(path).convert()
                    custom_wp_thumbnails[filename] = pygame.transform.smoothscale(img, (thumb_w, thumb_h))
                
                thumb_surf = pygame.Surface((thumb_w, thumb_h), pygame.SRCALPHA)
                draw_rounded_rect(thumb_surf, thumb_surf.get_rect(), (200, 200, 200), 12)
                thumb_surf.blit(custom_wp_thumbnails[filename], (0,0), special_flags=pygame.BLEND_RGBA_MULT)
                
                # اگر در حال کلیک است تیره شود
                if active_file_item and active_file_item['rect'] == rect:
                    pygame.draw.rect(thumb_surf, (0,0,0,50), thumb_surf.get_rect(), border_radius=12)
                
                surface.blit(thumb_surf, rect.topleft)
                clickable_rects[f'file_{filename}'] = rect

    except FileNotFoundError:
        error_text = render_persian_text("پوشه wallpapers یافت نشد", text_font, text_color)
        surface.blit(error_text, error_text.get_rect(center=(SCREEN_WIDTH/2, 200)))

    # هدر شیشه‌ای بالا
    header_surf = pygame.Surface((SCREEN_WIDTH, 100), pygame.SRCALPHA)
    header_surf.fill((250, 250, 250, 230) if not is_dark_mode else (30, 30, 35, 230))
    surface.blit(header_surf, (0,0))
    
    back_btn_text = render_persian_text(get_string("back", "< بازگشت"), text_font, BLUE)
    back_btn_rect = back_btn_text.get_rect(left=20, top=55)
    surface.blit(back_btn_text, back_btn_rect)
    clickable_rects['back_btn'] = back_btn_rect
    
    title = render_persian_text("انتخاب تصویر", settings_title_font, text_color)
    surface.blit(title, title.get_rect(centerx=SCREEN_WIDTH/2, top=50))

    if active_button_rect == back_btn_rect:
        surf = pygame.Surface(back_btn_rect.size, pygame.SRCALPHA); surf.fill((0,0,0,40)); surface.blit(surf, back_btn_rect.topleft)

    return clickable_rects

def draw_settings_display_screen(surface):
    global superisland_switch_progress
    surface.fill(get_current_color('settings_bg'))
    text_color = get_current_color('settings_title')
    
    back_btn_text = render_persian_text(get_string("back", "< بازگشت"), text_font, BLUE)
    back_btn_rect = back_btn_text.get_rect(left=20, top=55)
    surface.blit(back_btn_text, back_btn_rect)
    
    title = render_persian_text(get_string("display", "صفحه نمايش"), settings_title_font, text_color)
    surface.blit(title, title.get_rect(centerx=surface.get_width()/2, top=50))
    
    # --- دکمه حالت تاریک ---
    dark_mode_text = render_persian_text("حالت تاریک", text_font, text_color)
    surface.blit(dark_mode_text, (surface.get_width() - dark_mode_text.get_width() - 30, 130))
    switch_rect_dm = pygame.Rect(30, 120, 60, 30)
    switch_radius = switch_rect_dm.height / 2
    off_color, on_color = (200, 200, 200), BLUE
    dm_bg_color = tuple(int(off + (on - off) * dark_mode_switch_progress) for off, on in zip(off_color, on_color))
    draw_rounded_rect(surface, switch_rect_dm, dm_bg_color, switch_radius)
    circle_pos_x_dm = switch_rect_dm.left + switch_radius + (switch_rect_dm.width - 2 * switch_radius) * dark_mode_switch_progress
    pygame.draw.circle(surface, WHITE, (circle_pos_x_dm, switch_rect_dm.centery), switch_radius - 4)

    # --- دکمه SuperIsland ---
    si_y = 190
    superisland_text = render_persian_text("جزیره پویا (SuperIsland)", text_font, text_color)
    surface.blit(superisland_text, (surface.get_width() - superisland_text.get_width() - 30, si_y + 10))
    switch_rect_si = pygame.Rect(30, si_y, 60, 30)
    si_bg_color = tuple(int(off + (on - off) * superisland_switch_progress) for off, on in zip(off_color, on_color))
    draw_rounded_rect(surface, switch_rect_si, si_bg_color, switch_radius)
    circle_pos_x_si = switch_rect_si.left + switch_radius + (switch_rect_si.width - 2 * switch_radius) * superisland_switch_progress
    pygame.draw.circle(surface, WHITE, (circle_pos_x_si, switch_rect_si.centery), switch_radius - 4)

    if active_button_rect == back_btn_rect:
        surf = pygame.Surface(back_btn_rect.size, pygame.SRCALPHA); surf.fill((0,0,0,40)); surface.blit(surf, back_btn_rect.topleft)

    return {
        'back_btn': back_btn_rect, 
        'dark_mode_toggle': pygame.Rect(30, 120, surface.get_width() - 60, 50),
        'superisland_toggle': pygame.Rect(30, si_y, surface.get_width() - 60, 50)
    }

# (اصلاح شده) صفحه تنظیمات قفل با گزینههای پسزمینه و جلوه عمق
def draw_settings_lock_screen_screen(surface):
    global lock_screen_preset_rects; lock_screen_preset_rects.clear()
    surface.fill(get_current_color('settings_bg')); text_color = get_current_color('settings_title')
    back_btn_text = render_persian_text(get_string("back", "< بازگشت"), text_font, BLUE); back_btn_rect = back_btn_text.get_rect(left=20, top=55); surface.blit(back_btn_text, back_btn_rect)
    title = render_persian_text(get_string("lock_screen", "صفحه قفل"), settings_title_font, text_color); surface.blit(title, title.get_rect(centerx=surface.get_width()/2, top=50))
    
    # رسم استایلهای ساعت
    styles = ['default', 'bottom_right', 'stacked']; preview_width, preview_height = 100, 175
    total_width = (len(styles) * preview_width) + ((len(styles) - 1) * 20); start_x = (surface.get_width() - total_width) / 2; y_pos = 120
    preview_clock_font = mf(28)
    preview_date_font = mf(10)
    
    now = datetime.datetime.now()
    clickable_rects = {'back_btn': back_btn_rect}
    for i, style in enumerate(styles):
        rect = pygame.Rect(start_x + i * (preview_width + 20), y_pos, preview_width, preview_height)
        lock_screen_preset_rects.append(rect); clickable_rects[f'style_{style}'] = rect
        
        # رسم پس زمینه پیش نمایش
        preview_bg = pygame.Surface(rect.size, pygame.SRCALPHA)
        draw_gradient_background(preview_bg, (40, 0, 80), (10, 20, 100))
        
        # (اصلاح شده) رسم محتوای پیشنمایشها
        preview_content_surface = pygame.Surface(rect.size, pygame.SRCALPHA)
        if style == 'default':
            time_surf = preview_clock_font.render(now.strftime("%H:%M"), True, WHITE)
            preview_content_surface.blit(time_surf, time_surf.get_rect(center=(rect.width/2, rect.height/2 - 20)))
            date_surf = preview_date_font.render(now.strftime("%A, %d"), True, WHITE)
            preview_content_surface.blit(date_surf, date_surf.get_rect(center=(rect.width/2, rect.height/2 + 5)))
        elif style == 'bottom_right':
            time_surf = preview_clock_font.render(now.strftime("%H:%M"), True, WHITE)
            time_rect_preview = time_surf.get_rect(bottomright=(rect.width - 10, rect.height - 15))
            preview_content_surface.blit(time_surf, time_rect_preview)
            date_surf = preview_date_font.render(now.strftime("%A, %d"), True, WHITE)
            preview_content_surface.blit(date_surf, date_surf.get_rect(bottomright=(rect.width - 10, time_rect_preview.top - 2)))
        elif style == 'stacked':
            hour_surf = preview_clock_font.render(now.strftime("%H"), True, WHITE)
            minute_surf = preview_clock_font.render(now.strftime("%M"), True, WHITE)
            hour_rect_preview = hour_surf.get_rect(center=(rect.width/2, rect.height/2 - 20))
            minute_rect_preview = minute_surf.get_rect(center=(rect.width/2, hour_rect_preview.bottom))
            preview_content_surface.blit(hour_surf, hour_rect_preview)
            preview_content_surface.blit(minute_surf, minute_rect_preview)
        
        preview_bg.blit(preview_content_surface, (0,0))
        # ماسک گرد
        mask = pygame.Surface(rect.size, pygame.SRCALPHA)
        draw_rounded_rect(mask, mask.get_rect(), (255,255,255,255), 15)
        preview_bg.blit(mask, (0,0), special_flags=pygame.BLEND_RGBA_MULT)
        surface.blit(preview_bg, rect.topleft)

        if style == lock_screen_style: pygame.draw.rect(surface, BLUE, rect, 3, border_radius=15)
    
    # دکمههای انتخاب پسزمینه صفحه قفل
    btn_y_pos = y_pos + preview_height + 30
    custom_lock_bg_btn = pygame.Rect(30, btn_y_pos, surface.get_width() - 60, 50)
    default_lock_bg_btn = pygame.Rect(30, btn_y_pos + 60, surface.get_width() - 60, 50)
    
    draw_rounded_rect(surface, custom_lock_bg_btn, get_current_color('settings_button_bg'), 10)
    custom_text = render_persian_text("انتخاب پسزمینه قفل", text_font, get_current_color('settings_button_text'))
    surface.blit(custom_text, custom_text.get_rect(center=custom_lock_bg_btn.center))
    
    draw_rounded_rect(surface, default_lock_bg_btn, get_current_color('settings_button_bg'), 10)
    default_text = render_persian_text("استفاده از پیشفرض", text_font, get_current_color('settings_button_text'))
    surface.blit(default_text, default_text.get_rect(center=default_lock_bg_btn.center))
    
    clickable_rects['custom_lock_wallpaper_btn'] = custom_lock_bg_btn
    clickable_rects['default_lock_wallpaper_btn'] = default_lock_bg_btn

    # (جدید) گزینه سوییچی جلوه عمق
    depth_effect_y_pos = default_lock_bg_btn.bottom + 20
    # این گزینه فقط زمانی نمایش داده میشود که تصویر پسزمینه سفارشی باشد و کتابخانههای لازم نصب باشند
    if lock_screen_wallpaper_path and depth_effect_available:
        depth_effect_text = render_persian_text("جلوه عمق", text_font, text_color)
        surface.blit(depth_effect_text, (surface.get_width() - depth_effect_text.get_width() - 30, depth_effect_y_pos + 10))
        
        depth_switch_progress = 1.0 if is_depth_effect_enabled else 0.0 # برای انیمیشن فوری
        switch_rect = pygame.Rect(30, depth_effect_y_pos, 60, 30)
        switch_radius = switch_rect.height / 2
        off_color = (200, 200, 200)
        on_color = BLUE
        switch_bg_color = tuple(int(off + (on - off) * depth_switch_progress) for off, on in zip(off_color, on_color))
        draw_rounded_rect(surface, switch_rect, switch_bg_color, switch_radius)
        start_x = switch_rect.left + switch_radius
        end_x = switch_rect.right - switch_radius
        circle_pos_x = start_x + (end_x - start_x) * depth_switch_progress
        pygame.draw.circle(surface, WHITE, (circle_pos_x, switch_rect.centery), switch_radius - 4)
        clickable_rects['depth_effect_toggle'] = pygame.Rect(30, depth_effect_y_pos, surface.get_width() - 60, 50)

    
    if active_button_rect == back_btn_rect:
        surf = pygame.Surface(back_btn_rect.size, pygame.SRCALPHA); surf.fill((0,0,0,40)); surface.blit(surf, back_btn_rect.topleft)
    return clickable_rects

def draw_settings_custom_lock_wallpaper_screen(surface):
    global custom_wp_scroll_offset, target_custom_wp_scroll_offset, custom_wp_thumbnails
    
    surface.fill(get_current_color('settings_bg'))
    text_color = get_current_color('settings_title')
    
    # اعمال اسکرول نرم
    custom_wp_scroll_offset += (target_custom_wp_scroll_offset - custom_wp_scroll_offset) * 0.15

    clickable_rects = {}
    y_start = 120
    cols = 2
    padding = 15
    thumb_w = (SCREEN_WIDTH - (padding * 3)) // cols
    thumb_h = int(thumb_w * (SCREEN_HEIGHT / SCREEN_WIDTH))
    
    try:
        files = [f for f in os.listdir('wallpapers') if f.lower().endswith(('.png', '.jpg', '.jpeg', '.bmp'))]
        for i, filename in enumerate(files):
            row = i // cols
            col = i % cols
            x_pos = padding + col * (thumb_w + padding)
            y_pos = y_start + row * (thumb_h + padding) - custom_wp_scroll_offset
            
            if y_pos + thumb_h > 0 and y_pos < SCREEN_HEIGHT:
                rect = pygame.Rect(x_pos, y_pos, thumb_w, thumb_h)
                
                if filename not in custom_wp_thumbnails:
                    path = os.path.join('wallpapers', filename)
                    img = pygame.image.load(path).convert()
                    custom_wp_thumbnails[filename] = pygame.transform.smoothscale(img, (thumb_w, thumb_h))
                
                thumb_surf = pygame.Surface((thumb_w, thumb_h), pygame.SRCALPHA)
                draw_rounded_rect(thumb_surf, thumb_surf.get_rect(), (200, 200, 200), 12)
                thumb_surf.blit(custom_wp_thumbnails[filename], (0,0), special_flags=pygame.BLEND_RGBA_MULT)
                
                if active_file_item and active_file_item['rect'] == rect:
                    pygame.draw.rect(thumb_surf, (0,0,0,50), thumb_surf.get_rect(), border_radius=12)
                
                surface.blit(thumb_surf, rect.topleft)
                clickable_rects[f'file_{filename}'] = rect

    except FileNotFoundError:
        error_text = render_persian_text("پوشه wallpapers یافت نشد", text_font, text_color)
        surface.blit(error_text, error_text.get_rect(center=(SCREEN_WIDTH/2, 200)))

    # هدر شیشه‌ای
    header_surf = pygame.Surface((SCREEN_WIDTH, 100), pygame.SRCALPHA)
    header_surf.fill((250, 250, 250, 230) if not is_dark_mode else (30, 30, 35, 230))
    surface.blit(header_surf, (0,0))
    
    back_btn_text = render_persian_text(get_string("back", "< بازگشت"), text_font, BLUE)
    back_btn_rect = back_btn_text.get_rect(left=20, top=55)
    surface.blit(back_btn_text, back_btn_rect)
    clickable_rects['back_btn'] = back_btn_rect
    
    title = render_persian_text("انتخاب تصویر قفل", settings_title_font, text_color)
    surface.blit(title, title.get_rect(centerx=SCREEN_WIDTH/2, top=50))

    if active_button_rect == back_btn_rect:
        surf = pygame.Surface(back_btn_rect.size, pygame.SRCALPHA)
        surf.fill((0,0,0,40))
        surface.blit(surf, back_btn_rect.topleft)

    return clickable_rects

def draw_settings_battery_screen(surface):
    """صفحه باتری تنظیمات — به سبک iOS با باتری بزرگ و انیمیشن شارژ"""
    import math, time as _time
    sw, sh = surface.get_size()
    is_dark = is_dark_mode
    bg      = (242, 242, 247) if not is_dark else (17, 17, 21)
    txt_col = (20,  20,  24)  if not is_dark else (232, 232, 238)
    sub_col = (130, 130, 140) if not is_dark else (100, 100, 112)
    card_bg = (255, 255, 255) if not is_dark else (28,  28,  36)
    sep_col = (220, 220, 224) if not is_dark else (38,  38,  48)
    surface.fill(bg)

    # --- دریافت اطلاعات باتری ---
    batt_info = psutil.sensors_battery()
    pct  = int(batt_info.percent) if batt_info else 85
    plug = batt_info.power_plugged if batt_info else False

    # --- هدر ---
    tf_title = mf(22)
    tf_big   = mf(52)
    tf_med   = mf(16)
    tf_sm    = mf(13)

    back_r = pygame.Rect(14, 52, 68, 30)
    pygame.draw.rect(surface, (50, 140, 255), back_r, border_radius=8)
    bk_s = render_persian_text("< بازگشت", tf_sm, (255,255,255))
    surface.blit(bk_s, bk_s.get_rect(center=back_r.center))

    tit_s = render_persian_text("باتری", tf_title, txt_col)
    surface.blit(tit_s, tit_s.get_rect(right=sw-16, top=50))

    # ===== باتری بزرگ iOS-style =====
    now = _time.time()
    BAT_W, BAT_H = 180, 88
    BAT_TIP_W, BAT_TIP_H = 12, 36
    BAT_R = 18
    bx = (sw - BAT_W) // 2
    by = 108

    # رنگ پایه بر اساس سطح
    if plug:
        fill_col  = (52, 199, 89)  # سبز — در حال شارژ
        glow_col  = (52, 199, 89, 40)
    elif pct > 20:
        fill_col  = (52, 199, 89)
        glow_col  = (52, 199, 89, 30)
    elif pct > 10:
        fill_col  = (255, 204, 0)  # زرد
        glow_col  = (255, 204, 0, 30)
    else:
        fill_col  = (255, 59, 48)  # قرمز
        glow_col  = (255, 59, 48, 40)

    outline_col = (txt_col[0], txt_col[1], txt_col[2], 200)

    # هاله/glow
    glow_surf = pygame.Surface((BAT_W+24, BAT_H+24), pygame.SRCALPHA)
    pygame.draw.rect(glow_surf, (*fill_col, 35), (0,0,BAT_W+24,BAT_H+24), border_radius=BAT_R+8)
    surface.blit(glow_surf, (bx-12, by-12))

    # بدنه خالی باتری
    body_r = pygame.Rect(bx, by, BAT_W, BAT_H)
    pygame.draw.rect(surface, card_bg, body_r, border_radius=BAT_R)
    pygame.draw.rect(surface, txt_col, body_r, 3, border_radius=BAT_R)

    # نوک باتری
    tip_r = pygame.Rect(bx + BAT_W + 2, by + (BAT_H - BAT_TIP_H)//2, BAT_TIP_W, BAT_TIP_H)
    pygame.draw.rect(surface, txt_col, tip_r, border_radius=5)

    # پر شدن باتری
    INNER_PAD = 5
    fill_w_max = BAT_W - INNER_PAD*2
    if plug:
        # انیمیشن شارژ: موج روان
        wave = math.sin(now * 2.2) * 0.06 + 1.0   # ±6% نوسان
        fill_w = int(fill_w_max * min(1.0, (pct/100.0) * wave))
        # رنگ چشمک‌زن ملایم
        glow_a = int(abs(math.sin(now*1.8))*80 + 60)
        anim_col = (*fill_col, glow_a)
        glow2 = pygame.Surface((fill_w, BAT_H - INNER_PAD*2), pygame.SRCALPHA)
        glow2.fill(anim_col)
        inner_r = pygame.Rect(bx+INNER_PAD, by+INNER_PAD, fill_w, BAT_H-INNER_PAD*2)
        surface.blit(glow2, (bx+INNER_PAD, by+INNER_PAD))
        pygame.draw.rect(surface, fill_col, inner_r, border_radius=BAT_R-INNER_PAD-1)
    else:
        fill_w = int(fill_w_max * pct / 100)
        inner_r = pygame.Rect(bx+INNER_PAD, by+INNER_PAD, fill_w, BAT_H-INNER_PAD*2)
        pygame.draw.rect(surface, fill_col, inner_r, border_radius=BAT_R-INNER_PAD-1)

    # درصد روی باتری
    pct_s = tf_big.render(f"{pct}%", True, txt_col)
    surface.blit(pct_s, pct_s.get_rect(center=(bx+BAT_W//2, by+BAT_H//2)))

    # آیکون صاعقه هنگام شارژ
    if plug:
        bolt_cx = bx + BAT_W - 28
        bolt_cy = by + 14
        bolt_pts = [
            (bolt_cx,    bolt_cy),
            (bolt_cx-6,  bolt_cy+12),
            (bolt_cx+2,  bolt_cy+12),
            (bolt_cx-3,  bolt_cy+24),
            (bolt_cx+8,  bolt_cy+10),
            (bolt_cx+2,  bolt_cy+10),
        ]
        pygame.draw.polygon(surface, (255, 230, 50), bolt_pts)

    # وضعیت زیر باتری
    stat_y = by + BAT_H + 16
    if plug:
        if pct >= 100:
            stat_s = render_persian_text("شارژ کامل", tf_med, fill_col)
        else:
            stat_s = render_persian_text("در حال شارژ...", tf_med, fill_col)
    else:
        stat_s = render_persian_text("باتری", tf_med, sub_col)
    surface.blit(stat_s, stat_s.get_rect(centerx=sw//2, top=stat_y))

    # ===== اطلاعات سلامت باتری (کارت) =====
    card_y = stat_y + 40
    card_r = pygame.Rect(16, card_y, sw-32, 62)
    pygame.draw.rect(surface, card_bg, card_r, border_radius=14)

    health_s = render_persian_text("سلامت باتری", tf_med, txt_col)
    surface.blit(health_s, health_s.get_rect(right=sw-30, centery=card_r.centery))

    health_val = "عالی" if pct > 50 else ("متوسط" if pct > 20 else "ضعیف")
    hv_col = (52,199,89) if pct > 50 else ((255,204,0) if pct > 20 else (255,59,48))
    hv_s = tf_med.render(health_val, True, hv_col)
    surface.blit(hv_s, hv_s.get_rect(left=24, centery=card_r.centery))

    # ===== گزینه‌های صرفه‌جویی =====
    opts_y = card_y + 76
    opts = [
        ("حالت کم‌مصرف", "Low Power Mode", pct < 20),
        ("بهینه‌سازی شارژ", "Optimised Charging", True),
    ]
    for _i, (_label, _sub, _active) in enumerate(opts):
        _r = pygame.Rect(16, opts_y + _i*64, sw-32, 56)
        pygame.draw.rect(surface, card_bg, _r, border_radius=12)
        _ls = render_persian_text(_label, tf_med, txt_col)
        surface.blit(_ls, _ls.get_rect(right=sw-24, centery=_r.centery-8))
        _ss = tf_sm.render(_sub, True, sub_col)
        surface.blit(_ss, (_r.left+14, _r.centery+6))
        # toggle
        _tog_x = _r.left + 14
        _tog_r = pygame.Rect(_tog_x, _r.centery-12, 48, 24)
        _tc = (52,199,89) if _active else (180,180,190)
        pygame.draw.rect(surface, _tc, _tog_r, border_radius=12)
        _tc_x = _tog_r.right - 14 if _active else _tog_r.left + 14
        pygame.draw.circle(surface, WHITE, (_tc_x, _tog_r.centery), 10)

    return {'back_btn': back_r}


def draw_settings_about_screen(surface):
    # پس‌زمینه تیره ثابت
    surface.fill((20, 25, 35))
    
    # افکت تابش نور نرم از بالا سمت راست (گوشه)
    light_surf = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
    # رسم دایره‌های تو در تو با شفافیت کاهنده برای ایجاد هاله نور نرم
    for radius in range(int(SCREEN_WIDTH * 1.5), 0, -15):
        alpha = int(12 * (1 - radius / (SCREEN_WIDTH * 1.5)))
        if alpha > 0:
            pygame.draw.circle(light_surf, (80, 140, 255, alpha), (SCREEN_WIDTH, 0), radius)
    surface.blit(light_surf, (0, 0))
    
    # متن و دکمه‌ها
    back_btn_text = render_persian_text(get_string("back", "< بازگشت"), text_font, WHITE)
    back_btn_rect = back_btn_text.get_rect(left=20, top=55)
    surface.blit(back_btn_text, back_btn_rect)
    
    title = render_persian_text(get_string("about", "درباره"), settings_title_font, WHITE)
    surface.blit(title, title.get_rect(centerx=surface.get_width()/2, top=50))
    
    # لوگوی ثابت (بدون انیمیشن مقیاس)
    os_name_surf = about_font.render("ParsOS", True, WHITE)
    logo_rect = os_name_surf.get_rect(center=(surface.get_width()/2, surface.get_height()/2))
    surface.blit(os_name_surf, logo_rect)
    
    if active_button_rect == back_btn_rect:
        surf = pygame.Surface(back_btn_rect.size, pygame.SRCALPHA)
        surf.fill((0, 0, 0, 40))
        surface.blit(surf, back_btn_rect.topleft)
        
    return {'back_btn': back_btn_rect, 'logo_btn': logo_rect}

def draw_notes_context_menu(surface):
    menu_width, menu_height = 120, 80
    menu_rect = pygame.Rect(notes_context_menu_pos[0], notes_context_menu_pos[1], menu_width, menu_height)
    if menu_rect.right > SCREEN_WIDTH: menu_rect.right = SCREEN_WIDTH - 10
    if menu_rect.bottom > SCREEN_HEIGHT: menu_rect.bottom = SCREEN_HEIGHT - 10
    shadow_rect = menu_rect.move(3, 3)
    draw_rounded_rect(surface, shadow_rect, (0, 0, 0, 100), 10)
    draw_rounded_rect(surface, menu_rect, get_current_color('context_menu_bg'), 8)
    text_color = get_current_color('context_menu_text')
    copy_text = render_persian_text("کپی", text_font, text_color)
    paste_text = render_persian_text("جایگذاری", text_font, text_color)
    copy_rect = copy_text.get_rect(right=menu_rect.right - 15, top=menu_rect.top + 10)
    paste_rect = paste_text.get_rect(right=menu_rect.right - 15, top=copy_rect.bottom + 10)
    surface.blit(copy_text, copy_rect); surface.blit(paste_text, paste_rect)
    return {'copy': copy_rect, 'paste': paste_rect}

def format_time(seconds):
    if seconds < 0: seconds = 0
    mins = int(seconds // 60)
    secs = int(seconds % 60)
    return f"{mins:02d}:{secs:02d}"

def draw_scrolling_text(surface, text, font, color, center_x, y, max_width):
    # draw_scrolling_text: scrolls text if too long
    global music_text_scroll_x
    
    rendered_text = render_persian_text(text, font, color)
    text_w = rendered_text.get_width()
    
    if text_w <= max_width:
        # اگر متن کوتاه است، وسطچین کن
        surface.blit(rendered_text, rendered_text.get_rect(center=(center_x, y)))
    else:
        # اگر متن طولانی است، اسکرول کن
        # ایجاد یک سطح ماسک برای برش متن
        mask_surf = pygame.Surface((max_width, rendered_text.get_height()), pygame.SRCALPHA)
        
        # سرعت حرکت
        speed = 30 # پیکسل در ثانیه
        current_time = time.time()
        
        # محاسبه موقعیت (یک حرکت رفت و برگشتی یا تکرار شونده)
        # اینجا از تکرار شونده استفاده میکنیم
        cycle_width = text_w + 50 # 50 پیکسل فاصله
        offset = (current_time * speed) % cycle_width
        
        x_pos = -offset
        
        # رسم متن اصلی
        mask_surf.blit(rendered_text, (x_pos, 0))
        # رسم متن تکراری (برای پر کردن فضای خالی وقتی متن اول خارج میشود)
        if x_pos + text_w < max_width:
            mask_surf.blit(rendered_text, (x_pos + cycle_width, 0))
            
        # افزودن افکت محو شدن در دو طرف (Fade Text)
        fade_w = 20
        # گرادینت چپ
        fade_left = pygame.Surface((fade_w, mask_surf.get_height()), pygame.SRCALPHA)
        draw_gradient_background(fade_left, (0,0,0,0), (0,0,0,0)) # فقط برای ایجاد سوریس
        # (سادهتر: فقط متن را رسم میکنیم، فید کردن در پایگیم پیچیده است)
        
        surface.blit(mask_surf, (center_x - max_width//2, y - mask_surf.get_height()//2))

def draw_tactile_button(surface, rect, icon_type, state_key):
    """رسم دکمه با انیمیشن فشردن"""
    global music_button_states
    
    state = music_button_states.get(state_key, {'scale': 1.0, 'pressed': False})
    
    # مدیریت انیمیشن مقیاس
    target_scale = 0.85 if state['pressed'] else 1.0
    state['scale'] += (target_scale - state['scale']) * 0.4
    
    # مرکز دکمه
    center = rect.center
    
    # مقیاس کردن دکمه
    current_size = int(rect.width * state['scale'])
    if current_size < 1: current_size = 1
    
    # رسم دایره پسزمینه (در حالت فشرده کمی روشنتر)
    bg_alpha = 50 if not state['pressed'] else 80
    btn_surf = pygame.Surface((current_size, current_size), pygame.SRCALPHA)
    draw_rounded_rect(btn_surf, btn_surf.get_rect(), (255, 255, 255, bg_alpha), current_size//2)
    
    # رسم آیکون
    icon_color = WHITE
    if icon_type == 'play':
        if not is_music_playing:
            # مثلث پخش
            pts = [(current_size*0.35, current_size*0.25), 
                   (current_size*0.35, current_size*0.75), 
                   (current_size*0.75, current_size*0.5)]
            pygame.draw.polygon(btn_surf, icon_color, pts)
        else:
            # دو خط توقف
            w, h = current_size * 0.12, current_size * 0.4
            gap = current_size * 0.1
            cx, cy = current_size / 2, current_size / 2
            pygame.draw.rect(btn_surf, icon_color, (cx - w - gap/2, cy - h/2, w, h), border_radius=2)
            pygame.draw.rect(btn_surf, icon_color, (cx + gap/2, cy - h/2, w, h), border_radius=2)
            
    elif icon_type == 'next':
        # دو مثلث جلو
        cx, cy = current_size / 2, current_size / 2
        off = current_size * 0.15
        for i in [-1, 0]: # رسم دو فلش یا فلش و خط؟ همان استایل iOS
            # استایل iOS: دو مثلث چسبیده + خط
            pass 
        # رسم ساده Next
        pts = [(cx-off, cy-off), (cx-off, cy+off), (cx+off, cy)]
        pygame.draw.polygon(btn_surf, icon_color, pts)
        pygame.draw.rect(btn_surf, icon_color, (cx+off, cy-off, 3, off*2))
        
    elif icon_type == 'prev':
        cx, cy = current_size / 2, current_size / 2
        off = current_size * 0.15
        pts = [(cx+off, cy-off), (cx+off, cy+off), (cx-off, cy)]
        pygame.draw.polygon(btn_surf, icon_color, pts)
        pygame.draw.rect(btn_surf, icon_color, (cx-off-3, cy-off, 3, off*2))

    surface.blit(btn_surf, btn_surf.get_rect(center=center))

def draw_music_app_screen(surface):
    global is_music_playing, is_music_paused, music_track_name, current_track_length, \
           current_album_art_surface, music_playback_start_time_offset, current_track_index, \
           is_scrubbing_music, music_scrub_progress, cached_blurred_bg, last_played_track_name, \
           music_art_scale, target_music_art_scale, scrub_knob_scale, music_transition

    screen_w, screen_h = surface.get_size()
    
    # فونت‌ها
    title_font = mf(24)
    artist_font = mf(18)
    time_font = mf(12)
    plist_font = mf(11)
    shuf_font = mf(16)
    rep_font = mf(16)

    # ========== پس‌زمینه مات ==========
    if music_track_name != last_played_track_name or cached_blurred_bg is None:
        last_played_track_name = music_track_name
        if current_album_art_surface:
            try:
                art = current_album_art_surface.convert()
                s1 = pygame.transform.smoothscale(art, (screen_w // 6, screen_h // 6))
                s2 = pygame.transform.smoothscale(s1, (screen_w // 14, screen_h // 14))
                s3 = pygame.transform.smoothscale(s2, (screen_w // 8, screen_h // 8))
                s4 = pygame.transform.smoothscale(s3, (screen_w // 22, screen_h // 22))
                blurred = pygame.transform.smoothscale(s4, (screen_w, screen_h))
                overlay = pygame.Surface((screen_w, screen_h), pygame.SRCALPHA)
                overlay.fill((5, 8, 18, 180))
                blurred.blit(overlay, (0, 0))
                cached_blurred_bg = blurred
            except:
                cached_blurred_bg = None
        else:
            cached_blurred_bg = None

    if cached_blurred_bg:
        surface.blit(cached_blurred_bg, (0, 0))
    else:
        draw_gradient_background(surface, (60, 60, 70), (20, 20, 25))

    cover_size = 280
    cover_center_x = screen_w / 2
    cover_center_y = 240

    # تابع کمکی برای رسم کاور با گوشه گرد
    def draw_rounded_cover(surf, art, center_x, center_y, size):
        if art is None:
            return
        scaled = pygame.transform.smoothscale(art, (size, size))
        rounded = pygame.Surface((size, size), pygame.SRCALPHA)
        draw_rounded_rect(rounded, rounded.get_rect(), (255, 255, 255), 20)
        rounded.blit(scaled, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)
        pygame.draw.rect(rounded, (255,255,255, 50), rounded.get_rect(), 1, border_radius=20)
        rect = rounded.get_rect(center=(center_x, center_y))
        surf.blit(rounded, rect)

    use_transition = music_transition['active'] and music_transition['old_art'] is not None

    if use_transition:
        t = music_transition['progress']
        ease_progress = 1 - (1 - t) ** 3
        direction = music_transition['direction']
        offset = int(ease_progress * screen_w) * direction

        # کاور قدیم
        draw_rounded_cover(surface, music_transition['old_art'], cover_center_x - offset, cover_center_y, cover_size)
        # کاور جدید
        new_x = cover_center_x + (screen_w - offset) if direction == 1 else cover_center_x - (screen_w - offset)
        draw_rounded_cover(surface, music_transition['new_art'], new_x, cover_center_y, cover_size)

        # اسلاید متن
        old_name = music_transition['old_track_name']
        new_name = music_transition['new_track_name']
        old_name_clean = os.path.splitext(old_name)[0] if old_name else ""
        new_name_clean = os.path.splitext(new_name)[0] if new_name else ""
        text_offset = int(ease_progress * 60) * direction
        if old_name_clean:
            old_title = render_persian_text(old_name_clean, title_font, WHITE)
            surface.blit(old_title, old_title.get_rect(center=(cover_center_x - text_offset, 420)))
        if new_name_clean:
            new_title = render_persian_text(new_name_clean, title_font, WHITE)
            surface.blit(new_title, new_title.get_rect(center=(cover_center_x + (60 - text_offset) if direction == 1 else cover_center_x - (60 - text_offset), 420)))
        artist_surf = render_persian_text("ParsOS Music", artist_font, (180, 180, 180))
        surface.blit(artist_surf, artist_surf.get_rect(center=(screen_w/2, 455)))
    else:
        # حالت عادی با انیمیشن تنفس
        target_music_art_scale = 1.0 if is_music_playing else 0.8
        music_art_scale += (target_music_art_scale - music_art_scale) * 0.08
        current_size = int(cover_size * music_art_scale)
        cover_rect = pygame.Rect(0, 0, current_size, current_size)
        cover_rect.center = (cover_center_x, cover_center_y)

        # سایه
        shadow_offset = 20 * music_art_scale
        shadow_alpha = int(100 * music_art_scale)
        shadow_surface = pygame.Surface((current_size, current_size), pygame.SRCALPHA)
        draw_rounded_rect(shadow_surface, shadow_surface.get_rect(), (0, 0, 0, shadow_alpha), 25)
        shadow_surface = pygame.transform.scale(shadow_surface, (int(current_size*0.95), int(current_size*0.95)))
        surface.blit(shadow_surface, shadow_surface.get_rect(center=(cover_center_x, cover_center_y + shadow_offset)))

        # کاور اصلی با گوشه گرد
        draw_rounded_cover(surface, current_album_art_surface, cover_center_x, cover_center_y, current_size)

        # متن آهنگ
        track_name_cleaned = os.path.splitext(music_track_name)[0]
        draw_scrolling_text(surface, track_name_cleaned, title_font, WHITE, screen_w/2, 420, screen_w - 60)
        artist_surf = render_persian_text("ParsOS Music", artist_font, (180, 180, 180))
        surface.blit(artist_surf, artist_surf.get_rect(center=(screen_w/2, 455)))

    # ========== نوار پیشرفت (بدون تغییر) ==========
    seek_bar_y = 500
    seek_bar_height = 4
    seek_bar_width = screen_w - 60
    seek_bar_rect = pygame.Rect((screen_w - seek_bar_width)/2, seek_bar_y, seek_bar_width, seek_bar_height)

    current_time = 0
    progress = 0.0
    if is_scrubbing_music:
        progress = music_scrub_progress
        current_time = progress * current_track_length
    elif (is_music_playing or is_music_paused) and current_track_length > 0:
        current_time = music_playback_start_time_offset + pygame.mixer.music.get_pos() / 1000.0
        progress = current_time / current_track_length
    progress = max(0.0, min(1.0, progress))

    draw_rounded_rect(surface, seek_bar_rect, (255, 255, 255, 50), 2)
    fill_width = seek_bar_width * progress
    fill_rect = pygame.Rect(seek_bar_rect.left, seek_bar_rect.top, fill_width, seek_bar_height)
    draw_rounded_rect(surface, fill_rect, (200, 200, 200), 2)

    target_knob = 1.5 if is_scrubbing_music else 1.0
    scrub_knob_scale += (target_knob - scrub_knob_scale) * 0.2
    knob_radius = 6 * scrub_knob_scale
    knob_center = (fill_rect.right, seek_bar_rect.centery)
    pygame.draw.circle(surface, WHITE, knob_center, knob_radius)

    curr_time_surf = time_font.render(format_time(current_time), True, (180, 180, 180))
    total_time_surf = time_font.render(format_time(current_track_length), True, (180, 180, 180))
    surface.blit(curr_time_surf, (seek_bar_rect.left, seek_bar_rect.bottom + 8))
    surface.blit(total_time_surf, total_time_surf.get_rect(topright=(seek_bar_rect.right, seek_bar_rect.bottom + 8)))

    # ========== دکمه‌ها ==========
    controls_y = 600
    play_btn_size = 75
    side_btn_size = 50
    play_rect = pygame.Rect(0, 0, play_btn_size, play_btn_size)
    play_rect.center = (screen_w/2, controls_y)
    prev_rect = pygame.Rect(0, 0, side_btn_size, side_btn_size)
    prev_rect.center = (play_rect.left - 60, controls_y)
    next_rect = pygame.Rect(0, 0, side_btn_size, side_btn_size)
    next_rect.center = (play_rect.right + 60, controls_y)

    draw_tactile_button(surface, play_rect, 'play', 'play')
    draw_tactile_button(surface, prev_rect, 'prev', 'prev')
    draw_tactile_button(surface, next_rect, 'next', 'next')

    extra_btn_y = controls_y + 52
    extra_btn_size = 36
    extra_color = (180, 180, 180) if not is_dark_mode else (140, 140, 140)
    shuffle_rect = pygame.Rect(0, 0, extra_btn_size, extra_btn_size)
    shuffle_rect.center = (prev_rect.centerx, extra_btn_y)
    shuf_active_col = (255, 255, 255) if music_shuffle else extra_color
    shuf_s = shuf_font.render("⇄", True, shuf_active_col)
    surface.blit(shuf_s, shuf_s.get_rect(center=shuffle_rect.center))
    if music_shuffle:
        dot_x = shuffle_rect.centerx
        dot_y = shuffle_rect.bottom + 3
        pygame.draw.circle(surface, (255, 255, 255), (dot_x, dot_y), 3)

    repeat_rect = pygame.Rect(0, 0, extra_btn_size, extra_btn_size)
    repeat_rect.center = (next_rect.centerx, extra_btn_y)
    repeat_icons = ["↺", "↻", "❶"]
    rep_col = (255, 255, 255) if music_repeat > 0 else extra_color
    rep_s = rep_font.render(repeat_icons[music_repeat], True, rep_col)
    surface.blit(rep_s, rep_s.get_rect(center=repeat_rect.center))
    if music_repeat > 0:
        pygame.draw.circle(surface, rep_col, (repeat_rect.centerx, repeat_rect.bottom + 3), 3)

    if music_playlist:
        plist_text = f"{current_track_index + 1} / {len(music_playlist)}"
        plist_surf = plist_font.render(plist_text, True, (150, 150, 150))
        surface.blit(plist_surf, plist_surf.get_rect(center=(screen_w / 2, extra_btn_y)))

    return {
        'play_pause_btn': play_rect,
        'next_btn': next_rect,
        'prev_btn': prev_rect,
        'seek_bar': seek_bar_rect.inflate(0, 40),
        'shuffle_btn': shuffle_rect,
        'repeat_btn': repeat_rect,
    }

def draw_browser_app_screen(surface):
    global input_url_text, is_typing_url
    global api_results, api_loading

    clickable_rects = {}

    # =========================
    # 1️⃣ پسزمینه
    # =========================
    surface.fill((240, 240, 240) if not is_dark_mode else (30, 30, 30))

    header_height = 60
    tab_bar_height = 40

    # =========================
    # 2️⃣ نوار تب (ساده)
    # =========================
    tab_rect = pygame.Rect(0, 0, 150, tab_bar_height)
    pygame.draw.rect(surface, (255, 255, 255), tab_rect, border_top_left_radius=10, border_top_right_radius=10)
    pygame.draw.rect(surface, (100,100,100), tab_rect, 1, border_top_left_radius=10, border_top_right_radius=10)

    tab_txt = text_font.render("NovaSearch", True, BLACK)
    surface.blit(tab_txt, (tab_rect.x + 10, tab_rect.y + 10))

    # =========================
    # 3️⃣ نوار آدرس
    # =========================
    toolbar_y = tab_bar_height
    pygame.draw.rect(
        surface,
        (220, 220, 220) if not is_dark_mode else (50, 50, 50),
        (0, toolbar_y, SCREEN_WIDTH, header_height)
    )

    url_rect = pygame.Rect(10, toolbar_y + 10, SCREEN_WIDTH - 120, 40)
    pygame.draw.rect(
        surface,
        WHITE if not is_dark_mode else (80, 80, 80),
        url_rect,
        border_radius=8
    )

    display_text = input_url_text
    url_surf = text_font.render(display_text[-50:], True, BLACK)
    surface.blit(url_surf, (url_rect.x + 10, url_rect.centery - url_surf.get_height()/2))

    clickable_rects['url_bar'] = url_rect

    # =========================
    # 4️⃣ دکمه Go
    # =========================
    go_rect = pygame.Rect(SCREEN_WIDTH - 100, toolbar_y + 10, 80, 40)
    pygame.draw.rect(surface, BLUE, go_rect, border_radius=8)

    go_txt = text_font.render("Go", True, WHITE)
    surface.blit(go_txt, go_txt.get_rect(center=go_rect.center))

    clickable_rects['go_btn'] = go_rect

    # =========================
    # 5️⃣ محتوای نتایج
    # =========================
    content_y = header_height + tab_bar_height
    content_rect = pygame.Rect(0, content_y, SCREEN_WIDTH, SCREEN_HEIGHT - content_y)

    # ---------- اگر در حال جستجو هستیم ----------
    if api_loading:
        loading_txt = text_font.render("Searching WebSeek...", True, BLUE)
        surface.blit(loading_txt, loading_txt.get_rect(center=content_rect.center))

    # ---------- اگر نتیجه داریم ----------
    elif api_results:
        y_offset = content_y + 20

        for i, result in enumerate(api_results):
            result_rect = pygame.Rect(40, y_offset, SCREEN_WIDTH - 80, 30)

            pygame.draw.rect(surface, (255,255,255), result_rect, border_radius=6)
            pygame.draw.rect(surface, (200,200,200), result_rect, 1, border_radius=6)

            result_text = text_font.render(result, True, BLACK)
            surface.blit(result_text, (result_rect.x + 10, result_rect.y + 5))

            clickable_rects[f"result_{i}"] = result_rect
            y_offset += 45

    # ---------- اگر هنوز چیزی جستجو نشده ----------
    else:
        empty_txt = text_font.render("Type something and press Go...", True, (120,120,120))
        surface.blit(empty_txt, empty_txt.get_rect(center=content_rect.center))

    return clickable_rects

def search_via_api(query):
    global api_results, api_loading

    api_loading = True

    def worker():
        global api_results, api_loading
        try:
            response = requests.get(
                "http://127.0.0.1:8000/search",
                params={"q": query, "top_n": 10},
                timeout=5
            )
            data = response.json()
            api_results = data.get("results", [])
        except Exception as e:
            print("API Error:", e)
            api_results = []

        api_loading = False

    threading.Thread(target=worker, daemon=True).start()

def draw_app_screen():
    global app_screen_animation_direction, app_screen_animation_progress, app_context, app_surfaces
    main_app_surface = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT))
    app_name, app_page = app_context.get('app_name'), app_context.get('screen')

    clickable_rects = {}
    
    if app_context.get('app_type') == 'remote':
        # پیدا کردن سطح برنامه از سرور نمایش
        remote_surf = None
        with display_server.lock:
            for session_id, app in display_server.apps.items():
                if app.is_connected:
                    remote_surf = app.surface
                    break   # اولین برنامه متصل
        if remote_surf:
            scaled = pygame.transform.scale(remote_surf, (SCREEN_WIDTH, SCREEN_HEIGHT))
            main_app_surface.blit(scaled, (0,0))
        else:
            # در حال انتظار برای اتصال
            main_app_surface.fill((50,50,50))
            wait_text = render_persian_text("منتظر اتصال برنامه...", mf(18), WHITE)
            main_app_surface.blit(wait_text, wait_text.get_rect(center=(SCREEN_WIDTH/2, SCREEN_HEIGHT/2)))

    if app_context.get('app_type') == 'remote':
        session_id = app_context.get('session_id')
        if session_id is not None:
            remote_surf = display_server.get_app_surface(session_id)
            if remote_surf:
                # مقیاس‌بندی به اندازه صفحه (در صورت نیاز)
                scaled = pygame.transform.scale(remote_surf, (SCREEN_WIDTH, SCREEN_HEIGHT))
                main_app_surface.blit(scaled, (0,0))
            else:
                main_app_surface.fill((100,100,100))
    
    # (جدید) بررسی و اجرای منطق رسم برای برنامههای خارجی
    if app_context.get('is_external_app'):
        app_id = app_context.get('app_id')
        app_instance = running_app_instances.get(app_id)
        if app_instance:
            app_instance.draw(main_app_surface)
        else:
            # اگر به هر دلیلی نمونه برنامه وجود نداشت، یک صفحه خطا نمایش بده
            draw_installed_app_screen(main_app_surface)
    else:
        # اجرای تابع رسم مخصوص برنامههای داخلی سیستم عامل
        if app_name == 'settings':
            if app_page == 'main': draw_settings_main_screen(main_app_surface)
            elif app_page == 'wallpaper': draw_settings_wallpaper_screen(main_app_surface)
            elif app_page == 'display': draw_settings_display_screen(main_app_surface)
            elif app_page == 'lock_screen': draw_settings_lock_screen_screen(main_app_surface)
            elif app_page == 'custom_wallpaper': draw_settings_custom_wallpaper_screen(main_app_surface)
            elif app_page == 'custom_lock_wallpaper': draw_settings_custom_lock_wallpaper_screen(main_app_surface)
            elif app_page == 'language': draw_settings_language_screen(main_app_surface) # <--- (جدید) این خط اضافه شده است
            elif app_page == 'battery': draw_settings_battery_screen(main_app_surface)
            elif app_page == 'about': draw_settings_about_screen(main_app_surface)
        if app_name == 'notes':
            # فراخوانی متد رسم ماژول جدا شده و دریافت نقاط کلیک
            app_clicks = notes_module.draw(main_app_surface, current_w, current_h, app_context)
            
            # ثبت کادرهای کلیک در دیکشنری عمومی کلیک‌های فعال سیستم‌عامل
            for click_key, rect in app_clicks.items():
                # متغیر کامپوننت‌های کلیک بر اساس معماری سیستم‌عامل شما (مثلاً clickable_rects یا UI rects)
                clickable_rects[click_key] = rect
        elif app_name == 'music': draw_music_app_screen(main_app_surface)
        elif app_name == 'browser': draw_browser_app_screen(main_app_surface)
        elif app_name == 'files':
            draw_files_app_screen(main_app_surface)
        elif app_name == 'messenger':
            draw_messenger_app(main_app_surface)
        elif app_name == 'gallery':
            if is_gallery_editor_open:
                draw_gallery_editor(main_app_surface)
            else:
                draw_gallery_app_screen(main_app_surface)

    # ذخیره یک کپی از صفحه برنامه برای استفاده در منوی برنامههای اخیر
    if app_name:
        app_key = app_context.get('app_id', app_name)
        # فقط هر 5 فریم یکبار کپی بگیر تا سرعت کم نشود، یا در لحظه بستن
        # اما برای اطمینان فعلا همیشه کپی میگیریم:
        current_snapshot = main_app_surface.copy().convert_alpha()
        app_surfaces[app_key] = current_snapshot
        
        # --- اصلاح مهم: آپدیت کردن همزمان لیست برنامههای اخیر ---
        for item in recents_apps_list:
            # اگر این برنامه در لیست اخیر است، اسنپشاتش را همین الان آپدیت کن
            if item.get('app_id') == app_key or item.get('name') == app_name:
                item['snapshot'] = current_snapshot

    # مدیریت انیمیشن جابجایی بین صفحات داخلی یک برنامه
    if app_screen_animation_direction != 0:
        if app_screen_animation_direction != 0:
            # وابسته به فریم تایم
            app_screen_animation_progress += 4.5 * dt 
            if app_screen_animation_progress >= 1.0:
                app_screen_animation_progress, app_screen_animation_direction = 0, 0
            if app_context.get('animation_callback'): app_context['animation_callback'](); app_context['animation_callback'] = None
        progress = (1 - math.cos(app_screen_animation_progress * math.pi)) / 2
        old_surface = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT))
        if app_context.get('old_screen_draw_func'): app_context['old_screen_draw_func'](old_surface)
        x_offset_old = int(SCREEN_WIDTH * progress * app_screen_animation_direction); x_offset_new = x_offset_old - SCREEN_WIDTH * app_screen_animation_direction
        screen.blit(old_surface, (x_offset_old, 0)); screen.blit(main_app_surface, (x_offset_new, 0))
    else: screen.blit(main_app_surface, (0, 0))
    
    # این عناصر همیشه در بالای صفحه برنامه رسم میشوند
    draw_status_bar(get_current_color('status_bar_app'))
    draw_home_indicator(get_current_color('home_indicator_app'))

def draw_charging_animation():
    global charging_animation_alpha
    overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA); overlay.fill((0, 0, 0, int(charging_animation_alpha))); screen.blit(overlay, (0, 0))
    main_circle_radius = 100; y_offset = math.sin(time.time() * 2) * 10
    center_pos = (SCREEN_WIDTH / 2, SCREEN_HEIGHT / 2 + y_offset); pygame.draw.circle(screen, CHARGING_BLUE, center_pos, main_circle_radius)
    battery = psutil.sensors_battery()
    if battery:
        percent_surf = render_persian_text("".join([persian_digits.get(c, c) for c in str(battery.percent)]) + "%", battery_font, WHITE)
        screen.blit(percent_surf, percent_surf.get_rect(center=center_pos))
    for particle in charging_particles[:]:
        target_vec, particle_vec = pygame.Vector2(center_pos), pygame.Vector2(particle['pos'])
        direction = (target_vec - particle_vec).normalize(); particle_vec += direction * particle['speed']; particle['pos'] = [particle_vec.x, particle_vec.y]
        pygame.draw.circle(screen, CHARGING_BLUE, particle['pos'], particle['radius'])
        if particle_vec.distance_to(target_vec) < 10: charging_particles.remove(particle)

def draw_folder_view():
    global is_dragging_icon, selected_icon, folder_dragged_icon_from
    ease_progress = (1 - math.cos(folder_animation_progress * math.pi)) / 2
    if folder_view_blurred_bg is not None:
        folder_view_blurred_bg.set_alpha(int(255 * ease_progress)); screen.blit(folder_view_blurred_bg, (0, 0))
        overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA); overlay.fill((0, 0, 0, int(80 * ease_progress))); screen.blit(overlay, (0, 0))
    end_rect = pygame.Rect(30, SCREEN_HEIGHT / 2 - 150, SCREEN_WIDTH - 60, 300)
    start_rect = opened_folder_icon_rect if opened_folder_icon_rect else end_rect.copy()
    current_rect_vals = [s + (e - s) * ease_progress for s, e in zip(start_rect, end_rect)]; folder_rect = pygame.Rect(current_rect_vals)
    folder_bg_surface = pygame.Surface(folder_rect.size, pygame.SRCALPHA)
    bg_color = (0, 0, 0, 180) if is_dark_mode else (255, 255, 255, 180)
    draw_rounded_rect(folder_bg_surface, folder_bg_surface.get_rect(), bg_color, 20 * ease_progress)
    screen.blit(folder_bg_surface, folder_rect.topleft)
    if ease_progress > 0.9:
        folder_name_text = render_persian_text(opened_folder.get('name', 'پوشه'), text_font, get_current_color('settings_title'))
        screen.blit(folder_name_text, folder_name_text.get_rect(centerx=folder_rect.centerx, top=folder_rect.top + 15))
        folder_icons = opened_folder['contains']; cols = 3; padding = 20
        start_x = folder_rect.left + (folder_rect.width - (cols * icon_size + (cols - 1) * padding)) / 2; start_y = folder_rect.top + 50
        for i, icon in enumerate(folder_icons):
            target_x = start_x + (i % cols) * (icon_size + padding); target_y = start_y + (i // cols) * (icon_size + padding)
            if icon != selected_icon or not is_dragging_icon: icon['pos'] = [a + (b - a) * 0.3 for a, b in zip(icon['pos'], (target_x, target_y))]
            icon_x, icon_y = icon['pos']
            if is_folder_edit_mode and (icon != selected_icon or not is_dragging_icon):
                angle = time.time()*8 + i*2; icon_x += math.sin(angle)*1.5; icon_y += math.cos(angle*0.8)*1.5
            icon['rect'] = pygame.Rect(icon_x, icon_y, icon_size, icon_size); draw_icon_base(screen, icon, icon['rect'])

def draw_recents_screen():
    global recents_focused_index, target_recents_focused_index
    # (اصلاح شده) استفاده از منحنی ایزینگ قویتر برای شروع سریع و پایان نرم انیمیشن
    ease_progress = 1 - (1 - recents_animation_progress) ** 4
    
    if recents_view_blurred_bg is not None:
        recents_view_blurred_bg.set_alpha(int(255 * ease_progress))
        screen.blit(recents_view_blurred_bg, (0, 0))

    y_offset_anim = (1.0 - ease_progress) * SCREEN_HEIGHT
    
    # حرکت نرم به سمت کارت هدف
    recents_focused_index += (target_recents_focused_index - recents_focused_index) * 0.15

    card_width, card_height = 280, 500
    
    # رسم کارتها از آخر به اول تا روی هم به درستی قرار گیرند
    for i in range(len(recents_apps_list) - 1, -1, -1):
        app = recents_apps_list[i]
        
        # محاسبه فاصله کارت از کارت مرکزی (در حال فوکوس)
        distance = i - recents_focused_index
        
        # کارتهایی که خیلی دور هستند را رسم نکن
        if abs(distance) > 4:
            continue
            
        # محاسبه مقیاس و موقعیت بر اساس فاصله برای ایجاد پرسپکتیو
        scale = 1.0 - abs(distance) * 0.1
        card_x = SCREEN_WIDTH / 2 + distance * 100 - (card_width * scale) / 2
        card_y = SCREEN_HEIGHT / 2 - (card_height * scale) / 2 + abs(distance) * 25 + y_offset_anim

        # اعمال جابجایی عمودی هنگام حذف کارت
        if dragged_recent_app_index == i:
            card_y += dragged_recent_app_offset_y
        elif animating_recent_app_index == i:
            card_y += dragged_recent_app_offset_y

        scaled_size = (int(card_width * scale), int(card_height * scale))
        card_rect = pygame.Rect(card_x, card_y, *scaled_size)
        app['rect'] = card_rect

        # رسم محتوای کارت
        card_content_surf = pygame.Surface(scaled_size, pygame.SRCALPHA)
        if app.get('snapshot'):
            snapshot_scaled = pygame.transform.smoothscale(app['snapshot'], scaled_size)
            card_content_surf.blit(snapshot_scaled, (0, 0))
        else:
            default_bg_key = 'gallery_bg' if app['name'] == 'gallery' else 'notes_bg' if app['name'] == 'notes' else 'music_bg' if app['name'] == 'music' else 'browser_bg' if app['name'] == 'browser' else 'settings_bg'
            draw_rounded_rect(card_content_surf, card_content_surf.get_rect(), get_current_color(default_bg_key), 0)

        # ماسک برای گوشههای گرد
        mask = pygame.Surface(scaled_size, pygame.SRCALPHA)
        draw_rounded_rect(mask, mask.get_rect(), (255, 255, 255, 255), 20 * scale)
        card_content_surf.blit(mask, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)
        
        screen.blit(card_content_surf, card_rect.topleft)

        # رسم نام برنامه (فقط برای کارت اصلی)
        if abs(distance) < 0.5:
             app_name_surf = render_persian_text(app['name'], text_font, WHITE)
             name_bg_rect = pygame.Rect(0, 0, app_name_surf.get_width() + 20, app_name_surf.get_height() + 10)
             name_bg_rect.centerx = card_rect.centerx
             name_bg_rect.top = card_rect.top - 40 - y_offset_anim # بالاتر از کارت
             
             # محو شدن نام هنگام اسکرول
             name_alpha = (1 - abs(distance) * 2) * 255 * ease_progress
             name_bg_surf = pygame.Surface(name_bg_rect.size, pygame.SRCALPHA)
             draw_rounded_rect(name_bg_surf, name_bg_surf.get_rect(), (0, 0, 0, 100), 10)
             
             name_bg_surf.set_alpha(name_alpha)
             app_name_surf.set_alpha(name_alpha)

             screen.blit(name_bg_surf, name_bg_rect)
             screen.blit(app_name_surf, app_name_surf.get_rect(center=name_bg_rect.center))

        for app in closing_recent_apps:
            progress = app['anim_progress']
            ease_progress = 1 - (1 - progress) ** 3 # نرمی حرکت
            
            # کارت به سمت بالا حرکت کرده و محو میشود
            y_offset = -ease_progress * 300
            alpha = 255 * (1 - ease_progress)
            
            # از Rect ذخیره شده قبلی برای موقعیت اولیه استفاده میکنیم
            original_rect = app['rect']
            
            card_rect = original_rect.move(0, y_offset)
            
            # رسم محتوای کارت با آلفای محاسبه شده
            card_content_surf = pygame.Surface(card_rect.size, pygame.SRCALPHA)
            if app.get('snapshot'):
                snapshot_scaled = pygame.transform.smoothscale(app['snapshot'], card_rect.size)
                card_content_surf.blit(snapshot_scaled, (0, 0))
            else:
                default_bg_key = 'settings_bg'
                draw_rounded_rect(card_content_surf, card_content_surf.get_rect(), get_current_color(default_bg_key), 0)

            # ماسک گوشههای گرد
            mask = pygame.Surface(card_rect.size, pygame.SRCALPHA)
            draw_rounded_rect(mask, mask.get_rect(), (255, 255, 255, 255), 20 * original_rect.width / 280)
            card_content_surf.blit(mask, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)
            
            card_content_surf.set_alpha(alpha)
            screen.blit(card_content_surf, card_rect.topleft)

# --------------------------
#       حلقه اصلی برنامه
# --------------------------
running = True
app_swipe_interactive_progress = 0.0
is_returning_app_to_open = False

add_main_notification("تنظیمات", "سیستم", "سیستم راه اندازی شد.", icon_name="settings")

while running:
    dt = clock.get_time() / 1000.0
    mouse_pos = pygame.mouse.get_pos()
    events = pygame.event.get()
    kernel.kernel_instance.update()
    if is_language_picker_open and language_picker_progress > 0.9:
        for event in events: # رویدادها را جداگانه پردازش میکنیم
            if event.type == pygame.QUIT: running = False
            if event.type == pygame.MOUSEBUTTONUP and event.button == 1:
                temp_surf = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
                lang_buttons = draw_language_picker(temp_surf, 1.0) # رسم برای گرفتن rects

                clicked_inside_button = False
                for key, rect in lang_buttons.items():
                    if rect.collidepoint(event.pos):
                        lang_code = key.split('_')[1]
                        if lang_code != current_language:
                            current_language = lang_code
                            # (نام نمایشی در load_language_data بهروز میشود)
                            save_settings()
                            load_language_data() # (مهم) بارگذاری مجدد دیکشنری زبان

                        is_language_picker_open = False
                        clicked_inside_button = True
                        break

                if not clicked_inside_button:
                    # اگر روی دکمهای کلیک نشده بود، مودال را ببند
                    is_language_picker_open = False

                # این رویداد پردازش شد، آن را از لیست اصلی حذف کن
                events.remove(event)
                # از آنجایی که لیست رویدادها را تغییر دادیم، حلقه داخلی را بشکن
                break

                for btn_name, btn_data in cc_buttons.items():
                    if btn_data.get('type') == 'media_btn' and btn_data.get('rect') and btn_data['rect'].collidepoint(event.pos):
                        if btn_name == 'media_prev':
                            play_previous_song()
                        elif btn_name == 'media_play':
                            toggle_music_play_pause()
                        elif btn_name == 'media_next':
                            play_next_song()
                        break 
        
    for event in events:
        if event.type == pygame.QUIT: running = False
        if event.type == MUSIC_ENDED: play_next_song()

        if current_screen == "app_open" and app_context.get('is_external_app'):
            app_instance = running_app_instances.get(app_context['app_id'])
            if app_instance:
                app_instance.handle_event(event)

        #if app_context.get('app_type') == 'remote' and session_id:
            #display_server.remove_app(session_id)
        
        # بعد از حلقه رویدادها در app_open
        if app_context.get('app_type') == 'remote':
            session_id = app_context.get('session_id')
            if session_id is not None:
                # فقط رویدادهای داخل محدوده برنامه
                display_server.send_events_to_app(session_id, events)

        if is_low_battery_warning_visible and low_battery_warning_progress > 0.9 and event.type == pygame.MOUSEBUTTONUP and event.button == 1:
            temp_surface_for_buttons = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
            understand_rect, saver_rect = draw_low_battery_warning(temp_surface_for_buttons)
            if understand_rect.collidepoint(event.pos) or saver_rect.collidepoint(event.pos):
                is_low_battery_warning_visible = False
                continue

        if is_notification_center_open and notification_center_progress > 0.9:
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                nc_rect = pygame.Rect(10, 50, SCREEN_WIDTH - 20, SCREEN_HEIGHT - 100)
                if not nc_rect.collidepoint(event.pos):
                    is_notification_center_open = False

        # (بلوک کاملاً اصلاح شده برای مدیریت رویدادهای CC جدید)
        if is_control_center_open and control_center_progress > 0.9:
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                cc_rect_inner = pygame.Rect(10, 50 + cc_vertical_offset, SCREEN_WIDTH - 20, SCREEN_HEIGHT - 100)
                if not cc_rect_inner.collidepoint(event.pos):
                    is_control_center_open = False
                    continue # از پردازش بقیه رویدادها خارج شو

                is_dragging_cc_content = True
                cc_drag_start_y = event.pos[1]
                
                # بررسی کلیک روی اسلایدرها
                if cc_buttons.get('brightness_slider', {}).get('rect', pygame.Rect(0,0,0,0)).collidepoint(event.pos):
                    is_scrubbing_brightness = True
                    is_dragging_cc_content = False # اسکراب کردن اسلایدر نباید کل پنل را بکشد
                elif cc_buttons.get('volume_slider', {}).get('rect', pygame.Rect(0,0,0,0)).collidepoint(event.pos):
                    is_scrubbing_volume = True
                    is_dragging_cc_content = False
                
                # بررسی کلیک روی دکمهها
                for btn_name, btn_data in cc_buttons.items():
                    if btn_data.get('rect') and btn_data['rect'].collidepoint(event.pos):
                        btn_data['is_pressed'] = True
                        if btn_data.get('type') == 'large': # دکمههای بزرگ افکت فشاری دارند
                            btn_data['press_location'] = event.pos
                        break # فقط یک دکمه در هر کلیک

            if event.type == pygame.MOUSEMOTION:
                if is_dragging_cc_content:
                    delta_y = event.pos[1] - cc_drag_start_y
                    if delta_y > 0: # فقط کشیدن به پایین مجاز است
                        cc_vertical_offset = delta_y * 0.4
                
                # مدیریت حرکت روی اسلایدرها
                if is_scrubbing_brightness:
                    rect = cc_buttons['brightness_slider']['rect']
                    # محاسبه بر اساس پدینگ داخل اسلایدر
                    bar_inner_width = rect.width - 80 # (40 padding left, 40 padding right in draw_cc_slider)
                    click_x = event.pos[0] - (rect.left + 40)
                    cc_brightness = max(0.0, min(1.0, click_x / bar_inner_width))
                
                if is_scrubbing_volume:
                    rect = cc_buttons['volume_slider']['rect']
                    bar_inner_width = rect.width - 80
                    click_x = event.pos[0] - (rect.left + 40)
                    cc_volume = max(0.0, min(1.0, click_x / bar_inner_width))

            if event.type == pygame.MOUSEBUTTONUP and event.button == 1:
                if is_dragging_cc_content:
                    is_dragging_cc_content = False
                    target_cc_vertical_offset = 0.0 # بازگشت پنل به جای اول
                
                is_scrubbing_brightness = False
                is_scrubbing_volume = False

                for btn_name, btn_data in cc_buttons.items():
                    # چک کردن اگر دکمه فشرده شده بود
                    if btn_data.get('is_pressed'):
                        # اگر ماوس هنوز روی دکمه بود، آن را فعال/غیرفعال کن
                        if btn_data.get('rect') and btn_data['rect'].collidepoint(event.pos):
                            btn_data['is_active'] = not btn_data['is_active']
                            # (اختیاری) میتوانید اینجا منطق واقعی را اضافه کنید
                            # if btn_name == 'flashlight': print("Flashlight toggled")
                    
                    # ریست کردن وضعیت فشرده شدن
                    btn_data['is_pressed'] = False
                    if btn_data.get('type') == 'large':
                        btn_data['press_location'] = None

        if is_charging_animation_active and event.type == pygame.MOUSEBUTTONDOWN:
            charging_animation_should_end = True
            continue

        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if event.pos[0] > SCREEN_WIDTH - 60 and event.pos[1] < 60 and not is_control_center_open and not is_notification_center_open:
                is_dragging_control_center = True
            elif event.pos[0] < 60 and event.pos[1] < 60 and not is_notification_center_open and not is_control_center_open:
                is_dragging_notification_center = True

        if event.type == pygame.MOUSEMOTION:
            if is_dragging_control_center and event.pos[1] > 80:
                # (جدید) بررسی میکنیم که آیا از قبل باز نشده یا در حال پردازش نیست
                if not is_control_center_open and not is_blur_processing:
                    is_control_center_open = True
                    is_dragging_control_center = False
                    is_blur_processing = True # (قفل کردن برای جلوگیری از اجرای مجدد)
                    snapshot = screen.copy()
                    
                    # (جدید) به جای اجرای مستقیم، آن را به نخ میسپاریم
                    thread = threading.Thread(target=process_blur_in_thread, args=(snapshot,))
                    thread.start()
                    
                    # (مهم) اسنپشات را پاک میکنیم تا بعداً از نتیجه نخ استفاده شود
                    control_center_snapshot = None
            elif is_dragging_notification_center and event.pos[1] > 80:
                is_notification_center_open = True
                is_dragging_notification_center = False
                snapshot = screen.copy()
                notification_center_snapshot = apply_gaussian_blur(snapshot, iterations=15)

        if event.type == pygame.MOUSEBUTTONUP and event.button == 1:
            is_dragging_control_center = False
            is_dragging_notification_center = False

        if current_screen == "recents":
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_RIGHT: target_recents_focused_index = max(0, target_recents_focused_index - 1)
                elif event.key == pygame.K_LEFT: target_recents_focused_index = min(len(recents_apps_list) - 1, target_recents_focused_index + 1)

            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                recents_mouse_down_pos = event.pos
                if event.pos[1] < 100 or event.pos[1] > SCREEN_HEIGHT - 100:
                    current_screen = "recents_closing"
                else:
                    is_swiping_home = True; home_swipe_start_pos = event.pos
                    if animating_recent_app_index is not None:
                        animating_recent_app_index = None
                        dragged_recent_app_offset_y = 0
                    for i, app in enumerate(recents_apps_list):
                        if app.get('rect') and app['rect'].collidepoint(event.pos):
                            if abs(i - recents_focused_index) > 0.5:
                                target_recents_focused_index = i
                            else:
                                dragged_recent_app_index = i
                            break
            elif event.type == pygame.MOUSEMOTION:
                if is_swiping_home:
                    if dragged_recent_app_index is not None:
                        dragged_recent_app_offset_y += event.rel[1]
                    else:
                        move_ratio = -event.rel[0] / (SCREEN_WIDTH * 0.5)
                        target_recents_focused_index += move_ratio
                        target_recents_focused_index = max(0, min(len(recents_apps_list) - 1, target_recents_focused_index))
            elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
                is_click = recents_mouse_down_pos and pygame.math.Vector2(event.pos).distance_to(recents_mouse_down_pos) < 10
                if not dragged_recent_app_index:
                    target_recents_focused_index = round(target_recents_focused_index)
                if is_click and dragged_recent_app_index is not None:
                    clicked_app = recents_apps_list[dragged_recent_app_index]
                    current_screen, app_animation_progress = "app_opening", 0.0
                    opened_app_icon_rect = clicked_app['rect'].copy()
                    app_name = clicked_app['name']
                    notes_module = NotesApp(sc, mf, get_current_color, render_persian_text)
                    app_context = {'app_name': app_name, 'screen': 'main'}
                    if app_name in ['notes', 'music', 'browser', 'gallery', 'files', 'messenger']: app_context['screen'] = f"{app_name}_main"
                    if app_name == 'messenger':
                        messenger_start_server()  # شروع سرور UDP اگه در حال اجرا نباشه
                    if clicked_app.get('app_id'):
                        app_context['app_id'] = clicked_app.get('app_id')
                        app_context['is_external_app'] = True
                elif dragged_recent_app_index is not None:
                    if dragged_recent_app_offset_y < -150:
                        app_to_close = recents_apps_list.pop(dragged_recent_app_index)
                        app_to_close['anim_progress'] = 0.0
                        closing_recent_apps.append(app_to_close)
                        target_recents_focused_index = max(0, min(len(recents_apps_list) - 1, target_recents_focused_index))
                        dragged_recent_app_offset_y = 0
                    else:
                        animating_recent_app_index = dragged_recent_app_index
                        target_dragged_recent_app_offset_y = 0
                dragged_recent_app_index, is_swiping_home = False, False

        if is_showing_folder and folder_animation_progress > 0.9:
            folder_rect = pygame.Rect(30, SCREEN_HEIGHT/2 - 150, SCREEN_WIDTH-60, 300)
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                folder_mouse_down_pos = event.pos
                selected_icon_in_folder = get_icon_at_pos(mouse_pos, opened_folder['contains'])
                if selected_icon_in_folder: folder_mouse_down_start_time = time.time()
                elif not folder_rect.collidepoint(mouse_pos):
                    is_showing_folder, is_folder_edit_mode, folder_just_closed, is_dragging_icon, selected_icon = False, False, True, False, None
            elif event.type == pygame.MOUSEMOTION and is_dragging_icon:
                selected_icon['pos'] = [mouse_pos[0] + icon_drag_offset[0], mouse_pos[1] + icon_drag_offset[1]]; selected_icon['rect'].topleft = selected_icon['pos']
            elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
                if is_dragging_icon and selected_icon:
                    if not folder_rect.collidepoint(event.pos):
                        opened_folder['contains'].remove(selected_icon)
                        new_row, new_col = get_grid_pos(event.pos); selected_icon.update({'page': home_page_index, 'row': new_row, 'col': new_col})
                        icons[home_page_index].append(selected_icon); is_showing_folder = False
                        if not opened_folder['contains']:
                            container = dock_icons if opened_folder in dock_icons else icons[opened_folder['page']]
                            if opened_folder in container:
                                folders_to_delete.append({'folder': opened_folder, 'progress': 1.0, 'rect': opened_folder['rect'].copy()}); container.remove(opened_folder)
                    is_dragging_icon, selected_icon, is_folder_edit_mode = False, None, False
                elif selected_icon_in_folder and not is_folder_edit_mode:
                    is_click = pygame.math.Vector2(event.pos).distance_to(folder_mouse_down_pos) < 10
                    if is_click and selected_icon_in_folder['type'] == 'app':
                        current_screen, app_animation_progress = "app_opening", 0.0; opened_app_icon_rect = selected_icon_in_folder['rect'].copy()
                        app_name = selected_icon_in_folder['name']
                        app_context = {'app_name': app_name, 'screen': 'main'}
                        if app_name in ['notes', 'music', 'browser', 'files', 'gallery', 'messenger']: app_context['screen'] = f"{app_name}_main"
                        if selected_icon_in_folder.get('app_id'):
                            app_context['app_id'] = selected_icon_in_folder.get('app_id')
                            app_context['is_external_app'] = True
                        is_showing_folder, is_folder_edit_mode = False, False
                folder_mouse_down_start_time, selected_icon_in_folder = 0, None

        elif current_screen == "lock":
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1: is_swiping_lock, lock_swipe_start_pos = True, event.pos
            elif event.type == pygame.MOUSEMOTION and is_swiping_lock:
                if event.pos[1] - lock_swipe_start_pos[1] < 0: lock_screen_offset_y = event.pos[1] - lock_swipe_start_pos[1]
            elif event.type == pygame.MOUSEBUTTONUP and event.button == 1 and is_swiping_lock:
                is_swiping_lock = False
                if lock_swipe_start_pos and lock_swipe_start_pos[1] - event.pos[1] > lock_swipe_threshold:
                    current_screen, animation_progress, lock_screen_snapshot = "animating_unlock", 0.0, screen.copy()
                else: target_lock_offset_y = 0

        elif current_screen == "home":
            if folder_just_closed: folder_just_closed = False; continue
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                if time.time() - app_close_timestamp < 0.1: continue
                if event.pos[1] > SCREEN_HEIGHT - 40:
                    is_swiping_for_recents, recents_swipe_start_pos, recents_swipe_start_time = True, event.pos, time.time()
                else:
                    selected_icon_home, selected_icon_dock = get_icon_at_pos(mouse_pos, icons[home_page_index]), get_icon_at_pos(mouse_pos, dock_icons)
                    if selected_icon_dock: selected_icon, selected_icon_source = selected_icon_dock, 'dock'
                    elif selected_icon_home: selected_icon, selected_icon_source = selected_icon_home, 'home'
                    else: selected_icon, selected_icon_source = None, None
                    if selected_icon and not is_edit_mode:
                        pressed_icon, pressed_icon_animation_direction = selected_icon, 1
                    if is_edit_mode and selected_icon:
                        is_dragging_icon = True
                        icon_drag_offset = (selected_icon['pos'][0] - mouse_pos[0], selected_icon['pos'][1] - mouse_pos[1])
                    elif is_edit_mode and not selected_icon:
                         is_edit_mode, target_edit_mode_scale = False, 1.0; save_layout()
                    else:
                        if mouse_pos[1] < SCREEN_HEIGHT - 120 or dock_rect.collidepoint(mouse_pos):
                            is_swiping_home, home_swipe_start_pos = True, mouse_pos
                            if selected_icon: mouse_down_start_time = time.time()
            elif event.type == pygame.MOUSEMOTION:
                if is_dragging_icon and selected_icon:
                    selected_icon['pos'] = [mouse_pos[0] + icon_drag_offset[0], mouse_pos[1] + icon_drag_offset[1]]
                    if time.time() > page_swipe_timer:
                        if mouse_pos[0] < 40 and home_page_index > 0: target_offset, page_swipe_timer = SCREEN_WIDTH, time.time() + PAGE_SWIPE_COOLDOWN
                        elif mouse_pos[0] > SCREEN_WIDTH - 40 and home_page_index < num_home_pages - 1: target_offset, page_swipe_timer = -SCREEN_WIDTH, time.time() + PAGE_SWIPE_COOLDOWN
                elif is_swiping_home:
                    new_offset = mouse_pos[0] - home_swipe_start_pos[0]
                    if (home_page_index == 0 and new_offset > 0) or (home_page_index == num_home_pages - 1 and new_offset < 0): home_page_offset += (new_offset - home_page_offset) * 0.1
                    else: home_page_offset = new_offset
                    if abs(home_page_offset) > 15: mouse_down_start_time = 0
            elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
                if pressed_icon: pressed_icon_animation_direction = -1
                if is_swiping_for_recents:
                    swipe_dist = recents_swipe_start_pos[1] - event.pos[1]; swipe_time = time.time() - recents_swipe_start_time
                    if swipe_dist > 80 or (swipe_dist > 40 and swipe_time < 0.3):
                        current_screen, recents_animation_progress = "recents_opening", 0.0; bg_snapshot = screen.copy(); recents_view_blurred_bg = apply_gaussian_blur(bg_snapshot)
                    is_swiping_for_recents = False
                is_click = not is_swiping_home or (home_swipe_start_pos and pygame.math.Vector2(event.pos).distance_to(home_swipe_start_pos) < 10)

                if is_dragging_icon and selected_icon:
                    if dock_rect.collidepoint(event.pos) and len(dock_icons) < MAX_DOCK_ICONS and selected_icon_source == 'home' and selected_icon.get('type') != 'widget':
                        icons[selected_icon['page']].remove(selected_icon)
                        dock_icons.append(selected_icon)
                    elif not dock_rect.collidepoint(event.pos) and selected_icon_source == 'dock':
                        dock_icons.remove(selected_icon)
                        new_row, new_col = get_grid_pos(event.pos, selected_icon)
                        selected_icon.update({'page': home_page_index, 'row': new_row, 'col': new_col})
                        icons[home_page_index].append(selected_icon)
                    elif not folder_hover_target and selected_icon_source != 'dock':
                        item_w, item_h = (1,1)
                        if selected_icon.get('type') == 'widget':
                            item_w, item_h = selected_icon.get('size', (1,1))

                        new_row, new_col = get_grid_pos(event.pos, selected_icon)

                        if is_grid_area_free(home_page_index, new_row, new_col, item_w, item_h, selected_icon):
                             selected_icon.update({'row': new_row, 'col': new_col, 'page': home_page_index})
                    is_dragging_icon, selected_icon = False, None

                elif is_swiping_home:
                    delta_x = event.pos[0] - home_swipe_start_pos[0]
                    if delta_x < -home_swipe_threshold and home_page_index < num_home_pages-1: target_offset = -SCREEN_WIDTH
                    elif delta_x > home_swipe_threshold and home_page_index > 0: target_offset = SCREEN_WIDTH
                    else: target_offset = 0
                if not is_edit_mode and is_click and selected_icon:
                    if selected_icon['type'] == 'app':
                        current_screen, app_animation_progress = "app_opening", 0.0; opened_app_icon_rect = selected_icon['rect'].copy()
                        app_name = selected_icon['name']
                        # وقتی روی آیکون فایلها کلیک شد
                        if app_name == 'files': 
                            files_current_path = '.' 
                            files_list = scan_directory('.') # اسکن اولیه با تابع جدید
                            target_files_scroll_offset, files_scroll_offset = 0.0, 0.0
                        app_context = {'app_name': app_name, 'screen': 'main'}
                        if app_name in ['notes', 'music', 'browser', 'files', 'gallery', 'messenger']: app_context['screen'] = f"{app_name}_main"
                        if selected_icon.get('app_id'):
                            app_context['app_id'] = selected_icon.get('app_id')
                            app_context['is_external_app'] = True

                        target_app_snapshot = get_app_snapshot(app_name, app_context['screen'])
                        
                    elif selected_icon['type'] == 'folder':
                        is_showing_folder, opened_folder, opened_folder_icon_rect = True, selected_icon, selected_icon['rect'].copy()
                        bg_snapshot = screen.copy(); folder_view_blurred_bg = apply_gaussian_blur(bg_snapshot)
                    selected_icon = None
                is_swiping_home, mouse_down_start_time, folder_hover_target = False, 0, None

        elif current_screen == "app_open":
            app_name, app_page = app_context.get('app_name'), app_context.get('screen')
            if is_swiping_app_close:
                if event.type == pygame.MOUSEMOTION:
                    swipe_distance = app_swipe_start_pos[1] - event.pos[1]
                    app_swipe_interactive_progress = max(0, min(1, swipe_distance / (SCREEN_HEIGHT * 0.6)))
                elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
                    is_swiping_app_close = False
                    if app_swipe_interactive_progress > 0.4:
                        current_screen = "app_closing"
                        app_animation_progress = 1.0 - app_swipe_interactive_progress
                    else:
                        is_returning_app_to_open = True
                continue

            if app_name == 'messenger':
                # =====================================================
                # --- event handling پیام‌رسان SMS ---
                # =====================================================
                btns_m = {}
                temp_m = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT))
                btns_m = draw_messenger_app(temp_m)

                if event.type == pygame.MOUSEBUTTONUP and event.button == 1:
                    if btns_m.get('new_chat') and btns_m['new_chat'].collidepoint(event.pos):
                        messenger_page = 'new'
                        messenger_new_ip_text = ""
                        messenger_new_name_text = ""
                        messenger_new_peer_ip = ""
                        messenger_new_focus = 'name'
                    elif btns_m.get('name_field') and btns_m['name_field'].collidepoint(event.pos):
                        messenger_new_focus = 'name'
                    elif btns_m.get('ip_field') and btns_m['ip_field'].collidepoint(event.pos):
                        messenger_new_focus = 'ip'
                    elif btns_m.get('peer_ip_field') and btns_m['peer_ip_field'].collidepoint(event.pos):
                        messenger_new_focus = 'peer_ip'
                    elif btns_m.get('add_contact') and btns_m['add_contact'].collidepoint(event.pos):
                        _ip = messenger_new_ip_text.strip()
                        _nm = messenger_new_name_text.strip() or _ip
                        _pip = messenger_new_peer_ip.strip()
                        if _ip:
                            # اعتبارسنجی فرمت شماره تلفن
                            if not (_ip.startswith('+') and len(_ip) >= 10):
                                add_unimportant_notification("شماره باید با + شروع شود  مثال: +989123456789")
                            else:
                                existing = next((c for c in messenger_contacts if c['addr'] == _ip), None)
                                if existing:
                                    if _pip: existing['ip'] = _pip
                                else:
                                    messenger_contacts.append({'name': _nm, 'addr': _ip, 'ip': _pip})
                                    if _ip not in messenger_conversations:
                                        messenger_conversations[_ip] = []
                                _messenger_save_data()
                                messenger_start_server()
                                messenger_active_conv = _ip
                                messenger_page = 'chat'
                                messenger_new_ip_text = ""
                                messenger_new_name_text = ""
                                messenger_new_peer_ip = ""
                                add_unimportant_notification(f"مخاطب {_nm} اضافه شد")
                    # کلیک روی نتایج اسکن در صفحه new
                    elif True:
                        for _key, _rect in btns_m.items():
                            if _key.startswith('found_') and isinstance(_rect, pygame.Rect) and _rect.collidepoint(event.pos):
                                _idx = int(_key.split('_')[1])
                                if 0 <= _idx < len(messenger_contacts):
                                    _c = messenger_contacts[_idx]
                                    messenger_new_ip_text = _c['addr']
                                    messenger_new_name_text = _c['name']
                                break
                    if btns_m.get('back') and btns_m['back'].collidepoint(event.pos):
                        messenger_page = 'chats'
                        messenger_active_conv = None
                    elif btns_m.get('send') and btns_m['send'].collidepoint(event.pos):
                        if messenger_input_text.strip() and messenger_active_conv:
                            ok = messenger_send(messenger_active_conv, messenger_input_text.strip())
                            if ok:
                                messenger_input_text = ""
                            else:
                                add_unimportant_notification("خطا در ارسال پیام")
                    elif btns_m.get('input_field') and btns_m['input_field'].collidepoint(event.pos):
                        pass  # کاربر روی فیلد کلیک کرد — keyboard active
                    else:
                        # کلیک روی مخاطب
                        for key, rect in btns_m.items():
                            if key.startswith('conv_') and isinstance(rect, pygame.Rect) and rect.collidepoint(event.pos):
                                idx2 = int(key.split('_')[1])
                                if 0 <= idx2 < len(messenger_contacts):
                                    contact2 = messenger_contacts[idx2]
                                    messenger_active_conv = contact2['addr']
                                    messenger_page = 'chat'
                                    messenger_notification_badge = 0
                                    messenger_target_scroll = 99999.0
                                break

                if event.type == pygame.KEYDOWN:
                    if messenger_page == 'new':
                        if event.key == pygame.K_BACKSPACE:
                            if messenger_new_focus == 'ip':
                                messenger_new_ip_text = messenger_new_ip_text[:-1]
                            elif messenger_new_focus == 'peer_ip':
                                messenger_new_peer_ip = messenger_new_peer_ip[:-1]
                            else:
                                messenger_new_name_text = messenger_new_name_text[:-1]
                        elif event.key == pygame.K_TAB:
                            _focus_cycle = ['name', 'ip', 'peer_ip']
                            _idx = _focus_cycle.index(messenger_new_focus) if messenger_new_focus in _focus_cycle else 0
                            messenger_new_focus = _focus_cycle[(_idx + 1) % len(_focus_cycle)]
                        elif event.key == pygame.K_RETURN:
                            _ip = messenger_new_ip_text.strip()
                            _nm = messenger_new_name_text.strip() or _ip
                            _pip = messenger_new_peer_ip.strip()
                            if _ip:
                                if not (_ip.startswith('+') and len(_ip) >= 10):
                                    add_unimportant_notification("شماره باید با + شروع شود")
                                else:
                                    existing = next((c for c in messenger_contacts if c['addr'] == _ip), None)
                                    if existing:
                                        if _pip: existing['ip'] = _pip
                                    else:
                                        messenger_contacts.append({'name': _nm, 'addr': _ip, 'ip': _pip})
                                        if _ip not in messenger_conversations:
                                            messenger_conversations[_ip] = []
                                    _messenger_save_data()
                                    messenger_start_server()
                                    messenger_active_conv = _ip
                                    messenger_page = 'chat'
                                    add_unimportant_notification(f"مخاطب {_nm} اضافه شد")
                        elif event.unicode:
                            if messenger_new_focus == 'ip':
                                # کاراکترهای مجاز شماره تلفن
                                if event.unicode in '0123456789+':
                                    messenger_new_ip_text += event.unicode
                            elif messenger_new_focus == 'peer_ip':
                                # کاراکترهای مجاز IP
                                if event.unicode in '0123456789.':
                                    messenger_new_peer_ip += event.unicode
                            else:
                                messenger_new_name_text += event.unicode
                    elif messenger_page == 'chat':
                        if event.key == pygame.K_RETURN:
                            if messenger_input_text.strip() and messenger_active_conv:
                                ok = messenger_send(messenger_active_conv, messenger_input_text.strip())
                                if ok: messenger_input_text = ""
                        elif event.key == pygame.K_BACKSPACE:
                            messenger_input_text = messenger_input_text[:-1]
                        elif event.unicode:
                            messenger_input_text += event.unicode

                if event.type == pygame.MOUSEWHEEL and messenger_page == 'chat':
                    messenger_target_scroll = max(0.0, messenger_target_scroll - event.y * 30)

            if app_name == 'gallery':
                # ============================================================
                # --- ویرایشگر عکس ---
                # ============================================================
                if is_gallery_editor_open:
                    # --- rects ثابت toolbar (دقیقاً منطبق با draw_gallery_editor) ---
                    _BOT = 200; _TOP = 60
                    _back_r = pygame.Rect(12, 15, 70, 32)
                    _undo_r = pygame.Rect(90, 15, 55, 32)
                    _save_r = pygame.Rect(SCREEN_WIDTH - 80, 15, 68, 32)
                    _tools_k = ['pen','eraser','line','rect','text']
                    _tsz = 44
                    _ttw = len(_tools_k)*_tsz + (len(_tools_k)-1)*10
                    _tx0 = (SCREEN_WIDTH - _ttw)//2
                    _ty  = SCREEN_HEIGHT - _BOT + 18
                    _tool_r = {t: pygame.Rect(_tx0+i*(_tsz+10), _ty, _tsz, _tsz) for i,t in enumerate(_tools_k)}
                    _sizes_k = [2,4,7,12,20]
                    _szy = SCREEN_HEIGHT - _BOT + 78
                    _size_r = {sz: pygame.Rect(75+i*42, _szy, 36, 36) for i,sz in enumerate(_sizes_k)}
                    _coly = SCREEN_HEIGHT - _BOT + 124
                    _col_r = {i: (pygame.Rect(70+i*34, _coly, 28, 28), c) for i,c in enumerate(gallery_editor_colors)}
                    _img_r = gallery_editor_img_rect or pygame.Rect(0, _TOP, SCREEN_WIDTH, SCREEN_HEIGHT-_TOP-_BOT)

                    def _s2img(p):
                        if gallery_editor_surface is None: return p
                        _ew, _eh = gallery_editor_surface.get_size()
                        if _img_r.width==0 or _img_r.height==0: return p
                        return (max(0,min(_ew-1, int((p[0]-_img_r.x)*_ew/_img_r.width))),
                                max(0,min(_eh-1, int((p[1]-_img_r.y)*_eh/_img_r.height))))

                    if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                        _p = event.pos
                        if _back_r.collidepoint(_p):
                            is_gallery_editor_open = False
                        elif _undo_r.collidepoint(_p):
                            gallery_editor_undo()
                        elif _save_r.collidepoint(_p):
                            try:
                                pd = gallery_photos[gallery_selected_index]
                                pygame.image.save(gallery_editor_surface, pd['path'])
                                pd['image'] = gallery_editor_surface.copy()
                                pd['thumb'] = None
                                add_unimportant_notification("تصویر ذخیره شد")
                                is_gallery_editor_open = False
                            except Exception as ex:
                                add_unimportant_notification("خطا در ذخیره"); print(ex)
                        else:
                            _handled = False
                            for _tk, _tr in _tool_r.items():
                                if _tr.collidepoint(_p):
                                    gallery_editor_tool = _tk
                                    if _tk == 'text':
                                        gallery_editor_text_input = True
                                        gallery_editor_pending_text = ""
                                        gallery_editor_text_pos = None
                                    else:
                                        gallery_editor_text_input = False
                                    _handled = True; break
                            if not _handled:
                                for _sz, _sr in _size_r.items():
                                    if _sr.collidepoint(_p):
                                        gallery_editor_size = _sz; _handled = True; break
                            if not _handled:
                                for _ci, (_cr, _col) in _col_r.items():
                                    if _cr.collidepoint(_p):
                                        gallery_editor_color = _col; _handled = True; break
                            if not _handled and _img_r.collidepoint(_p):
                                if gallery_editor_tool == 'text':
                                    gallery_editor_text_pos = _s2img(_p)
                                    gallery_editor_text_input = True
                                    gallery_editor_pending_text = ""
                                else:
                                    gallery_editor_save_state()
                                    gallery_editor_is_drawing = True
                                    gallery_editor_last_pos = _s2img(_p)
                                    gallery_editor_start_pos = _s2img(_p)
                                    if gallery_editor_tool == 'pen' and gallery_editor_surface:
                                        pygame.draw.circle(gallery_editor_surface, gallery_editor_color,
                                                           gallery_editor_last_pos, gallery_editor_size)

                    elif event.type == pygame.MOUSEMOTION and gallery_editor_is_drawing and gallery_editor_surface:
                        if _img_r.collidepoint(event.pos):
                            _cp = _s2img(event.pos)
                            if gallery_editor_tool == 'pen' and gallery_editor_last_pos:
                                pygame.draw.line(gallery_editor_surface, gallery_editor_color,
                                                 gallery_editor_last_pos, _cp, gallery_editor_size * 2)
                                pygame.draw.circle(gallery_editor_surface, gallery_editor_color, _cp, gallery_editor_size)
                                gallery_editor_mark_dirty()
                            elif gallery_editor_tool == 'eraser' and gallery_editor_last_pos:
                                pygame.draw.circle(gallery_editor_surface, (255,255,255), _cp, gallery_editor_size*3)
                                gallery_editor_mark_dirty()
                            gallery_editor_last_pos = _cp

                    elif event.type == pygame.MOUSEBUTTONUP and event.button == 1 and gallery_editor_is_drawing:
                        if gallery_editor_surface and gallery_editor_start_pos:
                            _cp = _s2img(event.pos)
                            if gallery_editor_tool == 'line':
                                pygame.draw.line(gallery_editor_surface, gallery_editor_color,
                                                 gallery_editor_start_pos, _cp, gallery_editor_size)
                                gallery_editor_mark_dirty()
                            elif gallery_editor_tool == 'rect':
                                _rx = min(gallery_editor_start_pos[0], _cp[0])
                                _ry = min(gallery_editor_start_pos[1], _cp[1])
                                pygame.draw.rect(gallery_editor_surface, gallery_editor_color,
                                    pygame.Rect(_rx,_ry,abs(_cp[0]-gallery_editor_start_pos[0]),abs(_cp[1]-gallery_editor_start_pos[1])),
                                    gallery_editor_size)
                                gallery_editor_mark_dirty()
                        gallery_editor_is_drawing = False
                        gallery_editor_last_pos = None

                    elif event.type == pygame.KEYDOWN and gallery_editor_text_input and gallery_editor_tool == 'text':
                        if event.key == pygame.K_RETURN:
                            if gallery_editor_pending_text and gallery_editor_text_pos and gallery_editor_surface:
                                gallery_editor_save_state()
                                _pf = pygame.font.Font(main_font_path, gallery_editor_size*2+10) if main_font_path else pygame.font.Font(None, gallery_editor_size*2+14)
                                gallery_editor_surface.blit(_pf.render(gallery_editor_pending_text, True, gallery_editor_color), gallery_editor_text_pos)
                                gallery_editor_mark_dirty()
                                gallery_editor_pending_text = ""
                                gallery_editor_text_pos = None
                                gallery_editor_text_input = False
                        elif event.key == pygame.K_ESCAPE:
                            gallery_editor_pending_text = ""
                            gallery_editor_text_input = False
                        elif event.key == pygame.K_BACKSPACE:
                            gallery_editor_pending_text = gallery_editor_pending_text[:-1]
                        elif event.unicode:
                            gallery_editor_pending_text += event.unicode

                elif is_video_playing:
                    # --- رویدادهای پلیر ویدیو ---
                    if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                        temp_s = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT))
                        vbtns = draw_video_player(temp_s)
                        if vbtns.get('close_btn') and vbtns['close_btn'].collidepoint(event.pos):
                            close_video()
                        elif vbtns.get('seek_bar') and vbtns['seek_bar'].collidepoint(event.pos):
                            is_scrubbing_video = True
                            sx = vbtns['seek_bar'].x
                            sw_ = vbtns['seek_bar'].width
                            video_scrub_progress = max(0, min(1, (event.pos[0] - sx) / sw_))
                        elif vbtns.get('tap_zone') and vbtns['tap_zone'].collidepoint(event.pos):
                            # نمایش/مخفی کنترلها
                            video_controls_visible = True
                            video_controls_hide_timer = time.time()
                            video_ui_fade_target = 1.0
                    elif event.type == pygame.MOUSEMOTION and is_scrubbing_video:
                        temp_s = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT))
                        vbtns = draw_video_player(temp_s)
                        if vbtns.get('seek_bar'):
                            sx = vbtns['seek_bar'].x
                            sw_ = vbtns['seek_bar'].width
                            video_scrub_progress = max(0, min(1, (event.pos[0] - sx) / sw_))
                    elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
                        if is_scrubbing_video:
                            is_scrubbing_video = False
                            if video_capture and video_duration > 0:
                                target_frame = int(video_scrub_progress * video_total_frames)
                                video_capture.set(cv2.CAP_PROP_POS_FRAMES, target_frame)
                                video_current_frame = target_frame
                                video_current_time = video_scrub_progress * video_duration
                        else:
                            # کلیک روی play/pause
                            temp_s = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT))
                            vbtns = draw_video_player(temp_s)
                            if vbtns.get('play_btn') and vbtns['play_btn'].collidepoint(event.pos):
                                video_paused = not video_paused
                                if not video_paused:
                                    video_controls_hide_timer = time.time()

                elif is_gallery_fullscreen:
                    # رویدادهای حالت تمام صفحه تصویر
                    if event.type == pygame.MOUSEBUTTONUP and event.button == 1:
                        temp_surface = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT))
                        fs_buttons = draw_gallery_fullscreen_view(temp_surface)
                        
                        if fs_buttons:
                            if fs_buttons['back_btn'].collidepoint(event.pos):
                                gallery_animation_direction = -1
                                cols, padding = 3, 2
                                thumb_size = (SCREEN_WIDTH - (cols - 1) * padding) / cols
                                row, col = divmod(gallery_selected_index, cols)
                                start_y = 100
                                x = col * (thumb_size + padding)
                                y = start_y + row * (thumb_size + padding) - gallery_scroll_offset
                                gallery_start_rect = pygame.Rect(x, y, thumb_size, thumb_size)
                            
                            elif fs_buttons['next_zone'].collidepoint(event.pos):
                                gallery_selected_index = (gallery_selected_index + 1) % len(gallery_photos)
                            
                            elif fs_buttons['prev_zone'].collidepoint(event.pos):
                                gallery_selected_index = (gallery_selected_index - 1 + len(gallery_photos)) % len(gallery_photos)
                            
                            elif fs_buttons['info_btn'].collidepoint(event.pos):
                                is_gallery_info_visible = not is_gallery_info_visible
                            
                            elif fs_buttons.get('edit_btn') and fs_buttons['edit_btn'].collidepoint(event.pos):
                                # باز کردن ویرایشگر
                                photo_data = gallery_photos[gallery_selected_index]
                                # اگر تصویر هنوز لود نشده، اینجا لودش کن
                                if photo_data['image'] is None:
                                    try:
                                        _img = pygame.image.load(photo_data['path']).convert()
                                        _iw, _ih = _img.get_size()
                                        _sf = min(1.0, 1500 / max(_iw, _ih))
                                        if _sf < 1.0:
                                            _img = pygame.transform.smoothscale(_img, (int(_iw*_sf), int(_ih*_sf)))
                                        photo_data['image'] = _img
                                    except Exception as _e:
                                        add_unimportant_notification(f"خطا در بارگذاری تصویر")
                                if photo_data['image'] is not None:
                                    try:
                                        gallery_editor_open(photo_data['image'])
                                    except Exception as _e:
                                        add_unimportant_notification("خطا در ویرایشگر")
                                else:
                                    add_unimportant_notification("تصویر قابل ویرایش نیست")

                            elif fs_buttons['delete_btn'].collidepoint(event.pos):
                                try:
                                    photo_to_delete = gallery_photos[gallery_selected_index]
                                    os.remove(photo_to_delete['path'])
                                    del gallery_photos[gallery_selected_index]
                                    add_unimportant_notification("تصویر حذف شد")
                                    if not gallery_photos:
                                        is_gallery_fullscreen = False
                                    else:
                                        gallery_selected_index = gallery_selected_index % len(gallery_photos)
                                        load_gallery_photos()
                                except Exception as e:
                                    add_unimportant_notification("خطا در حذف تصویر")
                                    print(e)

                            elif is_gallery_info_visible:
                                is_gallery_info_visible = False

                else:
                    # --- نمای گرید ---
                    if event.type == pygame.MOUSEWHEEL:
                        all_media_count = len(gallery_photos) + len(gallery_videos)
                        cols, padding = 3, 2
                        thumb_size = (SCREEN_WIDTH - (cols - 1) * padding) / 3
                        max_scroll = max(0, gallery_content_height - SCREEN_HEIGHT)
                        target_gallery_scroll_offset -= event.y * 40
                        target_gallery_scroll_offset = max(0, min(target_gallery_scroll_offset, max_scroll))
                    
                    if event.type == pygame.MOUSEBUTTONUP and event.button == 1:
                        temp_surface_for_buttons = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
                        buttons = draw_gallery_app_screen(temp_surface_for_buttons)
                        
                        for key, rect in buttons.items():
                            if key.startswith('media_') and rect.collidepoint(event.pos):
                                idx = int(key.split('_')[1])
                                # تشخیص عکس یا ویدیو
                                all_media = list(gallery_photos) + list(gallery_videos)
                                if idx < len(all_media):
                                    media_item = all_media[idx]
                                    if media_item.get('type') == 'video':
                                        open_video(media_item['path'])
                                    else:
                                        # ایندکس فقط در photos
                                        photo_idx = idx  # gallery_photos اول است
                                        if photo_idx < len(gallery_photos):
                                            gallery_selected_index = photo_idx
                                            is_gallery_fullscreen = True
                                            gallery_animation_direction = 1
                                            gallery_start_rect = rect
                                            is_gallery_info_visible = False
                                break
                            # پشتیبانی قدیمی از کلید photo_
                            elif key.startswith('photo_') and rect.collidepoint(event.pos):
                                gallery_selected_index = int(key.split('_')[1])
                                is_gallery_fullscreen = True
                                gallery_animation_direction = 1
                                gallery_start_rect = rect
                                is_gallery_info_visible = False
                                break
                            
            if app_name in ['notes', 'browser'] and event.type == pygame.KEYDOWN:
                target_text, is_active = "", False

                if app_page == 'notes_main':
                    target_text, is_active = notes_text, True
                elif app_page == 'notes_save':
                    target_text, is_active = notes_save_filename, True
                elif app_name == 'browser' and is_typing_url:
                    target_text, is_active = input_url_text, True

                if is_active:
                    if app_page == 'notes_main':
                        # --- سیستم cursor پیشرفته برای یادداشت‌ها ---
                        notes_cursor_index = max(0, min(notes_cursor_index, len(notes_text)))
                        ci = notes_cursor_index

                        if event.key == pygame.K_BACKSPACE:
                            if ci > 0:
                                notes_text = notes_text[:ci-1] + notes_text[ci:]
                                notes_cursor_index = ci - 1
                        elif event.key == pygame.K_DELETE:
                            if ci < len(notes_text):
                                notes_text = notes_text[:ci] + notes_text[ci+1:]
                        elif event.key == pygame.K_LEFT:
                            notes_cursor_index = max(0, ci - 1)
                        elif event.key == pygame.K_RIGHT:
                            notes_cursor_index = min(len(notes_text), ci + 1)
                        elif event.key == pygame.K_UP:
                            # جابجایی به خط بالا
                            line_start = notes_text.rfind('\n', 0, ci)
                            col = ci - (line_start + 1)
                            prev_line_end = line_start
                            prev_line_start = notes_text.rfind('\n', 0, prev_line_end) + 1
                            new_ci = prev_line_start + min(col, prev_line_end - prev_line_start)
                            notes_cursor_index = max(0, new_ci)
                        elif event.key == pygame.K_DOWN:
                            # جابجایی به خط پایین
                            line_start = notes_text.rfind('\n', 0, ci) + 1
                            col = ci - line_start
                            next_line_start = notes_text.find('\n', ci)
                            if next_line_start != -1:
                                next_line_start += 1
                                next_line_end = notes_text.find('\n', next_line_start)
                                if next_line_end == -1: next_line_end = len(notes_text)
                                notes_cursor_index = next_line_start + min(col, next_line_end - next_line_start)
                        elif event.key == pygame.K_HOME:
                            line_start = notes_text.rfind('\n', 0, ci) + 1
                            notes_cursor_index = line_start
                        elif event.key == pygame.K_END:
                            line_end = notes_text.find('\n', ci)
                            notes_cursor_index = line_end if line_end != -1 else len(notes_text)
                        elif event.key == pygame.K_RETURN:
                            notes_text = notes_text[:ci] + '\n' + notes_text[ci:]
                            notes_cursor_index = ci + 1
                        elif event.unicode and event.key != pygame.K_RETURN:
                            notes_text = notes_text[:ci] + event.unicode + notes_text[ci:]
                            notes_cursor_index = ci + len(event.unicode)

                        # شروع تکرار کلید (hold)
                        notes_key_repeat_key = event.key
                        notes_key_repeat_timer = time.time() + notes_key_repeat_delay
                        notes_last_type_time = time.time()
                    else:
                        # رفتار ساده برای notes_save و browser
                        if event.key == pygame.K_BACKSPACE:
                            target_text = target_text[:-1]
                        elif event.key == pygame.K_RETURN:
                            if app_name == 'browser':
                                if browser_manager is not None and browser_manager.get_active_tab():
                                    browser_manager.get_active_tab().load_url(target_text)
                                is_typing_url = False
                        elif event.key != pygame.K_RETURN:
                            target_text += event.unicode
                        if app_page == 'notes_save': notes_save_filename = target_text
                        elif app_name == 'browser': input_url_text = target_text

            # --- تکرار کلید هنگام نگه داشتن (hold-to-repeat) ---
            if app_name == 'notes' and app_page == 'notes_main' and notes_key_repeat_key is not None:
                keys_pressed = pygame.key.get_pressed()
                key_still_held = False
                # بررسی کلیدهای مهم
                for k in [pygame.K_BACKSPACE, pygame.K_DELETE, pygame.K_LEFT, pygame.K_RIGHT, pygame.K_UP, pygame.K_DOWN]:
                    if k == notes_key_repeat_key and keys_pressed[k]:
                        key_still_held = True
                        break
                if not key_still_held:
                    notes_key_repeat_key = None
                elif time.time() >= notes_key_repeat_timer:
                    notes_key_repeat_timer = time.time() + notes_key_repeat_rate
                    notes_cursor_index = max(0, min(notes_cursor_index, len(notes_text)))
                    ci = notes_cursor_index
                    if notes_key_repeat_key == pygame.K_BACKSPACE and ci > 0:
                        notes_text = notes_text[:ci-1] + notes_text[ci:]
                        notes_cursor_index = ci - 1
                        notes_last_type_time = time.time()
                    elif notes_key_repeat_key == pygame.K_DELETE and ci < len(notes_text):
                        notes_text = notes_text[:ci] + notes_text[ci+1:]
                        notes_last_type_time = time.time()
                    elif notes_key_repeat_key == pygame.K_LEFT:
                        notes_cursor_index = max(0, ci - 1)
                    elif notes_key_repeat_key == pygame.K_RIGHT:
                        notes_cursor_index = min(len(notes_text), ci + 1)
                    elif notes_key_repeat_key == pygame.K_UP:
                        line_start = notes_text.rfind('\n', 0, ci)
                        col = ci - (line_start + 1)
                        prev_line_end = line_start
                        prev_line_start = notes_text.rfind('\n', 0, prev_line_end) + 1
                        notes_cursor_index = max(0, prev_line_start + min(col, prev_line_end - prev_line_start))
                    elif notes_key_repeat_key == pygame.K_DOWN:
                        line_start = notes_text.rfind('\n', 0, ci) + 1
                        col = ci - line_start
                        next_line_start = notes_text.find('\n', ci)
                        if next_line_start != -1:
                            next_line_start += 1
                            next_line_end = notes_text.find('\n', next_line_start)
                            if next_line_end == -1: next_line_end = len(notes_text)
                            notes_cursor_index = next_line_start + min(col, next_line_end - next_line_start)

            if event.type == pygame.KEYUP:
                if event.key == notes_key_repeat_key:
                    notes_key_repeat_key = None

            if event.type == pygame.MOUSEWHEEL and app_name == 'settings' and app_page in ['custom_wallpaper', 'custom_lock_wallpaper']:
                target_custom_wp_scroll_offset -= event.y * 40
                try:
                    # محاسبه هوشمند بر اساس تعداد فایل‌های واقعی پوشه
                    num_files = len([f for f in os.listdir('wallpapers') if f.lower().endswith(('.png', '.jpg', '.jpeg', '.bmp'))])
                    thumb_h = int(((SCREEN_WIDTH - 45) // 2) * (SCREEN_HEIGHT / SCREEN_WIDTH))
                    max_scroll = max(0, math.ceil(num_files / 2) * (thumb_h + 15) - SCREEN_HEIGHT + 150)
                except FileNotFoundError:
                    max_scroll = 0
                target_custom_wp_scroll_offset = max(0, min(target_custom_wp_scroll_offset, max_scroll))
                
            if event.type == pygame.MOUSEWHEEL and app_name in ['browser', 'files', 'notes']:
                if app_name == 'browser':
                    if browser_manager is not None and browser_manager.get_active_tab():
                        scroll_amount = -event.y * 50
                        browser_manager.get_active_tab().scroll(scroll_amount)
                elif app_name == 'notes' and app_page == 'notes_main':
                    total_h = sum(s.get_height() for s in text_surfaces_cache) if text_surfaces_cache else 0
                    max_s = max(0, total_h - (SCREEN_HEIGHT - 96 - 44))
                    target_scroll_offset = max(0.0, min(float(max_s), target_scroll_offset - event.y * 35))
                elif app_name == 'files':
                    target_files_scroll_offset -= event.y * 30
                    max_scroll = max(0, files_content_height - (SCREEN_HEIGHT - 100))
                    target_files_scroll_offset = max(0, min(target_files_scroll_offset, max_scroll))

            if event.type == pygame.MOUSEBUTTONDOWN:
                if app_name == 'notes' and app_page == 'notes_main' and event.button == 3:
                    is_notes_context_menu_open, notes_context_menu_pos = True, event.pos
                elif event.button == 1:
                    if is_notes_context_menu_open:
                        temp_surf = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA); menu_buttons = draw_notes_context_menu(temp_surf)
                        clicked_on_menu = False
                        for key, rect in menu_buttons.items():
                            if rect.collidepoint(event.pos):
                                if key == 'copy': clipboard_text = notes_text
                                elif key == 'paste': notes_text += clipboard_text
                                clicked_on_menu = True; break
                        is_notes_context_menu_open = False
                        if clicked_on_menu: continue
                    # --- بررسی کلیک‌های SuperIsland ---
                    if is_superisland_enabled and superisland_state != 'hidden':
                        temp_si_surf = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT))
                        si_buttons = draw_superisland(temp_si_surf)
                        
                        # اگر منو باز است و روی دکمه‌های کنترل کلیک شده
                        if superisland_state == 'expanded':
                            if si_buttons.get('si_play') and si_buttons['si_play'].collidepoint(event.pos):
                                toggle_music_play_pause()
                                continue
                            elif si_buttons.get('si_next') and si_buttons['si_next'].collidepoint(event.pos):
                                play_next_song()
                                continue
                            elif si_buttons.get('si_prev') and si_buttons['si_prev'].collidepoint(event.pos):
                                play_previous_song()
                                continue
                            elif not si_buttons.get('si_main').collidepoint(event.pos):
                                # کلیک بیرون از جزیره آن را می‌بندد
                                superisland_state = 'capsule'
                        
                        # کلیک برای باز کردن جزیره
                        if si_buttons.get('si_main') and si_buttons['si_main'].collidepoint(event.pos):
                            if superisland_state == 'capsule':
                                superisland_state = 'expanded'
                            continue
                    temp_surf = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT)); buttons = {}
                    if app_name == 'settings':
                        if app_page == 'main': buttons = draw_settings_main_screen(temp_surf)
                        elif app_page == 'wallpaper': buttons = draw_settings_wallpaper_screen(temp_surf)
                        elif app_page == 'display': buttons = draw_settings_display_screen(temp_surf)
                        elif app_page == 'lock_screen': buttons = draw_settings_lock_screen_screen(temp_surf)
                        elif app_page == 'custom_wallpaper': buttons = draw_settings_custom_wallpaper_screen(temp_surf)
                        elif app_page == 'custom_lock_wallpaper': buttons = draw_settings_custom_lock_wallpaper_screen(temp_surf)
                        elif app_page == 'language': buttons = draw_settings_language_screen(temp_surf)
                        elif app_page == 'battery': buttons = draw_settings_battery_screen(temp_surf)
                        elif app_page == 'about': buttons = draw_settings_about_screen(temp_surf)
                    elif app_name == 'notes':
                        if app_page == 'notes_main': buttons = notes_app.draw(temp_surf, SCREEN_WIDTH, SCREEN_HEIGHT, app_context)
                        elif app_page == 'notes_save': buttons = notes_app.draw(temp_surf, SCREEN_WIDTH, SCREEN_HEIGHT, app_context)
                        elif app_page == 'notes_open':
                            buttons = notes_app.draw(temp_surf, SCREEN_WIDTH, SCREEN_HEIGHT, app_context)
                            for file_item in notes_file_list:
                                if file_item['rect'].collidepoint(event.pos): active_file_item = file_item; break
                    elif app_name == 'music':
                        buttons = draw_music_app_screen(temp_surf) # فقط برای گرفتن Rectها
                        
                        if buttons['play_pause_btn'].collidepoint(event.pos):
                            music_button_states['play']['pressed'] = True
                            active_button_key = 'play_pause_btn'
                        elif buttons['next_btn'].collidepoint(event.pos):
                            music_button_states['next']['pressed'] = True
                            active_button_key = 'next_btn'
                        elif buttons['prev_btn'].collidepoint(event.pos):
                            music_button_states['prev']['pressed'] = True
                            active_button_key = 'prev_btn'
                        elif buttons.get('shuffle_btn') and buttons['shuffle_btn'].collidepoint(event.pos):
                            music_shuffle = not music_shuffle
                            add_unimportant_notification("پخش تصادفی " + ("فعال" if music_shuffle else "غیرفعال"))
                        elif buttons.get('repeat_btn') and buttons['repeat_btn'].collidepoint(event.pos):
                            music_repeat = (music_repeat + 1) % 3
                            labels = ["بدون تکرار", "تکرار پلیلیست", "تکرار یک آهنگ"]
                            add_unimportant_notification(labels[music_repeat])
                        elif buttons['seek_bar'].collidepoint(event.pos):
                            is_scrubbing_music = True
                            seek_rect = pygame.Rect(50, 500, SCREEN_WIDTH - 100, 4)
                            click_x = event.pos[0] - ((SCREEN_WIDTH - (SCREEN_WIDTH - 60))/2)
                            music_scrub_progress = max(0, min(1, click_x / (SCREEN_WIDTH - 60)))
                    elif app_name == 'browser':
                        buttons = draw_browser_app_screen(temp_surf)
                        is_url_input_active = buttons['url_bar'].collidepoint(event.pos)
                    elif app_name == 'files':
                        buttons = draw_files_app_screen(temp_surf)

                    active_button_rect, active_button_key = None, None
                    for key, value in buttons.items():
                        if key == 'links': continue
                        if isinstance(value, pygame.Rect) and value.collidepoint(event.pos):
                            active_button_rect, active_button_key = value, key
                            break
                    if not active_button_key and app_name == 'browser' and buttons.get('links'):
                        for rect_tuple, href in buttons['links'].items():
                            rect = pygame.Rect(rect_tuple)
                            if rect.collidepoint(event.pos):
                                is_downloadable = any(href.lower().endswith(ext) for ext in DOWNLOADABLE_EXTENSIONS)
                                if is_downloadable:
                                    download_thread = threading.Thread(target=download_file, args=(href,))
                                    download_thread.start()
                                    active_button_key, active_button_rect = None, None
                                else:
                                    active_button_key = 'link_clicked'
                                    browser_url_input = href
                                break

            elif event.type == pygame.MOUSEMOTION and is_scrubbing_music:
                seek_bar_rect = pygame.Rect(50, 440, SCREEN_WIDTH - 100, 8); click_x = event.pos[0] - seek_bar_rect.x
                music_scrub_progress = max(0, min(1, click_x / seek_bar_rect.width))

            elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
                if is_notes_context_menu_open: is_notes_context_menu_open = False
                if is_scrubbing_music:
                    is_scrubbing_music = False
                    if current_track_length > 0:
                        target_seconds = music_scrub_progress * current_track_length
                        pygame.mixer.music.play(start=target_seconds); music_playback_start_time_offset = target_seconds
                        if not is_music_playing: pygame.mixer.music.pause()

                if app_name == 'browser':
                    # گرفتن دکمه‌ها از تابع رسم
                    temp_surf = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT))
                    buttons = draw_browser_app_screen(temp_surf)

                    content_y = 100  # ارتفاع هدر + نوار تب‌ها

                    # کلیک روی محتوا - فقط اگر مرورگر آماده باشد
                    if event.pos[1] > content_y:
                        if browser_manager is not None:
                            active_tab = browser_manager.get_active_tab()
                            if active_tab is not None and getattr(active_tab, 'driver', None) is not None:
                                rel_x = event.pos[0]
                                rel_y = event.pos[1] - content_y
                                threading.Thread(
                                    target=active_tab.click_at,
                                    args=(rel_x, rel_y),
                                    daemon=True
                                ).start()

                    # نوار آدرس
                    if buttons.get('url_bar') and buttons['url_bar'].collidepoint(event.pos):
                        is_typing_url = True
                        if browser_manager is not None:
                            at = browser_manager.get_active_tab()
                            if at is not None:
                                input_url_text = at.url
                    else:
                        is_typing_url = False

                    # دکمه Go
                    if buttons.get('go_btn') and buttons['go_btn'].collidepoint(event.pos):
                        search_via_api(input_url_text)

                    # تب جدید
                    if buttons.get('new_tab') and buttons['new_tab'].collidepoint(event.pos):
                        if browser_manager is not None:
                            browser_manager.new_tab()

                    # انتخاب تب‌ها
                    if browser_manager is not None:
                        for key, rect in buttons.items():
                            if key.startswith('tab_') and isinstance(rect, pygame.Rect) and rect.collidepoint(event.pos):
                                browser_manager.active_tab_index = int(key.split('_')[1])
                                break

                if active_button_key and active_button_rect and active_button_rect.collidepoint(event.pos):
                    if app_name == 'files':
                        if event.type == pygame.MOUSEWHEEL:
                            files_scroll_velocity -= event.y * 12
                            files_is_user_scrolling = True
                            files_last_scroll_time = time.time()
                        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                            files_touch_start_y = event.pos[1]
                            files_touch_start_offset = target_files_scroll_offset
                            files_is_user_scrolling = True
                        elif event.type == pygame.MOUSEMOTION and pygame.mouse.get_pressed()[0]:
                            if 'files_touch_start_y' in locals():
                                dy = files_touch_start_y - event.pos[1]
                                max_scroll = max(0, files_content_height - (SCREEN_HEIGHT - 100))
                                # مقاومت overscroll
                                if target_files_scroll_offset <= 0 and dy < 0:
                                    dy *= files_overscroll_resistance
                                elif target_files_scroll_offset >= max_scroll and dy > 0:
                                    dy *= files_overscroll_resistance
                                target_files_scroll_offset = files_touch_start_offset + dy
                                files_scroll_velocity = 0
                        elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
                            if 'files_touch_start_y' in locals() and 'files_last_move_time' in locals():
                                dt = time.time() - files_last_move_time
                                if dt < 0.1:
                                    dy = files_touch_start_y - event.pos[1]
                                    files_scroll_velocity = (dy / dt) * 0.5
                                else:
                                    files_scroll_velocity = 0
                                files_is_user_scrolling = False
                            else:
                                files_is_user_scrolling = False
                        elif event.type == pygame.MOUSEMOTION and 'files_touch_start_y' in locals():
                            files_last_move_time = time.time()

                        if active_button_key == 'back_btn' and files_current_path != '.':
                            files_current_path = os.path.dirname(files_current_path)
                            files_list = scan_directory(files_current_path)
                            target_files_scroll_offset = 0.0
                            files_scroll_offset = 0.0
                            files_scroll_velocity = 0.0
                            files_is_user_scrolling = False

                        elif active_button_key.startswith('item_'):
                            item_index = int(active_button_key.split('_')[1])
                            clicked_item = files_list[item_index]
                            
                            if clicked_item['type'] == 'dir':
                                files_current_path = clicked_item['path']
                                files_list = scan_directory(files_current_path)
                                target_files_scroll_offset = 0.0
                                files_scroll_offset = 0.0
                                files_scroll_velocity = 0.0
                                files_is_user_scrolling = False
                            # ---------- رفع باگ اجرای فایل‌ها ----------
                            elif clicked_item['type'] == 'app_package':
                                install_prs_app(clicked_item['path'])
                            elif clicked_item['type'] == 'music':
                                if clicked_item['path'] not in music_playlist:
                                    music_playlist.append(clicked_item['path'])
                                current_track_index = music_playlist.index(clicked_item['path'])
                                pygame.mixer.music.load(clicked_item['path'])
                                pygame.mixer.music.play()
                                
                                is_music_playing = True
                                is_music_paused = False
                                current_track_length, current_album_art_surface = get_track_info(clicked_item['path'])
                                music_track_name = os.path.basename(clicked_item['path'])
                                add_unimportant_notification(f"در حال پخش: {clicked_item['name']}")
                            elif clicked_item['type'] == 'video':
                                open_video(clicked_item['path'])
                            elif clicked_item['type'] == 'image':
                                # چون برنامه مستقلی برای نمایش تکی فایل عکس خارج از گالری ندارید، فعلاً یک اعلان نمایش می‌دهیم
                                add_unimportant_notification(f"تصویر: {clicked_item['name']}")
                            else:
                                add_unimportant_notification(f"فرمت {clicked_item['name']} پشتیبانی نمی‌شود")
                            
                    if app_name == 'settings':
                        if app_page == 'main':
                            if active_button_key == 'wallpaper_btn': app_screen_animation_direction = 1; app_context.update({'old_screen_draw_func': draw_settings_main_screen, 'animation_callback': lambda: app_context.update({'screen': 'wallpaper'})})
                            elif active_button_key == 'display_btn': app_screen_animation_direction = 1; app_context.update({'old_screen_draw_func': draw_settings_main_screen, 'animation_callback': lambda: app_context.update({'screen': 'display'})})
                            elif active_button_key == 'lock_screen_btn': app_screen_animation_direction = 1; app_context.update({'old_screen_draw_func': draw_settings_main_screen, 'animation_callback': lambda: app_context.update({'screen': 'lock_screen'})})
                            elif active_button_key == 'battery_btn': app_screen_animation_direction = 1; app_context.update({'old_screen_draw_func': draw_settings_main_screen, 'animation_callback': lambda: app_context.update({'screen': 'battery'})})
                            elif active_button_key == 'about_btn': app_screen_animation_direction = 1; app_context.update({'old_screen_draw_func': draw_settings_main_screen, 'animation_callback': lambda: app_context.update({'screen': 'about'})})
                            elif active_button_key == 'lang_btn': 
                                app_screen_animation_direction = 1
                                app_context.update({'old_screen_draw_func': draw_settings_main_screen, 'animation_callback': lambda: app_context.update({'screen': 'language'})})
                            elif active_button_key == 'about_btn': 
                                app_screen_animation_direction = 1
                                app_context.update({'old_screen_draw_func': draw_settings_main_screen, 'animation_callback': lambda: app_context.update({'screen': 'about'})})
                        elif app_page == 'language':
                            if active_button_key == 'back_btn':
                                app_screen_animation_direction = -1
                                app_context.update({'old_screen_draw_func': draw_settings_language_screen, 'animation_callback': lambda: app_context.update({'screen': 'main'})})
                            elif active_button_key == 'select_lang_btn':
                                # (جدید) باز کردن مودال انتخاب زبان
                                is_language_picker_open = True
                                # (جدید) ذخیره Rect دکمه برای انیمیشن
                                temp_surf = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT))
                                buttons = draw_settings_language_screen(temp_surf)
                                language_picker_start_rect = buttons['select_lang_btn'].copy()

                                snapshot = screen.copy()
                                language_picker_blurred_bg = apply_gaussian_blur(snapshot)
                        elif app_page in ['wallpaper', 'display', 'lock_screen', 'custom_wallpaper', 'custom_lock_wallpaper', 'about', 'battery']:
                        # (اصلاح شده) منطق بازگشت برای پشتیبانی از صفحه زبان
                            old_func_name_map = {
                                'wallpaper': draw_settings_wallpaper_screen,
                                'display': draw_settings_display_screen,
                                'lock_screen': draw_settings_lock_screen_screen,
                                'custom_wallpaper': draw_settings_custom_wallpaper_screen,
                                'custom_lock_wallpaper': draw_settings_custom_lock_wallpaper_screen,
                                'about': draw_settings_about_screen,
                                'battery': draw_settings_battery_screen,
                            }
                            
                            # (توجه: صفحه 'language' در بالا مدیریت شد)
                            old_func = old_func_name_map.get(app_page, draw_settings_main_screen)

                            

                            target_screen = 'main'
                            if app_page == 'custom_wallpaper': target_screen = 'wallpaper'
                            if app_page == 'custom_lock_wallpaper': target_screen = 'lock_screen'

                            if active_button_key == 'back_btn': 
                                app_screen_animation_direction = -1
                                # (اصلاح شده) استفاده از lambda برای تعیین صفحه مقصد
                                app_context.update({'old_screen_draw_func': old_func, 'animation_callback': (lambda s=target_screen: lambda: app_context.update({'screen': s}))() })
                            if app_page == 'wallpaper':
                                if active_button_key.startswith('preset_'):
                                    i = int(active_button_key.split('_')[1]); saved_light_wallpaper_top, saved_light_wallpaper_bottom = wallpaper_presets[i]
                                    current_wallpaper_image, wallpaper_path = None, None; save_settings()
                                elif active_button_key == 'custom_wallpaper_btn':
                                    app_screen_animation_direction = 1; app_context.update({'old_screen_draw_func': draw_settings_wallpaper_screen, 'animation_callback': lambda: app_context.update({'screen': 'custom_wallpaper'})})
                            elif app_page == 'custom_wallpaper' and active_button_key.startswith('file_'):
                                filename = active_button_key.split('file_')[1]; path = os.path.join('wallpapers', filename)
                                if os.path.exists(path):
                                    try:
                                        loaded_image = pygame.image.load(path).convert(); current_wallpaper_image = pygame.transform.smoothscale(loaded_image, (SCREEN_WIDTH, SCREEN_HEIGHT))
                                        wallpaper_path = path; save_settings()
                                        app_screen_animation_direction = -1; app_context.update({'old_screen_draw_func': draw_settings_custom_wallpaper_screen, 'animation_callback': lambda: app_context.update({'screen': 'wallpaper'})})
                                    except pygame.error as e: print(f"Error setting new wallpaper: {e}")
                            elif app_page == 'custom_lock_wallpaper' and active_button_key.startswith('file_'):
                                filename = active_button_key.split('file_')[1]; path = os.path.join('wallpapers', filename)
                                if os.path.exists(path):
                                    try:
                                        loaded_image = pygame.image.load(path).convert(); current_lock_screen_wallpaper_image = pygame.transform.smoothscale(loaded_image, (SCREEN_WIDTH, SCREEN_HEIGHT)); lock_screen_wallpaper_path = path
                                        if is_depth_effect_enabled: process_depth_effect_image(current_lock_screen_wallpaper_image)
                                        save_settings(); app_screen_animation_direction = -1
                                        app_context.update({'old_screen_draw_func': draw_settings_custom_lock_wallpaper_screen, 'animation_callback': lambda: app_context.update({'screen': 'lock_screen'})})
                                    except pygame.error as e: print(f"Error setting new lock wallpaper: {e}")
                            elif app_page == 'display' and active_button_key == 'dark_mode_toggle':
                                is_dark_mode = not is_dark_mode; is_theme_animating = True; theme_animation_direction = 1 if is_dark_mode else -1; save_settings()
                            elif app_page == 'display' and active_button_key == 'superisland_toggle':
                                is_superisland_enabled = not is_superisland_enabled
                                save_settings()
                            elif app_page == 'lock_screen':
                                if active_button_key.startswith('style_'): lock_screen_style = active_button_key.split('_')[1]; save_settings()
                                elif active_button_key == 'custom_lock_wallpaper_btn': app_screen_animation_direction = 1; app_context.update({'old_screen_draw_func': draw_settings_lock_screen_screen, 'animation_callback': lambda: app_context.update({'screen': 'custom_lock_wallpaper'})})
                                elif active_button_key == 'default_lock_wallpaper_btn':
                                    current_lock_screen_wallpaper_image, lock_screen_wallpaper_path, current_lock_screen_subject_image, is_depth_effect_enabled = None, None, None, False; save_settings()
                                elif active_button_key == 'depth_effect_toggle':
                                    is_depth_effect_enabled = not is_depth_effect_enabled
                                    if is_depth_effect_enabled: process_depth_effect_image(current_lock_screen_wallpaper_image)
                                    save_settings()
                            elif app_page == 'about' and active_button_key == 'logo_btn':
                                current_time = time.time()
                                # بررسی اینکه آیا کلیک‌ها سریع و پشت سر هم بوده‌اند
                                if current_time - last_about_logo_click_time < 0.5:
                                    about_logo_click_count += 1
                                else:
                                    about_logo_click_count = 1
                                last_about_logo_click_time = current_time
                                
                                # فعال‌سازی با ۵ کلیک پشت سر هم
                                if about_logo_click_count >= 5 and not is_developer_mode:
                                    is_developer_mode = True
                                    add_unimportant_notification("حالت توسعه دهنده فعال شد")
                                    # راه‌اندازی ترمینال در پس‌زمینه
                                    threading.Thread(target=developer_terminal_thread, daemon=True).start()
                    elif app_name == 'notes':
                        if app_page == 'notes_main':
                            if active_button_key == 'save_btn': app_screen_animation_direction = 1; app_context.update({'old_screen_draw_func': notes_app.draw(temp_surf, SCREEN_WIDTH, SCREEN_HEIGHT, app_context), 'animation_callback': lambda: app_context.update({'screen': 'notes_save'})})
                            elif active_button_key == 'open_btn': app_screen_animation_direction = 1; app_context.update({'old_screen_draw_func': notes_app.draw(temp_surf, SCREEN_WIDTH, SCREEN_HEIGHT, app_context), 'animation_callback': lambda: app_context.update({'screen': 'notes_open'})})
                        elif app_page == 'notes_save':
                            if active_button_key == 'back_btn': app_screen_animation_direction = -1; app_context.update({'old_screen_draw_func': notes_app.draw(temp_surf, SCREEN_WIDTH, SCREEN_HEIGHT, app_context), 'animation_callback': lambda: app_context.update({'screen': 'notes_main'})})
                            elif active_button_key == 'confirm_btn':
                                try:
                                    with open(os.path.join('notes', notes_save_filename), 'w', encoding='utf-8') as f: f.write(notes_text)
                                    app_screen_animation_direction = -1; app_context.update({'old_screen_draw_func': notes_app.draw(temp_surf, SCREEN_WIDTH, SCREEN_HEIGHT, app_context), 'animation_callback': lambda: app_context.update({'screen': 'notes_main'})})
                                except IOError as e: print(f"Error saving file: {e}")
                        elif app_page == 'notes_open':
                            if active_button_key == 'back_btn': app_screen_animation_direction = -1; app_context.update({'old_screen_draw_func': notes_app.draw(temp_surf, SCREEN_WIDTH, SCREEN_HEIGHT, app_context), 'animation_callback': lambda: app_context.update({'screen': 'notes_main'})})
                            elif active_file_item:
                                try:
                                    with open(os.path.join('notes', active_file_item['name']), 'r', encoding='utf-8') as f: notes_text = f.read()
                                    app_screen_animation_direction = -1; app_context.update({'old_screen_draw_func': notes_app.draw(temp_surf, SCREEN_WIDTH, SCREEN_HEIGHT, app_context), 'animation_callback': lambda: app_context.update({'screen': 'notes_main'})})
                                except IOError as e: print(f"Error opening file: {e}")
                    elif app_name == 'music':
                        for key in music_button_states: music_button_states[key]['pressed'] = False
                    
                        if active_button_key == 'play_pause_btn':
                             if music_playlist:
                                    if is_music_playing: pygame.mixer.music.pause(); is_music_paused, is_music_playing = True, False
                                    elif is_music_paused: pygame.mixer.music.unpause(); is_music_paused, is_music_playing = False, True
                                    else: pygame.mixer.music.play(); music_playback_start_time_offset = 0; is_music_playing, is_music_paused = True, False
                        elif active_button_key == 'next_btn': play_next_song()
                        elif active_button_key == 'prev_btn': play_previous_song()
                        
                        if is_scrubbing_music:
                            is_scrubbing_music = False
                            if current_track_length > 0:
                                target_seconds = music_scrub_progress * current_track_length
                                try:
                                    pygame.mixer.music.play(start=target_seconds)
                                    music_playback_start_time_offset = target_seconds
                                    if not is_music_playing: pygame.mixer.music.pause()
                                except: pass
                active_button_rect, active_button_key, active_file_item = None, None, None

            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1 and event.pos[1] > SCREEN_HEIGHT - 40:
                 is_swiping_app_close, app_swipe_start_pos = True, event.pos
                 app_swipe_interactive_progress = 0.0

    # --------------------------
    #      منطق و بهروزرسانی وضعیت
    # --------------------------

    if is_language_picker_open and language_picker_progress < 1.0:
        language_picker_progress = min(1.0, language_picker_progress + 0.08)
    elif not is_language_picker_open and language_picker_progress > 0.0:
        language_picker_progress = max(0.0, language_picker_progress - 0.08)
        if language_picker_progress <= 0.0:
            language_picker_blurred_bg = None
            language_picker_start_rect = None # (جدید)
        
    if current_screen == "app_open" and app_context.get('is_external_app'):
        app_instance = running_app_instances.get(app_context['app_id'])
        if app_instance:
            app_instance.update()

    if browser_is_loading and 'browser_thread_key' in app_context:
        result_key = app_context['browser_thread_key']
        if result_key in thread_results:
            result = thread_results.pop(result_key)
            if result['status'] == 'success':
                html = result['html']
                final_url = result['final_url']
                soup = BeautifulSoup(html, 'html.parser')
                title_tag = soup.find('title')
                page_title = title_tag.string.strip() if title_tag else final_url
                from urllib.parse import urljoin
                for img in soup.find_all('img'):
                    if img.get('src'): img['src'] = urljoin(final_url, img['src'])
                for a in soup.find_all('a'):
                    if a.get('href'): a['href'] = urljoin(final_url, a['href'])
                html_content = str(soup.body) if soup.body else html
                browser_content_surfaces, browser_content_height = parse_html_to_surfaces(html_content, SCREEN_WIDTH - 40)
                browser_page_title = page_title
            else:
                html_content = f"<h3>خطا در دریافت آدرس</h3><p>{result['message']}</p>"
                browser_content_surfaces, browser_content_height = parse_html_to_surfaces(html_content, SCREEN_WIDTH - 40)
                browser_page_title = "خطا"

            browser_scroll_offset, target_browser_scroll_offset, is_url_input_active = 0.0, 0.0, False
            browser_is_loading = False
            del app_context['browser_thread_key']

    if active_heads_up_notification:
        notif = active_heads_up_notification
        elapsed_time = time.time() - notif['anim_start_time']
        progress = min(1.0, elapsed_time / notif['anim_duration'])
        ease_progress = 1 - pow(1 - progress, 3)
        if notif['state'] == 'entering':
            start_y, end_y = -80, 10; start_alpha, end_alpha = 0, 255
            notif['y_offset'] = start_y + (end_y - start_y) * ease_progress; notif['alpha'] = start_alpha + (end_alpha - start_alpha) * ease_progress
            if progress >= 1.0:
                notif['state'] = 'visible'; notif['timestamp'] = time.time()
        elif notif['state'] == 'visible':
            if time.time() - notif['timestamp'] > 4:
                notif['state'] = 'exiting'; notif['anim_start_time'] = time.time()
        elif notif['state'] == 'exiting':
            start_y, end_y = 10, -80; start_alpha, end_alpha = 255, 0
            notif['y_offset'] = start_y + (end_y - start_y) * ease_progress; notif['alpha'] = start_alpha + (end_alpha - start_alpha) * ease_progress
            if progress >= 1.0:
                active_heads_up_notification = None

    if is_returning_app_to_open:
        app_swipe_interactive_progress -= 0.08
        if app_swipe_interactive_progress <= 0:
            app_swipe_interactive_progress = 0.0
            is_returning_app_to_open = False

    if time.time() - cursor_timer > 0.5: cursor_visible = not cursor_visible; cursor_timer = time.time()
    battery_info = psutil.sensors_battery()
    if battery_info:
        is_plugged_in = battery_info.power_plugged
        if battery_info.percent < 20 and not is_plugged_in and not low_battery_warning_triggered:
            is_low_battery_warning_visible, low_battery_warning_triggered = True, True
        elif battery_info.percent >= 20 or is_plugged_in:
            low_battery_warning_triggered = False
            if is_plugged_in and is_low_battery_warning_visible: is_low_battery_warning_visible = False
    else: is_plugged_in = False

    if is_low_battery_warning_visible and low_battery_warning_progress < 1.0: low_battery_warning_progress = min(1.0, low_battery_warning_progress + 0.06)
    elif not is_low_battery_warning_visible and low_battery_warning_progress > 0.0: low_battery_warning_progress = max(0.0, low_battery_warning_progress - 0.06)

    # (جدید) بررسی میکنیم آیا نخ بلور کارش تمام شده است
    if blur_thread_result is not None:
        control_center_snapshot = blur_thread_result # نتیجه را اعمال کن
        blur_thread_result = None # نتیجه را پاک کن تا دوباره بررسی نشود

    if is_control_center_open and control_center_progress < 1.0: 
        control_center_progress = min(1.0, control_center_progress + 0.06)
    elif not is_control_center_open and control_center_progress > 0.0:
        control_center_progress = max(0.0, control_center_progress - 0.06)
        if control_center_progress <= 0.0: 
            control_center_snapshot = None
            # (مهم) حالا که پنل بسته شد، اجازه میدهیم بلور بعدی انجام شود
            if is_blur_processing: 
                # (اگر کاربر پنل را قبل از اتمام بلور ببندد، این متغیر ریست نمیشود)
                is_blur_processing = False

    if is_notification_center_open and notification_center_progress < 1.0: notification_center_progress = min(1.0, notification_center_progress + 0.06)
    elif not is_notification_center_open and notification_center_progress > 0.0:
        notification_center_progress = max(0.0, notification_center_progress - 0.06)
        if notification_center_progress <= 0.0: notification_center_snapshot = None

    if not is_dragging_cc_content and cc_vertical_offset != target_cc_vertical_offset:
        cc_vertical_offset += (target_cc_vertical_offset - cc_vertical_offset) * 0.2
        if abs(cc_vertical_offset - target_cc_vertical_offset) < 0.5: cc_vertical_offset = target_cc_vertical_offset

    for app in closing_recent_apps[:]:
        app['anim_progress'] += 0.07
        if app['anim_progress'] >= 1.0: closing_recent_apps.remove(app)

    if pressed_icon:
        pressed_icon_animation_progress += pressed_icon_animation_direction * 0.15; pressed_icon_animation_progress = max(0.0, min(1.0, pressed_icon_animation_progress))
        if pressed_icon_animation_direction == -1 and pressed_icon_animation_progress == 0.0:
            pressed_icon, pressed_icon_animation_direction = None, 0

    # (اصلاح شده) بهروزرسانی انیمیشن دکمههای CC
    for btn_name, btn_data in cc_buttons.items():
        # (جدید) از دکمههایی که وضعیت فعال/غیرفعال ندارند (مانند اسلایدرها) بگذر
        if 'is_active' not in btn_data:
            continue

        if 'scale_progress' in btn_data: # دکمههای بزرگ
            scale_target = 1.0 if btn_data['is_pressed'] else 0.0; btn_data['scale_progress'] += (scale_target - btn_data['scale_progress']) * 0.25
            press_target = 1.0 if btn_data['is_pressed'] else 0.0
            btn_data['press_anim_progress'] += (press_target - btn_data['press_anim_progress']) * 0.3
        
        # (جدید) مقداردهی اولیه color_progress برای دکمههای دایرهای در صورت عدم وجود
        # این کار از KeyError جلوگیری میکند
        if 'color_progress' not in btn_data:
            btn_data['color_progress'] = 1.0 if btn_data['is_active'] else 0.0

        color_target = 1.0 if btn_data['is_active'] else 0.0
        # (خط اصلاح شده) اکنون این خط امن است
        btn_data['color_progress'] += (color_target - btn_data['color_progress']) * 0.2


    is_plugged_in = battery_info.power_plugged if battery_info else False
    if is_plugged_in and not was_plugged_in and not is_charging_animation_active:
        is_charging_animation_active, charging_animation_should_end, charging_animation_start_time, charging_animation_alpha = True, False, time.time(), 0.0
        charging_particles = [create_charging_particle() for _ in range(30)]
    was_plugged_in = is_plugged_in
    if is_charging_animation_active:
        if time.time() - charging_animation_start_time > 12: charging_animation_should_end = True
        if charging_animation_should_end:
            charging_animation_alpha -= 10
            if charging_animation_alpha <= 0: is_charging_animation_active = False
        else: charging_animation_alpha = min(150, charging_animation_alpha + 5)
        if len(charging_particles) < 50 and not charging_animation_should_end: charging_particles.append(create_charging_particle())

    if is_theme_animating:
        theme_animation_progress += 0.04 * theme_animation_direction; theme_animation_progress = max(0.0, min(1.0, theme_animation_progress))
        progress = theme_animation_progress
        if not current_wallpaper_image:
            target_top, target_bottom = (DARK_MODE_BG_TOP, DARK_MODE_BG_BOTTOM) if is_dark_mode else (saved_light_wallpaper_top, saved_light_wallpaper_bottom)
            start_top, start_bottom = (saved_light_wallpaper_top, saved_light_wallpaper_bottom) if theme_animation_direction == 1 else (DARK_MODE_BG_TOP, DARK_MODE_BG_BOTTOM)
            BG_TOP_COLOR = tuple(int(s + (t - s) * progress) for s, t in zip(start_top, target_top))
            BG_BOTTOM_COLOR = tuple(int(s + (t - s) * progress) for s, t in zip(start_bottom, target_bottom))
        if (theme_animation_direction == 1 and theme_animation_progress >= 1.0) or (theme_animation_direction == -1 and theme_animation_progress <= 0.0):
            theme_animation_progress = 1.0 if is_dark_mode else 0.0; is_theme_animating = False

    if is_dark_mode and dark_mode_switch_progress < 1.0: dark_mode_switch_progress = min(1.0, dark_mode_switch_progress + 0.1)
    elif not is_dark_mode and dark_mode_switch_progress > 0.0: dark_mode_switch_progress = max(0.0, dark_mode_switch_progress - 0.1)

    if is_icon_animation_active:
        icon_animation_progress += 0.05;
        if icon_animation_progress >= 1.0: is_icon_animation_active, animating_icon = False, None
    if is_notes_icon_animation_active:
        notes_icon_animation_progress += 0.06;
        if notes_icon_animation_progress >= 1.0: is_notes_icon_animation_active, animating_notes_icon = False, None
    if is_music_icon_animation_active:
        music_icon_animation_progress += 0.05;
        if music_icon_animation_progress >= 1.0: is_music_icon_animation_active, animating_music_icon = False, None
    if is_browser_icon_animation_active:
        browser_icon_animation_progress += 0.05;
        if browser_icon_animation_progress >= 1.0: is_browser_icon_animation_active, animating_browser_icon = False, None

    if is_dragging_icon and selected_icon:
        current_hover_target = None; all_icons = icons[home_page_index] + dock_icons
        for icon in all_icons:
            if icon != selected_icon and icon['rect'].collidepoint(mouse_pos): current_hover_target = icon; break
        if current_hover_target and current_hover_target != folder_hover_target: folder_hover_target, folder_hover_start_time = current_hover_target, time.time()
        elif not current_hover_target: folder_hover_target = None
    else: folder_hover_target = None

    if folder_hover_target:
        hover_duration = time.time() - folder_hover_start_time
        if hover_duration > 0.5: folder_highlight_alpha = min(100, folder_highlight_alpha + 10)
        if hover_duration > 1.0:
            dragged_icon, target_icon = selected_icon, folder_hover_target
            if target_icon['type'] == 'folder':
                for container in icons + [dock_icons]:
                    if dragged_icon in container: container.remove(dragged_icon); break
                target_icon['contains'].append(dragged_icon); dragged_icon.pop('page', None); dragged_icon.pop('row', None); dragged_icon.pop('col', None)
            elif target_icon['type'] == 'app':
                for container in icons + [dock_icons]:
                    if dragged_icon in container: container.remove(dragged_icon)
                    if target_icon in container: container.remove(target_icon)
                new_folder = {'type': 'folder', 'name': 'پوشه', 'contains': [target_icon, dragged_icon], 'page': target_icon.get('page'), 'row': target_icon.get('row'), 'col': target_icon.get('col'), 'rect': pygame.Rect(0,0,icon_size,icon_size), 'pos': target_icon['pos']}
                for item in new_folder['contains']: item.pop('page', None); item.pop('row', None); item.pop('col', None)
                if 'page' in new_folder and new_folder['page'] is not None: icons[new_folder['page']].append(new_folder)
                else: dock_icons.append(new_folder)
            is_dragging_icon, selected_icon, folder_hover_target, folder_highlight_alpha = False, None, None, 0
    else: folder_highlight_alpha = max(0, folder_highlight_alpha - 10)

    if folder_mouse_down_start_time > 0 and time.time() - folder_mouse_down_start_time > long_press_duration:
        is_folder_edit_mode, is_dragging_icon, selected_icon = True, True, selected_icon_in_folder
        icon_drag_offset = (selected_icon['rect'].x - folder_mouse_down_pos[0], selected_icon['rect'].y - folder_mouse_down_pos[1]); folder_mouse_down_start_time = 0

    if opened_folder and is_showing_folder and folder_animation_progress < 1.0: folder_animation_progress += 0.07
    elif (not is_showing_folder) and folder_animation_progress > 0.0:
        folder_animation_progress -= 0.07
        if folder_animation_progress <= 0.0: opened_folder, is_folder_edit_mode = None, False
    folder_animation_progress = max(0.0, min(1.0, folder_animation_progress))

    if animating_recent_app_index is not None:
        dragged_recent_app_offset_y += (target_dragged_recent_app_offset_y - dragged_recent_app_offset_y) * 0.2
        if abs(target_dragged_recent_app_offset_y - dragged_recent_app_offset_y) < 1:
            dragged_recent_app_offset_y = 0; animating_recent_app_index = None

    if current_screen == "lock" and not is_swiping_lock:
        lock_screen_offset_y += (target_lock_offset_y - lock_screen_offset_y) * 0.2

    elif current_screen == "home":
        if mouse_down_start_time != 0 and time.time() - mouse_down_start_time > long_press_duration:
            is_edit_mode, target_edit_mode_scale, is_swiping_home, mouse_down_start_time = True, 0.85, False, 0
        edit_mode_scale += (target_edit_mode_scale - edit_mode_scale) * 0.2
        if not is_swiping_home:
            if abs(target_offset) > 0:
                home_page_offset += (target_offset - home_page_offset) * 0.25
                if abs(target_offset - home_page_offset) < 1:
                    if target_offset <= -SCREEN_WIDTH: home_page_index, home_page_offset = home_page_index+1, home_page_offset+SCREEN_WIDTH
                    elif target_offset >= SCREEN_WIDTH: home_page_index, home_page_offset = home_page_index-1, home_page_offset-SCREEN_WIDTH
                    target_offset, home_page_offset = 0, 0
            elif not is_dragging_icon: home_page_offset += (0 - home_page_offset) * 0.25

    if music_transition['active']:
        music_transition['progress'] += dt / music_transition['duration']
        if music_transition['progress'] >= 1.0:
            # پایان ترانزیشن
            music_transition['active'] = False
            current_track_index = music_transition['new_track_index']
            # اطمینان از همگام شدن متغیرهای دیگر
            if music_transition['new_track_index'] != -1:
                music_track_name = music_transition['new_track_name']
                # current_album_art_surface قبلاً به‌روز شده
            music_transition['old_art'] = None
            music_transition['new_art'] = None
            # بازنشانی مقیاس کاور
            target_music_art_scale = 1.0
            music_art_scale = 1.0

    # --------------------------
    #         رسم فریم
    # --------------------------
    screen.fill(BLACK)

    if current_screen == "lock": draw_lock_screen(lock_screen_offset_y); draw_status_bar()
    elif current_screen == "animating_unlock":
        progress = (1 - math.cos(animation_progress * math.pi)) / 2
        draw_main_background(screen)
        draw_home_screen_static_elements()
        home_scale = 0.8 + 0.2 * progress
        content_surface, content_rect = draw_home_screen_content(home_screen_surface, 0, scale=home_scale, alpha=255 * progress)
        screen.blit(content_surface, content_rect); draw_page_indicators(home_page_index, num_home_pages); draw_status_bar(alpha=255 * progress)
        if lock_screen_snapshot: lock_screen_snapshot.set_alpha(255 * (1 - progress)); screen.blit(lock_screen_snapshot, (0,0))
        animation_progress += 0.05
        if animation_progress >= 1.0: animation_progress, current_screen, lock_screen_snapshot = 0.0, "home", None

    elif current_screen == "home":
        is_folder_active = opened_folder is not None; blur_alpha = int(100 * folder_animation_progress)
        draw_main_background(screen)
        
        # ۱. اول آیکونها روی صفحه رسم میشوند
        content_surface, content_rect = draw_home_screen_content(home_screen_surface, home_page_offset, is_folder_view_active=is_folder_active)
        if is_folder_active:
            blur_surface = pygame.Surface(content_surface.get_size(), pygame.SRCALPHA); blur_surface.fill((0,0,0, blur_alpha)); content_surface.blit(blur_surface, (0,0))
        screen.blit(content_surface, content_rect)
        
        # ۲. حالا داک فراخوانی میشود و از آیکونهای زیرینش عکس گرفته و آنها را تار میکند
        draw_home_screen_static_elements() # <--- به اینجا منتقل شد
        
        for item in folders_to_delete[:]:
            item['progress'] -= 0.08
            if item['progress'] <= 0: folders_to_delete.remove(item)
            else: draw_icon_base(screen, item['folder'], item['rect'], scale=item['progress'], alpha=255 * item['progress'])
        draw_page_indicators(home_page_index, num_home_pages); draw_status_bar()

    elif current_screen in ["recents_opening", "recents_closing", "recents"]:
        if current_screen == "recents_opening": recents_animation_progress += 0.07
        elif current_screen == "recents_closing": recents_animation_progress -= 0.07
        recents_animation_progress = max(0.0, min(1.0, recents_animation_progress)); home_scale = 1.0 - 0.1 * recents_animation_progress; home_alpha = 255 * (1.0 - recents_animation_progress * 0.5)
        draw_main_background(screen)
        draw_home_screen_static_elements()
        content_surface, content_rect = draw_home_screen_content(home_screen_surface, 0, scale=home_scale, alpha=home_alpha)
        screen.blit(content_surface, content_rect); draw_page_indicators(home_page_index, num_home_pages); draw_status_bar(); draw_recents_screen()
        if current_screen == "recents_opening" and recents_animation_progress >= 1.0: current_screen = "recents"
        elif current_screen == "recents_closing" and recents_animation_progress <= 0.0: current_screen = "home"

    elif current_screen in ["app_opening", "app_closing"]:
        # استفاده از dt برای حرکت کاملا یکنواخت حتی در صورت افت فریم
        animation_speed = 2.5
        if current_screen == "app_opening": 
            app_animation_progress += animation_speed * dt
        else: 
            app_animation_progress -= animation_speed * dt
            
        app_animation_progress = max(0.0, min(1.0, app_animation_progress))

        progress = ios_ease(app_animation_progress)

        draw_main_background(screen)
        bg_scale = 1.0 - (0.08 * progress) # زوم بک ملایم‌تر صفحه اصلی
        
        draw_home_screen_static_elements()
        home_surf, home_rect = draw_home_screen_content(home_screen_surface, 0, scale=bg_scale, alpha=255)
        
        # تاریک شدن ملایم صفحه زیرین
        darken_layer = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        darken_layer.fill((0, 0, 0, int(80 * progress)))
        home_surf.blit(darken_layer, (0,0))
        
        screen.blit(home_surf, home_rect)

        start_rect = opened_app_icon_rect
        end_rect = pygame.Rect(0, 0, SCREEN_WIDTH, SCREEN_HEIGHT)

        current_x = start_rect.x + (end_rect.x - start_rect.x) * progress
        current_y = start_rect.y + (end_rect.y - start_rect.y) * progress
        current_w = max(1, start_rect.width + (end_rect.width - start_rect.width) * progress)
        current_h = max(1, start_rect.height + (end_rect.height - start_rect.height) * progress)
        
        current_radius = 22 + (0 - 22) * progress 
        if current_radius < 0: current_radius = 0

        if target_app_snapshot is None:
             target_app_snapshot = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT))
             target_app_snapshot.fill(get_current_color('settings_bg'))

        # ترفند حیاتی برای پرفورمنس: استفاده از scale سریع حین حرکت و smoothscale فقط در ابتدا و انتها
        if progress > 0.05 and progress < 0.95:
            scaled_app = pygame.transform.scale(target_app_snapshot, (int(current_w), int(current_h)))
        else:
            scaled_app = pygame.transform.smoothscale(target_app_snapshot, (int(current_w), int(current_h)))
            
        if scaled_app.get_flags() & pygame.SRCALPHA == 0:
            scaled_app = scaled_app.convert_alpha()
            
        mask = pygame.Surface((int(current_w), int(current_h)), pygame.SRCALPHA)
        draw_rounded_rect(mask, mask.get_rect(), (255, 255, 255, 255), current_radius)
        scaled_app.blit(mask, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)
        
        screen.blit(scaled_app, (current_x, current_y))
        
        # 7. بررسی پایان انیمیشن
        if current_screen == "app_opening" and app_animation_progress >= 1.0:
            # اجرای منطق باز شدن نهایی (کدهای اصلی شما)
            
            # --- کپی از لاجیک اصلی شما ---
            app_name = app_context.get('app_name')
            app_id = app_context.get('app_id', app_name)

                # === اضافه کردن پشتیبانی از برنامه‌های remote ===
            if app_context.get('app_type') == 'remote':
                app_id = app_context['app_id']
                install_path = os.path.join('installed_apps', app_id)
                manifest_path = os.path.join(install_path, 'manifest.json')
                try:
                    with open(manifest_path, 'r') as f:
                        manifest = json.load(f)
                    runtime = manifest.get('runtime', 'python')
                    main_file = manifest['main_file']
                    env = os.environ.copy()
                    env['PARSOS_DISPLAY'] = '127.0.0.1:9500'
                    cmd = [runtime, main_file] if runtime != 'binary' else [os.path.join(install_path, main_file)]
                    subprocess.Popen(cmd, cwd=install_path, env=env,
                                    stdout=sys.stdout, stderr=sys.stderr)
                    # بعداً وقتی کلاینت وصل شد session_id را تنظیم می‌کنیم
                    # می‌توانیم یک نگاشت موقت بسازیم یا از app_id استفاده کنیم.
                    # برای سادگی، session_id همان app_id را موقتاً می‌گذاریم
                    # ولی بهتر است از طریق شناسهٔ واقعی سرور این کار را بکنیم.
                    # نمایش سرور خودش session تولید می‌کند. ما اینجا صبر نمی‌کنیم.
                    # در draw_app_screen با app_id چک می‌کنیم.
                except Exception as e:
                    print(f"Failed to launch remote app: {e}")
                    current_screen = "home"  # برگشت به خانه
            
            if app_context.get('is_external_app'):
                # (همان کدهای قبلی برای اجرای native یا integrated)
                app_path = os.path.join('installed_apps', app_id)
                manifest_path = os.path.join(app_path, 'manifest.json')
                try:
                    with open(manifest_path, 'r', encoding='utf-8') as f: manifest = json.load(f)
                    app_type = manifest.get('type', 'integrated')
                    if app_type == 'native':
                        # ... (کد اجرای Native)
                        main_file = manifest.get('main_file', 'main.py')
                        script_path = os.path.join(app_path, main_file)
                        subprocess.Popen([sys.executable, script_path], cwd=app_path, stdout=sys.stdout, stderr=sys.stderr)
                        current_screen = "home"
                        # افزودن به Recents...
                    else:
                        current_screen = "app_open"
                        # ... (کد اجرای Integrated)
                        kernel.kernel_instance.register_process(app_id, app_name)
                        if app_id not in running_app_instances:
                             # ... (importlib logic)
                             main_file = manifest.get('main_file', 'main.py')
                             main_class_name = manifest.get('main_class')
                             module_path = os.path.join(app_path, main_file)
                             spec = importlib.util.spec_from_file_location(f"installed_apps.{app_id}.main", module_path)
                             app_module = importlib.util.module_from_spec(spec)
                             spec.loader.exec_module(app_module)
                             AppClass = getattr(app_module, main_class_name)
                             running_app_instances[app_id] = AppClass(app_id, app_name, app_path)
                except Exception as e:
                    print(f"Error: {e}")
                    current_screen = "home"
            else:
                 current_screen = "app_open"
                 kernel.kernel_instance.register_process(app_id, app_name)
            
            # مدیریت Recents
            existing_app = next((item for item in recents_apps_list if item.get('name') == app_name), None)
            if existing_app: recents_apps_list.remove(existing_app)
            new_recent = {'name': app_name}
            if app_context.get('app_id'): new_recent['app_id'] = app_context.get('app_id')
            recents_apps_list.insert(0, new_recent)

        elif current_screen == "app_closing" and app_animation_progress <= 0.0:
            # پایان بستن برنامه
            closed_app_name = app_context.get('app_name')
            
            # ذخیره وضعیت برای آیکون انیمیتد
            target_icon = None
            def find_icon(name, container):
                for icon in container:
                    if icon['type'] == 'app' and icon['name'] == name: return icon
                    if icon['type'] == 'folder':
                        found = find_icon(name, icon['contains'])
                        if found: return found
                return None
            
            for page in icons:
                target_icon = find_icon(closed_app_name, page)
                if target_icon: break
            if not target_icon: target_icon = find_icon(closed_app_name, dock_icons)
            
            # فعال کردن انیمیشن آیکون پس از بسته شدن (Wiggle)
            if target_icon:
                if closed_app_name == 'settings': animating_icon, is_icon_animation_active, icon_animation_progress = target_icon, True, 0.0
                elif closed_app_name == 'notes': animating_notes_icon, is_notes_icon_animation_active, notes_icon_animation_progress = target_icon, True, 0.0
                elif closed_app_name == 'music': animating_music_icon, is_music_icon_animation_active, music_icon_animation_progress = target_icon, True, 0.0
                elif closed_app_name == 'browser': animating_browser_icon, is_browser_icon_animation_active, browser_icon_animation_progress = target_icon, True, 0.0
            
            current_screen = "home"
            app_close_timestamp = time.time()

    elif current_screen == "app_open":
        if is_swiping_app_close or is_returning_app_to_open:
            draw_main_background(screen)
            progress = app_swipe_interactive_progress
            
            # مقیاس و شفافیت صفحه اصلی زیرین
            home_scale = 0.9 + (0.1 * progress) # از 0.9 شروع میشود و به 1 میرسد
            home_alpha = 255 # همیشه دیده شود اما زیر برنامه باشد
            
            draw_home_screen_static_elements()
            
            # رسم صفحه اصلی در پس زمینه
            content_surface, content_rect = draw_home_screen_content(home_screen_surface, 0, scale=home_scale, alpha=255)
            # تاریک کردن صفحه اصلی وقتی برنامه روی آن است
            darken_surf = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
            darken_surf.fill((0, 0, 0, int(100 * (1-progress)))) # هرچه پایین تر می آید روشن تر میشود
            screen.blit(content_surface, content_rect)
            screen.blit(darken_surf, (0,0))
            
            # محاسبه موقعیت کارت برنامه (که کوچک شده)
            scale_factor = 1.0 - (0.4 * progress) # تا 60 درصد کوچک میشود
            
            # محاسبه Rect فعلی برنامه
            current_w = SCREEN_WIDTH * scale_factor
            current_h = SCREEN_HEIGHT * scale_factor
            
            # موقعیت انگشت ماوس را دنبال کند
            mouse_x, mouse_y = pygame.mouse.get_pos()
            # مرکز کردن روی ماوس با کمی تاخیر یا افست
            target_x = mouse_x - (current_w / 2)
            # اگر داریم برمیگردیم، وسط صفحه برود
            if is_returning_app_to_open:
                target_x = (SCREEN_WIDTH - current_w) / 2
                target_y = (SCREEN_HEIGHT - current_h) / 2
            else:
                # افست دادن به Y تا زیر انگشت نباشد
                target_y = mouse_y - 100 
            
            # استفاده از app_key برای گرفتن آخرین وضعیت گرافیکی برنامه
            app_name = app_context.get('app_name')
            app_key = app_context.get('app_id', app_name)
            
            # گرفتن تصویر زنده یا اسنپشات ذخیره شده
            app_surf_to_draw = app_surfaces.get(app_key)
            if not app_surf_to_draw:
                 # اگر نبود، رندر کن
                 app_surf_to_draw = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT))
                 draw_app_screen() # روی app_surf_to_draw باید تغییر دهید اما چون draw_app_screen روی screen میکشد اینجا سخت است.
                 # ساده تر: از target_app_snapshot استفاده کن اگر موجود بود
                 if target_app_snapshot: app_surf_to_draw = target_app_snapshot
                 else: app_surf_to_draw = screen.copy() # آخرین فریم
            
            # اسکیل کردن و رسم با گوشه گرد
            if app_surf_to_draw:
                scaled_app = pygame.transform.smoothscale(app_surf_to_draw, (int(current_w), int(current_h)))
                
                # --- اصلاح: تبدیل به سطح با کانال آلفا و اعمال ماسک گرد ---
                # ۱. اطمینان از وجود کانال آلفا
                if scaled_app.get_flags() & pygame.SRCALPHA == 0:
                    scaled_app = scaled_app.convert_alpha()
                
                # ۲. ساخت ماسک با گوشه‌های گرد
                radius = 30 * progress
                mask = pygame.Surface((int(current_w), int(current_h)), pygame.SRCALPHA)
                draw_rounded_rect(mask, mask.get_rect(), (255, 255, 255, 255), radius)
                
                # ۳. اعمال ماسک روی کانال آلفای تصویر برنامه
                scaled_app.blit(mask, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)
                # ------------------------------------------------------------
                
                screen.blit(scaled_app, (target_x, target_y))

            if current_screen == "app_open" and app_context.get('app_type') == 'remote':
                # پیدا کردن session_id مربوطه (فرض می‌کنیم اولین جلسه)
                target_session = None
                with display_server.lock:
                    for sid, app in display_server.apps.items():
                        if app.is_connected:
                            target_session = sid
                            break
                if target_session is not None:
                    display_server.send_events_to_app(target_session, events)

            # رسم نوار هوم (Home Indicator)
            indicator_surface = pygame.Surface((130, 5), pygame.SRCALPHA)
            draw_rounded_rect(indicator_surface, indicator_surface.get_rect(), (255, 255, 255, 150), 2.5)
            # موقعیت اندیکاتور باید روی خود کارت برنامه باشد
            screen.blit(indicator_surface, (target_x + current_w/2 - 65, target_y + current_h - 15))
            draw_status_bar()
        else:
            draw_app_screen()

    notes_module = NotesApp(sc, mf, get_current_color, render_persian_text)

    if app_context.get('app_name') == 'gallery' and is_gallery_fullscreen: draw_gallery_fullscreen_view(screen)
    if app_context.get('app_name') == 'gallery' and is_video_playing: draw_video_player(screen)
    if app_context.get('app_name') == 'notes':
        notes_module.handle_event(event, app_context)
    if opened_folder is not None: draw_folder_view()

    if notification_center_progress > 0: draw_notification_center(screen, notification_center_progress)
    if control_center_progress > 0: draw_control_center(screen, control_center_progress, cc_vertical_offset) # <--- (اصلاح شده) حالا CC جدید را رسم میکند

    if is_charging_animation_active: draw_charging_animation()
    if low_battery_warning_progress > 0: draw_low_battery_warning(screen)

    draw_heads_up_notification(screen)
    draw_unimportant_notifications(screen)

    draw_superisland(screen)

    if language_picker_progress > 0:
        draw_language_picker(screen, language_picker_progress)

    messenger_poll_incoming()

    pygame.display.flip()
    clock.tick(90)
    
if browser_manager:
    browser_manager.quit()
    
save_layout(); save_settings(); save_notes()
pygame.quit(); sys.exit()

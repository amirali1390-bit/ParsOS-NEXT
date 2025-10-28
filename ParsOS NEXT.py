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

# (جدید) تلاش برای وارد کردن کتابخانه‌های مورد نیاز برای جلوه عمق
try:
    from rembg import remove
    from PIL import Image
    depth_effect_available = True
except ImportError:
    depth_effect_available = False
    print("Warning: 'rembg' and 'Pillow' libraries not found. Depth Effect will not be available.")
    print("Install them using: pip install rembg Pillow")

# (جدید) کلاس پایه برای تمام برنامه‌های قابل نصب
class ParsOS_App:
    def __init__(self, app_id, app_name, app_path):
        """سازنده برنامه که توسط سیستم عامل فراخوانی می‌شود."""
        self.app_id = app_id
        self.app_name = app_name
        self.app_path = app_path # مسیر پوشه برنامه برای دسترسی به فایل‌ها
        self.text_font = pygame.font.Font(main_font_path, 16)
        self.title_font = pygame.font.Font(main_font_path, 22)

    def handle_event(self, event):
        """این متد برای مدیریت رویدادها (کلیک، کیبورد و ...) است."""
        pass

    def update(self):
        """این متد برای به‌روزرسانی منطق برنامه در هر فریم است."""
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
# ابعاد صفحه نمایش
SCREEN_WIDTH = 400
SCREEN_HEIGHT = 700
screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
pygame.display.set_caption("ParsOS NEXT")

# (جدید) متغیرهای انیمیشن کلیک روی آیکون
pressed_icon = None
pressed_icon_animation_progress = 0.0
pressed_icon_animation_direction = 0

# (جدید) رنگ‌های ویجت ساعت
CLOCK_WIDGET_HAND_HOUR = (40, 40, 40)
CLOCK_WIDGET_HAND_MINUTE = (60, 60, 60)
CLOCK_WIDGET_HAND_SECOND = (255, 50, 50)
CLOCK_WIDGET_TICKS = (150, 150, 150)

unimportant_notifications = [] 
# (جدید) اعلان‌های اصلی
main_notifications = [] 
# (جدید) متغیر برای اعلان heads-up
active_heads_up_notification = None
notifications = [] # هر اعلان یک دیکشنری شامل متن، زمان و آلفا است

DOWNLOADABLE_EXTENSIONS = ['.zip', '.exe', '.pdf', '.png', '.jpg', '.jpeg', '.mp3', '.wav', '.txt', '.prs']

# -------------------
#      مدیریت رنگ‌ها و تم‌ها
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
    'gallery_bg': [(250, 250, 250), (28, 28, 28)]
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
# متغیرهای پس‌زمینه صفحه قفل
lock_screen_wallpaper_path = None
current_lock_screen_wallpaper_image = None
# (جدید) متغیرهای جلوه عمق
is_depth_effect_enabled = False
current_lock_screen_subject_image = None


# فونت‌ها
try:
    main_font_path = "Vazir.ttf"
    try:
        about_font = pygame.font.Font("ProductSans.ttf", 48)
    except FileNotFoundError:
        print("فونت ProductSans.ttf یافت نشد. از فونت وزیر برای صفحه 'درباره' استفاده می‌شود.")
        about_font = pygame.font.Font(main_font_path, 40)
    clock_font = pygame.font.Font(main_font_path, 80)
    battery_font = pygame.font.Font(main_font_path, 48)
    text_font = pygame.font.Font(main_font_path, 16)
    notes_font = pygame.font.Font(main_font_path, 18)
    music_font = pygame.font.Font(main_font_path, 22)
    status_bar_font = pygame.font.Font(main_font_path, 14)
    settings_title_font = pygame.font.Font(main_font_path, 24)
    music_time_font = pygame.font.Font(main_font_path, 12)
    browser_content_font = pygame.font.Font(main_font_path, 14)
except FileNotFoundError:
    print("فونت Vazir.ttf یافت نشد. از فونت پیش‌فرض استفاده می‌شود.")
    main_font_path = None
    about_font = pygame.font.Font(None, 60)
    clock_font = pygame.font.Font(None, 100)
    battery_font = pygame.font.Font(None, 60)
    text_font = pygame.font.Font(None, 24)
    notes_font = pygame.font.Font(None, 26)
    music_font = pygame.font.Font(None, 30)
    status_bar_font = pygame.font.Font(None, 20)
    settings_title_font = pygame.font.Font(None, 32)
    music_time_font = pygame.font.Font(None, 18)
    browser_content_font = pygame.font.Font(None, 20)

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
#app_just_closed = False # (جدید) برای رفع باگ منوی برنامه‌های اخیر
app_close_timestamp = 0.0

# (جدید) متغیرهای مدیریت وضعیت برای چندنخی
thread_results = {} # دیکشنری برای نگهداری نتایج نخ‌ها
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

# (جدید) متغیرهای برنامه فایل‌ها
files_current_path = '.'  # مسیر فعلی که در حال نمایش است
files_list = []           # لیست فایل‌ها و پوشه‌های مسیر فعلی
files_scroll_offset = 0.0
target_files_scroll_offset = 0.0
files_content_height = 0

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

# متغیرهای مرکز کنترل
is_control_center_open = False
control_center_progress = 0.0  # 0.0: بسته, 1.0: باز
is_dragging_control_center = False
control_center_snapshot = None
# (اصلاح شده) وضعیت دکمه‌های مرکز کنترل با ساختار جدید
cc_buttons = {
    # دکمه‌های بزرگ ردیف اول
    'wifi': {
        'is_active': False, 'is_pressed': False, 'scale_progress': 0.0, 'color_progress': 0.0, 
        'press_anim_progress': 0.0, 'press_location': None, 'label': 'وای فای', 'type': 'large'
    },
    'data': {
        'is_active': True, 'is_pressed': False, 'scale_progress': 0.0, 'color_progress': 1.0, 
        'press_anim_progress': 0.0, 'press_location': None, 'label': 'داده همراه', 'type': 'large'
    },
    
    # دکمه‌های گرد
    'dnd': {'is_active': False, 'is_pressed': False, 'label': 'مزاحم نشوید', 'icon': '🌙', 'type': 'circular'},
    'airplane': {'is_active': False, 'is_pressed': False, 'label': 'هواپیما', 'icon': '✈️', 'type': 'circular'},
    'bluetooth': {'is_active': False, 'is_pressed': False, 'label': 'بلوتوث', 'icon': 'B', 'type': 'circular'}, # آیکون بلوتوث در فونت‌ها نیست
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

# متغیرهای منوی برنامه‌های اخیر
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


# متغیرهای صفحه اصلی
icons = [[] for _ in range(num_home_pages)]
dock_icons = []
icon_size = 70
icon_padding = 25
icons_per_row = 4
rows_per_page = 4
MAX_DOCK_ICONS = 3
dock_height = 85
dock_margin = 10
dock_rect = pygame.Rect(dock_margin, SCREEN_HEIGHT - dock_height - dock_margin, SCREEN_WIDTH - 2 * dock_margin, dock_height)

# تنظیمات پیش‌فرض
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
    (اصلاح شده) این تابع تصویر ورودی از نوع pygame.Surface را برای جلوه عمق پردازش می‌کند.
    مشکل تبدیل فرمت تصویر تغییراندازه‌یافته با استفاده از روش مطمئن‌تر tostring حل شده است.
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
        # (اصلاح شده) بررسی جامع‌تر برای انواع مختلف آیکون
        if 'type' not in icon_data: icon_data['type'] = 'app'

        if icon_data.get('type') == 'app' and icon_data.get('name') not in app_list:
            continue

        # (جدید) افزودن منطق برای ویجت
        if icon_data.get('type') == 'widget':
             # اندازه پیش‌فرض برای ویجت ۱x۱ است
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

def load_gallery_photos():
    global gallery_photos, gallery_thumbnails
    if not os.path.exists('gallery_photos'):
        os.makedirs('gallery_photos')
    
    try:
        photo_files = [f for f in os.listdir('gallery_photos') if f.lower().endswith(('.png', '.jpg', '.jpeg'))]
        for filename in photo_files:
            path = os.path.join('gallery_photos', filename)
            gallery_photos.append({'path': path, 'image': None}) # خود عکس را بعدا بارگذاری می‌کنیم
            
            # ساخت و ذخیره تامبنیل‌ها برای سرعت بیشتر
            try:
                img = pygame.image.load(path)
                thumbnail_size = 150
                # حفظ نسبت تصویر
                width, height = img.get_size()
                if width > height:
                    new_height = int(thumbnail_size * (height / width))
                    new_size = (thumbnail_size, new_height)
                else:
                    new_width = int(thumbnail_size * (width / height))
                    new_size = (new_width, thumbnail_size)
                
                thumb = pygame.transform.smoothscale(img, new_size)
                gallery_thumbnails[path] = thumb
            except Exception as e:
                print(f"Error creating thumbnail for {filename}: {e}")

    except Exception as e:
        print(f"Error loading gallery photos: {e}")

# (جدید) این تابع را در انتهای بخش بارگذاری اولیه صدا بزنید
load_gallery_photos()

def load_layout():
    global icons, dock_icons
    loaded_apps = set()
    # (جدید) یک مجموعه برای ویجت‌ها تا از افزودن تکراری جلوگیری شود
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

    # افزودن برنامه‌های پیش‌فرض در صورت عدم وجود
    if 'settings' not in loaded_apps: icons[0].append({'type': 'app', 'name': 'settings', 'page': 0, 'row': 2, 'col': 0, 'rect': pygame.Rect(0,0,icon_size,icon_size), 'pos': [0,0]})
    if 'notes' not in loaded_apps: icons[0].append({'type': 'app', 'name': 'notes', 'page': 0, 'row': 2, 'col': 1, 'rect': pygame.Rect(0,0,icon_size,icon_size), 'pos': [0,0]})
    if 'music' not in loaded_apps: icons[0].append({'type': 'app', 'name': 'music', 'page': 0, 'row': 2, 'col': 2, 'rect': pygame.Rect(0,0,icon_size,icon_size), 'pos': [0,0]})
    if 'browser' not in loaded_apps: icons[0].append({'type': 'app', 'name': 'browser', 'page': 0, 'row': 2, 'col': 3, 'rect': pygame.Rect(0,0,icon_size,icon_size), 'pos': [0,0]})
    if 'gallery' not in loaded_apps: icons[0].append({'type': 'app', 'name': 'gallery', 'page': 0, 'row': 3, 'col': 0, 'rect': pygame.Rect(0,0,icon_size,icon_size), 'pos': [0,0]})
    if 'files' not in loaded_apps: icons[0].append({'type': 'app', 'name': 'files', 'page': 0, 'row': 3, 'col': 1, 'rect': pygame.Rect(0,0,icon_size,icon_size), 'pos': [0,0]})

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
        'is_depth_effect_enabled': is_depth_effect_enabled, # (جدید)
    }
    try:
        with open('settings.json', 'w') as f: json.dump(settings_data, f, indent=4)
    except IOError as e: print(f"Error saving settings: {e}")

def load_settings():
    global is_dark_mode, theme_animation_progress, saved_light_wallpaper_top, saved_light_wallpaper_bottom, \
           BG_TOP_COLOR, BG_BOTTOM_COLOR, lock_screen_style, dark_mode_switch_progress, wallpaper_path, current_wallpaper_image, \
           lock_screen_wallpaper_path, current_lock_screen_wallpaper_image, is_depth_effect_enabled
    try:
        with open('settings.json', 'r') as f:
            settings_data = json.load(f)
            is_dark_mode = settings_data.get('is_dark_mode', False)
            lock_screen_style = settings_data.get('lock_screen_style', 'default')
            wallpaper_path = settings_data.get('wallpaper_path', None)
            lock_screen_wallpaper_path = settings_data.get('lock_screen_wallpaper_path', None)
            is_depth_effect_enabled = settings_data.get('is_depth_effect_enabled', False) # (جدید)

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
                    # (جدید) پردازش تصویر عمقی هنگام بارگذاری
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
    if not mutagen_available:
        return 0, None
    length = 0
    art_surface = None
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
        elif filepath.lower().endswith('.wav'):
            audio = mutagen.wave.WAVE(filepath)
        elif filepath.lower().endswith('.ogg'):
            audio = mutagen.oggvorbis.OggVorbis(filepath)
        else:
            return 0, None
        length = audio.info.length
    except Exception as e:
        print(f"Error reading audio file metadata for {filepath}: {e}")
        return 0, None
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

# ایجاد پوشه‌های لازم در ابتدای برنامه
if not os.path.exists('wallpapers'): os.makedirs('wallpapers')

load_settings(); load_layout(); load_notes(); load_music_files()

# --------------------------
#       توابع کمکی
# --------------------------
# (جدید) توابع ایزینگ برای انیمیشن‌های روان و حرفه‌ای
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
    """به صورت بازگشتی در لیست آیکون‌ها (و پوشه‌ها) به دنبال app_id می‌گردد."""
    for icon in icon_list:
        if icon.get('app_id') == app_id:
            return icon
        if icon.get('type') == 'folder':
            found_in_folder = find_icon_by_app_id(app_id, icon.get('contains', []))
            if found_in_folder:
                return found_in_folder
    return None

def draw_cc_slider(surface, rect, progress, icon_char, text_color):
    """(جدید) یک اسلایدر سفارشی برای مرکز کنترل رسم می‌کند."""
    bar_rect = rect.inflate(-40, -rect.height * 0.7)
    draw_rounded_rect(surface, bar_rect, (80, 80, 90) if is_dark_mode else (200, 200, 205), 8)
    
    progress_width = bar_rect.width * progress
    progress_rect = pygame.Rect(bar_rect.left, bar_rect.top, progress_width, bar_rect.height)
    draw_rounded_rect(surface, progress_rect, (255, 255, 255) if is_dark_mode else (80, 80, 80), 8)
    
    handle_pos = (bar_rect.left + progress_width, bar_rect.centery)
    pygame.draw.circle(surface, WHITE, handle_pos, 12)
    
    icon_font = pygame.font.Font(main_font_path, 18) if main_font_path else pygame.font.Font(None, 24)
    icon_surf = icon_font.render(icon_char, True, text_color)
    surface.blit(icon_surf, icon_surf.get_rect(center=(rect.left + 20, bar_rect.centery)))

def draw_cc_circular_toggle(surface, rect, button_data, text_color, alpha):
    """(جدید) یک دکمه تاگل دایره‌ای برای مرکز کنترل رسم می‌کند."""
    progress = button_data.get('color_progress', 0.0)
    base_color = (60, 60, 70) if is_dark_mode else (220, 220, 225)
    active_color = (50, 150, 255)
    
    current_color = tuple(int(b + (a - b) * progress) for b, a in zip(base_color, active_color))
    final_color = (*current_color, int(alpha * 0.9))
    
    pygame.draw.circle(surface, final_color, rect.center, rect.width // 2)
    
    icon_font = pygame.font.Font(main_font_path, 20) if main_font_path else pygame.font.Font(None, 28)
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
    
    fonts = { 'p': browser_content_font, 'h1': pygame.font.Font(main_font_path, 22), 'h2': pygame.font.Font(main_font_path, 20), 'h3': pygame.font.Font(main_font_path, 18), 'a': browser_content_font, 'default': browser_content_font }
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
    (نسخه اصلاح شده)
    یک برنامه .prs را نصب یا به‌روزرسانی می‌کند.
    اگر app_id از قبل وجود داشته باشد، فقط فایل‌ها را جایگزین کرده و نام آیکون را به‌روز می‌کند.
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
                main_class = manifest_data.get('main_class')

                if not all([app_id, app_name, main_file, main_class]):
                    print("Error: manifest.json is missing required fields.")
                    add_unimportant_notification("نصب ناموفق: فایل ناقص")
                    return

                # --- (بخش کلیدی جدید: بررسی به‌روزرسانی) ---
                existing_icon = None
                for page_icons in icons:
                    existing_icon = find_icon_by_app_id(app_id, page_icons)
                    if existing_icon: break
                if not existing_icon:
                    existing_icon = find_icon_by_app_id(app_id, dock_icons)
                
                # مقصد نصب
                install_path = os.path.join('installed_apps', app_id)
                os.makedirs(install_path, exist_ok=True)
                
                # استخراج فایل‌ها (در هر صورت انجام می‌شود تا فایل‌ها جایگزین شوند)
                zip_ref.extractall(install_path)

                if existing_icon:
                    # --- منطق به‌روزرسانی ---
                    print(f"App '{app_id}' updating.")
                    # به‌روزرسانی نام آیکون در صورتی که در مانیفست جدید تغییر کرده باشد
                    existing_icon['name'] = app_name
                    
                    # (جدید) اگر برنامه در حال اجرا بود، آن را ببند تا نسخه جدید بارگذاری شود
                    if app_id in running_app_instances:
                        kernel.kernel_instance.terminate_process(app_id)
                        if app_id in running_app_instances: # بررسی مجدد (ممکن است در صف باشد)
                            del running_app_instances[app_id]
                        print(f"Closed running instance of {app_id} for update.")

                    save_layout() # ذخیره نام جدید آیکون
                    add_unimportant_notification(f"برنامه {app_name} به‌روزرسانی شد")

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
                        # توجه: در این حالت فایل‌ها استخراج شده‌اند اما آیکونی وجود ندارد
                        # می‌توان فایل‌های استخراج شده را پاک کرد، اما فعلاً آن را رها می‌کنیم
                        return

                    save_layout()
                    add_unimportant_notification(f"برنامه {app_name} نصب شد!")

        except Exception as e:
            print(f"Failed to install/update .PRS app: {e}")
            add_unimportant_notification(f"نصب/به‌روزرسانی ناموفق: {e}")
        finally:
            is_installing_app = False

    # شروع نخ نصب/به‌روزرسانی
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

def draw_gradient_background(surface, top_color, bottom_color):
    height = surface.get_height()
    for y in range(height):
        ratio = y / height
        r = int(top_color[0] * (1 - ratio) + bottom_color[0] * ratio)
        g = int(top_color[1] * (1 - ratio) + bottom_color[1] * ratio)
        b = int(top_color[2] * (1 - ratio) + bottom_color[2] * ratio)
        pygame.draw.line(surface, (r, g, b), (0, y), (surface.get_width(), y))

def draw_main_background(surface):
    if current_wallpaper_image and not is_dark_mode:
        surface.blit(current_wallpaper_image, (0, 0))
    else:
        top = DARK_MODE_BG_TOP if is_dark_mode else BG_TOP_COLOR
        bottom = DARK_MODE_BG_BOTTOM if is_dark_mode else BG_BOTTOM_COLOR
        draw_gradient_background(surface, top, bottom)

def draw_rounded_rect(surface, rect, color, corner_radius):
    if corner_radius < 0: corner_radius = 0
    if rect.width < 2 * corner_radius or rect.height < 2 * corner_radius:
        # اگر شعاع بزرگتر از نصف عرض یا ارتفاع باشد، مستطیل معمولی رسم کن
        if rect.width < 2 * corner_radius: corner_radius = rect.width / 2
        if rect.height < 2 * corner_radius: corner_radius = rect.height / 2
    
    # اطمینان از اینکه شعاع یک عدد صحیح است
    corner_radius = int(corner_radius)

    # رسم چهار دایره در گوشه‌ها
    pygame.draw.circle(surface, color, (rect.left + corner_radius, rect.top + corner_radius), corner_radius)
    pygame.draw.circle(surface, color, (rect.right - corner_radius - 1, rect.top + corner_radius), corner_radius)
    pygame.draw.circle(surface, color, (rect.left + corner_radius, rect.bottom - corner_radius - 1), corner_radius)
    pygame.draw.circle(surface, color, (rect.right - corner_radius - 1, rect.bottom - corner_radius - 1), corner_radius)

    # رسم دو مستطیل برای پر کردن فضای بین دایره‌ها
    pygame.draw.rect(surface, color, rect.inflate(-2 * corner_radius, 0))
    pygame.draw.rect(surface, color, rect.inflate(0, -2 * corner_radius))


def get_icon_at_pos(pos, icon_list):
    for icon in icon_list:
        if icon['rect'].collidepoint(pos): return icon
    return None

def get_grid_pos(pos, item_being_dragged=None):
    # (جدید) اگر آیتمی در حال جابجایی است، اندازه آن را در نظر می‌گیریم
    item_w, item_h = 1, 1 # اندازه پیش‌فرض در واحد گرید
    if item_being_dragged and item_being_dragged.get('type') == 'widget':
        item_w, item_h = item_being_dragged.get('size', (1,1))

    start_x = (SCREEN_WIDTH - (icons_per_row * icon_size + (icons_per_row - 1) * icon_padding)) / 2
    start_y = 60
    col = (pos[0] - start_x + icon_padding/2) // (icon_size + icon_padding)
    row = (pos[1] - start_y + icon_padding/2) // (icon_size + icon_padding)

    # اطمینان حاصل شود که ویجت از صفحه خارج نمی‌شود
    final_row = max(0, min(rows_per_page - item_h, int(row)))
    final_col = max(0, min(icons_per_row - item_w, int(col)))

    return int(final_row), int(final_col)

def apply_gaussian_blur(surface, iterations=10, scale_factor=4):
    width, height = surface.get_size()
    if width < 1 or height < 1: return surface
    temp_surface = surface.copy()
    for _ in range(iterations):
        small_w, small_h = max(1, width // scale_factor), max(1, height // scale_factor)
        small_surf = pygame.transform.smoothscale(temp_surface, (small_w, small_h))
        temp_surface = pygame.transform.smoothscale(small_surf, (width, height))
    return temp_surface

def create_charging_particle():
    side = random.randint(0, 3)
    if side == 0: pos = [random.randint(0, SCREEN_WIDTH), -10]
    elif side == 1: pos = [SCREEN_WIDTH + 10, random.randint(0, SCREEN_HEIGHT)]
    elif side == 2: pos = [random.randint(0, SCREEN_WIDTH), SCREEN_HEIGHT + 10]
    else: pos = [-10, random.randint(0, SCREEN_HEIGHT)]
    return {'pos': pos, 'radius': random.randint(3, 10), 'speed': random.uniform(1.5, 3.5)}

def play_next_song():
    global current_track_index, music_track_name, is_music_playing, is_music_paused, current_track_length, current_album_art_surface, music_playback_start_time_offset
    if not music_playlist: return
    current_track_index = (current_track_index + 1) % len(music_playlist)
    pygame.mixer.music.load(music_playlist[current_track_index])
    current_track_length, current_album_art_surface = get_track_info(music_playlist[current_track_index])
    pygame.mixer.music.play()
    music_track_name = os.path.basename(music_playlist[current_track_index])
    is_music_playing, is_music_paused = True, False
    music_playback_start_time_offset = 0

def play_previous_song():
    global current_track_index, music_track_name, is_music_playing, is_music_paused, current_track_length, current_album_art_surface, music_playback_start_time_offset
    if not music_playlist: return
    current_track_index = (current_track_index - 1 + len(music_playlist)) % len(music_playlist)
    pygame.mixer.music.load(music_playlist[current_track_index])
    current_track_length, current_album_art_surface = get_track_info(music_playlist[current_track_index])
    pygame.mixer.music.play()
    music_track_name = os.path.basename(music_playlist[current_track_index])
    is_music_playing, is_music_paused = True, False
    music_playback_start_time_offset = 0

# -----------------------------------
#      توابع رسم صفحات و عناصر
# -----------------------------------
# (جدید) تابع رسم ویجت ساعت
def draw_clock_widget(surface, rect):
    """ویجت ساعت آنالوگ را مطابق با نمونه تصویر، روی سطح ورودی رسم می‌کند."""
    # رسم پس‌زمینه سفید با گوشه‌های گرد
    draw_rounded_rect(surface, surface.get_rect(), (255, 255, 255), 22)

    center = rect.centerx, rect.centery
    radius = min(rect.width, rect.height) / 2 * 0.85

    # رسم نقطه‌های ساعت
    for i in range(60):
        angle = math.radians(i * 6 - 90)
        start_radius = radius * 0.95
        end_radius = radius
        if i % 5 == 0: # نقطه‌های مربوط به ساعت‌ها ضخیم‌تر هستند
             start_radius = radius * 0.88

        start_pos = (center[0] + start_radius * math.cos(angle), center[1] + start_radius * math.sin(angle))
        end_pos = (center[0] + end_radius * math.cos(angle), center[1] + end_radius * math.sin(angle))
        pygame.draw.line(surface, CLOCK_WIDGET_TICKS, start_pos, end_pos, 2)

    # گرفتن زمان فعلی
    now = datetime.datetime.now()
    hour = now.hour % 12 + now.minute / 60
    minute = now.minute + now.second / 60
    second = now.second

    # محاسبه زاویه عقربه‌ها
    hour_angle = math.radians(hour * 30 - 90)
    minute_angle = math.radians(minute * 6 - 90)
    second_angle = math.radians(second * 6 - 90)

    # رسم عقربه‌ها
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
    """بررسی می‌کند که آیا یک ناحیه مشخص در گرید صفحه اصلی خالی است یا خیر."""
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
    """یک اعلان متنی غیرمهم به پایین صفحه اضافه می‌کند."""
    # (جدید) اضافه کردن scale برای انیمیشن بزرگ شدن
    unimportant_notifications.append({
        'text': text,
        'timestamp': time.time(),
        'alpha': 0.0,
        'scale': 0.8, # شروع از مقیاس کوچک
        'state': 'entering' # وضعیت برای کنترل انیمیشن
    })

def download_file(url):
    """فایل را از URL داده شده دانلود و در پوشه downloads ذخیره می‌کند."""
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

# (جدید) تابع رسم اعلان‌ها روی صفحه
def draw_unimportant_notifications(surface):
    """اعلان‌های غیرمهم را با انیمیشن نرم شفافیت و اندازه رسم می‌کند."""
    y_offset = SCREEN_HEIGHT - 60
    for notification in unimportant_notifications[:]:
        # (اصلاح شده) مدیریت انیمیشن ورود، نمایش و خروج
        if notification['state'] == 'entering':
            notification['alpha'] += 25
            notification['scale'] += 0.02
            if notification['alpha'] >= 255:
                notification['alpha'] = 255
                notification['scale'] = 1.0
                notification['state'] = 'visible'
                notification['timestamp'] = time.time() # تایمر از اینجا شروع می‌شود
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

        # تغییر اندازه متن متناسب با پس‌زمینه
        scaled_text_surf = pygame.transform.smoothscale(text_surf, (int(text_surf.get_width() * notification['scale']), int(text_surf.get_height() * notification['scale'])))

        alpha = max(0, min(255, notification['alpha']))
        bg_surf.set_alpha(alpha)
        scaled_text_surf.set_alpha(alpha)

        surface.blit(bg_surf, bg_rect)
        surface.blit(scaled_text_surf, scaled_text_surf.get_rect(center=bg_rect.center))

        y_offset -= bg_rect.height + 10
        
# (جدید) تابع رسم یک کارت اعلان (برای مرکز اعلانات و heads-up)
def draw_notification_card(surface, rect, notification_data, alpha=255):
    """یک کارت اعلان با شمایل تصویر نمونه را رسم می‌کند."""
    card_surface = pygame.Surface(rect.size, pygame.SRCALPHA)
    
    bg_color = (255, 255, 255, int(220 * (alpha/255))) if not is_dark_mode else (40, 40, 50, int(220 * (alpha/255)))
    draw_rounded_rect(card_surface, card_surface.get_rect(), bg_color, 20)
    
    icon_rect = pygame.Rect(15, 15, 30, 30)
    # (اصلاح شده) ایجاد سطح با کانال آلفا برای جلوگیری از گوشه‌های سیاه
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

    # (اصلاح شده) دیگر در هر فریم بلور نمی‌کنیم
    if notification_center_snapshot:
        # فقط آلفای تصویر از قبل بلور شده را بر اساس پیشرفت انیمیشن تنظیم می‌کنیم
        notification_center_snapshot.set_alpha(int(progress * 255))
        surface.blit(notification_center_snapshot, (0, 0))

    ease_progress = 1 - (1 - progress) ** 4
    start_width, start_height = 50, 50
    end_width, end_height = SCREEN_WIDTH - 20, SCREEN_HEIGHT - 100
    current_width = start_width + (end_width - start_width) * ease_progress
    current_height = start_height + (end_height - start_height) * ease_progress
    end_x, end_y = 10, 50
    start_x, start_y = 10, 10 # شروع از چپ
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
    card_width, card_height = SCREEN_WIDTH - 20, 80
    card_rect = pygame.Rect(10, notif['y_offset'], card_width, card_height)
    
    draw_notification_card(surface, card_rect, notif, alpha=notif['alpha'])

def draw_3d_effect_button(surface, base_rect, color, radius, button_data, container_rect):
    """
    (نسخه نهایی و اصلاح شده) یک دکمه با افکت سه‌بعدی و گوشه‌های گرد نرم رسم می‌کند.
    این نسخه با اصلاح ترتیب رأس‌های چندضلعی، مشکل نمایش دایره‌های گوشه را برطرف می‌کند.
    """
    if button_data['press_anim_progress'] < 0.01 or button_data['press_location'] is None:
        draw_rounded_rect(surface, base_rect, color, radius)
        return

    progress = button_data['press_anim_progress']
    click_pos_abs = pygame.Vector2(button_data['press_location'])
    click_pos_relative = click_pos_abs - pygame.Vector2(container_rect.topleft)
    rect_center = pygame.Vector2(base_rect.center)

    # (اصلاح شده) تعریف گوشه‌ها در یک لیست برای تضمین ترتیب
    corner_points = [
        pygame.Vector2(base_rect.topleft), pygame.Vector2(base_rect.topright),
        pygame.Vector2(base_rect.bottomright), pygame.Vector2(base_rect.bottomleft)
    ]
    corner_names = ['topleft', 'topright', 'bottomright', 'bottomleft']

    # پیدا کردن نزدیک‌ترین گوشه به محل کلیک
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

    # ۱. رسم چهار دایره در گوشه‌های تغییرشکل‌یافته
    for p in poly_points:
        pygame.draw.circle(surface, color, (int(p.x), int(p.y)), int(radius))

    # ۲. رسم دو چندضلعی متقاطع برای پوشاندن فضای بین دایره‌ها
    # (اصلاح شده) ترتیب صحیح رأس‌ها برای جلوگیری از پیچ‌خوردگی چندضلعی
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
    """ (جدید) این تابع یک صفحه عمومی برای برنامه‌های نصب شده از طریق .prs را رسم می‌کند """
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
        for name in sorted(os.listdir(path)):
            full_path = os.path.join(path, name)
            # از نمایش فایل‌های مخفی (که با . شروع می‌شوند) خودداری کن
            if name.startswith('.'):
                continue
            if os.path.isdir(full_path):
                items.append({'name': name, 'type': 'dir', 'path': full_path})
            else:
                ext = name.split('.')[-1].lower()
                if ext in ['txt', 'md']:
                    file_type = 'text'
                elif ext == 'prs':
                    file_type = 'app_package'
                elif ext in ['mp3', 'wav', 'ogg']:
                    file_type = 'music'
                elif ext in ['png', 'jpg', 'jpeg', 'bmp']:
                    file_type = 'image'
                else:
                    file_type = 'file'
                items.append({'name': name, 'type': file_type, 'path': full_path})
    except Exception as e:
        print(f"Error scanning directory {path}: {e}")
        items.append({'name': f"Error: {e}", 'type': 'error', 'path': ''})
    return items

# (جدید) تابع اصلی برای رسم صفحه برنامه فایل‌ها
def draw_files_app_screen(surface):
    global files_content_height, files_list, files_scroll_offset
    surface.fill(get_current_color('settings_bg'))
    text_color = get_current_color('settings_title')
    
    back_btn_text = render_persian_text("<", settings_title_font, BLUE)
    back_btn_rect = back_btn_text.get_rect(left=20, top=50)
    if files_current_path != '.':
        surface.blit(back_btn_text, back_btn_rect)
        if active_button_rect == back_btn_rect:
            surf = pygame.Surface(back_btn_rect.size, pygame.SRCALPHA); surf.fill((0,0,0,30)); surface.blit(surf, back_btn_rect.topleft)

    path_text = os.path.abspath(files_current_path).replace(os.path.abspath('.'), 'Root', 1)
    title = render_persian_text(path_text, text_font, text_color)
    surface.blit(title, title.get_rect(left=back_btn_rect.right + 15, centery=back_btn_rect.centery))
    
    files_scroll_offset += (target_files_scroll_offset - files_scroll_offset) * 0.2
    
    y_pos = 100; item_height = 50; padding = 10
    clickable_rects = {'back_btn': back_btn_rect}
    
    for i, item in enumerate(files_list):
        item_y = y_pos + i * (item_height + padding) - files_scroll_offset
        item_rect = pygame.Rect(padding, item_y, SCREEN_WIDTH - 2 * padding, item_height)
        
        if item_rect.bottom > 100 and item_rect.top < SCREEN_HEIGHT:
            draw_rounded_rect(surface, item_rect, get_current_color('settings_button_bg'), 10)
            
            icon_rect = pygame.Rect(item_rect.left + 10, item_rect.centery - 15, 30, 30)
            if item['type'] == 'dir':
                draw_rounded_rect(surface, icon_rect, (100, 150, 255), 5)
            elif item['type'] == 'app_package':
                draw_rounded_rect(surface, icon_rect, (80, 80, 200), 5) 
                pygame.draw.rect(surface, WHITE, icon_rect.inflate(-10, -10), border_radius=2)
            elif item['type'] == 'text':
                draw_rounded_rect(surface, icon_rect, (200, 200, 200), 5)
                pygame.draw.line(surface, GRAY, (icon_rect.left+5, icon_rect.top+8), (icon_rect.right-5, icon_rect.top+8), 2)
                pygame.draw.line(surface, GRAY, (icon_rect.left+5, icon_rect.top+15), (icon_rect.right-5, icon_rect.top+15), 2)
            elif item['type'] == 'music':
                draw_rounded_rect(surface, icon_rect, (255, 100, 100), 5)
            elif item['type'] == 'image':
                draw_rounded_rect(surface, icon_rect, (100, 220, 100), 5)
            else:
                draw_rounded_rect(surface, icon_rect, GRAY, 5)

            name_surf = render_persian_text(item['name'], text_font, text_color)
            surface.blit(name_surf, name_surf.get_rect(left=icon_rect.right + 15, centery=item_rect.centery))

        # (*** خط اصلاح شده ***)
        # item_rect از قبل موقعیت صحیح روی صفحه را دارد. نیازی به جابجایی (move) نیست.
        clickable_rects[f"item_{i}"] = item_rect

    files_content_height = len(files_list) * (item_height + padding)
    return clickable_rects

def draw_control_center(surface, progress, vertical_offset=0.0):
    """ (نسخه کاملاً بازطراحی شده) مرکز کنترل را شبیه به تصویر نمونه رسم می‌کند. """
    global cc_buttons # برای دسترسی به rect های اسلایدر
    
    if progress <= 0:
        return

    if control_center_snapshot:
        control_center_snapshot.set_alpha(int(progress * 255))
        surface.blit(control_center_snapshot, (0, 0))

    # انیمیشن باز شدن (مانند قبل)
    ease_progress = 1 - (1 - progress) ** 4
    start_width, start_height = 50, 50
    end_width, end_height = SCREEN_WIDTH - 20, SCREEN_HEIGHT - 100
    current_width = start_width + (end_width - start_width) * ease_progress
    current_height = start_height + (end_height - start_height) * ease_progress
    end_x, end_y = 10, 50
    start_x, start_y = SCREEN_WIDTH - start_width - 10, 10
    current_x = start_x + (end_x - start_x) * ease_progress
    current_y = start_y + (end_y - start_y) * ease_progress + vertical_offset

    cc_rect = pygame.Rect(current_x, current_y, current_width, current_height)

    # سطح اصلی CC با پس‌زمینه نیمه‌شفاف
    cc_surface = pygame.Surface(cc_rect.size, pygame.SRCALPHA)
    bg_color = (10, 10, 15, int(180 * progress)) if is_dark_mode else (250, 250, 255, int(180 * progress))
    # draw_rounded_rect(cc_surface, cc_surface.get_rect(), bg_color, 25)

    if ease_progress > 0.8:
        # آلفا برای محو شدن نرم محتوا
        content_alpha = (ease_progress - 0.8) / 0.2 * 255
        text_color = (*WHITE, content_alpha) if is_dark_mode else (*BLACK, content_alpha)
        sub_text_color = (*LIGHT_GRAY, content_alpha) if is_dark_mode else (*GRAY, content_alpha)

        widget_padding = 15
        current_y_pos = widget_padding

        # --- 1. دکمه‌های بزرگ (Wi-Fi & Data) ---
        top_widget_width = (current_width - widget_padding * 3) / 2
        top_widget_height = 80
        
        wifi_rect_base = pygame.Rect(widget_padding, current_y_pos, top_widget_width, top_widget_height)
        data_rect_base = pygame.Rect(wifi_rect_base.right + widget_padding, current_y_pos, top_widget_width, top_widget_height)
        
        # ذخیره Rect کلی برای تشخیص کلیک
        cc_buttons['wifi']['rect'] = wifi_rect_base.move(cc_rect.topleft)
        cc_buttons['data']['rect'] = data_rect_base.move(cc_rect.topleft)

        # رسم دکمه وای‌فای
        btn_wifi = cc_buttons['wifi']
        base_color = (50, 50, 60) if is_dark_mode else (220, 220, 225)
        active_color = (50, 150, 255)
        wifi_color = tuple(int(b + (a - b) * btn_wifi['color_progress']) for b, a in zip(base_color, active_color))
        final_wifi_color = (*wifi_color, int(content_alpha * 0.8))
        draw_rounded_rect(cc_surface, wifi_rect_base, final_wifi_color, 20)
        wifi_text_surf = render_persian_text(btn_wifi['label'], text_font, text_color)
        wifi_text_surf.set_alpha(content_alpha)
        cc_surface.blit(wifi_text_surf, wifi_text_surf.get_rect(left=wifi_rect_base.left + 15, top=wifi_rect_base.top + 15))

        # رسم دکمه داده
        btn_data = cc_buttons['data']
        data_color = tuple(int(b + (a - b) * btn_data['color_progress']) for b, a in zip(base_color, active_color))
        final_data_color = (*data_color, int(content_alpha * 0.8))
        draw_rounded_rect(cc_surface, data_rect_base, final_data_color, 20)
        data_text_surf = render_persian_text(btn_data['label'], text_font, text_color)
        data_text_surf.set_alpha(content_alpha)
        cc_surface.blit(data_text_surf, data_text_surf.get_rect(left=data_rect_base.left + 15, top=data_rect_base.top + 15))
        
        current_y_pos += top_widget_height + widget_padding

        # --- 2. ویجت مدیا پلیر (Placeholder) ---
        media_rect = pygame.Rect(widget_padding, current_y_pos, current_width - widget_padding*2, 80)
        media_color = (50, 50, 60, int(content_alpha * 0.8)) if is_dark_mode else (220, 220, 225, int(content_alpha * 0.8))
        draw_rounded_rect(cc_surface, media_rect, media_color, 20)
        
        media_text_surf = render_persian_text("No playback history", status_bar_font, sub_text_color)
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

        # --- 4. گرید دکمه‌های گرد ---
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
            
            if btn_rect.bottom < current_height - widget_padding: # فقط دکمه‌هایی که جا می‌شوند را رسم کن
                cc_buttons[btn_name]['rect'] = btn_rect.move(cc_rect.topleft)
                draw_cc_circular_toggle(cc_surface, btn_rect, cc_buttons[btn_name], sub_text_color, content_alpha)

    # رسم سطح نهایی CC روی صفحه اصلی
    surface.blit(cc_surface, cc_rect.topleft)
    
def draw_battery_icon_status_bar(surface, pos, battery_info, text_color):
    """
    (نسخه نهایی) آیکون باتری را با استفاده از متدهای استاندارد Pygame رسم می‌کند
    تا از اعوجاج در گوشه‌ها جلوگیری شود و ظاهر دقیقاً مشابه نمونه اولیه باشد.
    """
    if not battery_info:
        return

    percent = battery_info.percent
    is_charging = battery_info.power_plugged

    # ابعاد آیکون
    body_width, body_height = 28, 14
    tip_width, tip_height = 3, 6
    radius = 4

    # موقعیت‌ها
    body_rect = pygame.Rect(pos[0] - body_width, pos[1], body_width, body_height)
    tip_rect = pygame.Rect(body_rect.right, body_rect.centery - tip_height / 2, tip_width, tip_height)
    
    # رنگ پس‌زمینه آیکون (همرنگ متن نوار وضعیت)
    icon_bg_color = text_color
    
    # رنگ متن درصد (متضاد با پس‌زمینه)
    # اگر پس زمینه خیلی روشن است، متن را تیره کن و بالعکس
    if sum(icon_bg_color[:3]) > 382: # 255 * 3 / 2
        percent_text_color = (10, 10, 10)
    else:
        percent_text_color = (240, 240, 240)

    # رسم بدنه اصلی (پُر) با گوشه‌های گرد
    pygame.draw.rect(surface, icon_bg_color, body_rect, border_radius=radius)
    # رسم نوک باتری
    pygame.draw.rect(surface, icon_bg_color, tip_rect, border_top_right_radius=2, border_bottom_right_radius=2)

    # نمایش درصد داخل آیکون
    percent_text = str(percent)
    try:
        percent_font = pygame.font.Font("Vazir-Bold.ttf", 11)
    except FileNotFoundError:
        percent_font = pygame.font.Font(main_font_path, 10) if main_font_path else pygame.font.Font(None, 13)
    
    percent_surf = percent_font.render(percent_text, True, percent_text_color)
    # تنظیم دقیق موقعیت متن برای وسط‌چین شدن بهتر
    surface.blit(percent_surf, percent_surf.get_rect(center=body_rect.center))

    # اگر در حال شارژ است، یک آیکون صاعقه کنار آن نمایش داده می‌شود
    if is_charging:
        charge_font = pygame.font.Font(main_font_path, 14) if main_font_path else pygame.font.Font(None, 16)
        charge_surf = charge_font.render("⚡", True, text_color)
        surface.blit(charge_surf, charge_surf.get_rect(midright=(body_rect.left - 5, body_rect.centery)))
        
def draw_gallery_app_screen(surface):
    global gallery_content_height, target_gallery_scroll_offset, gallery_scroll_offset
    
    surface.fill(get_current_color('settings_bg'))
    title = render_persian_text("گالری", settings_title_font, get_current_color('settings_title'))
    surface.blit(title, title.get_rect(centerx=surface.get_width() / 2, top=50))

    # حرکت نرم اسکرول
    gallery_scroll_offset += (target_gallery_scroll_offset - gallery_scroll_offset) * 0.2
    
    # تنظیمات گرید
    cols = 3
    padding = 10
    thumb_container_size = (SCREEN_WIDTH - (cols + 1) * padding) / cols
    
    clickable_rects = {}
    x, y = padding, 100 - gallery_scroll_offset
    
    for i, photo in enumerate(gallery_photos):
        thumb = gallery_thumbnails.get(photo['path'])
        if thumb:
            # مرکز کردن تامبنیل در کانتینر
            thumb_rect = thumb.get_rect(center=(x + thumb_container_size / 2, y + thumb_container_size / 2))
            
            # فقط تامبنیل‌های قابل مشاهده را رسم کن
            if thumb_rect.bottom > 100 and thumb_rect.top < SCREEN_HEIGHT:
                surface.blit(thumb, thumb_rect)

            clickable_rects[f'photo_{i}'] = pygame.Rect(x, y + gallery_scroll_offset, thumb_container_size, thumb_container_size)

        x += thumb_container_size + padding
        if (i + 1) % cols == 0:
            x = padding
            y += thumb_container_size + padding
            
    gallery_content_height = y + gallery_scroll_offset - 100
    return clickable_rects


def draw_gallery_fullscreen_view(surface):
    # (اصلاح شده) با افزودن gallery_start_rect به این خط، خطا برطرف می‌شود
    global gallery_animation_progress, gallery_animation_direction, is_gallery_fullscreen, gallery_start_rect
    
    # بارگذاری تصویر با کیفیت اصلی فقط در صورت نیاز
    photo_data = gallery_photos[gallery_selected_index]
    if photo_data['image'] is None:
        try:
            photo_data['image'] = pygame.image.load(photo_data['path']).convert()
        except Exception as e:
            print(f"Error loading full image: {e}")
            return
    
    image = photo_data['image']

    # انیمیشن
    if gallery_animation_direction != 0:
        gallery_animation_progress += 0.06 * gallery_animation_direction
        gallery_animation_progress = max(0.0, min(1.0, gallery_animation_progress))

    ease_progress = (1 - math.cos(gallery_animation_progress * math.pi)) / 2
    
    # محو کردن پس‌زمینه
    bg_alpha = int(255 * ease_progress)
    bg_color = get_current_color('settings_bg')
    bg_surface = pygame.Surface(surface.get_size())
    bg_surface.fill(bg_color)
    bg_surface.set_alpha(bg_alpha)
    surface.blit(bg_surface, (0,0))
    
    # درون‌یابی (Interpolation) بین Rect شروع و پایان
    end_rect = image.get_rect(center=surface.get_rect().center)
    
    # اطمینان از اینکه gallery_start_rect مقدار دارد
    if gallery_start_rect is None:
        gallery_start_rect = end_rect 

    current_rect_vals = [s + (e - s) * ease_progress for s, e in zip(gallery_start_rect, end_rect)]
    current_rect = pygame.Rect(current_rect_vals)
    
    # تغییر اندازه نرم تصویر و رسم آن
    scaled_image = pygame.transform.smoothscale(image, current_rect.size)
    surface.blit(scaled_image, current_rect)
    
    # اگر انیمیشن تمام شد، جهت را صفر کن
    if (gallery_animation_direction == 1 and gallery_animation_progress >= 1.0) or \
       (gallery_animation_direction == -1 and gallery_animation_progress <= 0.0):
        if gallery_animation_direction == -1: # اگر انیمیشن بستن تمام شد
            is_gallery_fullscreen = False
        gallery_animation_direction = 0

def draw_low_battery_warning(surface):
    """
    (جدید) این تابع پیام هشدار کمبود باتری را با انیمیشن نرم رسم می‌کند.
    """
    card_height = 180
    # محاسبه پیشرفت انیمیشن با حالت نرم (ease-out)
    ease_progress = (1 - math.cos(low_battery_warning_progress * math.pi)) / 2
    # محاسبه موقعیت عمودی کارت بر اساس پیشرفت انیمیشن
    y_pos = SCREEN_HEIGHT - (card_height + 20) * ease_progress
    card_rect = pygame.Rect(20, y_pos, SCREEN_WIDTH - 40, card_height)

    # تعیین رنگ‌ها بر اساس حالت تاریک یا روشن
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

    # رسم دکمه‌ها
    understand_btn_rect = pygame.Rect(card_rect.left + 20, card_rect.bottom - 60, (card_rect.width - 60) / 2, 40)
    saver_btn_rect = pygame.Rect(understand_btn_rect.right + 20, card_rect.bottom - 60, (card_rect.width - 60) / 2, 40)
    draw_rounded_rect(surface, understand_btn_rect, understand_btn_bg, 15)
    draw_rounded_rect(surface, saver_btn_rect, saver_btn_bg, 15)

    understand_text_surf = render_persian_text("متوجه شدم", text_font, understand_text_color)
    saver_text_surf = render_persian_text("ذخیره باتری", text_font, WHITE)
    surface.blit(understand_text_surf, understand_text_surf.get_rect(center=understand_btn_rect.center))
    surface.blit(saver_text_surf, saver_text_surf.get_rect(center=saver_btn_rect.center))

    # بازگرداندن Rect دکمه‌ها برای بررسی کلیک
    return understand_btn_rect, saver_btn_rect

def draw_status_bar(color=WHITE, alpha=255):
    bar_height = 30
    final_color = (color[0], color[1], color[2], alpha)
    
    try:
        # رسم ساعت در سمت چپ
        time_surface = status_bar_font.render(datetime.datetime.now().strftime("%H:%M"), True, final_color)
        time_surface.set_alpha(alpha)
        screen.blit(time_surface, time_surface.get_rect(midleft=(15, bar_height / 2)))
        
        # رسم آیکون باتری در سمت راست
        battery_info = psutil.sensors_battery()
        if battery_info:
            # موقعیت گوشه بالا-راست آیکون
            icon_pos = (SCREEN_WIDTH - 15, bar_height / 2 - 7) 
            draw_battery_icon_status_bar(screen, icon_pos, battery_info, final_color)

    except (AttributeError, TypeError):
        # این خطا ممکن است در فریم‌های اولیه رخ دهد
        pass

def draw_home_indicator(color=WHITE):
    draw_rounded_rect(screen, pygame.Rect((SCREEN_WIDTH - 130) / 2, SCREEN_HEIGHT - 15, 130, 5), color, 2.5)

def draw_files_icon(surface, rect):
    # پس‌زمینه سفید
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
    # پس‌زمینه سفید مشابه آیکون‌های دیگر
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

    # (اصلاح شده) برای ویجت‌ها از ماسک با شعاع بیشتری استفاده می‌کنیم
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
    # رسم پس‌زمینه اصلی
    if current_lock_screen_wallpaper_image:
        screen.blit(current_lock_screen_wallpaper_image, (0, offset_y))
    else:
        draw_gradient_background(screen, (40, 0, 80), (10, 20, 100))
    
    # رسم ساعت و تاریخ
    now = datetime.datetime.now()
    if lock_screen_style == 'default':
        time_surf = clock_font.render("".join([persian_digits.get(c, c) for c in now.strftime("%H:%M")]), True, WHITE)
        screen.blit(time_surf, time_surf.get_rect(center=(SCREEN_WIDTH/2, SCREEN_HEIGHT/2 - 170 + offset_y)))
        date_surf = text_font.render(now.strftime("%A, %B %d"), True, WHITE)
        screen.blit(date_surf, date_surf.get_rect(center=(SCREEN_WIDTH/2, SCREEN_HEIGHT/2 - 100 + offset_y)))
    elif lock_screen_style == 'bottom_right':
        time_surf = clock_font.render("".join([persian_digits.get(c, c) for c in now.strftime("%H:%M")]), True, WHITE)
        time_rect = time_surf.get_rect(bottomright=(SCREEN_WIDTH - 30, SCREEN_HEIGHT - 80 + offset_y)); screen.blit(time_surf, time_rect)
        date_surf = text_font.render(now.strftime("%A, %B %d"), True, WHITE)
        screen.blit(date_surf, date_surf.get_rect(bottomright=(SCREEN_WIDTH - 30, time_rect.top - 5 + offset_y)))
    elif lock_screen_style == 'stacked':
        hour_surf = clock_font.render("".join([persian_digits.get(c, c) for c in now.strftime("%H")]), True, WHITE)
        minute_surf = clock_font.render("".join([persian_digits.get(c, c) for c in now.strftime("%M")]), True, WHITE)
        hour_rect = hour_surf.get_rect(center=(SCREEN_WIDTH/2, SCREEN_HEIGHT/2 - 100 + offset_y))
        minute_rect = minute_surf.get_rect(center=(SCREEN_WIDTH/2, hour_rect.bottom + offset_y))
        screen.blit(hour_surf, hour_rect); screen.blit(minute_surf, minute_rect)
        date_surf = text_font.render(now.strftime("%A, %B %d"), True, WHITE)
        screen.blit(date_surf, date_surf.get_rect(center=(SCREEN_WIDTH/2, minute_rect.bottom + 40 + offset_y)))

    # (جدید) رسم لایه سوژه برای جلوه عمق
    if is_depth_effect_enabled and current_lock_screen_subject_image:
        screen.blit(current_lock_screen_subject_image, (0, offset_y))

    swipe_text = render_persian_text("برای باز کردن، به بالا بکشید", text_font, LIGHT_GRAY)
    screen.blit(swipe_text, swipe_text.get_rect(center=(SCREEN_WIDTH/2, SCREEN_HEIGHT - 50 + offset_y)))


def draw_home_screen_content(surface, offset, scale=1.0, alpha=255, is_folder_view_active=False):
    surface.fill((0, 0, 0, 0))
    start_x = (SCREEN_WIDTH - (icons_per_row * icon_size + (icons_per_row - 1) * icon_padding)) / 2; start_y = 60

    # (اصلاح شده) اندازه فعلی آیکون را در ابتدای حلقه محاسبه می‌کنیم
    current_icon_base_size = int(icon_size * edit_mode_scale)
    size_diff = icon_size - current_icon_base_size

    icon_lists = [icons[page] for page in range(num_home_pages)] + [dock_icons]
    for container_idx, container in enumerate(icon_lists):
        is_dock = container_idx == len(icon_lists) - 1
        if is_dock:
            # (اصلاح شده) داک نمی‌تواند ویجت داشته باشد، پس محاسبات آن ساده است
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
            
            # (جدید) مرکز کردن ویجت‌ها بر اساس اندازه بزرگترشان
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
    # draw_main_background(screen) # <--- (حذف شد) این خط مشکل‌ساز بود
    
    # --- ساخت داک شیشه‌ای ---
    final_dock_surface = pygame.Surface(dock_rect.size, pygame.SRCALPHA)
    
    # 1. گرفتن تصویر پس‌زمینه زیر داک
    try:
        # (اصلاح شده) حالا این تابع پس‌زمینه‌ای را که در حلقه اصلی کشیده شده، ضبط می‌کند
        dock_bg_capture = screen.subsurface(dock_rect).copy()
    except ValueError:
        # Fallback در صورتی که داک خارج از صفحه باشد (مثلاً حین انیمیشن)
        dock_bg_capture = pygame.Surface(dock_rect.size)
        draw_main_background(dock_bg_capture)

    # 2. تار کردن تصویر گرفته شده (با ایترشن بیشتر برای تاری قوی‌تر)
    blurred_dock_bg = apply_gaussian_blur(dock_bg_capture, iterations=10, scale_factor=4) # (تغییر)
    final_dock_surface.blit(blurred_dock_bg, (0, 0))
    
    # 3. افزودن لایه نیمه‌شفاف برای خوانایی (افکت شیشه‌ای)
    overlay_color = (255, 255, 255, 60) if not is_dark_mode else (10, 10, 10, 60)
    draw_rounded_rect(final_dock_surface, final_dock_surface.get_rect(), overlay_color, 25)
    
    # 4. ایجاد ماسک نهایی برای گوشه‌های گرد
    mask = pygame.Surface(dock_rect.size, pygame.SRCALPHA)
    draw_rounded_rect(mask, mask.get_rect(), (255, 255, 255, 255), 25)
    final_dock_surface.blit(mask, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)
    
    # 5. رسم داک نهایی روی صفحه
    screen.blit(final_dock_surface, dock_rect.topleft)
    
    draw_home_indicator()


def draw_page_indicators(current_page, total_pages):
    indicator_radius, spacing = 4, 15; total_width = (total_pages - 1) * spacing
    start_x = (SCREEN_WIDTH - total_width) / 2; y_pos = SCREEN_HEIGHT - 110
    for i in range(total_pages):
        pygame.draw.circle(screen, WHITE if i == current_page else GRAY, (int(start_x + i * spacing), y_pos), indicator_radius)

def draw_settings_main_screen(surface):
    surface.fill(get_current_color('settings_bg'))
    title = render_persian_text("تنظیمات", settings_title_font, get_current_color('settings_title')); surface.blit(title, title.get_rect(centerx=surface.get_width()/2, top=50))
    btn_color, text_color = get_current_color('settings_button_bg'), get_current_color('settings_button_text')
    buttons_to_draw = [
        ("پس‌زمینه", pygame.Rect(30, 120, surface.get_width() - 60, 50), 'wallpaper_btn'),
        ("صفحه نمایش", pygame.Rect(30, 180, surface.get_width() - 60, 50), 'display_btn'),
        ("صفحه قفل", pygame.Rect(30, 240, surface.get_width() - 60, 50), 'lock_screen_btn'),
        ("درباره", pygame.Rect(30, 300, surface.get_width() - 60, 50), 'about_btn')
    ]
    clickable_rects = {}
    for text, rect, key in buttons_to_draw:
        draw_rounded_rect(surface, rect, btn_color, 10)
        if active_button_rect == rect:
            surf = pygame.Surface(rect.size, pygame.SRCALPHA); surf.fill((0,0,0,40)); surface.blit(surf, rect.topleft)
        btn_text = render_persian_text(text, text_font, text_color); surface.blit(btn_text, btn_text.get_rect(center=rect.center))
        clickable_rects[key] = rect
    return clickable_rects

def draw_settings_wallpaper_screen(surface):
    global wallpaper_preset_rects; wallpaper_preset_rects.clear()
    surface.fill(get_current_color('settings_bg')); text_color = get_current_color('settings_title')
    back_btn_text = render_persian_text("< بازگشت", text_font, BLUE); back_btn_rect = back_btn_text.get_rect(left=20, top=55); surface.blit(back_btn_text, back_btn_rect)
    title = render_persian_text("پس‌زمینه", settings_title_font, text_color); surface.blit(title, title.get_rect(centerx=surface.get_width()/2, top=50))
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
    custom_text = render_persian_text("انتخاب از فایل...", text_font, get_current_color('settings_button_text'))
    surface.blit(custom_text, custom_text.get_rect(center=custom_btn_rect.center))
    clickable_rects['custom_wallpaper_btn'] = custom_btn_rect
    if active_button_rect in [back_btn_rect, custom_btn_rect]:
        surf = pygame.Surface(active_button_rect.size, pygame.SRCALPHA); surf.fill((0,0,0,40)); surface.blit(surf, active_button_rect.topleft)
    return clickable_rects

def draw_settings_custom_wallpaper_screen(surface):
    surface.fill(get_current_color('settings_bg')); text_color = get_current_color('settings_title')
    back_btn_text = render_persian_text("< بازگشت", text_font, BLUE); back_btn_rect = back_btn_text.get_rect(left=20, top=55); surface.blit(back_btn_text, back_btn_rect)
    title = render_persian_text("انتخاب تصویر", settings_title_font, text_color); surface.blit(title, title.get_rect(centerx=surface.get_width()/2, top=50))
    y_pos = 120
    clickable_rects = {'back_btn': back_btn_rect}
    try:
        files = [f for f in os.listdir('wallpapers') if f.lower().endswith(('.png', '.jpg', '.jpeg', '.bmp'))]
        for filename in files:
            file_rect = pygame.Rect(30, y_pos, surface.get_width() - 60, 40)
            draw_rounded_rect(surface, file_rect, get_current_color('settings_button_bg'), 8)
            if active_file_item and active_file_item['rect'] == file_rect:
                surf = pygame.Surface(file_rect.size, pygame.SRCALPHA); surf.fill((0,0,0,40)); surface.blit(surf, file_rect.topleft)
            file_surf = text_font.render(filename, True, get_current_color('settings_button_text'))
            surface.blit(file_surf, file_surf.get_rect(centery=file_rect.centery, left=file_rect.left + 15))
            file_item = {'name': filename, 'rect': file_rect}
            clickable_rects[f'file_{filename}'] = file_rect
            y_pos += 50
    except FileNotFoundError:
        error_text = render_persian_text("پوشه wallpapers یافت نشد", text_font, text_color)
        surface.blit(error_text, error_text.get_rect(center=(surface.get_width()/2, 150)))
    if active_button_rect == back_btn_rect:
        surf = pygame.Surface(back_btn_rect.size, pygame.SRCALPHA); surf.fill((0,0,0,40)); surface.blit(surf, back_btn_rect.topleft)
    return clickable_rects


def draw_settings_display_screen(surface):
    surface.fill(get_current_color('settings_bg')); text_color = get_current_color('settings_title')
    back_btn_text = render_persian_text("< بازگشت", text_font, BLUE); back_btn_rect = back_btn_text.get_rect(left=20, top=55); surface.blit(back_btn_text, back_btn_rect)
    title = render_persian_text("صفحه نمایش", settings_title_font, text_color); surface.blit(title, title.get_rect(centerx=surface.get_width()/2, top=50))
    dark_mode_text = render_persian_text("حالت تاریک", text_font, text_color); surface.blit(dark_mode_text, (surface.get_width() - dark_mode_text.get_width() - 30, 130))
    switch_rect = pygame.Rect(30, 120, 60, 30); switch_radius = switch_rect.height / 2
    off_color = (200, 200, 200); on_color = BLUE
    switch_bg_color = tuple(int(off + (on - off) * dark_mode_switch_progress) for off, on in zip(off_color, on_color))
    draw_rounded_rect(surface, switch_rect, switch_bg_color, switch_radius)
    start_x = switch_rect.left + switch_radius; end_x = switch_rect.right - switch_radius
    circle_pos_x = start_x + (end_x - start_x) * dark_mode_switch_progress
    pygame.draw.circle(surface, WHITE, (circle_pos_x, switch_rect.centery), switch_radius - 4)
    if active_button_rect == back_btn_rect:
        surf = pygame.Surface(back_btn_rect.size, pygame.SRCALPHA); surf.fill((0,0,0,40)); surface.blit(surf, back_btn_rect.topleft)
    return {'back_btn': back_btn_rect, 'dark_mode_toggle': pygame.Rect(30, 120, surface.get_width() - 60, 50)}

# (اصلاح شده) صفحه تنظیمات قفل با گزینه‌های پس‌زمینه و جلوه عمق
def draw_settings_lock_screen_screen(surface):
    global lock_screen_preset_rects; lock_screen_preset_rects.clear()
    surface.fill(get_current_color('settings_bg')); text_color = get_current_color('settings_title')
    back_btn_text = render_persian_text("< بازگشت", text_font, BLUE); back_btn_rect = back_btn_text.get_rect(left=20, top=55); surface.blit(back_btn_text, back_btn_rect)
    title = render_persian_text("صفحه قفل", settings_title_font, text_color); surface.blit(title, title.get_rect(centerx=surface.get_width()/2, top=50))
    
    # رسم استایل‌های ساعت
    styles = ['default', 'bottom_right', 'stacked']; preview_width, preview_height = 100, 175
    total_width = (len(styles) * preview_width) + ((len(styles) - 1) * 20); start_x = (surface.get_width() - total_width) / 2; y_pos = 120
    preview_clock_font = pygame.font.Font(main_font_path, 28) if main_font_path else pygame.font.Font(None, 32)
    preview_date_font = pygame.font.Font(main_font_path, 10) if main_font_path else pygame.font.Font(None, 12)
    
    now = datetime.datetime.now()
    clickable_rects = {'back_btn': back_btn_rect}
    for i, style in enumerate(styles):
        rect = pygame.Rect(start_x + i * (preview_width + 20), y_pos, preview_width, preview_height)
        lock_screen_preset_rects.append(rect); clickable_rects[f'style_{style}'] = rect
        
        # رسم پس زمینه پیش نمایش
        preview_bg = pygame.Surface(rect.size, pygame.SRCALPHA)
        draw_gradient_background(preview_bg, (40, 0, 80), (10, 20, 100))
        
        # (اصلاح شده) رسم محتوای پیش‌نمایش‌ها
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
    
    # دکمه‌های انتخاب پس‌زمینه صفحه قفل
    btn_y_pos = y_pos + preview_height + 30
    custom_lock_bg_btn = pygame.Rect(30, btn_y_pos, surface.get_width() - 60, 50)
    default_lock_bg_btn = pygame.Rect(30, btn_y_pos + 60, surface.get_width() - 60, 50)
    
    draw_rounded_rect(surface, custom_lock_bg_btn, get_current_color('settings_button_bg'), 10)
    custom_text = render_persian_text("انتخاب پس‌زمینه قفل", text_font, get_current_color('settings_button_text'))
    surface.blit(custom_text, custom_text.get_rect(center=custom_lock_bg_btn.center))
    
    draw_rounded_rect(surface, default_lock_bg_btn, get_current_color('settings_button_bg'), 10)
    default_text = render_persian_text("استفاده از پیش‌فرض", text_font, get_current_color('settings_button_text'))
    surface.blit(default_text, default_text.get_rect(center=default_lock_bg_btn.center))
    
    clickable_rects['custom_lock_wallpaper_btn'] = custom_lock_bg_btn
    clickable_rects['default_lock_wallpaper_btn'] = default_lock_bg_btn

    # (جدید) گزینه سوییچی جلوه عمق
    depth_effect_y_pos = default_lock_bg_btn.bottom + 20
    # این گزینه فقط زمانی نمایش داده می‌شود که تصویر پس‌زمینه سفارشی باشد و کتابخانه‌های لازم نصب باشند
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
    surface.fill(get_current_color('settings_bg')); text_color = get_current_color('settings_title')
    back_btn_text = render_persian_text("< بازگشت", text_font, BLUE); back_btn_rect = back_btn_text.get_rect(left=20, top=55); surface.blit(back_btn_text, back_btn_rect)
    title = render_persian_text("پس‌زمینه صفحه قفل", settings_title_font, text_color); surface.blit(title, title.get_rect(centerx=surface.get_width()/2, top=50))
    y_pos = 120
    clickable_rects = {'back_btn': back_btn_rect}
    try:
        files = [f for f in os.listdir('wallpapers') if f.lower().endswith(('.png', '.jpg', '.jpeg', '.bmp'))]
        for filename in files:
            file_rect = pygame.Rect(30, y_pos, surface.get_width() - 60, 40)
            draw_rounded_rect(surface, file_rect, get_current_color('settings_button_bg'), 8)
            if active_file_item and active_file_item['rect'] == file_rect:
                surf = pygame.Surface(file_rect.size, pygame.SRCALPHA); surf.fill((0,0,0,40)); surface.blit(surf, file_rect.topleft)
            file_surf = text_font.render(filename, True, get_current_color('settings_button_text'))
            surface.blit(file_surf, file_surf.get_rect(centery=file_rect.centery, left=file_rect.left + 15))
            file_item = {'name': filename, 'rect': file_rect}
            clickable_rects[f'file_{filename}'] = file_rect
            y_pos += 50
    except FileNotFoundError:
        error_text = render_persian_text("پوشه wallpapers یافت نشد", text_font, text_color)
        surface.blit(error_text, error_text.get_rect(center=(surface.get_width()/2, 150)))
    if active_button_rect == back_btn_rect:
        surf = pygame.Surface(back_btn_rect.size, pygame.SRCALPHA); surf.fill((0,0,0,40)); surface.blit(surf, back_btn_rect.topleft)
    return clickable_rects

def draw_settings_about_screen(surface):
    draw_gradient_background(surface, HYPEROS_TOP, HYPEROS_BOTTOM)
    back_btn_text = render_persian_text("< بازگشت", text_font, WHITE); back_btn_rect = back_btn_text.get_rect(left=20, top=55); surface.blit(back_btn_text, back_btn_rect)
    title = render_persian_text("درباره", settings_title_font, WHITE); surface.blit(title, title.get_rect(centerx=surface.get_width()/2, top=50))
    os_name_surf = about_font.render("ParsOS", True, WHITE)
    surface.blit(os_name_surf, os_name_surf.get_rect(center=(surface.get_width()/2, surface.get_height()/2)))
    if active_button_rect == back_btn_rect:
        surf = pygame.Surface(back_btn_rect.size, pygame.SRCALPHA); surf.fill((0,0,0,40)); surface.blit(surf, back_btn_rect.topleft)
    return {'back_btn': back_btn_rect}

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
    paste_text = render_persian_text("جای‌گذاری", text_font, text_color)
    copy_rect = copy_text.get_rect(right=menu_rect.right - 15, top=menu_rect.top + 10)
    paste_rect = paste_text.get_rect(right=menu_rect.right - 15, top=copy_rect.bottom + 10)
    surface.blit(copy_text, copy_rect); surface.blit(paste_text, paste_rect)
    return {'copy': copy_rect, 'paste': paste_rect}

def draw_notes_app_screen(surface):
    global notes_text
    # (جدید) بررسی برای باز کردن فایل خاص از برنامه فایل‌ها
    file_path_to_open = app_context.get('file_path')
    if file_path_to_open and os.path.exists(file_path_to_open):
        try:
            with open(file_path_to_open, 'r', encoding='utf-8') as f:
                notes_text = f.read()
            # نام فایل را برای ذخیره‌سازی بعدی تنظیم کن
            notes_save_filename = os.path.basename(file_path_to_open)
            app_context['file_path'] = None # فقط یک بار فایل را باز کن
        except Exception as e:
            notes_text = f"خطا در باز کردن فایل:\n{e}"

    surface.fill(get_current_color('notes_bg'))
    
    text_surfaces = render_persian_text(notes_text, notes_font, get_current_color('notes_text'), is_note=True)
    btn_color, text_color = get_current_color('settings_button_bg'), get_current_color('settings_button_text')
    save_btn_rect, open_btn_rect = pygame.Rect(20, 45, 80, 35), pygame.Rect(110, 45, 80, 35)
    draw_rounded_rect(surface, save_btn_rect, btn_color, 8); draw_rounded_rect(surface, open_btn_rect, btn_color, 8)
    if active_button_rect == save_btn_rect:
        surf = pygame.Surface(save_btn_rect.size, pygame.SRCALPHA); surf.fill((0,0,0,40)); surface.blit(surf, save_btn_rect.topleft)
    if active_button_rect == open_btn_rect:
        surf = pygame.Surface(open_btn_rect.size, pygame.SRCALPHA); surf.fill((0,0,0,40)); surface.blit(surf, open_btn_rect.topleft)
    save_text = render_persian_text("ذخیره", text_font, text_color); open_text = render_persian_text("باز کردن", text_font, text_color)
    surface.blit(save_text, save_text.get_rect(center=save_btn_rect.center)); surface.blit(open_text, open_text.get_rect(center=open_btn_rect.center))
    y = 100; last_line_rect = None
    for line_surf in text_surfaces:
        x = SCREEN_WIDTH - line_surf.get_width() - 20; surface.blit(line_surf, (x, y))
        last_line_rect = pygame.Rect(x, y, line_surf.get_width(), line_surf.get_height()); y += line_surf.get_height()
    if cursor_visible:
        cursor_y = y - (last_line_rect.height if last_line_rect else notes_font.get_height())
        cursor_x = last_line_rect.left - 5 if last_line_rect and last_line_rect.width > 0 else SCREEN_WIDTH - 25
        pygame.draw.line(surface, get_current_color('notes_text'), (cursor_x, cursor_y), (cursor_x, cursor_y + notes_font.get_height()), 2)
    if is_notes_context_menu_open:
        draw_notes_context_menu(surface)
    return {'save_btn': save_btn_rect, 'open_btn': open_btn_rect}

def draw_notes_save_screen(surface):
    surface.fill(get_current_color('settings_bg')); text_color = get_current_color('settings_title')
    back_btn_text = render_persian_text("< بازگشت", text_font, BLUE); back_btn_rect = back_btn_text.get_rect(left=20, top=55); surface.blit(back_btn_text, back_btn_rect)
    title = render_persian_text("ذخیره یادداشت", settings_title_font, text_color); surface.blit(title, title.get_rect(centerx=surface.get_width()/2, top=50))
    input_box_rect = pygame.Rect(50, 150, surface.get_width() - 100, 40); pygame.draw.rect(surface, get_current_color('settings_button_bg'), input_box_rect, border_radius=8)
    pygame.draw.rect(surface, BLUE, input_box_rect, 2, border_radius=8)
    filename_surf = render_persian_text(notes_save_filename, text_font, get_current_color('settings_button_text'))
    surface.blit(filename_surf, filename_surf.get_rect(centery=input_box_rect.centery, right=input_box_rect.right - 10))
    confirm_save_btn = pygame.Rect(surface.get_width()/2 - 50, 220, 100, 40); draw_rounded_rect(surface, confirm_save_btn, BLUE, 10)
    save_text = render_persian_text("ذخیره", text_font, WHITE); surface.blit(save_text, save_text.get_rect(center=confirm_save_btn.center))
    if active_button_rect == back_btn_rect:
        surf = pygame.Surface(back_btn_rect.size, pygame.SRCALPHA); surf.fill((0,0,0,40)); surface.blit(surf, back_btn_rect.topleft)
    if active_button_rect == confirm_save_btn:
        surf = pygame.Surface(confirm_save_btn.size, pygame.SRCALPHA); surf.fill((0,0,0,40)); surface.blit(surf, confirm_save_btn.topleft)
    return {'back_btn': back_btn_rect, 'confirm_btn': confirm_save_btn, 'input_box': input_box_rect}

def draw_notes_open_screen(surface):
    global notes_file_list
    surface.fill(get_current_color('settings_bg')); text_color = get_current_color('settings_title')
    back_btn_text = render_persian_text("< بازگشت", text_font, BLUE); back_btn_rect = back_btn_text.get_rect(left=20, top=55); surface.blit(back_btn_text, back_btn_rect)
    title = render_persian_text("باز کردن یادداشت", settings_title_font, text_color); surface.blit(title, title.get_rect(centerx=surface.get_width()/2, top=50))
    notes_file_list.clear(); y_pos = 120
    clickable_rects = {'back_btn': back_btn_rect}
    try:
        files = [f for f in os.listdir('notes') if f.endswith('.txt')]
        for filename in files:
            file_rect = pygame.Rect(30, y_pos, surface.get_width() - 60, 40)
            draw_rounded_rect(surface, file_rect, get_current_color('settings_button_bg'), 8)
            if active_file_item and active_file_item['rect'] == file_rect:
                surf = pygame.Surface(file_rect.size, pygame.SRCALPHA); surf.fill((0,0,0,40)); surface.blit(surf, file_rect.topleft)
            file_surf = render_persian_text(filename, text_font, get_current_color('settings_button_text'))
            surface.blit(file_surf, file_surf.get_rect(centery=file_rect.centery, right=file_rect.right - 15))
            file_item = {'name': filename, 'rect': file_rect}
            notes_file_list.append(file_item)
            clickable_rects[f'file_{filename}'] = file_rect
            y_pos += 50
    except FileNotFoundError:
        error_text = render_persian_text("پوشه notes یافت نشد", text_font, text_color)
        surface.blit(error_text, error_text.get_rect(center=(surface.get_width()/2, 150)))
    if active_button_rect == back_btn_rect:
        surf = pygame.Surface(back_btn_rect.size, pygame.SRCALPHA); surf.fill((0,0,0,40)); surface.blit(surf, back_btn_rect.topleft)
    return clickable_rects

def format_time(seconds):
    if seconds < 0: seconds = 0
    mins = int(seconds // 60)
    secs = int(seconds % 60)
    return f"{mins:02d}:{secs:02d}"

def draw_music_app_screen(surface):
    global is_music_playing, is_music_paused, music_track_name, current_track_length, current_album_art_surface, music_playback_start_time_offset, current_track_index
    # (جدید) بررسی برای پخش فایل خاص از برنامه فایل‌ها
    file_path_to_play = app_context.get('file_path')
    if file_path_to_play and os.path.exists(file_path_to_play):
        try:
            # اگر این آهنگ در پلی‌لیست وجود دارد، به آن برو
            if file_path_to_play in music_playlist:
                current_track_index = music_playlist.index(file_path_to_play)
            else: # در غیر این صورت، آن را به ابتدای پلی‌لیست اضافه کن
                music_playlist.insert(0, file_path_to_play)
                current_track_index = 0

            pygame.mixer.music.load(music_playlist[current_track_index])
            current_track_length, current_album_art_surface = get_track_info(music_playlist[current_track_index])
            music_track_name = os.path.basename(music_playlist[current_track_index])
            pygame.mixer.music.play()
            is_music_playing, is_music_paused = True, False
            music_playback_start_time_offset = 0
            
            app_context['file_path'] = None # فقط یک بار آهنگ را پخش کن
        except Exception as e:
            music_track_name = "خطا در پخش فایل"
            print(f"Error playing music file: {e}")

    surface.fill(get_current_color('music_bg'))
    text_color = get_current_color('music_text')
    
    # ... (بقیه کدهای رسم برنامه موسیقی بدون تغییر باقی می‌ماند) ...
    cover_art_rect = pygame.Rect(0, 0, 250, 250); cover_art_rect.center = (surface.get_width() / 2, 200)
    if current_album_art_surface:
        draw_rounded_rect(surface, cover_art_rect.inflate(10, 10), (100, 100, 100, 50), 25)
        scaled_art = pygame.transform.smoothscale(current_album_art_surface, cover_art_rect.size)
        art_surf_final = pygame.Surface(cover_art_rect.size, pygame.SRCALPHA)
        draw_rounded_rect(art_surf_final, art_surf_final.get_rect(), (255, 255, 255), 20)
        art_surf_final.blit(scaled_art, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)
        surface.blit(art_surf_final, cover_art_rect.topleft)
    else:
        draw_rounded_rect(surface, cover_art_rect, (100,100,100), 20)
        music_icon_surf = pygame.Surface((100, 100), pygame.SRCALPHA); draw_music_icon(music_icon_surf, music_icon_surf.get_rect())
        surface.blit(music_icon_surf, music_icon_surf.get_rect(center=cover_art_rect.center))
    track_surf = render_persian_text(music_track_name, music_font, text_color)
    surface.blit(track_surf, track_surf.get_rect(center=(surface.get_width()/2, 380)))
    seek_bar_y = 440
    seek_bar_rect = pygame.Rect(50, seek_bar_y, surface.get_width() - 100, 8)
    draw_rounded_rect(surface, seek_bar_rect, (180, 180, 180), 4)
    progress = 0
    current_time_seconds = 0
    if is_scrubbing_music:
        progress = music_scrub_progress
        current_time_seconds = progress * current_track_length
    elif is_music_playing or is_music_paused:
        if current_track_length > 0:
            current_pos_ms = pygame.mixer.music.get_pos()
            current_time_seconds = music_playback_start_time_offset + (current_pos_ms / 1000.0)
            progress = current_time_seconds / current_track_length
    progress = max(0, min(1, progress))
    progress_rect = pygame.Rect(seek_bar_rect.x, seek_bar_rect.y, seek_bar_rect.width * progress, seek_bar_rect.height)
    draw_rounded_rect(surface, progress_rect, BLUE, 4)
    handle_pos_x = seek_bar_rect.x + seek_bar_rect.width * progress
    pygame.draw.circle(surface, BLUE, (handle_pos_x, seek_bar_rect.centery), 8)
    pygame.draw.circle(surface, WHITE, (handle_pos_x, seek_bar_rect.centery), 5)
    current_time_str = format_time(current_time_seconds)
    total_time_str = format_time(current_track_length)
    current_time_surf = music_time_font.render(current_time_str, True, text_color)
    total_time_surf = music_time_font.render(total_time_str, True, text_color)
    surface.blit(current_time_surf, current_time_surf.get_rect(right=seek_bar_rect.left - 10, centery=seek_bar_rect.centery))
    surface.blit(total_time_surf, total_time_surf.get_rect(left=seek_bar_rect.right + 10, centery=seek_bar_rect.centery))
    
    btn_bg_color = get_current_color('settings_button_bg')
    
    play_pause_btn_rect = pygame.Rect(0, 0, 70, 70); play_pause_btn_rect.center = (surface.get_width()/2, 520)
    pygame.draw.circle(surface, btn_bg_color, play_pause_btn_rect.center, 35)
    if is_music_playing:
        bar_width, bar_height, corner_radius = 8, 24, 3
        pause_bar1 = pygame.Rect(play_pause_btn_rect.centerx - 12, play_pause_btn_rect.centery - 12, bar_width, bar_height)
        pause_bar2 = pygame.Rect(play_pause_btn_rect.centerx + 4, play_pause_btn_rect.centery - 12, bar_width, bar_height)
        draw_rounded_rect(surface, pause_bar1, text_color, corner_radius); draw_rounded_rect(surface, pause_bar2, text_color, corner_radius)
    else:
        center = pygame.Vector2(play_pause_btn_rect.center)
        size = 15
        p1 = (center.x + size * 0.7, center.y)
        p2 = (center.x - size * 0.5, center.y - size * 0.8)
        p3 = (center.x - size * 0.5, center.y + size * 0.8)
        pygame.draw.polygon(surface, text_color, [p1, p2, p3])
        pygame.draw.circle(surface, text_color, p1, 3); pygame.draw.circle(surface, text_color, p2, 3); pygame.draw.circle(surface, text_color, p3, 3)

    next_btn_rect = pygame.Rect(0, 0, 50, 50)
    next_btn_rect.center = (play_pause_btn_rect.centerx + 80, play_pause_btn_rect.centery)
    pygame.draw.circle(surface, btn_bg_color, next_btn_rect.center, 25)
    p1 = (next_btn_rect.centerx - 5, next_btn_rect.centery - 10)
    p2 = (next_btn_rect.centerx - 5, next_btn_rect.centery + 10)
    p3 = (next_btn_rect.centerx + 5, next_btn_rect.centery)
    pygame.draw.polygon(surface, text_color, [p1,p2,p3])
    pygame.draw.rect(surface, text_color, (next_btn_rect.centerx + 5, next_btn_rect.centery - 10, 4, 20))
    
    prev_btn_rect = pygame.Rect(0, 0, 50, 50)
    prev_btn_rect.center = (play_pause_btn_rect.centerx - 80, play_pause_btn_rect.centery)
    pygame.draw.circle(surface, btn_bg_color, prev_btn_rect.center, 25)
    p1 = (prev_btn_rect.centerx + 5, prev_btn_rect.centery - 10)
    p2 = (prev_btn_rect.centerx + 5, prev_btn_rect.centery + 10)
    p3 = (prev_btn_rect.centerx - 5, prev_btn_rect.centery)
    pygame.draw.polygon(surface, text_color, [p1,p2,p3])
    pygame.draw.rect(surface, text_color, (prev_btn_rect.centerx - 9, prev_btn_rect.centery - 10, 4, 20))

    seek_bar_clickable_rect = seek_bar_rect.inflate(0, 20)
    return {'play_pause_btn': play_pause_btn_rect, 'seek_bar': seek_bar_clickable_rect, 'next_btn': next_btn_rect, 'prev_btn': prev_btn_rect}

def draw_browser_app_screen(surface):
    surface.fill(get_current_color('browser_bg'))
    text_color = get_current_color('settings_title')
    
    # دکمه‌های بازگشت و جلو
    back_btn_rect = pygame.Rect(10, 50, 40, 40)
    forward_btn_rect = pygame.Rect(back_btn_rect.right + 5, 50, 40, 40)
    url_bar_rect = pygame.Rect(forward_btn_rect.right + 5, 50, SCREEN_WIDTH - 180, 40)
    go_btn_rect = pygame.Rect(url_bar_rect.right + 5, 50, 55, 40)
    
    # رسم دکمه بازگشت
    back_is_active = browser_history_index > 0
    back_color = BLUE if back_is_active else GRAY
    draw_rounded_rect(surface, back_btn_rect, get_current_color('settings_button_bg'), 8)
    back_text = text_font.render("<", True, back_color)
    surface.blit(back_text, back_text.get_rect(center=back_btn_rect.center))

    # رسم دکمه جلو
    forward_is_active = browser_history_index < len(browser_history) - 1
    forward_color = BLUE if forward_is_active else GRAY
    draw_rounded_rect(surface, forward_btn_rect, get_current_color('settings_button_bg'), 8)
    forward_text = text_font.render(">", True, forward_color)
    surface.blit(forward_text, forward_text.get_rect(center=forward_btn_rect.center))
    
    # نوار URL و دکمه "برو"
    draw_rounded_rect(surface, url_bar_rect, get_current_color('settings_button_bg'), 8)
    if is_url_input_active: pygame.draw.rect(surface, BLUE, url_bar_rect, 2, border_radius=8)
    url_text_surf = text_font.render(browser_url_input, True, text_color)
    surface.blit(url_text_surf, url_text_surf.get_rect(centery=url_bar_rect.centery, left=url_bar_rect.left + 10), pygame.Rect(0, 0, url_bar_rect.width - 20, url_bar_rect.height))
    draw_rounded_rect(surface, go_btn_rect, BLUE, 8)
    go_text_surf = render_persian_text("برو", text_font, WHITE)
    surface.blit(go_text_surf, go_text_surf.get_rect(center=go_btn_rect.center))

    clickable_rects = {'back_btn': back_btn_rect, 'forward_btn': forward_btn_rect, 'url_bar': url_bar_rect, 'go_btn': go_btn_rect, 'links': {}}
    content_area_rect = pygame.Rect(10, 100, SCREEN_WIDTH - 20, SCREEN_HEIGHT - 120)

    # نمایش نشانگر بارگذاری
    if browser_is_loading:
        loading_text = render_persian_text("در حال بارگذاری...", settings_title_font, text_color)
        surface.blit(loading_text, loading_text.get_rect(center=content_area_rect.center))
    elif browser_content_height > 0:
        y = 0
        for item in browser_content_surfaces:
            line_surf = item['surface']
            draw_y = content_area_rect.top + y - browser_scroll_offset
            x_pos = content_area_rect.centerx - line_surf.get_width()/2 if item.get('type') == 'image' else content_area_rect.left + 10
            
            if draw_y + line_surf.get_height() > content_area_rect.top and draw_y < content_area_rect.bottom:
                surface.blit(line_surf, (x_pos, draw_y))
                if item.get('href'):
                    link_rect = pygame.Rect(x_pos, draw_y, line_surf.get_width(), line_surf.get_height())
                    # (اصلاح شده) تبدیل Rect به tuple برای استفاده به عنوان کلید دیکشنری
                    link_key = (link_rect.x, link_rect.y, link_rect.w, link_rect.h)
                    clickable_rects['links'][link_key] = item['href']
            
            y += line_surf.get_height()
            if item.get('type') == 'image': y += 10 # فاصله بعد از تصویر

    # رسم اسکرول بار
    if browser_content_height > content_area_rect.height:
        scrollbar_area_rect = pygame.Rect(content_area_rect.right - 8, content_area_rect.top, 8, content_area_rect.height)
        handle_height = max(20, (content_area_rect.height / browser_content_height) * content_area_rect.height)
        scroll_ratio = browser_scroll_offset / (browser_content_height - content_area_rect.height) if (browser_content_height - content_area_rect.height) > 0 else 0
        handle_y = scrollbar_area_rect.top + scroll_ratio * (scrollbar_area_rect.height - handle_height)
        scrollbar_handle_rect = pygame.Rect(scrollbar_area_rect.left, handle_y, 8, handle_height)
        draw_rounded_rect(surface, scrollbar_handle_rect, GRAY, 4)

    return clickable_rects


def draw_app_screen():
    global app_screen_animation_direction, app_screen_animation_progress, app_context, app_surfaces
    main_app_surface = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT))
    app_name, app_page = app_context.get('app_name'), app_context.get('screen')
    
    # (جدید) بررسی و اجرای منطق رسم برای برنامه‌های خارجی
    if app_context.get('is_external_app'):
        app_id = app_context.get('app_id')
        app_instance = running_app_instances.get(app_id)
        if app_instance:
            app_instance.draw(main_app_surface)
        else:
            # اگر به هر دلیلی نمونه برنامه وجود نداشت، یک صفحه خطا نمایش بده
            draw_installed_app_screen(main_app_surface)
    else:
        # اجرای تابع رسم مخصوص برنامه‌های داخلی سیستم عامل
        if app_name == 'settings':
            if app_page == 'main': draw_settings_main_screen(main_app_surface)
            elif app_page == 'wallpaper': draw_settings_wallpaper_screen(main_app_surface)
            elif app_page == 'display': draw_settings_display_screen(main_app_surface)
            elif app_page == 'lock_screen': draw_settings_lock_screen_screen(main_app_surface)
            elif app_page == 'custom_wallpaper': draw_settings_custom_wallpaper_screen(main_app_surface)
            elif app_page == 'custom_lock_wallpaper': draw_settings_custom_lock_wallpaper_screen(main_app_surface)
            elif app_page == 'about': draw_settings_about_screen(main_app_surface)
        elif app_name == 'notes':
            if app_page == 'notes_main': draw_notes_app_screen(main_app_surface)
            elif app_page == 'notes_save': draw_notes_save_screen(main_app_surface)
            elif app_page == 'notes_open': draw_notes_open_screen(main_app_surface)
        elif app_name == 'music': draw_music_app_screen(main_app_surface)
        elif app_name == 'browser': draw_browser_app_screen(main_app_surface)
        elif app_name == 'files':
            draw_files_app_screen(main_app_surface)
        elif app_name == 'gallery': draw_gallery_app_screen(main_app_surface)

    # ذخیره یک کپی از صفحه برنامه برای استفاده در منوی برنامه‌های اخیر
    if app_name:
        # کلید دیکشنری را شناسه برنامه قرار می‌دهیم تا منحصر به فرد باشد
        app_key = app_context.get('app_id', app_name)
        app_surfaces[app_key] = main_app_surface.copy()

    # مدیریت انیمیشن جابجایی بین صفحات داخلی یک برنامه
    if app_screen_animation_direction != 0:
        app_screen_animation_progress += 0.05
        if app_screen_animation_progress >= 1.0:
            app_screen_animation_progress, app_screen_animation_direction = 0, 0
            if app_context.get('animation_callback'): app_context['animation_callback'](); app_context['animation_callback'] = None
        progress = (1 - math.cos(app_screen_animation_progress * math.pi)) / 2
        old_surface = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT))
        if app_context.get('old_screen_draw_func'): app_context['old_screen_draw_func'](old_surface)
        x_offset_old = int(SCREEN_WIDTH * progress * app_screen_animation_direction); x_offset_new = x_offset_old - SCREEN_WIDTH * app_screen_animation_direction
        screen.blit(old_surface, (x_offset_old, 0)); screen.blit(main_app_surface, (x_offset_new, 0))
    else: screen.blit(main_app_surface, (0, 0))
    
    # این عناصر همیشه در بالای صفحه برنامه رسم می‌شوند
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
    # (اصلاح شده) استفاده از منحنی ایزینگ قوی‌تر برای شروع سریع و پایان نرم انیمیشن
    ease_progress = 1 - (1 - recents_animation_progress) ** 4
    
    if recents_view_blurred_bg is not None:
        recents_view_blurred_bg.set_alpha(int(255 * ease_progress))
        screen.blit(recents_view_blurred_bg, (0, 0))

    y_offset_anim = (1.0 - ease_progress) * SCREEN_HEIGHT
    
    # حرکت نرم به سمت کارت هدف
    recents_focused_index += (target_recents_focused_index - recents_focused_index) * 0.15

    card_width, card_height = 280, 500
    
    # رسم کارت‌ها از آخر به اول تا روی هم به درستی قرار گیرند
    for i in range(len(recents_apps_list) - 1, -1, -1):
        app = recents_apps_list[i]
        
        # محاسبه فاصله کارت از کارت مرکزی (در حال فوکوس)
        distance = i - recents_focused_index
        
        # کارت‌هایی که خیلی دور هستند را رسم نکن
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

        # ماسک برای گوشه‌های گرد
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
            
            # کارت به سمت بالا حرکت کرده و محو می‌شود
            y_offset = -ease_progress * 300
            alpha = 255 * (1 - ease_progress)
            
            # از Rect ذخیره شده قبلی برای موقعیت اولیه استفاده می‌کنیم
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

            # ماسک گوشه‌های گرد
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

add_main_notification("تنظیمات", "وای فای متصل شد", "به شبکه خانگی متصل شدید.", icon_name="settings")

while running:
    mouse_pos = pygame.mouse.get_pos()
    events = pygame.event.get()
    kernel.kernel_instance.update()
    for event in events:
        if event.type == pygame.QUIT: running = False
        if event.type == MUSIC_ENDED: play_next_song()

        if current_screen == "app_open" and app_context.get('is_external_app'):
            app_instance = running_app_instances.get(app_context['app_id'])
            if app_instance:
                app_instance.handle_event(event)

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
                
                # بررسی کلیک روی دکمه‌ها
                for btn_name, btn_data in cc_buttons.items():
                    if btn_data.get('rect') and btn_data['rect'].collidepoint(event.pos):
                        btn_data['is_pressed'] = True
                        if btn_data.get('type') == 'large': # دکمه‌های بزرگ افکت فشاری دارند
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
                            # (اختیاری) می‌توانید اینجا منطق واقعی را اضافه کنید
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
                is_control_center_open = True
                is_dragging_control_center = False
                snapshot = screen.copy()
                control_center_snapshot = apply_gaussian_blur(snapshot, iterations=15)
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
                    app_context = {'app_name': app_name, 'screen': 'main'}
                    if app_name in ['notes', 'music', 'browser', 'gallery', 'files']: app_context['screen'] = f"{app_name}_main"
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
                        if app_name in ['notes', 'music', 'browser', 'files', 'gallery']: app_context['screen'] = f"{app_name}_main"
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
                        if app_name == 'files': files_current_path, files_list, target_files_scroll_offset, files_scroll_offset = '.', scan_directory('.'), 0.0, 0.0
                        app_context = {'app_name': app_name, 'screen': 'main'}
                        if app_name in ['notes', 'music', 'browser', 'files', 'gallery']: app_context['screen'] = f"{app_name}_main"
                        if selected_icon.get('app_id'):
                            app_context['app_id'] = selected_icon.get('app_id')
                            app_context['is_external_app'] = True
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

            if app_name == 'gallery':
                if is_gallery_fullscreen:
                    if event.type == pygame.MOUSEBUTTONUP and event.button == 1 and gallery_animation_direction == 0:
                        gallery_animation_direction = -1; cols, padding = 3, 10; thumb_size = (SCREEN_WIDTH - (cols + 1) * padding) / cols
                        row, col = divmod(gallery_selected_index, cols)
                        x, y_base = padding + col * (thumb_size + padding), 100 + row * (thumb_size + padding)
                        y_on_screen = y_base - gallery_scroll_offset
                        gallery_start_rect = pygame.Rect(x, y_on_screen, thumb_size, thumb_size)
                else:
                    if event.type == pygame.MOUSEWHEEL:
                        target_gallery_scroll_offset -= event.y * 30; max_scroll = max(0, gallery_content_height - (SCREEN_HEIGHT - 100))
                        target_gallery_scroll_offset = max(0, min(target_gallery_scroll_offset, max_scroll))
                    if event.type == pygame.MOUSEBUTTONUP and event.button == 1:
                        temp_surface_for_buttons = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
                        original_offset, gallery_scroll_offset = gallery_scroll_offset, target_gallery_scroll_offset
                        buttons = draw_gallery_app_screen(temp_surface_for_buttons)
                        gallery_scroll_offset = original_offset
                        for key, rect in buttons.items():
                            if key.startswith('photo_') and rect.collidepoint(event.pos):
                                gallery_selected_index = int(key.split('_')[1]); is_gallery_fullscreen = True
                                gallery_animation_direction, gallery_start_rect = 1, rect; break

            if app_name in ['notes', 'browser'] and event.type == pygame.KEYDOWN:
                target_text, is_active = "", False
                if app_page == 'notes_main': target_text, is_active = notes_text, True
                elif app_page == 'notes_save': target_text, is_active = notes_save_filename, True
                elif app_name == 'browser' and is_url_input_active: target_text, is_active = browser_url_input, True
                if is_active:
                    if event.key == pygame.K_BACKSPACE: target_text = target_text[:-1]
                    elif event.key == pygame.K_RETURN and app_page == 'notes_main': target_text += '\n'
                    elif event.key != pygame.K_RETURN: target_text += event.unicode
                    if app_page == 'notes_main': notes_text = target_text
                    elif app_page == 'notes_save': notes_save_filename = target_text
                    elif app_name == 'browser': browser_url_input = target_text

            if event.type == pygame.MOUSEWHEEL and app_name in ['browser', 'files']:
                if app_name == 'browser':
                    browser_scroll_offset -= event.y * 30; max_scroll = max(0, browser_content_height - (SCREEN_HEIGHT - 120))
                    browser_scroll_offset = max(0, min(browser_scroll_offset, max_scroll))
                elif app_name == 'files':
                    target_files_scroll_offset -= event.y * 30; max_scroll = max(0, files_content_height - (SCREEN_HEIGHT - 100))
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
                    temp_surf = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT)); buttons = {}
                    if app_name == 'settings':
                        if app_page == 'main': buttons = draw_settings_main_screen(temp_surf)
                        elif app_page == 'wallpaper': buttons = draw_settings_wallpaper_screen(temp_surf)
                        elif app_page == 'display': buttons = draw_settings_display_screen(temp_surf)
                        elif app_page == 'lock_screen': buttons = draw_settings_lock_screen_screen(temp_surf)
                        elif app_page == 'custom_wallpaper': buttons = draw_settings_custom_wallpaper_screen(temp_surf)
                        elif app_page == 'custom_lock_wallpaper': buttons = draw_settings_custom_lock_wallpaper_screen(temp_surf)
                        elif app_page == 'about': buttons = draw_settings_about_screen(temp_surf)
                    elif app_name == 'notes':
                        if app_page == 'notes_main': buttons = draw_notes_app_screen(temp_surf)
                        elif app_page == 'notes_save': buttons = draw_notes_save_screen(temp_surf)
                        elif app_page == 'notes_open':
                            buttons = draw_notes_open_screen(temp_surf)
                            for file_item in notes_file_list:
                                if file_item['rect'].collidepoint(event.pos): active_file_item = file_item; break
                    elif app_name == 'music':
                        buttons = draw_music_app_screen(temp_surf)
                        if buttons['seek_bar'].collidepoint(event.pos):
                            is_scrubbing_music = True; seek_bar_rect = pygame.Rect(50, 440, SCREEN_WIDTH - 100, 8)
                            click_x = event.pos[0] - seek_bar_rect.x
                            music_scrub_progress = max(0, min(1, click_x / seek_bar_rect.width))
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
                    url_to_load = None
                    if (active_button_key == 'go_btn' and active_button_rect.collidepoint(event.pos)) or active_button_key == 'link_clicked':
                        from urllib.parse import quote_plus
                        query = browser_url_input.strip()
                        is_url = '.' in query and ' ' not in query and not query.startswith('?')
                        url_to_load = query if is_url else f"https://www.google.com/search?q={quote_plus(query)}"
                        if not browser_history or url_to_load != browser_history[browser_history_index]:
                            browser_history = browser_history[:browser_history_index+1]
                            browser_history.append(url_to_load)
                            browser_history_index += 1
                    elif active_button_key == 'back_btn' and browser_history_index > 0:
                        browser_history_index -= 1
                        url_to_load = browser_history[browser_history_index]
                    elif active_button_key == 'forward_btn' and browser_history_index < len(browser_history) - 1:
                        browser_history_index += 1
                        url_to_load = browser_history[browser_history_index]

                    if url_to_load and not browser_is_loading:
                        browser_url_input = url_to_load
                        browser_is_loading = True
                        result_key = f"browser_{time.time()}"
                        thread = threading.Thread(target=fetch_web_page_thread, args=(url_to_load, result_key))
                        thread.start()
                        app_context['browser_thread_key'] = result_key
                        is_url_input_active = False

                if active_button_key and active_button_rect and active_button_rect.collidepoint(event.pos):
                    if app_name == 'files':
                        if active_button_key == 'back_btn' and files_current_path != '.':
                            files_current_path = os.path.dirname(files_current_path); files_list = scan_directory(files_current_path)
                            target_files_scroll_offset, files_scroll_offset = 0.0, 0.0
                        elif active_button_key.startswith('item_'):
                            item_index = int(active_button_key.split('_')[1]); clicked_item = files_list[item_index]
                            if clicked_item['type'] == 'dir':
                                files_current_path = clicked_item['path']; files_list = scan_directory(files_current_path)
                                target_files_scroll_offset, files_scroll_offset = 0.0, 0.0
                            elif clicked_item['type'] == 'app_package':
                                install_prs_app(clicked_item['path']); files_list = scan_directory(files_current_path)
                            else:
                                target_app = None
                                if clicked_item['type'] == 'text': target_app = 'notes'
                                elif clicked_item['type'] == 'music': target_app = 'music'
                                elif clicked_item['type'] == 'image': print("Opening images from Files app is not fully supported yet.")
                                if target_app:
                                    app_screen_animation_direction = 1
                                    def set_new_app_context(app=target_app, path=clicked_item['path']):
                                        app_context.update({'app_name': app, 'screen': f"{app}_main", 'file_path': path})
                                    app_context.update({'old_screen_draw_func': draw_files_app_screen, 'animation_callback': set_new_app_context})
                    if app_name == 'settings':
                        if app_page == 'main':
                            if active_button_key == 'wallpaper_btn': app_screen_animation_direction = 1; app_context.update({'old_screen_draw_func': draw_settings_main_screen, 'animation_callback': lambda: app_context.update({'screen': 'wallpaper'})})
                            elif active_button_key == 'display_btn': app_screen_animation_direction = 1; app_context.update({'old_screen_draw_func': draw_settings_main_screen, 'animation_callback': lambda: app_context.update({'screen': 'display'})})
                            elif active_button_key == 'lock_screen_btn': app_screen_animation_direction = 1; app_context.update({'old_screen_draw_func': draw_settings_main_screen, 'animation_callback': lambda: app_context.update({'screen': 'lock_screen'})})
                            elif active_button_key == 'about_btn': app_screen_animation_direction = 1; app_context.update({'old_screen_draw_func': draw_settings_main_screen, 'animation_callback': lambda: app_context.update({'screen': 'about'})})
                        elif app_page in ['wallpaper', 'display', 'lock_screen', 'custom_wallpaper', 'custom_lock_wallpaper', 'about']:
                            old_func_name = f'draw_settings_{app_page}_screen'; target_screen = 'main'
                            if app_page == 'custom_wallpaper': target_screen = 'wallpaper'
                            if app_page == 'custom_lock_wallpaper': target_screen = 'lock_screen'
                            if active_button_key == 'back_btn': app_screen_animation_direction = -1; app_context.update({'old_screen_draw_func': globals()[old_func_name], 'animation_callback': lambda: app_context.update({'screen': target_screen})})
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
                            elif app_page == 'lock_screen':
                                if active_button_key.startswith('style_'): lock_screen_style = active_button_key.split('_')[1]; save_settings()
                                elif active_button_key == 'custom_lock_wallpaper_btn': app_screen_animation_direction = 1; app_context.update({'old_screen_draw_func': draw_settings_lock_screen_screen, 'animation_callback': lambda: app_context.update({'screen': 'custom_lock_wallpaper'})})
                                elif active_button_key == 'default_lock_wallpaper_btn':
                                    current_lock_screen_wallpaper_image, lock_screen_wallpaper_path, current_lock_screen_subject_image, is_depth_effect_enabled = None, None, None, False; save_settings()
                                elif active_button_key == 'depth_effect_toggle':
                                    is_depth_effect_enabled = not is_depth_effect_enabled
                                    if is_depth_effect_enabled: process_depth_effect_image(current_lock_screen_wallpaper_image)
                                    save_settings()
                    elif app_name == 'notes':
                        if app_page == 'notes_main':
                            if active_button_key == 'save_btn': app_screen_animation_direction = 1; app_context.update({'old_screen_draw_func': draw_notes_app_screen, 'animation_callback': lambda: app_context.update({'screen': 'notes_save'})})
                            elif active_button_key == 'open_btn': app_screen_animation_direction = 1; app_context.update({'old_screen_draw_func': draw_notes_app_screen, 'animation_callback': lambda: app_context.update({'screen': 'notes_open'})})
                        elif app_page == 'notes_save':
                            if active_button_key == 'back_btn': app_screen_animation_direction = -1; app_context.update({'old_screen_draw_func': draw_notes_save_screen, 'animation_callback': lambda: app_context.update({'screen': 'notes_main'})})
                            elif active_button_key == 'confirm_btn':
                                try:
                                    with open(os.path.join('notes', notes_save_filename), 'w', encoding='utf-8') as f: f.write(notes_text)
                                    app_screen_animation_direction = -1; app_context.update({'old_screen_draw_func': draw_notes_save_screen, 'animation_callback': lambda: app_context.update({'screen': 'notes_main'})})
                                except IOError as e: print(f"Error saving file: {e}")
                        elif app_page == 'notes_open':
                            if active_button_key == 'back_btn': app_screen_animation_direction = -1; app_context.update({'old_screen_draw_func': draw_notes_open_screen, 'animation_callback': lambda: app_context.update({'screen': 'notes_main'})})
                            elif active_file_item:
                                try:
                                    with open(os.path.join('notes', active_file_item['name']), 'r', encoding='utf-8') as f: notes_text = f.read()
                                    app_screen_animation_direction = -1; app_context.update({'old_screen_draw_func': draw_notes_open_screen, 'animation_callback': lambda: app_context.update({'screen': 'notes_main'})})
                                except IOError as e: print(f"Error opening file: {e}")
                    elif app_name == 'music':
                        if active_button_key == 'play_pause_btn':
                            if music_playlist:
                                if is_music_playing: pygame.mixer.music.pause(); is_music_paused, is_music_playing = True, False
                                elif is_music_paused: pygame.mixer.music.unpause(); is_music_paused, is_music_playing = False, True
                                else: pygame.mixer.music.play(); music_playback_start_time_offset = 0; is_music_playing, is_music_paused = True, False
                        elif active_button_key == 'next_btn': play_next_song()
                        elif active_button_key == 'prev_btn': play_previous_song()
                active_button_rect, active_button_key, active_file_item = None, None, None

            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1 and event.pos[1] > SCREEN_HEIGHT - 40:
                 is_swiping_app_close, app_swipe_start_pos = True, event.pos
                 app_swipe_interactive_progress = 0.0

    # --------------------------
    #      منطق و به‌روزرسانی وضعیت
    # --------------------------
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

            browser_scroll_offset, is_url_input_active = 0, False
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

    if is_control_center_open and control_center_progress < 1.0: control_center_progress = min(1.0, control_center_progress + 0.06)
    elif not is_control_center_open and control_center_progress > 0.0:
        control_center_progress = max(0.0, control_center_progress - 0.06)
        if control_center_progress <= 0.0: control_center_snapshot = None

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

    # (اصلاح شده) به‌روزرسانی انیمیشن دکمه‌های CC
    for btn_name, btn_data in cc_buttons.items():
        # (جدید) از دکمه‌هایی که وضعیت فعال/غیرفعال ندارند (مانند اسلایدرها) بگذر
        if 'is_active' not in btn_data:
            continue

        if 'scale_progress' in btn_data: # دکمه‌های بزرگ
            scale_target = 1.0 if btn_data['is_pressed'] else 0.0; btn_data['scale_progress'] += (scale_target - btn_data['scale_progress']) * 0.25
            press_target = 1.0 if btn_data['is_pressed'] else 0.0
            btn_data['press_anim_progress'] += (press_target - btn_data['press_anim_progress']) * 0.3
        
        # (جدید) مقداردهی اولیه color_progress برای دکمه‌های دایره‌ای در صورت عدم وجود
        # این کار از KeyError جلوگیری می‌کند
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
        
        # ۱. اول آیکون‌ها روی صفحه رسم می‌شوند
        content_surface, content_rect = draw_home_screen_content(home_screen_surface, home_page_offset, is_folder_view_active=is_folder_active)
        if is_folder_active:
            blur_surface = pygame.Surface(content_surface.get_size(), pygame.SRCALPHA); blur_surface.fill((0,0,0, blur_alpha)); content_surface.blit(blur_surface, (0,0))
        screen.blit(content_surface, content_rect)
        
        # ۲. حالا داک فراخوانی می‌شود و از آیکون‌های زیرینش عکس گرفته و آن‌ها را تار می‌کند
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
        draw_main_background(screen)
        if current_screen == "app_opening": app_animation_progress += 0.04
        else: app_animation_progress -= 0.04
        app_animation_progress = max(0.0, min(1.0, app_animation_progress))

        # (تغییر) استفاده از Quartic ease-out برای انیمیشن نرم‌تر
        progress = ease_out_cubic(app_animation_progress)

        home_scale, home_alpha = 1.0 - 0.1 * progress, 255 * (1 - progress)
        if home_alpha > 0:
            draw_home_screen_static_elements()
            indicator_surface = pygame.Surface((130, 5), pygame.SRCALPHA)
            draw_rounded_rect(indicator_surface, indicator_surface.get_rect(), (255, 255, 255, int(255 * (1 - progress))), 2.5)
            screen.blit(indicator_surface, ((SCREEN_WIDTH - 130) / 2, SCREEN_HEIGHT - 15))
            content_surface, content_rect = draw_home_screen_content(home_screen_surface, 0, scale=home_scale, alpha=home_alpha); screen.blit(content_surface, content_rect)

        start_rect = opened_app_icon_rect
        end_rect = screen.get_rect()

        current_center_x = start_rect.centerx + (end_rect.centerx - start_rect.centerx) * progress
        current_center_y = start_rect.centery + (end_rect.centery - start_rect.centery) * progress
        current_width = start_rect.width + (end_rect.width - start_rect.width) * progress
        current_height = start_rect.height + (end_rect.height - start_rect.height) * progress
        
        current_rect = pygame.Rect(0, 0, current_width, current_height)
        current_rect.center = (current_center_x, current_center_y)

        current_radius = 20 * (1 - progress)
        anim_surface = pygame.Surface(current_rect.size, pygame.SRCALPHA)
        
        app_name = app_context.get('app_name')
        if app_context.get('is_external_app'): app_open_bg_key = 'settings_bg'
        else: app_open_bg_key = 'gallery_bg' if app_name == 'gallery' else 'files_bg' if app_name == 'files' else 'notes_bg' if app_name == 'notes' else 'music_bg' if app_name == 'music' else 'browser_bg' if app_name == 'browser' else 'settings_bg'
        draw_rounded_rect(anim_surface, anim_surface.get_rect(), get_current_color(app_open_bg_key), current_radius)
        
        screen.blit(anim_surface, current_rect.topleft)
        draw_status_bar()
        
        if current_screen == "app_opening" and app_animation_progress >= 1.0:
            current_screen = "app_open"; app_name = app_context.get('app_name')

            # (جدید) ثبت فرآیند در کرنل
            app_id = app_context.get('app_id', app_name) # از app_id استفاده کن اگر وجود دارد
            kernel.kernel_instance.register_process(app_id, app_name)
            
            if app_context.get('is_external_app'):
                app_id = app_context['app_id']
                if app_id not in running_app_instances:
                    try:
                        app_path = os.path.join('installed_apps', app_id)
                        manifest_path = os.path.join(app_path, 'manifest.json')
                        with open(manifest_path, 'r', encoding='utf-8') as f: manifest = json.load(f)
                        main_file = manifest.get('main_file', 'main.py'); main_class_name = manifest.get('main_class'); module_path = os.path.join(app_path, main_file)
                        spec = importlib.util.spec_from_file_location(f"installed_apps.{app_id}.main", module_path)
                        app_module = importlib.util.module_from_spec(spec); spec.loader.exec_module(app_module)
                        AppClass = getattr(app_module, main_class_name)
                        running_app_instances[app_id] = AppClass(app_id, app_name, app_path)
                    except Exception as e:
                        print(f"ERROR: Could not load external app '{app_id}': {e}")
                        running_app_instances[app_id] = ParsOS_App(app_id, f"Error: {app_name}", app_path)
            existing_app = next((item for item in recents_apps_list if item.get('name') == app_name and item.get('app_id') == app_context.get('app_id')), None)
            if existing_app: recents_apps_list.remove(existing_app)
            new_recent = {'name': app_name}
            if app_context.get('app_id'): new_recent['app_id'] = app_context.get('app_id')
            recents_apps_list.insert(0, new_recent);
            if len(recents_apps_list) > 10: recents_apps_list.pop()

        elif current_screen == "app_closing" and app_animation_progress <= 0.0:
            closed_app_name = app_context.get('app_name')
            app_id = app_context.get('app_id', closed_app_name)
            kernel.kernel_instance.terminate_process(app_id)
            for app in recents_apps_list:
                if app['name'] == closed_app_name: app['snapshot'] = app_surfaces.get(app_context.get('app_id', closed_app_name)); break
            if app_context.get('is_external_app') and app_context.get('app_id') in running_app_instances:
                del running_app_instances[app_context.get('app_id')]
            target_icon = None
            def find_icon(name, container):
                for icon in container:
                    if icon['type'] == 'app' and icon['name'] == name: return icon
                    if icon['type'] == 'folder':
                        found = find_icon(name, icon['contains']);
                        if found: return found
                return None
            for page in icons:
                target_icon = find_icon(closed_app_name, page);
                if target_icon: break
            if not target_icon: target_icon = find_icon(closed_app_name, dock_icons)
            if target_icon:
                if closed_app_name == 'settings': animating_icon, is_icon_animation_active, icon_animation_progress = target_icon, True, 0.0
                elif closed_app_name == 'notes': animating_notes_icon, is_notes_icon_animation_active, notes_icon_animation_progress = target_icon, True, 0.0; save_notes()
                elif closed_app_name == 'music':
                    animating_music_icon, is_music_icon_animation_active, music_icon_animation_progress = target_icon, True, 0.0
                    pygame.mixer.music.set_endevent(); pygame.mixer.music.stop(); is_music_playing, is_music_paused = False, False
                elif closed_app_name == 'browser': animating_browser_icon, is_browser_icon_animation_active, browser_icon_animation_progress = target_icon, True, 0.0
            current_screen, app_close_timestamp = "home", time.time()

    elif current_screen == "app_open":
        if is_swiping_app_close or is_returning_app_to_open:
            draw_main_background(screen)
            progress = app_swipe_interactive_progress
            home_scale, home_alpha = 1.0 - 0.15 * progress, 255 * progress
            draw_home_screen_static_elements()
            indicator_surface = pygame.Surface((130, 5), pygame.SRCALPHA)
            draw_rounded_rect(indicator_surface, indicator_surface.get_rect(), (255, 255, 255, int(255 * progress)), 2.5)
            screen.blit(indicator_surface, ((SCREEN_WIDTH - 130) / 2, SCREEN_HEIGHT - 15))
            content_surface, content_rect = draw_home_screen_content(home_screen_surface, 0, scale=home_scale, alpha=home_alpha); screen.blit(content_surface, content_rect)
            
            start_rect = opened_app_icon_rect
            end_rect = screen.get_rect()
            anim_progress_from_open = 1.0 - progress
            
            current_center_x = start_rect.centerx + (end_rect.centerx - start_rect.centerx) * anim_progress_from_open
            current_center_y = start_rect.centery + (end_rect.centery - start_rect.centery) * anim_progress_from_open
            current_width = start_rect.width + (end_rect.width - start_rect.width) * anim_progress_from_open
            current_height = start_rect.height + (end_rect.height - start_rect.height) * anim_progress_from_open
            current_rect = pygame.Rect(0, 0, current_width, current_height)
            current_rect.center = (current_center_x, current_center_y)

            current_radius = 20 * progress
            anim_surface = pygame.Surface(current_rect.size, pygame.SRCALPHA)
            
            app_name = app_context.get('app_name')
            if app_context.get('is_external_app'): app_open_bg_key = 'settings_bg'
            else: app_open_bg_key = 'gallery_bg' if app_name == 'gallery' else 'files_bg' if app_name == 'files' else 'notes_bg' if app_name == 'notes' else 'music_bg' if app_name == 'music' else 'browser_bg' if app_name == 'browser' else 'settings_bg'
            draw_rounded_rect(anim_surface, anim_surface.get_rect(), get_current_color(app_open_bg_key), current_radius)
            
            screen.blit(anim_surface, current_rect.topleft)
            draw_status_bar()
        else:
            draw_app_screen()

    if app_context.get('app_name') == 'gallery' and is_gallery_fullscreen: draw_gallery_fullscreen_view(screen)
    if opened_folder is not None: draw_folder_view()

    if notification_center_progress > 0: draw_notification_center(screen, notification_center_progress)
    if control_center_progress > 0: draw_control_center(screen, control_center_progress, cc_vertical_offset) # <--- (اصلاح شده) حالا CC جدید را رسم می‌کند

    if is_charging_animation_active: draw_charging_animation()
    if low_battery_warning_progress > 0: draw_low_battery_warning(screen)

    draw_heads_up_notification(screen)
    draw_unimportant_notifications(screen)

    pygame.display.flip()
    clock.tick(90)

save_layout(); save_settings(); save_notes()
pygame.quit(); sys.exit()

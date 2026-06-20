# apps/notes.py

import pygame
import os
import time


class NotesApp:

    def __init__(
        self,
        sc_func,
        mf_func,
        get_color_func,
        render_text_func
    ):

        self.sc = sc_func
        self.mf = mf_func
        self.get_current_color = get_color_func
        self.render_persian_text = render_text_func

        # =====================================================
        # متن
        # =====================================================

        self.notes_text = ""
        self.last_notes_text = ""

        # =====================================================
        # فایل
        # =====================================================

        self.notes_save_filename = "یادداشت جدید.txt"

        # =====================================================
        # کش
        # =====================================================

        self.text_surfaces_cache = []
        self.cache_dirty = True

        # =====================================================
        # اسکرول
        # =====================================================

        self.scroll_offset = 0.0
        self.target_scroll_offset = 0.0

        # =====================================================
        # کرسر
        # =====================================================

        self.notes_cursor_index = 0
        self.cursor_line_index = 0
        self.cursor_x_in_line = 0

        # =====================================================
        # شمارنده
        # =====================================================

        self.notes_word_count = 0
        self.notes_char_count = 0

        # =====================================================
        # تایپ
        # =====================================================

        self.notes_last_type_time = 0.0

        # =====================================================
        # ذخیره خودکار
        # =====================================================

        self.last_save_time = 0

        # =====================================================
        # کلیپ‌بورد
        # =====================================================

        self.clipboard_text = ""

        # =====================================================
        # منوی راست کلیک
        # =====================================================

        self.is_notes_context_menu_open = False
        self.notes_context_menu_pos = (0, 0)

        # =====================================================
        # کلیک‌ها
        # =====================================================

        self.last_clickable_rects = {}

        # =====================================================
        # لود
        # =====================================================

        self.load_notes_on_startup()

    # =========================================================
    # متن فارسی
    # =========================================================

    def make_text_surface(self, text, font, color):

        return self.render_persian_text(
            text,
            font,
            color
        )

    # =========================================================
    # بارگذاری
    # =========================================================

    def load_notes_on_startup(self):

        try:

            with open(
                "notes.txt",
                "r",
                encoding="utf-8"
            ) as f:

                self.notes_text = f.read()

        except:

            self.notes_text = (
                "به برنامه یادداشت پارس‌او‌اس خوش آمدید.\n"
                "اینجا بنویسید..."
            )

        self.notes_cursor_index = len(
            self.notes_text
        )

        self.cache_dirty = True

    # =========================================================
    # ذخیره خودکار
    # =========================================================

    def save_auto_notes(self):

        try:

            with open(
                "notes.txt",
                "w",
                encoding="utf-8"
            ) as f:

                f.write(self.notes_text)

        except Exception as e:

            print(
                "Auto Save Error:",
                e
            )

    # =========================================================
    # ذخیره فایل
    # =========================================================

    def save_to_custom_file(self):

        try:

            if not os.path.exists("notes"):
                os.makedirs("notes")

            filepath = os.path.join(
                "notes",
                self.notes_save_filename
            )

            with open(
                filepath,
                "w",
                encoding="utf-8"
            ) as f:

                f.write(self.notes_text)

            return True

        except Exception as e:

            print(
                "Save Error:",
                e
            )

            return False

    # =========================================================
    # آپدیت کش
    # =========================================================

    def update_counts_and_cache(
        self,
        max_width
    ):

        if not self.cache_dirty:
            return

        self.notes_char_count = len(
            self.notes_text
        )

        self.notes_word_count = len([
            w for w in self.notes_text.split()
            if w.strip()
        ])

        self.text_surfaces_cache = []

        font = self.mf(18)

        lines = self.notes_text.split('\n')

        accumulated_chars = 0

        self.cursor_line_index = 0
        self.cursor_x_in_line = 0

        line_index = 0

        for line in lines:

            if line == "":

                self.text_surfaces_cache.append({
                    'text': '',
                    'surface': None,
                    'y': line_index * self.sc(28)
                })

                line_index += 1
                accumulated_chars += 1

                continue

            words = line.split(" ")

            current_line = ""

            for word in words:

                test_line = (
                    current_line + " " + word
                    if current_line
                    else word
                )

                rendered = self.make_text_surface(
                    test_line,
                    font,
                    self.get_current_color(
                        'text_main'
                    )
                )

                if rendered.get_width() <= max_width:

                    current_line = test_line

                else:

                    surf = self.make_text_surface(
                        current_line,
                        font,
                        self.get_current_color(
                            'text_main'
                        )
                    )

                    self.text_surfaces_cache.append({
                        'text': current_line,
                        'surface': surf,
                        'y': line_index * self.sc(28)
                    })

                    line_len = len(current_line)

                    if (
                        accumulated_chars + line_len
                        >= self.notes_cursor_index
                    ):

                        self.cursor_line_index = line_index

                        local_index = (
                            self.notes_cursor_index
                            - accumulated_chars
                        )

                        sub_text = current_line[
                            :local_index
                        ]

                        sub_render = self.make_text_surface(
                            sub_text,
                            font,
                            self.get_current_color(
                                'text_main'
                            )
                        )

                        self.cursor_x_in_line = (
                            sub_render.get_width()
                        )

                    accumulated_chars += (
                        line_len + 1
                    )

                    line_index += 1

                    current_line = word

            if current_line:

                surf = self.make_text_surface(
                    current_line,
                    font,
                    self.get_current_color(
                        'text_main'
                    )
                )

                self.text_surfaces_cache.append({
                    'text': current_line,
                    'surface': surf,
                    'y': line_index * self.sc(28)
                })

                line_len = len(current_line)

                if (
                    accumulated_chars + line_len
                    >= self.notes_cursor_index
                ):

                    self.cursor_line_index = line_index

                    local_index = (
                        self.notes_cursor_index
                        - accumulated_chars
                    )

                    sub_text = current_line[
                        :local_index
                    ]

                    sub_render = self.make_text_surface(
                        sub_text,
                        font,
                        self.get_current_color(
                            'text_main'
                        )
                    )

                    self.cursor_x_in_line = (
                        sub_render.get_width()
                    )

                accumulated_chars += (
                    line_len + 1
                )

                line_index += 1

        self.cache_dirty = False

    # =========================================================
    # رویدادها
    # =========================================================

    def handle_event(
        self,
        event,
        app_context
    ):

        # =====================================================
        # اسکرول
        # =====================================================

        if event.type == pygame.MOUSEWHEEL:

            total_height = (
                len(self.text_surfaces_cache)
                * self.sc(28)
            )

            visible_height = (
                app_context.get(
                    'height',
                    600
                )
                - self.sc(120)
            )

            max_scroll = max(
                0,
                total_height - visible_height
            )

            self.target_scroll_offset = max(
                0,
                min(
                    max_scroll,
                    self.target_scroll_offset
                    - (
                        event.y
                        * self.sc(45)
                    )
                )
            )

            return True

        # =====================================================
        # کلیک
        # =====================================================

        if event.type == pygame.MOUSEBUTTONDOWN:

            # -------------------------------------------------
            # راست کلیک
            # -------------------------------------------------

            if event.button == 3:

                self.is_notes_context_menu_open = True

                self.notes_context_menu_pos = (
                    event.pos
                )

                return True

            # -------------------------------------------------
            # چپ کلیک
            # -------------------------------------------------

            if event.button == 1:

                if self.is_notes_context_menu_open:

                    mx, my = (
                        self.notes_context_menu_pos
                    )

                    copy_rect = pygame.Rect(
                        mx,
                        my,
                        self.sc(120),
                        self.sc(35)
                    )

                    paste_rect = pygame.Rect(
                        mx,
                        my + self.sc(35),
                        self.sc(120),
                        self.sc(35)
                    )

                    if copy_rect.collidepoint(
                        event.pos
                    ):

                        self.clipboard_text = (
                            self.notes_text
                        )

                        try:

                            pygame.scrap.init()

                            pygame.scrap.put(
                                pygame.SCRAP_TEXT,
                                self.notes_text.encode(
                                    'utf-8'
                                )
                            )

                        except:
                            pass

                        self.is_notes_context_menu_open = False

                        return True

                    elif paste_rect.collidepoint(
                        event.pos
                    ):

                        text_to_paste = (
                            self.clipboard_text
                        )

                        try:

                            pygame.scrap.init()

                            sys_text = (
                                pygame.scrap.get(
                                    pygame.SCRAP_TEXT
                                )
                            )

                            if sys_text:

                                text_to_paste = (
                                    sys_text.decode(
                                        'utf-8'
                                    ).strip('\x00')
                                )

                        except:
                            pass

                        ci = self.notes_cursor_index

                        self.notes_text = (
                            self.notes_text[:ci]
                            + text_to_paste
                            + self.notes_text[ci:]
                        )

                        self.notes_cursor_index += len(
                            text_to_paste
                        )

                        self.cache_dirty = True

                        self.is_notes_context_menu_open = False

                        return True

                    else:

                        self.is_notes_context_menu_open = False

                for action, rect in self.last_clickable_rects.items():

                    if rect.collidepoint(
                        event.pos
                    ):

                        if action == 'notes_save_page_trigger':

                            self.save_to_custom_file()

                            return True

        # =====================================================
        # کیبورد
        # =====================================================

        if event.type == pygame.KEYDOWN:

            self.notes_last_type_time = (
                time.time()
            )

            ci = self.notes_cursor_index

            # -------------------------------------------------
            # بک اسپیس
            # -------------------------------------------------

            if event.key == pygame.K_BACKSPACE:

                if ci > 0:

                    self.notes_text = (
                        self.notes_text[:ci - 1]
                        + self.notes_text[ci:]
                    )

                    self.notes_cursor_index -= 1

                    self.cache_dirty = True

                return True

            # -------------------------------------------------
            # اینتر
            # -------------------------------------------------

            elif event.key == pygame.K_RETURN:

                self.notes_text = (
                    self.notes_text[:ci]
                    + '\n'
                    + self.notes_text[ci:]
                )

                self.notes_cursor_index += 1

                self.cache_dirty = True

                return True

            # -------------------------------------------------
            # چپ
            # -------------------------------------------------

            elif event.key == pygame.K_LEFT:

                if self.notes_cursor_index > 0:

                    self.notes_cursor_index -= 1

                return True

            # -------------------------------------------------
            # راست
            # -------------------------------------------------

            elif event.key == pygame.K_RIGHT:

                if (
                    self.notes_cursor_index
                    < len(self.notes_text)
                ):

                    self.notes_cursor_index += 1

                return True

            # -------------------------------------------------
            # Ctrl + C
            # -------------------------------------------------

            elif (
                event.key == pygame.K_c
                and (
                    pygame.key.get_mods()
                    & pygame.KMOD_CTRL
                )
            ):

                self.clipboard_text = (
                    self.notes_text
                )

                try:

                    pygame.scrap.init()

                    pygame.scrap.put(
                        pygame.SCRAP_TEXT,
                        self.notes_text.encode(
                            'utf-8'
                        )
                    )

                except:
                    pass

                return True

            # -------------------------------------------------
            # Ctrl + V
            # -------------------------------------------------

            elif (
                event.key == pygame.K_v
                and (
                    pygame.key.get_mods()
                    & pygame.KMOD_CTRL
                )
            ):

                text_to_paste = (
                    self.clipboard_text
                )

                try:

                    pygame.scrap.init()

                    sys_text = pygame.scrap.get(
                        pygame.SCRAP_TEXT
                    )

                    if sys_text:

                        text_to_paste = (
                            sys_text.decode(
                                'utf-8'
                            ).strip('\x00')
                        )

                except:
                    pass

                self.notes_text = (
                    self.notes_text[:ci]
                    + text_to_paste
                    + self.notes_text[ci:]
                )

                self.notes_cursor_index += len(
                    text_to_paste
                )

                self.cache_dirty = True

                return True

            # -------------------------------------------------
            # تایپ
            # -------------------------------------------------

            elif (
                event.unicode
                and event.key not in [
                    pygame.K_ESCAPE,
                    pygame.K_TAB
                ]
            ):

                self.notes_text = (
                    self.notes_text[:ci]
                    + event.unicode
                    + self.notes_text[ci:]
                )

                self.notes_cursor_index += len(
                    event.unicode
                )

                self.cache_dirty = True

                return True

        return False

    # =========================================================
    # رسم
    # =========================================================

    def draw(
        self,
        surface,
        w,
        h,
        app_context
    ):

        clickable_rects = {}

        # =====================================================
        # ذخیره خودکار
        # =====================================================

        if (
            time.time()
            - self.last_save_time
            > 3
        ):

            self.save_auto_notes()

            self.last_save_time = (
                time.time()
            )

        # =====================================================
        # اسکرول نرم
        # =====================================================

        self.scroll_offset += (
            self.target_scroll_offset
            - self.scroll_offset
        ) * 0.35

        # =====================================================
        # پس زمینه
        # =====================================================

        surface.fill(
            self.get_current_color(
                'card_bg'
            )
        )

        # =====================================================
        # نوار بالا
        # =====================================================

        toolbar_h = self.sc(50)

        pygame.draw.rect(
            surface,
            self.get_current_color(
                'nav_bg'
            ),
            (
                0,
                0,
                w,
                toolbar_h
            )
        )

        # =====================================================
        # دکمه ذخیره
        # =====================================================

        save_btn_rect = pygame.Rect(
            w - self.sc(120),
            self.sc(10),
            self.sc(100),
            self.sc(30)
        )

        pygame.draw.rect(
            surface,
            self.get_current_color(
                'accent'
            ),
            save_btn_rect,
            border_radius=self.sc(8)
        )

        save_txt = self.make_text_surface(
            "ذخیره فایل",
            self.mf(14),
            (255, 255, 255)
        )

        surface.blit(
            save_txt,
            (
                save_btn_rect.centerx
                - save_txt.get_width() // 2,

                save_btn_rect.centery
                - save_txt.get_height() // 2
            )
        )

        clickable_rects[
            'notes_save_page_trigger'
        ] = save_btn_rect

        # =====================================================
        # محتوا
        # =====================================================

        content_width = (
            w - self.sc(80)
        )

        self.update_counts_and_cache(
            content_width
        )

        text_area_y = (
            toolbar_h + self.sc(20)
        )

        clip_rect = pygame.Rect(
            self.sc(20),
            text_area_y,
            w - self.sc(40),
            h - self.sc(80)
        )

        surface.set_clip(clip_rect)

        # =====================================================
        # خطوط
        # =====================================================

        for line in self.text_surfaces_cache:

            surf = line['surface']

            current_y = (
                text_area_y
                + line['y']
                - self.scroll_offset
            )

            if (
                surf
                and current_y > -50
                and current_y < h + 50
            ):

                surface.blit(
                    surf,
                    (
                        w
                        - self.sc(40)
                        - surf.get_width(),

                        current_y
                    )
                )

        # =====================================================
        # کرسر
        # =====================================================

        if (
            (
                time.time()
                - self.notes_last_type_time
            ) % 1.0
        ) < 0.5:

            cursor_y = (
                text_area_y
                + (
                    self.cursor_line_index
                    * self.sc(28)
                )
                - self.scroll_offset
            )

            cursor_x = (
                w
                - self.sc(40)
                - self.cursor_x_in_line
            )

            pygame.draw.line(
                surface,
                self.get_current_color(
                    'accent'
                ),
                (
                    cursor_x,
                    cursor_y
                ),
                (
                    cursor_x,
                    cursor_y
                    + self.sc(20)
                ),
                2
            )

        surface.set_clip(None)

        # =====================================================
        # نوار وضعیت
        # =====================================================

        status_h = self.sc(30)

        status_y = (
            h - status_h
        )

        pygame.draw.rect(
            surface,
            self.get_current_color(
                'nav_bg'
            ),
            (
                0,
                status_y,
                w,
                status_h
            )
        )

        info_text = (
            f"کلمات: {self.notes_word_count}"
            f"   |   "
            f"کاراکترها: {self.notes_char_count}"
        )

        info_surface = self.make_text_surface(
            info_text,
            self.mf(12),
            self.get_current_color(
                'text_muted'
            )
        )

        surface.blit(
            info_surface,
            (
                self.sc(20),
                status_y + self.sc(5)
            )
        )

        # =====================================================
        # منوی راست کلیک
        # =====================================================

        if self.is_notes_context_menu_open:

            mx, my = (
                self.notes_context_menu_pos
            )

            menu_rect = pygame.Rect(
                mx,
                my,
                self.sc(120),
                self.sc(70)
            )

            pygame.draw.rect(
                surface,
                self.get_current_color(
                    'card_bg'
                ),
                menu_rect,
                border_radius=self.sc(6)
            )

            pygame.draw.rect(
                surface,
                self.get_current_color(
                    'border'
                ),
                menu_rect,
                1,
                border_radius=self.sc(6)
            )

            # -------------------------------------------------
            # کپی
            # -------------------------------------------------

            copy_rect = pygame.Rect(
                mx,
                my,
                self.sc(120),
                self.sc(35)
            )

            copy_txt = self.make_text_surface(
                "کپی کل متن",
                self.mf(13),
                self.get_current_color(
                    'text_main'
                )
            )

            surface.blit(
                copy_txt,
                (
                    copy_rect.centerx
                    - copy_txt.get_width() // 2,

                    copy_rect.centery
                    - copy_txt.get_height() // 2
                )
            )

            # -------------------------------------------------
            # پیست
            # -------------------------------------------------

            paste_rect = pygame.Rect(
                mx,
                my + self.sc(35),
                self.sc(120),
                self.sc(35)
            )

            paste_txt = self.make_text_surface(
                "جایگذاری",
                self.mf(13),
                self.get_current_color(
                    'text_main'
                )
            )

            surface.blit(
                paste_txt,
                (
                    paste_rect.centerx
                    - paste_txt.get_width() // 2,

                    paste_rect.centery
                    - paste_txt.get_height() // 2
                )
            )

        self.last_clickable_rects = (
            clickable_rects
        )

        return clickable_rects
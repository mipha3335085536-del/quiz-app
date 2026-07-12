"""
答题程序 - Kivy 移动端应用
打包 APK 版本，支持题库导入、随机答题、错题重刷
"""

import os
import json
import uuid
import random
import shutil
from datetime import datetime

# Kivy 配置必须在导入前设置
from kivy.config import Config
Config.set('graphics', 'width', '400')
Config.set('graphics', 'height', '700')
Config.set('kivy', 'window_icon', 'icon.png')

from kivy.app import App
from kivy.uix.screenmanager import ScreenManager, Screen, SlideTransition
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.scrollview import ScrollView
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.uix.textinput import TextInput
from kivy.uix.popup import Popup
from kivy.uix.filechooser import FileChooserListView
from kivy.uix.checkbox import CheckBox
from kivy.uix.progressbar import ProgressBar
from kivy.uix.widget import Widget
from kivy.uix.image import Image
from kivy.core.window import Window
from kivy.metrics import dp, sp
from kivy.utils import platform, get_color_from_hex
from kivy.clock import Clock
from kivy.graphics import Color, RoundedRectangle, Rectangle
from kivy.properties import StringProperty, NumericProperty, ListProperty, BooleanProperty, ObjectProperty

# 复用导入和题库管理模块
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from import_handler import ImportHandler
from question_bank import QuestionBank

# ==================== 常量与配色 ====================

COLORS = {
    'primary': '#4f46e5',
    'primary_dark': '#4338ca',
    'success': '#10b981',
    'danger': '#ef4444',
    'warning': '#f59e0b',
    'bg': '#f0f2f5',
    'card': '#ffffff',
    'text': '#1e293b',
    'text_secondary': '#64748b',
    'border': '#e2e8f0',
    'nav_bg': '#1e293b',
    'nav_text': '#cbd5e1',
    'nav_active': '#4f46e5',
}

TYPE_NAMES = {'single': '单选题', 'multiple': '多选题', 'judge': '判断题'}
TYPE_COLORS = {
    'single': ('#dbeafe', '#1d4ed8'),
    'multiple': ('#fef3c7', '#b45309'),
    'judge': ('#d1fae5', '#065f46'),
}

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_FOLDER = os.path.join(BASE_DIR, 'data')
os.makedirs(DATA_FOLDER, exist_ok=True)


# ==================== 自定义组件 ====================

class RoundedButton(Button):
    """圆角按钮"""
    def __init__(self, bg_color=None, radius=12, **kwargs):
        super().__init__(**kwargs)
        self.bg_color = get_color_from_hex(bg_color or COLORS['primary'])
        self.radius = radius
        self.background_color = (0, 0, 0, 0)
        self.background_normal = ''
        self.background_down = ''
        self.bind(pos=self._update_rect, size=self._update_rect)

    def _update_rect(self, *args):
        self.canvas.before.clear()
        with self.canvas.before:
            Color(*self.bg_color)
            RoundedRectangle(pos=self.pos, size=self.size, radius=[self.radius])


class RoundedCard(BoxLayout):
    """圆角卡片"""
    def __init__(self, bg_color=None, radius=12, **kwargs):
        super().__init__(**kwargs)
        self.bg_color = get_color_from_hex(bg_color or COLORS['card'])
        self.radius = radius
        self.bind(pos=self._update_rect, size=self._update_rect)

    def _update_rect(self, *args):
        self.canvas.before.clear()
        with self.canvas.before:
            Color(*self.bg_color)
            RoundedRectangle(pos=self.pos, size=self.size, radius=[self.radius])


class StatusBar(BoxLayout):
    """顶部状态栏"""
    def __init__(self, title="", **kwargs):
        super().__init__(orientation='horizontal', size_hint=(1, None), height=dp(50), **kwargs)
        self.bg_color = get_color_from_hex(COLORS['nav_bg'])
        self.bind(pos=self._update_rect, size=self._update_rect)
        self.title = title

        # 标题
        self.title_label = Label(
            text=title, font_size=sp(16), bold=True,
            color=get_color_from_hex('#ffffff'),
            size_hint=(1, 1), halign='center', valign='middle'
        )
        self.title_label.bind(size=self.title_label.setter('text_size'))
        self.add_widget(self.title_label)

    def _update_rect(self, *args):
        self.canvas.before.clear()
        with self.canvas.before:
            Color(*self.bg_color)
            Rectangle(pos=self.pos, size=self.size)


# ==================== 各页面 ====================

class HomeScreen(Screen):
    """首页"""
    def __init__(self, app_ref=None, **kwargs):
        super().__init__(**kwargs)
        self.app = app_ref
        self.build_ui()

    def build_ui(self):
        root = BoxLayout(orientation='vertical', spacing=0)

        # 顶部状态栏
        root.add_widget(StatusBar(title="📝 答题程序"))

        # 滚动内容
        scroll = ScrollView(size_hint=(1, 1))
        content = BoxLayout(orientation='vertical', spacing=dp(12),
                            padding=[dp(16), dp(16), dp(16), dp(16)],
                            size_hint_y=None)
        content.bind(minimum_height=content.setter('height'))

        # 标题
        title = Label(
            text="欢迎使用答题程序",
            font_size=sp(22), bold=True,
            color=get_color_from_hex(COLORS['text']),
            size_hint_y=None, height=dp(40)
        )
        content.add_widget(title)

        subtitle = Label(
            text="导入题库 → 随机答题 → 错题重刷",
            font_size=sp(13),
            color=get_color_from_hex(COLORS['text_secondary']),
            size_hint_y=None, height=dp(24)
        )
        content.add_widget(subtitle)

        # 功能卡片
        cards_data = [
            ('📥', '导入题库', '支持 Word/Excel 格式\n自动解析题目和选项', 'import'),
            ('📝', '开始答题', '题目随机排序，实时判断\n答完显示成绩和错题回顾', 'quiz'),
            ('📋', '错题本', '自动标记错题\n支持错题重刷', 'wrong'),
        ]

        for icon, title, desc, target in cards_data:
            card = RoundedCard(
                orientation='vertical', size_hint_y=None, height=dp(130),
                padding=[dp(16), dp(12), dp(16), dp(12)]
            )
            card_inner = BoxLayout(orientation='vertical', spacing=dp(4))

            # 图标
            icon_label = Label(
                text=icon, font_size=sp(28),
                size_hint_y=None, height=dp(36),
                color=get_color_from_hex(COLORS['text'])
            )
            card_inner.add_widget(icon_label)

            # 标题
            title_label = Label(
                text=title, font_size=sp(15), bold=True,
                color=get_color_from_hex(COLORS['text']),
                size_hint_y=None, height=dp(24)
            )
            card_inner.add_widget(title_label)

            # 描述
            desc_label = Label(
                text=desc, font_size=sp(11),
                color=get_color_from_hex(COLORS['text_secondary']),
                size_hint_y=None, height=dp(32),
                halign='left'
            )
            desc_label.bind(size=desc_label.setter('text_size'))
            card_inner.add_widget(desc_label)

            # 进入按钮
            btn = RoundedButton(
                text="进入 →", size_hint=(None, None),
                size=(dp(100), dp(32)),
                font_size=sp(12), bg_color=COLORS['primary'],
                color=get_color_from_hex('#ffffff'),
                pos_hint={'right': 1}
            )
            btn.bind(on_release=lambda x, t=target: self.switch_to(t))
            card_inner.add_widget(btn)

            card.add_widget(card_inner)
            content.add_widget(card)

        # 题库概览
        info_card = RoundedCard(
            orientation='vertical', size_hint_y=None, height=dp(100),
            padding=[dp(16), dp(12), dp(16), dp(12)]
        )

        info_title = Label(
            text="题库概览", font_size=sp(14), bold=True,
            color=get_color_from_hex(COLORS['text']),
            size_hint_y=None, height=dp(28)
        )
        info_card.add_widget(info_title)

        self.stats_label = Label(
            text="加载中...", font_size=sp(13),
            color=get_color_from_hex(COLORS['text_secondary']),
            size_hint_y=None, height=dp(40),
            halign='left'
        )
        self.stats_label.bind(size=self.stats_label.setter('text_size'))
        info_card.add_widget(self.stats_label)

        content.add_widget(info_card)

        # 底部留白
        content.add_widget(Widget(size_hint_y=None, height=dp(20)))

        scroll.add_widget(content)
        root.add_widget(scroll)
        self.add_widget(root)

    def on_enter(self, *args):
        """进入页面时刷新统计"""
        if self.app and hasattr(self.app, 'question_bank'):
            info = self.app.question_bank.get_info()
            stats = f"📚 总题数：{info['total']} 题\n❌ 错题数：{info['wrong_count']} 题"
            if info.get('type_counts'):
                types = ' | '.join([f"{k} {v}题" for k, v in info['type_counts'].items()])
                stats += f"\n📊 {types}"
            self.stats_label.text = stats

    def switch_to(self, screen_name):
        if self.app:
            self.app.sm.current = screen_name


class ImportScreen(Screen):
    """导入题库页面"""
    def __init__(self, app_ref=None, **kwargs):
        super().__init__(**kwargs)
        self.app = app_ref
        self.selected_file = None
        self.build_ui()

    def build_ui(self):
        root = BoxLayout(orientation='vertical', spacing=0)

        # 顶部
        top_bar = BoxLayout(
            orientation='horizontal', size_hint=(1, None), height=dp(50),
            padding=[dp(8), 0, dp(8), 0]
        )
        with top_bar.canvas.before:
            Color(*get_color_from_hex(COLORS['nav_bg']))
            Rectangle(pos=top_bar.pos, size=top_bar.size)
        top_bar.bind(pos=lambda w, _: w.canvas.before.clear() or setattr(w, '_drawn', True) if not hasattr(w, '_drawn') else None)

        back_btn = Button(
            text="← 返回", size_hint=(None, 1), width=dp(70),
            background_color=(0, 0, 0, 0), color=get_color_from_hex('#ffffff'),
            font_size=sp(13)
        )
        back_btn.bind(on_release=lambda x: setattr(self.app.sm, 'current', 'home'))
        top_bar.add_widget(back_btn)

        top_bar.add_widget(Label(
            text="📥 导入题库", font_size=sp(16), bold=True,
            color=get_color_from_hex('#ffffff'),
            size_hint=(1, 1)
        ))
        top_bar.add_widget(Widget(size_hint=(None, 1), width=dp(70)))
        root.add_widget(top_bar)

        # 滚动内容
        scroll = ScrollView(size_hint=(1, 1))
        content = BoxLayout(orientation='vertical', spacing=dp(12),
                            padding=[dp(16), dp(12), dp(16), dp(16)],
                            size_hint_y=None)
        content.bind(minimum_height=content.setter('height'))

        # 说明
        content.add_widget(Label(
            text="上传 Word (.docx) 或 Excel (.xlsx/.xls)\n格式的题库文件",
            font_size=sp(12),
            color=get_color_from_hex(COLORS['text_secondary']),
            size_hint_y=None, height=dp(40)
        ))

        # 模板按钮
        template_box = BoxLayout(
            orientation='horizontal', size_hint_y=None, height=dp(44),
            spacing=dp(8)
        )

        excel_btn = RoundedButton(
            text="📊 Excel模板", size_hint=(1, 1),
            font_size=sp(12), bg_color=COLORS['primary'],
            color=get_color_from_hex('#ffffff')
        )
        excel_btn.bind(on_release=lambda x: self.download_template('excel'))
        template_box.add_widget(excel_btn)

        word_btn = RoundedButton(
            text="📄 Word模板", size_hint=(1, 1),
            font_size=sp(12), bg_color=COLORS['primary'],
            color=get_color_from_hex('#ffffff')
        )
        word_btn.bind(on_release=lambda x: self.download_template('word'))
        template_box.add_widget(word_btn)
        content.add_widget(template_box)

        # 文件选择区域
        file_card = RoundedCard(
            orientation='vertical', size_hint_y=None, height=dp(160),
            padding=[dp(16), dp(12), dp(16), dp(12)]
        )
        file_card.add_widget(Label(
            text="📁", font_size=sp(36),
            size_hint_y=None, height=dp(48)
        ))

        self.file_label = Label(
            text="点击下方按钮选择题库文件",
            font_size=sp(12),
            color=get_color_from_hex(COLORS['text_secondary']),
            size_hint_y=None, height=dp(30)
        )
        file_card.add_widget(self.file_label)

        file_card.add_widget(Label(
            text="支持 .docx / .xlsx / .xls 格式",
            font_size=sp(10),
            color=get_color_from_hex('#94a3b8'),
            size_hint_y=None, height=dp(20)
        ))

        choose_btn = RoundedButton(
            text="📂 选择文件并导入", size_hint=(None, None),
            size=(dp(180), dp(40)),
            font_size=sp(13), bg_color=COLORS['primary'],
            color=get_color_from_hex('#ffffff'),
            pos_hint={'center_x': 0.5}
        )
        choose_btn.bind(on_release=self.open_file_chooser)
        file_card.add_widget(choose_btn)

        content.add_widget(file_card)

        # 进度指示
        self.status_label = Label(
            text="", font_size=sp(11),
            color=get_color_from_hex(COLORS['text_secondary']),
            size_hint_y=None, height=dp(24)
        )
        content.add_widget(self.status_label)

        # 预览标题
        content.add_widget(Label(
            text="当前题库内容：", font_size=sp(13), bold=True,
            color=get_color_from_hex(COLORS['text']),
            size_hint_y=None, height=dp(28)
        ))

        # 预览列表容器
        self.preview_box = BoxLayout(
            orientation='vertical', size_hint_y=None,
            spacing=dp(2)
        )
        self.preview_box.bind(minimum_height=self.preview_box.setter('height'))
        content.add_widget(self.preview_box)

        # 清空按钮
        clear_btn = RoundedButton(
            text="🗑️ 清空题库", size_hint=(None, None),
            size=(dp(140), dp(38)),
            font_size=sp(12), bg_color=COLORS['danger'],
            color=get_color_from_hex('#ffffff'),
            pos_hint={'right': 1}
        )
        clear_btn.bind(on_release=lambda x: self.clear_bank())
        content.add_widget(clear_btn)

        content.add_widget(Widget(size_hint_y=None, height=dp(20)))

        scroll.add_widget(content)
        root.add_widget(scroll)
        self.add_widget(root)

    def on_enter(self, *args):
        self.refresh_preview()

    def download_template(self, ttype):
        """下载模板（桌面版保存到文件，移动版提示）"""
        if self.app:
            handler = self.app.import_handler
            filepath = os.path.join(DATA_FOLDER, f'template.{ttype}')
            if ttype == 'excel':
                handler.create_excel_template(filepath)
            else:
                handler.create_word_template(filepath)
            self.status_label.text = f"模板已生成：{filepath}"
            self.status_label.color = get_color_from_hex(COLORS['success'])

    def open_file_chooser(self, *args):
        """打开文件选择器"""
        # 在移动端使用原生文件选择器，桌面端使用 Kivy FileChooser
        if platform == 'android':
            from android.storage import primary_external_storage_path
            from android.permissions import request_permissions, Permission
            request_permissions([Permission.READ_EXTERNAL_STORAGE])
            # 使用 Android 原生文件选择
            try:
                from jnius import autoclass, cast
                PythonActivity = autoclass('org.kivy.android.PythonActivity')
                Intent = autoclass('android.content.Intent')
                intent = Intent(Intent.ACTION_OPEN_DOCUMENT)
                intent.addCategory(Intent.CATEGORY_OPENABLE)
                intent.setType('*/*')
                intent.putExtra(Intent.EXTRA_MIME_TYPES, [
                    'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
                    'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                    'application/vnd.ms-excel'
                ])
                currentActivity = cast('android.app.Activity', PythonActivity.mActivity)
                currentActivity.startActivityForResult(intent, 1001)
            except:
                self._show_file_popup()
        else:
            self._show_file_popup()

    def _show_file_popup(self):
        """显示内置文件选择弹窗"""
        popup_layout = BoxLayout(orientation='vertical', spacing=dp(8), padding=dp(8))
        filechooser = FileChooserListView(
            path=os.path.expanduser('~'),
            filters=['*.xlsx', '*.xls', '*.docx']
        )
        popup_layout.add_widget(filechooser)

        btn_layout = BoxLayout(orientation='horizontal', size_hint_y=None, height=dp(40), spacing=dp(8))
        cancel_btn = Button(text="取消", size_hint=(1, 1))
        select_btn = Button(text="选择", size_hint=(1, 1))

        popup = Popup(title="选择题库文件", content=popup_layout,
                      size_hint=(0.9, 0.8), auto_dismiss=False)

        cancel_btn.bind(on_release=popup.dismiss)
        select_btn.bind(on_release=lambda x: self._on_file_selected(filechooser, popup))

        btn_layout.add_widget(cancel_btn)
        btn_layout.add_widget(select_btn)
        popup_layout.add_widget(btn_layout)
        popup.open()

    def _on_file_selected(self, filechooser, popup):
        """文件选中回调"""
        selection = filechooser.selection
        if selection:
            self.selected_file = selection[0]
            self.file_label.text = f"已选择：{os.path.basename(self.selected_file)}"
            popup.dismiss()
            self.import_file()

    def import_file(self):
        """导入文件"""
        if not self.selected_file:
            return

        filepath = self.selected_file
        ext = os.path.splitext(filepath)[1].lower()

        try:
            if self.app:
                handler = self.app.import_handler
                if ext in ('.xlsx', '.xls'):
                    questions = handler.import_from_excel(filepath)
                elif ext == '.docx':
                    questions = handler.import_from_word(filepath)
                else:
                    self.status_label.text = "不支持的文件格式"
                    self.status_label.color = get_color_from_hex(COLORS['danger'])
                    return

                if not questions:
                    self.status_label.text = "未能解析出题目，请检查文件格式"
                    self.status_label.color = get_color_from_hex(COLORS['danger'])
                    return

                count = self.app.question_bank.import_questions(questions)
                self.status_label.text = f"✅ 成功导入 {count} 道题目！"
                self.status_label.color = get_color_from_hex(COLORS['success'])
                self.selected_file = None
                self.file_label.text = "点击下方按钮选择题库文件"
                self.refresh_preview()
        except Exception as e:
            self.status_label.text = f"导入失败：{str(e)}"
            self.status_label.color = get_color_from_hex(COLORS['danger'])

    def refresh_preview(self):
        """刷新题目预览"""
        self.preview_box.clear_widgets()
        if not self.app:
            return

        questions = self.app.question_bank.get_all_questions()
        if not questions:
            self.preview_box.add_widget(Label(
                text="暂无题目", font_size=sp(11),
                color=get_color_from_hex(COLORS['text_secondary']),
                size_hint_y=None, height=dp(30)
            ))
            return

        for i, q in enumerate(questions[:20]):  # 只显示前20条
            row = BoxLayout(
                orientation='horizontal', size_hint_y=None, height=dp(32),
                spacing=dp(4)
            )
            row.add_widget(Label(
                text=f"{i+1}.", font_size=sp(10),
                color=get_color_from_hex(COLORS['text_secondary']),
                size_hint=(None, 1), width=dp(28)
            ))
            row.add_widget(Label(
                text=TYPE_NAMES.get(q.get('type', 'single'), '单选题'),
                font_size=sp(10),
                color=get_color_from_hex(COLORS['text_secondary']),
                size_hint=(None, 1), width=dp(56)
            ))
            row.add_widget(Label(
                text=q.get('content', '')[:30],
                font_size=sp(10),
                color=get_color_from_hex(COLORS['text']),
                size_hint=(1, 1), halign='left'
            ))
            self.preview_box.add_widget(row)

        if len(questions) > 20:
            self.preview_box.add_widget(Label(
                text=f"... 共 {len(questions)} 题，仅显示前 20 题",
                font_size=sp(10),
                color=get_color_from_hex(COLORS['text_secondary']),
                size_hint_y=None, height=dp(24)
            ))

    def clear_bank(self):
        """清空题库"""
        def confirm_clear(instance):
            if self.app:
                self.app.question_bank.clear()
                self.refresh_preview()
                self.status_label.text = "题库已清空"
                self.status_label.color = get_color_from_hex(COLORS['success'])
            popup.dismiss()

        content = BoxLayout(orientation='vertical', spacing=dp(12), padding=dp(16))
        content.add_widget(Label(text="确定要清空所有题目吗？\n此操作不可恢复！"))
        btn_box = BoxLayout(orientation='horizontal', spacing=dp(8), size_hint_y=None, height=dp(40))
        btn_box.add_widget(Button(text="取消", on_release=lambda x: popup.dismiss()))
        btn_box.add_widget(Button(text="确认清空", on_release=confirm_clear,
                                  background_color=get_color_from_hex(COLORS['danger'])))
        content.add_widget(btn_box)
        popup = Popup(title="确认", content=content, size_hint=(0.8, 0.3))
        popup.open()


class QuizScreen(Screen):
    """答题页面"""
    def __init__(self, app_ref=None, **kwargs):
        super().__init__(**kwargs)
        self.app = app_ref
        self.quiz_questions = []
        self.current_index = 0
        self.answers = {}
        self.quiz_mode = 'all'
        self.submitted = False
        self.build_ui()

    def build_ui(self):
        root = BoxLayout(orientation='vertical', spacing=0)

        # 顶部栏
        top_bar = BoxLayout(
            orientation='horizontal', size_hint=(1, None), height=dp(50),
            padding=[dp(8), 0, dp(8), 0]
        )
        with top_bar.canvas.before:
            Color(*get_color_from_hex(COLORS['nav_bg']))
            Rectangle(pos=top_bar.pos, size=top_bar.size)

        back_btn = Button(
            text="← 返回", size_hint=(None, 1), width=dp(70),
            background_color=(0, 0, 0, 0), color=get_color_from_hex('#ffffff'),
            font_size=sp(13)
        )
        back_btn.bind(on_release=self.go_back)
        top_bar.add_widget(back_btn)

        self.mode_title = Label(
            text="📝 答题", font_size=sp(16), bold=True,
            color=get_color_from_hex('#ffffff'),
            size_hint=(1, 1)
        )
        top_bar.add_widget(self.mode_title)
        top_bar.add_widget(Widget(size_hint=(None, 1), width=dp(70)))
        root.add_widget(top_bar)

        # 主内容区 - 初始显示模式选择
        self.main_content = BoxLayout(orientation='vertical', spacing=dp(8))
        root.add_widget(self.main_content)
        self.add_widget(root)

    def on_enter(self, *args):
        self.show_mode_select()

    def go_back(self, *args):
        """返回按钮逻辑"""
        if hasattr(self, 'question_view') and self.question_view in self.main_content.children:
            self.show_mode_select()
        else:
            self.app.sm.current = 'home'

    def show_mode_select(self):
        """显示答题模式选择"""
        self.main_content.clear_widgets()

        if not self.app:
            return

        info = self.app.question_bank.get_info()

        scroll = ScrollView(size_hint=(1, 1))
        content = BoxLayout(orientation='vertical', spacing=dp(12),
                            padding=[dp(16), dp(16), dp(16), dp(16)],
                            size_hint_y=None)
        content.bind(minimum_height=content.setter('height'))

        content.add_widget(Label(
            text="选择答题模式", font_size=sp(20), bold=True,
            color=get_color_from_hex(COLORS['text']),
            size_hint_y=None, height=dp(40)
        ))

        # 全部题目卡片
        card1 = RoundedCard(
            orientation='vertical', size_hint_y=None, height=dp(140),
            padding=[dp(16), dp(12), dp(16), dp(12)]
        )
        card1.add_widget(Label(
            text="📚", font_size=sp(36),
            size_hint_y=None, height=dp(44)
        ))
        card1.add_widget(Label(
            text="全部题目", font_size=sp(16), bold=True,
            color=get_color_from_hex(COLORS['text']),
            size_hint_y=None, height=dp(26)
        ))
        card1.add_widget(Label(
            text=f"从 {info['total']} 道题目中随机抽取",
            font_size=sp(11),
            color=get_color_from_hex(COLORS['text_secondary']),
            size_hint_y=None, height=dp(22)
        ))
        btn1 = RoundedButton(
            text="开始答题", size_hint=(None, None),
            size=(dp(140), dp(36)),
            font_size=sp(13), bg_color=COLORS['primary'],
            color=get_color_from_hex('#ffffff'),
            pos_hint={'center_x': 0.5}
        )
        btn1.bind(on_release=lambda x: self.start_quiz('all'))
        card1.add_widget(btn1)
        content.add_widget(card1)

        # 错题重刷卡片
        card2 = RoundedCard(
            orientation='vertical', size_hint_y=None, height=dp(140),
            padding=[dp(16), dp(12), dp(16), dp(12)]
        )
        card2.add_widget(Label(
            text="🔄", font_size=sp(36),
            size_hint_y=None, height=dp(44)
        ))
        card2.add_widget(Label(
            text="错题重刷", font_size=sp(16), bold=True,
            color=get_color_from_hex(COLORS['text']),
            size_hint_y=None, height=dp(26)
        ))
        card2.add_widget(Label(
            text=f"只练习 {info['wrong_count']} 道错题",
            font_size=sp(11),
            color=get_color_from_hex(COLORS['text_secondary']),
            size_hint_y=None, height=dp(22)
        ))
        wrong_count = info['wrong_count']
        btn2 = RoundedButton(
            text="开始重刷" if wrong_count > 0 else "暂无错题",
            size_hint=(None, None),
            size=(dp(140), dp(36)),
            font_size=sp(13),
            bg_color=COLORS['warning'] if wrong_count > 0 else '#94a3b8',
            color=get_color_from_hex('#ffffff'),
            pos_hint={'center_x': 0.5}
        )
        if wrong_count > 0:
            btn2.bind(on_release=lambda x: self.start_quiz('wrong'))
        card2.add_widget(btn2)
        content.add_widget(card2)

        content.add_widget(Widget(size_hint_y=None, height=dp(20)))
        scroll.add_widget(content)
        self.main_content.add_widget(scroll)

    def start_quiz(self, mode):
        """开始答题"""
        if not self.app:
            return

        questions = self.app.question_bank.get_all_questions()
        if mode == 'wrong':
            wrong_ids = self.app.question_bank.get_wrong_question_ids()
            questions = [q for q in questions if q['id'] in wrong_ids]

        if not questions:
            self._show_popup("提示", "没有可用的题目，请先导入题库！")
            return

        random.shuffle(questions)
        self.quiz_questions = questions
        self.current_index = 0
        self.answers = {}
        self.quiz_mode = mode
        self.submitted = False

        self.mode_title.text = "🔄 错题重刷" if mode == 'wrong' else "📝 全部答题"
        self.show_question()

    def show_question(self):
        """显示当前题目"""
        self.main_content.clear_widgets()

        if self.current_index >= len(self.quiz_questions):
            self.show_result()
            return

        q = self.quiz_questions[self.current_index]
        q_type = q.get('type', 'single')
        total = len(self.quiz_questions)
        answered = len(self.answers)
        correct_count = sum(1 for a in self.answers.values() if a['is_correct'])

        # 检查是否已提交
        existing = self.answers.get(self.current_index)
        self.submitted = existing is not None

        main_box = BoxLayout(orientation='vertical', spacing=dp(6))
        scroll = ScrollView(size_hint=(1, 1))

        content = BoxLayout(orientation='vertical', spacing=dp(8),
                            padding=[dp(12), dp(10), dp(12), dp(10)],
                            size_hint_y=None)
        content.bind(minimum_height=content.setter('height'))

        # 进度条
        progress_box = BoxLayout(orientation='vertical', size_hint_y=None, height=dp(40), spacing=dp(2))
        ratio = answered / total if total > 0 else 0
        bar = ProgressBar(value=int(ratio * 100), max=100, size_hint_y=None, height=dp(8))
        progress_box.add_widget(bar)

        stats = BoxLayout(orientation='horizontal', size_hint_y=None, height=dp(20))
        stats.add_widget(Label(
            text=f"{answered}/{total}", font_size=sp(11),
            color=get_color_from_hex(COLORS['text_secondary']),
            size_hint=(1, 1)
        ))
        stats.add_widget(Label(
            text=f"✅ {correct_count}", font_size=sp(11),
            color=get_color_from_hex(COLORS['success']),
            size_hint=(None, 1), width=dp(60)
        ))
        stats.add_widget(Label(
            text=f"❌ {answered - correct_count}", font_size=sp(11),
            color=get_color_from_hex(COLORS['danger']),
            size_hint=(None, 1), width=dp(60)
        ))
        progress_box.add_widget(stats)
        content.add_widget(progress_box)

        # 题目卡片
        q_card = RoundedCard(
            orientation='vertical', size_hint_y=None,
            padding=[dp(12), dp(10), dp(12), dp(10)]
        )
        q_card.bind(minimum_height=q_card.setter('height'))

        # 题型标签
        type_bg, type_fg = TYPE_COLORS.get(q_type, ('#e2e8f0', '#475569'))
        type_label = Label(
            text=TYPE_NAMES.get(q_type, '单选题'),
            font_size=sp(10),
            color=get_color_from_hex(type_fg),
            size_hint_y=None, height=dp(24),
            halign='left'
        )
        q_card.add_widget(type_label)

        # 题目内容
        q_text = Label(
            text=f"第 {self.current_index + 1} 题. {q.get('content', '')}",
            font_size=sp(15),
            color=get_color_from_hex(COLORS['text']),
            size_hint_y=None,
            halign='left'
        )
        q_text.bind(
            width=lambda s, w: setattr(s, 'text_size', (w, None)),
            texture_size=lambda s, t: setattr(s, 'height', t[1] + dp(16))
        )
        q_card.add_widget(q_text)

        # 选项
        self.option_btns = []
        options = q.get('options', [])

        if q_type == 'judge':
            options = [{'key': '对', 'text': '对 / 正确'}, {'key': '错', 'text': '错 / 错误'}]

        self.selected_values = []
        if existing:
            ans = existing['answer']
            self.selected_values = ans.split(',') if isinstance(ans, str) else (ans if isinstance(ans, list) else [ans])

        for opt in options:
            opt_key = opt['key']
            opt_text = f"{opt_key}. {opt['text']}"

            is_selected = opt_key in self.selected_values
            bg_color = COLORS['card']

            if self.submitted:
                correct_ans = q.get('answer', '')
                correct_list = [x.strip().upper() for x in correct_ans.split(',')]
                if opt_key.upper() in correct_list:
                    bg_color = '#d1fae5'
                elif is_selected and not existing.get('is_correct', False):
                    bg_color = '#fee2e2'
            elif is_selected:
                bg_color = '#eef2ff'

            opt_btn = Button(
                text=f"  {'✓' if is_selected else '○'}  {opt_text}",
                font_size=sp(13),
                background_color=get_color_from_hex(bg_color),
                color=get_color_from_hex(COLORS['text']),
                size_hint_y=None, height=dp(40),
                halign='left'
            )
            opt_btn.bind(texture_size=opt_btn.setter('size'))
            opt_btn.opt_key = opt_key

            if not self.submitted:
                if q_type == 'multiple':
                    opt_btn.bind(on_release=lambda x, k=opt_key: self.toggle_multi(k))
                else:
                    opt_btn.bind(on_release=lambda x, k=opt_key: self.select_option(k))

            self.option_btns.append(opt_btn)
            q_card.add_widget(opt_btn)

        # 反馈区域
        self.feedback_label = Label(
            text="", font_size=sp(12),
            size_hint_y=None, height=dp(10),
            halign='left'
        )
        q_card.add_widget(self.feedback_label)

        if self.submitted and existing:
            self.show_feedback(existing, q)

        content.add_widget(q_card)

        # 底部按钮
        btn_box = BoxLayout(
            orientation='horizontal', size_hint_y=None, height=dp(44),
            spacing=dp(6)
        )

        prev_btn = Button(
            text="◀", size_hint=(0.2, 1),
            background_color=get_color_from_hex('#e2e8f0'),
            color=get_color_from_hex(COLORS['text']),
            font_size=sp(14)
        )
        prev_btn.bind(on_release=lambda x: self.prev_question())
        prev_btn.disabled = self.current_index == 0
        btn_box.add_widget(prev_btn)

        submit_btn = RoundedButton(
            text="提交答案", size_hint=(0.35, 1),
            font_size=sp(13), bg_color=COLORS['primary'],
            color=get_color_from_hex('#ffffff')
        )
        submit_btn.bind(on_release=lambda x: self.submit_answer())
        if self.submitted:
            submit_btn.disabled = True
            submit_btn.bg_color = get_color_from_hex('#94a3b8')
        btn_box.add_widget(submit_btn)

        next_btn = Button(
            text="▶", size_hint=(0.2, 1),
            background_color=get_color_from_hex('#e2e8f0'),
            color=get_color_from_hex(COLORS['text']),
            font_size=sp(14)
        )
        next_btn.bind(on_release=lambda x: self.next_question())
        next_btn.disabled = self.current_index >= total - 1
        btn_box.add_widget(next_btn)

        finish_btn = Button(
            text="完成", size_hint=(0.25, 1),
            background_color=get_color_from_hex(COLORS['danger'] if answered >= total else '#94a3b8'),
            color=get_color_from_hex('#ffffff'),
            font_size=sp(12)
        )
        finish_btn.bind(on_release=lambda x: self.show_result())
        btn_box.add_widget(finish_btn)

        content.add_widget(btn_box)

        # 题号导航
        nav_label = Label(
            text="题号导航：", font_size=sp(10),
            color=get_color_from_hex(COLORS['text_secondary']),
            size_hint_y=None, height=dp(20),
            halign='left'
        )
        content.add_widget(nav_label)

        nav_grid = GridLayout(
            cols=8, size_hint_y=None,
            spacing=dp(3), padding=[0, 0, 0, dp(8)]
        )
        nav_grid.bind(minimum_height=nav_grid.setter('height'))

        for i in range(total):
            ans = self.answers.get(i)
            if ans:
                btn_bg = COLORS['success'] if ans['is_correct'] else COLORS['danger']
                btn_fg = '#ffffff'
            else:
                btn_bg = COLORS['border']
                btn_fg = COLORS['text_secondary']

            if i == self.current_index:
                btn_bg = COLORS['primary']
                btn_fg = '#ffffff'

            nav_btn = Button(
                text=str(i + 1), font_size=sp(9),
                background_color=get_color_from_hex(btn_bg),
                color=get_color_from_hex(btn_fg),
                size_hint_y=None, height=dp(30)
            )
            nav_btn.index = i
            nav_btn.bind(on_release=lambda x, idx=i: self.jump_to(idx))
            nav_grid.add_widget(nav_btn)

        content.add_widget(nav_grid)
        content.add_widget(Widget(size_hint_y=None, height=dp(20)))

        scroll.add_widget(content)
        main_box.add_widget(scroll)
        self.main_content.add_widget(main_box)

    def select_option(self, key):
        """单选"""
        if self.submitted:
            return
        self.selected_values = [key]
        self.show_question()

    def toggle_multi(self, key):
        """多选切换"""
        if self.submitted:
            return
        if key in self.selected_values:
            self.selected_values.remove(key)
        else:
            self.selected_values.append(key)
        self.show_question()

    def submit_answer(self):
        """提交答案"""
        if self.submitted or not self.selected_values:
            self._show_popup("提示", "请选择答案后再提交！")
            return

        q = self.quiz_questions[self.current_index]
        q_type = q.get('type', 'single')
        correct_answer = q.get('answer', '').strip().upper()

        if q_type == 'multiple':
            answer = ','.join(sorted(self.selected_values))
            user_sorted = sorted([x.strip().upper() for x in self.selected_values])
            correct_sorted = sorted([x.strip().upper() for x in correct_answer.split(',')])
            is_correct = user_sorted == correct_sorted
        else:
            answer = self.selected_values[0]
            is_correct = answer.strip().upper() == correct_answer

        self.answers[self.current_index] = {
            'answer': answer,
            'is_correct': is_correct,
        }

        if not is_correct and self.app:
            self.app.question_bank.mark_wrong(q['id'])

        self.submitted = True
        self.show_question()

    def show_feedback(self, record, question):
        """显示答题反馈"""
        if record['is_correct']:
            self.feedback_label.text = "✅ 回答正确！"
            self.feedback_label.color = get_color_from_hex(COLORS['success'])
            self.feedback_label.height = dp(28)
        else:
            correct_ans = question.get('answer', '')
            if question.get('options') and question.get('type', 'single') != 'judge':
                correct_list = [x.strip().upper() for x in correct_ans.split(',')]
                correct_texts = []
                for opt in question['options']:
                    if opt['key'].upper() in correct_list:
                        correct_texts.append(f"{opt['key']}. {opt['text']}")
                correct_ans = '；'.join(correct_texts) if correct_texts else correct_ans

            msg = f"❌ 回答错误\n正确答案：{correct_ans}"
            explanation = question.get('explanation', '')
            if explanation:
                msg += f"\n💡 {explanation}"
            self.feedback_label.text = msg
            self.feedback_label.color = get_color_from_hex(COLORS['danger'])
            self.feedback_label.height = dp(60)

    def prev_question(self):
        if self.current_index > 0:
            self.current_index -= 1
            self.submitted = self.answers.get(self.current_index) is not None
            existing = self.answers.get(self.current_index)
            if existing:
                ans = existing['answer']
                self.selected_values = ans.split(',') if isinstance(ans, str) else (ans if isinstance(ans, list) else [ans])
            else:
                self.selected_values = []
            self.show_question()

    def next_question(self):
        if self.current_index < len(self.quiz_questions) - 1:
            self.current_index += 1
            self.submitted = self.answers.get(self.current_index) is not None
            existing = self.answers.get(self.current_index)
            if existing:
                ans = existing['answer']
                self.selected_values = ans.split(',') if isinstance(ans, str) else (ans if isinstance(ans, list) else [ans])
            else:
                self.selected_values = []
            self.show_question()

    def jump_to(self, index):
        self.current_index = index
        self.submitted = self.answers.get(index) is not None
        existing = self.answers.get(index)
        if existing:
            ans = existing['answer']
            self.selected_values = ans.split(',') if isinstance(ans, str) else (ans if isinstance(ans, list) else [ans])
        else:
            self.selected_values = []
        self.show_question()

    def show_result(self):
        """显示答题结果"""
        total = len(self.quiz_questions)
        correct = sum(1 for a in self.answers.values() if a['is_correct'])
        wrong = total - correct
        accuracy = round(correct / total * 100, 1) if total > 0 else 0

        self.main_content.clear_widgets()

        scroll = ScrollView(size_hint=(1, 1))
        content = BoxLayout(orientation='vertical', spacing=dp(10),
                            padding=[dp(16), dp(12), dp(16), dp(16)],
                            size_hint_y=None)
        content.bind(minimum_height=content.setter('height'))

        # 标题
        content.add_widget(Label(
            text="🎉 答题完成！", font_size=sp(22), bold=True,
            color=get_color_from_hex(COLORS['text']),
            size_hint_y=None, height=dp(40)
        ))

        # 统计卡片
        stats_grid = GridLayout(cols=2, spacing=dp(8), size_hint_y=None, height=dp(160))

        stat_items = [
            ('总题数', total, COLORS['text']),
            ('答对', correct, COLORS['success']),
            ('答错', wrong, COLORS['danger']),
            ('正确率', f'{accuracy}%', COLORS['primary']),
        ]

        for label, value, color in stat_items:
            card = RoundedCard(
                orientation='vertical', size_hint=(1, 1),
                padding=[dp(8), dp(8), dp(8), dp(8)]
            )
            card.add_widget(Label(
                text=str(value), font_size=sp(28), bold=True,
                color=get_color_from_hex(color),
                size_hint=(1, 0.7)
            ))
            card.add_widget(Label(
                text=label, font_size=sp(11),
                color=get_color_from_hex(COLORS['text_secondary']),
                size_hint=(1, 0.3)
            ))
            stats_grid.add_widget(card)

        content.add_widget(stats_grid)

        # 操作按钮
        btn_box = BoxLayout(orientation='horizontal', size_hint_y=None, height=dp(40), spacing=dp(8))

        redo_btn = RoundedButton(
            text="📝 再答一次", size_hint=(1, 1),
            font_size=sp(12), bg_color=COLORS['primary'],
            color=get_color_from_hex('#ffffff')
        )
        redo_btn.bind(on_release=lambda x: self.show_mode_select())
        btn_box.add_widget(redo_btn)

        wrong_btn = RoundedButton(
            text="📋 错题本", size_hint=(1, 1),
            font_size=sp(12), bg_color=COLORS['warning'],
            color=get_color_from_hex('#ffffff')
        )
        wrong_btn.bind(on_release=lambda x: setattr(self.app.sm, 'current', 'wrong'))
        btn_box.add_widget(wrong_btn)

        content.add_widget(btn_box)

        # 错题回顾
        if wrong > 0:
            content.add_widget(Label(
                text="📋 错题回顾", font_size=sp(14), bold=True,
                color=get_color_from_hex(COLORS['danger']),
                size_hint_y=None, height=dp(30)
            ))

            for i, q in enumerate(self.quiz_questions):
                ans = self.answers.get(i)
                if ans and not ans['is_correct']:
                    correct_ans = q.get('answer', '')
                    if q.get('options') and q.get('type', 'single') != 'judge':
                        correct_list = [x.strip().upper() for x in correct_ans.split(',')]
                        correct_texts = []
                        for opt in q['options']:
                            if opt['key'].upper() in correct_list:
                                correct_texts.append(f"{opt['key']}. {opt['text']}")
                        correct_ans = '；'.join(correct_texts) if correct_texts else correct_ans

                    item = RoundedCard(
                        orientation='vertical', size_hint_y=None,
                        padding=[dp(10), dp(8), dp(10), dp(8)]
                    )
                    item.bind(minimum_height=item.setter('height'))

                    item.add_widget(Label(
                        text=f"{i+1}. {q.get('content', '')}",
                        font_size=sp(11), bold=True,
                        color=get_color_from_hex(COLORS['text']),
                        size_hint_y=None, height=dp(24),
                        halign='left'
                    ))
                    item.add_widget(Label(
                        text=f"❌ 你的答案：{ans['answer']}",
                        font_size=sp(10),
                        color=get_color_from_hex(COLORS['danger']),
                        size_hint_y=None, height=dp(20),
                        halign='left'
                    ))
                    item.add_widget(Label(
                        text=f"✅ 正确答案：{correct_ans}",
                        font_size=sp(10),
                        color=get_color_from_hex(COLORS['success']),
                        size_hint_y=None, height=dp(20),
                        halign='left'
                    ))
                    content.add_widget(item)

        content.add_widget(Widget(size_hint_y=None, height=dp(20)))
        scroll.add_widget(content)
        self.main_content.add_widget(scroll)

    def _show_popup(self, title, message):
        """显示弹窗"""
        content = BoxLayout(orientation='vertical', padding=dp(16), spacing=dp(8))
        content.add_widget(Label(text=message, font_size=sp(13)))
        btn = Button(text="确定", size_hint_y=None, height=dp(36))
        popup = Popup(title=title, content=content, size_hint=(0.7, 0.3))
        btn.bind(on_release=popup.dismiss)
        content.add_widget(btn)
        popup.open()


class WrongScreen(Screen):
    """错题本页面"""
    def __init__(self, app_ref=None, **kwargs):
        super().__init__(**kwargs)
        self.app = app_ref
        self.build_ui()

    def build_ui(self):
        root = BoxLayout(orientation='vertical', spacing=0)

        # 顶部栏
        top_bar = BoxLayout(
            orientation='horizontal', size_hint=(1, None), height=dp(50),
            padding=[dp(8), 0, dp(8), 0]
        )
        with top_bar.canvas.before:
            Color(*get_color_from_hex(COLORS['nav_bg']))
            Rectangle(pos=top_bar.pos, size=top_bar.size)

        back_btn = Button(
            text="← 返回", size_hint=(None, 1), width=dp(70),
            background_color=(0, 0, 0, 0), color=get_color_from_hex('#ffffff'),
            font_size=sp(13)
        )
        back_btn.bind(on_release=lambda x: setattr(self.app.sm, 'current', 'home'))
        top_bar.add_widget(back_btn)

        top_bar.add_widget(Label(
            text="📋 错题本", font_size=sp(16), bold=True,
            color=get_color_from_hex('#ffffff'),
            size_hint=(1, 1)
        ))
        top_bar.add_widget(Widget(size_hint=(None, 1), width=dp(70)))
        root.add_widget(top_bar)

        # 内容区
        self.content_area = BoxLayout(orientation='vertical')
        root.add_widget(self.content_area)
        self.add_widget(root)

    def on_enter(self, *args):
        self.refresh()

    def refresh(self):
        """刷新错题列表"""
        self.content_area.clear_widgets()

        if not self.app:
            return

        wrong_ids = self.app.question_bank.get_wrong_question_ids()
        all_questions = self.app.question_bank.get_all_questions()
        wrong_questions = [q for q in all_questions if q['id'] in wrong_ids]

        if not wrong_questions:
            empty = BoxLayout(orientation='vertical', spacing=dp(8))
            empty.add_widget(Widget())
            empty.add_widget(Label(
                text="🎉", font_size=sp(48)
            ))
            empty.add_widget(Label(
                text="暂无错题记录",
                font_size=sp(14),
                color=get_color_from_hex(COLORS['text_secondary'])
            ))
            empty.add_widget(Label(
                text="去答题页面开始练习吧！",
                font_size=sp(11),
                color=get_color_from_hex('#94a3b8')
            ))
            empty.add_widget(Widget())
            self.content_area.add_widget(empty)
            return

        # 操作按钮
        btn_box = BoxLayout(
            orientation='horizontal', size_hint_y=None, height=dp(40),
            spacing=dp(8), padding=[dp(12), dp(8), dp(12), 0]
        )

        redo_btn = RoundedButton(
            text="🔄 错题重刷", size_hint=(1, 1),
            font_size=sp(12), bg_color=COLORS['primary'],
            color=get_color_from_hex('#ffffff')
        )
        redo_btn.bind(on_release=lambda x: self.start_wrong_quiz())
        btn_box.add_widget(redo_btn)

        clear_btn = RoundedButton(
            text="🗑️ 清空", size_hint=(1, 1),
            font_size=sp(12), bg_color=COLORS['danger'],
            color=get_color_from_hex('#ffffff')
        )
        clear_btn.bind(on_release=lambda x: self.clear_all())
        btn_box.add_widget(clear_btn)

        self.content_area.add_widget(btn_box)

        # 错题列表
        scroll = ScrollView(size_hint=(1, 1))
        list_box = BoxLayout(orientation='vertical', spacing=dp(4),
                             padding=[dp(12), dp(8), dp(12), dp(16)],
                             size_hint_y=None)
        list_box.bind(minimum_height=list_box.setter('height'))

        for i, q in enumerate(wrong_questions):
            q_type = q.get('type', 'single')

            card = RoundedCard(
                orientation='vertical', size_hint_y=None,
                padding=[dp(10), dp(8), dp(10), dp(8)]
            )
            card.bind(minimum_height=card.setter('height'))

            # 题号和题型
            header = BoxLayout(orientation='horizontal', size_hint_y=None, height=dp(24))
            header.add_widget(Label(
                text=f"{i+1}. {TYPE_NAMES.get(q_type, '单选题')}",
                font_size=sp(10),
                color=get_color_from_hex(COLORS['text_secondary']),
                size_hint=(1, 1), halign='left'
            ))

            remove_btn = Button(
                text="移除", size_hint=(None, 1), width=dp(56),
                font_size=sp(9),
                background_color=get_color_from_hex('#fee2e2'),
                color=get_color_from_hex(COLORS['danger'])
            )
            remove_btn.qid = q['id']
            remove_btn.bind(on_release=lambda x, qid=q['id']: self.remove_one(qid))
            header.add_widget(remove_btn)
            card.add_widget(header)

            # 题目内容
            card.add_widget(Label(
                text=q.get('content', ''),
                font_size=sp(12), bold=True,
                color=get_color_from_hex(COLORS['text']),
                size_hint_y=None, height=dp(24),
                halign='left'
            ))

            # 正确答案
            correct_ans = q.get('answer', '')
            if q.get('options') and q_type != 'judge':
                correct_list = [x.strip().upper() for x in correct_ans.split(',')]
                correct_texts = []
                for opt in q['options']:
                    if opt['key'].upper() in correct_list:
                        correct_texts.append(f"{opt['key']}. {opt['text']}")
                correct_ans = '；'.join(correct_texts) if correct_texts else correct_ans

            card.add_widget(Label(
                text=f"✅ 正确答案：{correct_ans}",
                font_size=sp(10),
                color=get_color_from_hex(COLORS['success']),
                size_hint_y=None, height=dp(20),
                halign='left'
            ))

            # 解析
            explanation = q.get('explanation', '')
            if explanation:
                card.add_widget(Label(
                    text=f"💡 {explanation}",
                    font_size=sp(10),
                    color=get_color_from_hex(COLORS['text_secondary']),
                    size_hint_y=None, height=dp(20),
                    halign='left'
                ))

            list_box.add_widget(card)

        scroll.add_widget(list_box)
        self.content_area.add_widget(scroll)

    def remove_one(self, qid):
        """移除单个错题"""
        if self.app:
            self.app.question_bank.remove_wrong_mark(qid)
            self.refresh()

    def clear_all(self):
        """清空所有错题"""
        def do_clear(instance):
            if self.app:
                self.app.question_bank.clear_wrong()
                self.refresh()
            popup.dismiss()

        content = BoxLayout(orientation='vertical', spacing=dp(8), padding=dp(16))
        content.add_widget(Label(text="确定要清空所有错题标记吗？"))
        btn_box = BoxLayout(orientation='horizontal', spacing=dp(8), size_hint_y=None, height=dp(36))
        btn_box.add_widget(Button(text="取消", on_release=lambda x: popup.dismiss()))
        btn_box.add_widget(Button(text="确认清空", on_release=do_clear,
                                  background_color=get_color_from_hex(COLORS['danger'])))
        content.add_widget(btn_box)
        popup = Popup(title="确认", content=content, size_hint=(0.8, 0.3))
        popup.open()

    def start_wrong_quiz(self):
        """跳转到错题重刷"""
        self.app.sm.current = 'quiz'
        quiz_screen = self.app.sm.get_screen('quiz')
        quiz_screen.start_quiz('wrong')


# ==================== 主应用 ====================

class QuizApp(App):
    """答题程序主应用"""

    def build(self):
        self.title = '答题程序'
        self.icon = 'icon.png'

        # 初始化模块
        self.question_bank = QuestionBank(DATA_FOLDER)
        self.import_handler = ImportHandler()

        # 屏幕管理器
        self.sm = ScreenManager(transition=SlideTransition())

        # 注册页面
        self.sm.add_widget(HomeScreen(app_ref=self, name='home'))
        self.sm.add_widget(ImportScreen(app_ref=self, name='import'))
        self.sm.add_widget(QuizScreen(app_ref=self, name='quiz'))
        self.sm.add_widget(WrongScreen(app_ref=self, name='wrong'))

        return self.sm


if __name__ == '__main__':
    QuizApp().run()

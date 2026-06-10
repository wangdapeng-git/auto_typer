import math
import threading
import time
import tkinter as tk
from tkinter import filedialog, scrolledtext

import customtkinter as ctk
from pynput.keyboard import Controller

from codec_utils import APP_VERSION, encode_payload


class HoverTip:
    def __init__(self, widget, text):
        self.widget = widget
        self.text = text
        self.tip_window = None
        self.widget.bind("<Enter>", self.show_tip, add="+")
        self.widget.bind("<Leave>", self.hide_tip, add="+")
        self.widget.bind("<ButtonPress>", self.hide_tip, add="+")

    def show_tip(self, _event=None):
        if self.tip_window or not self.text:
            return

        x = self.widget.winfo_rootx() + 18
        y = self.widget.winfo_rooty() + self.widget.winfo_height() + 8
        self.tip_window = tk.Toplevel(self.widget)
        self.tip_window.wm_overrideredirect(True)
        self.tip_window.wm_geometry(f"+{x}+{y}")

        tip_label = tk.Label(
            self.tip_window,
            text=self.text,
            justify="left",
            background="#fff8dc",
            relief="solid",
            borderwidth=1,
            padx=8,
            pady=6,
            wraplength=260,
        )
        tip_label.pack()

    def hide_tip(self, _event=None):
        if self.tip_window is not None:
            self.tip_window.destroy()
            self.tip_window = None


class AutoTyperApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title(f"Auto Typer Sender {APP_VERSION}")
        self.geometry("980x780")
        self.help_tips = []

        self.is_paused = False
        self.typing_active = False
        self.current_encoded_str = ""
        self.total_chunks = 0
        self.completed_chunks = 0
        self.typing_thread = None
        self.stop_event = threading.Event()
        self.kb_controller = Controller()

        self.build_ui()
        self.bind_input_events()
        self.refresh_estimate()

    def build_ui(self):
        header_frame = ctk.CTkFrame(self, fg_color="transparent")
        header_frame.pack(pady=(8, 4), fill="x", padx=20)

        header_label = ctk.CTkLabel(
            header_frame,
            text=f"Auto Typer Sender {APP_VERSION}",
            font=ctk.CTkFont(size=18, weight="bold"),
            anchor="w",
        )
        header_label.pack(side="left")
        self.add_help_badge(
            header_frame,
            (
                "使用说明\n\n"
                "1. 使用前请先切换到英文输入法\n"
                "2. 支持导入文件，或直接在文本框中输入内容\n"
                "3. 点击开始后，请在倒计时内切换到目标窗口\n"
                "4. 主程序仅负责编码和发送；解码请使用 isolated_decoder.py\n"
                "5. 带 ? 标记的项支持鼠标悬浮说明"
            ),
            padx=(6, 0),
            pady=(0, 0),
        )

        file_label = ctk.CTkLabel(self, text="输入方式 1：导入文件")
        file_label.pack(pady=(4, 2), fill="x")

        self.file_choice_frame = ctk.CTkFrame(self)
        self.file_choice_frame.pack(pady=(0, 6), fill="x", padx=20)

        self.file_path_entry = ctk.CTkEntry(self.file_choice_frame, placeholder_text="文件路径")
        self.file_path_entry.pack(side="left", padx=10, fill="x", expand=True)

        self.select_file_button = ctk.CTkButton(self.file_choice_frame, text="选择文件", command=self.select_file)
        self.select_file_button.pack(side="left", padx=10, fill="x", expand=True)
        self.add_help_badge(self.file_choice_frame, "选择需要自动输入的文件；如果这里留空，程序会使用下方文本框中的内容。")

        text_label = ctk.CTkLabel(self, text="输入方式 2：直接输入文本")
        text_label.pack(pady=(2, 2), fill="x")

        self.text_input_frame = ctk.CTkFrame(self)
        self.text_input_frame.pack(pady=(0, 6), fill="x", padx=20)
        self.text_input_frame.configure(height=132)
        self.text_input_frame.pack_propagate(False)

        self.text_input = ctk.CTkTextbox(
            self.text_input_frame,
            height=112,
            corner_radius=10,
            fg_color="#f0f0f0",
            text_color="#333333",
            border_color="#a0a0a0",
            border_width=2,
        )
        self.text_input.pack(padx=10, pady=8, fill="both", expand=True)
        self.bind_help_tip(self.text_input, "适合直接输入或粘贴长文本；如果文本框非空，会优先使用这里的内容。")

        self.setting_label = ctk.CTkLabel(self, text="参数设置")
        self.setting_label.pack(pady=(2, 2), fill="x")

        self.setting_frame1 = ctk.CTkFrame(self)
        self.setting_frame1.pack(pady=(0, 6), fill="x", padx=20)

        self.one_step_group, self.one_step_len_entry = self.create_param_group(
            self.setting_frame1,
            "单步长度（整数）",
            "单步长度",
            "10",
            "每次连续输入的字符数。值越大越快，值越小通常更稳。",
            "建议从 10 开始；如果目标窗口容易漏字，可适当调小。",
        )
        self.one_step_group.pack(side="left", padx=(12, 8), pady=8, fill="x", expand=True)
        self.add_vertical_divider(self.setting_frame1).pack(side="left", pady=10)

        self.step_interval_group, self.step_interval_entry = self.create_param_group(
            self.setting_frame1,
            "步间隔（秒）",
            "步间隔",
            "0.1",
            "每段输入完成后的等待时间。远程桌面、网页输入框等场景可适当增大。",
            "每段输入之间的等待时间，单位为秒；远程环境卡顿时可调大。",
        )
        self.step_interval_group.pack(side="left", padx=8, pady=8, fill="x", expand=True)
        self.add_vertical_divider(self.setting_frame1).pack(side="left", pady=10)

        self.fix_sym_group, self.fix_sym_max_entry = self.create_param_group(
            self.setting_frame1,
            "最大纠错字符（整数）",
            "纠错字符",
            "10",
            "增强模式生效。值越大，纠错能力越强，但输出长度也会增加。",
            "通常保持默认值 10 即可；远程输入越不稳定，越适合适度调大。",
        )
        self.fix_sym_group.pack(side="left", padx=8, pady=8, fill="x", expand=True)
        self.add_vertical_divider(self.setting_frame1).pack(side="left", pady=10)

        self.wait_time_group, self.wait_time_len_entry = self.create_param_group(
            self.setting_frame1,
            "开始前等待（秒）",
            "等待时长",
            "5",
            "点击开始后，程序会先等待指定秒数，再开始自动输入；需要切换窗口时可适当调大。",
            "如果你需要切换窗口或手动聚焦输入框，可以把这里调大一些。",
        )
        self.wait_time_group.pack(side="left", padx=(8, 12), pady=8, fill="x", expand=True)

        self.setting_frame2 = ctk.CTkFrame(self)
        self.setting_frame2.pack(pady=(0, 6), fill="x", padx=20)

        self.mode_group = ctk.CTkFrame(self.setting_frame2, fg_color="transparent")
        self.mode_group.pack(side="left", padx=(12, 24), pady=8, fill="x")

        mode_label_row = ctk.CTkFrame(self.mode_group, fg_color="transparent")
        mode_label_row.pack(anchor="w")
        mode_label = ctk.CTkLabel(mode_label_row, text="编码模式")
        mode_label.pack(side="left")
        self.add_help_badge(
            mode_label_row,
            "默认模式输出标准编码；小写模式仅使用 0-9 和 a-z，更适合对字符集有限制的输入场景。",
            padx=(2, 0),
            pady=(0, 8),
        )

        self.mode_segmented = ctk.CTkSegmentedButton(
            self.mode_group,
            values=["默认模式", "小写模式"],
            command=lambda _value: self.refresh_estimate(),
        )
        self.mode_segmented.pack(anchor="w", pady=(4, 0), fill="x")
        self.mode_segmented.set("默认模式")
        self.bind_help_tip(self.mode_segmented, "二选一：默认模式输出标准编码；小写模式输出仅含 0-9 和 a-z 的小写编码。")

        self.enhanced_mode_var = ctk.BooleanVar(value=False)
        self.enhanced_mode_group = ctk.CTkFrame(self.setting_frame2, fg_color="transparent")
        self.enhanced_mode_group.pack(side="left", padx=(0, 18), pady=8)
        self.enhanced_mode_checkbox = ctk.CTkCheckBox(
            self.enhanced_mode_group,
            text="增强模式",
            variable=self.enhanced_mode_var,
            onvalue=True,
            offvalue=False,
            command=self.refresh_estimate,
        )
        self.enhanced_mode_checkbox.pack(side="left")
        self.bind_help_tip(self.enhanced_mode_checkbox, "对当前编码模式加入纠错信息。小写模式下会把纠错参数写入编码负载。")
        self.add_help_badge(self.enhanced_mode_group, "增强模式会增加容错率，但输出也会更长。", padx=(2, 0), pady=(0, 8))

        estimate_frame = ctk.CTkFrame(self)
        estimate_frame.pack(pady=(0, 6), fill="x", padx=20)

        self.estimate_label = ctk.CTkLabel(
            estimate_frame,
            text="编码预估：原文 0 字符 | 编码后 0 字符 | 0 段 | 预计 0.0 秒",
            justify="left",
            anchor="w",
        )
        self.estimate_label.pack(padx=12, pady=(12, 6), fill="x")

        self.progress_label = ctk.CTkLabel(
            estimate_frame,
            text="发送进度：未开始",
            justify="left",
            anchor="w",
        )
        self.progress_label.pack(padx=12, pady=(0, 8), fill="x")

        self.progressbar = ctk.CTkProgressBar(estimate_frame)
        self.progressbar.pack(padx=12, pady=(0, 12), fill="x")
        self.progressbar.set(0)

        self.operation_label = ctk.CTkLabel(self, text="操作区")
        self.operation_label.pack(pady=(2, 2), fill="x")

        self.button_frame = ctk.CTkFrame(self)
        self.button_frame.pack(pady=(0, 6), fill="x", padx=20)

        self.start_button_group = ctk.CTkFrame(self.button_frame, fg_color="transparent")
        self.start_button_group.pack(side="left", padx=10, fill="x", expand=True)
        self.start_button = ctk.CTkButton(self.start_button_group, text="开始自动打字", command=self.start_typing)
        self.start_button.pack(side="left", fill="x", expand=True)
        self.bind_help_tip(self.start_button, "读取当前输入内容并开始倒计时，倒计时结束后会自动输入到目标窗口。")
        self.add_help_badge(self.start_button_group, "开始前请确认目标窗口可以接收键盘输入。", padx=(2, 0), pady=(0, 8))

        self.pause_button = ctk.CTkButton(self.button_frame, text="暂停/恢复", command=self.pause_resume_typing)
        self.pause_button.pack(side="left", padx=10, fill="x", expand=True)

        self.stop_button = ctk.CTkButton(self.button_frame, text="停止", command=self.stop_typing_by_button)
        self.stop_button.pack(side="left", padx=10, fill="x", expand=True)

        self.log_text = scrolledtext.ScrolledText(self, state="disabled", height=8)
        self.log_text.pack(pady=(0, 8), fill="both", expand=True)

    def bind_input_events(self):
        self.file_path_entry.bind("<KeyRelease>", lambda _event: self.refresh_estimate(), add="+")
        self.text_input.bind("<KeyRelease>", lambda _event: self.refresh_estimate(), add="+")
        self.one_step_len_entry.bind("<KeyRelease>", lambda _event: self.refresh_estimate(), add="+")
        self.step_interval_entry.bind("<KeyRelease>", lambda _event: self.refresh_estimate(), add="+")
        self.wait_time_len_entry.bind("<KeyRelease>", lambda _event: self.refresh_estimate(), add="+")
        self.fix_sym_max_entry.bind("<KeyRelease>", lambda _event: self.refresh_estimate(), add="+")

    def bind_help_tip(self, widget, text):
        if widget is None or not text:
            return

        try:
            self.help_tips.append(HoverTip(widget, text))
            return
        except (AttributeError, NotImplementedError, tk.TclError):
            pass

        for child in widget.winfo_children():
            self.bind_help_tip(child, text)

    def add_help_badge(self, parent, text, side="left", padx=(2, 0), pady=(0, 8)):
        help_badge = ctk.CTkLabel(
            parent,
            text="?",
            width=10,
            height=10,
            corner_radius=0,
            fg_color="transparent",
            text_color="#94a3b8",
            font=ctk.CTkFont(size=8, weight="bold"),
        )
        help_badge.pack(side=side, padx=padx, pady=pady, anchor="n")
        self.bind_help_tip(help_badge, text)
        return help_badge

    def add_vertical_divider(self, parent):
        return ctk.CTkFrame(parent, width=1, height=42, fg_color="#d4d4d8")

    def create_param_group(self, parent, label_text, placeholder_text, default_value, badge_text, entry_tip):
        group = ctk.CTkFrame(parent, fg_color="transparent")
        label_row = ctk.CTkFrame(group, fg_color="transparent")
        label_row.pack(anchor="w")
        label = ctk.CTkLabel(label_row, text=label_text)
        label.pack(side="left")
        self.add_help_badge(label_row, badge_text, padx=(2, 0), pady=(0, 8))

        entry = ctk.CTkEntry(group, placeholder_text=placeholder_text, width=120)
        entry.insert(0, default_value)
        entry.pack(anchor="w", pady=(4, 0), fill="x")
        self.bind_help_tip(entry, entry_tip)
        return group, entry

    def get_fix_sym_count(self):
        try:
            return int(self.fix_sym_max_entry.get())
        except (ValueError, AttributeError):
            return 10

    def get_wait_time(self):
        try:
            return int(self.wait_time_len_entry.get())
        except ValueError:
            return 0

    def get_one_step_len(self):
        try:
            return max(1, int(self.one_step_len_entry.get()))
        except ValueError:
            return 10

    def get_step_interval(self):
        try:
            return max(0.0, float(self.step_interval_entry.get()))
        except ValueError:
            return 0.1

    def is_lowercase_mode(self):
        return self.mode_segmented.get() == "小写模式"

    def get_input_bytes(self):
        file_path = self.file_path_entry.get().strip()
        input_text = self.text_input.get("1.0", "end-1c")
        if file_path and not input_text.strip():
            try:
                with open(file_path, "rb") as file_obj:
                    return file_obj.read()
            except OSError:
                return None
        return input_text.encode("utf-8")

    def build_encoded_content(self, content):
        return encode_payload(
            content,
            lowercase_mode=self.is_lowercase_mode(),
            enhanced_mode=bool(self.enhanced_mode_var.get()),
            n_sym=self.get_fix_sym_count(),
        )

    def refresh_estimate(self):
        content = self.get_input_bytes()
        if content is None:
            self.estimate_label.configure(text="编码预估：文件不可读")
            return

        encoded = self.build_encoded_content(content)
        step_len = self.get_one_step_len()
        chunks = math.ceil(len(encoded) / step_len) if encoded else 0
        total_seconds = self.get_wait_time() + (chunks * self.get_step_interval())
        mode_name = "小写模式" if self.is_lowercase_mode() else "默认模式"
        if bool(self.enhanced_mode_var.get()):
            mode_name += "+增强"

        self.current_encoded_str = encoded
        self.total_chunks = chunks
        self.estimate_label.configure(
            text=(
                f"编码预估：模式 {mode_name} | 原文 {len(content)} 字节 | "
                f"编码后 {len(encoded)} 字符 | {chunks} 段 | 预计 {total_seconds:.1f} 秒"
            )
        )

    def append_log(self, message):
        self.log_text.configure(state="normal")
        self.log_text.insert("end", str(message) + "\n")
        self.log_text.see("end")
        self.log_text.configure(state="disabled")

    def update_progress(self, completed, total):
        total = max(total, 1)
        progress = completed / total
        self.progressbar.set(progress)
        self.progress_label.configure(text=f"发送进度：{completed}/{total} 段 ({progress * 100:.1f}%)")

    def reset_progress(self):
        self.completed_chunks = 0
        self.progressbar.set(0)
        if self.total_chunks > 0:
            self.progress_label.configure(text=f"发送进度：0/{self.total_chunks} 段 (0.0%)")
        else:
            self.progress_label.configure(text="发送进度：未开始")

    def select_file(self):
        file_path = filedialog.askopenfilename()
        self.file_path_entry.delete(0, "end")
        self.file_path_entry.insert(0, file_path)
        self.refresh_estimate()

    def start_typing(self):
        self.append_log("Info: start_typing")
        if self.typing_active:
            self.append_log("Error: 当前已有进行中的打字任务。")
            return

        try:
            one_step_len = int(self.one_step_len_entry.get())
        except ValueError:
            self.append_log("Error: 单步长度必须为整数。")
            return

        try:
            step_interval = float(self.step_interval_entry.get())
        except ValueError:
            self.append_log("Error: 步间隔必须为数字。")
            return

        content = self.get_input_bytes()
        if content is None:
            self.append_log("Error: 文件不可读取。")
            return

        self.current_encoded_str = self.build_encoded_content(content)
        self.total_chunks = math.ceil(len(self.current_encoded_str) / max(1, one_step_len)) if self.current_encoded_str else 0
        self.reset_progress()
        self.typing_active = True
        self.stop_event.clear()
        self.is_paused = False
        self.typing_thread = threading.Thread(
            target=self.type_content,
            args=(self.current_encoded_str, one_step_len, step_interval),
            daemon=True,
        )
        self.typing_thread.start()

    def pause_resume_typing(self):
        if self.typing_active:
            self.is_paused = not self.is_paused
            self.append_log(f"打字 {'暂停' if self.is_paused else '恢复'}.")

    def stop_typing_by_button(self):
        self.is_paused = False
        self.stop_event.set()
        self.append_log("终止打字任务")

    def split_chunks(self, text, chunk_size):
        for index in range(0, len(text), chunk_size):
            yield text[index:index + chunk_size]

    def wait_with_stop(self, seconds, slice_seconds=0.05):
        end_time = time.monotonic() + max(0.0, seconds)
        while not self.stop_event.is_set():
            remaining = end_time - time.monotonic()
            if remaining <= 0:
                return True
            time.sleep(min(slice_seconds, remaining))
        return False

    def type_chunk(self, chunk):
        for char in chunk:
            if self.stop_event.is_set():
                return False
            self.kb_controller.type(char)
        return True

    def type_content(self, encoded_str, one_step_len, step_interval):
        wait_time_len = self.get_wait_time()
        was_stopped = False
        pause_logged = False

        try:
            for countdown in range(wait_time_len):
                if self.stop_event.is_set():
                    was_stopped = True
                    break
                left_seconds = wait_time_len - countdown
                self.append_log(f"即将开始打字，请将光标移到需要打字的窗口。倒计时: {left_seconds}")
                if not self.wait_with_stop(1):
                    was_stopped = True
                    break

            chunks = list(self.split_chunks(encoded_str, max(1, one_step_len)))
            total = len(chunks)
            for chunk in chunks:
                if self.stop_event.is_set():
                    was_stopped = True
                    break

                while self.is_paused and not self.stop_event.is_set():
                    if not pause_logged:
                        self.append_log("打字任务暂停中，等待恢复")
                        pause_logged = True
                    if not self.wait_with_stop(0.1):
                        was_stopped = True
                        break

                if self.stop_event.is_set():
                    was_stopped = True
                    break

                pause_logged = False
                self.append_log(f"打字中: {chunk[:10]}")
                if not self.type_chunk(chunk):
                    was_stopped = True
                    break

                self.completed_chunks += 1
                self.after(0, self.update_progress, self.completed_chunks, total)
                if not self.wait_with_stop(step_interval):
                    was_stopped = True
                    break
        finally:
            self.typing_active = False
            self.is_paused = False
            self.stop_event.clear()

        if was_stopped:
            self.append_log("打字任务已停止。")
        else:
            self.append_log("打字完成。")


if __name__ == "__main__":
    app = AutoTyperApp()
    app.mainloop()

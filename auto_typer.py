import time
import zlib
import base64
import threading
import tkinter as tk
import customtkinter as ctk 
from tkinter import filedialog, scrolledtext
from pynput.keyboard import Controller, Listener, Key
from reedsolo import RSCodec, ReedSolomonError

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

        self.title("Auto Typer V1.0")
        self.geometry("800x700")

        # 创建一个CTkFrame作为使用说明的容器
        self.input_method_frame = ctk.CTkFrame(self)
        self.input_method_frame.pack(pady=10, fill='x', padx=20)

        self.input_method_label = ctk.CTkLabel(
            self.input_method_frame,
            text=(
                "Auto Typer 使用说明\n\n"
                "1. 使用前请先切换到英文输入法\n"
                "2. 支持导入文件，或直接在文本框中输入内容\n"
                "3. 点击开始后，请在倒计时内切换到目标窗口\n"
                "4. 输入完成后，可在“解码”窗口还原结果\n"
                "5. 带 ? 标记的项支持鼠标悬浮说明"
            ),
            height=10,
            justify="left",
            anchor="w",
        )
        self.input_method_label.pack(side='left', pady=10, fill='x', expand=True)
        self.help_tips = []

        self.input_method_label = ctk.CTkLabel(self, text="输入方式 1：导入文件", height=10)
        self.input_method_label.pack(pady=10, fill='x')

        # 创建一个CTkFrame作为文件选择的容器
        self.file_choice_frame = ctk.CTkFrame(self)
        self.file_choice_frame.pack(pady=10, fill='x', padx=20)

        self.file_path_entry = ctk.CTkEntry(self.file_choice_frame, placeholder_text="文件路径")
        self.file_path_entry.pack(side='left', padx=10, fill='x', expand=True) # 文件路径输入

        self.select_file_button = ctk.CTkButton(self.file_choice_frame, text="选择文件", command=self.select_file)
        self.select_file_button.pack(side='left', padx=10, fill='x', expand=True) # 选择文件按钮
        self.add_help_badge(self.file_choice_frame, "选择需要自动输入的文件；如果这里留空，程序会使用下方文本框中的内容。")
        self.bind_help_tip(self.file_path_entry, "文件路径可手动填写，也可通过“选择文件”按钮自动带入。")
        self.bind_help_tip(self.select_file_button, "选择一个本地文件，程序会读取其内容并编码后自动输入。")

        self.input_method_label = ctk.CTkLabel(self, text="输入方式 2：直接输入文本", height=10)
        self.input_method_label.pack(pady=10, fill='x')


        # 创建一个CTkFrame作为文件选择的容器
        self.text_input_frame = ctk.CTkFrame(self)
        self.text_input_frame.pack(pady=10, fill='x', padx=20)

        self.text_input = ctk.CTkTextbox(self.text_input_frame,
                                          height=25,
                                          corner_radius=10,  # 设置圆角
                                          fg_color="#f0f0f0",  # 设置前景色（文本框内部的颜色）
                                          text_color="#333333",  # 设置文本颜色
                                          border_color="#a0a0a0",  # 设置边框颜色
                                          border_width=2,  # 设置边框宽度
                                          ) 
        self.text_input.pack(pady=10, fill='both', expand=True) # 直接文本输入框
        self.bind_help_tip(self.text_input, "适合直接输入短文本；如果已选择文件，程序会优先使用文件内容。")

        self.setting_label = ctk.CTkLabel(self, text="参数设置", height=10)
        self.setting_label.pack(pady=10, fill='x')

        self.setting_frame1 = ctk.CTkFrame(self)
        self.setting_frame1.pack(pady=10, fill='x', padx=20)
        self.one_step_group, self.one_step_len_entry = self.create_param_group(
            self.setting_frame1,
            "单步长度（整数）",
            "单步长度 (整数)",
            "10",
            "每次连续输入的字符数。值越大越快，值越小通常更稳。",
            "建议从 10 开始；如果目标窗口容易漏字，可适当调小。",
        )
        self.one_step_group.pack(side='left', padx=(12, 8), pady=8, fill='x', expand=True)
        self.add_vertical_divider(self.setting_frame1).pack(side='left', pady=10)

        self.step_interval_group, self.step_interval_entry = self.create_param_group(
            self.setting_frame1,
            "步间隔（秒）",
            "步间隔 (浮点数)",
            "0.1",
            "每段输入完成后的等待时间。远程桌面、网页输入框等场景可适当增大。",
            "每段输入之间的等待时间，单位为秒；远程环境卡顿时可调大。",
        )
        self.step_interval_group.pack(side='left', padx=8, pady=8, fill='x', expand=True)
        self.add_vertical_divider(self.setting_frame1).pack(side='left', pady=10)

        self.fix_sym_group, self.fix_sym_max_entry = self.create_param_group(
            self.setting_frame1,
            "最大纠错字符（整数）",
            "最大纠错字符 (整数)",
            "10",
            "仅增强模式生效。值越大，纠错能力越强，但输出长度也会增加。",
            "通常保持默认值 10 即可；远程输入越不稳定，越适合适度调大。",
        )
        self.fix_sym_group.pack(side='left', padx=8, pady=8, fill='x', expand=True)
        self.add_vertical_divider(self.setting_frame1).pack(side='left', pady=10)

        self.wait_time_group, self.wait_time_len_entry = self.create_param_group(
            self.setting_frame1,
            "开始前等待（秒）",
            "等待时长 (整数)",
            "5",
            "点击开始后，程序会先等待指定秒数，再开始自动输入；需要切换窗口时可适当调大。",
            "如果你需要切换窗口或手动聚焦输入框，可以把这里调大一些。",
        )
        self.wait_time_group.pack(side='left', padx=(8, 12), pady=8, fill='x', expand=True)

        self.setting_frame2 = ctk.CTkFrame(self)
        self.setting_frame2.pack(pady=10, fill='x', padx=20)
        # 创建一个复选框用于记录是否启动增强模式
        self.enhanced_mode_var = ctk.BooleanVar(value=False)  # 创建一个布尔型变量，默认为False
        self.enhanced_mode_group = ctk.CTkFrame(self.setting_frame2, fg_color="transparent")
        self.enhanced_mode_group.pack(side='left', padx=(12, 18), pady=8)
        self.enhanced_mode_checkbox = ctk.CTkCheckBox(self.enhanced_mode_group, text="增强模式", variable=self.enhanced_mode_var, onvalue=True, offvalue=False)
        self.enhanced_mode_checkbox.pack(side='left')
        self.bind_help_tip(self.enhanced_mode_checkbox, "先压缩，再加入纠错信息。适合远程环境不稳定或文本较长的场景。")
        self.add_help_badge(self.enhanced_mode_group, "增强模式会增加传输冗余，提高容错率，但输出也会更长。", padx=(2, 0), pady=(0, 8))

        self.lowercase_mode_var = ctk.BooleanVar(value=False)
        self.lowercase_mode_group = ctk.CTkFrame(self.setting_frame2, fg_color="transparent")
        self.lowercase_mode_group.pack(side='left', padx=(0, 12), pady=8)
        self.lowercase_mode_checkbox = ctk.CTkCheckBox(self.lowercase_mode_group, text="小写模式", variable=self.lowercase_mode_var, onvalue=True, offvalue=False)
        self.lowercase_mode_checkbox.pack(side='left')
        self.bind_help_tip(self.lowercase_mode_checkbox, "勾选后会使用 hex 编码，输出仅包含 0-9 和 a-f。")
        self.add_help_badge(self.lowercase_mode_group, "适合只允许数字和小写字母输入的目标环境。", padx=(2, 0), pady=(0, 8))

        self.setting_label = ctk.CTkLabel(self, text="操作区", height=10)
        self.setting_label.pack(pady=10, fill='x')

        # 创建一个CTkFrame作为按钮的容器
        self.button_frame = ctk.CTkFrame(self)
        self.button_frame.pack(pady=10, fill='x', padx=20)

        self.start_button_group = ctk.CTkFrame(self.button_frame, fg_color="transparent")
        self.start_button_group.pack(side='left', padx=10, fill='x', expand=True)
        self.start_button = ctk.CTkButton(self.start_button_group, text="开始自动打字", command=self.start_typing)
        self.start_button.pack(side='left', fill='x', expand=True) # 开始按钮
        self.bind_help_tip(self.start_button, "读取当前输入内容并开始倒计时，倒计时结束后会自动输入到目标窗口。")
        self.add_help_badge(self.start_button_group, "开始前请确认目标窗口可以接收键盘输入。", padx=(2, 0), pady=(0, 8))
        
        self.pause_button = ctk.CTkButton(self.button_frame, text="暂停/恢复", command=self.pause_resume_typing)
        self.pause_button.pack(side='left', padx=10, fill='x', expand=True) # 暂停按钮
        self.bind_help_tip(self.pause_button, "仅在打字过程中生效，可临时暂停后继续。")

        self.stop_button = ctk.CTkButton(self.button_frame, text="停止", command=self.stop_typing_by_button)
        self.stop_button.pack(side='left', padx=10, fill='x', expand=True) # 停止按钮
        self.bind_help_tip(self.stop_button, "立即结束当前打字任务，未输入的剩余内容会被丢弃。")

        self.decode_button_group = ctk.CTkFrame(self.button_frame, fg_color="transparent")
        self.decode_button_group.pack(side='left', padx=10, fill='x', expand=True)
        self.open_decode_window_button = ctk.CTkButton(self.decode_button_group, text="解码", command=self.open_decode_window)
        self.open_decode_window_button.pack(side='left', fill='x', expand=True) # 解码按钮
        self.bind_help_tip(self.open_decode_window_button, "打开解码窗口，将 base64 或 hex 文本还原为原始内容。")
        self.add_help_badge(self.decode_button_group, "解码时要与编码模式保持一致，例如小写模式对应 hex。", padx=(2, 0), pady=(0, 8))


        # 日志框
        self.log_text = scrolledtext.ScrolledText(self, state='disabled', height=10)
        self.log_text.pack(pady=10, fill='both', expand=True)  # 让日志框填充剩余空间

        # 初始化变量
        self.is_paused = False
        self.stop_typing = False
        self.typing_active = False
        self.kb_controller = Controller()

    def bind_help_tip(self, widget, text):
        self.help_tips.append(HoverTip(widget, text))

    def create_param_group(self, parent, label_text, placeholder_text, default_value, badge_text, entry_tip):
        group = ctk.CTkFrame(parent, fg_color="transparent")
        label_row = ctk.CTkFrame(group, fg_color="transparent")
        label_row.pack(anchor='w')
        label = ctk.CTkLabel(label_row, text=label_text)
        label.pack(side='left')
        self.add_help_badge(label_row, badge_text, padx=(2, 0), pady=(0, 8))

        entry = ctk.CTkEntry(group, placeholder_text=placeholder_text, width=120)
        entry.insert(0, default_value)
        entry.pack(anchor='w', pady=(4, 0), fill='x')
        self.bind_help_tip(entry, entry_tip)
        return group, entry

    def add_vertical_divider(self, parent):
        return ctk.CTkFrame(parent, width=1, height=42, fg_color="#d4d4d8")

    def add_help_badge(self, parent, text, side='left', padx=(2, 0), pady=(0, 8)):
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
        help_badge.pack(side=side, padx=padx, pady=pady, anchor='n')
        self.bind_help_tip(help_badge, text)
        return help_badge

    #     # 设置监听器
    #     self.listener = Listener(on_press=self.on_press)
    #     self.listener.start()

    # def on_press(self, key):
    #     if key == r"'\x03'": # ctrl+c
    #         self.stop_typing = True
    #         self.append_log("Typing stopped by Ctrl+C key.")
    #         return False
    #     elif key == r"'\x18'" and self.typing_active == False:
    #         self.append_log("Typing stary by Ctrl+X key.")
    #         self.start_typing()
    #         return False
         
    def start_typing(self):
        # 获取参数
        self.append_log("Info: start_typing")
        try:
            one_step_len = int(self.one_step_len_entry.get())
        except ValueError:
            self.append_log("Error: One Step Length must be an integer.")
            return
        try:
            step_interval = float(self.step_interval_entry.get())
        except ValueError:
            self.append_log("Error: Step Interval must be a float.")
            return
        
        # 获取文件路径或直接输入的文本
        file_path = self.file_path_entry.get()
        input_text = self.text_input.get("1.0", "end-1c").strip()
        if file_path is not None and len(file_path)>0 and len(input_text)<=0:
            with open(file_path, 'rb') as f:
                input_text=f.read()
        else:
            input_text = bytes(input_text, encoding = "utf8")

        # 启动打字线程
        self.typing_active = True
        self.typing_thread = threading.Thread(target=self.type_content, args=(input_text, one_step_len, step_interval))
        self.typing_thread.start()

    def pause_resume_typing(self):
        if self.typing_active:
            self.is_paused = not self.is_paused
            status = "暂停" if self.is_paused else "恢复"
            self.append_log(f"打字 {status}.")

    def stop_typing_by_button(self):
        self.stop_typing = True
        self.append_log("终止打字任务")

    def type_content(self, content, one_step_len, step_interval):
        # 读取文件并转换为编码字符串
        encoded_str = self.file2base64(content)
        self.type_str(encoded_str, one_step_len, step_interval)

    def select_file(self):
        file_path = filedialog.askopenfilename()
        self.file_path_entry.delete(0, "end")
        self.file_path_entry.insert(0, file_path)

    def type_str(self, in_str, one_step_len, step_interval):
        wait_time_len = int(self.wait_time_len_entry.get())
        for i in range(wait_time_len): # 默认等待5秒
            self.append_log(f"即将开始打字，请将光标移到需要打字的窗口。倒计时: {wait_time_len-i}")
            time.sleep(1)
        for i in self.spilt_list(in_str, one_step_len):
            if self.stop_typing:
                break
            while self.is_paused:
                self.append_log(f"打字任务暂停中，等待恢复")
                time.sleep(0.5)
                pass
            self.append_log(f"打字中: {i[:10]}")  # 显示部分输入内容
            self.kb_controller.type(i)
            threading.Event().wait(step_interval)
        self.typing_active = False
        
        if not self.stop_typing:
            self.append_log(f"打字完成，状态切换为: {self.typing_active}")
        self.stop_typing = False

    def file2base64(self, content):
        """将文件以二进制转成base64字符串"""
        if int(self.enhanced_mode_var.get())==1: # 增强模式
            compressed_data = zlib.compress(content)
            if hasattr(self, 'fix_sym_max_entry'):
                n_sym = int(self.fix_sym_max_entry.get())
            else:
                n_sym = 10
            content  = RSCodec(n_sym).encode(compressed_data)

        if int(self.lowercase_mode_var.get()) == 1:
            b4str = content.hex()
            self.append_log(f"已编码为小写模式(hex):{b4str[:20]}")
        else:
            base64_str = base64.b64encode(content)  # base64类型
            b4str = base64_str.decode('utf-8')  # str
            self.append_log(f"已编码为 base64:{b4str[:20]}")
        return b4str
        
    def spilt_list(self, like_list, one_len):
        # 将字符串按照特定长度等分
        for i in range(0, len(like_list), one_len):
            yield like_list[i:i + one_len]

    def append_log(self, message):
        self.log_text.configure(state='normal')
        self.log_text.insert("end", str(message) + "\n")
        self.log_text.see("end")
        self.log_text.configure(state='disabled')

    def open_decode_window(self):
        # 创建一个新窗口
        decode_window = ctk.CTkToplevel(self)
        decode_window.title("解码窗口")
        decode_window.geometry("400x300+1000+400") # 增加x轴和y轴偏移

        # 在新窗口中创建一个文本输入框
        self.decode_entry = ctk.CTkEntry(decode_window, placeholder_text="输入要解码的文本（base64 或 hex）")
        self.decode_entry.pack(pady=10, expand=True)
        self.bind_help_tip(self.decode_entry, "默认模式输入 base64；勾选小写模式后，这里应输入 hex。")

        # 在新窗口中创建一个解码按钮
        decode_button = ctk.CTkButton(decode_window, text="开始解码", command=self.decode_text)
        decode_button.pack(pady=10)
        self.bind_help_tip(decode_button, "将当前输入的编码文本还原为原始内容。")
        self.add_help_badge(decode_window, "如果解码失败，请先检查编码模式和纠错参数是否与生成时一致。", padx=(0, 0))

        # 在新窗口中创建一个解码后文本的窗口
        self.result_textbox = ctk.CTkTextbox(decode_window, height=10, width=40)
        self.result_textbox.pack(pady=10, fill='both', expand=True)

    def decode_text(self):
        # 获取输入框中的文本
        text_to_decode = self.decode_entry.get()
        # 执行解码操作
        try:
            decoded_text = self.perform_decoding(text_to_decode)
        except Exception as e:
            self.append_log(f"解码失败: {e}")
            decoded_text = ""
        # 将解码结果显示在文本展示窗口中
        self.result_textbox.delete(1.0, "end")  # 清空文本展示窗口
        self.result_textbox.insert("end", decoded_text)  # 插入解码结果

    def perform_decoding(self, encoded_str):
        # 解码逻辑
        if int(self.lowercase_mode_var.get()) == 1:
            text = bytes.fromhex(encoded_str)
        else:
            text = base64.b64decode(encoded_str)
        if int(self.enhanced_mode_var.get())==1: # 增强模式 
            if hasattr(self, 'fix_sym_max_entry'):
                n_sym = int(self.fix_sym_max_entry.get())
            else:
                n_sym = 10
            try:
                compressed_data = RSCodec(n_sym).decode(text)[0]
                text = zlib.decompress(compressed_data)
            except ReedSolomonError as e:
                self.append_log(f"增强模式下解码失败: {e}")
        self.append_log(f"已将编码解码:{text.decode()[:20]}")
        return text.decode()

if __name__ == "__main__":
    app = AutoTyperApp()
    app.mainloop()

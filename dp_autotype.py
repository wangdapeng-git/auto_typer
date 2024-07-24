import time
import zlib
import base64
import threading
import customtkinter as ctk 
from tkinter import filedialog, scrolledtext
from pynput.keyboard import Controller, Listener, Key
from reedsolo import RSCodec, ReedSolomonError

class AutoTyperApp(ctk.CTk):

    def __init__(self):
        super().__init__()

        self.title("Auto Typer V1.0")
        self.geometry("800x700")

        # 创建一个CTkFrame作为使用说明的容器
        self.input_method_frame = ctk.CTkFrame(self)
        self.input_method_frame.pack(pady=10, fill='x', padx=20)

        self.input_method_label = ctk.CTkLabel(self.input_method_frame, text="""
                                                Auto Typer 使用说明
                                                                                        
                                                1. 准备环境：请确保已经将打字环境切换为英文输入
                                                2. 选择文件导入或文本框输入，指定自动打字的输入
                                                3. 启动任务后，在五秒内将光标移到需要打字的窗口
                                                4. 等待打字完成后，对输出的base64字符串进行解码
                                                5. 增强模式会对数据进行压缩并具备一定的纠错功能
                                                """, height=10)
        self.input_method_label.pack(side='left', pady=10, fill='x')

        self.input_method_label = ctk.CTkLabel(self, text="输入方式1：文件导入", height=10)
        self.input_method_label.pack(pady=10, fill='x')

        # 创建一个CTkFrame作为文件选择的容器
        self.file_choice_frame = ctk.CTkFrame(self)
        self.file_choice_frame.pack(pady=10, fill='x', padx=20)

        self.file_path_entry = ctk.CTkEntry(self.file_choice_frame, placeholder_text="文件路径")
        self.file_path_entry.pack(side='left', padx=10, fill='x', expand=True) # 文件路径输入

        self.select_file_button = ctk.CTkButton(self.file_choice_frame, text="选择文件", command=self.select_file)
        self.select_file_button.pack(side='left', padx=10, fill='x', expand=True) # 选择文件按钮

        self.input_method_label = ctk.CTkLabel(self, text="输入方式2：文本输入", height=10)
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

        self.setting_label = ctk.CTkLabel(self, text="配置项", height=10)
        self.setting_label.pack(pady=10, fill='x')

        self.setting_frame1 = ctk.CTkFrame(self)
        self.setting_frame1.pack(pady=10, fill='x', padx=20)
        # one_step_len 输入
        self.one_step_len_label = ctk.CTkLabel(self.setting_frame1, text="单步长度 (整数)")
        self.one_step_len_label.pack(side='left', pady=(10, 0))  # 上边距为10，下边距为0
        self.one_step_len_entry = ctk.CTkEntry(self.setting_frame1, placeholder_text="单步长度 (整数)")
        self.one_step_len_entry.insert(0, "10")  # 设置默认值为 10
        self.one_step_len_entry.pack(side='left', padx=10, fill='x')

        # step_interval 输入
        self.step_interval_entry = ctk.CTkEntry(self.setting_frame1, placeholder_text="步间隔 (浮点数)")
        self.step_interval_entry.insert(0, "0.1")  # 设置默认值为 0.1
        self.step_interval_entry.pack(side='right', padx=10, fill='x')
        self.one_step_len_label = ctk.CTkLabel(self.setting_frame1, text="步间隔 (浮点数)")
        self.one_step_len_label.pack(side='right', pady=(10, 0))  # 上边距为10，下边距为0

        self.setting_frame2 = ctk.CTkFrame(self)
        self.setting_frame2.pack(pady=10, fill='x', padx=20)
        # 创建一个复选框用于记录是否启动增强模式
        self.enhanced_mode_var = ctk.BooleanVar(value=False)  # 创建一个布尔型变量，默认为False
        self.enhanced_mode_checkbox = ctk.CTkCheckBox(self.setting_frame2, text="增强模式", variable=self.enhanced_mode_var, onvalue=True, offvalue=False)
        self.enhanced_mode_checkbox.pack(side='left', padx=10, fill='x', expand=True)

        self.fix_sym_max_label  = ctk.CTkLabel(self.setting_frame2, text="最大纠错字符 (整数)")
        self.fix_sym_max_label.pack(side='left', pady=(10, 0))  # 上边距为10，下边距为0
        self.fix_sym_max_entry = ctk.CTkEntry(self.setting_frame2, placeholder_text="最大纠错字符 (整数)")
        self.fix_sym_max_entry.insert(0, "10")  # 设置默认值为 10
        self.fix_sym_max_entry.pack(side='left', padx=10, fill='x')

        self.wait_time_len_entry = ctk.CTkEntry(self.setting_frame2, placeholder_text="等待时长 (整数)")
        self.wait_time_len_entry.insert(0, "5")  # 设置默认值为 10
        self.wait_time_len_entry.pack(side='right', padx=10, fill='x')
        self.wait_time_len_label  = ctk.CTkLabel(self.setting_frame2, text="任务等待时长（秒）")
        self.wait_time_len_label.pack(side='right', pady=(10, 0))  # 上边距为10，下边距为0

        self.setting_label = ctk.CTkLabel(self, text="核心按钮", height=10)
        self.setting_label.pack(pady=10, fill='x')

        # 创建一个CTkFrame作为按钮的容器
        self.button_frame = ctk.CTkFrame(self)
        self.button_frame.pack(pady=10, fill='x', padx=20)

        self.start_button = ctk.CTkButton(self.button_frame, text="开始自动打字", command=self.start_typing)
        self.start_button.pack(side='left', padx=10, fill='x', expand=True) # 开始按钮
        
        self.pause_button = ctk.CTkButton(self.button_frame, text="暂停/恢复", command=self.pause_resume_typing)
        self.pause_button.pack(side='left', padx=10, fill='x', expand=True) # 暂停按钮

        self.stop_button = ctk.CTkButton(self.button_frame, text="停止", command=self.stop_typing_by_button)
        self.stop_button.pack(side='left', padx=10, fill='x', expand=True) # 停止按钮

        self.open_decode_window_button = ctk.CTkButton(self.button_frame, text="解码", command=self.open_decode_window)
        self.open_decode_window_button.pack(side='left', padx=10, fill='x', expand=True) # 解码按钮


        # 日志框
        self.log_text = scrolledtext.ScrolledText(self, state='disabled', height=10)
        self.log_text.pack(pady=10, fill='both', expand=True)  # 让日志框填充剩余空间

        # 初始化变量
        self.is_paused = False
        self.stop_typing = False
        self.typing_active = False
        self.kb_controller = Controller()

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
        # 读取文件并转换为 base64 字符串
        b4str = self.file2base64(content)
        self.type_str(b4str, one_step_len, step_interval)

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
        self.decode_entry = ctk.CTkEntry(decode_window, placeholder_text="输入要解码的文本")
        self.decode_entry.pack(pady=10, expand=True)

        # 在新窗口中创建一个解码按钮
        decode_button = ctk.CTkButton(decode_window, text="开始解码", command=self.decode_text)
        decode_button.pack(pady=10)

        # 在新窗口中创建一个解码后文本的窗口
        self.result_textbox = ctk.CTkTextbox(decode_window, height=10, width=40)
        self.result_textbox.pack(pady=10, fill='both', expand=True)

    def decode_text(self):
        # 获取输入框中的文本
        text_to_decode = self.decode_entry.get()
        # 执行解码操作
        decoded_text = self.perform_decoding(text_to_decode)
        # 将解码结果显示在文本展示窗口中
        self.result_textbox.delete(1.0, "end")  # 清空文本展示窗口
        self.result_textbox.insert("end", decoded_text)  # 插入解码结果

    def perform_decoding(self, base64_str):
        # 解码逻辑
        text = base64.b64decode(base64_str)
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
        self.append_log(f"已将 base64 解码:{text.decode()[:20]}")
        return text.decode()

if __name__ == "__main__":
    app = AutoTyperApp()
    app.mainloop()

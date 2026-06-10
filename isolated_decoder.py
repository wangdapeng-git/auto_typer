import queue
import threading
import tkinter as tk
from tkinter import filedialog, scrolledtext

import customtkinter as ctk

from codec_utils import APP_VERSION, decode_payload


class DecoderReceiverApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title(f"Auto Typer Receiver {APP_VERSION}")
        self.geometry("1040x860")
        self.minsize(900, 720)
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(2, weight=1)
        self.grid_rowconfigure(6, weight=1)

        self.input_stats_job = None
        self.decode_token = 0
        self.decoding_active = False
        self.ui_queue = queue.SimpleQueue()
        self.input_wrap_width = 120
        self.reformatting_input = False

        intro_label = ctk.CTkLabel(
            self,
            text=(
                f"Auto Typer Receiver {APP_VERSION}\n\n"
                "纯解码接收端：用于把发送端产出的编码文本还原为原文。"
            ),
            justify="left",
            anchor="w",
        )
        intro_label.grid(row=0, column=0, padx=16, pady=(16, 10), sticky="ew")

        input_header = ctk.CTkFrame(self, fg_color="transparent")
        input_header.grid(row=1, column=0, padx=16, pady=(0, 6), sticky="ew")

        input_label = ctk.CTkLabel(input_header, text="编码输入")
        input_label.pack(side="left")

        self.input_stats_label = ctk.CTkLabel(input_header, text="0 字符", text_color="#64748b")
        self.input_stats_label.pack(side="left", padx=(10, 0))

        self.load_button = ctk.CTkButton(input_header, text="导入文本文件", width=120, command=self.load_input_file)
        self.load_button.pack(side="right")

        self.input_textbox = self.create_text_area(tk.WORD)
        self.input_textbox.grid(row=2, column=0, padx=16, pady=(0, 10), sticky="nsew")
        self.input_textbox.bind("<<Modified>>", self.on_input_modified, add="+")

        self.status_label = ctk.CTkLabel(
            self,
            text="输入编码文本后点击“开始解码”。程序会自动识别默认模式、小写模式及增强模式。",
            justify="left",
            anchor="w",
        )
        self.status_label.grid(row=3, column=0, padx=16, pady=(0, 10), sticky="ew")

        button_frame = ctk.CTkFrame(self, fg_color="transparent")
        button_frame.grid(row=4, column=0, padx=16, pady=(0, 10), sticky="ew")

        self.decode_button = ctk.CTkButton(button_frame, text="开始解码", command=self.decode_text)
        self.decode_button.pack(side="left")

        self.clear_button = ctk.CTkButton(button_frame, text="清空", command=self.clear_text)
        self.clear_button.pack(side="left", padx=(10, 0))

        self.export_button = ctk.CTkButton(button_frame, text="导出结果", command=self.export_result)
        self.export_button.pack(side="left", padx=(10, 0))

        output_header = ctk.CTkFrame(self, fg_color="transparent")
        output_header.grid(row=5, column=0, padx=16, pady=(0, 6), sticky="ew")

        output_label = ctk.CTkLabel(output_header, text="解码结果")
        output_label.pack(side="left")

        self.output_stats_label = ctk.CTkLabel(output_header, text="0 字符", text_color="#64748b")
        self.output_stats_label.pack(side="left", padx=(10, 0))

        self.result_textbox = self.create_text_area(tk.WORD)
        self.result_textbox.grid(row=6, column=0, padx=16, pady=(0, 16), sticky="nsew")

        self.refresh_input_stats(0)
        self.refresh_output_stats(0)
        self.after(50, self.process_ui_queue)

    def create_text_area(self, wrap_mode):
        text_widget = scrolledtext.ScrolledText(
            self,
            wrap=wrap_mode,
            undo=False,
            maxundo=0,
            autoseparators=False,
            font=("Consolas", 10),
            relief="solid",
            borderwidth=1,
        )
        text_widget.configure(highlightthickness=0)
        return text_widget

    def get_text_length(self, text_widget):
        try:
            return text_widget.count("1.0", "end-1c", "chars")[0]
        except Exception:
            return len(text_widget.get("1.0", "end-1c"))

    def get_compact_input_text(self):
        return "".join(self.input_textbox.get("1.0", "end-1c").split())

    def wrap_encoded_text(self, text):
        if not text:
            return ""
        return "\n".join(
            text[index:index + self.input_wrap_width]
            for index in range(0, len(text), self.input_wrap_width)
        )

    def replace_input_text(self, text):
        self.reformatting_input = True
        try:
            self.input_textbox.delete("1.0", "end")
            self.input_textbox.insert("end", text)
            self.input_textbox.edit_modified(False)
        finally:
            self.reformatting_input = False

    def refresh_input_stats(self, length=None):
        if length is None:
            length = len(self.get_compact_input_text())
        self.input_stats_label.configure(text=f"{length} 字符")

    def refresh_output_stats(self, length=None):
        if length is None:
            length = self.get_text_length(self.result_textbox)
        self.output_stats_label.configure(text=f"{length} 字符")

    def schedule_input_stats_refresh(self):
        if self.input_stats_job is not None:
            self.after_cancel(self.input_stats_job)
        self.input_stats_job = self.after(350, self.finish_input_stats_refresh)

    def finish_input_stats_refresh(self):
        self.input_stats_job = None
        compact_text = self.get_compact_input_text()
        wrapped_text = self.wrap_encoded_text(compact_text)
        current_text = self.input_textbox.get("1.0", "end-1c")
        if current_text != wrapped_text:
            self.replace_input_text(wrapped_text)
        self.refresh_input_stats(len(compact_text))

    def on_input_modified(self, _event=None):
        if self.reformatting_input:
            return
        if self.input_textbox.edit_modified():
            self.schedule_input_stats_refresh()
            self.input_textbox.edit_modified(False)

    def set_decode_controls_state(self, enabled):
        state = "normal" if enabled else "disabled"
        self.decode_button.configure(state=state)
        self.load_button.configure(state=state)

    def load_input_file(self):
        file_path = filedialog.askopenfilename(
            filetypes=[
                ("Text files", "*.txt"),
                ("All files", "*.*"),
            ]
        )
        if not file_path:
            return

        try:
            with open(file_path, "r", encoding="utf-8") as file_obj:
                content = file_obj.read()
        except OSError as exc:
            self.status_label.configure(text=f"读取文件失败：{exc}")
            return
        except UnicodeDecodeError:
            self.status_label.configure(text="读取文件失败：请提供 UTF-8 编码的文本文件。")
            return

        compact_text = "".join(content.split())
        self.replace_input_text(self.wrap_encoded_text(compact_text))
        self.refresh_input_stats(len(compact_text))
        self.status_label.configure(text=f"已导入文件：{file_path}")

    def clear_text(self):
        self.decode_token += 1
        self.decoding_active = False
        self.set_decode_controls_state(True)
        self.replace_input_text("")
        self.result_textbox.delete("1.0", "end")
        self.refresh_input_stats(0)
        self.refresh_output_stats(0)
        self.status_label.configure(text="已清空输入和输出。")

    def export_result(self):
        result_text = self.result_textbox.get("1.0", "end-1c")
        if not result_text:
            self.status_label.configure(text="导出失败：当前没有可导出的解码结果。")
            return

        file_path = filedialog.asksaveasfilename(
            defaultextension=".txt",
            filetypes=[
                ("Text files", "*.txt"),
                ("All files", "*.*"),
            ],
        )
        if not file_path:
            return

        try:
            with open(file_path, "w", encoding="utf-8") as file_obj:
                file_obj.write(result_text)
        except OSError as exc:
            self.status_label.configure(text=f"导出失败：{exc}")
            return

        self.status_label.configure(text=f"导出完成：{file_path}")

    def decode_text(self):
        if self.decoding_active:
            self.status_label.configure(text="解码任务进行中，请等待当前任务完成。")
            return

        encoded_text = self.get_compact_input_text()
        encoded_length = len(encoded_text)
        if not encoded_text:
            self.status_label.configure(text="解码失败：输入内容不能为空。")
            return

        self.decode_token += 1
        token = self.decode_token
        self.decoding_active = True
        self.set_decode_controls_state(False)
        self.result_textbox.delete("1.0", "end")
        self.refresh_output_stats(0)
        self.status_label.configure(text=f"正在解码：输入 {encoded_length} 字符，请稍候...")

        worker = threading.Thread(
            target=self.decode_worker,
            args=(token, encoded_text, encoded_length),
            daemon=True,
        )
        worker.start()

    def decode_worker(self, token, encoded_text, encoded_length):
        try:
            decoded_text = decode_payload(encoded_text, decode_mode="auto")
        except Exception as exc:
            self.ui_queue.put(("decode_error", token, str(exc)))
            return

        self.ui_queue.put(("decode_success", token, encoded_length, decoded_text))

    def process_ui_queue(self):
        while True:
            try:
                message = self.ui_queue.get_nowait()
            except queue.Empty:
                break

            action = message[0]
            if action == "decode_error":
                _, token, error_message = message
                self.finish_decode_error(token, error_message)
            elif action == "decode_success":
                _, token, encoded_length, decoded_text = message
                self.finish_decode_success(token, encoded_length, decoded_text)

        self.after(50, self.process_ui_queue)

    def finish_decode_error(self, token, error_message):
        if token != self.decode_token:
            return

        self.decoding_active = False
        self.set_decode_controls_state(True)
        self.result_textbox.delete("1.0", "end")
        self.refresh_output_stats(0)
        self.status_label.configure(text=f"解码失败：{error_message}")

    def finish_decode_success(self, token, encoded_length, decoded_text):
        if token != self.decode_token:
            return

        self.result_textbox.delete("1.0", "end")
        self.status_label.configure(text="解码完成，正在写入结果...")
        self.render_result_in_chunks(token, encoded_length, decoded_text, 0)

    def render_result_in_chunks(self, token, encoded_length, decoded_text, start_index, chunk_size=16384):
        if token != self.decode_token:
            return

        end_index = min(start_index + chunk_size, len(decoded_text))
        if start_index < end_index:
            self.result_textbox.insert("end", decoded_text[start_index:end_index])

        if end_index < len(decoded_text):
            self.after(1, self.render_result_in_chunks, token, encoded_length, decoded_text, end_index, chunk_size)
            return

        self.decoding_active = False
        self.set_decode_controls_state(True)
        self.refresh_output_stats(len(decoded_text))
        self.status_label.configure(text=f"解码完成：输入 {encoded_length} 字符，输出 {len(decoded_text)} 字符。")


if __name__ == "__main__":
    app = DecoderReceiverApp()
    app.mainloop()

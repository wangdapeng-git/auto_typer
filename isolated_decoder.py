import customtkinter as ctk

from codec_utils import APP_VERSION, decode_payload


class DecoderReceiverApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title(f"Auto Typer Receiver {APP_VERSION}")
        self.geometry("760x680")

        intro_label = ctk.CTkLabel(
            self,
            text=(
                f"Auto Typer Receiver {APP_VERSION}\n\n"
                "纯解码接收端：用于把发送端产出的编码文本还原为原文。"
            ),
            justify="left",
            anchor="w",
        )
        intro_label.pack(padx=16, pady=(16, 10), fill="x")

        control_frame = ctk.CTkFrame(self)
        control_frame.pack(padx=16, pady=(0, 10), fill="x")

        mode_label = ctk.CTkLabel(control_frame, text="解码模式")
        mode_label.pack(side="left", padx=(10, 6), pady=10)

        self.mode_var = ctk.StringVar(value="auto")
        self.mode_menu = ctk.CTkOptionMenu(
            control_frame,
            values=["auto", "base64", "base36"],
            variable=self.mode_var,
        )
        self.mode_menu.pack(side="left", padx=(0, 12), pady=10)

        self.enhanced_var = ctk.BooleanVar(value=False)
        self.enhanced_checkbox = ctk.CTkCheckBox(
            control_frame,
            text="增强模式",
            variable=self.enhanced_var,
            onvalue=True,
            offvalue=False,
        )
        self.enhanced_checkbox.pack(side="left", padx=(0, 12), pady=10)

        fix_sym_label = ctk.CTkLabel(control_frame, text="纠错字符")
        fix_sym_label.pack(side="left", padx=(0, 6), pady=10)

        self.fix_sym_entry = ctk.CTkEntry(control_frame, width=90, placeholder_text="10")
        self.fix_sym_entry.insert(0, "10")
        self.fix_sym_entry.pack(side="left", padx=(0, 10), pady=10)

        self.input_textbox = ctk.CTkTextbox(self, height=220)
        self.input_textbox.pack(padx=16, pady=(0, 10), fill="both", expand=True)

        self.status_label = ctk.CTkLabel(
            self,
            text="输入编码文本后点击“开始解码”。base36 对应新的小写模式，base64 对应默认模式。",
            justify="left",
            anchor="w",
        )
        self.status_label.pack(padx=16, pady=(0, 10), fill="x")

        button_frame = ctk.CTkFrame(self, fg_color="transparent")
        button_frame.pack(padx=16, pady=(0, 10), fill="x")

        decode_button = ctk.CTkButton(button_frame, text="开始解码", command=self.decode_text)
        decode_button.pack(side="left")

        clear_button = ctk.CTkButton(button_frame, text="清空", command=self.clear_text)
        clear_button.pack(side="left", padx=(10, 0))

        self.result_textbox = ctk.CTkTextbox(self, height=220)
        self.result_textbox.pack(padx=16, pady=(0, 16), fill="both", expand=True)

    def clear_text(self):
        self.input_textbox.delete("1.0", "end")
        self.result_textbox.delete("1.0", "end")
        self.status_label.configure(text="已清空输入和输出。")

    def decode_text(self):
        try:
            n_sym = int(self.fix_sym_entry.get())
        except ValueError:
            self.status_label.configure(text="解码失败：纠错字符必须是整数。")
            return

        try:
            decoded_text = decode_payload(
                self.input_textbox.get("1.0", "end-1c"),
                decode_mode=self.mode_var.get(),
                enhanced_mode=bool(self.enhanced_var.get()),
                n_sym=n_sym,
            )
        except Exception as exc:
            self.status_label.configure(text=f"解码失败：{exc}")
            self.result_textbox.delete("1.0", "end")
            return

        self.result_textbox.delete("1.0", "end")
        self.result_textbox.insert("end", decoded_text)
        self.status_label.configure(text="解码完成：结果仅显示在当前窗口。")


if __name__ == "__main__":
    app = DecoderReceiverApp()
    app.mainloop()

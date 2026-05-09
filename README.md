# auto_typer

Windows 平台自动打字软件，适用于无法复制的远程环境

软件截图：
![image](https://github.com/user-attachments/assets/d6287965-2b5c-4151-a0b6-711af5fbed77)

环境说明：
```bash
pip3 install pynput==1.7.7 -i https://pypi.tuna.tsinghua.edu.cn/simple/
pip3 install customtkinter==5.2.2 -i https://pypi.tuna.tsinghua.edu.cn/simple/
pip3 install pyinstaller==6.9.0 -i https://pypi.tuna.tsinghua.edu.cn/simple/
pip3 install reedsolo==1.7.0 -i https://pypi.tuna.tsinghua.edu.cn/simple/
```

打包命令：`pyinstaller --onefile --windowed auto_typer.py`

使用说明：
- 默认模式输出为 `base64`
- 勾选“小写模式”后，输出限制为 `hex`，仅包含 `0-9a-f`
- 增强模式会对数据进行压缩并具备一定的纠错功能
- 解码时需要和输出模式保持一致

注意：
- 需要在 Windows 环境下运行该文件，才能生成 exe 文件
- 非增强模式输出的结果为 base64 编码的字符串，可以用第三方工具解码
- 增强模式输出的结果只能用本程序解码，暂不支持其他第三方工具
- 为了保证纠错功能，增强模式输出的结果长度一般高于非增强模式
- 当文本较多时或远程环境网络不稳定时，优先考虑增强模式（带压缩功能）
- 本工具只适用于小批量的文本信息传输，不适合大规模数据和其他格式文件

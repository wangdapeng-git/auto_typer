# auto_typer
Windows 平台自动打字软件，适用于无法复制的远程环境

软件截图：
![image](https://github.com/user-attachments/assets/d6287965-2b5c-4151-a0b6-711af5fbed77)


环境说明
pip3 install pynput==1.7.7 -i https://pypi.tuna.tsinghua.edu.cn/simple/
pip3 install customtkinter==5.2.2 -i https://pypi.tuna.tsinghua.edu.cn/simple/
pip3 install pyinstaller==6.9.0 -i https://pypi.tuna.tsinghua.edu.cn/simple/
pip3 install reedsolo==1.7.0 -i https://pypi.tuna.tsinghua.edu.cn/simple/

打包命令：pyinstaller --onefile --windowed data_utility/tools/dp_autotype_gui.py 

注意：需要在windows环境下运行该文件，才能生成exe文件

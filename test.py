import pyautogui
import time

# 等待 1 秒，以便你有时间将鼠标移动到目标位置
time.sleep(1)

# 获取当前鼠标位置
x, y = pyautogui.position()
print(f"Current mouse position: ({x}, {y})")

# 模拟鼠标点击
while (1):
    pyautogui.click(x, y)

# 你也可以直接指定坐标进行点击，例如：
# pyautogui.click(100, 200)
import torch
import socket
import time
import os
import struct
import cv2
import numpy as np
import threading
import tkinter as tk
from tkinter import ttk
from PIL import Image, ImageTk

from models.experimental import attempt_load
from utils.general import non_max_suppression, scale_coords
from utils.torch_utils import select_device
from utils.plots import plot_one_box

class Client:
    def __init__(self, server_address):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.connect(server_address)

    def send_command(self, command):
        self.sock.sendall(command.encode('utf-8'))

    def receive_image(self):
        # 接收图像数据的长度和分辨率
        data = self.sock.recv(8)
        while len(data) < 8:
            more_data = self.sock.recv(8 - len(data))
            if not more_data:
                raise Exception("Socket connection broken")
            data += more_data
        info = struct.unpack('lhh', data)
        self.sock.sendall("ok".encode('utf-8'))
        img_data_len = info[0]
        resolution = info[1], info[2]
        # 接收图像数据
        img_data = b''
        while len(img_data) < img_data_len:
            to_read = img_data_len - len(img_data)
            img_data += self.sock.recv(min(to_read, 1024))
        # 检查数据的有效性
        if not img_data:
            print("Received empty image data")
            return None
        # 将图像数据解码为图像
        img = cv2.imdecode(np.frombuffer(img_data, dtype='uint8'), 1)
        if img is None:
            print("Failed to decode image data")
            return None
        return img

    def close(self):
        self.sock.sendall("exit".encode('utf-8'))
        self.sock.close()

def receive_images(client, canvas, processed_canvas):
    try:
        #检测photo文件夹是否存在，不存在则创建
        if not os.path.exists("photo"):
            os.mkdir("photo")

        # 创建一个当前时间命名的文件夹
        global file_path
        file_path = os.path.join("photo", time.strftime("%Y%m%d%H%M%S", time.localtime()))
        os.mkdir(file_path)

        # 初始化模型
        device = select_device('0' if torch.cuda.is_available() else 'cpu')
        model = attempt_load('weights/last.pt', map_location=device)
        model.to(device)
        # 如果使用GPU，就开启半精度浮点数加速
        if device.type != 'cpu':
            model(torch.zeros(1, 3, 640, 640).to(device).type_as(next(model.parameters())))

        while is_connect:
            img = client.receive_image()
            img_time_dis = time.strftime("%Y%m%d%H%M%S", time.localtime()) + '-' +str(distance)

            # 如果不是np.array类型，就跳过
            if not isinstance(img, np.ndarray):
                continue

            img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)

            # 旋转180度
            img = cv2.rotate(img, cv2.ROTATE_180)

            # 调整图像通道顺序为CHW
            img_chw = img.transpose(2, 0, 1)

            # 将图像转换为Tensor
            img_tensor = torch.from_numpy(img_chw).unsqueeze(0).float().to(device) / 255.0
            pred = model(img_tensor)[0]
            pred = non_max_suppression(pred, 0.25, 0.45)

            for i, det in enumerate(pred):
                if len(det):
                    det[:, :4] = scale_coords(img_tensor.shape[2:], det[:, :4], img.shape).round()
            
            processed_img = img.copy()

            # 将图像转换为PIL格式
            img = Image.fromarray(img)
            imgtk = ImageTk.PhotoImage(image=img)
            canvas.create_image(0, 0, anchor=tk.NW, image=imgtk)
            canvas.image = imgtk
            canvas.update()

            # 绘制检测框
            for *xyxy, conf, cls in det:
                label = f'{model.names[int(cls)]} {conf:.2f}'
                plot_one_box(xyxy, processed_img, label=label, line_thickness=3)

            
            # 图片保存到文件夹
            if is_write:
                cv2.imwrite(os.path.join(file_path, f"{img_time_dis}.jpg"), processed_img)

            processed_img = Image.fromarray(processed_img)
            processed_imgtk = ImageTk.PhotoImage(image=processed_img)
            processed_canvas.create_image(0, 0, anchor=tk.NW, image=processed_imgtk)
            processed_canvas.image = processed_imgtk
            processed_canvas.update()

    except Exception as e:
        print(f"An error occurred: {e}")

def main():
    global key_down, is_connect, distance

    key_down = False
    is_connect = False
    distance = 0

    def on_key_press(event):
        global key_down
        key = event.keysym.lower()
        if key_down == True:
            key_down = False
            send_command("stop")    
        else:
            key_down = True
        if key in ('up', 'down', 'left', 'right', 'escape', 'j', 'k', 'w', 's', 'a', 'd', 'f'):
            send_command(key)
        if key == 'n':
            write()
        if key in ('c', 'v', 'b'):
            change_distance(key)

    def connect():
        global client_control, client_camera, is_connect
        ip = ip_entry.get()
        client_camera = Client((ip, 8881))
        client_control = Client((ip, 8880))

        is_connect = True
        receive_thread = threading.Thread(target=receive_images, args=(client_camera, canvas, processed_canvas))
        receive_thread.start()

    def disconnect():
        global client_control, client_camera, is_connect
        if is_connect:
            client_camera.close()
            client_control.close()
            is_connect = False

    def send_command(command):
        global client_control, is_connect
        if is_connect == False:
            return
        client_control.send_command(command)

    def on_closing():
        global client_control, client_camera, is_connect
        if is_connect == False:
            root.destroy()
            return
        client_control.send_command("close") 
        client_camera.send_command("close")
        disconnect()
        root.destroy()

    def open_file():
        if not file_path or not os.path.exists(file_path):
            return
        # disconnect()
        os.system(f"start explorer {file_path}")

    def write():
        global is_write
        if is_write:
            is_write = False
            write_button.config(text="开始保存")
        else:
            is_write = True
            write_button.config(text="停止保存")
    
    def change_distance(command):
        global distance
        if command == 'c':
            distance += 1
        elif command == 'v':
            distance -= 1
        elif command == 'b':
            distance = 0
        distance_value.config(text=distance)
    
    # 创建 Tkinter 界面
    root = tk.Tk()
    root.title("Remote Control")

    # 绑定按键事件
    root.bind('<KeyPress>', on_key_press)

    # 创建输入 IP 地址的部分
    ip_frame=tk.Frame(root)
    ip_frame.grid(column=1,row=0, columnspan=3)

    # 创建输入 IP 地址的标签和输入框
    ip_label = ttk.Label(ip_frame, text="IP:")
    ip_label.grid(column=0, row=0, padx=5, pady=5)
    ip_entry = ttk.Entry(ip_frame)
    ip_entry.grid(column=1, row=0, padx=5, pady=5)

    # 创建连接和断开连接按钮
    connect_button = ttk.Button(ip_frame, text="连接", command=connect)
    connect_button.grid(column=0, row=1, padx=5, pady=5)
    disconnect_button = ttk.Button(ip_frame, text="断开连接", command=disconnect)
    disconnect_button.grid(column=1, row=1, padx=5, pady=5)

    # 点击按钮断开连接并打开保存的图片文件夹
    open_button = ttk.Button(ip_frame, text="打开文件夹", command=open_file)
    open_button.grid(column=0, row=2, padx=5, pady=5)

    # 点击按钮开始或停止保存图片
    global is_write
    is_write = False
    write_button = ttk.Button(ip_frame, text="开始保存", command=write)
    write_button.grid(column=1, row=2, padx=5, pady=5)

    # 实时显示距离
    distance_label = ttk.Label(ip_frame, text="距离:")
    distance_label.grid(column=0, row=3, padx=5, pady=5)
    distance_value = ttk.Label(ip_frame, text=distance)
    distance_value.grid(column=1, row=3, padx=5, pady=5)

    # 创建显示摄像头图像的画布
    canvas = tk.Canvas(root, width=640, height=480)
    canvas.grid(column=0, row=0, columnspan=3, padx=5, pady=5)
    processed_canvas = tk.Canvas(root, width=640, height=480)
    processed_canvas.grid(column=0, row=1, padx=5, pady=5)

    # 创建方向按钮
    button_frame=tk.Frame(root)
    button_frame.grid(column=3,row=1, columnspan=3) 
    button_width = 10

    up_button = ttk.Button(button_frame, text="前进", command=lambda: send_command("up"), width=button_width)
    up_button.grid(column=1, row=0, padx=5, pady=5)

    down_button = ttk.Button(button_frame, text="后退", command=lambda: send_command("down"), width=button_width)
    down_button.grid(column=1, row=2, padx=5, pady=5)

    left_button = ttk.Button(button_frame, text="左转", command=lambda: send_command("left"), width=button_width)
    left_button.grid(column=0, row=1, padx=5, pady=5)

    right_button = ttk.Button(button_frame, text="右转", command=lambda: send_command("right"), width=button_width)
    right_button.grid(column=2, row=1, padx=5, pady=5)

    stop_button = ttk.Button(button_frame, text="停下", command=lambda: send_command("escape"), width=button_width)
    stop_button.grid(column=1, row=1, padx=5, pady=5)

    accelerate_button = ttk.Button(button_frame, text="加速", command=lambda: send_command("j"), width=button_width)
    accelerate_button.grid(column=3, row=0, padx=5, pady=5)

    decelerate_button = ttk.Button(button_frame, text="减速", command=lambda: send_command("k"), width=button_width)
    decelerate_button.grid(column=3, row=2, padx=5, pady=5)

    camera_up_button = ttk.Button(button_frame, text="镜头上移", command=lambda: send_command("w"), width=button_width)
    camera_up_button.grid(column=1, row=3, padx=5, pady=5)

    camera_down_button = ttk.Button(button_frame, text="镜头下移", command=lambda: send_command("s"), width=button_width)
    camera_down_button.grid(column=1, row=5, padx=5, pady=5)

    camera_left_button = ttk.Button(button_frame, text="镜头左移", command=lambda: send_command("a"), width=button_width)
    camera_left_button.grid(column=0, row=4, padx=5, pady=5)

    camera_right_button = ttk.Button(button_frame, text="镜头右移", command=lambda: send_command("d"), width=button_width)
    camera_right_button.grid(column=2, row=4, padx=5, pady=5)

    camera_reset_button = ttk.Button(button_frame, text="镜头回中", command=lambda: send_command("f"), width=button_width)
    camera_reset_button.grid(column=1, row=4, padx=5, pady=5)

    root.protocol("WM_DELETE_WINDOW", on_closing) # 关闭窗口时调用 on_closing 函数
    root.mainloop()

if __name__ == '__main__':
    main()

import socket
import struct
import cv2
import numpy
import threading
import RPi.GPIO as GPIO
import time

class Camera:
    def __init__(self, resolution=(640, 480), fps=30):
        self.resolution = resolution
        self.fps = fps
        self.camera = cv2.VideoCapture(0)

    def get_frame(self):
        _, img = self.camera.read()
        img = cv2.resize(img, self.resolution)
        _, img_encode = cv2.imencode('.jpg', img, [int(cv2.IMWRITE_JPEG_QUALITY), self.fps])
        return numpy.array(img_encode).tobytes()

    def close(self):
        self.camera.release()

class Server:
    def __init__(self, addr_port=('', 8881)):
        self.server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.server.bind(addr_port)
        self.server.listen(5)

    def accept(self):
        return self.server.accept()

#控制
def tonum(num):  # 用于处理角度转换的函数
    fm = 10.0 / 180.0
    num = num * fm + 2.5
    num = int(num * 10) / 10.0
    return num
# 设置编码规范
GPIO.setmode(GPIO.BCM)

# 无视警告，开启引脚
GPIO.setwarnings(False)
servopin1 = 24  #舵机1,方向为左右转
servopin2 = 23   #舵机2,方向为上下转


GPIO.setup(servopin1, GPIO.OUT, initial=False)
GPIO.setup(servopin2, GPIO.OUT, initial=False)
p1 = GPIO.PWM(servopin1,50) #50HZ
p2 = GPIO.PWM(servopin2,50) #50HZ

p1.start(tonum(85)) #初始化角度
p2.start(tonum(80)) #初始化角度
time.sleep(0.5)
p1.ChangeDutyCycle(0) #清除当前占空比，使舵机停止抖动
p2.ChangeDutyCycle(0) #清除当前占空比，使舵机停止抖动
time.sleep(0.1)

c = 9  #云台舵机1初始化角度：90度
d = 8  #云台舵机2初始化角度：80度

q = [0, 10, 20, 30, 40, 50, 60, 70, 80, 90,
 100, 110, 120, 130, 140, 150, 160, 170, 180]  #旋转角度列表


# 定义输出引脚
IN1 = 5
IN2 = 6
IN3 = 13
IN4 = 19

# 定义使能引脚
ENA = 26
ENB = 20

# 设置引脚为输出
GPIO.setup([IN1,IN2,IN3,IN4, ENA, ENB], GPIO.OUT)

#设置pwm频率

pwm_ENB = GPIO.PWM(ENB,2000)
pwm_ENA = GPIO.PWM(ENA,2000)
#pwm启动
pwm_ENA.start(0)
pwm_ENB.start(0)

# 开启控制服务
def ctrl_server():
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    # host = get_host_ip()
    sp = 30
    host = ''
    port = 8880
    s.bind((host, port))
    s.listen(5)
    while True:
        sock, addr = s.accept()
        print('Accept new connection from %s:%s...' % addr)
        sock.send(b'Accept!')
        motor_init()
        is_close = False
        while True:
            data = sock.recv(1024)
            motor_init()
            if data and data.decode('utf-8') == 'close':
                is_close = True
                break
            if not data or data.decode('utf-8') == 'exit':
                break
            elif data.decode('utf-8') == 'up':
                print("diaoyong-sp:",sp)
                up(sp)
            elif data.decode('utf-8') == 'down':
                back(sp)
            elif data.decode('utf-8') == 'left':
                left(sp)
            elif data.decode('utf-8') == 'right':
                right(sp)
            elif data.decode('utf-8') == 'escape':
                stop()
            elif data.decode('utf-8') == 'w':
                ddown() # duo ji hua le
            elif data.decode('utf-8') == 's':
                dup() # shang xia xiang fan
            elif data.decode('utf-8') == 'a':
                dleft()
            elif data.decode('utf-8') == 'd':
                dright()
            elif data.decode('utf-8') == 'f':
                dcenter()
            elif data.decode('utf-8') == 'j':
                sp = sp + 10
                print("jia-sp:",sp)
            elif data.decode('utf-8') == 'k':
                sp = sp - 10
                print("jian-sp:",sp)
            print("get data:" + data.decode('utf-8'))
        print("close connection")
        if is_close:
            sock.close()
            break
    print("bye~")
    GPIO.cleanup()


def dcenter():
    global c,d
    c = 9  #云台舵机1初始化角度：90度
    d = 8  #云台舵机2初始化角度：80度
    p1.start(tonum(85)) #初始化角度
    p2.start(tonum(80)) #初始化角度
    time.sleep(0.5)
    p1.ChangeDutyCycle(0) #清除当前占空比，使舵机停止抖动
    p2.ChangeDutyCycle(0) #清除当前占空比，使舵机停止抖动
    print('laile')

    

def dleft():
    global c   #引入全局变量
    if c < 16:  #判断角度是否大于20度
        c = c+1
        g = q[c]  #调用q列表中的第c位元素
        print('当前角度为',g)
        p1.ChangeDutyCycle(tonum(g))  #执行角度变化，跳转到q列表中对应第c位元素的角度
        time.sleep(0.1)
        p1.ChangeDutyCycle(0)  #清除当前占空比，使舵机停止抖动
        time.sleep(0.01)

       
def dright():
    global c    #引入全局变量
    if c > 2:
        c = c-1
        g = q[c]  #调用q列表中的第c位元素
        print('当前角度为',g)
        p1.ChangeDutyCycle(tonum(g)) #执行角度变化，跳转到q列表中对应第c位元素的角度
        time.sleep(0.1)
        p1.ChangeDutyCycle(0) #清除当前占空比，使舵机停止抖动
        time.sleep(0.01)


def dup():
    global d    #引入全局变量
    if d < 16:
        d = d+1
        g = q[d]  #调用q列表中的第d位元素
        print('当前角度为',g)
        print('laile')
        p2.ChangeDutyCycle(tonum(g)) #执行角度变化，跳转到q列表中对应第d位元素的角度
        time.sleep(0.1)
        p2.ChangeDutyCycle(0) #清除当前占空比，使舵机停止抖动
        time.sleep(0.01)
def ddown():
    global d    #引入全局变量
    if d > 2:
        d = d-1
        g = q[d]  #调用q列表中的第d位元素
        print('当前角度为',g)
        p2.ChangeDutyCycle(tonum(g)) #执行角度变化，跳转到q列表中对应第d位元素的角度
        time.sleep(0.1)
        p2.ChangeDutyCycle(0) #清除当前占空比，使舵机停止抖动
        time.sleep(0.01)
#GPIO初始化状态
def motor_init():
# pwm_ENA and pwm_ENB 是用来控制小车速度的
    GPIO.setmode(GPIO.BCM)
    global pwm_ENA 
    global pwm_ENB
    global delaytime #delaytime 可以用来控制小车的运动时间
    GPIO.setup(ENA,GPIO.OUT,initial=GPIO.HIGH) 
    GPIO.setup(IN1,GPIO.OUT,initial=GPIO.LOW)
    GPIO.setup(IN2,GPIO.OUT,initial=GPIO.LOW)
    GPIO.setup(ENB,GPIO.OUT,initial=GPIO.HIGH)
    GPIO.setup(IN3,GPIO.OUT,initial=GPIO.LOW)
    GPIO.setup(IN4,GPIO.OUT,initial=GPIO.LOW)
    

def up(sp):
    print("up-sp:",sp)
    GPIO.output(IN1,GPIO.HIGH)
    GPIO.output(IN2,GPIO.LOW)  #setting GPIO
    GPIO.output(IN3,GPIO.LOW)
    GPIO.output(IN4,GPIO.HIGH)
    pwm_ENB.ChangeDutyCycle(sp)
    pwm_ENA.ChangeDutyCycle(sp) #setting speed
    #time.sleep(0.1) #setting delaytime
#左转

def left(sp):
    GPIO.setmode(GPIO.BCM)
    GPIO.output(IN1, GPIO.HIGH)
    GPIO.output(IN2, GPIO.LOW)
    GPIO.output(IN3, GPIO.HIGH)
    GPIO.output(IN4, GPIO.LOW)  
    pwm_ENB.ChangeDutyCycle(sp)
    pwm_ENA.ChangeDutyCycle(sp)
#停车
def stop():
    GPIO.setmode(GPIO.BCM)
    GPIO.output(IN1, GPIO.LOW)
    GPIO.output(IN2, GPIO.LOW)
    GPIO.output(IN3, GPIO.LOW)
    GPIO.output(IN4, GPIO.LOW)
    pwm_ENA.ChangeDutyCycle(0)
    pwm_ENB.ChangeDutyCycle(0)
#后退
def back(sp):
    GPIO.setmode(GPIO.BCM)
    GPIO.output(IN1, GPIO.LOW)
    GPIO.output(IN2, GPIO.HIGH)
    GPIO.output(IN3, GPIO.HIGH)
    GPIO.output(IN4, GPIO.LOW)    
    pwm_ENB.ChangeDutyCycle(sp)
    pwm_ENA.ChangeDutyCycle(sp)
def right(sp):
    GPIO.setmode(GPIO.BCM)
    GPIO.output(IN1,GPIO.LOW)
    GPIO.output(IN2,GPIO.HIGH)
    GPIO.output(IN3,GPIO.LOW)
    GPIO.output(IN4,GPIO.HIGH)
    pwm_ENB.ChangeDutyCycle(sp)
    pwm_ENA.ChangeDutyCycle(sp)

# 程序入口
if __name__ == '__main__':
    # 创建 Camera 和 Server 对象
    camera = Camera()
    server = Server()

    # 创建线程
    t_ctrl = threading.Thread(target=ctrl_server, name='LoopThread2')
    t_ctrl.start()


    while True:
        client, addr = server.accept()
        print('Accept new connection from %s:%s...' % addr)
        is_close = False
        while True:
            try:
                frame = camera.get_frame()
                client.send(struct.pack("!qhh", len(frame), *camera.resolution) + frame)
            except ConnectionResetError:
                print("Camera Connection reset by peer.")
            data = client.recv(1024).decode('utf-8')
            if not data or data == 'exit':
                print("Camera Client disconnected")
                break
            elif data and data == 'close':
                print("Camera Client closed")
                is_close = True
                break
        if is_close:
            print("Camera 8881 bye~")
            client.close()
            break
    camera.close()

import tkinter as tk
from tkinter import filedialog, ttk, messagebox
from PIL import Image, ImageTk, ImageOps
import numpy as np
import math
import threading
import time

class FixedStereographicProjectionApp:
    def __init__(self, root):
        self.root = root
        self.root.title("球极投影")
        self.root.geometry("1200x750")
        
        # 首先定义所有变量
        self.original_image = None
        self.projected_image = None
        self.rotation_x = 0
        self.rotation_y = 0
        self.rotation_z = 0
        self.output_size = 400
        self.sphere_radius = 1.0
        self.projection_radius_multiplier = 3.0
        self.auto_update = False
        self.processing_thread = None
        self.is_processing = False
        self.last_update_time = 0
        
        # 进度条变量
        self.progress_var = tk.DoubleVar()
        self.progress_var.set(0)
        
        # 创建主框架
        self.main_frame = ttk.Frame(root, padding="10")
        self.main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # 配置网格权重
        root.columnconfigure(0, weight=1)
        root.rowconfigure(0, weight=1)
        self.main_frame.columnconfigure(0, weight=1)
        self.main_frame.columnconfigure(1, weight=1)
        self.main_frame.columnconfigure(2, weight=1)
        
        # 左侧控制面板
        self.control_frame = ttk.LabelFrame(self.main_frame, text="控制面板", padding="10")
        self.control_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), padx=(0, 10))
        
        # 右侧预览面板
        self.preview_frame = ttk.LabelFrame(self.main_frame, text="预览", padding="10")
        self.preview_frame.grid(row=0, column=1, sticky=(tk.W, tk.E, tk.N, tk.S), padx=(0, 10))
        
        # 右侧结果面板
        self.result_frame = ttk.LabelFrame(self.main_frame, text="投影结果", padding="10")
        self.result_frame.grid(row=0, column=2, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # 设置框架扩展
        for i in range(3):
            self.main_frame.rowconfigure(i, weight=1)
            self.control_frame.rowconfigure(i, weight=0)
            self.preview_frame.rowconfigure(i, weight=1)
            self.result_frame.rowconfigure(i, weight=1)
        
        # 创建控制面板部件
        self.create_controls()
        
        # 创建预览和结果显示区域
        self.create_preview_area()
        self.create_result_area()
        
        # 绑定窗口大小变化事件
        self.root.bind("<Configure>", self.on_window_resize)

    def create_controls(self):
        # 加载图像按钮
        self.load_button = ttk.Button(self.control_frame, text="加载图像", command=self.load_image)
        self.load_button.grid(row=0, column=0, columnspan=2, pady=(0, 10), sticky=(tk.W, tk.E))
        
        # 旋转控制
        ttk.Label(self.control_frame, text="X轴旋转:").grid(row=1, column=0, sticky=tk.W, pady=(10, 0))
        self.x_rotation_scale = ttk.Scale(self.control_frame, from_=0, to=360, orient=tk.HORIZONTAL, 
                                          command=lambda v: self.on_parameter_change('x', float(v)))
        self.x_rotation_scale.grid(row=1, column=1, sticky=(tk.W, tk.E), pady=(10, 0))
        self.x_rotation_label = ttk.Label(self.control_frame, text="0°")
        self.x_rotation_label.grid(row=1, column=2, padx=(5, 0), pady=(10, 0))
        
        ttk.Label(self.control_frame, text="Y轴旋转:").grid(row=2, column=0, sticky=tk.W, pady=(10, 0))
        self.y_rotation_scale = ttk.Scale(self.control_frame, from_=0, to=360, orient=tk.HORIZONTAL, 
                                          command=lambda v: self.on_parameter_change('y', float(v)))
        self.y_rotation_scale.grid(row=2, column=1, sticky=(tk.W, tk.E), pady=(10, 0))
        self.y_rotation_label = ttk.Label(self.control_frame, text="0°")
        self.y_rotation_label.grid(row=2, column=2, padx=(5, 0), pady=(10, 0))
        
        ttk.Label(self.control_frame, text="Z轴旋转:").grid(row=3, column=0, sticky=tk.W, pady=(10, 0))
        self.z_rotation_scale = ttk.Scale(self.control_frame, from_=0, to=360, orient=tk.HORIZONTAL, 
                                          command=lambda v: self.on_parameter_change('z', float(v)))
        self.z_rotation_scale.grid(row=3, column=1, sticky=(tk.W, tk.E), pady=(10, 0))
        self.z_rotation_label = ttk.Label(self.control_frame, text="0°")
        self.z_rotation_label.grid(row=3, column=2, padx=(5, 0), pady=(10, 0))
        
        # 投影参数
        ttk.Label(self.control_frame, text="投影中心:").grid(row=4, column=0, sticky=tk.W, pady=(20, 0))
        self.projection_var = tk.StringVar(value="north")
        ttk.Radiobutton(self.control_frame, text="北极", variable=self.projection_var, 
                       value="north", command=self.on_projection_change).grid(row=4, column=1, sticky=tk.W, pady=(20, 0))
        ttk.Radiobutton(self.control_frame, text="南极", variable=self.projection_var, 
                       value="south", command=self.on_projection_change).grid(row=4, column=2, sticky=tk.W, pady=(20, 0))
        
        ttk.Label(self.control_frame, text="球体半径:").grid(row=5, column=0, sticky=tk.W, pady=(10, 0))
        self.radius_scale = ttk.Scale(self.control_frame, from_=0.5, to=3.0, value=1.0, 
                                      orient=tk.HORIZONTAL, command=self.on_radius_change)
        self.radius_scale.grid(row=5, column=1, sticky=(tk.W, tk.E), pady=(10, 0))
        self.radius_label = ttk.Label(self.control_frame, text="1.0")
        self.radius_label.grid(row=5, column=2, padx=(5, 0), pady=(10, 0))
        
        # 投影半径设置
        ttk.Label(self.control_frame, text="投影半径倍数:").grid(row=6, column=0, sticky=tk.W, pady=(10, 0))
        self.radius_multiplier_scale = ttk.Scale(self.control_frame, from_=0.1, to=2.0, value=0.5, 
                                                 orient=tk.HORIZONTAL, command=self.on_radius_multiplier_change)
        self.radius_multiplier_scale.grid(row=6, column=1, sticky=(tk.W, tk.E), pady=(10, 0))
        self.radius_multiplier_label = ttk.Label(self.control_frame, text="0.5")
        self.radius_multiplier_label.grid(row=6, column=2, padx=(5, 0), pady=(10, 0))
        
        # 自动/手动更新选项
        self.auto_update_var = tk.BooleanVar(value=False)
        self.auto_update_check = ttk.Checkbutton(self.control_frame, text="自动更新预览", 
                                                 variable=self.auto_update_var, 
                                                 command=self.on_auto_update_change)
        self.auto_update_check.grid(row=7, column=0, columnspan=3, pady=(20, 0), sticky=tk.W)
        
        # 处理按钮
        self.process_button = ttk.Button(self.control_frame, text="手动更新预览", command=self.manual_update)
        self.process_button.grid(row=8, column=0, columnspan=3, pady=(10, 0), sticky=(tk.W, tk.E))
        
        # 进度条
        self.progress_bar = ttk.Progressbar(self.control_frame, variable=self.progress_var, maximum=100)
        self.progress_bar.grid(row=9, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=(10, 0))
        
        # 保存按钮
        self.save_button = ttk.Button(self.control_frame, text="保存结果", command=self.save_image, state=tk.DISABLED)
        self.save_button.grid(row=10, column=0, columnspan=3, pady=(10, 0), sticky=(tk.W, tk.E))
        
        # 状态标签
        self.status_label = ttk.Label(self.control_frame, text="请加载一张图像")
        self.status_label.grid(row=11, column=0, columnspan=3, pady=(20, 0))

    def create_preview_area(self):
        # 预览画布
        self.preview_canvas = tk.Canvas(self.preview_frame, bg="lightgray", width=300, height=300)
        self.preview_canvas.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), pady=(0, 10))
        
        # 预览标签
        self.preview_label = ttk.Label(self.preview_frame, text="无图像")
        self.preview_label.grid(row=1, column=0)
        
        # 预览图像引用
        self.preview_photo = None

    def create_result_area(self):
        # 结果画布
        self.result_canvas = tk.Canvas(self.result_frame, bg="lightgray", width=400, height=400)
        self.result_canvas.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), pady=(0, 10))
        
        # 结果标签
        self.result_label = ttk.Label(self.result_frame, text="投影结果将显示在这里")
        self.result_label.grid(row=1, column=0)
        
        # 结果图像引用
        self.result_photo = None

    def load_image(self):
        file_path = filedialog.askopenfilename(
            title="选择图像文件",
            filetypes=[("图像文件", "*.png *.jpg *.jpeg *.bmp *.gif *.tiff")]
        )
        
        if file_path:
            try:
                self.original_image = Image.open(file_path).convert("RGB")
                self.update_preview()
                self.status_label.config(text=f"已加载: {file_path.split('/')[-1]}")
                if self.auto_update_var.get():
                    self.start_processing_thread()
            except Exception as e:
                self.status_label.config(text=f"加载图像失败: {str(e)}")

    def update_preview(self):
        if self.original_image:
            # 调整预览大小
            preview_size = (300, 300)
            preview_img = self.original_image.copy()
            preview_img.thumbnail(preview_size, Image.Resampling.LANCZOS)
            
            # 转换为PhotoImage并显示
            self.preview_photo = ImageTk.PhotoImage(preview_img)
            self.preview_canvas.delete("all")
            self.preview_canvas.create_image(
                150, 150, image=self.preview_photo, anchor=tk.CENTER
            )
            self.preview_label.config(text=f"原始图像: {self.original_image.size[0]}×{self.original_image.size[1]}")

    def on_parameter_change(self, axis, value):
        if axis == 'x':
            self.rotation_x = value
            self.x_rotation_label.config(text=f"{value:.1f}°")
        elif axis == 'y':
            self.rotation_y = value
            self.y_rotation_label.config(text=f"{value:.1f}°")
        elif axis == 'z':
            self.rotation_z = value
            self.z_rotation_label.config(text=f"{value:.1f}°")
        
        if self.auto_update_var.get() and self.original_image:
            self.start_processing_thread()

    def on_projection_change(self):
        if self.auto_update_var.get() and self.original_image:
            self.start_processing_thread()

    def on_radius_change(self, value):
    # 将字符串转换为浮点数
        self.sphere_radius = float(value)
    # 使用浮点数进行格式化
        self.radius_label.config(text=f"{self.sphere_radius:.2f}")
    
        if self.auto_update_var.get() and self.original_image:
            self.start_processing_thread()

    def on_radius_multiplier_change(self, value):
    # 将字符串转换为浮点数
        self.projection_radius_multiplier = float(value)
    # 使用浮点数进行格式化
        self.radius_multiplier_label.config(text=f"{self.projection_radius_multiplier:.1f}")
    
        if self.auto_update_var.get() and self.original_image:
            self.start_processing_thread()

    def on_auto_update_change(self):
        self.auto_update = self.auto_update_var.get()

    def manual_update(self):
        if self.original_image:
            self.start_processing_thread()

    def start_processing_thread(self):
        # 防止重复启动处理线程
        if self.is_processing:
            return
            
        # 创建新线程处理图像
        self.is_processing = True
        self.processing_thread = threading.Thread(target=self.process_image_thread)
        self.processing_thread.daemon = True
        self.processing_thread.start()

    def process_image_thread(self):
        try:
            # 获取当前时间，用于防抖
            current_time = time.time()
            if current_time - self.last_update_time < 0.1:  # 100ms防抖
                time.sleep(0.1)
            
            self.last_update_time = current_time
            
            # 在主线程中更新UI
            self.root.after(0, lambda: self.status_label.config(text="正在处理..."))
            self.root.after(0, lambda: self.progress_var.set(0))
            
            # 获取原始图像尺寸
            width, height = self.original_image.size
            
            # 转换为numpy数组
            img_array = np.array(self.original_image)
            
            # 创建输出图像
            output_array = np.zeros((self.output_size, self.output_size, 3), dtype=np.uint8)
            
            # 将角度转换为弧度
            rx = math.radians(self.rotation_x)
            ry = math.radians(self.rotation_y)
            rz = math.radians(self.rotation_z)
            
            # 旋转矩阵
            Rx = np.array([
                [1, 0, 0],
                [0, math.cos(rx), -math.sin(rx)],
                [0, math.sin(rx), math.cos(rx)]
            ])
            
            Ry = np.array([
                [math.cos(ry), 0, math.sin(ry)],
                [0, 1, 0],
                [-math.sin(ry), 0, math.cos(ry)]
            ])
            
            Rz = np.array([
                [math.cos(rz), -math.sin(rz), 0],
                [math.sin(rz), math.cos(rz), 0],
                [0, 0, 1]
            ])
            
            # 组合旋转矩阵
            R = np.dot(Rz, np.dot(Ry, Rx))
            
            # 投影中心选择
            projection_north = (self.projection_var.get() == "north")
            
            # 对于输出图像的每个像素
            center = self.output_size // 2
            # 将投影半径扩大指定倍数
            max_distance = center * 0.9 * self.projection_radius_multiplier
            
            total_pixels = self.output_size * self.output_size
            processed_pixels = 0
            
            for y in range(self.output_size):
                for x in range(self.output_size):
                    # 将像素坐标转换为归一化坐标
                    nx = (x - center) / max_distance
                    ny = (y - center) / max_distance
                    
                    # 计算到原点的距离
                    r2 = nx * nx + ny * ny
                    
                    # 球极投影反变换
                    if projection_north:
                        # 从北极投影
                        X = 2 * nx / (1 + r2)
                        Y = 2 * ny / (1 + r2)
                        Z = (1 - r2) / (1 + r2)
                    else:
                        # 从南极投影
                        X = 2 * nx / (1 + r2)
                        Y = 2 * ny / (1 + r2)
                        Z = -(1 - r2) / (1 + r2)
                    
                    # 应用球体半径
                    X *= self.sphere_radius
                    Y *= self.sphere_radius
                    Z *= self.sphere_radius
                    
                    # 应用旋转
                    point = np.array([X, Y, Z])
                    rotated_point = np.dot(R, point)
                    
                    # 转换为球面坐标
                    r = np.linalg.norm(rotated_point)
                    if r == 0:
                        processed_pixels += 1
                        continue
                    
                    # 计算球面坐标
                    theta = math.atan2(rotated_point[1], rotated_point[0])  # 经度
                    phi = math.acos(rotated_point[2] / r)  # 纬度
                    
                    # 将球面坐标映射到原始图像坐标
                    u = (theta + math.pi) / (2 * math.pi) * (width - 1)
                    v = phi / math.pi * (height - 1)
                    
                    # 双线性插值
                    u1, v1 = int(u), int(v)
                    u2, v2 = min(u1 + 1, width - 1), min(v1 + 1, height - 1)
                    
                    # 计算权重
                    du, dv = u - u1, v - v1
                    
                    # 获取四个相邻像素
                    if 0 <= u1 < width and 0 <= v1 < height:
                        c11 = img_array[v1, u1]
                        c12 = img_array[v1, u2] if u2 < width else c11
                        c21 = img_array[v2, u1] if v2 < height else c11
                        c22 = img_array[v2, u2] if u2 < width and v2 < height else c11
                        
                        # 插值计算颜色
                        color = (
                            (1 - du) * (1 - dv) * c11 +
                            du * (1 - dv) * c12 +
                            (1 - du) * dv * c21 +
                            du * dv * c22
                        )
                        
                        output_array[y, x] = color
                    
                    processed_pixels += 1
                
                # 更新进度条
                if y % 20 == 0:  # 每20行更新一次进度
                    progress = (y * self.output_size) / total_pixels * 100
                    self.root.after(0, lambda p=progress: self.progress_var.set(p))
            
            # 转换为PIL图像
            self.projected_image = Image.fromarray(output_array, 'RGB')
            
            # 在主线程中显示结果
            self.root.after(0, self.display_result)
            self.root.after(0, lambda: self.save_button.config(state=tk.NORMAL))
            self.root.after(0, lambda: self.status_label.config(text="处理完成"))
            self.root.after(0, lambda: self.progress_var.set(100))
            
        except Exception as e:
            self.root.after(0, lambda: self.status_label.config(text=f"处理失败: {str(e)}"))
        finally:
            self.is_processing = False

    def display_result(self):
        if self.projected_image:
            # 调整显示大小
            display_img = self.projected_image.copy()
            display_img.thumbnail((400, 400), Image.Resampling.LANCZOS)
            
            # 转换为PhotoImage并显示
            self.result_photo = ImageTk.PhotoImage(display_img)
            self.result_canvas.delete("all")
            self.result_canvas.create_image(
                200, 200, image=self.result_photo, anchor=tk.CENTER
            )
            
            # 绘制圆形边界
            center = 200
            radius = 200 * 0.9
            self.result_canvas.create_oval(
                center - radius, center - radius,
                center + radius, center + radius,
                outline="red", width=2
            )
            
            self.result_label.config(text=f"投影结果: {self.projected_image.size[0]}×{self.projected_image.size[1]} (半径倍数: {self.projection_radius_multiplier})")

    def save_image(self):
        if self.projected_image:
            file_path = filedialog.asksaveasfilename(
                title="保存投影结果",
                defaultextension=".png",
                filetypes=[("PNG文件", "*.png"), ("JPEG文件", "*.jpg"), ("所有文件", "*.*")]
            )
            
            if file_path:
                try:
                    # 保存完整分辨率的图像
                    self.projected_image.save(file_path)
                    self.status_label.config(text=f"已保存到: {file_path}")
                except Exception as e:
                    self.status_label.config(text=f"保存失败: {str(e)}")

    def on_window_resize(self, event):
        # 可以根据窗口大小调整布局
        pass

def main():
    root = tk.Tk()
    app = FixedStereographicProjectionApp(root)
    root.mainloop()

if __name__ == "__main__":
    main()

import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import cv2
from PIL import Image, ImageTk
import os
from moviepy.editor import VideoFileClip, AudioFileClip
import tempfile


class VideoCropperApp:
    def __init__(self, master):
        self.master = master
        master.title("视频裁切工具 v2.0")

        # 状态变量初始化
        self.input_path = tk.StringVar()
        self.output_path = tk.StringVar()
        self.size_info = tk.StringVar(value="尺寸：未选择")
        self.crop_coords = None
        self.original_size = (0, 0)
        self.scale_x = 1.0
        self.scale_y = 1.0
        self.img_x = 0
        self.img_y = 0
        self.new_w = 0
        self.new_h = 0
        self.crop_mode = "free"
        self.lock = False
        self.rect = None
        self.current_img = None
        self.start_x = 0
        self.start_y = 0
        self.width_var = tk.StringVar()
        self.height_var = tk.StringVar()
        # 新增路径记忆属性
        # self.last_input_path = os.path.expanduser("~")  # 默认用户主目录
        # self.last_output_path = os.path.expanduser("~")
        # 默认使用当前目录
        self.last_input_path = os.path.abspath(os.path.curdir)
        self.last_output_path = os.path.abspath(os.path.curdir)
        # 界面初始化
        self.create_widgets()
        self.bind_events()

        # 窗口居中显示
        self.center_window()

    def center_window(self):
        """使窗口居中显示"""
        self.master.update_idletasks()
        width = self.master.winfo_width()
        height = self.master.winfo_height()
        screen_width = self.master.winfo_screenwidth()
        screen_height = self.master.winfo_screenheight()
        x = (screen_width - width) // 2
        y = (screen_height - height) // 2
        self.master.geometry(f"+{x}+{y}")

    def create_widgets(self):
        """优化后的控件布局"""
        # 输入路径区域
        input_frame = tk.Frame(self.master)
        input_frame.grid(row=0, column=0, columnspan=3, padx=10, pady=5, sticky="ew")
        tk.Label(input_frame, text="输入视频:").pack(side=tk.LEFT, padx=5)
        tk.Entry(input_frame, textvariable=self.input_path, width=50).pack(
            side=tk.LEFT, expand=True
        )
        tk.Button(input_frame, text="浏览", command=self.select_input).pack(
            side=tk.LEFT, padx=5
        )

        # 输出路径区域
        output_frame = tk.Frame(self.master)
        output_frame.grid(row=1, column=0, columnspan=3, padx=10, pady=5, sticky="ew")
        tk.Label(output_frame, text="输出目录:").pack(side=tk.LEFT, padx=5)
        tk.Entry(output_frame, textvariable=self.output_path, width=50).pack(
            side=tk.LEFT, expand=True
        )
        tk.Button(output_frame, text="浏览", command=self.select_output).pack(
            side=tk.LEFT, padx=5
        )

        # 控制面板
        control_frame = tk.Frame(self.master)
        control_frame.grid(row=2, column=0, columnspan=3, pady=10, sticky="ew")

        # 模式选择
        mode_frame = tk.Frame(control_frame)
        mode_frame.pack(side=tk.LEFT, padx=20)
        tk.Label(mode_frame, text="裁切模式:").pack(side=tk.LEFT)
        self.mode_combobox = ttk.Combobox(
            mode_frame, values=["自由选择", "1:1 正方形"], width=10
        )
        self.mode_combobox.pack(side=tk.LEFT, padx=5)
        self.mode_combobox.current(0)

        # 尺寸显示
        self.size_label = tk.Label(
            control_frame, textvariable=self.size_info, fg="blue", width=25
        )
        self.size_label.pack(side=tk.LEFT, padx=20)

        # 操作按钮组
        btn_frame = tk.Frame(control_frame)
        btn_frame.pack(side=tk.RIGHT, padx=20)
        self.reset_btn = tk.Button(
            btn_frame, text="重置绘制", command=self.reset_canvas
        )
        self.reset_btn.pack(side=tk.LEFT, padx=5)
        self.lock_btn = tk.Button(btn_frame, text="锁定尺寸", command=self.toggle_lock)
        self.lock_btn.pack(side=tk.LEFT, padx=5)

        # 输出尺寸区域
        size_frame = tk.Frame(self.master)
        size_frame.grid(row=3, column=0, columnspan=3, pady=5, sticky="ew")

        # 尺寸输入组件
        size_input_frame = tk.Frame(size_frame)
        size_input_frame.pack(side=tk.LEFT, padx=20)
        tk.Label(size_input_frame, text="输出尺寸:").pack(side=tk.LEFT)
        self.width_combo = ttk.Combobox(
            size_input_frame,
            textvariable=self.width_var,
            values=["", "1920", "1280", "1080", "720"],
            width=6,
        )
        self.width_combo.pack(side=tk.LEFT, padx=2)
        tk.Label(size_input_frame, text="×").pack(side=tk.LEFT)
        self.height_combo = ttk.Combobox(
            size_input_frame,
            textvariable=self.height_var,
            values=["", "1080", "720", "480", "360"],
            width=6,
        )
        self.height_combo.pack(side=tk.LEFT, padx=2)
        tk.Label(size_input_frame, text="px").pack(side=tk.LEFT)

        # 开始裁切按钮
        self.process_btn = tk.Button(
            size_frame, text="开始裁切", command=self.process_video, width=15
        )
        self.process_btn.pack(side=tk.RIGHT, padx=20)

        # 预览画布
        self.canvas = tk.Canvas(
            self.master, width=800, height=500, bg="black", cursor="crosshair"
        )
        self.canvas.grid(row=4, column=0, columnspan=3, padx=10, pady=10, sticky="nsew")

        # 窗口尺寸适配
        self.master.columnconfigure(0, weight=1)
        self.master.rowconfigure(4, weight=1)

    def get_target_size(self):
        """智能尺寸计算"""
        try:
            width = int(self.width_var.get()) if self.width_var.get() else 0
            height = int(self.height_var.get()) if self.height_var.get() else 0
        except ValueError:
            messagebox.showerror("错误", "尺寸必须为整数")
            return None

        # 正方形模式特殊处理
        if self.mode_combobox.get() == "1:1 正方形":
            valid_sizes = [s for s in [width, height] if s > 0]
            if not valid_sizes:
                return None
            size = min(valid_sizes) if len(valid_sizes) > 1 else valid_sizes[0]
            return (size, size)

        # 自动比例计算
        if not hasattr(self, "crop_coords") or not self.crop_coords:
            return (width or None, height or None)

        orig_width = self.crop_coords[2] - self.crop_coords[0]
        orig_height = self.crop_coords[3] - self.crop_coords[1]

        # 计算缺失的尺寸
        if width <= 0 and height <= 0:
            return None
        if width <= 0:
            width = int(height * orig_width / orig_height)
        if height <= 0:
            height = int(width * orig_height / orig_width)

        return (max(1, width), max(1, height))

    def bind_events(self):
        """绑定画布事件"""
        self.canvas.bind("<ButtonPress-1>", self.start_rect)
        self.canvas.bind("<B1-Motion>", self.draw_rect)
        self.canvas.bind("<ButtonRelease-1>", self.end_rect)

    def unbind_events(self):
        """解绑画布事件"""
        self.canvas.unbind("<ButtonPress-1>")
        self.canvas.unbind("<B1-Motion>")
        self.canvas.unbind("<ButtonRelease-1>")

    def toggle_lock(self):
        """切换锁定状态"""
        self.lock = not self.lock
        self.lock_btn.config(
            text="解锁尺寸" if self.lock else "锁定尺寸",
            bg="#90EE90" if self.lock else "SystemButtonFace",
        )
        if self.lock:
            self.unbind_events()
        else:
            self.bind_events()

    def reset_canvas(self):
        """重置画布状态"""
        if self.rect:
            self.canvas.delete(self.rect)
            self.rect = None
        self.size_info.set("尺寸：未选择")
        self.crop_coords = None
        if self.lock:
            self.toggle_lock()  # 自动解除锁定
        self.show_preview()

    def select_input(self):
        """智能路径选择与自动输出目录设置"""
        initial_dir = self._get_smart_initial_dir(
            self.input_path.get(), self.last_input_path
        )

        path = filedialog.askopenfilename(
            title="选择输入视频",
            initialdir=initial_dir,
            filetypes=[("视频文件", "*.mp4 *.avi *.mov")],
        )

        if not path:
            return

        # 更新输入路径
        self.input_path.set(path)
        input_dir = os.path.dirname(path)
        self.last_input_path = input_dir

        # 自动设置输出目录
        if not self.output_path.get():
            self.output_path.set(input_dir)
            self.last_output_path = input_dir

        self.reset_canvas()

    def select_output(self):
        """保留原有逻辑，但使用更新后的记忆路径"""
        initial_dir = self._get_smart_initial_dir(
            self.output_path.get(), self.last_output_path
        )

        path = filedialog.askdirectory(title="选择输出目录", initialdir=initial_dir)

        if path:
            self.output_path.set(path)
            self.last_output_path = path

    def _get_smart_initial_dir(self, current_path, last_path):
        """智能判断初始目录的优先级"""
        if current_path and os.path.exists(current_path):
            return (
                os.path.dirname(current_path)
                if os.path.isfile(current_path)
                else current_path
            )
        if last_path and os.path.exists(last_path):
            return last_path
        return os.path.expanduser("~")  # 默认回退到用户目录

    def show_preview(self):
        """优化后的预览显示方法"""
        if not os.path.exists(self.input_path.get()):
            return

        # 清空画布并重置背景
        self.canvas.delete("all")
        self.canvas.config(bg="#F0F0F0")  # 改为浅灰色背景

        cap = cv2.VideoCapture(self.input_path.get())
        ret, frame = cap.read()
        if not ret:
            messagebox.showerror("错误", "无法读取视频")
            return

        # 计算缩放后的显示尺寸
        orig_w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        orig_h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        self.original_size = (orig_w, orig_h)

        # 计算保持比例的显示尺寸
        canvas_w = self.canvas.winfo_width()
        canvas_h = self.canvas.winfo_height()
        ratio = min(canvas_w / orig_w, canvas_h / orig_h)
        self.new_w = int(orig_w * ratio)
        self.new_h = int(orig_h * ratio)
        self.scale_x = orig_w / self.new_w
        self.scale_y = orig_h / self.new_h

        # 计算居中位置
        self.img_x = (canvas_w - self.new_w) // 2
        self.img_y = (canvas_h - self.new_h) // 2

        # 绘制预览边界框
        self.draw_preview_border()

        # 转换并显示图像
        resized = cv2.resize(frame, (self.new_w, self.new_h))
        img = cv2.cvtColor(resized, cv2.COLOR_BGR2RGB)
        self.preview_img = ImageTk.PhotoImage(Image.fromarray(img))

        # 创建图像对象并居中显示
        self.canvas.create_image(
            self.img_x,
            self.img_y,
            anchor=tk.NW,
            image=self.preview_img,
            tags="video_preview",
        )
        cap.release()

    def draw_preview_border(self):
        """绘制视频预览边界框"""
        # 绘制浅灰色背景底板
        self.canvas.create_rectangle(
            self.img_x - 1,
            self.img_y - 1,
            self.img_x + self.new_w + 1,
            self.img_y + self.new_h + 1,
            fill="#84fab0",
            outline="#8fd3f4",
            width=2,
            tags="preview_border",
        )

        # 添加文字提示
        self.canvas.create_text(
            self.img_x + 10,
            self.img_y + 15,
            text="视频预览区域",
            fill="#606060",
            anchor=tk.NW,
            font=("微软雅黑", 9),
            tags="preview_text",
        )

    def start_rect(self, event):
        """开始绘制矩形"""
        if self.rect and not self.lock:
            messagebox.showwarning("提示", "请先点击重置按钮清除当前绘制框！")
            return
        if self.lock:
            return

        # 转换为有效坐标
        x, y = event.x, event.y
        if not (
            self.img_x <= x <= self.img_x + self.new_w
            and self.img_y <= y <= self.img_y + self.new_h
        ):
            return

        # 记录起始点（原始视频坐标）
        self.start_x = (x - self.img_x) * self.scale_x
        self.start_y = (y - self.img_y) * self.scale_y

        # 创建矩形对象
        self.rect = self.canvas.create_rectangle(x, y, x, y, outline="red", width=2)

    def draw_rect(self, event):
        """修复后的动态绘制逻辑"""
        if not self.rect or self.lock:
            return

        # 限制在视频显示区域内
        x = max(self.img_x, min(event.x, self.img_x + self.new_w))
        y = max(self.img_y, min(event.y, self.img_y + self.new_h))

        # 转换为原始视频坐标
        current_x = (x - self.img_x) * self.scale_x
        current_y = (y - self.img_y) * self.scale_y

        # 正方形模式处理
        if self.mode_combobox.get() == "1:1 正方形":
            dx = current_x - self.start_x
            dy = current_y - self.start_y

            # 计算方向符号
            x_sign = 1 if dx >= 0 else -1
            y_sign = 1 if dy >= 0 else -1

            # 计算最大可用边长（考虑四个方向）
            max_side_x = (
                self.original_size[0] - self.start_x if x_sign > 0 else self.start_x
            )
            max_side_y = (
                self.original_size[1] - self.start_y if y_sign > 0 else self.start_y
            )
            max_side = min(abs(dx), abs(dy), max_side_x, max_side_y)

            # 应用符号和边长
            current_x = self.start_x + x_sign * max_side
            current_y = self.start_y + y_sign * max_side

            # 强制保证正方形
            side = min(abs(current_x - self.start_x), abs(current_y - self.start_y))
            current_x = self.start_x + x_sign * side
            current_y = self.start_y + y_sign * side

            # 二次边界检查
            current_x = max(0, min(current_x, self.original_size[0]))
            current_y = max(0, min(current_y, self.original_size[1]))

            # 转换回显示坐标
            x = self.img_x + (current_x / self.scale_x)
            y = self.img_y + (current_y / self.scale_y)

        # 更新矩形显示坐标
        start_display_x = self.img_x + (self.start_x / self.scale_x)
        start_display_y = self.img_y + (self.start_y / self.scale_y)
        self.canvas.coords(self.rect, start_display_x, start_display_y, x, y)

        # 更新尺寸显示
        self.update_size_info(current_x, current_y)

    def update_size_info(self, end_x, end_y):
        """更新尺寸显示（增加单位提示）"""
        width = int(abs(end_x - self.start_x))
        height = int(abs(end_y - self.start_y))

        if width == 0 or height == 0:
            self.size_info.set("尺寸：未选择")
            return

        if self.mode_combobox.get() == "1:1 正方形":
            info = f"边长：{width}像素"
        else:
            info = f"宽：{width}像素 高：{height}像素"

        # 增加分辨率限制提示
        if width < 10 or height < 10:
            info += " (尺寸过小)"
        elif width > self.original_size[0] or height > self.original_size[1]:
            info += " (超出范围)"

        self.size_info.set(f"当前尺寸：{info}")

    def end_rect(self, event):
        """修复后的结束绘制逻辑"""
        if not self.rect or self.lock:
            return

        # 最终坐标处理
        x = max(self.img_x, min(event.x, self.img_x + self.new_w))
        y = max(self.img_y, min(event.y, self.img_y + self.new_h))

        # 转换为原始坐标
        end_x = (x - self.img_x) * self.scale_x
        end_y = (y - self.img_y) * self.scale_y

        # 保存有效坐标
        self.crop_coords = (
            int(min(self.start_x, end_x)),
            int(min(self.start_y, end_y)),
            int(max(self.start_x, end_x)),
            int(max(self.start_y, end_y)),
        )
        # 强制正方形最终坐标
        if self.mode_combobox.get() == "1:1 正方形":
            x1, y1, x2, y2 = self.crop_coords
            side = min(abs(x2 - x1), abs(y2 - y1))

            # 根据拖动方向调整坐标
            new_x2 = x1 + side if x2 > x1 else x1 - side
            new_y2 = y1 + side if y2 > y1 else y1 - side

            # 二次边界限制
            new_x2 = max(0, min(new_x2, self.original_size[0]))
            new_y2 = max(0, min(new_y2, self.original_size[1]))

            self.crop_coords = (
                int(min(x1, new_x2)),
                int(min(y1, new_y2)),
                int(max(x1, new_x2)),
                int(max(y1, new_y2)),
            )
        print(f"Debug - Final Crop Coords: {self.crop_coords}")  # 调试输出

    def process_video(self):
        if not self.validate_inputs():
            return

        # 创建临时目录
        temp_dir = tempfile.mkdtemp()
        temp_video_path = os.path.join(temp_dir, "temp_video.mp4")

        try:
            # 处理视频（无音频版本）
            self.process_video_without_audio(temp_video_path)

            # 合并音频
            final_path = self.add_audio_to_video(temp_video_path)

            messagebox.showinfo("完成", f"视频已保存至:\n{final_path}")
        except Exception as e:
            messagebox.showerror("错误", f"处理失败: {str(e)}")
        finally:
            # 清理临时文件
            if os.path.exists(temp_dir):
                for f in os.listdir(temp_dir):
                    os.remove(os.path.join(temp_dir, f))
                os.rmdir(temp_dir)

    def process_video_without_audio(self, output_path):
        """修复视频流处理逻辑"""
        x1, y1, x2, y2 = self.crop_coords
        target_size = self.get_target_size()

        cap = cv2.VideoCapture(self.input_path.get())
        if not cap.isOpened():
            raise RuntimeError("无法打开视频文件")

        fps = cap.get(cv2.CAP_PROP_FPS)
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))

        # 正确设置视频编码参数
        fourcc = cv2.VideoWriter_fourcc(*"mp4v")
        final_size = target_size if target_size else (x2 - x1, y2 - y1)
        out = cv2.VideoWriter(output_path, fourcc, fps, final_size)

        try:
            frame_count = 0
            while True:
                ret, frame = cap.read()
                if not ret:
                    break

                # 执行裁切和缩放
                cropped = frame[y1:y2, x1:x2]
                if target_size:
                    cropped = cv2.resize(cropped, target_size)

                # 写入处理后的帧
                out.write(cropped)
                frame_count += 1

                # 进度显示（可选）
                if frame_count % 10 == 0:
                    print(f"处理进度: {frame_count}/{total_frames} 帧")

        except Exception as e:
            raise RuntimeError(f"视频处理失败: {str(e)}")
        finally:
            # 确保在最后释放资源
            cap.release()
            out.release()
            print("视频流资源已释放")

    def add_audio_to_video(self, video_path):
        """优化音视频合并逻辑"""
        final_path = os.path.join(
            self.output_path.get(), f"cropped_{os.path.basename(self.input_path.get())}"
        )

        try:
            # 加载原始视频信息
            original_clip = VideoFileClip(self.input_path.get())
            video_clip = VideoFileClip(video_path)

            # 同步时间信息
            if original_clip.audio is not None:
                # 保持音频与视频时长一致
                audio_clip = original_clip.audio.subclip(0, video_clip.duration)
                final_clip = video_clip.set_audio(audio_clip)
            else:
                final_clip = video_clip

            # 优化输出参数
            final_clip.write_videofile(
                final_path,
                codec="libx264",
                audio_codec="aac",
                ffmpeg_params=["-movflags", "faststart"],  # 优化网络播放
                threads=4,  # 使用多线程加速
            )
            return final_path
        except Exception as e:
            # 异常处理优化
            error_msg = f"音视频合并失败: {str(e)}\n已保存中间文件: {video_path}"
            messagebox.showwarning("警告", error_msg)
            return video_path

    def validate_inputs(self):
        """验证输入合法性"""
        errors = []
        if not self.input_path.get():
            errors.append("请选择输入视频")
        if not self.output_path.get():
            errors.append("请选择输出目录")
        if not self.crop_coords:
            errors.append("请先绘制裁切区域")
        elif (self.crop_coords[2] - self.crop_coords[0]) <= 0 or (
            self.crop_coords[3] - self.crop_coords[1]
        ) <= 0:
            errors.append("裁切尺寸无效")
        # ... [原有验证不变，增加尺寸验证] ...
        try:
            if self.width_var.get():
                int(self.width_var.get())
            if self.height_var.get():
                int(self.height_var.get())
        except ValueError:
            errors.append("输出尺寸必须为整数")
        if errors:
            messagebox.showerror("输入错误", "\n".join(errors))
            return False
        return True


if __name__ == "__main__":
    root = tk.Tk()
    app = VideoCropperApp(root)
    root.mainloop()

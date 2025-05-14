# gunicorn_config.py
import os
import multiprocessing

# 绑定地址
bind = "0.0.0.0:" + os.environ.get("PORT", "8080")

# 工作进程数量 - 使用CPU核心数的2倍
workers = multiprocessing.cpu_count() * 2 + 1

# 工作模式
worker_class = "gevent"

# 禁用自动monkey patching，因为我们已经在wsgi.py中手动处理了
gevent_monkey_patching = False

# 超时设置 - 增加到300秒，因为Gemini API调用可能需要较长时间
timeout = 300

# 日志配置
accesslog = "-"  # 输出到标准输出
errorlog = "-"   # 输出到标准错误
loglevel = "info"

# 预加载应用
preload_app = True

# 保持连接超时
keepalive = 65

# 允许重启工作进程
graceful_timeout = 30

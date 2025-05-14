"""
OSINT 安全风险调查工具后端 API

这个Flask应用提供了一个HTTP POST接口，接收机构名称、国家和风险列表，
然后使用Google Gemini API进行调查，返回结构化的调查结果。

代码已重构为模块化结构:
- app.py: 主应用入口
- config.py: 配置相关代码
- gemini_service.py: Gemini API调用相关功能
- response_parser.py: 响应解析功能
- routes.py: API路由定义
"""

import os
from flask import Flask, request, jsonify
from flask_cors import CORS
from config import logger
from routes import register_routes
# 只导入fixed_deepsearch_new.py中的蓝图
from fixed_deepsearch_new import fixed_deepsearch_bp
from deepsearch_simple import deepsearch_simple_bp

# 注意：不要导入deepsearch.py中的蓝图，以避免路由冲突

# 创建Flask应用
app = Flask(__name__, static_url_path='', static_folder='static')

# 配置CORS - 增强对SSE的支持
# 注意：当supports_credentials为True时，origins不能为*，必须指定具体域名

# 自定义origin处理函数，确保返回的值不含分号
def cors_origin_check(origin):
    """CORS源检查函数，确保返回的值不含分号"""
    print(f"CORS origin_check called with: '{origin}'")
    
    # 定义允许的源
    allowed_origins = [
        "https://deepdriverfront.vercel.app", 
        "http://localhost:5173", 
        "http://localhost:3000",
        "http://localhost:8080",  # Vite默认端口
        "http://127.0.0.1:61694",  # Cascade浏览器集成端口
        "http://127.0.0.1:8080"  # 使用IP地址访问的Vite
    ]
    
    # 检查origin是否为None
    if origin is None:
        print("Origin is None, returning None")
        return None
    
    # 检查origin是否包含分号
    if ';' in origin:
        print(f"WARNING: Received origin '{origin}' contains semicolon, cleaning it")
        # 清理origin，移除分号
        cleaned_origin = origin.split(";")[0].strip()
        print(f"Cleaned origin: '{cleaned_origin}'")
        origin = cleaned_origin
    
    # 检查origin是否在允许列表中
    if origin in allowed_origins or "localhost" in origin or "vercel.app" in origin:
        print(f"Origin '{origin}' is allowed")
        return origin
    
    # 如果不在允许列表中，返回第一个允许的origin
    print(f"Origin '{origin}' is not allowed, returning first allowed origin: '{allowed_origins[0]}'")
    return allowed_origins[0]

# 配置CORS - 使用更宽松的配置以支持跨域请求
print("Configuring CORS settings...")

# 定义允许的源 - 确保每个URL格式正确
allowed_origins = [
    "https://deepdriverfront.vercel.app",  # Vercel部署的前端
    "https://deepdriver.up.railway.app",   # Railway部署的后端
    "http://localhost:5173",              # Vite开发服务器
    "http://localhost:3000",              # 其他开发服务器
    "http://localhost:8080",              # 其他开发服务器
    "http://127.0.0.1:61694",             # Cascade浏览器集成
    "http://127.0.0.1:8080"               # 使用IP访问的开发服务器
]

# 打印格式化的允许源列表
print("Allowed origins:")
for origin in allowed_origins:
    print(f"  - {origin}")

# 打印允许的源列表
print(f"Allowed origins: {allowed_origins}")

# 使用更宽松的CORS配置
print("Configuring CORS with wildcard origin...")
cors = CORS(
    app,
    resources={r"/api/*": {
        "origins": "*",  # 临时允许所有来源进行测试
        "methods": ["GET", "POST", "OPTIONS"],
        "allow_headers": ["*"],  # 允许所有头部
        "supports_credentials": False,
        "max_age": 86400,
        "send_wildcard": True,
        "vary_header": True,
        "automatic_options": True,
        "expose_headers": ["Content-Type", "Cache-Control"]
    }}
)

# 添加CORS和SSE相关的头部设置
@app.after_request
def add_headers(response):
    """添加CORS和SSE相关的头部设置"""
    # 记录请求信息，用于调试
    print(f"Processing request: {request.method} {request.path} from {request.remote_addr}")
    print(f"Request headers: {dict(request.headers)}")
    print(f"Original response headers: {dict(response.headers)}")
    
    # 如果是SSE响应，添加相关头部
    if response.mimetype == 'text/event-stream':
        response.headers['Cache-Control'] = 'no-cache, no-transform'
        response.headers['X-Accel-Buffering'] = 'no'  # 禁用Nginx缓冲，对于SSE很重要
    
    # 特别检查并清理Access-Control-Allow-Origin头部
    origin_header = response.headers.get('Access-Control-Allow-Origin')
    if origin_header:
        print(f"Found Access-Control-Allow-Origin: '{origin_header}'")
        if ';' in origin_header:
            print(f"WARNING: Access-Control-Allow-Origin contains semicolon: '{origin_header}'")
            # 清理头部，移除分号
            cleaned_origin = origin_header.split(";")[0].strip()
            print(f"Cleaning Access-Control-Allow-Origin to: '{cleaned_origin}'")
            # 先删除原有头部，然后添加清理后的头部
            del response.headers['Access-Control-Allow-Origin']
            response.headers['Access-Control-Allow-Origin'] = cleaned_origin
    
    # 检查是否有多个Access-Control-Allow-Origin头部
    # 这可能发生在WSGI服务器层面，如Gunicorn或uWSGI
    all_headers = dict(response.headers)
    origin_headers = [k for k in all_headers.keys() if k.lower() == 'access-control-allow-origin']
    if len(origin_headers) > 1:
        print(f"WARNING: Multiple Access-Control-Allow-Origin headers found: {origin_headers}")
        # 保留第一个，删除其他的
        for k in origin_headers[1:]:
            del response.headers[k]
    
    # 全局添加CORS头部，确保所有请求都能正确处理CORS
    # 如果没有设置Access-Control-Allow-Origin，则添加通配符
    if 'Access-Control-Allow-Origin' not in response.headers:
        response.headers['Access-Control-Allow-Origin'] = '*'
    
    # 添加其他必要的CORS头部
    response.headers['Access-Control-Allow-Methods'] = 'GET, POST, OPTIONS, PUT, DELETE'
    response.headers['Access-Control-Allow-Headers'] = 'Content-Type, Authorization, X-Requested-With, Cache-Control, Accept, Origin'
    
    # 打印最终头部，用于调试
    print(f"Final response headers after Flask-CORS processing: {dict(response.headers)}")
    
    return response

# 不再需要手动处理CORS预检请求，Flask-CORS会自动处理

# 添加全局健康检查端点
@app.route('/health')
def health_check():
    """健康检查端点，用于Railway监控"""
    import time
    return jsonify({
        "status": "healthy", 
        "timestamp": int(time.time()),
        "version": "1.0.0",
        "environment": os.environ.get("FLASK_ENV", "production")
    })
    # 不再手动设置CORS头部，由Flask-CORS自动处理

# 添加静态文件路由
@app.route('/test')
def test_page():
    return app.send_static_file('test_resolve.html')

# 添加简单的API测试路由
@app.route('/api/test')
def api_test():
    logger.info("Received request to /api/test")
    return jsonify({"status": "ok", "message": "API is working"})

# 添加简单的DeepSearch测试路由
@app.route('/api/deepsearch_test')
def deepsearch_test():
    institution_A = request.args.get('institution_A', 'test')
    logger.info(f"Received test request to /api/deepsearch_test with institution_A={institution_A}")
    return jsonify({
        "status": "ok", 
        "message": "DeepSearch test route is working",
        "institution_A": institution_A
    })

# 注册API路由
register_routes(app)

# 打印所有路由信息，用于调试
print("\nRegistered routes:")
for rule in app.url_map.iter_rules():
    print(f"Route: {rule.endpoint} -> {rule.rule} [{', '.join(rule.methods)}]")

# 注册修复版的DeepSearch蓝图
app.register_blueprint(fixed_deepsearch_bp)

# 注册DeepSearch Simple蓝图
app.register_blueprint(deepsearch_simple_bp)

# 再次打印所有路由信息，确认蓝图注册成功
print("\nAll registered routes (after blueprints):")
for rule in app.url_map.iter_rules():
    print(f"Route: {rule.endpoint} -> {rule.rule} [{', '.join(rule.methods)}]")

# 仅在直接运行此文件时启动开发服务器
if __name__ == '__main__':
    # 在开发环境中运行
    logger.info("Starting OSINT security risk investigation tool backend service...")
    # 使用环境变量或默认值设置端口
    port = int(os.environ.get("PORT", 5000))
    logger.info(f"Server will run on port {port}")
    # 添加更多配置选项，优化对SSE的支持
    app.run(
        host="0.0.0.0", 
        port=port, 
        debug=False,  # 生产环境中禁用调试模式
        threaded=True,
        use_reloader=False,  # 在生产环境中禁用自动重载
        use_debugger=False  # 在生产环境中禁用调试器
    )

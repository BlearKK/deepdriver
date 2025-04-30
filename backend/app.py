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

from flask import Flask
from flask_cors import CORS
from config import logger
from routes import register_routes

# 创建Flask应用
app = Flask(__name__, static_url_path='', static_folder='static')
CORS(app)  # 启用CORS，允许前端跨域请求

# 添加静态文件路由
@app.route('/test')
def test_page():
    return app.send_static_file('test_resolve.html')

# 注册API路由
register_routes(app)

if __name__ == "__main__":
    # 在开发环境中运行
    logger.info("启动OSINT安全风险调查工具后端服务...")
    app.run(host='0.0.0.0', port=5000, debug=True)

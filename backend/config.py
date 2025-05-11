"""
OSINT 安全风险调查工具 - 配置模块

包含应用的配置信息，如API密钥、模型ID等。
"""

import os
import logging
from dotenv import load_dotenv
from google import genai

# 配置日志
logging.basicConfig(level=logging.INFO, 
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# 加载环境变量
load_dotenv()

# 获取API密钥
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
if not GOOGLE_API_KEY:
    logger.error("未找到GOOGLE_API_KEY环境变量，请确保.env文件中包含此密钥")
    raise ValueError("缺少GOOGLE_API_KEY环境变量")

# 为了方便在其他模块中使用，将API_KEY导出
API_KEY = GOOGLE_API_KEY

# 配置Gemini API客户端
client = genai.Client(api_key=GOOGLE_API_KEY)

# 选择模型ID - 使用支持搜索接地的Gemini模型
MODEL_ID = "gemini-2.5-flash-preview-04-17"

# 获取提示词模板路径
def get_prompt_template_path():
    """获取提示词模板文件路径"""
    # 首先尝试在当前目录查找文件
    current_dir_path = os.path.join(os.path.dirname(__file__), 'Company_search.md')
    if os.path.exists(current_dir_path):
        return current_dir_path
    
    # 如果当前目录没有，再尝试在上级目录查找（兼容本地开发环境）
    parent_dir_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'Company_search.md')
    if os.path.exists(parent_dir_path):
        return parent_dir_path
    
    # 如果都找不到，使用当前目录路径（部署环境）
    logger.warning("未找到Company_search.md文件，使用当前目录路径")
    return current_dir_path

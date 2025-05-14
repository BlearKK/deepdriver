"""
OSINT 安全风险调查工具 - Gemini API 客户端模块

负责 Gemini API 的客户端配置、初始化和调用。
支持接地搜索、多轮对话和安全设置。
"""

import json
import time
import re
import os
from typing import Dict, Any, Optional, List, Union
from dataclasses import dataclass

# 先导入 logger
from config import MODEL_ID, API_KEY, logger

# 定义接地搜索可用性标志
GROUNDING_AVAILABLE = False
USE_NEW_API = False

# 尝试导入新版 Google Generative AI 库
try:
    from google import genai
    from google.genai.types import Tool, GenerateContentConfig, GoogleSearch, ThinkingConfig
    
    # 设置接地搜索和API版本标志
    GROUNDING_AVAILABLE = True
    USE_NEW_API = True
    logger.info("成功导入新版google.genai库，接地搜索功能可用")
    
except ImportError as e:
    logger.warning(f"无法导入新版google.genai库: {e}")
    
    # 尝试导入旧版 Google Generative AI 库
    try:
        import google.generativeai as genai
        from google.generativeai.types import GenerationConfig
        
        # 尝试导入安全设置相关类型
        try:
            from google.generativeai.types import SafetySetting, HarmCategory, HarmBlockThreshold
            logger.info("成功导入安全设置相关类型")
        except ImportError:
            # 如果无法导入SafetySetting，使用替代方法
            try:
                from google.generativeai.types import SafetySettingDict as SafetySetting
                from google.generativeai.types import HarmCategory, HarmBlockThreshold
                logger.info("使用SafetySettingDict替代SafetySetting")
            except ImportError as e2:
                logger.warning(f"无法导入安全设置相关类型: {e2}")
        
        # 尝试导入旧版接地搜索相关类型
        try:
            from google.generativeai.types import Tool
            
            # 定义兼容类
            class GoogleSearch:
                def __init__(self):
                    pass
            
            # 使用GenerationConfig替代GenerateContentConfig
            GenerateContentConfig = GenerationConfig
            
            # 定义ThinkingConfig类
            class ThinkingConfig:
                def __init__(self, include_thoughts=True):
                    self.include_thoughts = include_thoughts
            
            GROUNDING_AVAILABLE = True
            logger.info("成功导入旧版接地搜索相关类型")
        except ImportError as e3:
            logger.warning(f"无法导入旧版接地搜索相关类型: {e3}")
            # 定义兼容类
            Tool = None
            GoogleSearch = None
            GenerateContentConfig = None
            ThinkingConfig = None
    except ImportError as e4:
        logger.error(f"无法导入任何版本的Google AI库: {e4}")

# 重试配置
MAX_RETRIES = 3
RETRY_DELAY = 2  # 秒

@dataclass
class GeminiResponse:
    """Gemini API响应的标准化格式"""
    text: str
    metadata: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    raw_response: Any = None  # 原始响应对象

def get_gemini_client():
    """
    获取并配置 Gemini API 客户端实例
    
    Returns:
        预配置的 Gemini API 客户端实例
    """
    try:
        if USE_NEW_API:
            # 使用新版API
            client = genai.Client(api_key=API_KEY)
            logger.info(f"成功创建新版Gemini客户端，使用模型: {MODEL_ID}")
            return client
        else:
            # 使用旧版API
            genai.configure(api_key=API_KEY)
            model = genai.GenerativeModel(MODEL_ID)
            logger.info(f"成功创建旧版Gemini客户端，使用模型: {MODEL_ID}")
            return model
    except Exception as e:
        error_msg = f"创建Gemini客户端实例失败: {e}"
        logger.error(error_msg)
        raise ValueError(error_msg)

def get_generation_config(temperature: float = 0.4, max_output_tokens: int = 65536) -> Dict[str, Any]:
    """
    获取 Gemini API 生成配置
    
    Args:
        temperature: 生成文本的随机性，越低越精确
        max_output_tokens: 最大输出长度
        
    Returns:
        Dict[str, Any]: 生成配置对象
    """
    return {
        "temperature": temperature,
        "max_output_tokens": max_output_tokens,
        "top_p": 0.95,
        "top_k": 40
    }

def extract_search_metadata(response) -> Dict[str, Any]:
    """
    从API响应中提取接地搜索元数据
    
    Args:
        response: API响应对象
        
    Returns:
        Dict[str, Any]: 包含接地搜索元数据的字典
    """
    search_metadata = {}
    
    try:
        # 检查是否使用新版API
        if USE_NEW_API:
            # 尝试从候选结果中提取元数据
            if hasattr(response, 'candidates') and response.candidates:
                candidate = response.candidates[0]
                
                # 1. 首先尝试从 grounding 字段提取
                if hasattr(candidate, 'grounding') and candidate.grounding:
                    logger.info("检测到 grounding 字段")
                    
                    # 提取搜索入口点
                    if hasattr(candidate.grounding, 'search_entry_point') and candidate.grounding.search_entry_point:
                        entry_point = candidate.grounding.search_entry_point
                        
                        # 提取搜索链接
                        if hasattr(entry_point, 'chips') and entry_point.chips:
                            search_urls = []
                            for chip in entry_point.chips:
                                if hasattr(chip, 'url') and chip.url:
                                    search_urls.append(chip.url)
                            
                            if search_urls:
                                # 安全地记录搜索URL数量
                                if search_urls is not None:
                                    logger.info(f"从 grounding.search_entry_point.chips 提取到 {len(search_urls)} 个搜索URL")
                                else:
                                    logger.warning("search_urls 为 None，无法记录URL数量")
                                search_metadata["search_urls"] = search_urls
                        
                        # 提取渲染内容
                        if hasattr(entry_point, 'rendered_content') and entry_point.rendered_content:
                            rendered_content = entry_point.rendered_content
                            search_metadata["rendered_content"] = rendered_content
                    
                    # 提取搜索建议
                    if hasattr(candidate.grounding, 'search_suggestions') and candidate.grounding.search_suggestions:
                        search_suggestions = candidate.grounding.search_suggestions
                        search_queries = []
                        
                        for suggestion in search_suggestions:
                            if hasattr(suggestion, 'query'):
                                search_queries.append(suggestion.query)
                        
                        if search_queries:
                            # 安全地记录搜索查询数量
                            if search_queries is not None:
                                logger.info(f"从 grounding.search_suggestions 提取到 {len(search_queries)} 个搜索查询")
                            else:
                                logger.warning("search_queries 为 None，无法记录查询数量")
                            search_metadata["search_queries"] = search_queries
                    
                    # 提取接地块
                    if hasattr(candidate.grounding, 'grounding_chunks') and candidate.grounding.grounding_chunks:
                        chunks = candidate.grounding.grounding_chunks
                        grounding_urls = []
                        
                        for chunk in chunks:
                            if hasattr(chunk, 'web') and hasattr(chunk.web, 'url') and chunk.web.url:
                                grounding_urls.append(chunk.web.url)
                        
                        if grounding_urls:
                            # 安全地记录接地URL数量
                            if grounding_urls is not None:
                                logger.info(f"从 grounding.grounding_chunks 提取到 {len(grounding_urls)} 个接地URL")
                            else:
                                logger.warning("grounding_urls 为 None，无法记录URL数量")
                            search_metadata["grounding_urls"] = grounding_urls
                
                # 2. 尝试从 grounding_metadata 字段提取
                if hasattr(candidate, 'grounding_metadata') and candidate.grounding_metadata:
                    logger.info("检测到 grounding_metadata 字段")
                    
                    # 提取搜索URL
                    if hasattr(candidate.grounding_metadata, 'search_urls') and candidate.grounding_metadata.search_urls:
                        search_urls = candidate.grounding_metadata.search_urls
                        # 安全地记录搜索URL数量
                        if search_urls is not None:
                            logger.info(f"从 grounding_metadata.search_urls 提取到 {len(search_urls)} 个搜索URL")
                        else:
                            logger.warning("search_urls 为 None，无法记录URL数量")
                        search_metadata["search_urls"] = search_urls
                    
                    # 提取渲染内容
                    if hasattr(candidate.grounding_metadata, 'rendered_content') and candidate.grounding_metadata.rendered_content:
                        rendered_content = candidate.grounding_metadata.rendered_content
                        search_metadata["rendered_content"] = rendered_content
        else:
            # 旧版API的元数据提取
            # 尝试从文本内容中提取URL
            if hasattr(response, 'text'):
                text = response.text
                
                # 匹配接地搜索URL的模式
                url_patterns = [
                    r'(https?://vertexaisearch\.cloud\.google\.com/grounding-api-redirect/[^\s"\'\)\]>]+)',
                    r'(https?://[^\s"\'\)\]>]+gemini-api-redirect[^\s"\'\)\]>]*)',
                    r'(https?://[^\s"\'\)\]>]+google\.com/search[^\s"\'\)\]>]*)',
                    r'(https?://[^\s"\'\)\]>]+googleapis\.com/search[^\s"\'\)\]>]*)',
                ]
                
                all_urls = []
                for pattern in url_patterns:
                    urls = re.findall(pattern, text)
                    if urls:
                        all_urls.extend(urls)
                
                if all_urls:
                    logger.info(f"从文本中提取到 {len(all_urls)} 个接地搜索URL")
                    search_metadata["search_urls"] = all_urls
    
    except Exception as e:
        logger.warning(f"提取接地搜索元数据时出错: {e}")
    
    return search_metadata

def call_gemini_api(user_prompt: str, 
                   system_instruction: Optional[str] = None,
                   temperature: float = 0.4,
                   max_output_tokens: int = 65536,
                   enable_grounding: bool = True,
                   enable_thinking: bool = True) -> GeminiResponse:
    """
    调用 Gemini API 生成内容
    
    Args:
        user_prompt: 用户提示内容
        system_instruction: 系统指令（可选）
        temperature: 生成文本的随机性，越低越精确
        max_output_tokens: 最大输出长度
        enable_grounding: 是否启用接地搜索功能
        enable_thinking: 是否启用思考功能
        
    Returns:
        GeminiResponse: API响应对象
    """
    # 检查参数
    if not user_prompt:
        return GeminiResponse(text="", error="用户提示不能为空")
    
    # 自动读取 Company_search.md 作为系统指令
    if not system_instruction:
        try:
            md_path = os.path.join(os.path.dirname(__file__), 'Company_search.md')
            parent_md_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'Company_search.md')
            
            # 先检查当前目录
            if os.path.exists(md_path):
                with open(md_path, 'r', encoding='utf-8') as f:
                    system_instruction = f.read().strip()
                logger.info(f"从当前目录加载系统指令: {md_path}")
            # 再检查上级目录
            elif os.path.exists(parent_md_path):
                with open(parent_md_path, 'r', encoding='utf-8') as f:
                    system_instruction = f.read().strip()
                logger.info(f"从上级目录加载系统指令: {parent_md_path}")
            else:
                logger.warning("未找到Company_search.md文件")
        except Exception as e:
            logger.warning(f"读取系统指令文件失败: {e}")
    
    # 使用重试机制调用API
    for attempt in range(MAX_RETRIES):
        try:
            logger.info(f"API调用尝试 {attempt + 1}/{MAX_RETRIES}")
            
            # 检查是否使用新版API
            if USE_NEW_API and GROUNDING_AVAILABLE and enable_grounding:
                try:
                    # 使用新版API调用
                    logger.info("使用新版API调用Gemini")
                    
                    # 创建客户端
                    client = get_gemini_client()
                    
                    # 创建GoogleSearch工具
                    google_search_tool = Tool(
                        google_search=GoogleSearch()
                    )
                    
                    # 创建思考配置
                    thinking_config = None
                    if enable_thinking:
                        thinking_config = ThinkingConfig(include_thoughts=True)
                        logger.info("启用思考功能")
                    
                    # 创建生成配置
                    config = GenerateContentConfig(
                        temperature=temperature,
                        max_output_tokens=max_output_tokens,
                        top_p=0.95,
                        top_k=40,
                        tools=[google_search_tool],
                        response_modalities=["TEXT"],  # 只返回文本响应
                        thinking_config=thinking_config,  # 添加思考配置
                        system_instruction=system_instruction  # 系统指令
                    )
                    
                    # 调用API
                    try:
                        logger.info(f"开始调用新版API，模型: {MODEL_ID}")
                        response = client.models.generate_content(
                            model=MODEL_ID,
                            contents=user_prompt,
                            config=config
                        )
                        
                        logger.info("新版API调用成功")
                    except Exception as api_error:
                        logger.error(f"新版API调用失败: {str(api_error)}", exc_info=True)
                        # 打印更详细的错误信息
                        if hasattr(api_error, 'response') and api_error.response:
                            logger.error(f"错误响应状态码: {api_error.response.status_code if hasattr(api_error.response, 'status_code') else 'N/A'}")
                            logger.error(f"错误响应内容: {api_error.response.text if hasattr(api_error.response, 'text') else 'N/A'}")
                        raise
                    
                    # 提取文本内容
                    text_content = ""
                    if hasattr(response, 'candidates') and response.candidates:
                        candidate = response.candidates[0]
                        if hasattr(candidate, 'content') and hasattr(candidate.content, 'parts'):
                            for part in candidate.content.parts:
                                if hasattr(part, 'text'):
                                    text_content += part.text
                    
                    # 提取元数据
                    metadata = {
                        "model": MODEL_ID,
                        "api_version": "new",
                        "grounding_enabled": True
                    }
                    
                    # 提取接地搜索元数据
                    search_metadata = extract_search_metadata(response)
                    if search_metadata:
                        metadata["grounding_metadata"] = search_metadata
                    
                    return GeminiResponse(text=text_content, metadata=metadata, raw_response=response)
                
                except Exception as e:
                    logger.warning(f"新版API调用失败: {e}")
                    logger.info("尝试使用旧版API")
            
            # 使用旧版API
            try:
                # 创建模型实例
                model = None
                if not USE_NEW_API:
                    model = get_gemini_client()
                else:
                    # 如果新版API失败，重新配置旧版API
                    genai.configure(api_key=API_KEY)
                    model = genai.GenerativeModel(MODEL_ID)
                
                # 设置生成参数
                gen_params = get_generation_config(temperature, max_output_tokens)
                model.generation_config = genai.types.GenerationConfig(
                    temperature=gen_params["temperature"],
                    max_output_tokens=gen_params["max_output_tokens"],
                    top_p=gen_params["top_p"],
                    top_k=gen_params["top_k"]
                )
                
                # 组装内容
                contents = f"{system_instruction}\n\n{user_prompt}" if system_instruction else user_prompt
                
                # 调用API
                try:
                    logger.info(f"开始调用旧版API，模型: {MODEL_ID}")
                    response = model.generate_content(contents=contents)
                    
                    # 检查响应
                    if not response or not hasattr(response, 'text') or not response.text.strip():
                        logger.error("API返回了空响应")
                        raise ValueError("API返回了空响应")
                    
                    logger.info("旧版API调用成功")
                except Exception as api_error:
                    logger.error(f"旧版API调用失败: {str(api_error)}", exc_info=True)
                    # 打印更详细的错误信息
                    if hasattr(api_error, 'response') and api_error.response:
                        logger.error(f"错误响应状态码: {api_error.response.status_code if hasattr(api_error.response, 'status_code') else 'N/A'}")
                        logger.error(f"错误响应内容: {api_error.response.text if hasattr(api_error.response, 'text') else 'N/A'}")
                    raise
                
                # 提取元数据
                metadata = {
                    "prompt_tokens": getattr(response, 'prompt_token_count', None),
                    "completion_tokens": getattr(response, 'completion_token_count', None),
                    "total_tokens": getattr(response, 'total_token_count', None),
                    "model": MODEL_ID,
                    "api_version": "old"
                }
                
                # 提取接地搜索元数据
                if GROUNDING_AVAILABLE and enable_grounding:
                    search_metadata = extract_search_metadata(response)
                    if search_metadata:
                        metadata["grounding_metadata"] = search_metadata
                
                logger.info("旧版API调用成功")
                return GeminiResponse(text=response.text, metadata=metadata, raw_response=response)
            
            except Exception as e:
                if attempt < MAX_RETRIES - 1:
                    logger.warning(f"API调用失败，等待{RETRY_DELAY}秒后重试: {str(e)}")
                    time.sleep(RETRY_DELAY)
                else:
                    raise
        
        except Exception as e:
            if attempt < MAX_RETRIES - 1:
                logger.warning(f"API调用尝试{attempt + 1}失败: {str(e)}")
                time.sleep(RETRY_DELAY)
            else:
                logger.error(f"所有API调用尝试均失败: {str(e)}")
                # 尝试使用备用方法
                return try_backup_method(user_prompt, system_instruction, e)

def get_safety_settings() -> List[Dict[str, str]]:
    """
    获取安全设置参数
    
    Returns:
        List[Dict[str, str]]: 安全设置参数列表
    """
    return [
        {
            "category": "HARM_CATEGORY_HARASSMENT",
            "threshold": "BLOCK_ONLY_HIGH"
        },
        {
            "category": "HARM_CATEGORY_HATE_SPEECH",
            "threshold": "BLOCK_ONLY_HIGH"
        },
        {
            "category": "HARM_CATEGORY_SEXUALLY_EXPLICIT",
            "threshold": "BLOCK_ONLY_HIGH"
        },
        {
            "category": "HARM_CATEGORY_DANGEROUS_CONTENT",
            "threshold": "BLOCK_ONLY_HIGH"
        }
    ]

def try_backup_method(user_prompt: str, system_instruction: Optional[str] = None, last_error: Exception = None) -> GeminiResponse:
    """
    备用方法，当主要API调用方法失败时使用
    采用简化的参数和不同的调用方式
    
    Args:
        user_prompt: 用户提示内容
        system_instruction: 系统指令（可选）
        last_error: 上一次失败的错误
    
    Returns:
        GeminiResponse: API响应对象
    """
    try:
        logger.info("尝试备用API调用方法")
        
        # 自动读取 Company_search.md
        if not system_instruction:
            import os
            md_path = os.path.join(os.path.dirname(__file__), 'Company_search.md')
            parent_md_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'Company_search.md')
            
            # 先检查当前目录
            if os.path.exists(md_path):
                with open(md_path, 'r', encoding='utf-8') as f:
                    system_instruction = f.read().strip()
            # 再检查上级目录
            elif os.path.exists(parent_md_path):
                with open(parent_md_path, 'r', encoding='utf-8') as f:
                    system_instruction = f.read().strip()
        
        # 检查系统指令
        if not system_instruction:
            logger.warning("system_instruction 为空，继续使用空指令")
        
        # 初始化API（重新配置API密钥）
        genai.configure(api_key=API_KEY)
        model = genai.GenerativeModel(MODEL_ID)
        
        # 设置生成参数（简化版）
        generation_config = genai.types.GenerationConfig(
            temperature=0.4,
            max_output_tokens=8192,
            top_p=0.95,
            top_k=40
        )
        
        # 组装内容（直接拼接）
        contents = f"{system_instruction}\n\n{user_prompt}" if system_instruction else user_prompt
        
        # 调用API（简化版）
        try:
            logger.info(f"开始调用备用方法，模型: {MODEL_ID}")
            model.generation_config = generation_config
            response = model.generate_content(contents=contents)
            
            if not response or not hasattr(response, 'text') or not response.text.strip():
                logger.error("API返回了空响应")
                raise ValueError("API返回了空响应")
                
            logger.info("备用方法调用成功")
        except Exception as api_error:
            logger.error(f"备用方法调用失败: {str(api_error)}", exc_info=True)
            # 打印更详细的错误信息
            if hasattr(api_error, 'response') and api_error.response:
                logger.error(f"错误响应状态码: {api_error.response.status_code if hasattr(api_error.response, 'status_code') else 'N/A'}")
                logger.error(f"错误响应内容: {api_error.response.text if hasattr(api_error.response, 'text') else 'N/A'}")
            raise
            
        metadata = {
            "prompt_tokens": getattr(response, 'prompt_token_count', None),
            "completion_tokens": getattr(response, 'completion_token_count', None),
            "total_tokens": getattr(response, 'total_token_count', None),
            "model": MODEL_ID,
            "backup_method": True
        }
        
        return GeminiResponse(text=response.text, metadata=metadata, raw_response=response)
    except Exception as e:
        error_msg = f"备用方法失败 -> {str(e)}"
        logger.error(f"所有API调用方法均失败: {error_msg}")
        return GeminiResponse(text="", error=error_msg)

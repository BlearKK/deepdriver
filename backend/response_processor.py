"""
OSINT 安全风险调查工具 - 响应处理模块

负责处理 Gemini API 响应，提取文本内容、搜索元数据和解析结果。
"""

import re
import json
import time
from typing import List, Dict, Any, Optional, Union
from config import logger
from response_parser import parse_gemini_response

def extract_text_content(response) -> Optional[str]:
    """
    从 API 响应中提取文本内容。
    
    Args:
        response: API 响应对象
        
    Returns:
        str: 提取的文本内容，如果提取失败则返回 None
    """
    try:
        # 确保response对象有效
        if not response:
            logger.error("API响应对象为空")
            raise ValueError("API response object is None")
            
        # 尝试获取文本内容
        if hasattr(response, 'text'):
            text_content = response.text
        elif hasattr(response, 'candidates') and response.candidates and hasattr(response.candidates[0], 'content'):
            # 尝试从candidates中提取文本
            text_content = ""
            for part in response.candidates[0].content.parts:
                if hasattr(part, 'text'):
                    text_content += part.text
        else:
            # 尝试将整个响应转换为字符串
            text_content = str(response)
            
        # 检查响应是否为空
        if not text_content or text_content.strip() == "":
            logger.error("API返回了空响应内容")
            raise ValueError("Invalid or empty API response content")
            
        logger.info(f"获取到文本响应，长度: {len(text_content) if isinstance(text_content, str) else '(非字符串)'}")
        logger.debug(f"响应前100个字符: {text_content[:100] if len(text_content) > 100 else text_content}")
        
        return text_content
    except Exception as e:
        logger.error(f"提取文本内容时出错: {str(e)}")
        return None

def extract_search_metadata(response) -> Dict[str, Any]:
    """
    从 API 响应中提取搜索元数据，包括接地搜索的URL。
    
    Args:
        response: API 响应对象
        
    Returns:
        Dict[str, Any]: 提取的搜索元数据，包含 search_urls 字段
    """
    search_metadata = {}
    
    try:
        # 首先检查响应对象是否有效
        if not response:
            logger.warning("响应对象为None，无法提取搜索元数据")
            return search_metadata
        
        # 判断是否使用新版API
        if hasattr(response, 'candidates') and response.candidates:
            candidate = response.candidates[0]
            logger.info("使用新版API响应格式提取元数据")
            
            # 1. 首先尝试从 grounding 字段提取 search_suggestions
            if hasattr(candidate, 'grounding') and candidate.grounding:
                logger.info("检测到 grounding 字段")
                
                # 提取搜索建议
                if hasattr(candidate.grounding, 'search_suggestions') and candidate.grounding.search_suggestions:
                    search_suggestions = candidate.grounding.search_suggestions
                    logger.info(f"从 grounding 提取到 {len(search_suggestions)} 个搜索建议")
                    
                    # 提取每个搜索建议的查询内容
                    search_queries = []
                    for suggestion in search_suggestions:
                        if hasattr(suggestion, 'query'):
                            search_queries.append(suggestion.query)
                    
                    if search_queries:
                        logger.info(f"提取到搜索查询: {search_queries}")
                        search_metadata["search_queries"] = search_queries
                        # 同时添加 webSearchQueries 字段，以符合 Google 官方文档
                        search_metadata["webSearchQueries"] = search_queries
                    
                # 提取渲染内容
                if hasattr(candidate.grounding, 'rendered_content') and candidate.grounding.rendered_content:
                    rendered_content = candidate.grounding.rendered_content
                    search_metadata["rendered_content"] = rendered_content
                
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
                            logger.info(f"从 grounding.search_entry_point.chips 提取到 {len(search_urls)} 个搜索URL")
                            search_metadata["search_urls"] = search_urls
            
            # 2. 尝试从 grounding_metadata 字段提取
            if hasattr(candidate, 'grounding_metadata') and candidate.grounding_metadata:
                logger.info("检测到 grounding_metadata 字段")
                
                # 提取搜索URL
                if hasattr(candidate.grounding_metadata, 'search_urls') and candidate.grounding_metadata.search_urls:
                    search_urls = candidate.grounding_metadata.search_urls
                    logger.info(f"从 grounding_metadata.search_urls 提取到 {len(search_urls)} 个搜索URL")
                    search_metadata["search_urls"] = search_urls
        else:
            # 如果没有candidates字段，可能是旧版API响应
            logger.info("使用旧版API响应格式提取元数据")
            # 尝试从文本内容中提取URL
            if hasattr(response, 'text') and response.text:
                # 匹配接地搜索URL的模式
                url_patterns = [
                    r'(https?://vertexaisearch\.cloud\.google\.com/grounding-api-redirect/[^\s"\'\)\]>]+)',
                    r'(https?://[^\s"\'\)\]>]+gemini-api-redirect[^\s"\'\)\]>]*)',
                    r'(https?://[^\s"\'\)\]>]+google\.com/search[^\s"\'\)\]>]*)',
                    r'(https?://[^\s"\'\)\]>]+googleapis\.com/search[^\s"\'\)\]>]*)',
                ]
                
                all_urls = []
                for pattern in url_patterns:
                    urls = re.findall(pattern, response.text)
                    if urls:
                        all_urls.extend(urls)
                
                if all_urls:
                    logger.info(f"从文本中提取到 {len(all_urls)} 个接地搜索URL")
                    search_metadata["search_urls"] = all_urls
            
            # 尝试从元数据中提取搜索查询
            if hasattr(response, 'metadata') and response.metadata:
                metadata = response.metadata
                if isinstance(metadata, dict) and "grounding_metadata" in metadata:
                    grounding_metadata = metadata["grounding_metadata"]
                    if isinstance(grounding_metadata, dict) and "search_urls" in grounding_metadata:
                        search_urls = grounding_metadata["search_urls"]
                        logger.info(f"从 metadata.grounding_metadata.search_urls 提取到 {len(search_urls)} 个搜索URL")
                        search_metadata["search_urls"] = search_urls
    
    except Exception as e:
        logger.warning(f"提取搜索元数据时出错: {e}")
    
    return search_metadata

def generate_default_queries(institution: str, risk_list: List[str], time_range_start: str = None, time_range_end: str = None) -> List[str]:
    """
    根据机构名称、风险项和时间范围生成默认搜索查询。
    
    Args:
        institution (str): 机构名称
        risk_list (List[str]): 风险项列表
        time_range_start (str, optional): 开始时间，格式为YYYY-MM
        time_range_end (str, optional): 结束时间，格式为YYYY-MM
        
    Returns:
        List[str]: 生成的默认搜索查询列表
    """
    default_queries = []
    
    # 构建时间范围限制
    time_filter = ""
    if time_range_start and time_range_end:
        # 将YYYY-MM格式转换为Google搜索查询格式
        start_year, start_month = time_range_start.split('-')
        end_year, end_month = time_range_end.split('-')
        # 构建Google搜索的时间范围过滤器
        time_filter = f" after:{start_year}/{start_month}/01 before:{end_year}/{end_month}/31"
        logger.info(f"添加时间范围过滤器: {time_filter}")
    
    # 根据机构名称和风险项生成查询
    for risk in risk_list:
        # 中文查询 - 更精确的查询格式
        default_queries.append(f"\"{institution}\" \"{risk}\" 合作{time_filter}")
        default_queries.append(f"\"{institution}\" \"{risk}\" 关系{time_filter}")
        
        # 英文查询 - 更精确的查询格式
        default_queries.append(f"\"{institution}\" \"{risk}\" collaboration{time_filter}")
        default_queries.append(f"\"{institution}\" \"{risk}\" partnership{time_filter}")
        default_queries.append(f"\"{institution}\" \"{risk}\" connection{time_filter}")
    
    logger.info(f"生成默认搜索查询: {default_queries}")
    return default_queries

def parse_json_response(text_content: str) -> Optional[List[Dict[str, Any]]]:
    """
    解析 JSON 格式的响应。
    
    Args:
        text_content (str): 文本内容
        
    Returns:
        Optional[List[Dict[str, Any]]]: 解析的 JSON 结果，如果解析失败则返回 None
    """
    try:
        # 检查是否是 JSON 字符串包裹在双引号中的情况
        if text_content.strip().startswith('"') and text_content.strip().endswith('"'):
            # 尝试去除外层引号并解析
            try:
                inner_content = json.loads(text_content)
                if isinstance(inner_content, str):
                    text_content = inner_content
            except Exception as e:
                logger.warning(f"去除外层引号解析失败: {str(e)}")
        
        # 检查是否包含 Markdown 代码块
        code_block_pattern = r'```(?:json)?\s*([\s\S]*?)\s*```'
        code_blocks = re.findall(code_block_pattern, text_content)
        
        if code_blocks:
            logger.info(f"从响应中提取到 {len(code_blocks)} 个代码块")
            # 尝试解析每个代码块
            for block in code_blocks:
                try:
                    results = json.loads(block)
                    logger.info("成功解析代码块为JSON")
                    
                    # 处理结果格式
                    if isinstance(results, list):
                        logger.info(f"获取到JSON列表，包含 {len(results)} 个结果")
                        return results
                    elif isinstance(results, dict):
                        logger.info("获取到JSON字典，转换为列表")
                        return [results]
                except json.JSONDecodeError:
                    logger.warning("代码块不是有效的JSON，尝试下一个代码块")
                    continue
        
        # 尝试直接解析整个响应
        try:
            results = json.loads(text_content)
            logger.info("成功直接解析响应为JSON")
            
            # 处理结果格式
            if isinstance(results, list):
                logger.info(f"获取到JSON列表，包含 {len(results)} 个结果")
                return results
            elif isinstance(results, dict):
                logger.info("获取到JSON字典，转换为列表")
                return [results]
        except json.JSONDecodeError:
            logger.warning("整个响应不是有效的JSON")
    
    except Exception as e:
        logger.warning(f"解析JSON响应时出错: {str(e)}")
    
    return None

def process_response(response, institution: str, country: str, risk_list: List[str], time_range_start: str = None, time_range_end: str = None) -> List[Dict[str, Any]]:
    """
    处理 API 响应，提取结果和元数据，包括接地搜索的URL。
    
    Args:
        response: API 响应对象
        institution (str): 机构名称
        country (str): 国家
        risk_list (List[str]): 风险项列表
        time_range_start (str, optional): 开始时间，格式为YYYY-MM
        time_range_end (str, optional): 结束时间，格式为YYYY-MM
        
    Returns:
        List[Dict[str, Any]]: 处理后的结果列表，包含接地搜索的URL
    """
    try:
        # 提取文本内容
        text_content = extract_text_content(response)
        if not text_content:
            raise ValueError("无法从响应中提取文本内容")
        
        # 提取搜索元数据
        search_metadata = extract_search_metadata(response)
        
        # 如果搜索元数据中没有搜索查询，直接生成默认查询
        # 注意：原代码尝试调用extract_text_search_queries函数，但该函数未定义
        
        # 如果仍然没有搜索查询，生成默认查询
        if "search_queries" not in search_metadata:
            default_queries = generate_default_queries(institution, risk_list, time_range_start, time_range_end)
            search_metadata["search_queries"] = default_queries
            search_metadata["webSearchQueries"] = default_queries
        
        # 尝试解析 JSON 格式的响应
        parsed_results = parse_json_response(text_content)
        
        # 如果无法解析 JSON，尝试使用 response_parser 模块解析
        if not parsed_results:
            logger.info("尝试使用response_parser模块解析响应")
            parsed_results = parse_gemini_response(text_content, institution, risk_list)
        
        # 为结果添加搜索元数据
        if parsed_results:
            for result in parsed_results:
                # 添加完整的搜索元数据对象
                result["search_metadata"] = search_metadata
                
                # 为兼容性考虑，将各种搜索相关字段直接添加到结果的根级别
                # 1. 搜索查询 - 同时支持旧格式和新格式
                if "search_queries" in search_metadata:
                    result["search_queries"] = search_metadata["search_queries"]
                if "webSearchQueries" in search_metadata:
                    result["webSearchQueries"] = search_metadata["webSearchQueries"]
                
                # 2. 渲染内容 - 同时支持旧格式和新格式
                if "rendered_content" in search_metadata:
                    result["rendered_content"] = search_metadata["rendered_content"]
                if "renderedContent" in search_metadata:
                    result["renderedContent"] = search_metadata["renderedContent"]
                
                # 3. 将接地搜索URL添加到sources字段
                if "search_urls" in search_metadata and search_metadata["search_urls"]:
                    # 确保 sources 字段存在
                    if "sources" not in result or not result["sources"]:
                        result["sources"] = []
                    
                    # 添加接地搜索URL - 确保search_urls不是None且是可迭代的
                    search_urls = search_metadata["search_urls"]
                    if search_urls is not None:
                        url_count = 0
                        for url in search_urls:
                            if url is not None and url not in result["sources"]:
                                result["sources"].append(url)
                                url_count += 1
                        
                        logger.info(f"将 {url_count} 个接地搜索URL添加到sources字段")
        
        # 如果解析结果为空，则创建基本结果
        if not parsed_results:
            logger.warning("解析结果为空，创建基本结果")
            parsed_results = []
            for risk in risk_list:
                result = {
                    "risk_item": risk,
                    "institution_A": institution,
                    "relationship_type": "Unknown",
                    "finding_summary": text_content[:500] if text_content else "无法解析响应",
                    "potential_intermediary_B": None,
                    "sources": []
                }
                
                # 如果有搜索元数据，添加到结果中
                if search_metadata:
                    result["search_metadata"] = search_metadata
                
                parsed_results.append(result)
        
        return parsed_results
    
    except Exception as e:
        logger.error(f"处理响应时出错: {str(e)}", exc_info=True)
        raise

def generate_error_results(institution: str, risk_list: List[str], error: Exception) -> List[Dict[str, Any]]:
    """
    生成错误结果。
    
    Args:
        institution (str): 机构名称
        risk_list (List[str]): 风险项列表
        error (Exception): 错误对象
        
    Returns:
        List[Dict[str, Any]]: 错误结果列表
    """
    logger.error(f"生成错误结果: {str(error)}", exc_info=True)
    
    # 确保risk_list不为None且是可迭代的
    if risk_list is None:
        logger.warning("risk_list为None，使用默认风险项['Unknown']")
        risk_list = ['Unknown']
    elif not isinstance(risk_list, list) or len(risk_list) == 0:
        logger.warning(f"risk_list不是有效的列表或为空: {risk_list}，使用默认风险项['Unknown']")
        risk_list = ['Unknown']
    
    # 创建更详细的错误结果
    error_results = []
    for risk in risk_list:
        error_message = f"调用Gemini API失败: {str(error)}"
        # 添加错误类型信息，便于调试
        error_type = type(error).__name__
        error_results.append({
            "risk_item": risk,
            "institution_A": institution,
            "finding_summary": f"{error_message} (错误类型: {error_type})",
            "relationship_type": "Error",
            "potential_intermediary_B": None,
            "sources": [],
            "error_details": {
                "error_type": error_type,
                "error_message": str(error),
                "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
            }
        })
    
    return error_results

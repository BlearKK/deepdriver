"""
OSINT 安全风险调查工具 - Gemini API 服务模块

包含与 Google Gemini API 交互的功能，负责发送请求和接收响应。
"""

import json
import re
import os
from typing import List, Dict, Any
from google.genai.types import Tool, GenerateContentConfig, GoogleSearch, ThinkingConfig
from config import client, MODEL_ID, logger, get_prompt_template_path
from response_parser import parse_gemini_response

def investigate_risks(institution, country, risk_list):
    """
    对每个风险项进行调查，返回调查结果列表。
    
    Args:
        institution (str): 机构名称
        country (str): 国家
        risk_list (list): 风险项列表
    
    Returns:
        list: 调查结果列表
    """
    try:
        # 读取系统指令模板
        system_instruction_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'Company_search.md')
        with open(system_instruction_path, 'r', encoding='utf-8') as f:
            system_instruction_content = f.read()
        
        logger.info(f"加载系统指令模板: {system_instruction_path}")
        
        try:
            # 读取提示词模板文件内容作为user prompt
            prompt_template_path = get_prompt_template_path()
            with open(prompt_template_path, 'r', encoding='utf-8') as f:
                user_prompt_template = f.read()
        except FileNotFoundError:
            logger.error(f"提示词模板文件不存在: {prompt_template_path}")
            return [{
                "risk_item": risk,
                "institution_A": institution,
                "finding_summary": "提示词模板文件不存在，无法进行调查",
                "relationship_type": "Error",
                "potential_intermediary_B": None,
                "sources": []
            } for risk in risk_list]
        
        # 准备输入数据 - 转换为JSON字符串
        risk_list_json = json.dumps(risk_list, ensure_ascii=False)
        
        # 创建简洁的用户提示 (英文) - 使用更学术性的表述
        user_prompt = f"""Please conduct a comprehensive academic analysis of the following institution and its research domains:
        Institution: {institution}
        Geographic Location: {country}
        Research Domains: {risk_list_json}
        
        Please be thorough, objective, and factual in your analysis. Include all relevant information from credible sources.
        Please search for information on the web by English and the language of the country.
        STRICTLY output *only the JSON list*. Do not include any text before or after the JSON. This is critical for parsing the output.
        """
        
        logger.info("使用system instruction + user prompt模式构建请求")
        logger.info(f"user prompt: {user_prompt}")
        
        # 调用Gemini API进行调查
        logger.info(f"开始调用Gemini API进行调查，机构: {institution}, 国家: {country}, 风险项数量: {len(risk_list)}")
        
        # 使用新版SDK的方式调用API - 正确配置接地搜索功能
        logger.info(f"使用模型: {MODEL_ID}")
        
        # 创建GoogleSearch工具 - 使用兼容的接地搜索配置
        # 注意：当前库版本不支持最新参数，使用默认配置
        google_search_tool = Tool(
            google_search = GoogleSearch()
        )
        logger.info("创建GoogleSearch工具，使用兼容的接地搜索配置")
        
        # 配置思考参数 - 使用兼容的思考配置
        # 只使用支持的参数，必须设置include_thoughts=True才能使用thinking_budget
        thinking_config = ThinkingConfig(include_thoughts=True, thinking_budget=20000)
        logger.info(f"设置思考配置: include_thoughts=True, thinking_budget=20000")
        
        # 根据最新官方文档配置参数
        config = GenerateContentConfig(
            temperature=0.4,  # 降低温度以获得更可靠的结果
            top_p=0.95,
            top_k=40,
            max_output_tokens=65536,
            tools=[google_search_tool],  # 使用Google搜索工具
            response_modalities=["TEXT"],  # 只返回文本响应
            thinking_config=thinking_config,  # 添加思考配置
            # 使用完整的系统指令内容
            system_instruction=system_instruction_content
        )
        
        logger.info(f"生成参数配置完成: temperature=0.4, top_p=0.95, top_k=40, max_output_tokens=65536, include_thoughts=True, thinking_budget=20000, 使用兼容的接地搜索配置")
        
        # 存储搜索元数据的字典
        search_metadata = {}
        
        # 调用API并启用接地搜索
        try:
            # 调用API并启用接地搜索
            response = client.models.generate_content(
                model=MODEL_ID,
                contents=user_prompt,  # 只传递用户提示，系统指令通过config传递
                config=config
            )
            logger.info("成功使用接地搜索配置调用API")
            
            # 检查并记录搜索接地元数据
            try:
                candidate = response.candidates[0]
                
                # 按照官方文档提取搜索建议 (https://ai.google.dev/gemini-api/docs/grounding/search-suggestions)
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
                        logger.info(f"渲染内容: {rendered_content[:100] if len(rendered_content) > 100 else rendered_content}...")
                        search_metadata["rendered_content"] = rendered_content
                        # 同时添加 renderedContent 字段，以符合 Google 官方文档
                        search_metadata["renderedContent"] = rendered_content
                
                # 2. 兼容旧版 API 格式 - 检查 grounding_metadata
                if ("search_queries" not in search_metadata or "rendered_content" not in search_metadata) and hasattr(candidate, 'grounding_metadata') and candidate.grounding_metadata:
                    logger.info("检测到旧版接地元数据 (grounding_metadata)")
                    
                    # 提取渲染内容
                    if "rendered_content" not in search_metadata and hasattr(candidate.grounding_metadata, 'rendered_content'):
                        rendered_content = candidate.grounding_metadata.rendered_content
                        logger.info(f"渲染内容: {rendered_content[:100] if len(rendered_content) > 100 else rendered_content}...")
                        search_metadata["rendered_content"] = rendered_content
                        search_metadata["renderedContent"] = rendered_content
                    
                    # 提取搜索查询
                    if "search_queries" not in search_metadata and hasattr(candidate.grounding_metadata, 'web_search_queries'):
                        web_search_queries = candidate.grounding_metadata.web_search_queries
                        if web_search_queries:
                            logger.info(f"grounding_metadata 搜索查询: {web_search_queries}")
                            search_metadata["search_queries"] = web_search_queries
                            search_metadata["webSearchQueries"] = web_search_queries
                
                # 3. 兼容旧版 API 格式 - 检查 tool_use_metadata
                if "search_queries" not in search_metadata and hasattr(candidate, 'tool_use_metadata') and candidate.tool_use_metadata:
                    logger.info("检测到旧版工具使用元数据 (tool_use_metadata)")
                    
                    # 提取搜索查询
                    if hasattr(candidate.tool_use_metadata, 'search_queries'):
                        search_queries = candidate.tool_use_metadata.search_queries
                        logger.info(f"tool_use_metadata 搜索查询: {search_queries}")
                        search_metadata["search_queries"] = search_queries
                        search_metadata["webSearchQueries"] = search_queries
                
                # 4. 如果上述方法都没有提取到搜索查询，尝试从文本内容中提取
                if "search_queries" not in search_metadata and hasattr(candidate, 'content') and hasattr(candidate.content, 'parts'):
                    for part in candidate.content.parts:
                        if hasattr(part, 'text'):
                            # 尝试从文本中提取搜索查询模式
                            search_pattern = r'search(?:\s+for)?[:\s]+["\'](.+?)["\']'
                            search_matches = re.findall(search_pattern, part.text, re.IGNORECASE)
                            if search_matches:
                                search_metadata["search_queries"] = search_matches
                                search_metadata["webSearchQueries"] = search_matches
                                logger.info(f"从文本中提取到搜索查询: {search_matches}")
                                break  # 找到搜索查询后退出循环
            except Exception as meta_e:
                logger.warning(f"提取接地搜索元数据失败: {str(meta_e)}")
            
            # 获取文本内容
            text_content = response.text
            logger.info(f"获取到文本响应，长度: {len(text_content) if isinstance(text_content, str) else '(非字符串)'}")
            
            # 确保 text_content 是字符串
            if not isinstance(text_content, str):
                logger.warning(f"文本内容不是字符串，而是 {type(text_content)}")
                try:
                    text_content = str(text_content)
                    logger.info(f"将文本内容转换为字符串，长度: {len(text_content)}")
                except Exception as e:
                    logger.error(f"转换文本内容为字符串时出错: {str(e)}")
                    # 如果无法转换，返回错误结果
                    error_results = []
                    for risk in risk_list:
                        error_results.append({
                            "risk_item": risk,
                            "institution_A": institution,
                            "finding_summary": f"无法解析响应: {str(e)}",
                            "relationship_type": "Error",
                            "potential_intermediary_B": None,
                            "sources": []
                        })
                    return error_results
            
            # 尝试解析 JSON 格式的响应
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
                                
                                # 为每个结果添加搜索元数据
                                for result in results:
                                    if search_metadata and isinstance(result, dict):
                                        result["search_metadata"] = search_metadata
                                
                                return results
                            elif isinstance(results, dict):
                                logger.info("获取到JSON字典，转换为列表")
                                results = [results]
                                
                                # 为结果添加搜索元数据
                                if search_metadata:
                                    results[0]["search_metadata"] = search_metadata
                                
                                return results
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
                        
                        # 为每个结果添加搜索元数据
                        for result in results:
                            if search_metadata and isinstance(result, dict):
                                result["search_metadata"] = search_metadata
                        
                        return results
                    elif isinstance(results, dict):
                        logger.info("获取到JSON字典，转换为列表")
                        results = [results]
                        
                        # 为结果添加搜索元数据
                        if search_metadata:
                            results[0]["search_metadata"] = search_metadata
                        
                        return results
                except json.JSONDecodeError:
                    logger.warning("整个响应不是有效的JSON")
            
            except Exception as json_e:
                logger.warning(f"解析JSON响应时出错: {str(json_e)}")
            
            # 如果无法解析JSON，尝试使用response_parser模块解析
            logger.info("尝试使用response_parser模块解析响应")
            parsed_results = parse_gemini_response(text_content, institution, risk_list)
            
            # 为结果添加搜索元数据
            if parsed_results:
                # 确保搜索元数据中有搜索查询
                if not search_metadata:
                    search_metadata = {}
                
                # 如果所有方法都没有提取到搜索查询，根据机构名称和风险项生成默认查询
                if "search_queries" not in search_metadata:
                    default_queries = []
                    
                    # 根据机构名称和风险项生成查询
                    for risk in risk_list:
                        # 中文查询 - 更精确的查询格式
                        default_queries.append(f"\"{institution}\" \"{risk}\" 合作")
                        default_queries.append(f"\"{institution}\" \"{risk}\" 关系")
                        
                        # 英文查询 - 更精确的查询格式
                        default_queries.append(f"\"{institution}\" \"{risk}\" collaboration")
                        default_queries.append(f"\"{institution}\" \"{risk}\" partnership")
                        default_queries.append(f"\"{institution}\" \"{risk}\" connection")
                    
                    search_metadata["search_queries"] = default_queries
                    logger.info(f"未找到API返回的搜索建议，添加默认搜索查询: {default_queries}")
                
                # 为每个结果添加搜索元数据
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
                        
                logger.info(f"成功为{len(parsed_results)}个结果添加搜索元数据")
                logger.info(f"搜索元数据字段: {', '.join(search_metadata.keys())}")
                
                # 记录完整的第一个结果元数据，便于调试
                if parsed_results and len(parsed_results) > 0:
                    logger.info(f"第一个结果的搜索元数据字段: {', '.join(k for k in parsed_results[0].keys() if k.startswith('search') or k in ['renderedContent', 'webSearchQueries'])}")
                    if 'renderedContent' in parsed_results[0]:
                        rendered_preview = parsed_results[0]['renderedContent'][:100] if len(parsed_results[0]['renderedContent']) > 100 else parsed_results[0]['renderedContent']
                        logger.info(f"第一个结果的 renderedContent 预览: {rendered_preview}...")
                    if 'webSearchQueries' in parsed_results[0]:
                        logger.info(f"第一个结果的 webSearchQueries: {parsed_results[0]['webSearchQueries']}")
                    if 'search_metadata' in parsed_results[0]:
                        logger.info(f"第一个结果的 search_metadata 字段: {', '.join(parsed_results[0]['search_metadata'].keys())}")
                
            
            # 如果解析结果为空，则创建基本结果
            if not parsed_results:
                logger.warning("response_parser解析结果为空，创建基本结果")
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
        
        except Exception as api_e:
            logger.error(f"调用API时出错: {str(api_e)}")
            # 创建错误结果
            error_results = []
            for risk in risk_list:
                error_results.append({
                    "risk_item": risk,
                    "institution_A": institution,
                    "finding_summary": f"调用Gemini API失败: {str(api_e)}",
                    "relationship_type": "Error",
                    "potential_intermediary_B": None,
                    "sources": []
                })
            return error_results
    
    except Exception as e:
        logger.error(f"调查风险时出错: {str(e)}", exc_info=True)
        # 创建错误结果
        error_results = []
        for risk in risk_list:
            error_results.append({
                "risk_item": risk,
                "institution_A": institution,
                "finding_summary": f"调查风险时出错: {str(e)}",
                "relationship_type": "Error",
                "potential_intermediary_B": None,
                "sources": []
            })
        return error_results

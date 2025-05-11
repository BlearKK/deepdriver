"""
OSINT 安全风险调查工具 - Gemini API 服务模块

主要服务接口，负责协调各个子模块完成风险调查任务。
"""

import os
from typing import List, Dict, Any
from config import logger, API_KEY
from gemini_client import call_gemini_api
from prompt_manager import load_prompts
from response_processor import process_response, generate_error_results

def mock_investigate_risks(institution, country, risk_list):
    """
    提供模拟的调查结果，在Gemini API不可用时使用。
    
    Args:
        institution (str): 机构名称
        country (str): 国家
        risk_list (list): 风险项列表
    
    Returns:
        list: 模拟的调查结果列表
    """
    logger.warning(f"使用模拟数据代替Gemini API调用，机构: {institution}, 国家: {country}")
    
    results = []
    for risk in risk_list:
        result = {
            "risk_item": risk,
            "institution_A": institution,
            "relationship_type": "模拟数据",
            "finding_summary": f"这是{institution}关于{risk}的模拟调查结果。由于Gemini API暂时不可用，系统生成了此模拟数据用于测试。请在确保API密钥正确设置后再次尝试。",
            "potential_intermediary_B": "模拟中间机构",
            "sources": [
                "https://example.com/source1",
                "https://example.com/source2"
            ]
        }
        results.append(result)
    
    return results

def investigate_risks(institution, country, risk_list, enable_grounding=False, time_range_start=None, time_range_end=None):
    """
    对每个风险项进行调查，返回调查结果列表。
    如果Gemini API不可用或API_KEY未配置，将使用模拟数据。
    
    Args:
        institution (str): 机构名称
        country (str): 国家
        risk_list (list): 风险项列表
        enable_grounding (bool): 是否启用接地搜索功能
    
    Returns:
        list: 调查结果列表
    """
    # 强制设置不使用模拟模式
    use_mock = False  # 强制不使用模拟数据
    # 原代码: use_mock = os.environ.get("USE_MOCK", "false").lower() == "true"
    
    # 检查API密钥是否配置
    if use_mock or not API_KEY:
        logger.warning(f"USE_MOCK设置为true或API_KEY未配置，使用模拟数据")
        return mock_investigate_risks(institution, country, risk_list)
    
    try:
        # 1. 加载系统指令和构建用户提示
        logger.info(f"开始调查风险，机构: {institution}, 国家: {country}, 风险项数量: {len(risk_list)}, 时间范围: {time_range_start} 到 {time_range_end}")
        system_instruction, user_prompt = load_prompts(institution, country, risk_list, time_range_start, time_range_end)
        
        if not system_instruction:
            logger.error("无法加载系统指令，返回错误结果")
            return generate_error_results(institution, risk_list, ValueError("系统指令文件不存在或无法读取"))
        
        # 2. 直接调用API
        try:
            logger.info(f"调用Gemini API，接地搜索功能状态: {enable_grounding}")
            response = call_gemini_api(user_prompt, system_instruction, enable_grounding=enable_grounding)
            
            # 保存原始响应
            raw_text = response.text if hasattr(response, 'text') else ""
            raw_metadata = {}
            
            # 提取原始元数据
            if hasattr(response, 'metadata'):
                raw_metadata = response.metadata
                logger.info(f"提取到原始元数据，字段数: {len(raw_metadata)}")
            else:
                logger.warning("响应中没有metadata字段")
                
        except Exception as api_error:
            logger.error(f"调用API失败: {str(api_error)}")
            return generate_error_results(institution, risk_list, api_error)
        
        # 4. 处理响应
        try:
            results = process_response(response, institution, country, risk_list, time_range_start, time_range_end)
            
            # 添加原始响应到结果中
            if results and len(results) > 0:
                results[0]['raw_text'] = raw_text
                results[0]['raw_metadata'] = raw_metadata
                logger.info("已将原始响应添加到结果中")
                
            logger.info(f"成功处理响应，获得 {len(results)} 个结果")
            return results
        except Exception as process_error:
            logger.error(f"处理响应失败: {str(process_error)}")
            return generate_error_results(institution, risk_list, process_error)
    
    except Exception as e:
        logger.error(f"调查风险时出错: {str(e)}", exc_info=True)
        return generate_error_results(institution, risk_list, e)

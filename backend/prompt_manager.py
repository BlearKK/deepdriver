"""
OSINT 安全风险调查工具 - 提示词管理模块

负责加载、处理和构建提示词模板和系统指令。
"""

import os
import json
from typing import List, Dict, Any, Optional, Tuple
from config import logger, get_prompt_template_path

def find_system_instruction_file() -> Optional[str]:
    """
    查找系统指令文件 (Company_search.md)。
    
    Returns:
        str: 系统指令文件路径，如果找不到则返回 None
    """
    # 可能的文件路径
    system_instruction_path_options = [
        os.path.join(os.path.dirname(__file__), 'Company_search.md'),
        os.path.join(os.path.dirname(os.path.dirname(__file__)), 'Company_search.md')
    ]
    
    # 查找存在的文件
    for path_option in system_instruction_path_options:
        if os.path.exists(path_option):
            logger.info(f"找到系统指令文件: {path_option}")
            return path_option
    
    # 如果找不到文件
    logger.error("关键的系统指令文件Company_search.md在预设路径中均未找到")
    return None

def load_system_instruction() -> Optional[str]:
    """
    加载系统指令内容。
    
    Returns:
        str: 系统指令内容，如果加载失败则返回 None
    """
    # 查找系统指令文件
    system_instruction_path = find_system_instruction_file()
    if not system_instruction_path:
        return None
    
    try:
        # 读取文件内容
        with open(system_instruction_path, 'r', encoding='utf-8') as f:
            system_instruction_content = f.read()
        
        logger.info(f"加载系统指令模板: {system_instruction_path}")
        return system_instruction_content
    except Exception as e:
        logger.error(f"读取系统指令文件时出错: {str(e)}")
        return None

def load_user_prompt_template() -> Optional[str]:
    """
    加载用户提示词模板内容。
    
    Returns:
        str: 用户提示词模板内容，如果加载失败则返回 None
    """
    try:
        # 获取提示词模板文件路径
        prompt_template_path = get_prompt_template_path()
        
        # 读取文件内容
        with open(prompt_template_path, 'r', encoding='utf-8') as f:
            user_prompt_template = f.read()
        
        logger.info(f"加载用户提示词模板: {prompt_template_path}")
        return user_prompt_template
    except Exception as e:
        logger.error(f"读取用户提示词模板文件时出错: {str(e)}")
        return None

def build_user_prompt(institution: str, country: str, risk_list: List[str], time_range_start: Optional[str] = None, time_range_end: Optional[str] = None) -> str:
    """
    构建用户提示内容。
    
    Args:
        institution (str): 机构名称
        country (str): 国家
        risk_list (List[str]): 风险项列表
        
    Returns:
        str: 构建好的用户提示内容
    """
    # 转换为JSON字符串
    risk_list_json = json.dumps(risk_list, ensure_ascii=False)
    
    # 创建更详细的用户提示，包含具体指导
    user_prompt = f"""
 I need you to investigate potential connections between the following institution and risk items:
    
    Institution A: {institution}
    Location: {country}
    Risk List C: {risk_list_json}
    """    
    
    # 添加时间范围参数（如果提供）
    if time_range_start:
        user_prompt += f"""
    Time Range Start: {time_range_start}
    """
    
    if time_range_end:
        user_prompt += f"""
    Time Range End: {time_range_end}
    """
        
    user_prompt += f"""
    
    For each risk item, please analyze any direct or indirect connections, or significant mentions linking them with the institution{', focusing STRICTLY on information within the specified time range' if time_range_start or time_range_end else ''}.
    
    {'' if not (time_range_start or time_range_end) else 'IMPORTANT: You MUST ONLY include events, publications, collaborations, and other connections that occurred WITHIN the specified time range. DO NOT include information from outside this time period. If a source does not explicitly mention a date within the specified range, do NOT include it in your analysis.'}
    
    
    Please format your response as a JSON list following the exact schema described in the system instructions.
    
    IMPORTANT INSTRUCTION: You MUST search for each item in BOTH English AND the native language of {country}. 
    For example, if the country is "China", search using both English terms AND Chinese terms.
    If the country is "Germany", search using both English terms AND German terms.
    If the country is "Worldwide", search using English terms.
    
    Remember to use numerical citations [1], [2], etc. in the finding_summary that correspond exactly to the sources array.
    """
    
    logger.info("构建用户提示内容完成")
    return user_prompt

def load_prompts(institution: str, country: str, risk_list: List[str], time_range_start: Optional[str] = None, time_range_end: Optional[str] = None) -> Tuple[Optional[str], str]:
    """
    加载系统指令和构建用户提示。
    
    Args:
        institution (str): 机构名称
        country (str): 国家
        risk_list (List[str]): 风险项列表
        
    Returns:
        Tuple[Optional[str], str]: 系统指令内容和用户提示内容
    """
    # 加载系统指令
    system_instruction = load_system_instruction()
    
    # 构建用户提示
    user_prompt = build_user_prompt(institution, country, risk_list, time_range_start, time_range_end)
    
    return system_instruction, user_prompt

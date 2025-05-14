"""
模拟数据生成器 - 用于DeepSearch功能的测试模式
"""

import random
import time
import json
import os
from datetime import datetime

# 预定义的关系类型
RELATIONSHIP_TYPES = [
    "Direct", 
    "Indirect", 
    "Significant Mention", 
    "No Evidence Found"
]

# 预定义的模拟发现摘要
MOCK_FINDINGS = {
    "Direct": [
        "有明确证据表明两个机构之间存在直接合作关系。包括联合研究项目、学术交流计划和共同发表的研究论文。",
        "发现多项联合研究项目和技术转让协议，表明两个机构之间存在紧密的合作伙伴关系。",
        "有文件记录显示两个机构签署了正式合作协议，包括人员交流、资源共享和联合研究项目。"
    ],
    "Indirect": [
        "通过第三方机构发现间接联系。两个机构都与同一研究网络或联盟有关联，但没有直接合作证据。",
        "两个机构通过共同的合作伙伴或中介机构建立了间接联系，但未发现直接合作证据。",
        "发现两个机构参与了同一国际研究计划，但似乎没有直接互动。"
    ],
    "Significant Mention": [
        "在目标机构的出版物或官方文件中发现对该研究组织的多次引用和参考，表明关注度较高。",
        "目标机构的研究人员经常引用该组织的工作，但没有发现正式合作关系。",
        "在目标机构的战略文件中提到该研究组织作为重要参考对象，但未发现实质性合作。"
    ],
    "No Evidence Found": [
        "未发现两个机构之间存在任何形式的合作、联系或重要提及。",
        "公开资料中没有发现任何表明两个机构之间存在关联的证据。",
        "经过全面搜索，未能找到任何表明两个机构之间存在关系的信息。"
    ]
}

def generate_mock_result(institution_a, risk_item):
    """
    生成模拟的分析结果
    
    Args:
        institution_a: 目标机构名称
        risk_item: 风险项目名称
        
    Returns:
        dict: 模拟的分析结果
    """
    # 基于机构名称和风险项目名称生成一个伪随机种子，确保相同输入产生相同结果
    seed = hash(f"{institution_a}:{risk_item}") % 10000
    random.seed(seed)
    
    # 随机选择关系类型，但偏向于"No Evidence Found"
    weights = [0.1, 0.15, 0.15, 0.6]  # 权重分配给各种关系类型
    relationship_type = random.choices(RELATIONSHIP_TYPES, weights=weights, k=1)[0]
    
    # 根据关系类型选择一个模拟发现摘要
    finding_summary = random.choice(MOCK_FINDINGS[relationship_type])
    
    # 构建结果对象
    result = {
        "risk_item": risk_item,
        "institution_A": institution_a,
        "relationship_type": relationship_type,
        "finding_summary": finding_summary
    }
    
    return result

# 模拟连接超时的设置
# 如果设置为True，将模拟连接超时情况
SIMULATE_TIMEOUT = os.getenv("SIMULATE_TIMEOUT", "false").lower() == "true"

# 模拟连接超时的时间（秒）
# 默认为180秒，小于前端的270秒重连时间，以确保能触发重连
# 可以通过环境变量SIMULATE_TIMEOUT_SECONDS来调整
SIMULATE_TIMEOUT_SECONDS = int(os.getenv("SIMULATE_TIMEOUT_SECONDS", "180"))

# 记录模拟开始时间
_simulation_start_time = datetime.now()

def mock_call_openrouter_api(system_prompt, user_prompt):
    """
    模拟OpenRouter API调用
    
    Args:
        system_prompt: 系统提示
        user_prompt: 用户提示
        
    Returns:
        list: 包含模拟结果的列表
    """
    global _simulation_start_time
    
    # 防止递归调用
    import inspect
    frame = inspect.currentframe()
    stack_depth = 0
    while frame:
        stack_depth += 1
        frame = frame.f_back
        
    # 如果调用栈深度超过一定限制，返回错误信息
    if stack_depth > 50:  # 设置一个合理的限制
        print(f"警告: 检测到递归调用，当前栈深度: {stack_depth}")
        return [{
            "risk_item": "Recursion Error",
            "institution_A": "Error",
            "relationship_type": "Unknown",
            "finding_summary": "Detected potential infinite recursion in mock API call"
        }]
    
    # 检查是否需要模拟超时
    if SIMULATE_TIMEOUT:
        current_time = datetime.now()
        elapsed_seconds = (current_time - _simulation_start_time).total_seconds()
        
        # 如果超过了设定的超时时间，重置计时并抛出异常
        if elapsed_seconds > SIMULATE_TIMEOUT_SECONDS:
            print(f"模拟连接超时: 已运行{elapsed_seconds:.1f}秒，超过了{SIMULATE_TIMEOUT_SECONDS}秒的限制")
            _simulation_start_time = current_time  # 重置计时器
            raise Exception("模拟连接超时")
    
    # 从用户提示中提取机构名称和风险项目
    try:
        # 提取提示中的机构名称和风险项目
        prompt_lines = user_prompt.strip().split('\n')
        analysis_line = prompt_lines[1] if len(prompt_lines) > 1 else prompt_lines[0]
        parts = analysis_line.split('与')
        
        if len(parts) >= 2:
            institution_a = parts[0].replace('请分析', '').strip()
            risk_item = parts[1].split('之间')[0].strip()
        else:
            # 如果无法解析，使用默认值
            institution_a = "Unknown Institution"
            risk_item = "Unknown Risk Item"
        
        # 生成模拟结果
        result = generate_mock_result(institution_a, risk_item)
        
        # 模拟API延迟 - 在模拟超时模式下增加延迟
        if SIMULATE_TIMEOUT:
            delay = random.uniform(1.0, 3.0)  # 增加延迟，使得超时更快发生
        else:
            delay = random.uniform(0.5, 2.0)
        time.sleep(delay)
        
        return [result]
    
    except Exception as e:
        print(f"Error in mock API call: {str(e)}")
        return [{
            "relationship_type": "Unknown",
            "finding_summary": f"模拟API调用出错: {str(e)}"
        }]

# 测试代码
if __name__ == "__main__":
    # 测试模拟API调用
    test_prompt = "请分析 University of Toronto 与 Army Research Laboratory 之间的关系。"
    result = mock_call_openrouter_api("", test_prompt)
    print(json.dumps(result, ensure_ascii=False, indent=2))

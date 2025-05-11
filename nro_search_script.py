import os
import json
import requests
from time import sleep
import argparse
from dotenv import load_dotenv
from tqdm import tqdm

# 加载环境变量（如果有.env文件）
load_dotenv()

# 1. 配置
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")  # 请先设置环境变量
if not OPENROUTER_API_KEY:
    raise ValueError("请设置OPENROUTER_API_KEY环境变量，或创建.env文件包含此变量")

MODEL = "perplexity/sonar-reasoning-pro"
NRO_JSON_PATH = "frontend/osintdigger/public/Sanction_list/Named Research Organizations.json"
PROMPT_PATH = "NRO_search.md"
OUTPUT_PATH = "nro_search_results.json"

def parse_arguments():
    """解析命令行参数"""
    parser = argparse.ArgumentParser(description='批量调用LLM进行机构关系分析')
    parser.add_argument('--institution', '-i', type=str, required=False,
                      help='目标机构名称(Institution A)')
    parser.add_argument('--output', '-o', type=str, default=OUTPUT_PATH,
                      help=f'输出结果JSON文件路径，默认为{OUTPUT_PATH}')
    parser.add_argument('--model', '-m', type=str, default=MODEL,
                      help=f'使用的LLM模型，默认为{MODEL}')
    parser.add_argument('--delay', '-d', type=float, default=1.0,
                      help='每次API调用之间的延迟秒数，默认为1秒')
    return parser.parse_args()

def read_json_file(file_path):
    """读取JSON文件并返回内容"""
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        print(f"读取{file_path}失败: {e}")
        return None

def read_prompt_template(file_path):
    """读取prompt模板文件"""
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            return f.read()
    except Exception as e:
        print(f"读取{file_path}失败: {e}")
        return None

def call_openrouter_api(system_prompt, user_prompt, model_name):
    """调用OpenRouter API"""
    url = "https://openrouter.ai/api/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://osintdigger.com",  # 替换为你的网站
        "X-Title": "OSINT Digger"  # 应用名称
    }
    
    payload = {
        "model": model_name,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ],
        "stream": False,  # 测试阶段用False，后续可用True实现流式
        "temperature": 0.1  # 使用较低的温度以获得更确定性的回答
    }
    
    try:
        response = requests.post(url, headers=headers, json=payload)
        response.raise_for_status()
        # 解析LLM返回的内容
        content = response.json()["choices"][0]["message"]["content"]
        try:
            # 尝试提取JSON部分
            json_start = content.find('[')
            json_end = content.rfind(']') + 1
            if json_start >= 0 and json_end > json_start:
                json_content = content[json_start:json_end]
                return json.loads(json_content)
            else:
                # 如果没有找到JSON数组，尝试解析整个内容
                return json.loads(content)
        except Exception as e:
            print(f"解析LLM回复失败: {e}")
            print(f"原始回复: {content}")
            # 尝试创建一个基本结构的回复
            return [{
                "risk_item": user_prompt,
                "institution_A": "解析失败",
                "relationship_type": "Unknown",
                "finding_summary": f"解析失败: {str(e)[:100]}..."
            }]
    except requests.exceptions.RequestException as e:
        print(f"API调用失败: {e}")
        return None

def save_results(results, output_path):
    """保存结果到JSON文件"""
    try:
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(results, f, ensure_ascii=False, indent=2)
        print(f"\n全部完成，结果已保存到 {output_path}")
        return True
    except Exception as e:
        print(f"保存结果失败: {e}")
        return False

def main():
    """主函数"""
    args = parse_arguments()
    
    # 读取研究机构列表
    nro_data = read_json_file(NRO_JSON_PATH)
    if not nro_data:
        return
    
    risk_list = [item["name"] for item in nro_data]
    print(f"已加载 {len(risk_list)} 个研究机构名称")
    
    # 读取Prompt模板
    system_prompt = read_prompt_template(PROMPT_PATH)
    if not system_prompt:
        return
    
    # 获取目标机构名称
    institution_A = args.institution
    if not institution_A:
        institution_A = input("请输入Target Institution A：").strip()
    
    print(f"开始分析目标机构 '{institution_A}' 与 {len(risk_list)} 个研究机构的关系...")
    
    results = []
    
    # 批量调用LLM，使用tqdm显示进度条
    for idx, risk_item in enumerate(tqdm(risk_list, desc="处理进度")):
        # 构建用户提示
        user_prompt = f"""
请分析 {institution_A} 与 {risk_item} 之间的关系。
请按照要求的JSON格式返回结果。
"""
        
        print(f"\n正在处理({idx+1}/{len(risk_list)}): {risk_item}")
        
        # 调用LLM
        llm_result = call_openrouter_api(system_prompt, user_prompt, args.model)
        
        if llm_result:
            # 确保结果是列表格式
            if not isinstance(llm_result, list):
                llm_result = [llm_result]
            
            # 只保留第一个对象，并确保字段完整
            result = llm_result[0]
            result["risk_item"] = risk_item
            result["institution_A"] = institution_A
            if "relationship_type" not in result:
                result["relationship_type"] = "Unknown"
            
            results.append(result)
            
            # 实时输出卡片内容
            relationship = result.get("relationship_type", "Unknown")
            print(f"关系类型: {relationship}")
            if relationship in ["Direct", "Indirect", "Significant Mention"]:
                summary = result.get("finding_summary", "无详细信息")
                print(f"发现摘要: {summary[:100]}..." if len(summary) > 100 else summary)
        else:
            print("本项处理失败，跳过。")
        
        # 适当延迟，防止API限流
        sleep(args.delay)
    
    # 保存所有结果
    save_results(results, args.output)
    
    # 输出统计信息
    relationship_counts = {}
    for result in results:
        rel_type = result.get("relationship_type", "Unknown")
        relationship_counts[rel_type] = relationship_counts.get(rel_type, 0) + 1
    
    print("\n关系类型统计:")
    for rel_type, count in relationship_counts.items():
        print(f"- {rel_type}: {count} 个")

if __name__ == "__main__":
    main()

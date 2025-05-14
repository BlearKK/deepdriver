import os
import json
import time
import requests
from flask import Blueprint, request, jsonify, Response
import concurrent.futures
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

# 获取API密钥
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
if not OPENROUTER_API_KEY:
    raise ValueError("请设置OPENROUTER_API_KEY环境变量")

# 配置
MODEL = "perplexity/sonar-reasoning-pro"
# 使用绝对路径
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# 打印路径信息，用于调试
print(f"BASE_DIR: {BASE_DIR}")
print(f"Current directory: {os.getcwd()}")

# 尝试不同的路径组合
NRO_JSON_PATH_OPTIONS = [
    os.path.join(BASE_DIR, "frontend", "osintdigger", "public", "Sanction_list", "Named Research Organizations.json"),
    os.path.join(BASE_DIR, "frontend", "osintdigger", "public", "NRO_list", "Named Research Organizations.json"),
    "../frontend/osintdigger/public/Sanction_list/Named Research Organizations.json",
    "../frontend/osintdigger/public/NRO_list/Named Research Organizations.json",
    "./frontend/osintdigger/public/Sanction_list/Named Research Organizations.json",
    "./frontend/osintdigger/public/NRO_list/Named Research Organizations.json",
    os.path.join(os.getcwd(), "frontend", "osintdigger", "public", "Sanction_list", "Named Research Organizations.json"),
    os.path.join(os.getcwd(), "frontend", "osintdigger", "public", "NRO_list", "Named Research Organizations.json")
]

# 选择第一个存在的文件路径
NRO_JSON_PATH = None
for path in NRO_JSON_PATH_OPTIONS:
    if os.path.exists(path):
        NRO_JSON_PATH = path
        print(f"Found NRO_JSON_PATH: {NRO_JSON_PATH}")
        break

if not NRO_JSON_PATH:
    NRO_JSON_PATH = NRO_JSON_PATH_OPTIONS[0]  # 默认使用第一个路径
    print(f"Warning: No valid NRO_JSON_PATH found, using default: {NRO_JSON_PATH}")

# 同样处理PROMPT_PATH
PROMPT_PATH_OPTIONS = [
    os.path.join(BASE_DIR, "NRO_search.md"),
    "../NRO_search.md",
    "./NRO_search.md",
    os.path.join(os.getcwd(), "NRO_search.md"),
    os.path.join(BASE_DIR, "backend", "NRO_search.md"),
    os.path.join(os.getcwd(), "backend", "NRO_search.md")
]

PROMPT_PATH = None
for path in PROMPT_PATH_OPTIONS:
    if os.path.exists(path):
        PROMPT_PATH = path
        print(f"Found PROMPT_PATH: {PROMPT_PATH}")
        break

if not PROMPT_PATH:
    PROMPT_PATH = PROMPT_PATH_OPTIONS[0]  # 默认使用第一个路径
    print(f"Warning: No valid PROMPT_PATH found, using default: {PROMPT_PATH}")

# 创建Blueprint
deepsearch_simple_bp = Blueprint('deepsearch_simple', __name__, url_prefix='/api')

# 打印Blueprint信息
print(f"DeepSearch Simple Blueprint created with URL prefix: {deepsearch_simple_bp.url_prefix}")

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

def call_openrouter_api(system_prompt, user_prompt):
    """调用OpenRouter API"""
    url = "https://openrouter.ai/api/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://osintdigger.com",  # 替换为你的网站
        "X-Title": "OSINT Digger"  # 应用名称
    }
    
    payload = {
        "model": MODEL,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ],
        "stream": False,  # 使用非流式API
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

# 并行处理多个请求的函数
def process_risk_item(risk_item, institution_A, system_prompt):
    """并行处理单个风险项目的函数"""
    print(f"Processing risk item: {risk_item} for institution: {institution_A}")
    
    # 构建user_prompt
    user_prompt = f"""
请分析 {institution_A} 与 {risk_item} 之间的关系。
请按照要求的JSON格式返回结果。
"""
    
    # 调用LLM
    llm_result = call_openrouter_api(system_prompt, user_prompt)
    
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
        
        # 确保字段类型正确
        if not isinstance(result.get("finding_summary", ""), str):
            result["finding_summary"] = str(result.get("finding_summary", ""))
            
        print(f"Successfully processed risk item: {risk_item}")
        return result
    else:
        # 返回错误结果
        error_result = {
            "risk_item": risk_item,
            "institution_A": institution_A,
            "relationship_type": "Unknown",
            "finding_summary": "处理失败，无法获取结果"
        }
        print(f"Failed to process risk item: {risk_item}")
        return error_result

@deepsearch_simple_bp.route('/deepsearch_simple', methods=['GET', 'POST', 'OPTIONS'])
def deepsearch_simple():
    # OPTIONS 请求处理
    if request.method == 'OPTIONS':
        # 返回空响应，Flask-CORS会处理CORS头部
        print("Received OPTIONS request to /api/deepsearch_simple, returning empty response")
        response = Response(status=204)  # No Content
        return response

    # 处理GET请求
    # 打印请求信息，帮助调试
    print(f"Received request to /api/deepsearch_simple with args: {request.args}")
    
    institution_A = request.args.get('institution_A', '')
    if not institution_A:
        error_msg = {"error": "Missing institution_A parameter"}
        print(f"Error: {error_msg}")
        return jsonify(error_msg), 400
    
    # 获取已处理的项目列表（如果有）
    processed_items = request.args.get('processed', '')
    processed_list = processed_items.split(',') if processed_items else []
    print(f"Processing DeepSearch Simple request: institution_A={institution_A}, already processed: {len(processed_list)} items")
    
    # 如果提供了session_id，尝试从缓存恢复之前的处理状态
    session_id = request.args.get('session_id', '')
    if session_id:
        print(f"Continuing session: {session_id}")
    
    # 读取系统提示
    system_prompt = read_prompt_template(PROMPT_PATH)
    if not system_prompt:
        # 如果无法读取提示模板，使用硬编码的默认提示
        print("Warning: Could not read prompt template, using default prompt")
        system_prompt = """你是一个专门分析机构关系的专家。你的任务是分析目标机构A与风险机构B之间的关系。

请按照以下格式返回JSON结果：
[
  {
    "relationship_type": "Direct/Indirect/Significant Mention/No Evidence Found",
    "finding_summary": "详细发现总结"
  }
]

关系类型定义：
- Direct: 直接关系，如合作、合资、合同等
- Indirect: 间接关系，如通过第三方建立的联系
- Significant Mention: 有重要提及，但关系不明确
- No Evidence Found: 没有找到明显关系证据

请确保返回的是有效的JSON格式。"""

    # 打印请求信息，帮助调试
    print(f"Received request to /api/deepsearch_simple with args: {request.args}")
    
    institution_A = request.args.get('institution_A', '')
    if not institution_A:
        error_msg = {"error": "Missing institution_A parameter"}
        print(f"Error: {error_msg}")
        return jsonify(error_msg), 400
    
    # 获取已处理的项目列表（如果有）
    processed_items = request.args.get('processed', '')
    processed_list = processed_items.split(',') if processed_items else []
    print(f"Processing DeepSearch Simple request: institution_A={institution_A}, already processed: {len(processed_list)} items")
    
    # 如果提供了session_id，尝试从缓存恢复之前的处理状态
    session_id = request.args.get('session_id', '')
    if session_id:
        print(f"Continuing session: {session_id}")
    
    # 读取系统提示
    system_prompt = read_prompt_template(PROMPT_PATH)
    if not system_prompt:
        # 如果无法读取提示模板，使用硬编码的默认提示
        print("Warning: Could not read prompt template, using default prompt")
        system_prompt = """
你是一个专门分析机构关系的专家。你的任务是分析目标机构A与风险机构B之间的关系。

请按照以下格式返回JSON结果：
[
  {
    "relationship_type": "Direct/Indirect/Significant Mention/No Evidence Found",
    "finding_summary": "详细的关系分析和证据总结"
  }
]

关系类型说明：
- Direct: 直接关系，如合作伙伴、子公司、资金往来等
- Indirect: 间接关系，如通过第三方建立的联系
- Significant Mention: 有重要提及，但关系不明确
- No Evidence Found: 没有找到明显关系证据

请确保返回的是有效的JSON格式。
"""
    
    # 读取研究机构列表
    nro_data = read_json_file(NRO_JSON_PATH)
    
    # 如果无法读取研究机构列表，尝试直接从backend目录加载
    if not nro_data:
        print("Warning: Could not read NRO list from configured paths")
        # 尝试直接从backend目录加载
        current_dir = os.path.dirname(os.path.abspath(__file__))
        direct_path = os.path.join(current_dir, "Named Research Organizations.json")
        print(f"尝试直接从当前目录加载: {direct_path}")
        
        try:
            with open(direct_path, "r", encoding="utf-8") as f:
                nro_data = json.load(f)
                print(f"成功从当前目录加载NRO数据，包含{len(nro_data)}个条目")
        except Exception as e:
            print(f"从当前目录加载失败: {e}")
            return jsonify({"error": "Failed to load NRO data"}), 500
    
    # 注意：JSON文件中的字段名是"Name"（首字母大写）
    risk_list = [item["Name"] for item in nro_data]
    
    # 使用完整列表，而不是只取前5个
    sample_risk_list = risk_list
    
    # 过滤掉已处理的项目
    if processed_list:
        print(f"过滤已处理的项目，原始列表长度: {len(sample_risk_list)}")
        sample_risk_list = [item for item in sample_risk_list if item not in processed_list]
        print(f"过滤后列表长度: {len(sample_risk_list)}")
    
    # 获取批处理大小，默认10个项目一批
    batch_size = int(request.args.get('batch_size', 10))
    # 限制每次请求处理的最大项目数，防止请求超时
    max_items = min(batch_size, len(sample_risk_list))
    
    print(f"处理批次大小: {max_items}, 总剩余项目: {len(sample_risk_list)}")
    
    # 只处理指定数量的项目
    current_batch = sample_risk_list[:max_items]
    
    results = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
        # 创建任务列表
        futures = [executor.submit(process_risk_item, risk_item, institution_A, system_prompt) for risk_item in current_batch]
        
        # 收集结果
        for future in concurrent.futures.as_completed(futures):
            try:
                result = future.result()
                results.append(result)
                print(f"处理完成: {result['risk_item']}")
            except Exception as e:
                print(f"处理失败: {e}")
                # 添加错误结果
                error_result = {
                    "risk_item": "Unknown",  # 失败时无法知道具体是哪个项目
                    "institution_A": institution_A,
                    "relationship_type": "Unknown",
                    "finding_summary": f"处理失败: {str(e)[:100]}..."
                }
                results.append(error_result)
    
    # 构建响应
    response_data = {
        "total": len(risk_list),  # 总数是完整的NRO列表长度
        "processed": len(processed_list) + len(results),  # 已处理的数量
        "remaining": len(sample_risk_list) - len(results),  # 剩余待处理的数量
        "results": results,
        "batch_size": max_items,  # 返回当前批次大小
        "continuation": len(sample_risk_list) > max_items,  # 如果还有未处理的项目，返回true
        "next_batch": [item for item in processed_list] + [result["risk_item"] for result in results]  # 下一批处理时要跳过的项目
    }
    
    # 打印响应数据结构，便于调试
    print(f"Response data structure: {list(response_data.keys())}")
    print(f"Results count: {len(results)}")
    if results:
        print(f"Sample result: {results[0]}")
    
    # 打印响应信息
    print(f"Sending response with {len(results)} results, {len(processed_list)} already processed")
    
    # 返回结果，使用jsonify创建响应
    response = jsonify(response_data)
    
    # 记录请求信息便于调试
    print(f"Request Origin: {request.headers.get('Origin', 'None')}")
    
    # 只添加缓存控制头，确保不缓存响应
    # CORS相关头部由Flask-CORS自动处理
    response.headers.add('Cache-Control', 'no-store, no-cache, must-revalidate, max-age=0')
    response.headers.add('Pragma', 'no-cache')
    response.headers.add('Expires', '0')
    
    print(f"Blueprint: Returning JSON response. Flask-CORS should handle Access-Control headers.")
    print(f"Response headers before Flask-CORS processing: {dict(response.headers)}")
    
    return response

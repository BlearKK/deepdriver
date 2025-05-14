"""
修复版的DeepSearch功能 - 解决变量引用错误
"""

import os
import json
import time
import requests
from flask import Blueprint, Response, stream_with_context, request, jsonify
from dotenv import load_dotenv

# 导入模拟数据生成器
from mock_data import mock_call_openrouter_api

# 加载环境变量
load_dotenv()

# 创建Blueprint
fixed_deepsearch_bp = Blueprint('fixed_deepsearch', __name__, url_prefix='/api')

# 存储会话数据的字典
session_data = {}

# 添加健康检查端点
@fixed_deepsearch_bp.route('/health', methods=['GET'])
def health_check():
    return jsonify({"status": "ok", "message": "DeepSearch API is running"})


# 测试模式设置 - 默认为关闭
TEST_MODE = os.getenv("TEST_MODE", "false").lower() == "true"

# 打印测试模式状态
print(f"FixedDeepSearch运行模式: {'测试模式' if TEST_MODE else '生产模式'}")

# 获取API密钥
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")

# 如果不是测试模式且没有API密钥，则报错
if not TEST_MODE and not OPENROUTER_API_KEY:
    raise ValueError("请设置OPENROUTER_API_KEY环境变量或启用测试模式")

# 配置
MODEL = "perplexity/sonar-reasoning-pro"

# 使用绝对路径
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# 打印路径信息，用于调试
print(f"BASE_DIR: {BASE_DIR}")
print(f"Current directory: {os.getcwd()}")

# 尝试不同的路径组合
NRO_JSON_PATH_OPTIONS = [
    # 优先检查后端目录中的文件
    os.path.join(os.path.dirname(__file__), "Named Research Organizations.json"),  # backend目录（最可靠）
    os.path.join(os.getcwd(), "Named Research Organizations.json"),  # 当前目录
    "./Named Research Organizations.json",  # 相对于当前目录
    
    # 部署环境可能的路径
    "/app/backend/Named Research Organizations.json",
    "/app/Named Research Organizations.json",
    
    # 前端目录中的文件（作为备用）
    os.path.join(BASE_DIR, "frontend", "osintdigger", "public", "Sanction_list", "Named Research Organizations.json"),
    os.path.join(BASE_DIR, "frontend", "osintdigger", "public", "NRO_list", "Named Research Organizations.json"),
    "../frontend/osintdigger/public/Sanction_list/Named Research Organizations.json",
    "../frontend/osintdigger/public/NRO_list/Named Research Organizations.json",
    "./frontend/osintdigger/public/Sanction_list/Named Research Organizations.json",
    "./frontend/osintdigger/public/NRO_list/Named Research Organizations.json",
    os.path.join(os.getcwd(), "frontend", "osintdigger", "public", "Sanction_list", "Named Research Organizations.json"),
    os.path.join(os.getcwd(), "frontend", "osintdigger", "public", "NRO_list", "Named Research Organizations.json"),
    "/app/frontend/osintdigger/public/Sanction_list/Named Research Organizations.json",
    "/app/frontend/osintdigger/public/NRO_list/Named Research Organizations.json",
    "/app/public/Sanction_list/Named Research Organizations.json",
    "/app/public/NRO_list/Named Research Organizations.json",
    os.path.join(os.path.dirname(os.getcwd()), "frontend", "osintdigger", "public", "Sanction_list", "Named Research Organizations.json"),
    os.path.join(os.path.dirname(os.getcwd()), "frontend", "osintdigger", "public", "NRO_list", "Named Research Organizations.json")
]

# 选择第一个存在的文件路径
NRO_JSON_PATH = None
print("开始查找NRO文件路径...")
for path in NRO_JSON_PATH_OPTIONS:
    print(f"检查路径: {path}")
    if os.path.exists(path):
        NRO_JSON_PATH = path
        print(f"找到NRO文件: {NRO_JSON_PATH}")
        break

if not NRO_JSON_PATH:
    NRO_JSON_PATH = NRO_JSON_PATH_OPTIONS[0]  # 默认使用第一个路径
    print(f"警告: 未找到有效的NRO文件路径，使用默认路径: {NRO_JSON_PATH}")

# 同样处理PROMPT_PATH
PROMPT_PATH_OPTIONS = [
    # 优先检查backend目录
    os.path.join(os.getcwd(), "NRO_search.md"),  # 当前目录
    os.path.join(os.path.dirname(__file__), "NRO_search.md"),  # backend目录（最可靠）
    "./NRO_search.md",  # 相对于当前目录
    # 其他可能的路径
    os.path.join(BASE_DIR, "backend", "NRO_search.md"),
    os.path.join(BASE_DIR, "NRO_search.md"),
    "../NRO_search.md",
    # 部署环境可能的路径
    "/app/backend/NRO_search.md",
    "/app/NRO_search.md"
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

# 读取JSON文件并返回内容
def read_json_file(file_path):
    """读取JSON文件并返回内容"""
    try:
        with open(file_path, 'r', encoding='utf-8') as file:
            data = json.load(file)
            print(f"成功读取JSON文件: {file_path}, 包含{len(data)}个项目")
            return data
    except FileNotFoundError:
        print(f"文件未找到: {file_path}")
        return None
    except json.JSONDecodeError as e:
        print(f"解析JSON文件失败: {file_path}, 错误: {str(e)}")
        return None
    except Exception as e:
        print(f"读取文件时发生错误: {file_path}, 错误: {str(e)}")
        return None

# 读取prompt模板文件
def read_prompt_template(file_path):
    """读取prompt模板文件"""
    try:
        with open(file_path, 'r', encoding='utf-8') as file:
            content = file.read()
            return content
    except Exception as e:
        print(f"读取模板文件失败: {str(e)}")
        return None

def call_openrouter_api(system_prompt, user_prompt):
    """调用OpenRouter API或模拟数据生成器"""
    # 检查是否使用测试模式
    if TEST_MODE:
        print(f"测试模式: 使用模拟数据生成器处理提示: {user_prompt[:50]}...")
        return mock_call_openrouter_api(system_prompt, user_prompt)
    
    # 生产模式 - 调用真实API
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

def fixed_deepsearch_generator(institution_A, processed=None, progress=None, heartbeat_interval=5, session_id=None):
    """修复版的生成器函数，用于流式返回深度搜索结果"""
    print(f"Starting fixed_deepsearch_generator for institution_A: {institution_A}, heartbeat_interval: {heartbeat_interval}s, progress: {progress}")
    
    # 初始化心跳计时器
    last_heartbeat = time.time()
    
    # 记录开始时间和模拟超时的开始时间
    start_time = time.time()
    simulation_start_time = time.time()
    
    # 检查是否启用了超时模拟
    simulate_timeout = os.getenv("SIMULATE_TIMEOUT", "false").lower() == "true"
    simulate_timeout_seconds = int(os.getenv("SIMULATE_TIMEOUT_SECONDS", "180"))
    
    if simulate_timeout:
        print(f"超时模拟已启用，将在{simulate_timeout_seconds}秒后模拟连接超时")
    
    # 读取系统提示
    system_prompt = read_prompt_template(PROMPT_PATH)
    if not system_prompt:
        print("Warning: Could not read prompt template, using default prompt")
        system_prompt = """
You are an expert in analyzing relationships between institutions. Your task is to analyze the relationship between target institution A and risk institution B.

Please return JSON results in the following format:
[
  {
    "relationship_type": "Direct/Indirect/Significant Mention/No Evidence Found",
    "finding_summary": "Detailed relationship analysis and evidence summary"
  }
]

Relationship type description:
- Direct: Direct relationship, such as partners, subsidiaries, funding, etc.
- Indirect: Indirect relationship, such as connections established through third parties
- Significant Mention: Important mention, but the relationship is unclear
- No Evidence Found: No obvious evidence of relationship found

Please ensure that the returned result is valid JSON format.
"""
    else:
        print("Successfully loaded prompt template")
    
    # 加载NRO数据
    print(f"开始加载NRO数据，路径: {NRO_JSON_PATH}")
    nro_data = read_json_file(NRO_JSON_PATH)
    
    # 如果无法从文件加载，尝试直接从前端的公共路径加载
    if not nro_data:
        print("尝试从其他可能的路径加载NRO数据...")
        # 尝试所有可能的路径
        for path in NRO_JSON_PATH_OPTIONS:
            if path != NRO_JSON_PATH:  # 跳过已尝试的路径
                print(f"尝试路径: {path}")
                nro_data = read_json_file(path)
                if nro_data:
                    print(f"成功从备用路径加载: {path}")
                    break
    
    # 如果仍然无法加载，使用默认列表
    if not nro_data:
        print("警告: 无法加载NRO数据，使用默认列表")
        risk_list = [
            "A.A. Kharkevich Institute for Information Transmission Problems, IITP, Russian Academy of Sciences (Russia)",
            "Academy of Military Medical Sciences (People's Republic of China)",
            "Academy of Military Science (People's Republic of China)"
            # 这里只列出了几个示例，实际应该有更多
        ]
    else:
        # 先检查NRO数据的结构
        if len(nro_data) > 0:
            first_item = nro_data[0]
            print(f"NRO数据结构示例: {first_item}")
            
            # 判断机构名称字段
            if "name" in first_item:
                name_field = "name"
            elif "Name" in first_item:
                name_field = "Name"
            elif "institution" in first_item:
                name_field = "institution"
            elif "Institution" in first_item:
                name_field = "Institution"
            else:
                # 如果无法确定字段名，尝试使用第一个字段
                name_field = list(first_item.keys())[0]
                print(f"无法确定机构名称字段，使用第一个字段: {name_field}")
            
            # 提取机构名称列表
            risk_list = [item[name_field] for item in nro_data]
            print(f"成功加载NRO数据，包含{len(risk_list)}个风险机构，使用字段: {name_field}")
        else:
            # 如果数据为空，使用默认列表
            risk_list = [
                "A.A. Kharkevich Institute for Information Transmission Problems, IITP, Russian Academy of Sciences (Russia)",
                "Academy of Military Medical Sciences (People's Republic of China)",
                "Academy of Military Science (People's Republic of China)"
            ]
            print(f"警告: NRO数据为空，使用默认列表包含{len(risk_list)}个风险机构")
    
    # 初始化已处理的项目列表
    processed_items = []
    if processed:
        try:
            # 尝试解析JSON格式
            if isinstance(processed, str):
                try:
                    processed_items = json.loads(processed)
                    print(f"成功解析JSON格式的processed参数: {len(processed_items)}个项目")
                except json.JSONDecodeError:
                    # 如果不是JSON，尝试将其作为逗号分隔的字符串处理
                    processed_items = [item.strip() for item in processed.split(',') if item.strip()]
                    print(f"将processed参数当作逗号分隔的字符串处理: {len(processed_items)}个项目")
            elif isinstance(processed, list):
                processed_items = processed
                print(f"processed参数已经是列表格式: {len(processed_items)}个项目")
        except Exception as e:
            print(f"解析processed参数时出错: {str(e)}")
            processed_items = []
    
    # 如果提供了进度参数，但没有提供已处理的项目列表，则使用进度参数
    progress_value = 0
    if progress and not processed_items:
        try:
            progress_value = int(progress)
            print(f"使用前端提供的进度参数: {progress_value}")
        except (ValueError, TypeError) as e:
            print(f"解析progress参数时出错: {str(e)}")
            progress_value = 0
    
    # 过滤掉已处理的项目
    risk_list = [item for item in risk_list if item not in processed_items]
    
    # 计算总项目数和初始进度
    total_items = len(risk_list)
    initial_progress = max(len(processed_items), progress_value)
    current_progress = initial_progress
    
    print(f"开始处理{total_items}个项目，已处理{initial_progress}个项目")
    
    # 计算批次大小和总批次数 - 在所有路径中都初始化
    batch_size = 5  # 每批处理5个项目
    total_batches = (total_items + batch_size - 1) // batch_size if total_items > 0 else 0  # 向上取整
    
    # 如果没有需要处理的项目，直接返回完成消息
    if not risk_list:
        yield {
            "type": "complete",
            "message": "All items have been processed",
            "progress": current_progress,
            "total": current_progress,
            "batch": "0/0",  # 添加批次信息，避免引用错误
            "total_batches": 0
        }
        return
    
    # 发送初始化消息
    yield {
        "type": "init",
        "total": total_items + initial_progress,
        "progress": initial_progress,
        "session_id": session_id,
        "total_batches": total_batches  # 添加总批次数信息
    }
    
    # 使用之前定义的batch_size和total_batches变量
    # 已在上面初始化，这里不需要重复定义
    
    # 处理每个批次
    for batch_index in range(total_batches):
        batch_start = batch_index * batch_size
        batch_end = min(batch_start + batch_size, total_items)
        batch_items = risk_list[batch_start:batch_end]
        
        # 发送批次开始消息
        yield {
            "type": "heartbeat", 
            "timestamp": int(time.time()),
            "progress": current_progress, 
            "total": initial_progress + total_items,
            "batch": f"{batch_index+1}/{total_batches}",
            "total_batches": total_batches  # 确保包含总批次数
        }
        
        # 处理当前批次的项目
        for risk_item in batch_items:
            # 当前时间
            current_time = time.time()
            elapsed = int(current_time - start_time)
            
            # 检查是否需要模拟超时
            if simulate_timeout and (current_time - simulation_start_time) > simulate_timeout_seconds:
                print(f"模拟连接超时: 已运行{int(current_time - simulation_start_time)}秒，超过了{simulate_timeout_seconds}秒的限制")
                # 抛出异常模拟连接中断
                raise Exception("模拟连接超时，连接中断")
            
            # 检查是否需要发送心跳
            if current_time - last_heartbeat >= heartbeat_interval:
                # 发送心跳消息
                yield {
                    "type": "heartbeat",
                    "timestamp": int(current_time),
                    "progress": current_progress,
                    "total": initial_progress + total_items,
                    "elapsed": elapsed,
                    "batch": f"{batch_index+1}/{total_batches}",  # 添加批次信息
                    "total_batches": total_batches  # 确保包含总批次数
                }
                # 更新心跳时间
                last_heartbeat = current_time
            
            try:
                # 防止risk_item中包含特殊字符
                safe_risk_item = str(risk_item).replace('\\', '').replace('"', '').strip()
                safe_institution_A = str(institution_A).replace('\\', '').replace('"', '').strip()
                
                # 构建user_prompt用户提示
                user_prompt = f"""
Please analyze the relationship between {safe_institution_A} and {safe_risk_item}.
Please return results in the required JSON format.
"""
            
                # 调用LLM
                llm_result = call_openrouter_api(system_prompt, user_prompt)
                
                if llm_result:
                    # 确保结果是列表格式
                    if not isinstance(llm_result, list):
                        llm_result = [llm_result]
                    
                    # 只保留第一个对象，并确保字段完整
                    result = llm_result[0]
                    result["risk_item"] = safe_risk_item
                    result["institution_A"] = safe_institution_A
                    
                    # 发送结果
                    yield {
                        "type": "result",
                        "result": result
                    }
                    
                    # 更新进度
                    current_progress += 1
                else:
                    # 如果LLM返回为空，创建一个错误结果
                    error_result = {
                        "risk_item": safe_risk_item,
                        "institution_A": safe_institution_A,
                        "relationship_type": "Error",
                        "finding_summary": "API调用失败，未能获取结果"
                    }
                    
                    # 发送错误结果
                    yield {
                        "type": "result",
                        "result": error_result
                    }
                    
                    # 更新进度
                    current_progress += 1
            except Exception as e:
                # 处理单个项目的异常，但继续处理其他项目
                print(f"处理项目时出错: {risk_item}, 错误: {str(e)}")
                error_result = {
                    "risk_item": risk_item,
                    "institution_A": institution_A,
                    "relationship_type": "Error",
                    "finding_summary": f"处理出错: {str(e)[:100]}..."
                }
                
                # 发送错误结果
                yield {
                    "type": "result",
                    "result": error_result
                }
                
                # 更新进度
                current_progress += 1
    
    # 发送完成消息
    yield {
        "type": "complete",
        "message": "All items have been processed",
        "progress": current_progress,
        "total": initial_progress + total_items,
        "batch": f"{total_batches}/{total_batches}",  # 添加批次信息
        "total_batches": total_batches  # 确保包含总批次数
    }

@fixed_deepsearch_bp.route('/deepsearch', methods=['GET', 'OPTIONS'])
def fixed_deepsearch():
    """修复版的DeepSearch API端点"""
    # --- OPTIONS 请求处理 ---
    if request.method == 'OPTIONS':
        # 返回空响应，Flask-CORS会处理CORS头部
        print("Received OPTIONS request to /api/deepsearch, returning empty response")
        response = Response(status=204)  # No Content
        return response
    institution_A = request.args.get('institution_A', '')
    session_id = request.args.get('session_id', '')
    progress = request.args.get('progress', None)
    
    # 如果提供了会话ID，从会话存储中获取数据
    if session_id and session_id in session_data:
        session_info = session_data.get(session_id)
        institution_A = session_info.get('institution_A', institution_A)
        processed_param = session_info.get('processed', [])
        print(f"Using session data for {session_id}: institution_A={institution_A}, processed_items={len(processed_param)}")
    else:
        # 如果没有提供会话ID或会话不存在，使用URL参数
        processed_param = request.args.get('processed', '')
        print(f"No valid session found, using URL parameters")
        
        # 检查是否提供了目标机构
        if not institution_A:
            return jsonify({"error": "Missing institution_A parameter"}), 400
        
    # 如果提供了进度参数，转换为整数
    if progress is not None:
        try:
            progress = int(progress)
        except ValueError:
            print(f"Invalid progress value: {progress}, ignoring")
            progress = None

    print(f"Processing Fixed DeepSearch request: institution_A={institution_A}, session_id={session_id}, processed_param={processed}")
    processed_param = request.args.get('processed', '')
    
    # 获取心跳间隔
    heartbeat_interval = int(request.args.get('heartbeat', 5))
    
    print(f"Processing Fixed DeepSearch request: institution_A={institution_A}, session_id={session_id}, processed_param={processed_param}")

    def generate():
        # 发送连接消息
        connect_message = {"type": "connect", "message": "Connection established"}
        yield f"data: {json.dumps(connect_message, ensure_ascii=False)}\n\n"
        try:
            # 调用生成器，传递已处理的项目列表、进度参数和会话ID
            for event_data_dict in fixed_deepsearch_generator(
                institution_A=institution_A, 
                processed=processed_param, 
                progress=progress,
                heartbeat_interval=heartbeat_interval, 
                session_id=session_id
            ):
                print(f"Sending SSE event data dict: {str(event_data_dict)[:100]}...")
                json_string = json.dumps(event_data_dict, ensure_ascii=False)
                yield f"data: {json_string}\n\n"
        except Exception as e:
            # 处理生成器异常
            error_message = str(e).replace('\n', ' ').replace('"', '\\"')
            print(f"Generator exception: {error_message}")
            error_event = {"type": "error", "message": error_message}
            yield f"data: {json.dumps(error_event, ensure_ascii=False)}\n\n"

    # 创建SSE响应
    response = Response(
        stream_with_context(generate()),
        content_type='text/event-stream; charset=utf-8'
    )
    return response

# 添加会话注册接口
@fixed_deepsearch_bp.route('/register_session', methods=['POST', 'OPTIONS'])
def register_session():
    # 处理OPTIONS请求
    if request.method == 'OPTIONS':
        print("Received OPTIONS request to /api/register_session, returning empty response")
        response = Response(status=204)  # No Content
        return response
        
    # 打印请求信息，帮助调试
    print(f"Received POST request to /api/register_session")
    print(f"Request headers: {dict(request.headers)}")
    print(f"Request data: {request.data}")
    print(f"Request content type: {request.content_type}")
    print(f"Request method: {request.method}")
    
    # 获取POST请求中的数据
    data = request.get_json()
    if not data:
        return jsonify({"error": "No data provided"}), 400
        
    # 获取必要的参数 - 支持两种参数名称
    institution_A = data.get('institution_A', data.get('institutionA', ''))
    print(f"Extracted institution_A: {institution_A}")
    
    # 如果没有机构名称，返回错误
    if not institution_A:
        print("Error: Missing institution_A parameter")
        print(f"Available data keys: {data.keys()}")
        return jsonify({"error": "Missing institution_A parameter"}), 400
        
    # 获取已处理的项目列表（如果有）
    processed_items = data.get('processedItems', [])
    
    # 生成会话ID
    session_id = data.get('sessionId') or f"session_{int(time.time() * 1000)}"
    
    # 存储会话数据
    session_data[session_id] = {
        'institution_A': institution_A,
        'processed': processed_items,
        'created_at': time.time()
    }
    
    # 清理旧会话（超过30分钟的会话）
    current_time = time.time()
    expired_sessions = []
    for sid, session_info in session_data.items():
        if current_time - session_info.get('created_at', 0) > 1800:  # 30分钟 = 1800秒
            expired_sessions.append(sid)
    
    for sid in expired_sessions:
        session_data.pop(sid, None)
    
    print(f"Registered session {session_id} with institution_A={institution_A} and {len(processed_items)} processed items")
    print(f"Current active sessions: {len(session_data)}")
    
    return jsonify({"session_id": session_id, "message": "Session registered successfully"})

# 添加测试模式切换端点
@fixed_deepsearch_bp.route('/test_mode', methods=['GET', 'POST'])
def toggle_test_mode():
    global TEST_MODE
    
    if request.method == 'POST':
        try:
            # 切换测试模式
            data = request.get_json()
            if data and 'enabled' in data:
                TEST_MODE = bool(data['enabled'])
                print(f"测试模式已{'启用' if TEST_MODE else '禁用'}")
        except Exception as e:
            print(f"切换测试模式时出错: {str(e)}")
            return jsonify({"error": str(e)}), 400
    
    # 返回当前测试模式状态
    return jsonify({
        "test_mode": TEST_MODE,
        "message": f"DeepSearch is running in {'TEST' if TEST_MODE else 'PRODUCTION'} mode"
    })

# 如果直接运行此文件，启动测试服务器
if __name__ == "__main__":
    from flask import Flask
    app = Flask(__name__)
    app.register_blueprint(fixed_deepsearch_bp)
    
    @app.after_request
    def after_request(response):
        response.headers.add('Access-Control-Allow-Origin', '*')
        response.headers.add('Access-Control-Allow-Headers', 'Content-Type,Authorization')
        response.headers.add('Access-Control-Allow-Methods', 'GET,PUT,POST,DELETE,OPTIONS')
        response.headers.add('Access-Control-Allow-Credentials', 'true')
        response.headers.add('Cache-Control', 'no-cache')
        response.headers.add('X-Accel-Buffering', 'no')  # 禁用Nginx缓冲
        return response
    
    print("启动修复版DeepSearch测试服务器...")
    print(f"测试模式: {TEST_MODE}")
    print(f"模拟超时: {os.getenv('SIMULATE_TIMEOUT', 'false')}")
    print(f"超时时间: {os.getenv('SIMULATE_TIMEOUT_SECONDS', '180')}秒")
    app.run(host='0.0.0.0', port=5000, debug=True)

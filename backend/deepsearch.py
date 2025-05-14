import os
import json
import time
import requests
from flask import Blueprint, request, Response, stream_with_context, jsonify
from dotenv import load_dotenv

# 导入模拟数据生成器
from mock_data import mock_call_openrouter_api

# 加载环境变量
load_dotenv()

# 获取API密钥
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")

# 测试模式设置 - 强制关闭
# 注意：无论环境变量如何设置，我们都强制将测试模式设置为关闭状态
print("开始设置测试模式...")
print(f"环境变量中TEST_MODE的原始值: {os.getenv('TEST_MODE', 'not set')}")

# 强制关闭测试模式
TEST_MODE = False
print("测试模式已强制关闭！")

# 如果不是测试模式且没有API密钥，则报错
if not TEST_MODE and not OPENROUTER_API_KEY:
    raise ValueError("请设置OPENROUTER_API_KEY环境变量或启用测试模式")

# 打印测试模式状态
print(f"DeepSearch运行模式: {'测试模式' if TEST_MODE else '生产模式'}")

# 打印最终使用的模式
print(f"TEST_MODE = {TEST_MODE}")


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

# 创建Blueprint
deepsearch_bp = Blueprint('deepsearch', __name__, url_prefix='/api')

# 添加健康检查端点
@deepsearch_bp.route('/health', methods=['GET'])
def health_check():
    """健康检查端点，用于Railway监控"""
    return jsonify({"status": "healthy", "timestamp": int(time.time())}), 200

# 打印Blueprint信息
print(f"DeepSearch Blueprint created with URL prefix: {deepsearch_bp.url_prefix}")

def read_json_file(file_path):
    """读取JSON文件并返回内容"""
    try:
        print(f"尝试读取JSON文件: {file_path}")
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)
            print(f"成功读取JSON文件，包含{len(data)}个条目")
            # 打印前5个条目的名称，帮助调试
            for i, item in enumerate(data[:5]):
                print(f"  条目 {i+1}: {item.get('Name', 'No Name')}")
            return data
    except FileNotFoundError:
        print(f"文件不存在: {file_path}")
        return None
    except json.JSONDecodeError as e:
        print(f"JSON解析错误: {file_path}, 错误: {e}")
        return None
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
    """调用OpenRouter API或模拟数据生成器"""
    # 检查是否使用测试模式
    if TEST_MODE:
        try:
            print(f"测试模式: 使用模拟数据生成器处理提示: {user_prompt[:50]}...")
            return mock_call_openrouter_api(system_prompt, user_prompt)
        except RecursionError as e:
            print(f"RecursionError in mock_call_openrouter_api: {e}")
            # 返回一个错误消息作为结果
            return [{
                "risk_item": user_prompt.split('与')[1].split('之间')[0].strip() if '与' in user_prompt else "Unknown Risk Item",
                "institution_A": user_prompt.split('请分析')[1].split('与')[0].strip() if '请分析' in user_prompt else "Unknown Institution",
                "relationship_type": "Unknown",
                "finding_summary": "Processing error: maximum recursion depth exceeded"
            }]
        except Exception as e:
            print(f"Error in mock_call_openrouter_api: {e}")
            # 返回一个错误消息作为结果
            return [{
                "risk_item": "Error",
                "institution_A": "Error",
                "relationship_type": "Unknown",
                "finding_summary": f"Processing error: {str(e)}"
            }]
    
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

def deepsearch_generator(institution_A, heartbeat_interval=5, processed=None, progress=None, session_id=None):
    """生成器函数，用于流式返回结果 - 修复版
    
    Args:
        institution_A: 目标机构名称
        heartbeat_interval: 心跳间隔（秒），默认5秒
        processed: 已处理的项目列表或字符串，用于支持客户端重连
        progress: 当前进度，整数值
        session_id: 会话ID，用于跟踪同一次搜索的多个连接
    """
    print(f"Starting deepsearch_generator for institution_A: {institution_A}, heartbeat_interval: {heartbeat_interval}s, progress: {progress}")
    
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
    
    # 保存完整的风险项目列表，用于计算总数
    full_risk_list = risk_list.copy()
    total_all_items = len(full_risk_list)
    
    # 打印已处理项目的前几个，用于调试
    if processed_items and len(processed_items) > 0:
        print(f"已处理项目示例: {processed_items[:3]}")
    
    # 将已处理项目转换为集合，提高查找效率
    processed_set = set(processed_items)
    
    # 过滤掉已处理的项目，只保留未处理的项目
    risk_list = [item for item in full_risk_list if item not in processed_set]
    
    # 打印详细的过滤信息
    print(f"完整风险列表有{len(full_risk_list)}个项目，已处理{len(processed_set)}个项目，剩余{len(risk_list)}个项目需要处理")
    
    # 如果没有需要处理的项目，则返回空列表
    if not risk_list:
        print("所有项目已处理完毕")
    
    # 计算总项目数和初始进度
    total_items = len(risk_list)
    initial_progress = max(len(processed_items), progress_value)
    current_progress = initial_progress
    
    # 打印详细的进度信息
    print(f"完整风险列表: {total_all_items}个项目")
    print(f"已处理项目: {initial_progress}个项目")
    print(f"剩余待处理项目: {total_items}个项目")
    
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
            "total": total_all_items,  # 使用完整风险列表的总数
            "batch": "0/0",  # 添加批次信息，避免引用错误
            "total_batches": 0
        }
        return
    
    # 发送初始化消息
    yield {
        "type": "init",
        "total": total_all_items,  # 使用完整风险列表的总数
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
            "total": total_all_items,  # 使用完整风险列表的总数
            "batch": f"{batch_index+1}/{total_batches}",
            "total_batches": total_batches
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
                    "total": total_all_items,  # 使用完整风险列表的总数
                    "elapsed": elapsed,
                    "batch": f"{batch_index+1}/{total_batches}",
                    "total_batches": total_batches
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
Return the result in the required JSON format.
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
                    if "relationship_type" not in result:
                        result["relationship_type"] = "Unknown"
                
                    # 直接yield字典而不是JSON字符串
                    yield {"type": "result", "result": result}
                else:
                    # 发送错误结果
                    error_result = {
                        "risk_item": safe_risk_item,
                        "institution_A": safe_institution_A,
                        "relationship_type": "Unknown",
                        "finding_summary": "Processing failed, unable to get results"
                    }
                    yield {"type": "result", "result": error_result}
                
                # 更新进度
                current_progress += 1
                
            except Exception as e:
                # 捕获并处理所有异常
                print(f"Error processing item {risk_item}: {str(e)}")
                error_result = {
                    "risk_item": str(risk_item)[:100],  # 限制长度防止过长
                    "institution_A": str(institution_A)[:100],  # 限制长度防止过长
                    "relationship_type": "Unknown",
                    "finding_summary": f"Processing error: {str(e)[:200]}"  # 限制错误消息长度
                }
                yield {"type": "result", "result": error_result}
                
                # 即使出错也要更新进度
                current_progress += 1
            
            # 适当延迟，防止API限流
            time.sleep(1)
    
    # 所有批次处理完成后，发送完成消息
    yield {
        "type": "complete",
        "message": "All items have been processed",
        "progress": current_progress,
        "total": initial_progress + total_items,
        "elapsed": int(time.time() - start_time)
    }
    print(f"DeepSearch completed. Processed {current_progress} items in {int(time.time() - start_time)} seconds.")

# 存储会话数据的字典
session_data = {}

# 添加参数注册接口
@deepsearch_bp.route('/register_session', methods=['POST', 'OPTIONS'])
def register_session():
    # 处理OPTIONS请求（跨域预检请求）
    if request.method == 'OPTIONS':
        print("Received OPTIONS request to /api/register_session, returning empty response")
        response = make_response()
        response.headers.add('Access-Control-Allow-Methods', 'POST, OPTIONS')
        response.headers.add('Access-Control-Allow-Headers', 'Content-Type')
        return response
        
    try:
        # 获取POST请求中的数据
        print(f"Received POST request to /api/register_session")
        data = request.get_json()
        if not data:
            return jsonify({"error": "No data provided"}), 400
            
        # 获取目标机构名称
        institution_A = data.get('institution_A', '')
        if not institution_A:
            return jsonify({"error": "Missing institution_A parameter"}), 400
            
        # 获取已处理的项目列表（如果有）
        processed_items = data.get('processed', [])
        
        # 生成会话ID
        session_id = data.get('session_id', f"session_{int(time.time())}")
        
        # 存储会话数据
        session_data[session_id] = {
            'institution_A': institution_A,
            'processed': processed_items,
            'created_at': time.time()
        }
        
        # 定期清理旧会话数据（超过30分钟的会话）
        current_time = time.time()
        expired_sessions = [sid for sid, sdata in session_data.items() 
                           if current_time - sdata.get('created_at', 0) > 1800]  # 30分钟 = 1800秒
        for sid in expired_sessions:
            session_data.pop(sid, None)
            
        print(f"Registered new session: {session_id} for institution: {institution_A} with {len(processed_items)} processed items")
        
        # 返回会话ID
        return jsonify({
            "session_id": session_id,
            "message": "Session registered successfully"
        })
    except Exception as e:
        print(f"注册会话时出错: {str(e)}")
        return jsonify({"error": str(e)}), 500

# 添加测试模式切换端点
@deepsearch_bp.route('/test_mode', methods=['GET', 'POST'])
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

@deepsearch_bp.route('/deepsearch', methods=['GET', 'OPTIONS'])
def deepsearch():
    # --- OPTIONS 请求处理 ---
    if request.method == 'OPTIONS':
        # 返回空响应，Flask-CORS会处理CORS头部
        print("Received OPTIONS request to /api/deepsearch, returning empty response")
        response = Response(status=204)  # No Content
        return response

    # --- GET 请求处理 ---
    # 打印请求信息，帮助调试
    print(f"Received GET request to /api/deepsearch with args: {request.args}")

    # 获取会话ID - 这是现在的主要参数
    session_id = request.args.get('session_id', '')
    if not session_id:
        error_msg = {"error": "Missing session_id parameter"}
        print(f"Error: {error_msg}")
        return jsonify(error_msg), 400
        
    # 从会话存储中获取数据
    session_info = session_data.get(session_id)
    if not session_info:
        # 如果会话不存在，尝试使用URL参数（兼容旧版本）
        institution_A = request.args.get('institution_A', '')
        if not institution_A:
            error_msg = {"error": "Session not found and no institution_A provided"}
            print(f"Error: {error_msg}")
            return jsonify(error_msg), 400
            
        # 获取已处理的项目列表（如果有）
        processed_param = request.args.get('processed', '')
        processed_items = []
        
        if processed_param:
            try:
                # 尝试解析JSON格式
                processed_items = json.loads(processed_param)
                print(f"Successfully parsed processed items as JSON: {len(processed_items)} items")
            except json.JSONDecodeError:
                # 如果不是JSON，尝试简单的字符串分割
                processed_items = processed_param.split(',')
                print(f"Parsed processed items as comma-separated string: {len(processed_items)} items")
            except Exception as e:
                print(f"Error parsing processed items: {str(e)}")
                processed_items = []
                
        print(f"Session not found, using URL parameters: institution_A={institution_A}, processed_items={len(processed_items)}")
    else:
        # 使用会话中存储的数据
        institution_A = session_info.get('institution_A', '')
        processed_items = session_info.get('processed', [])
        print(f"Using session data: institution_A={institution_A}, processed_items={len(processed_items)}")
    
    # 获取其他参数
    heartbeat_interval = int(request.args.get('heartbeat', 5))
    print(f"Processing DeepSearch request: institution_A={institution_A}, session_id={session_id}, processed_items={len(processed_items)}, heartbeat_interval={heartbeat_interval}s")

    def generate():
        # 发送连接消息
        connect_message = {"type": "connect", "message": "Connection established"}
        yield f"data: {json.dumps(connect_message, ensure_ascii=False)}\n\n"
        try:
            # 调用生成器，传递已处理的项目列表和会话ID
            for event_data_dict in deepsearch_generator(institution_A, heartbeat_interval, processed_items, session_id):
                print(f"Sending SSE event data dict: {str(event_data_dict)[:100]}...")
                json_string = json.dumps(event_data_dict, ensure_ascii=False)
                yield f"data: {json_string}\n\n"
        except Exception as e:
            # 处理生成器异常
            error_message = str(e).replace('\n', ' ').replace('"', '\\"')
            print(f"Generator exception: {error_message}")
            error_event = {"type": "error", "message": error_message}
            yield f"data: {json.dumps(error_event, ensure_ascii=False)}\n\n"

    # --- 准备SSE相关头部 ---
    # 只保留SSE特定的头部，移除所有CORS相关头部
    response_headers = {
        # SSE Headers
        'Content-Type': 'text/event-stream; charset=utf-8',
        'Connection': 'keep-alive'
        # Cache-Control 和 X-Accel-Buffering 会由 app.py 中的 after_request 钩子添加
    }
    
    # 记录请求信息便于调试
    print(f"Processing DeepSearch request with headers: {dict(request.headers)}")
    print(f"Using SSE headers: {response_headers}")
    
    # --- 创建最终的 Response 对象 ---
    # 直接创建 Response 对象，只设置SSE相关头部
    # Flask-CORS 会自动处理CORS头部
    response = Response(
        stream_with_context(generate()),
        headers=response_headers
    )

    # 打印响应头部，用于调试
    print(f"Blueprint: Returning SSE response. Flask-CORS should handle Access-Control headers.")
    return response

    # --- 确保移除这里之后所有重复的代码块 ---
"""
OSINT 安全风险调查工具 - 路由模块

定义 Flask 应用的 API 路由，处理前端请求。
"""

from flask import request, jsonify
from config import logger
from gemini_service import investigate_risks
from response_parser import parse_gemini_response
from url_resolver import batch_resolve_urls
from datetime import datetime

def register_routes(app):
    """
    注册 API 路由。
    
    Args:
        app: Flask 应用实例
    """
    # 添加健康检查端点 - 使用不同的函数名避免冲突
    @app.route('/api/status', methods=['GET', 'OPTIONS'])
    def api_status_check():
        """
        健康检查端点，用于验证API是否可访问
        使用/api/status而非/api/health以避免与现有端点冲突
        """
        print("API status check endpoint called")
        # 记录请求头信息，用于调试
        print(f"Request headers: {dict(request.headers)}")
        
        # 返回简单的JSON响应
        response = jsonify({
            'status': 'ok',
            'message': 'API is running',
            'timestamp': datetime.now().isoformat(),
            'version': '1.0.0',
            'cors_enabled': True
        })
        
        # 添加CORS头部
        response.headers.add('Access-Control-Allow-Origin', '*')
        response.headers.add('Access-Control-Allow-Headers', '*')
        response.headers.add('Access-Control-Allow-Methods', 'GET, OPTIONS')
        
        return response
    
    @app.route('/api/check_risks', methods=['POST'])
    def check_risks():
        """
        接收前端发送的机构名称、国家和风险列表，调用Gemini API进行调查，
        并返回结构化的调查结果。
        
        请求格式:
        {
          "institution": "机构名称",
          "country": "国家",
          "risk_list": ["风险项1", "风险项2", ...]
        }
        
        返回格式:
        [
          {
            "risk_item": "风险项1",
            "institution_A": "机构名称",
            "relationship_type": "关系类型",
            "finding_summary": "调查摘要",
            "potential_intermediary_B": "潜在中间机构",
            "sources": ["来源URL1", "来源URL2", ...]
          },
          ...
        ]
        """
        try:
            # 解析请求数据
            data = request.json
            if not data:
                return jsonify({"error": "请求体为空"}), 400
            
            # 提取必要字段
            institution = data.get("institution")
            country = data.get("country")
            risk_list = data.get("risk_list", [])
            
            # 提取可选参数
            enable_grounding = data.get("enable_grounding", False)  # 默认不启用接地搜索
            raw_mode = data.get("raw", False)  # 默认不返回原始响应
            
            # 提取时间范围参数
            time_range_start = data.get("time_range_start", None)  # 开始时间，格式为 YYYY-MM
            time_range_end = data.get("time_range_end", None)  # 结束时间，格式为 YYYY-MM
            
            # 日志记录时间范围
            if time_range_start or time_range_end:
                logger.info(f"指定了时间范围: {time_range_start} 到 {time_range_end}")
            
            # 验证必要字段
            if not institution:
                return jsonify({"error": "缺少institution字段"}), 400
            if not country:
                return jsonify({"error": "缺少country字段"}), 400
            if not risk_list or not isinstance(risk_list, list):
                return jsonify({"error": "risk_list必须是非空列表"}), 400
            
            # 调用Gemini API进行调查
            logger.info(f"开始调用investigate_risks函数，参数: institution={institution}, country={country}, risk_list={risk_list}, enable_grounding={enable_grounding}, time_range_start={time_range_start}, time_range_end={time_range_end}")
            response = investigate_risks(institution, country, risk_list, enable_grounding=enable_grounding, time_range_start=time_range_start, time_range_end=time_range_end)
            logger.info(f"调用investigate_risks函数完成，响应类型: {type(response)}")
            
            # 如果调用失败，返回错误信息
            if response is None:
                logger.error("调用Gemini API失败，返回了None")
                return jsonify({
                    "error": "调用Gemini API失败，请检查API密钥是否有效"
                }), 500
            
            # 检查response是否为列表
            if not isinstance(response, list):
                logger.error(f"调用Gemini API返回了非列表类型的响应: {type(response)}")
                return jsonify({
                    "error": f"调用Gemini API返回了非列表类型的响应: {type(response)}"
                }), 500
            
            # 检查response是否为空列表
            if len(response) == 0:
                logger.error("调用Gemini API返回了空列表")
                return jsonify({
                    "error": "调用Gemini API返回了空列表"
                }), 500
            
            # 记录响应内容
            logger.info(f"调用Gemini API成功，返回了{len(response)}个结果")
            logger.info(f"第一个结果的字段: {', '.join(response[0].keys() if response and len(response) > 0 and isinstance(response[0], dict) else [])}")
            
            # 解析响应
            try:
                results = response  # 直接使用response，因为investigate_risks函数已经处理了解析
                
                # 返回结果
                logger.info(f"返回结果到前端，结果数量: {len(results)}")
                
                # 如果是raw模式，返回原始响应
                if raw_mode and results and len(results) > 0:
                    # 获取原始响应
                    raw_response = {
                        "results": results,
                        "raw_text": results[0].get("raw_text", "") if results and len(results) > 0 else "",
                        "raw_metadata": results[0].get("raw_metadata", {}) if results and len(results) > 0 else {}
                    }
                    logger.info("返回原始响应到前端")
                    return jsonify(raw_response)
                
                return jsonify(results)
            except Exception as parse_error:
                logger.error(f"解析Gemini API响应时出错: {str(parse_error)}", exc_info=True)
                return jsonify({
                    "error": f"解析Gemini API响应时出错: {str(parse_error)}"
                }), 500
        
        except Exception as e:
            logger.error(f"处理请求时出错: {str(e)}", exc_info=True)
            return jsonify({"error": f"服务器内部错误: {str(e)}"}), 500
            
    @app.route('/api/test_resolve', methods=['GET'])
    def test_resolve():
        """
        测试URL解析功能是否正常工作的简单路由
        """
        logger.info("收到 /api/test_resolve 请求")
        return jsonify({
            "status": "ok",
            "message": "URL解析测试路由正常工作"
        })
    
    @app.route('/api/resolve_urls', methods=['POST', 'OPTIONS'])
    def resolve_urls():
        """
        接收前端发送的 URL 列表，解析每个 URL 并返回解析结果。
        
        请求格式:
        {
          "urls": ["URL1", "URL2", ...],
          "timeout": 10  // 可选，每个 URL 的超时时间（秒）
        }
        
        返回格式:
        {
          "results": [
            {
              "url": "解析后的URL1",
              "status": "ok",
              "original_url": "原始URL1",
              "time_taken": 1.23
            },
            {
              "url": "原始URL2",
              "status": "error",
              "message": "错误信息",
              "original_url": "原始URL2",
              "time_taken": 0.45
            },
            ...
          ],
          "total_time": 5.67,
          "success_count": 8,
          "error_count": 2
        }
        """
        # 处理OPTIONS请求
        if request.method == 'OPTIONS':
            logger.info("OPTIONS请求处理")
            response = app.make_default_options_response()
            return response
            
        try:
            # 记录收到的请求
            logger.info(f"收到 /api/resolve_urls 请求")
            logger.info(f"请求头: {dict(request.headers)}")
            logger.info(f"请求数据: {request.data.decode('utf-8') if request.data else ''}")
            
            # 解析请求数据
            try:
                data = request.json
                logger.info(f"解析的JSON数据: {data}")
            except Exception as e:
                logger.error(f"JSON解析错误: {str(e)}", exc_info=True)
                return jsonify({"error": f"JSON解析错误: {str(e)}"}), 400
                
            if not data:
                logger.warning("请求体为空")
                return jsonify({"error": "请求体为空"}), 400
            
            # 提取 URL 列表
            urls = data.get("urls", [])
            timeout = data.get("timeout", 10)  # 默认超时时间为 10 秒
            
            # 记录提取的数据
            logger.info(f"提取的数据: urls={urls}, timeout={timeout}")
            
            # 验证 URL 列表
            if not urls or not isinstance(urls, list):
                logger.warning(f"URLs 不是有效的列表: {urls}")
                return jsonify({"error": "urls必须是非空列表"}), 400
            
            # 限制列表大小，避免过多请求
            max_urls = 50
            if len(urls) > max_urls:
                logger.warning(f"URL 数量超过限制: {len(urls)} > {max_urls}")
                return jsonify({"error": f"URL数量超过限制，最多允许{max_urls}个URL"}), 400
            
            # 验证超时时间
            if not isinstance(timeout, (int, float)) or timeout <= 0 or timeout > 30:
                logger.warning(f"超时时间无效: {timeout}")
                return jsonify({"error": "timeout必须是1-30之间的数字"}), 400
            
            # 记录开始时间
            import time
            start_time = time.time()
            
            # 调用 URL 解析函数
            logger.info(f"开始解析 {len(urls)} 个 URL，超时时间: {timeout} 秒")
            
            try:
                # 尝试解析 URL
                from url_resolver import batch_resolve_urls
                results = batch_resolve_urls(urls, max_timeout=timeout)
                
                # 记录解析结果
                logger.info(f"解析结果: {results}")
                
                # 确保每个结果都包含所需的字段
                for result in results:
                    # 确保标题和描述字段存在
                    if 'title' not in result:
                        result['title'] = ''
                    if 'description' not in result:
                        result['description'] = ''
                    
                    # 处理可能的乱码问题
                    try:
                        if result['title'] and isinstance(result['title'], str):
                            result['title'] = result['title'].encode('latin1').decode('utf-8', errors='ignore')
                        if result['description'] and isinstance(result['description'], str):
                            result['description'] = result['description'].encode('latin1').decode('utf-8', errors='ignore')
                    except Exception as e:
                        logger.warning(f"处理字符编码时出错: {str(e)}")
                        
                    # 确保状态字段存在
                    if 'status' not in result:
                        result['status'] = 'error'
                        result['message'] = '解析失败'
            except Exception as resolve_error:
                logger.error(f"URL 解析过程中出错: {str(resolve_error)}", exc_info=True)
                # 返回错误结果，但不中断请求
                results = [{
                    'url': url,
                    'status': 'error',
                    'message': f'解析过程中出错: {str(resolve_error)}',
                    'original_url': url,
                    'time_taken': 0.0
                } for url in urls]
            
            # 计算统计信息
            end_time = time.time()
            total_time = round(end_time - start_time, 2)
            success_count = sum(1 for r in results if r['status'] == 'ok')
            error_count = len(results) - success_count
            
            # 根据前端的需求准备两种响应格式
            # 1. 标准格式：包含 results 数组和统计信息
            standard_response = {
                "results": results,
                "total_time": total_time,
                "success_count": success_count,
                "error_count": error_count
            }
            
            # 2. 简化格式：直接返回结果数组（前端也支持这种格式）
            simplified_response = results
            
            # 根据请求参数决定返回哪种格式
            response_format = data.get("format", "standard")
            
            if response_format == "simplified":
                logger.info(f"返回简化响应格式: {simplified_response}")
                return jsonify(simplified_response)
            else:
                logger.info(f"返回标准响应格式: {standard_response}")
                return jsonify(standard_response)
            
        except Exception as e:
            logger.error(f"处理 URL 解析请求时出错: {str(e)}", exc_info=True)
            # 返回详细的错误信息
            return jsonify({
                "error": f"服务器内部错误: {str(e)}",
                "traceback": str(e.__traceback__)
            }), 500

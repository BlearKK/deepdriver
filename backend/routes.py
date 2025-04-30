"""
OSINT 安全风险调查工具 - 路由模块

定义 Flask 应用的 API 路由，处理前端请求。
"""

from flask import request, jsonify
from config import logger
from gemini_service import investigate_risks
from response_parser import parse_gemini_response
from url_resolver import batch_resolve_urls

def register_routes(app):
    """
    注册 API 路由。
    
    Args:
        app: Flask 应用实例
    """
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
            
            # 验证必要字段
            if not institution:
                return jsonify({"error": "缺少institution字段"}), 400
            if not country:
                return jsonify({"error": "缺少country字段"}), 400
            if not risk_list or not isinstance(risk_list, list):
                return jsonify({"error": "risk_list必须是非空列表"}), 400
            
            # 调用Gemini API进行调查
            response = investigate_risks(institution, country, risk_list)
            
            # 如果调用失败，返回错误信息
            if response is None:
                return jsonify({
                    "error": "调用Gemini API失败"
                }), 500
            
            # 解析响应
            results = parse_gemini_response(response, risk_list, institution)
            
            # 返回结果
            return jsonify(results)
        
        except Exception as e:
            logger.error(f"处理请求时出错: {str(e)}", exc_info=True)
            return jsonify({"error": f"服务器内部错误: {str(e)}"}), 500
            
    @app.route('/api/resolve_urls', methods=['POST'])
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
        try:
            # 记录收到的请求
            logger.info(f"收到 /api/resolve_urls 请求: {request.data.decode('utf-8') if request.data else ''}")
            
            # 解析请求数据
            data = request.json
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
                logger.info(f"解析结果: {results}")
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
            
            # 计算总耗时和成功/失败数量
            total_time = round(time.time() - start_time, 2)
            success_count = sum(1 for r in results if r.get('status') == 'ok')
            error_count = len(results) - success_count
            
            # 构建响应数据
            response_data = {
                "results": results,
                "total_time": total_time,
                "success_count": success_count,
                "error_count": error_count
            }
            
            logger.info(f"返回响应: 成功={success_count}, 失败={error_count}, 总耗时={total_time}")
            
            # 返回结果
            return jsonify(response_data)
            
        except Exception as e:
            logger.error(f"处理 URL 解析请求时出错: {str(e)}", exc_info=True)
            # 返回详细的错误信息
            return jsonify({
                "error": f"服务器内部错误: {str(e)}",
                "traceback": str(e.__traceback__)
            }), 500

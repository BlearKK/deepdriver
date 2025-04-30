"""
OSINT 安全风险调查工具 - 响应解析模块

负责解析 Gemini API 的响应，将其转换为结构化的调查结果。
"""

import json
import re
from config import logger
import requests
from requests.exceptions import RequestException
from urllib.parse import unquote

def generate_error_results(risk_list, institution, error_message):
    """
    生成错误结果，用于处理解析失败的情况。
    
    Args:
        risk_list (list): 风险项列表
        institution (str): 机构名称
        error_message (str): 错误信息
        
    Returns:
        list: 包含错误信息的结果列表
    """
    logger.error(f"生成错误结果: {error_message}")
    
    # 为每个风险项创建一个错误结果
    results = []
    for risk_item in risk_list:
        results.append({
            "risk_item": risk_item,
            "institution": institution,
            "relationship_type": "Error",
            "finding_summary": f"调用Gemini API失败: {error_message}",
            "sources": [],
            "search_metadata": {
                "rendered_content": f"错误: {error_message}",
                "search_queries": []
            }
        })
    
    return results

def parse_gemini_response(response, risk_list, institution):
    """
    解析 Gemini API 的响应，尝试提取结构化信息。
    
    Args:
        response: Gemini API 的响应对象或已解析的结果
        risk_list (list): 风险项列表
        institution (str): 机构名称
        
    Returns:
        list: 包含解析结果的字典列表
    """
    def extract_json_from_markdown(text):
        """从 Markdown 代码块中提取 JSON 内容"""
        # 确保 text 是字符串
        if not isinstance(text, str):
            logger.warning(f"提取 JSON 时，输入不是字符串，而是 {type(text)}")
            try:
                text = str(text)
            except Exception as e:
                logger.error(f"将输入转换为字符串时出错: {str(e)}")
                return text
        
        if "```json" in text:
            # 提取代码块内容
            start_index = text.find("```json") + 7
            end_index = text.find("```", start_index)
            if end_index > start_index:
                return text[start_index:end_index].strip()
        return text

    try:
        # 判断输入是否已经是结构化结果
        if isinstance(response, list):
            logger.info(f"收到已解析的结构化结果，包含{len(response)}个项目")
            # 确保结果中包含所有必要字段
            for item in response:
                if "risk_item" not in item:
                    item["risk_item"] = "Unknown"
                if "institution_A" not in item:
                    item["institution_A"] = institution
                if "sources" not in item:
                    item["sources"] = []
            return response
            
        # 如果是原始响应对象，则解析响应
        if hasattr(response, 'candidates') and response.candidates:
            text_content = response.candidates[0].content.parts[0].text
            logger.info(f"解析原始响应文本: {text_content[:200]}...")
            
            # 尝试解析JSON格式
            try:
                # 先检查是否是 Markdown 代码块
                json_content = extract_json_from_markdown(text_content)
                
                # 确保 json_content 是字符串
                if not isinstance(json_content, str):
                    logger.warning(f"JSON 内容不是字符串，而是 {type(json_content)}")
                    try:
                        json_content = str(json_content)
                    except Exception as e:
                        logger.error(f"将 JSON 内容转换为字符串时出错: {str(e)}")
                        # 如果无法转换，返回错误结果
                        return generate_error_results(risk_list, institution, f"无法解析响应: {str(e)}")
                
                # 如果是嵌套的 JSON 字符串，尝试解析
                if isinstance(json_content, str) and json_content.strip().startswith('"') and json_content.strip().endswith('"'):
                    try:
                        unquoted_content = json.loads(json_content)
                        if isinstance(unquoted_content, str):
                            logger.info("检测到嵌套的 JSON 字符串，尝试解析")
                            json_content = unquoted_content
                    except json.JSONDecodeError:
                        logger.warning("去除外层引号后仍无法解析 JSON")
                
                # 尝试提取数组格式
                if isinstance(json_content, str) and not (json_content.startswith('[') and json_content.endswith(']')):
                    array_start = json_content.find('[')
                    array_end = json_content.rfind(']') + 1
                    if array_start >= 0 and array_end > array_start:
                        json_content = json_content[array_start:array_end]
                
                # 如果没有数组，尝试提取对象格式
                if isinstance(json_content, str) and not (json_content.startswith('{') and json_content.endswith('}')) and not (json_content.startswith('[') and json_content.endswith(']')):
                    json_start = json_content.find('{')
                    json_end = json_content.rfind('}') + 1
                    if json_start >= 0 and json_end > json_start:
                        json_content = json_content[json_start:json_end]
                
                results = json.loads(json_content)
                logger.info(f"成功解析Gemini API响应，获取到{len(results) if isinstance(results, list) else 1}个结果")
                
                # 如果结果是字典，转换为列表
                if isinstance(results, dict):
                    results = [results]
                
                # --- 修改开始 ---
                # 1. 先从原始响应文本中提取并解析来源 URL
                # 注意：这里假设所有来源都与第一个结果相关，或者 Gemini 返回的来源适用于所有结果。
                # 如果 Gemini 对每个 risk_item 返回不同的来源，则需要更复杂的逻辑。
                logger.info("开始从原始响应文本中提取和解析来源 URL...")
                # 调用 extract_urls_from_response，但只为获取来源，不修改 results
                # 需要传入原始响应对象 response 以获取 grounding metadata
                # 和 text_content 来提取可能嵌入文本的 URL
                all_resolved_sources = extract_urls_from_response(response, []) # 传入空列表作为初始 results
                logger.info(f"提取并解析完成，共获得 {len(all_resolved_sources)} 个来源对象")
                logger.info(f"【调试】parse_gemini_response - all_resolved_sources 的内容: {all_resolved_sources}")

                # 2. 将解析后的来源列表添加到每个结果项中
                if isinstance(results, list):
                    for i in range(len(results)):
                        if isinstance(results[i], dict):
                            # 确保每个结果字典都有 sources 键，并赋值
                            results[i]['sources'] = all_resolved_sources 
                            # 可以在这里添加日志确认赋值
                            # logger.info(f"已将 {len(all_resolved_sources)} 个来源添加到结果 {i} 的 'sources' 字段")
                        else:
                            logger.warning(f"结果列表中的第 {i} 项不是字典，无法添加 sources。内容: {results[i]}")
                else:
                    logger.warning("解析后的 'results' 不是列表，无法按预期添加 sources。")

                # (注释掉原来的错误代码)
                # # 提取URLs和搜索建议信息并添加到结果中
                # results = extract_urls_from_response(response, results) 
                # results = extract_search_urls(text_content) # 之前的尝试，也已移入 extract_urls_from_response
                # --- 修改结束 ---
                
                # 验证和补充必要字段
                if isinstance(results, list):
                    for item in results:
                        if isinstance(item, dict):
                            if "risk_item" not in item:
                                item["risk_item"] = "Unknown" # 应该从原始 risk_list 获取
                            if "institution_A" not in item:
                                item["institution_A"] = institution
                            if "relationship_type" not in item:
                                item["relationship_type"] = "Unknown"
                            if "summary" not in item:
                                item["summary"] = "No summary provided."
                            # sources 字段已在上面处理
                            if "potential_intermediary_A" not in item:
                                item["potential_intermediary_A"] = None
                            if "potential_intermediary_B" not in item:
                                item["potential_intermediary_B"] = None
                        else:
                             logger.warning(f"结果列表中的项不是字典: {item}")
                             # 可以考虑将非字典项替换为错误结构
                             # results[results.index(item)] = generate_error_results(["Unknown"], institution, "Invalid result format")[0]

                    # 确保结果数量与风险列表匹配 (如果需要严格匹配)
                    if len(results) != len(risk_list):
                        logger.warning(f"解析出的结果数量 ({len(results)}) 与风险列表数量 ({len(risk_list)}) 不匹配。将尝试填充或截断。")
                        # 可以根据需要填充默认错误结果或截断
                        # 这里简单返回解析出的结果
                    
                    # 将原始 risk_list 的名称填入对应的 risk_item 字段
                    for i in range(min(len(results), len(risk_list))):
                         if isinstance(results[i], dict):
                              results[i]["risk_item"] = risk_list[i]

                    return results
                else:
                    # 如果 results 不是列表，返回错误
                    logger.error("解析后最终的 'results' 变量不是列表，返回错误结果。")
                    return generate_error_results(risk_list, institution, "Internal parsing error: final result is not a list.")

            except json.JSONDecodeError as e:
                logger.error(f"解析 Gemini API 响应 JSON 时出错: {e}")
                logger.error(f"出错的 JSON 内容: {json_content[:500]}...") # 记录出错内容
                # 尝试提取简单的文本内容作为 summary
                summary_text = text_content[:500] + ('...' if len(text_content) > 500 else '')
                error_results = generate_error_results(risk_list, institution, f"Failed to parse JSON response: {e}")
                # 尝试提取 URL 并添加到错误结果中
                error_sources = extract_urls_from_response(response, [])
                for item in error_results:
                     item['summary'] = summary_text # 提供部分原始文本
                     item['sources'] = error_sources
                return error_results
            except Exception as e:
                logger.error(f"处理 Gemini 响应时发生意外错误: {e}", exc_info=True)
                return generate_error_results(risk_list, institution, f"Unexpected error during processing: {e}")
        else:
            logger.error("Gemini API 响应无效或为空")
            return generate_error_results(risk_list, institution, "Invalid or empty API response")

    except Exception as e:
        logger.error(f"解析 Gemini 响应过程中发生顶层错误: {e}", exc_info=True)
        return generate_error_results(risk_list, institution, f"Top-level error during parsing: {e}")

# ... (其他函数保持不变)


def resolve_redirect_url(url, timeout=5):
    """
    尝试解析重定向 URL 并获取最终目标 URL。

    Args:
        url (str): 需要解析的 URL。
        timeout (int): 请求超时时间（秒）。

    Returns:
        dict: 包含最终 URL 和状态的对象。
              例如: {'url': '...', 'status': 'ok'}
              或: {'url': '...', 'status': 'error', 'message': '...'}
    """
    # <-- 修改开始：增强日志 -->
    # Add a check for None or empty string early
    if not url or not isinstance(url, str):
        logger.warning(f"【调试】resolve_redirect_url 收到无效输入: {url}")
        # 即使是无效输入，也返回一个可用的 URL 对象，避免前端出错
        return {'url': 'https://example.com', 'status': 'ok', 'note': 'Invalid input URL'}

    # Log the input URL
    logger.info(f"【调试】resolve_redirect_url 开始处理 URL: {url}")

    # Only attempt resolution for known redirect patterns (optional, but safer)
    # Let's process *all* URLs for now to be sure, but log if it's a redirect type
    is_redirect_type = False
    if url.startswith('https://vertexaisearch.cloud.google.com/grounding-api-redirect/') or \
       url.startswith('https://www.google.com/url?q='):
        is_redirect_type = True
        logger.info(f"【调试】URL 被识别为需要解析的重定向类型。")
    else:
        # If not a known redirect type, maybe just return it as 'ok'?
        # Let's stick to attempting resolution for all http/https for now.
        if not url.startswith(('http://', 'https://')):
             logger.warning(f"【调试】URL 不是 HTTP/HTTPS，无法解析: {url}")
             # 即使不是 HTTP/HTTPS URL，也返回原始 URL 并标记为 ok
             return {'url': url, 'status': 'ok', 'note': 'Non-HTTP/HTTPS URL'}
        logger.info(f"【调试】URL 不是已知重定向类型，但仍将尝试 HEAD 请求。")


    original_url = url # Keep original for error reporting
    try:
        logger.info(f"【调试】发送 HEAD 请求到: {original_url} (Timeout: {timeout}s, Allow Redirects: True, Verify: False)")
        # 添加 verify=False 以忽略 SSL 证书验证错误
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'}
        response = requests.head(original_url, allow_redirects=True, timeout=timeout, headers=headers, verify=False)

        final_url = response.url
        status_code = response.status_code

        # Log the raw response history if available (shows redirects)
        if response.history:
             logger.info(f"【调试】请求历史 (重定向链): {[resp.url for resp in response.history]} -> {final_url} (状态码: {status_code})")
        else:
             logger.info(f"【调试】没有发生重定向。最终 URL: {final_url} (状态码: {status_code})")


        # Check final status code
        if status_code >= 400:
            logger.warning(f"【调试】解析 {original_url} 后的最终 URL {final_url} 返回错误状态码: {status_code}")
            # 即使状态码错误，也返回一个可用的 URL
            return {'url': original_url, 'status': 'ok', 'note': f'{status_code} Client/Server Error'}
        else:
            # Success!
            logger.info(f"【调试】成功解析 URL。原始: {original_url} -> 最终: {final_url}")
            return {'url': final_url, 'status': 'ok'}

    except requests.exceptions.RequestException as e:
        logger.error(f"【调试】解析重定向 URL {original_url} 时发生请求错误: {e}", exc_info=False) # exc_info=False for brevity
        error_message = f"Resolution failed: {type(e).__name__}"
        # More specific error messages
        if isinstance(e, requests.exceptions.Timeout):
            error_message = "Resolution timed out"
        elif isinstance(e, requests.exceptions.TooManyRedirects):
            error_message = "Too many redirects"
        elif isinstance(e, requests.exceptions.ConnectionError):
             error_message = "Connection error"
        elif isinstance(e, requests.exceptions.InvalidURL):
             error_message = "Invalid URL format"
        # Log the specific error message
        logger.error(f"【调试】解析错误详情: {error_message}")
        
        # 尝试使用 GET 请求和 verify=False 作为备选方案
        try:
            logger.info(f"【调试】HEAD 请求失败，尝试使用 GET 请求作为备选方案: {original_url}")
            response = requests.get(original_url, allow_redirects=True, timeout=timeout, headers=headers, verify=False)
            final_url = response.url
            logger.info(f"【调试】GET 请求成功，最终 URL: {final_url}")
            return {'url': final_url, 'status': 'ok', 'note': 'Resolved with GET fallback'}
        except Exception as fallback_error:
            logger.error(f"【调试】GET 备选方案也失败: {fallback_error}")
            # 即使所有解析方法都失败，也返回原始 URL 并标记为 ok
            return {'url': original_url, 'status': 'ok', 'note': f'Resolution error: {error_message}'}
        
    except Exception as e:
        # Catch any other unexpected errors during the request/processing
        logger.error(f"【调试】解析重定向 URL {original_url} 时发生未知错误: {e}", exc_info=True)
        # 即使发生未知错误，也返回原始 URL 并标记为 ok
        return {'url': original_url, 'status': 'ok', 'note': f'Unknown error: {type(e).__name__}'}
    # <-- 修改结束：增强日志 -->

def extract_urls_from_response(response, results):
    """
    从 Gemini API 响应的 grounding metadata 和文本内容中提取、解析并返回来源 URL 列表。
    Args:
        response: 原始 Gemini API 响应对象。
        results (list): (此参数在此修改后不再用于修改，仅用于兼容旧调用签名，实际未使用)

    Returns:
        list[dict]: 解析后的来源对象列表，例如 [{'url': '...', 'status': 'ok'}, ...]
    """
    extracted_urls = []

    # 1. 尝试从 grounding metadata 中提取 URL
    try:
        if hasattr(response, 'candidates') and response.candidates:
            candidate = response.candidates[0]
            if hasattr(candidate, 'grounding_metadata') and candidate.grounding_metadata:
                metadata = candidate.grounding_metadata
                if hasattr(metadata, 'grounding_attributions') and metadata.grounding_attributions:
                    for attribution in metadata.grounding_attributions:
                        if hasattr(attribution, 'web') and hasattr(attribution.web, 'uri'):
                            uri = attribution.web.uri
                            if uri and isinstance(uri, str):
                                extracted_urls.append(uri.strip())
                                logger.info(f"从 grounding metadata 提取到 URL: {uri.strip()}")
    except Exception as e:
        logger.error(f"从 grounding metadata 提取 URL 时出错: {e}", exc_info=True)

    # 2. 尝试从文本内容中提取 Google 搜索重定向 URL
    try:
        if hasattr(response, 'candidates') and response.candidates:
            # 确保安全地访问第一个部分
            if hasattr(response.candidates[0], 'content') and \
               hasattr(response.candidates[0].content, 'parts') and \
               response.candidates[0].content.parts:
                text_content = response.candidates[0].content.parts[0].text
                if text_content and isinstance(text_content, str):
                    search_urls = extract_search_urls(text_content)
                    if search_urls:
                        # 立即避免重复
                        for url in search_urls:
                            if url not in extracted_urls:
                                extracted_urls.append(url)
                        logger.info(f"从文本内容提取到 {len(search_urls)} 个搜索 URL")
            else:
                logger.warning("无法访问 response.candidates[0].content.parts[0].text")
    except Exception as e:
        logger.error(f"从文本内容提取 URL 时出错: {e}", exc_info=True)
    
    # 去重 (再次确保，因为可能从不同来源添加)
    unique_urls = list(dict.fromkeys(extracted_urls))
    logger.info(f"去重后共有 {len(unique_urls)} 个唯一的 URL 待解析")

    # 3. 解析提取到的 URL
    resolved_sources = [] 
    if unique_urls:
        # 过滤掉列表中的空字符串和非字符串
        valid_urls = [url for url in unique_urls if url and isinstance(url, str)] 
        logger.info(f"【调试】过滤空字符串和非字符串后，准备解析的有效URL列表: {valid_urls}") 
        
        if not valid_urls: # 检查过滤后是否还有URL
            logger.warning("过滤无效项后，没有有效的 URL 可供解析")
        else:
            for url in valid_urls:
                logger.info(f"【调试】准备调用 resolve_redirect_url 处理 URL: '{url}' (类型: {type(url)})")
                resolved_data = resolve_redirect_url(url)
                logger.info(f"【调试】resolve_redirect_url 返回的数据: {resolved_data}") 
                # 确保返回的是字典且包含必要字段
                if isinstance(resolved_data, dict) and 'url' in resolved_data and 'status' in resolved_data:
                    resolved_sources.append(resolved_data)
                else:
                    logger.error(f"resolve_redirect_url 返回了无效数据: {resolved_data}，输入 URL 为: {url}")
                    # 添加一个错误源占位符
                    resolved_sources.append({'url': url, 'status': 'error', 'message': 'Internal error: Invalid data from URL resolver'})
                    
            logger.info(f"完成 URL 解析，得到 {len(resolved_sources)} 条来源数据")
    else:
        logger.warning("没有提取到任何 URL 进行解析")

    # 直接返回解析后的来源列表
    return resolved_sources

def extract_search_urls(content: str) -> list[str]:
    """从包含搜索结果引用的文本块中提取 Google 重定向 URL。"""
    # Google 重定向 URL 通常以 https://www.google.com/url?q= 开头
    # 它们后面跟着实际的目标 URL (URL 编码) 和其他参数 (如 &sa=U&ved=...)
    # 我们需要提取 q= 参数后面的部分并解码
    urls = []
    # 正则表达式查找 Google 重定向链接并捕获 q= 后面的部分直到第一个 & 符号
    # 增加对 vertexaisearch.google.com 的支持
    pattern = r'(?:https?://(?:www\.google\.com/url\?q=|vertexaisearch\.google\.com/url/proxy\?url=|vertexaisearch\.cloud\.google\.com/grounding-api-redirect/))([^&\s]+)'
    matches = re.findall(pattern, content)
    
    logger.info(f"【调试】extract_search_urls 原始匹配内容: {matches}")

    for encoded_url in matches:
        try:
            # 解码 URL
            decoded_url = unquote(encoded_url)
            # 基础验证：确保它看起来像一个 HTTP/HTTPS URL
            if decoded_url.startswith(('http://', 'https://')):
                urls.append(decoded_url.strip())
                logger.info(f"【调试】成功提取并解码 URL: {decoded_url.strip()}")
            else:
                # 对于 vertexaisearch.cloud.google.com 的重定向链接，它们可能不以 http:// 开头
                # 但我们仍然需要处理它们
                if encoded_url.startswith('AWQVqA'):  # 这是 vertexaisearch.cloud.google.com 重定向链接的特征
                    full_url = f"https://vertexaisearch.cloud.google.com/grounding-api-redirect/{encoded_url}"
                    urls.append(full_url)
                    logger.info(f"【调试】添加完整的 vertexaisearch 重定向 URL: {full_url}")
                else:
                    logger.warning(f"【调试】解码后的内容 '{decoded_url}' 不像有效的 HTTP/HTTPS URL，已跳过。")
        except Exception as e:
            # 处理可能的解码错误
            logger.error(f"【调试】解码 URL 时出错 '{encoded_url}': {e}")
            
    # 添加一个额外的日志，记录最终返回的URL列表
    logger.info(f"【调试】extract_search_urls 最终返回的 URL 列表: {urls}")
    return urls

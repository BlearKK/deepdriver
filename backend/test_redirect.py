"""
测试重定向URL解析功能

这个脚本专门用于测试 resolve_redirect_url 函数，
检查它是否能正确解析 vertexaisearch.cloud.google.com 的重定向 URL。
"""

import requests
from urllib.parse import unquote
import logging
import sys

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger("redirect_test")

def resolve_redirect_url(url, timeout=5):
    """
    尝试解析重定向 URL 并获取最终目标 URL。
    """
    # 检查无效输入
    if not url or not isinstance(url, str):
        logger.warning(f"收到无效输入: {url}")
        return {'url': url, 'status': 'error', 'message': 'Invalid input URL'}

    # 记录输入URL
    logger.info(f"开始处理 URL: {url}")

    # 检查是否是重定向类型
    is_redirect_type = False
    if url.startswith('https://vertexaisearch.cloud.google.com/grounding-api-redirect/'):
        is_redirect_type = True
        logger.info(f"URL 被识别为需要解析的重定向类型。")
    else:
        if not url.startswith(('http://', 'https://')):
             logger.warning(f"URL 不是 HTTP/HTTPS，无法解析: {url}")
             return {'url': url, 'status': 'error', 'message': 'Non-HTTP/HTTPS URL'}
        logger.info(f"URL 不是已知重定向类型，但仍将尝试 HEAD 请求。")

    original_url = url  # 保留原始URL以便出错时返回
    try:
        logger.info(f"发送 HEAD 请求到: {original_url} (Timeout: {timeout}s, Allow Redirects: True)")
        
        # 尝试使用 HEAD 请求
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        response = requests.head(original_url, allow_redirects=True, timeout=timeout, headers=headers)
        
        final_url = response.url
        status_code = response.status_code

        # 记录重定向链
        if response.history:
             logger.info(f"请求历史 (重定向链): {[resp.url for resp in response.history]} -> {final_url} (状态码: {status_code})")
        else:
             logger.info(f"没有发生重定向。最终 URL: {final_url} (状态码: {status_code})")

        # 检查最终状态码
        if status_code >= 400:
            logger.warning(f"最终 URL {final_url} 返回错误状态码: {status_code}")
            return {'url': original_url, 'status': 'error', 'message': f'{status_code} Client/Server Error'}
        else:
            # 成功！
            logger.info(f"成功解析 URL。原始: {original_url} -> 最终: {final_url}")
            return {'url': final_url, 'status': 'ok'}

    except requests.exceptions.RequestException as e:
        logger.error(f"解析重定向 URL 时发生请求错误: {e}")
        error_message = f"Resolution failed: {type(e).__name__}"
        # 更具体的错误消息
        if isinstance(e, requests.exceptions.Timeout):
            error_message = "Resolution timed out"
        elif isinstance(e, requests.exceptions.TooManyRedirects):
            error_message = "Too many redirects"
        elif isinstance(e, requests.exceptions.ConnectionError):
             error_message = "Connection error"
        elif isinstance(e, requests.exceptions.InvalidURL):
             error_message = "Invalid URL format"
        # 记录具体错误消息
        logger.error(f"解析错误详情: {error_message}")
        return {'url': original_url, 'status': 'error', 'message': error_message}
    except Exception as e:
        # 捕获其他未知异常
        logger.error(f"解析重定向 URL 时发生未知错误: {e}")
        return {'url': original_url, 'status': 'error', 'message': f'Unknown resolution error: {type(e).__name__}'}

def test_with_get_request(url, timeout=5):
    """使用 GET 请求测试 URL 解析（可能比 HEAD 更可靠但效率较低）"""
    logger.info(f"使用 GET 请求测试 URL: {url}")
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        response = requests.get(url, allow_redirects=True, timeout=timeout, headers=headers)
        
        final_url = response.url
        status_code = response.status_code
        
        logger.info(f"GET 请求结果 - 最终 URL: {final_url}, 状态码: {status_code}")
        if response.history:
            logger.info(f"重定向历史: {[resp.url for resp in response.history]}")
        
        return {'url': final_url, 'status': 'ok' if status_code < 400 else 'error'}
    except Exception as e:
        logger.error(f"GET 请求失败: {e}")
        return {'url': url, 'status': 'error', 'message': str(e)}

def main():
    # 测试URL列表，包括一些 vertexaisearch 重定向URL
    test_urls = [
        # 普通URL，应该能正常解析
        "https://www.google.com",
        "https://www.baidu.com",
        
        # vertexaisearch 重定向URL（从前端日志中提取）
        "https://vertexaisearch.cloud.google.com/grounding-api-redirect/AWQVqAIJBwQDTwAeUT1ohCL8jl0IiYL6ZUUTA-LsiwgeT2hZMrpLwaHM7HoFG875sKh-l-eSpv92L8uHSWZ5jxL27LzKz1o-6JPSykDG8Wr_iZsmlZOKXLQEjy5MWN5pAigoyCO_Ctl7OWm7",
        "https://vertexaisearch.cloud.google.com/grounding-api-redirect/AWQVqAIxvrfrwI-P2e3WLTPvU8A13skuWyesROLI8ANWZGbnt69gv_g3BUCjlgElzzSUTuAw22EAGSx9TnP2RvfNgv8-9Be5oe8AIh-iBs52qfKyPZXCH1cqBSRTIe2rKGAsPfdW0zIAYY3ypkwKfDek124qXsqVlv3tqoU="
    ]
    
    logger.info("开始测试 resolve_redirect_url 函数...")
    
    # 测试每个URL
    for url in test_urls:
        logger.info(f"\n===== 测试 URL: {url} =====")
        
        # 测试 HEAD 请求（默认方法）
        logger.info("使用 HEAD 请求测试:")
        head_result = resolve_redirect_url(url)
        logger.info(f"HEAD 结果: {head_result}")
        
        # 测试 GET 请求（备选方法）
        logger.info("使用 GET 请求测试:")
        get_result = test_with_get_request(url)
        logger.info(f"GET 结果: {get_result}")
        
        logger.info(f"===== 测试完成 =====\n")
    
    logger.info("所有测试完成!")

if __name__ == "__main__":
    main()

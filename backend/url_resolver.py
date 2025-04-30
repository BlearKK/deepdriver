"""
OSINT 安全风险调查工具 - URL 解析模块

提供 URL 解析功能，将重定向链接解析为最终目标 URL，并提取网页标题和描述。
"""

import requests
import urllib3
from config import logger
from urllib.parse import unquote
import time
from bs4 import BeautifulSoup
import re

# 禁用 SSL 警告
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

def resolve_url(url, timeout=10):
    """
    解析 URL，获取最终目标 URL，并提取网页标题和描述。
    
    Args:
        url (str): 需要解析的 URL
        timeout (int): 请求超时时间（秒）
        
    Returns:
        dict: 包含最终 URL、状态、标题和描述的对象
              例如: {'url': '...', 'status': 'ok', 'title': '...', 'description': '...'}
              或: {'url': '...', 'status': 'error', 'message': '...'}
    """
    # 记录输入 URL 和开始时间
    logger.info(f"开始解析 URL: {url}")
    start_time = time.time()
    
    # 检查无效输入
    if not url or not isinstance(url, str):
        logger.warning(f"收到无效输入: {url}")
        return {
            'url': url, 
            'status': 'error', 
            'message': '无效的 URL 输入',
            'title': '',
            'description': '无效的 URL 输入'
        }
    
    # 如果 URL 不包含协议，添加 http://
    if not url.startswith(('http://', 'https://')):
        url = 'http://' + url
        logger.info(f"添加 HTTP 协议头，新 URL: {url}")
    
    try:
        # 设置请求头，模拟浏览器行为
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1'
        }
        
        # 直接发送 GET 请求以获取页面内容
        logger.info(f"发送 GET 请求到: {url}")
        response = requests.get(
            url, 
            allow_redirects=True, 
            timeout=timeout, 
            headers=headers, 
            verify=False  # 忽略 SSL 证书验证
        )
        
        # 获取最终 URL
        final_url = response.url
        status_code = response.status_code
        
        # 记录重定向链
        if response.history:
            logger.info(f"请求历史 (重定向链): {[resp.url for resp in response.history]} -> {final_url}")
        else:
            logger.info(f"没有发生重定向。最终 URL: {final_url}")
        
        # 检查状态码
        if 200 <= status_code < 300:
            # 成功状态码
            logger.info(f"GET 请求成功，状态码: {status_code}")
            
            # 检查内容类型是否为 HTML
            content_type = response.headers.get('Content-Type', '').lower()
            
            if 'text/html' in content_type:
                # 尝试检测编码
                if response.encoding is None or response.encoding == 'ISO-8859-1':
                    # 尝试从内容中检测编码
                    response.encoding = response.apparent_encoding
                
                # 提取标题和描述
                title, description = extract_title_and_description(response.text, final_url)
            else:
                # 非 HTML 内容，使用域名作为标题
                title = get_domain_from_url(final_url)
                description = f"非 HTML 内容: {content_type}"
            
            logger.info(f"提取到网页标题: {title}")
            logger.info(f"提取到网页描述: {description[:100]}..." if len(description) > 100 else f"提取到网页描述: {description}")
            
            end_time = time.time()
            logger.info(f"成功解析 URL。原始: {url} -> 最终: {final_url}，耗时: {round(end_time - start_time, 2)}秒")
            
            return {
                'url': final_url, 
                'status': 'ok',
                'original_url': url,
                'time_taken': round(end_time - start_time, 2),
                'title': title,
                'description': description
            }
        else:
            # 错误状态码
            logger.warning(f"GET 请求失败，状态码: {status_code}")
            title = get_domain_from_url(final_url)
            description = f"HTTP 状态码: {status_code}"
            
            end_time = time.time()
            return {
                'url': final_url, 
                'status': 'error',
                'message': f'无法访问网页，状态码: {status_code}',
                'original_url': url,
                'time_taken': round(end_time - start_time, 2),
                'title': title,
                'description': description
            }
            
    except requests.exceptions.Timeout:
        end_time = time.time()
        logger.warning(f"URL 解析超时: {url}")
        return {
            'url': url,
            'status': 'error',
            'message': '请求超时',
            'original_url': url,
            'time_taken': round(end_time - start_time, 2),
            'title': get_domain_from_url(url),
            'description': '请求超时，无法获取网页内容'
        }
        
    except requests.exceptions.TooManyRedirects:
        end_time = time.time()
        logger.warning(f"URL 重定向次数过多: {url}")
        return {
            'url': url,
            'status': 'error',
            'message': '重定向次数过多',
            'original_url': url,
            'time_taken': round(end_time - start_time, 2),
            'title': get_domain_from_url(url),
            'description': '重定向次数过多，无法获取网页内容'
        }
        
    except requests.exceptions.RequestException as e:
        end_time = time.time()
        logger.warning(f"URL 解析错误: {url}, 错误: {str(e)}")
        return {
            'url': url,
            'status': 'error',
            'message': f'请求错误: {str(e)}',
            'original_url': url,
            'time_taken': round(end_time - start_time, 2),
            'title': get_domain_from_url(url),
            'description': f'请求错误: {str(e)}'
        }

def extract_title_and_description(html_content, url):
    """
    从 HTML 内容中提取网页标题和描述。
    
    Args:
        html_content (str): HTML 内容
        url (str): 网页 URL，用于备用
        
    Returns:
        tuple: (标题, 描述)
    """
    try:
        # 创建 BeautifulSoup 对象
        soup = BeautifulSoup(html_content, 'html.parser')
        
        # 提取标题
        title = ""
        if soup.title and soup.title.string:
            title = soup.title.string.strip()
        
        # 如果没有标题，尝试使用 h1
        if not title and soup.h1:
            title = soup.h1.get_text().strip()
        
        # 如果仍然没有标题，使用域名
        if not title:
            title = get_domain_from_url(url)
        
        # 提取描述
        description = ""
        
        # 首先尝试使用 meta description
        meta_desc = soup.find('meta', attrs={'name': 'description'}) or \
                   soup.find('meta', attrs={'property': 'og:description'}) or \
                   soup.find('meta', attrs={'property': 'twitter:description'})
        
        if meta_desc and meta_desc.get('content'):
            description = meta_desc['content'].strip()
        
        # 如果没有 meta description，尝试提取正文的前几个段落
        if not description:
            paragraphs = soup.find_all('p')
            content_text = ""
            for p in paragraphs[:3]:  # 只取前 3 个段落
                text = p.get_text().strip()
                if len(text) > 50:  # 只考虑足够长的段落
                    content_text += text + " "
                    if len(content_text) > 300:  # 限制描述长度
                        break
            
            if content_text:
                description = content_text.strip()
        
        # 如果仍然没有描述，尝试提取所有可见文本
        if not description:
            # 移除脚本和样式标签
            for script in soup(["script", "style"]):
                script.extract()
            
            # 获取可见文本
            text = soup.get_text()
            
            # 处理文本
            lines = (line.strip() for line in text.splitlines())
            chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
            text = ' '.join(chunk for chunk in chunks if chunk)
            
            # 限制描述长度
            if text:
                description = text[:300].strip()
        
        # 如果还是没有描述，使用默认文本
        if not description:
            description = f"没有可用的描述。请访问网页了解更多信息。"
        
        # 清理标题和描述中的特殊字符
        title = re.sub(r'[\r\n\t]+', ' ', title)
        description = re.sub(r'[\r\n\t]+', ' ', description)
        
        # 将多个空格压缩为一个
        title = re.sub(r'\s+', ' ', title)
        description = re.sub(r'\s+', ' ', description)
        
        # 限制标题和描述的长度
        title = title[:100]
        description = description[:500]
        
        return title, description
        
    except Exception as e:
        logger.error(f"提取标题和描述时出错: {e}")
        return get_domain_from_url(url), f"无法提取网页内容: {str(e)}"


def get_domain_from_url(url):
    """
    从 URL 中提取域名。
    
    Args:
        url (str): URL 字符串
        
    Returns:
        str: 域名
    """
    try:
        from urllib.parse import urlparse
        parsed_url = urlparse(url)
        domain = parsed_url.netloc
        
        # 移除 www. 前缀
        if domain.startswith('www.'):
            domain = domain[4:]
        
        return domain
    except Exception as e:
        logger.error(f"从 URL 提取域名时出错: {e}")
        # 如果无法解析，返回原始 URL
        return url


def batch_resolve_urls(urls, max_timeout=10):
    """
    批量解析 URL 列表
    
    Args:
        urls (list): URL 字符串列表
        max_timeout (int): 每个 URL 的最大超时时间（秒）
        
    Returns:
        list: 解析结果列表，每个元素是一个包含 url 和 status 的字典
    """
    if not urls or not isinstance(urls, list):
        return []
    
    results = []
    total_start_time = time.time()
    
    logger.info(f"开始批量解析 {len(urls)} 个 URL")
    
    for i, url in enumerate(urls):
        logger.info(f"解析 URL {i+1}/{len(urls)}: {url}")
        result = resolve_url(url, timeout=max_timeout)
        results.append(result)
    
    total_time = round(time.time() - total_start_time, 2)
    success_count = sum(1 for r in results if r['status'] == 'ok')
    
    logger.info(f"批量解析完成。总计: {len(results)}，成功: {success_count}，失败: {len(results) - success_count}，总耗时: {total_time}秒")
    
    return results

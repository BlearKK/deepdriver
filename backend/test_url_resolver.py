"""
URL 解析测试脚本

这个脚本用于测试 URL 解析功能，直接调用 url_resolver.py 中的函数，
绕过 Flask 路由和 HTTP 请求，以便更好地诊断问题。
"""

import sys
import json
import time
from url_resolver import resolve_url, batch_resolve_urls

# 设置控制台输出编码为UTF-8，解决中文显示问题
sys.stdout.reconfigure(encoding='utf-8')

def test_single_url(url, timeout=15):
    """测试单个 URL 解析，并显示提取的网页标题和描述"""
    print(f"\n测试解析单个 URL: {url}")
    print("-" * 80)
    
    start_time = time.time()
    result = resolve_url(url, timeout=timeout)
    end_time = time.time()
    
    print(f"解析状态: {result['status']}")
    print(f"解析耗时: {result['time_taken']:.2f}秒 (实际耗时: {round(end_time - start_time, 2)}秒)")
    
    if result['status'] == 'ok':
        print(f"原始 URL: {result['original_url']}")
        print(f"最终 URL: {result['url']}")
        print(f"\n提取的网页标题: {result['title']}")
        print(f"提取的网页描述: {result['description'][:200]}..." if len(result['description']) > 200 else f"提取的网页描述: {result['description']}")
    else:
        print(f"错误信息: {result.get('message', '未知错误')}")
        if 'title' in result:
            print(f"提取的网页标题: {result['title']}")
        if 'description' in result:
            print(f"提取的网页描述: {result['description'][:200]}..." if len(result['description']) > 200 else f"提取的网页描述: {result['description']}")
    
    return result

def test_batch_urls(urls, timeout=10):
    """测试批量 URL 解析"""
    print(f"\n测试批量解析 {len(urls)} 个 URL")
    print("-" * 50)
    
    start_time = time.time()
    results = batch_resolve_urls(urls, max_timeout=timeout)
    end_time = time.time()
    
    print(f"解析结果: {json.dumps(results, ensure_ascii=False, indent=2)}")
    print(f"总耗时: {round(end_time - start_time, 2)}秒")
    print(f"成功数量: {sum(1 for r in results if r['status'] == 'ok')}")
    print(f"失败数量: {sum(1 for r in results if r['status'] != 'ok')}")
    
    return results

if __name__ == "__main__":
    # 测试用的 URL 列表
    test_urls = [
        # 用户提到的特定 URL
        "https://vertexaisearch.cloud.google.com/grounding-api-redirect/AWQVqAJ4Rnk3tAPkQ1Fuee91opmzps4IfIYtgQoLckCRiM2N__U53cHUqWwEIvVp6tcnwsW2BC4LNtypIwzRku4FvqW0UnUgJ5-rmD61Fl0yMVEycWfgBeZIsX-BHvwmBL0xvYL7hbrQzSw=",
        "https://vertexaisearch.cloud.google.com/grounding-api-redirect/AWQVqAKRZD4bvoyAlUWlkmRDCv9AhCqx1fLEZvqrljpVHKmRokqSEqMWGLRSUVqVpK2Pn6m4YQJjyC9LWitaCBw6eiSmQfQZhvayxgMMlWL47kmP7wLg3erwU4-8ob7OvNpoCITfhQ8cOw==",
        
        # 其他测试 URL
        "https://vertexaisearch.cloud.google.com/grounding-api-redirect/AWQVqALfyFEQbzY8pooVP9MAi6PtjD01YesatPEiIJdJz98hMUaLrejkRzIgNlKQ7jhPAKKsuHrf_NBdbj5P-W53sQOO2jJwRy0NKcEnJl0XR6fPUkfiry2XCylNgSy_3NuWcERV424TQraZ4vX9XBqBy0HMklIu5ma1Sw==",
        "https://vertexaisearch.cloud.google.com/grounding-api-redirect/AWQVqAJ4Rnk3tAPkQ1Fuee91opmzps4IfIYtgQoLckCRiM2N__U53cHUqWwEIvVp6tcnwsW2BC4LNtypIwzRku4FvqW0UnUgJ5-rmD61Fl0yMVEycWfgBeZIsX-BHvwmBL0xvYL7hbrQzSw="
    ]
    
    # 1. 测试单个 URL
    print("\n===== 测试单个 URL 解析（提取网页标题和描述） =====")
    for url in test_urls:
        test_single_url(url)
    
    # 2. 测试批量 URL
    print("\n===== 测试批量 URL 解析 =====")
    test_batch_urls(test_urls)

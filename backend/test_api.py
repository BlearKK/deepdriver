"""
OSINT安全风险调查工具API测试脚本

这个脚本用于测试后端API是否正常工作，
可以发送测试请求并显示返回结果。
"""

import requests
import json
import time
import sys
import os
import urllib3

# 禁用 SSL 警告
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# 添加项目根目录到 Python 路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# 导入配置和日志模块
from config import logger
from response_parser import resolve_redirect_url

# 设置控制台输出编码为UTF-8，解决中文显示问题
sys.stdout.reconfigure(encoding='utf-8')

# API地址
API_URL = "http://localhost:5000/api/check_risks"

# 测试数据
test_data = {
    "institution": "Tsinghua University",
    "country": "China",
    "risk_list": ["Nanjing University of Aeronautics and Astronautics"],
    "enable_grounding": True,  # 启用接地搜索功能
    "time_range_start": "2010-01",  # 开始时间
    "time_range_end": "2015-12"    # 结束时间
}

def test_api(enable_grounding=True, time_range_start=None, time_range_end=None):
    """
    测试API是否正常工作
    
    Args:
        enable_grounding (bool): 是否启用接地搜索功能
        time_range_start (str): 开始时间，格式为 YYYY-MM
        time_range_end (str): 结束时间，格式为 YYYY-MM
    """
    # 更新测试数据
    test_data["enable_grounding"] = enable_grounding
    
    # 更新时间范围参数
    if time_range_start is not None:
        test_data["time_range_start"] = time_range_start
    elif "time_range_start" in test_data:
        # 如果没有提供新的时间范围参数，但测试数据中存在，则保留
        pass
        
    if time_range_end is not None:
        test_data["time_range_end"] = time_range_end
    elif "time_range_end" in test_data:
        # 如果没有提供新的时间范围参数，但测试数据中存在，则保留
        pass
    print("正在发送请求到API...")
    print(f"请求数据: {json.dumps(test_data, ensure_ascii=False, indent=2)}")
    
    try:
        # 发送POST请求
        start_time = time.time()
        response = requests.post(API_URL, json=test_data, timeout=60)  # 增加超时时间到60秒
        end_time = time.time()
        
        # 计算响应时间
        response_time = end_time - start_time
        
        # 检查响应状态
        if response.status_code == 200:
            print(f"\n[成功] API请求成功! 响应时间: {response_time:.2f}秒")
            
            # 解析JSON响应
            results = response.json()
            print(f"\n[响应数据] 共有 {len(results)} 个结果")
            
            # 显示第一个结果
            if results and len(results) > 0:
                first_result = results[0]
                print(f"\n[第一个结果]")
                print(f"风险项: {first_result.get('risk_item', 'N/A')}")
                print(f"机构A: {first_result.get('institution_A', 'N/A')}")
                print(f"关系类型: {first_result.get('relationship_type', 'N/A')}")
                
                # 输出搜索查询
                if 'search_queries' in first_result:
                    print("\n[搜索查询]")
                    for query in first_result['search_queries']:
                        print(f"- {query}")
                
                # 输出网络搜索查询
                if 'webSearchQueries' in first_result:
                    print("\n[网络搜索查询]")
                    for query in first_result['webSearchQueries']:
                        print(f"- {query}")
                print(f"\n调查摘要:\n{first_result.get('finding_summary', 'N/A')}")
                
                # 显示来源
                sources = first_result.get('sources', [])
                if sources:
                    print(f"\n来源: {len(sources)} 个")
                    for i, source in enumerate(sources):
                        print(f"  [{i+1}] {source}")
                else:
                    print("\n\u6ca1\u6709\u63d0\u4f9b\u6765\u6e90\u3002")
        else:
            print(f"\n[\u9519\u8bef] API\u8bf7\u6c42\u5931\u8d25! \u72b6\u6001\u7801: {response.status_code}")
            print(f"\u54cd\u5e94\u5185\u5bb9: {response.text}")
    
    except Exception as e:
        print(f"\n[\u9519\u8bef] \u53d1\u751f\u5f02\u5e38: {str(e)}")


def test_url_resolver():
    """
    测试 URL 解析功能，包括提取网页标题和描述
    """
    from url_resolver import resolve_url
    
    # 测试 URL
    test_urls = [
        "https://vertexaisearch.cloud.google.com/grounding-api-redirect/AWQVqAJ4Rnk3tAPkQ1Fuee91opmzps4IfIYtgQoLckCRiM2N__U53cHUqWwEIvVp6tcnwsW2BC4LNtypIwzRku4FvqW0UnUgJ5-rmD61Fl0yMVEycWfgBeZIsX-BHvwmBL0xvYL7hbrQzSw=",
        "https://www.uatair.com/en/about/cooperation.html",
        "https://www.google.com",
        "https://github.com",
        "https://example.com/nonexistent-page"
    ]
    
    print("\n===== 测试 URL 解析功能 =====\n")
    
    for i, url in enumerate(test_urls):
        print(f"\n[{i+1}/{len(test_urls)}] 测试 URL: {url}")
        
        try:
            start_time = time.time()
            result = resolve_url(url, timeout=15)  # 增加超时时间
            end_time = time.time()
            
            print(f"  状态: {result['status']}")
            print(f"  解析耗时: {result['time_taken']:.2f}秒")
            
            if result['status'] == 'ok':
                print(f"  原始 URL: {result['original_url']}")
                print(f"  最终 URL: {result['url']}")
                print(f"  标题: {result['title']}")
                print(f"  描述: {result['description'][:100]}..." if len(result['description']) > 100 else f"  描述: {result['description']}")
            else:
                print(f"  错误信息: {result.get('message', '未知错误')}")
                if 'title' in result:
                    print(f"  标题: {result['title']}")
                if 'description' in result:
                    print(f"  描述: {result['description'][:100]}..." if len(result['description']) > 100 else f"  描述: {result['description']}")
        
        except Exception as e:
            print(f"  [错误] 测试过程中出现异常: {str(e)}")
        
        print("  " + "-" * 50)

        print(f"\n[错误] 测试过程中出错: {str(e)}")

def test_url_resolution():
    """
    测试 URL 解析功能
    从 API 响应中提取 sources 字段，然后对每个 URL 调用 resolve_redirect_url 函数
    """
    print("正在测试 URL 解析功能...")
    print("1. 首先发送 API 请求获取原始 URL 列表")
    
    try:
        # 发送 POST 请求获取 API 响应
        response = requests.post(API_URL, json=test_data, timeout=120)  # 增加超时时间到120秒
        
        if response.status_code != 200:
            print(f"[错误] API 请求失败! 状态码: {response.status_code}")
            return
        
        # 解析 JSON 响应
        result = response.json()
        
        if not isinstance(result, list) or len(result) == 0:
            print("[错误] API 返回格式错误或为空列表")
            return
        
        # 提取第一个风险项的 sources 字段
        first_item = result[0]
        all_sources = first_item.get('sources', [])
        
        if not all_sources:
            print("[错误] 没有找到任何 sources")
            return
        
        print(f"\n2. 成功获取 {len(all_sources)} 个原始 URL")
        
        # 限制测试的 URL 数量，避免处理太多 URL 导致测试时间过长
        max_urls_to_test = 5  # 最多测试 5 个 URL
        sources = all_sources[:max_urls_to_test]
        
        print(f"\n为了节省时间，只测试前 {len(sources)} 个 URL (共 {len(all_sources)} 个)")
        
        # 打印原始 URL 列表
        print("\n原始 URL 列表:")
        for i, source in enumerate(sources):
            print(f"  {i+1}. {source}")
        
        print("\n3. 开始解析每个 URL...")
        
        # 创建一个新的 sources 列表，包含解析后的 URL 对象
        resolved_sources = []
        
        for i, source in enumerate(sources):
            print(f"\n解析 URL {i+1}/{len(sources)}: {source}")
            try:
                # 调用 resolve_redirect_url 函数，增加超时时间
                start_time = time.time()
                resolved_data = resolve_redirect_url(source, timeout=15)  # 增加超时时间到 15 秒
                end_time = time.time()
                
                # 计算响应时间
                response_time = end_time - start_time
                
                print(f"  - 解析结果 ({response_time:.2f}秒): {resolved_data}")
                
                # 显示解析前后的对比
                if resolved_data['status'] == 'ok' and resolved_data['url'] != source:
                    print(f"  - 原始 URL: {source}")
                    print(f"  - 解析后: {resolved_data['url']}")
                    if 'note' in resolved_data:
                        print(f"  - 备注: {resolved_data['note']}")
                
                resolved_sources.append(resolved_data)
            except Exception as e:
                print(f"  - 解析失败: {str(e)}")
                continue
                print(f"  - [错误] 解析过程中出错: {str(e)}")
                # 即使出错，也添加一个错误对象
                resolved_sources.append({'url': source, 'status': 'ok', 'note': f'解析错误: {str(e)}'})
        
        print("\n4. URL 解析完成，总结:")
        print(f"  - 总共解析了 {len(resolved_sources)} 个 URL")
        print(f"  - 成功解析: {sum(1 for s in resolved_sources if s['status'] == 'ok')} 个")
        print(f"  - 解析失败: {sum(1 for s in resolved_sources if s['status'] == 'error')} 个")
        
        # 打印解析后的 URL 列表
        print("\n解析后的 URL 列表:")
        for i, resolved_data in enumerate(resolved_sources):
            status = resolved_data['status']
            url = resolved_data['url']
            note = resolved_data.get('note', '')
            
            status_str = "✓" if status == "ok" else "✗"
            print(f"  {i+1}. [{status_str}] {url}")
            if note:
                print(f"     备注: {note}")
        
        # 创建一个完整的 sources 列表，包含所有原始 URL
        print("\n5. 我们可以修改 response_parser.py 文件，确保它返回的 sources 是对象数组而不是字符串数组:")
        print("\n代码示例:")
        print("```python")
        print("# 在 parse_gemini_response 函数中的代码示例")
        print("# 将原始字符串数组转换为对象数组")
        print("if isinstance(sources, list) and sources and isinstance(sources[0], str):")
        print("    # 如果 sources 是字符串数组，将其转换为对象数组")
        print("    object_sources = []")
        print("    for source in sources:")
        print("        # 将字符串转换为对象")
        print("        object_sources.append({'url': source, 'status': 'ok'})")
        print("    # 替换原始 sources")
        print("    sources = object_sources")
        print("```")
        
        print("\n6. 也可以使用我们之前实现的前端兼容处理方案:")
        print("```typescript")
        print("// 在 ResultCard.tsx 文件中的代码示例")
        print("// 如果 source 是字符串，转换为对象")
        print("let source = sourceItem;")
        print("if (typeof sourceItem === 'string') {")
        print("    source = { url: sourceItem, status: 'ok' };")
        print("}")
        print("```")
        
    except Exception as e:
        print(f"\n[错误] 测试过程中出错: {str(e)}")
        import traceback
        traceback.print_exc()

def test_resolve_urls_api():
    """
    测试 /api/resolve_urls 端点
    """
    try:
        # 准备测试 URL
        test_urls = [
            "https://vertexaisearch.google.com/url/proxy?url=https%3A%2F%2Fen.wikipedia.org%2Fwiki%2FNanjing_University_of_Aeronautics_and_Astronautics",
            "https://vertexaisearch.google.com/url/proxy?url=https%3A%2F%2Fwww.nuaa.edu.cn%2F",
            "https://www.google.com/url?q=https://www.example.com",
            "https://example.com"
        ]
        
        print(f"\n测试 /api/resolve_urls 端点，发送 {len(test_urls)} 个 URL")
        
        # 发送请求
        response = requests.post(
            "http://localhost:5000/api/resolve_urls",
            json={
                "urls": test_urls,
                "timeout": 10
            }
        )
        
        # 检查响应状态
        print(f"\n响应状态码: {response.status_code}")
        if response.status_code != 200:
            print(f"错误: 服务器返回状态码 {response.status_code}")
            print(f"错误信息: {response.text}")
            return
        
        # 解析响应
        result = response.json()
        print(f"\n响应数据: {json.dumps(result, indent=2, ensure_ascii=False)}")
        
        # 检查结果
        if "results" in result and isinstance(result["results"], list):
            print(f"\n成功解析 {len(result['results'])} 个 URL")
            print(f"成功数量: {result.get('success_count', 0)}")
            print(f"失败数量: {result.get('error_count', 0)}")
            print(f"总耗时: {result.get('total_time', 0)} 秒")
            
            # 显示详细结果
            for i, item in enumerate(result["results"]):
                status = item.get("status", "unknown")
                status_icon = "✅" if status == "ok" else "❌"
                original_url = item.get("original_url", "N/A")
                resolved_url = item.get("url", "N/A")
                time_taken = item.get("time_taken", 0)
                
                print(f"\n{status_icon} URL {i+1}:")
                print(f"  原始 URL: {original_url}")
                print(f"  解析后 URL: {resolved_url}")
                print(f"  状态: {status}")
                print(f"  耗时: {time_taken} 秒")
                
                if status != "ok" and "message" in item:
                    print(f"  错误信息: {item['message']}")
        else:
            print(f"错误: 响应中没有有效的 results 字段")
            
    except Exception as e:
        print(f"测试过程中出错: {str(e)}")
        import traceback
        traceback.print_exc()

def print_help():
    """
    打印帮助信息
    """
    print("使用方法: python test_api.py [选项]")
    print("选项:")
    print("  --api             测试 API 是否正常工作，启用接地搜索 (默认)")
    print("  --api-no-grounding 测试 API 是否正常工作，不启用接地搜索")
    print("  --url             测试 URL 解析功能")
    print("  --resolve         测试 /api/resolve_urls 端点")
    print("  --all             运行所有测试")
    print("  --help            显示此帮助信息")

if __name__ == "__main__":
    # 解析命令行参数
    if len(sys.argv) > 1:
        arg = sys.argv[1].lower()
        if arg == "--api":
            test_api(enable_grounding=True, time_range_start="2010-01", time_range_end="2015-12")
        elif arg == "--api-no-grounding":
            test_api(enable_grounding=False, time_range_start="2010-01", time_range_end="2015-12")
        elif arg == "--url":
            test_url_resolution()
        elif arg == "--resolve":
            test_resolve_urls_api()
        elif arg == "--all":
            test_api(enable_grounding=True, time_range_start="2010-01", time_range_end="2015-12")
            print("\n" + "-"*80 + "\n")
            test_url_resolution()
            print("\n" + "-"*80 + "\n")
            test_resolve_urls_api()
        elif arg == "--help":
            print_help()
        else:
            print(f"\n[错误] 未知参数: {arg}")
            print_help()
    else:
        # 默认运行带时间范围的API测试
        test_api(enable_grounding=True, time_range_start="2010-01", time_range_end="2015-12")

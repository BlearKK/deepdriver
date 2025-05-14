import requests
import json
from pprint import pprint

def test_cors_headers():
    """
    测试CORS头部是否正确设置，特别是检查Access-Control-Allow-Origin头部是否不含分号
    """
    # 测试URL - 使用主应用的健康检查端点，因为它应该很快响应
    url = "http://localhost:5000/health"
    
    # 设置Origin头部，模拟来自Vercel的请求
    headers = {
        "Origin": "https://deepdriverfront.vercel.app"
    }
    
    print("正在测试CORS头部...")
    
    try:
        # 发送OPTIONS请求（预检请求）
        options_response = requests.options(url, headers=headers)
        print("\n=== OPTIONS请求响应 ===")
        print(f"状态码: {options_response.status_code}")
        print("响应头部:")
        for key, value in options_response.headers.items():
            if key.lower().startswith('access-control'):
                print(f"  {key}: {value}")
                # 检查是否有分号
                if isinstance(value, str) and ';' in value:
                    print(f"  警告: '{key}'头部中包含分号!")
        
        # 发送GET请求
        get_response = requests.get(url, headers=headers)
        print("\n=== GET请求响应 ===")
        print(f"状态码: {get_response.status_code}")
        print("响应头部:")
        for key, value in get_response.headers.items():
            if key.lower().startswith('access-control'):
                print(f"  {key}: {value}")
                # 检查是否有分号
                if isinstance(value, str) and ';' in value:
                    print(f"  警告: '{key}'头部中包含分号!")
        
        # 检查Access-Control-Allow-Origin头部
        origin_header = get_response.headers.get('Access-Control-Allow-Origin')
        if origin_header:
            if ';' in origin_header:
                print("\n[X] 测试失败: Access-Control-Allow-Origin头部中包含分号")
                print(f"  值: '{origin_header}'")
            else:
                print("\n[√] 测试通过: Access-Control-Allow-Origin头部不含分号")
                print(f"  值: '{origin_header}'")
        else:
            print("\n[?] 未找到Access-Control-Allow-Origin头部")
        
    except Exception as e:
        print(f"\n[X] 测试出错: {str(e)}")
        
if __name__ == "__main__":
    test_cors_headers()

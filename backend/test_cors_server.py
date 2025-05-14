#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
CORS头部测试工具 - 服务器版本

这个脚本可以测试服务器上的CORS头部配置是否正确，特别是检查Access-Control-Allow-Origin头部是否不含分号。
使用方法：
1. 将此脚本上传到服务器
2. 运行: python test_cors_server.py
3. 脚本会自动测试所有关键API端点的CORS配置
"""

import requests
import json
import argparse
import sys
import time
from colorama import init, Fore, Style

# 初始化colorama，支持Windows终端颜色
init()

def print_header(text):
    """打印带颜色的标题"""
    print(f"\n{Fore.CYAN}{Style.BRIGHT}{text}{Style.RESET_ALL}")

def print_success(text):
    """打印成功信息"""
    print(f"{Fore.GREEN}{text}{Style.RESET_ALL}")

def print_warning(text):
    """打印警告信息"""
    print(f"{Fore.YELLOW}{text}{Style.RESET_ALL}")

def print_error(text):
    """打印错误信息"""
    print(f"{Fore.RED}{text}{Style.RESET_ALL}")

def print_info(text):
    """打印普通信息"""
    print(f"{Fore.WHITE}{text}{Style.RESET_ALL}")

def test_cors_endpoint(base_url, endpoint, origin, method="GET"):
    """
    测试特定端点的CORS头部配置
    
    Args:
        base_url: 基础URL，如 "https://api.example.com"
        endpoint: API端点，如 "/api/health"
        origin: 请求的Origin头部值，如 "https://example.com"
        method: 请求方法，默认为 "GET"
    
    Returns:
        成功返回True，失败返回False
    """
    url = f"{base_url.rstrip('/')}/{endpoint.lstrip('/')}"
    headers = {"Origin": origin}
    
    print_info(f"测试端点: {url}")
    print_info(f"请求方法: {method}")
    print_info(f"Origin: {origin}")
    
    try:
        # 首先发送OPTIONS请求（预检请求）
        if method != "OPTIONS":
            print_header("OPTIONS请求（预检请求）")
            options_response = requests.options(url, headers=headers, timeout=10)
            print_info(f"状态码: {options_response.status_code}")
            
            # 检查CORS头部
            cors_headers = {}
            for key, value in options_response.headers.items():
                if key.lower().startswith('access-control'):
                    cors_headers[key] = value
                    # 检查是否有分号
                    if isinstance(value, str) and ';' in value:
                        print_error(f"  {key}: {value} (包含分号!)")
                    else:
                        print_info(f"  {key}: {value}")
            
            if not cors_headers:
                print_warning("  未找到CORS头部")
            
            # 检查Access-Control-Allow-Origin头部
            origin_header = options_response.headers.get('Access-Control-Allow-Origin')
            if origin_header:
                if ';' in origin_header:
                    print_error(f"OPTIONS请求的Access-Control-Allow-Origin头部包含分号: '{origin_header}'")
                    return False
            else:
                print_warning("OPTIONS请求未返回Access-Control-Allow-Origin头部")
        
        # 发送实际请求
        print_header(f"{method}请求")
        if method == "GET":
            response = requests.get(url, headers=headers, timeout=10)
        elif method == "POST":
            response = requests.post(url, headers=headers, json={"test": "data"}, timeout=10)
        elif method == "OPTIONS":
            response = requests.options(url, headers=headers, timeout=10)
        else:
            print_error(f"不支持的请求方法: {method}")
            return False
        
        print_info(f"状态码: {response.status_code}")
        
        # 检查CORS头部
        cors_headers = {}
        for key, value in response.headers.items():
            if key.lower().startswith('access-control'):
                cors_headers[key] = value
                # 检查是否有分号
                if isinstance(value, str) and ';' in value:
                    print_error(f"  {key}: {value} (包含分号!)")
                else:
                    print_info(f"  {key}: {value}")
        
        if not cors_headers:
            print_warning("  未找到CORS头部")
            
        # 检查Access-Control-Allow-Origin头部
        origin_header = response.headers.get('Access-Control-Allow-Origin')
        if origin_header:
            if ';' in origin_header:
                print_error(f"{method}请求的Access-Control-Allow-Origin头部包含分号: '{origin_header}'")
                return False
            else:
                print_success(f"{method}请求的Access-Control-Allow-Origin头部正确: '{origin_header}'")
                return True
        else:
            print_warning(f"{method}请求未返回Access-Control-Allow-Origin头部")
            return False
            
    except Exception as e:
        print_error(f"测试出错: {str(e)}")
        return False

def test_all_endpoints(base_url, origin):
    """
    测试所有关键端点的CORS配置
    
    Args:
        base_url: 基础URL，如 "https://api.example.com"
        origin: 请求的Origin头部值，如 "https://example.com"
    """
    print_header("开始测试CORS头部配置")
    print_info(f"基础URL: {base_url}")
    print_info(f"Origin: {origin}")
    print_info(f"时间: {time.strftime('%Y-%m-%d %H:%M:%S')}")
    print_info("=" * 50)
    
    # 定义要测试的端点和方法
    endpoints = [
        ("/health", "GET"),
        ("/api/health", "GET"),
        ("/api/test", "GET"),
        ("/api/deepsearch", "GET"),
        ("/api/deepsearch_simple", "GET"),
        ("/api/check_risks", "POST"),
        ("/api/resolve_urls", "POST")
    ]
    
    results = {}
    
    for endpoint, method in endpoints:
        print_header(f"\n测试 {method} {endpoint}")
        result = test_cors_endpoint(base_url, endpoint, origin, method)
        results[f"{method} {endpoint}"] = result
        print_info("-" * 50)
    
    # 打印总结
    print_header("\n测试结果总结")
    success_count = sum(1 for result in results.values() if result)
    total_count = len(results)
    
    print_info(f"总计测试端点: {total_count}")
    print_info(f"成功: {success_count}")
    print_info(f"失败: {total_count - success_count}")
    
    if success_count == total_count:
        print_success("\n✅ 所有端点的CORS配置正确!")
    else:
        print_warning("\n⚠️ 部分端点的CORS配置有问题:")
        for endpoint, result in results.items():
            if not result:
                print_error(f"  - {endpoint}")

def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="测试服务器的CORS头部配置")
    parser.add_argument("--url", default="http://localhost:5000", help="服务器基础URL，默认为http://localhost:5000")
    parser.add_argument("--origin", default="https://deepdriverfront.vercel.app", help="请求的Origin头部值，默认为https://deepdriverfront.vercel.app")
    
    args = parser.parse_args()
    
    try:
        test_all_endpoints(args.url, args.origin)
    except KeyboardInterrupt:
        print_warning("\n用户中断测试")
        sys.exit(1)

if __name__ == "__main__":
    main()

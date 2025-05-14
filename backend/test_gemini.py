"""
OSINT 安全风险调查工具 - Gemini API 测试脚本

用于测试 Gemini API 集成是否正常工作
"""

import os
import time
import json
import sys
from config import logger
from gemini_client import call_gemini_api, try_backup_method

# 设置控制台输出编码为UTF-8，解决中文显示问题
sys.stdout.reconfigure(encoding='utf-8')

def test_gemini_api():
    """
    测试 Gemini API 集成
    """
    print("===== 测试 Gemini API 功能 =====")
    
    # 测试数据
    test_data = {
        "user_prompt": "请介绍一下清华大学的基本情况",
        "system_instruction": "你是一位专业的教育顾问，请提供准确、全面的信息。",
        "temperature": 0.2,
        "max_output_tokens": 8192
    }
    
    print("\n[测试数据]")
    print(json.dumps(test_data, ensure_ascii=False, indent=2))
    
    print("\n[1] 测试主要API调用方法")
    try:
        start_time = time.time()
        response = call_gemini_api(**test_data)
        end_time = time.time()
        
        if not response.error:
            print(f"\n[成功] API调用成功! 响应时间: {end_time - start_time:.2f}秒")
            print("\n[响应文本]")
            print(response.text)
            print("\n[元数据]")
            print(json.dumps(response.metadata, indent=2, ensure_ascii=False))
        else:
            print(f"\n[错误] API调用失败: {response.error}")
    
    except Exception as e:
        print(f"\n[错误] 发生异常: {str(e)}")
    
    print("\n[2] 测试备用API调用方法")
    try:
        start_time = time.time()
        response = try_backup_method(
            test_data["user_prompt"],
            Exception("模拟主方法失败")
        )
        end_time = time.time()
        
        if not response.error:
            print(f"\n[成功] 备用方法调用成功! 响应时间: {end_time - start_time:.2f}秒")
            print("\n[响应文本]")
            print(response.text)
            print("\n[元数据]")
            print(json.dumps(response.metadata, indent=2, ensure_ascii=False))
        else:
            print(f"\n[错误] 备用方法调用失败: {response.error}")
            
    except Exception as e:
        print(f"\n[错误] 备用方法发生异常: {str(e)}")

def print_help():
    """
    打印帮助信息
    """
    print("使用方法: python test_gemini.py [选项]")
    print("选项:")
    print("  --api       测试 Gemini API 调用 (默认)")
    print("  --help      显示此帮助信息")

if __name__ == "__main__":
    # 解析命令行参数
    if len(sys.argv) > 1:
        arg = sys.argv[1].lower()
        if arg == "--api":
            test_gemini_api()
        elif arg == "--help":
            print_help()
        else:
            print(f"未知选项: {arg}")
            print_help()
    else:
        # 默认运行 API 测试
        test_gemini_api()

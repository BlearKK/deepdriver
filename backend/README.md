# OSINT 安全风险调查工具后端

这是一个基于 Flask 的后端 API 服务，用于接收前端请求，调用 Google Gemini API 进行安全风险调查和机构关系分析，并返回结构化的调查结果。

## 功能介绍

本后端服务提供以下主要功能：

1. **风险调查接口** - HTTP POST 接口 `/api/check_risks`，接收机构名称、国家和风险列表，然后使用 Google Gemini API 进行调查，返回结构化的调查结果。

2. **机构关系分析** - 提供批量分析目标机构与研究组织关系的功能，支持识别直接关联、间接关联和重要提及等关系类型。

### 工作流程

1. 前端发送包含机构名称、国家和风险列表的 POST 请求
2. 后端接收请求并验证参数
3. 对每个风险项，构建提示词并调用 Gemini API 进行调查
4. 解析 Gemini API 的响应，提取关系类型、调查摘要、潜在中间机构和来源 URL
5. 将所有调查结果组织成一个 JSON 数组返回给前端

## 安装与配置

### 环境要求

- Python 3.7+
- pip 包管理器

### 安装步骤

1. 克隆或下载本项目代码
2. 安装依赖包：

```bash
pip install -r requirements.txt
```

3. 配置环境变量：

```bash
# 复制示例环境变量文件
cp .env.example .env

# 编辑.env文件，填入你的Google API密钥
# 使用记事本或其他文本编辑器打开.env文件
# 将your_google_api_key_here替换为你的实际API密钥
```

## 运行服务

```bash
python app.py
```

服务将在 http://localhost:5000 上运行，提供 `/api/check_risks` 接口。

## API 接口说明

### POST /api/check_risks

#### 请求格式

```json
{
  "institution": "机构名称",
  "country": "国家",
  "risk_list": ["风险项1", "风险项2", ...]
}
```

#### 响应格式

```json
[
  {
    "risk_item": "风险项1",
    "relationship_type": "关系类型",
    "finding_summary": "调查摘要",
    "potential_intermediary_B": "潜在中间机构",
    "sources": ["来源URL1", "来源URL2", ...]
  },
  ...
]
```

#### 错误响应

```json
{
  "error": "错误信息"
}
```

## 与前端对接

前端可以使用 fetch 或 axios 等工具向后端发送 POST 请求，例如：

```javascript
fetch('http://localhost:5000/api/check_risks', {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json',
  },
  body: JSON.stringify({
    institution: '清华大学',
    country: '中国',
    risk_list: ['涉外合作', '资金流动']
  }),
})
.then(response => response.json())
.then(data => {
  console.log('调查结果:', data);
  // 处理返回的数据，例如使用ResultCard组件展示
})
.catch(error => {
  console.error('请求出错:', error);
});
```

## 注意事项

1. 确保 `.env` 文件中包含有效的 Google API 密钥
2. 每个风险项的调查会消耗 API 配额，请合理控制请求频率
3. 服务默认在开发模式下运行，生产环境请关闭 debug 模式并配置适当的 WSGI 服务器

## 故障排除

- 如果遇到 "未找到GOOGLE_API_KEY环境变量" 错误，请检查 `.env` 文件是否正确配置
- 如果遇到 API 调用失败，请检查 API 密钥是否有效，以及是否有足够的配额
- 如果解析响应出错，可能是 Gemini API 的响应格式发生变化，请检查日志并更新解析逻辑

## 批量机构关系分析功能

### NRO搜索脚本

本项目包含一个用于批量分析目标机构与研究组织关系的脚本 `nro_search_script.py`。该脚本具有以下特点：

1. 批量调用 OpenRouter 的 perplexity/sonar-reasoning-pro 模型
2. 使用 NRO_search.md 作为系统提示词，为每个研究机构生成关系分析
3. 支持三种关系类型的识别：
   - Direct（直接关联）
   - Indirect（间接关联）
   - Significant Mention（重要提及）
4. 实现了进度条显示和实时结果输出
5. 结果以JSON格式保存，包含关系类型和详细发现摘要

### 使用方法

```bash
python nro_search_script.py --target "目标机构名称" --output "输出文件路径.json"
```

### 参数说明

- `--target`: 指定要分析的目标机构名称
- `--output`: 指定结果输出的JSON文件路径
- `--mock`: 启用模拟模式，不调用真实API（可选）

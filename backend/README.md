# OSINT 安全风险调查工具后端

这是一个基于 Flask 的后端 API 服务，用于接收前端请求，调用 Google Gemini API 进行安全风险调查，并返回结构化的调查结果。

## 功能介绍

本后端服务提供了一个 HTTP POST 接口 `/api/check_risks`，接收机构名称、国家和风险列表，然后使用 Google Gemini API 进行调查，返回结构化的调查结果。

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

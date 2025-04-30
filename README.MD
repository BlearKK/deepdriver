# RSA OSINT 助手 (MVP)

## 描述

本项目旨在构建一个开源情报 (OSINT) 搜索辅助工具，专门为在大学和研究机构工作的研究安全分析师 (RSA) 设计。其目标是通过简化基于特定关注领域搜索目标实体的潜在风险和关联的过程，来帮助 RSA 进行初步的尽职调查。

当前版本是一个最小可行产品 (MVP)，专注于验证核心的搜索和分析工作流程。

## MVP 焦点

此 MVP 的主要目标是测试以下核心功能：
1.  接收用户输入的目标实体和国家/地区。
2.  允许用户定义和管理一个简单的关注关键词/实体列表。
3.  基于用户输入，使用外部的生成式人工智能 (Gemini) 服务触发 OSINT 搜索。
4.  显示搜索结果（摘要和来源链接）。
5.  允许用户进行与搜索相关的基本笔记记录。

**MVP 限制:**
* 身份验证通过**单个、固定的用户账户**处理。没有多用户注册或管理功能。
* 关注列表管理是针对固定用户账户的手动操作。
* **不包含**针对内部观察名单（如 NRO 名单）或外部制裁名单（如 OFAC）的自动匹配功能[cite: 1, 2]。
* **不包含**引导式深入调查或复杂的报告生成等高级功能[cite: 2]。

## 技术栈

* **前端框架**: React
* **后端与数据库**: Python (Flask) + Supabase (基于 PostgreSQL)
* **样式**: Tailwind CSS
* **UI 组件**: Shadcn UI
* **编程语言**: Python/JavaScript/TypeScript

## 核心 MVP 工作流程

1.  **登录**: 使用预定义的固定用户凭据访问工具。
2.  **输入**: 输入目标实体 (A) 和国家/地区。
3.  **管理关注列表 (C)**: 手动添加/编辑/保存与搜索相关的关注关键词或实体。此列表为固定用户持久化保存。
4.  **搜索**: 使用目标实体和关注列表启动 OSINT 搜索。
5.  **审阅**: 查看外部 GenAI 服务返回的摘要和来源链接。
6.  **记录**: 添加与调查结果相关的简单笔记。

## 开始使用

### 前置条件

* Python 3.8+
* Node.js 16+
* npm 或 yarn
* Google Gemini API 密钥

### 后端设置

1. 克隆代码仓库：
   ```bash
   git clone https://github.com/你的用户名/OSINT.git
   cd OSINT
   ```

2. 创建并激活虚拟环境：
   ```bash
   # Windows
   python -m venv venv
   .\venv\Scripts\activate
   
   # MacOS/Linux
   python -m venv venv
   source venv/bin/activate
   ```

3. 安装后端依赖：
   ```bash
   cd backend
   pip install -r requirements.txt
   ```

4. 创建 `.env` 文件并添加你的 Google Gemini API 密钥：
   ```
   GOOGLE_API_KEY=your_api_key_here
   ```

5. 启动后端服务：
   ```bash
   python app.py
   ```
   后端服务将在 http://localhost:5000 运行

### 前端设置

1. 进入前端目录：
   ```bash
   cd ../frontend/osintdigger
   ```

2. 安装前端依赖：
   ```bash
   npm install
   # 或者
   yarn install
   ```

3. 启动前端开发服务器：
   ```bash
   npm run dev
   # 或者
   yarn dev
   ```
   前端应用将在 http://localhost:8080 运行

### 使用方法

1. 打开浏览器访问 http://localhost:8080
2. 输入目标机构名称、国家和关注项
3. 点击“开始调查”按钮
4. 查看系统返回的调查结果和来源链接

## 未来目标 (MVP 之后)

* 实现完整的用户认证和管理系统。
* 集成针对内部和外部观察名单/制裁名单的自动匹配功能[cite: 1, 2]。
* 开发引导式深入调查功能[cite: 2]。
* 实现强大的报告生成和导出功能[cite: 2]。
* 基于用户反馈改进 UI/UX。
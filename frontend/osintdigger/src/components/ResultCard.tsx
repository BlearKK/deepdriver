import { ExternalLink, RefreshCw } from "lucide-react";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import GoogleSearchSuggestion from "./GoogleSearchSuggestion";
import "./GoogleSearchSuggestion.css";
import { useState, useEffect } from "react";
import axios from "axios";

// 后端返回的sources是字符串数组，而不是对象数组

// 定义新的 Source 对象类型
// 将接口导出，以便其他组件可以引用
export interface Source {
  url: string;
  status: 'ok' | 'error';
  message?: string; // 错误信息，可选
  original_url?: string; // 原始 URL，解析后的 URL 会有这个字段
  time_taken?: number; // 解析耗时，秒
  isResolving?: boolean; // 是否正在解析中
  isResolved?: boolean; // 是否已经解析过
  index?: number; // URL 在数组中的索引
  title?: string; // 网页标题
  description?: string; // 网页描述
}

interface ResultCardProps {
  result: {
    risk_item: string;
    relationship_type: string;
    finding_summary: string;
    potential_intermediary_B?: string | null;
    sources?: Source[]; // <-- 修改类型为 Source 对象数组
    // 添加 Google 搜索建议相关字段 - 新格式
    search_metadata?: {
      rendered_content?: string;
      search_queries?: string[];
    };
    // 兼容旧格式
    rendered_content?: string;
    search_queries?: string[];
  };
}

const ResultCard = ({ result: initialResult }: ResultCardProps) => {
  // 使用内部状态管理 result，以便于更新 UI
  const [result, setResult] = useState(initialResult);
  // 状态变量跟踪 URL 解析状态
  const [resolveError, setResolveError] = useState<string | null>(null);
  
  // 调试日志：打印sources数量和内容
  console.log(
    `【调试】risk_item: ${result.risk_item}, sources数量:`, 
    result.sources?.length,
    "sources内容:",
    result.sources 
  );
  
  // 处理 sources 数组，确保每个元素都是对象并添加索引
  try {
    if (result.sources && Array.isArray(result.sources) && result.sources.length > 0) {
      result.sources = result.sources.map((source, index) => {
        // 如果source是null或undefined，创建一个默认对象
        if (source === null || source === undefined) {
          console.error(`【数据错误】sources[${index}]是null或undefined`);
          return {
            url: '无效URL',
            status: 'error',
            message: '无效的源数据',
            isResolving: false,
            isResolved: true,
            index: index
          };
        }
        
        if (typeof source === 'string') {
          return { 
            url: source || '无效URL', 
            status: 'ok', 
            isResolving: false,
            isResolved: false,
            index: index
          };
        }
        
        // 确保source是一个对象
        if (typeof source !== 'object') {
          console.error(`【数据错误】sources[${index}]不是字符串也不是对象:`, source);
          return {
            url: '无效URL',
            status: 'error',
            message: `无效的源数据类型: ${typeof source}`,
            isResolving: false,
            isResolved: true,
            index: index
          };
        }
        
        // 确保url字段存在
        if (!source.url) {
          console.error(`【数据错误】sources[${index}]缺少url字段:`, source);
          return {
            ...source,
            url: '无效URL',
            status: 'error',
            message: '缺少URL',
            isResolving: false,
            isResolved: true,
            index: index
          };
        }
        
        return { 
          ...source, 
          isResolving: source.isResolving || false,
          isResolved: source.isResolved || false,
          index: index
        };
      });
    } else if (result.sources && !Array.isArray(result.sources)) {
      console.error('【数据错误】sources不是数组:', result.sources);
      result.sources = [];
    }
  } catch (error) {
    console.error('【严重错误】处理sources数组时出错:', error);
    result.sources = [];
  }
  
  // 解析全部 URL 的函数
  const resolveAllUrls = async () => {
    if (!result || !result.sources || !Array.isArray(result.sources) || result.sources.length === 0) {
      console.error('【URL解析】没有可解析的 URL');
      setResolveError('没有可解析的 URL');
      return;
    }

    // 清除之前的错误信息
    setResolveError(null);

    // 按顺序解析每个 URL
    for (let i = 0; i < result.sources.length; i++) {
      const source = result.sources[i];
      if (source && source.url && !source.isResolved && !source.isResolving) {
        await resolveSingleUrl(i);
        // 添加小延迟，避免请求过快
        await new Promise(resolve => setTimeout(resolve, 300));
      }
    }
  };

  // 解析单个 URL 的函数
  const resolveSingleUrl = async (sourceIndex: number) => {
    // 检查数据有效性
    if (!result || !result.sources || !Array.isArray(result.sources) || sourceIndex >= result.sources.length) {
      console.error(`【URL解析】无效的数据或索引: ${sourceIndex}`);
      return;
    }

    // 获取要解析的源
    const sourceToResolve = result.sources[sourceIndex];
    if (!sourceToResolve || !sourceToResolve.url) {
      console.error(`【URL解析】源 ${sourceIndex} 没有有效的 URL`);
      return;
    }

    // 如果已经解析过或正在解析，则跳过
    if (sourceToResolve.isResolved || sourceToResolve.isResolving) {
      console.log(`【URL解析】跳过已解析或正在解析的 URL: ${sourceToResolve.url}`);
      return;
    }

    // 更新状态，标记为正在解析中
    setResult(prevResult => {
      const newSources = [...prevResult.sources];
      newSources[sourceIndex] = { ...sourceToResolve, isResolving: true };
      return { ...prevResult, sources: newSources };
    });

    try {
      // 使用绝对路径调用后端 API
      const apiUrl = 'http://localhost:5000/api/resolve_urls';
      console.log(`【URL解析】发送请求到 ${apiUrl}，解析单个 URL: ${sourceToResolve.url}`);
      
      // 准备请求数据
      const requestData = { urls: [sourceToResolve.url] };
      
      // 发送请求
      const response = await fetch(apiUrl, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(requestData),
        mode: 'cors' // 启用跨域请求
      });
      
      // 如果请求失败，抛出错误
      if (!response.ok) {
        const errorText = await response.text();
        throw new Error(`请求失败 (${response.status}): ${errorText || response.statusText}`);
      }
      
      // 解析响应数据
      const data = await response.json();
      console.log(`【URL解析】响应数据:`, data);
      
      // 检查响应数据格式
      if (!data.results || !Array.isArray(data.results) || data.results.length === 0) {
        throw new Error('服务器返回的数据格式不正确');
      }
      
      // 获取解析结果
      const resolvedData = data.results[0];
      
      // 更新状态，标记为已解析
      setResult(prevResult => {
        const newSources = [...prevResult.sources];
        newSources[sourceIndex] = { 
          ...sourceToResolve, 
          url: resolvedData.url,
          original_url: resolvedData.original_url,
          status: resolvedData.status,
          time_taken: resolvedData.time_taken,
          message: resolvedData.message,
          // 添加标题和描述字段
          title: resolvedData.title || null,
          description: resolvedData.description || null,
          isResolving: false,
          isResolved: true,
          index: sourceIndex
        };
        return { ...prevResult, sources: newSources };
      });
      
      // 调试日志，显示提取的标题和描述
      console.log(`【URL解析】提取的标题: ${resolvedData.title || '无'}`);
      
      console.log(`【URL解析】成功解析 URL: ${sourceToResolve.url} -> ${resolvedData.url}`);
      return true; // 返回成功状态
    } catch (error) {
      // 安全地处理错误对象
      const errorMessage = error instanceof Error ? error.message : '未知错误';
      console.error(`【URL解析】解析 URL 出错:`, errorMessage);
      
      // 更新状态，标记为解析失败
      setResult(prevResult => {
        const newSources = [...prevResult.sources];
        newSources[sourceIndex] = { 
          ...sourceToResolve, 
          status: 'error',
          message: errorMessage,
          isResolving: false,
          isResolved: true,
          index: sourceIndex
        };
        return { ...prevResult, sources: newSources };
      });
      
      // 设置错误信息，但不影响批量解析的继续
      return false; // 返回失败状态
    }
  };
  return (
    <Card className="w-full">
      <CardHeader>
        <CardTitle className="text-xl">{result.risk_item}</CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        <p className="text-sm font-medium">
          Relationship Type: {result.relationship_type}
        </p>
        
        {result.potential_intermediary_B && (
          <p className="text-sm font-medium">
            Potential Intermediary: {result.potential_intermediary_B}
          </p>
        )}

        <p className="text-sm text-muted-foreground mt-4">
          {result.finding_summary}
        </p>
        
        {/* 根据 Google 官方文档要求，添加 Google 搜索建议组件 */}
        {/* 同时支持新旧两种数据格式 */}
        <div className="mt-4 w-full flex justify-center">
          <div className="w-full max-w-full overflow-hidden">
            <GoogleSearchSuggestion 
              renderedContent={
                (result.search_metadata && result.search_metadata.rendered_content) || 
                result.rendered_content
              } 
              searchQueries={
                (result.search_metadata && result.search_metadata.search_queries) || 
                result.search_queries
              } 
            />
          </div>
        </div>

        {result.sources && result.sources.length > 0 && (
          <>
            <div className="flex justify-between items-center mt-4 mb-2">
              <h4 className="text-sm font-semibold">Sources ({result.sources.length})</h4>
              
              {/* 添加一键解析所有 URL 的按钮 */}
              <Button 
                variant="outline" 
                size="sm"
                onClick={resolveAllUrls}
                disabled={result.sources.every(s => s.isResolved || s.isResolving)}
                className="text-xs"
              >
                <RefreshCw className="h-3 w-3 mr-1" />
                解析所有 URL
              </Button>
            </div>
            
            {resolveError && (
              <div className="p-2 mb-2 text-sm bg-red-50 text-red-700 rounded border border-red-200">
                解析错误: {resolveError}
              </div>
            )}
            
            {/* 修改：使用 div 替代 ul，并移除内边距 */} 
            <div className="space-y-2 max-h-[500px] overflow-y-auto">
              {/* 修改：迭代 source 对象 */} 
              {result.sources.map((sourceItem, index) => {
                // <-- 新增：兼容处理，如果 source 是字符串，转换为对象 -->
                let source = sourceItem;
                if (typeof sourceItem === 'string') {
                  // 如果 source 是字符串，转换为对象
                  source = { url: sourceItem, status: 'ok' };
                  console.log(`【前端兼容】将字符串 source 转换为对象:`, sourceItem);
                }
                
                // 使用try-catch包裹整个URL处理逻辑
                let hostname = '';
                let displayUrl = '#'; // 默认为无效链接
                let isError = false;
                let errorMessage = ''; 
                
                try {
                  // 安全地获取URL
                  if (source && typeof source === 'object') {
                    // 检查URL是否有效
                    if (typeof source.url === 'string' && source.url) {
                      displayUrl = source.url;
                      isError = source.status === 'error';
                      errorMessage = source.message || 'Resolution failed';
                      
                      // 尝试解析URL
                      try {
                        const parsedUrl = new URL(source.url);
                        hostname = parsedUrl.hostname.replace(/^www\./, '');
                      } catch (e) {
                        console.error(`【前端解析】URL解析失败: ${source.url}`, e);
                        hostname = "Parsing Error";
                        isError = true;
                        errorMessage = `URL格式无效: ${e.message}`;
                        displayUrl = '#';
                      }
                    } else {
                      console.error(`【前端校验】无效的URL:`, source.url);
                      hostname = "Invalid URL";
                      isError = true;
                      errorMessage = "无效的URL格式";
                    }
                  } else {
                    console.error(`【前端校验】无效的source对象:`, source);
                    hostname = "Invalid Data";
                    isError = true;
                    errorMessage = "无效的数据格式";
                  }

                } catch (error) {
                  console.error('【严重错误】处理URL时发生异常:', error);
                  // 出现异常时返回错误卡片
                  return (
                    <div key={index} className="p-3 border rounded-lg shadow-sm bg-red-50 dark:bg-red-900 border-red-200 dark:border-red-700">
                      <p className="text-sm font-medium truncate text-red-700 dark:text-red-300">
                        {index + 1}. 数据处理错误
                      </p>
                      <p className="text-xs text-red-600 dark:text-red-400 break-all">
                        Error: 渲染此项时发生错误，请刷新页面重试
                      </p>
                    </div>
                  );
                }
                
                // 修改：替换 li 为 div 卡片结构
                return (
                  // 修改：根据错误状态添加不同样式
                  <div 
                    key={index} 
                    className={`p-3 border rounded-lg shadow-sm ${isError ? 
                      // 检查是否是 403 Forbidden 错误
                      (errorMessage && (errorMessage.includes('403') || errorMessage.includes('Forbidden'))) ? 
                        // 403 错误显示为黄色警告
                        'bg-yellow-50 dark:bg-yellow-900 border-yellow-200 dark:border-yellow-700' : 
                        // 其他错误显示为红色
                        'bg-red-50 dark:bg-red-900 border-red-200 dark:border-red-700' 
                      : 'bg-gray-50 dark:bg-gray-800'}`}
                  >
                    {/* 显示网页标题和解析状态 */} 
                    <div className="flex items-center justify-between mb-1">
                      <p 
                        className={`text-sm font-medium truncate ${isError ? 
                          // 检查是否是 403 Forbidden 错误
                          (errorMessage && (errorMessage.includes('403') || errorMessage.includes('Forbidden'))) ? 
                            // 403 错误显示为黄色警告
                            'text-yellow-700 dark:text-yellow-300' : 
                            // 其他错误显示为红色
                            'text-red-700 dark:text-red-300' 
                          : 'text-gray-800 dark:text-gray-200'}`}
                        title={source && source.title ? source.title : hostname}
                      >
                        {index + 1}. {source && source.title ? source.title : hostname} 
                      </p>
                      
                      {/* 显示解析状态或解析按钮 */}
                      <div className="flex items-center gap-2">
                        {/* 显示解析耗时 */}
                        {source && source.time_taken !== undefined && !source.isResolving && (
                          <span className="text-xs text-gray-500">
                            {typeof source.time_taken === 'number' ? source.time_taken.toFixed(2) : '0.00'}s
                          </span>
                        )}
                        
                        {source && source.isResolving ? (
                          <span className="text-xs bg-blue-100 text-blue-700 px-2 py-0.5 rounded-full flex items-center">
                            <RefreshCw className="h-3 w-3 mr-1 animate-spin" />
                            正在解析
                          </span>
                        ) : source && source.isResolved ? (
                          <span className="text-xs bg-green-100 text-green-700 px-2 py-0.5 rounded-full">
                            已解析
                          </span>
                        ) : (
                          <Button 
                            variant="outline" 
                            size="sm"
                            className="text-xs h-6 px-2 py-0"
                            onClick={() => resolveSingleUrl(source && source.index !== undefined ? source.index : index)}
                          >
                            <RefreshCw className="h-3 w-3 mr-1" />
                            解析
                          </Button>
                        )}
                      </div>
                    </div>
                    
                    {/* 根据错误状态显示链接或错误信息 */}
                    {isError ? (
                      // 检查是否是 403 Forbidden 错误
                      errorMessage && (errorMessage.includes('403') || errorMessage.includes('Forbidden')) ? (
                        <p className="text-xs text-yellow-600 dark:text-yellow-400 break-all">
                          提示: 该网页可能需要手动访问。请点击下方链接直接在浏览器中打开: <a href={displayUrl !== '#' ? displayUrl : undefined} target="_blank" rel="noopener noreferrer" className="underline hover:text-yellow-800">{displayUrl !== '#' ? displayUrl : '无效URL'}</a>
                        </p>
                      ) : (
                        <p className="text-xs text-red-600 dark:text-red-400 break-all">
                          Error: {errorMessage} {displayUrl !== '#' ? `(URL: ${displayUrl})` : ''}
                        </p>
                      )
                    
                    ) : (
                      <div className="space-y-2">
                        {/* 显示网页描述 */}
                        {source && source.description && (
                          <div className="text-xs text-gray-700 dark:text-gray-300 line-clamp-3">
                            {typeof source.description === 'string' ? source.description : '无描述'}
                          </div>
                        )}
                        
                        <div className="space-y-1">
                          {/* 显示原始 URL，如果存在 */}
                          {source && source.original_url && source.original_url !== source.url && (
                            <div className="text-xs text-gray-500 break-all">
                              原始 URL: {typeof source.original_url === 'string' ? source.original_url : '无效URL'}
                            </div>
                          )}
                          
                          {/* 显示解析后的 URL */}
                          <a
                            href={displayUrl !== '#' ? displayUrl : undefined}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="text-xs text-blue-600 dark:text-blue-400 hover:text-blue-800 dark:hover:text-blue-300 hover:underline inline-flex items-center gap-1 break-all"
                          >
                            {displayUrl !== '#' ? displayUrl : '无效URL'} {/* 显示最终解析的 URL 文本 */}
                            <ExternalLink className="h-3 w-3 flex-shrink-0" />
                          </a>
                        </div>
                      </div>
                    )}
                  </div>
                );
              })}
            </div>
          </>
        )}
      </CardContent>
    </Card>
  );
};

export default ResultCard;

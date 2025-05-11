import React, { useState, useCallback } from 'react';
import { Source } from '@/types';
import { Button } from '@/components/ui/button';
import { ChevronDown, ChevronUp, RefreshCw } from 'lucide-react';
import SourceItem from './SourceItem';
import axios from 'axios';

interface SourceListProps {
  sources: Source[] | undefined;
  riskItem: string; // Pass riskItem for context in potential future updates or logging
}

const SourceList: React.FC<SourceListProps> = ({ sources, riskItem }) => {
  const [isExpanded, setIsExpanded] = useState(false);
  const [resolvingUrls, setResolvingUrls] = useState<Set<string>>(new Set());
  const [resolveErrors, setResolveErrors] = useState<Record<string, string>>({});
  // Store updated sources internally to reflect resolved titles
  const [internalSources, setInternalSources] = useState<Source[] | undefined>(sources);
  // 添加一个状态来跟踪批量解析是否正在进行
  const [isBatchResolving, setIsBatchResolving] = useState(false);

  // Update internalSources if the prop changes
  React.useEffect(() => {
    setInternalSources(sources);
  }, [sources]);

  // 解析URL的通用函数 - 获取正确的API URL
  const getApiUrl = useCallback(() => {
    // 使用环境变量获取API基础URL
    let apiBaseUrl = import.meta.env.VITE_API_BASE_URL || 'http://localhost:5000';
    
    // 确保apiBaseUrl是一个绝对URL
    if (apiBaseUrl && !apiBaseUrl.startsWith('http')) {
      apiBaseUrl = `https://${apiBaseUrl}`;
    }
    
    // 去除可能的尾部斜杠
    if (apiBaseUrl.endsWith('/')) {
      apiBaseUrl = apiBaseUrl.slice(0, -1);
    }
    
    console.log(`使用API基础URL: ${apiBaseUrl}`);
    return `${apiBaseUrl}/api/resolve_urls`;
  }, []);
  
  // 解析单个 URL 的函数
  const handleResolveUrl = useCallback(async (sourceToResolve: Source) => {
    // 如果已经在解析中，则跳过
    if (resolvingUrls.has(sourceToResolve.url)) {
      return;
    }
    
    // 添加到正在解析的集合中
    setResolvingUrls(prev => new Set([...prev, sourceToResolve.url]));

    try {
      // 获取API URL
      const apiUrl = getApiUrl();
      
      console.log(`【URL解析】发送请求到 ${apiUrl}，解析单个 URL: ${sourceToResolve.url}`);
      
      // 获取基础URL和测试URL
      const baseUrl = apiUrl.substring(0, apiUrl.lastIndexOf('/api/'));
      const testUrl = `${baseUrl}/api/test_resolve`;
      
      // 先测试连接是否正常
      try {
        console.log(`测试连接到后端: ${testUrl}`);
        const testResponse = await axios.get(testUrl);
        console.log(`测试连接响应:`, testResponse.data);
      } catch (testError) {
        console.error(`测试连接失败:`, testError);
        // 将错误添加到解析错误中
        setResolveErrors(prev => ({
          ...prev,
          [sourceToResolve.url]: `连接后端失败: ${testError.message || '未知错误'}`
        }));
        // 从正在解析的集合中移除
        setResolvingUrls(prev => {
          const newSet = new Set(prev);
          newSet.delete(sourceToResolve.url);
          return newSet;
        });
        return; // 如果测试连接失败，则不继续解析URL
      }
      
      // 设置请求头
      const headers = {
        'Content-Type': 'application/json',
        'Accept': 'application/json'
      };
      
      console.log(`发送POST请求到 ${apiUrl}`, {
        urls: [sourceToResolve.url],
        headers
      });
      
      // 添加更多请求配置
      console.log(`发送的请求数据:`, {
        urls: [sourceToResolve.url],
        timeout: 10,
        format: "simplified" // 请求简化响应格式
      });
      
      const response = await axios.post(apiUrl, {
        urls: [sourceToResolve.url],
        timeout: 10,
        format: "simplified" // 请求简化响应格式，直接返回结果数组
      }, { 
        headers,
        timeout: 15000, // 请求超时时间设置为15秒
        validateStatus: function (status) {
          // 允许所有状态码，以便我们可以手动处理错误
          return true;
        }
      });
      
      // 检查响应状态
      if (response.status !== 200) {
        console.error(`请求失败，状态码: ${response.status}`, response.data);
        throw new Error(`请求失败，状态码: ${response.status}`);
      }
      
      // 详细记录响应数据
      console.log(`响应状态码: ${response.status}`);
      console.log(`响应头信息:`, response.headers);
      console.log(`响应数据类型:`, typeof response.data);
      if (Array.isArray(response.data)) {
        console.log(`响应数据是数组，长度: ${response.data.length}`);
      }
      
      // 调试输出后端响应
      console.log('【URL解析】后端响应数据:', response.data);
      
      // 提取的信息
      let resolvedInfo = {
        title: null as string | null,
        description: null as string | null,
        status: 'ok' as 'ok' | 'error' | 'warning',
        statusCode: null as number | null,
        message: null as string | null
      };
      
      // 处理不同的响应格式
      try {
        if (response.data) {
          // 处理简化格式（数组）
          if (Array.isArray(response.data) && response.data.length > 0) {
            // 找到对应当前 URL 的结果
            const result = response.data.find(r => 
              (r.original_url === sourceToResolve.url) || 
              (r.url === sourceToResolve.url) ||
              (sourceToResolve.url.includes(r.url)) ||
              (r.url.includes(sourceToResolve.url))
            ) || response.data[0]; // 如果找不到对应的，就使用第一个
            
            console.log(`找到的结果:`, result);
            
            resolvedInfo = {
              title: result.title || null,
              description: result.description || null,
              status: result.status || 'ok',
              statusCode: result.status_code || null,
              message: result.message || null
            };
            console.log(`【URL解析】从数组响应中提取信息:`, resolvedInfo);
          } 
          // 处理标准格式（对象包含 results 数组）
          else if (response.data.results && Array.isArray(response.data.results)) {
            // 找到对应当前 URL 的结果
            const result = response.data.results.find(r => 
              (r.original_url === sourceToResolve.url) || 
              (r.url === sourceToResolve.url) ||
              (sourceToResolve.url.includes(r.url)) ||
              (r.url.includes(sourceToResolve.url))
            ) || response.data.results[0]; // 如果找不到对应的，就使用第一个
            
            if (result) {
              resolvedInfo = {
                title: result.title || null,
                description: result.description || null,
                status: result.status || 'ok',
                statusCode: result.status_code || null,
                message: result.message || null
              };
              console.log(`【URL解析】从结果对象中提取信息:`, resolvedInfo);
            }
          }
          // 处理单个结果对象
          else if (typeof response.data === 'object') {
            const result = response.data;
            resolvedInfo = {
              title: result.title || null,
              description: result.description || null,
              status: result.status || 'ok',
              statusCode: result.status_code || null,
              message: result.message || null
            };
            console.log(`【URL解析】从单个结果对象中提取信息:`, resolvedInfo);
          }
        }
      } catch (parseError) {
        console.error(`解析响应数据时出错:`, parseError);
      }
      
      // 兼容旧格式
      if (response.data && response.data.resolved_urls) {
        // 兼容旧格式: { resolved_urls: { [url]: title } }
        resolvedInfo.title = response.data.resolved_urls[sourceToResolve.url] || null;
        console.log(`【URL解析】从 resolved_urls 中提取标题:`, resolvedInfo.title);
      }
      
      // 根据状态码和消息判断是否需要特殊处理
      if (resolvedInfo.statusCode === 404 || resolvedInfo.message?.includes('404')) {
        // 404 错误，标记为错误
        resolvedInfo.status = 'error';
      } else if (resolvedInfo.statusCode === 403 || 
                resolvedInfo.message?.includes('403') || 
                resolvedInfo.message?.includes('Forbidden') ||
                resolvedInfo.message?.includes('访问被拒绝')) {
        // 403 错误或访问被拒绝，标记为警告
        resolvedInfo.status = 'warning';
      }
      
      // 更新内部源状态
      setInternalSources(prevSources =>
        prevSources?.map(s =>
          s.url === sourceToResolve.url
            ? { 
                ...s, 
                resolved_title: resolvedInfo.title || 'Title not found',
                resolved_description: resolvedInfo.description,
                resolved_status: resolvedInfo.status,
                resolved_message: resolvedInfo.message
              }
            : s
        )
      );

    } catch (error) {
      console.error('Error resolving URL:', error);
      const errorMessage = error instanceof Error ? error.message : 'Unknown error';
      setResolveErrors(prev => ({ ...prev, [sourceToResolve.url]: errorMessage }));
       // Optionally keep the old title or clear it on error
       setInternalSources(prevSources =>
        prevSources?.map(s =>
          s.url === sourceToResolve.url
            ? { ...s, resolved_title: null } // Clear title on error
            : s
        )
      );
    } finally {
      setResolvingUrls(prev => {
        const newResolving = new Set(prev);
        newResolving.delete(sourceToResolve.url);
        return newResolving;
      });
    }
  }, []);
  
  // 一键解析所有 URL 的函数
  const handleResolveAllUrls = useCallback(async () => {
    // 检查是否有未解析的 URL
    const unresolvedSources = internalSources?.filter(
      source => !resolvingUrls.has(source.url) && source.resolved_title === undefined
    );
    
    if (!unresolvedSources || unresolvedSources.length === 0) {
      console.log('【URL解析】没有需要解析的 URL');
      return;
    }
    
    // 设置批量解析状态
    setIsBatchResolving(true);
    
    console.log(`【URL解析】开始批量解析 ${unresolvedSources.length} 个 URL`);
    
    try {
      // 按顺序解析每个 URL
      for (let i = 0; i < unresolvedSources.length; i++) {
        const source = unresolvedSources[i];
        await handleResolveUrl(source);
        // 添加小延迟，避免请求过快
        await new Promise(resolve => setTimeout(resolve, 200));
      }
      
      console.log('【URL解析】批量解析完成');
    } catch (error) {
      console.error('【URL解析】批量解析过程中出错:', error);
    } finally {
      // 无论成功或失败，都重置批量解析状态
      setIsBatchResolving(false);
    }
  }, [internalSources, resolvingUrls, handleResolveUrl]);

  if (!internalSources || internalSources.length === 0) {
    return <p className="text-sm text-gray-500">No sources provided.</p>;
  }

  const displayedSources = isExpanded ? internalSources : internalSources.slice(0, 3); // Show first 3 when collapsed

  return (
    <div>
      <div className="flex justify-between items-center mb-2">
        <h4 className="text-md font-semibold">Sources ({internalSources.length})</h4>
        
        {/* 添加一键解析所有 URL 的按钮 */}
        {internalSources && internalSources.length > 0 && (
          <Button 
            variant={isBatchResolving ? "default" : "outline"}
            size="sm"
            onClick={handleResolveAllUrls}
            disabled={isBatchResolving || internalSources.every(s => resolvingUrls.has(s.url) || s.resolved_title !== undefined)}
            className="text-xs relative"
          >
            <RefreshCw className={`h-3 w-3 mr-1 ${isBatchResolving ? 'animate-spin' : ''}`} />
            {isBatchResolving 
              ? `正在解析...` 
              : `解析所有 URL`
            }
          </Button>
        )}
      </div>
      <ul className="space-y-1 list-none p-0 mb-2">
        {displayedSources.map((source, index) => (
          <SourceItem
            key={`source-${index}-${source.url.substring(0, 20)}`} // 使用索引和 URL 的前 20 个字符作为唯一 key
            source={source}
            onResolve={handleResolveUrl}
            isResolving={resolvingUrls.has(source.url)}
            resolveError={resolveErrors[source.url]}
            index={isExpanded ? index + 1 : (internalSources.indexOf(source) + 1)} // 添加索引，从1开始计数
          />
        ))}
      </ul>
      {internalSources.length > 3 && (
        <Button
          variant="outline"
          size="sm"
          onClick={() => setIsExpanded(!isExpanded)}
          className="w-full text-sm"
        >
          {isExpanded ? 'Show Less' : `Show More (${internalSources.length - 3})`}
          {isExpanded ? <ChevronUp className="ml-2 h-4 w-4" /> : <ChevronDown className="ml-2 h-4 w-4" />}
        </Button>
      )}
    </div>
  );
};

export default SourceList;

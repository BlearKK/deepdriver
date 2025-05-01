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

  // 单个 URL 解析函数
  const handleResolveUrl = useCallback(async (sourceToResolve: Source) => {
    setResolvingUrls(prev => new Set(prev).add(sourceToResolve.url));
    setResolveErrors(prev => {
      const newErrors = { ...prev };
      delete newErrors[sourceToResolve.url];
      return newErrors;
    });

    try {
      // 使用环境变量获取API基础URL
      const apiBaseUrl = import.meta.env.VITE_API_BASE_URL || 'http://localhost:5000';
      const apiUrl = `${apiBaseUrl}/api/resolve_urls`;
      
      console.log(`【URL解析】发送请求到 ${apiUrl}，解析单个 URL: ${sourceToResolve.url}`);
      
      // 发送请求到后端 API
      const response = await axios.post(apiUrl, {
        urls: [sourceToResolve.url]
      });
      
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
      if (response.data && Array.isArray(response.data) && response.data.length > 0) {
        // 新格式: 数组式式
        const result = response.data[0];
        resolvedInfo = {
          title: result.title || null,
          description: result.description || null,
          status: result.status || 'ok',
          statusCode: result.status_code || null,
          message: result.message || null
        };
        console.log(`【URL解析】从数组响应中提取信息:`, resolvedInfo);
      } 
      else if (response.data && response.data.results && Array.isArray(response.data.results)) {
        // 兼容旧格式: { results: [] }
        const result = response.data.results.find(r => r.original_url === sourceToResolve.url || r.url === sourceToResolve.url);
        if (result) {
          resolvedInfo = {
            title: result.title || null,
            description: result.description || null,
            status: result.status || 'ok',
            statusCode: result.status_code || null,
            message: result.message || null
          };
        }
        console.log(`【URL解析】从 results 数组中提取信息:`, resolvedInfo);
      }
      else if (response.data && response.data.resolved_urls) {
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

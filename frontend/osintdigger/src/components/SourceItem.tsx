import React, { useMemo } from 'react';
import { Source } from '@/types';
import { Button } from '@/components/ui/button';
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from '@/components/ui/tooltip';
import { ExternalLink, RefreshCw, AlertCircle, FileText, Info } from 'lucide-react';

interface SourceItemProps {
  source: Source;
  onResolve: (source: Source) => void; // Callback function to trigger URL resolution
  isResolving: boolean; // Flag to indicate if this specific source is being resolved
  resolveError?: string | null; // Error message specific to this source's resolution attempt
  index?: number; // 添加索引属性，用于显示序号
}

const SourceItem: React.FC<SourceItemProps> = ({ source, onResolve, isResolving, resolveError, index }) => {
  // 检测是否是 Google Vertex AI URL
  const isGoogleVertexUrl = useMemo(() => {
    return source.url.includes('vertexaisearch.cloud.google.com/grounding-api-redirect/');
  }, [source.url]);
  
  // 为 Google Vertex AI URL 提供特殊处理
  const specialUrlHandling = useMemo(() => {
    if (isGoogleVertexUrl) {
      return {
        displayName: 'Google Vertex AI Search Result',
        tooltip: '这是 Google Vertex AI 搜索结果链接，可能无法解析标题',
        icon: Info,
        iconColor: 'text-blue-500'
      };
    }
    return null;
  }, [isGoogleVertexUrl]);

  // 根据解析状态确定显示样式
  const resolvedStatus = useMemo(() => {
    // 如果有错误信息，优先使用错误信息
    if (resolveError) {
      return {
        icon: AlertCircle,
        iconColor: 'text-red-500',
        bgColor: 'bg-red-50',
        borderColor: 'border-red-200',
        textColor: 'text-red-700',
        tooltip: `解析错误: ${resolveError}`
      };
    }
    
    // 使用源中的解析状态
    if (source.resolved_status === 'error') {
      return {
        icon: AlertCircle,
        iconColor: 'text-red-500',
        bgColor: 'bg-red-50',
        borderColor: 'border-red-200',
        textColor: 'text-red-700',
        tooltip: source.resolved_message || '404 错误，无法访问网页'
      };
    } else if (source.resolved_status === 'warning') {
      return {
        icon: AlertCircle,
        iconColor: 'text-yellow-500',
        bgColor: 'bg-yellow-50',
        borderColor: 'border-yellow-200',
        textColor: 'text-yellow-700',
        tooltip: source.resolved_message || '需要手动访问的网页'
      };
    } else if (source.resolved_title) {
      return {
        icon: FileText,
        iconColor: 'text-green-500',
        bgColor: 'bg-white',
        borderColor: 'border-gray-200',
        textColor: 'text-gray-800',
        tooltip: '标题已解析'
      };
    }
    
    // 如果是特殊 URL，使用特殊处理
    if (specialUrlHandling) {
      return {
        icon: specialUrlHandling.icon,
        iconColor: specialUrlHandling.iconColor,
        bgColor: 'bg-blue-50',
        borderColor: 'border-blue-200',
        textColor: 'text-blue-700',
        tooltip: specialUrlHandling.tooltip
      };
    }
    
    // 默认状态
    return {
      icon: FileText,
      iconColor: 'text-gray-500',
      bgColor: 'bg-white',
      borderColor: 'border-gray-200',
      textColor: 'text-gray-800',
      tooltip: '解析 URL 标题'
    };
  }, [resolveError, source.resolved_status, source.resolved_message, source.resolved_title, specialUrlHandling]);
  
  // 确定图标和颜色
  const ResolveIcon = isResolving ? RefreshCw : resolvedStatus.icon;
  const iconColor = isResolving ? 'text-blue-500 animate-spin' : resolvedStatus.iconColor;

  return (
    <li 
      key={source.url} 
      className={`flex flex-col py-2 px-3 mb-2 rounded-lg border ${resolvedStatus.borderColor} ${resolvedStatus.bgColor}`}
    >
      <div className="flex items-center justify-between mb-1">
        <div className="flex items-center space-x-2 overflow-hidden">
          {/* 显示序号，如果提供了index */}
          {index !== undefined && (
            <span className="text-sm font-bold text-orange-500 min-w-[30px]">【{index}】</span>
          )}
          <TooltipProvider>
            <Tooltip delayDuration={100}>
              <TooltipTrigger asChild>
                <Button
                  variant="ghost"
                  size="icon"
                  className={`h-6 w-6 ${iconColor}`}
                  onClick={() => !source.resolved_title && !isResolving && onResolve(source)}
                  disabled={isResolving || !!source.resolved_title || isGoogleVertexUrl}
                >
                  <ResolveIcon className="h-4 w-4" />
                </Button>
              </TooltipTrigger>
              <TooltipContent>
                <p>{resolvedStatus.tooltip}</p>
              </TooltipContent>
            </Tooltip>
          </TooltipProvider>
          <span 
            className={`text-sm font-medium truncate ${resolvedStatus.textColor}`} 
            title={source.resolved_title || (specialUrlHandling?.displayName || source.url)}
          >
            {source.resolved_title || (specialUrlHandling?.displayName || source.url)}
          </span>
        </div>
        <a href={source.url} target="_blank" rel="noopener noreferrer">
          <Button variant="ghost" size="icon" className="h-6 w-6 text-blue-600 hover:text-blue-800">
            <ExternalLink className="h-4 w-4" />
          </Button>
        </a>
      </div>
      
      {/* 显示网页描述 */}
      {source.resolved_description && (
        <div className={`text-xs mt-1 line-clamp-2 ${resolvedStatus.textColor}`}>
          {source.resolved_description}
        </div>
      )}
      
      {/* 显示原始 URL */}
      <div className="text-xs text-gray-500 mt-1 truncate">
        {source.url}
      </div>
      
      {/* 显示错误或警告信息 */}
      {source.resolved_message && (source.resolved_status === 'error' || source.resolved_status === 'warning') && (
        <div className={`text-xs mt-1 ${source.resolved_status === 'error' ? 'text-red-600' : 'text-yellow-600'}`}>
          {source.resolved_message}
        </div>
      )}
    </li>
  );
};

export default SourceItem;

// SSE客户端工具 - 处理SSE连接和回退逻辑

import { SSE_CONFIG } from '../constants';
import { SSEMessage, SearchResult } from '../types';

// SSE连接配置类型
export interface SSEConnectionConfig {
  institutionA: string;  // 目标机构名称
  apiBaseUrl: string;    // API基础URL
  onMessage: (data: SSEMessage) => void;  // 消息处理函数
  onError: (error: Event) => void;       // 错误处理函数
  onFallback: (institutionA: string) => void; // 回退处理函数
  processedItems?: Set<string>;  // 已处理的项目列表
  sessionId?: string; // 会话ID
  progress?: number;  // 当前进度
}

interface ReconnectData {
  // reconnect data properties
}

type CleanupFunction = () => void;

/**
 * 注册会话并获取会话ID
 * @param config 连接配置
 * @returns 返回会话ID的Promise
 */
export const registerSession = async ({
  institutionA,
  apiBaseUrl,
  processedItems = new Set<string>(),
  sessionId = `session_${Date.now()}`
}: Omit<SSEConnectionConfig, 'onMessage' | 'onError' | 'onFallback'>): Promise<string> => {
  // 处理已处理项目列表
  console.log(`注册会话，当前已处理项目数: ${processedItems.size}`);
  const processedArray = Array.from(processedItems);
  
  // 构建注册会话URL
  let registerUrl = '';
  const isDevelopment = process.env.NODE_ENV === 'development';
  
  // 在开发环境中，始终使用localhost:5000
  if (isDevelopment) {
    registerUrl = 'http://localhost:5000/api/register_session';
    console.log(`开发环境使用固定URL: ${registerUrl}`);
  } else {
    // 在生产环境中，使用apiBaseUrl
    // 确保apiBaseUrl不以斜杠结尾
    const baseUrl = apiBaseUrl.endsWith('/') ? apiBaseUrl.slice(0, -1) : apiBaseUrl;
    registerUrl = `${baseUrl}/api/register_session`;
    console.log(`生产环境使用动态URL: ${registerUrl}`);
  }
  
  try {
    // 发送POST请求注册会话
    console.log(`发送注册会话请求到: ${registerUrl}`);
    const response = await fetch(registerUrl, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({
        institutionA: institutionA,
        processedItems: processedArray,
        sessionId: sessionId
      })
    });
    
    if (!response.ok) {
      throw new Error(`注册会话失败: ${response.status} ${response.statusText}`);
    }
    
    const data = await response.json();
    console.log(`注册会话成功，会话ID: ${data.session_id}`);
    return data.session_id || sessionId;
  } catch (error) {
    console.error(`注册会话时出错:`, error);
    // 如果注册失败，返回原始的会话ID
    return sessionId;
  }
};

/**
 * 创建SSE连接
 * @param config 连接配置
 * @returns 连接对象和清理函数
 */
export const createSSEConnection = async ({
  institutionA,
  apiBaseUrl,
  onMessage,
  onError,
  onFallback,
  processedItems = new Set<string>(),
  sessionId = `session_${Date.now()}`,
  progress
}: SSEConnectionConfig): Promise<{
  eventSource: EventSource;
  cleanup: () => void;
  reconnect: () => void;
}> => {
  // 检查参数
  if (!institutionA || institutionA.trim() === '') {
    console.error('错误: institutionA不能为空');
    throw new Error('institutionA is required');
  }
  
  if (!apiBaseUrl) {
    console.error('错误: apiBaseUrl不能为空');
    throw new Error('apiBaseUrl is required');
  }
  
  // 生成随机ID和时间戳，用于防止缓存
  const randomId = Math.floor(Math.random() * 1000000);
  const timestamp = Math.floor(Date.now() / 1000);
  const encodedInstitution = encodeURIComponent(institutionA);
  
  // 判断是否是服务器环境
  const isProduction = window.location.hostname !== 'localhost' && !window.location.hostname.includes('127.0.0.1');
  const isDevelopment = import.meta.env.MODE === 'development';
  
  // 在服务器环境中调整连接超时时间，但不直接切换到HTTP请求
  // 我们将先尝试SSE连接，只有在连接失败时才会回退到HTTP请求
  console.log(`尝试建立SSE连接，环境: ${isProduction ? '生产环境' : '本地环境'}, 开发模式: ${isDevelopment}`);
  
  // 如果是跨域请求，记录日志但仍然尝试SSE连接
  if (apiBaseUrl !== window.location.origin) {
    console.log(`检测到跨域请求 (${apiBaseUrl} != ${window.location.origin})，但仍然尝试SSE连接`);
  }
  
  // 第一步：准备会话参数
  // 简化实现，跳过会话注册步骤，直接使用会话ID
  console.log(`使用会话ID: ${sessionId}`);
  
  // 将已处理项目列表存储在本地存储中，而不是发送到服务器
  // 这样可以避免 URL 过长的问题
  if (processedItems.size > 0) {
    try {
      // 使用localStorage存储已处理项目列表
      localStorage.setItem(`processed_${sessionId}`, JSON.stringify(Array.from(processedItems)));
      console.log(`已将${processedItems.size}个已处理项目存储在本地`);
    } catch (err) {
      console.warn(`存储已处理项目失败:`, err);
    }
  }
  
  // 第二步：构建SSE URL - 传递会话ID和进度信息（如果有）
  let sseUrl = '';
  
  // 准备基本参数
  let params = `institution_A=${encodeURIComponent(institutionA)}&session_id=${sessionId}&_t=${timestamp}&_r=${randomId}`;
  
  // 如果有进度信息，添加到URL中
  if (progress !== undefined && progress > 0) {
    params += `&progress=${progress}`;
    console.log(`在URL中包含进度信息: ${progress}`);
  } else if (processedItems && processedItems.size > 0) {
    // 如果没有直接提供进度信息，但有已处理项目列表，使用列表大小作为进度
    params += `&progress=${processedItems.size}`;
    console.log(`使用已处理项目数量作为进度: ${processedItems.size}`);
  }
  
  // 在开发环境中，始终使用localhost:5000
  if (isDevelopment) {
    sseUrl = `http://localhost:5000/api/deepsearch?${params}`;
    console.log(`开发环境使用完整URL: ${sseUrl}`);
  } else {
    // 在生产环境中，使用apiBaseUrl
    // 确保apiBaseUrl不以斜杠结尾
    const baseUrl = apiBaseUrl.endsWith('/') ? apiBaseUrl.slice(0, -1) : apiBaseUrl;
    sseUrl = `${baseUrl}/api/deepsearch?${params}`;
    console.log(`生产环境使用完整URL: ${sseUrl}`);
  }
  
  console.log(`Connecting to SSE endpoint: ${sseUrl}`);
  
  // 创建EventSource连接
  // 在开发环境中，不使用withCredentials，避免跨域问题
  const eventSource = new EventSource(sseUrl, { 
    withCredentials: false // 始终不使用withCredentials，避免跨域问题
  });
  let reconnectAttempts = 0;
  let connectionTimeoutId: number | null = null;
  let heartbeatTimeoutId: number | null = null;
  let lastActivityTime = Date.now();
  
  // 设置连接超时，使用常量文件中设置的超时值
  // 在跨域请求中可能需要更长的时间来建立连接
  const effectiveTimeout = SSE_CONFIG.CONNECTION_TIMEOUT; // 使用常量文件中的超时设置
  
  console.log(`设置连接超时: ${effectiveTimeout/1000}秒`);
  
  connectionTimeoutId = window.setTimeout(() => {
    console.log(`SSE连接超时 (${effectiveTimeout/1000}秒)，切换到HTTP请求`);
    eventSource.close();
    onFallback(institutionA);
  }, effectiveTimeout);
  
  // 设置主动重连定时器 (4分45秒 = 285000毫秒)
  // Railway平台有5分钟(300秒)的连接限制
  const RECONNECT_INTERVAL = 285000; // 4分45秒
  let reconnectTimeoutId: number | null = null;
  
  console.log(`设置主动重连定时器: ${RECONNECT_INTERVAL/1000}秒`);
  reconnectTimeoutId = window.setTimeout(() => {
    console.log(`主动重连: 连接时间接近5分钟限制，主动关闭并重新连接`);
    // 发送重连警告消息
    try {
      onMessage({
        type: 'reconnect_warning',
        message: 'Connection approaching time limit, reconnecting...'
      });
    } catch (notifyError) {
      console.error('Error sending reconnect warning:', notifyError);
    }
    
    // 关闭当前连接
    eventSource.close();
    
    // 清除所有定时器
    if (connectionTimeoutId) {
      clearTimeout(connectionTimeoutId);
      connectionTimeoutId = null;
    }
    if (heartbeatTimeoutId) {
      clearTimeout(heartbeatTimeoutId);
      heartbeatTimeoutId = null;
    }
    if (reconnectTimeoutId) {
      clearTimeout(reconnectTimeoutId);
      reconnectTimeoutId = null;
    }
    
    // 触发重连函数
    reconnect();
  }, RECONNECT_INTERVAL);
  
  // 添加活动检查定时器，定期检查连接是否活跃
  const activityCheckerId = window.setInterval(() => {
    const inactiveTime = Date.now() - lastActivityTime;
    if (inactiveTime > SSE_CONFIG.HEARTBEAT_TIMEOUT) {
      console.log(`SSE connection inactive for ${inactiveTime/1000} seconds, attempting to reconnect...`);
      
      // 尝试重连而不是立即回退到HTTP
      if (reconnectAttempts < SSE_CONFIG.MAX_RECONNECT_ATTEMPTS) {
        reconnectAttempts++;
        console.log(`Reconnect attempt ${reconnectAttempts}/${SSE_CONFIG.MAX_RECONNECT_ATTEMPTS}`);
        
        // 发送连接警告消息
        try {
          onMessage({
            type: 'connection_warning',
            message: `Connection inactive, attempting reconnect ${reconnectAttempts}/${SSE_CONFIG.MAX_RECONNECT_ATTEMPTS}...`
          });
        } catch (notifyError) {
          console.error('Error sending connection warning:', notifyError);
        }
        
        // 重置最后活动时间，给予更多时间重连
        lastActivityTime = Date.now();
      } else {
        console.log(`Exceeded maximum reconnect attempts (${SSE_CONFIG.MAX_RECONNECT_ATTEMPTS}), falling back to HTTP`);
        clearInterval(activityCheckerId);
        eventSource.close();
        onFallback(institutionA);
      }
    }
  }, SSE_CONFIG.ACTIVITY_CHECK_INTERVAL);
  
  // 处理连接打开
  eventSource.onopen = () => {
    console.log('SSE connection opened');
    // 更新最后活动时间
    lastActivityTime = Date.now();
    
    // 清除连接超时
    if (connectionTimeoutId) {
      clearTimeout(connectionTimeoutId);
      connectionTimeoutId = null;
    }
    
    // 设置心跳超时
    heartbeatTimeoutId = window.setTimeout(() => {
      console.log('No heartbeat received after connection, trying fallback');
      eventSource.close();
      onFallback(institutionA);
    }, SSE_CONFIG.HEARTBEAT_TIMEOUT);
    
    // 重置重连计数器
    reconnectAttempts = 0;
    
    // 发送连接成功事件
    try {
      onMessage({
        type: 'connect',
        message: 'Connection established'
      });
    } catch (error) {
      console.error('Error sending connect event:', error);
    }
  };
  
  // 处理消息
  eventSource.onmessage = (event) => {
    try {
      // 更新最后活动时间
      lastActivityTime = Date.now();
      
      console.log('Received SSE message:', event.data);
      let data: SSEMessage;
      
      try {
        data = JSON.parse(event.data) as SSEMessage;
      } catch (parseError) {
        console.error('Error parsing SSE message:', parseError);
        // 尝试处理非JSON消息
        data = {
          type: 'raw',
          message: event.data
        } as SSEMessage;
      }
      
      // 重置心跳超时
      if (heartbeatTimeoutId) {
        clearTimeout(heartbeatTimeoutId);
      }
      
      // 如果是心跳消息，设置新的心跳超时
      if (data.type === 'heartbeat') {
        // 重置重连计数器，因为收到了有效消息
        reconnectAttempts = 0;
        
        heartbeatTimeoutId = window.setTimeout(() => {
          console.log('No heartbeat received, checking connection status...');
          
          // 尝试重连而不是立即回退到HTTP
          if (reconnectAttempts < SSE_CONFIG.MAX_RECONNECT_ATTEMPTS) {
            reconnectAttempts++;
            console.log(`Heartbeat reconnect attempt ${reconnectAttempts}/${SSE_CONFIG.MAX_RECONNECT_ATTEMPTS}`);
            
            // 发送连接警告消息
            try {
              onMessage({
                type: 'connection_warning',
                message: `Heartbeat missed, attempting reconnect ${reconnectAttempts}/${SSE_CONFIG.MAX_RECONNECT_ATTEMPTS}...`
              });
            } catch (notifyError) {
              console.error('Error sending heartbeat warning:', notifyError);
            }
            
            // 重置最后活动时间，给予更多时间重连
            lastActivityTime = Date.now();
            
            // 设置新的心跳超时，继续等待
            heartbeatTimeoutId = window.setTimeout(() => {
              if (reconnectAttempts >= SSE_CONFIG.MAX_RECONNECT_ATTEMPTS) {
                console.log('Maximum heartbeat reconnect attempts reached, falling back to HTTP');
                eventSource.close();
                onFallback(institutionA);
              }
            }, SSE_CONFIG.HEARTBEAT_TIMEOUT / 2);
          } else {
            console.log('Maximum heartbeat reconnect attempts reached, falling back to HTTP');
            eventSource.close();
            onFallback(institutionA);
          }
        }, SSE_CONFIG.HEARTBEAT_TIMEOUT);
      }
      
      // 传递消息给回调函数
      onMessage(data);
    } catch (error) {
      console.error('Error handling SSE message:', error);
      onError(error);
    }
  };
  
  // 处理错误
  eventSource.onerror = (error) => {
    console.error('SSE connection error:', error);
    
    // 记录错误时间
    const errorTime = Date.now();
    const timeSinceLastActivity = errorTime - lastActivityTime;
    console.log(`Time since last activity: ${timeSinceLastActivity}ms`);
    
    // 如果最近有活动，给予更多重试机会
    const effectiveMaxRetries = timeSinceLastActivity < 5000 ? 
      SSE_CONFIG.MAX_RECONNECT_ATTEMPTS + 2 : 
      SSE_CONFIG.MAX_RECONNECT_ATTEMPTS;
    
    // 尝试重新连接
    if (reconnectAttempts < effectiveMaxRetries) {
      reconnectAttempts++;
      console.log(`SSE error, reconnect attempt ${reconnectAttempts}/${effectiveMaxRetries}`);
      // 不立即关闭连接，让浏览器尝试重新连接
      
      // 如果是第一次错误，尝试发送一个错误通知但继续保持连接
      if (reconnectAttempts === 1) {
        try {
          onMessage({
            type: 'connection_warning',
            message: 'Connection experiencing issues, attempting to reconnect...'
          });
        } catch (notifyError) {
          console.error('Error sending connection warning:', notifyError);
        }
      }
    } else {
      // 超过最大重试次数，关闭连接并切换到HTTP备用方案
      console.log(`SSE connection failed after ${reconnectAttempts} reconnect attempts, switching to HTTP fallback`);
      // 清除所有超时
      if (connectionTimeoutId) {
        clearTimeout(connectionTimeoutId);
      }
      if (heartbeatTimeoutId) {
        clearTimeout(heartbeatTimeoutId);
      }
      eventSource.close();
      onFallback(institutionA);
    }
  };
  
  // 重连函数
  const reconnect = () => {
    console.log(`执行重连，已处理项目数: ${processedItems.size}`);
    console.log(`重连时的目标机构: "${institutionA}"`);
    
    try {
      // 检查目标机构是否为空
      if (!institutionA || !institutionA.trim()) {
        console.error('重连失败: 目标机构为空');
        return false;
      }
      
      // 先关闭旧的连接
      if (eventSource) {
        // 清除所有事件处理程序
        eventSource.onmessage = null;
        eventSource.onerror = null;
        eventSource.onopen = null;
        
        // 关闭连接
        eventSource.close();
        console.log('旧连接已关闭');
      }
      
      // 清除所有定时器
      if (connectionTimeoutId) {
        clearTimeout(connectionTimeoutId);
        connectionTimeoutId = null;
      }
      if (heartbeatTimeoutId) {
        clearTimeout(heartbeatTimeoutId);
        heartbeatTimeoutId = null;
      }
      if (reconnectTimeoutId) {
        clearTimeout(reconnectTimeoutId);
        reconnectTimeoutId = null;
      }
      
      // 记录当前已处理的项目列表和会话ID
      const currentProcessedItems = new Set(processedItems);
      const currentSessionId = sessionId;
      const currentInstitutionA = institutionA;
      
      console.log(`重连前的状态: 会话ID=${currentSessionId}, 目标机构="${currentInstitutionA}", 已处理项目数=${currentProcessedItems.size}`);
      
      // 不直接创建新的EventSource，而是调用onMessage回调
      // 这样可以让useDeepSearch钩子创建新的连接
      console.log('通知上层组件创建新连接...');
      
      // 先清理当前资源
      cleanup();
      
      // 通知上层组件创建新连接
      // 使用一个特殊的标记来表示这是主动重连而不是错误回退
      // 传递已处理的项目列表、会话ID和目标机构名称
      onMessage({
        type: 'reconnect_warning',
        message: 'Connection approaching time limit, reconnecting...',
        reconnect: true,
        processedItems: Array.from(currentProcessedItems),
        sessionId: currentSessionId,
        institutionA: currentInstitutionA
      });
      
      return true;
    } catch (error) {
      console.error('重连失败:', error);
      // 如果重连失败，尝试回退到HTTP请求
      onFallback(institutionA);
      return false;
    }
  };
  
  // 返回清理函数
  const cleanup = () => {
    if (connectionTimeoutId) {
      clearTimeout(connectionTimeoutId);
    }
    if (heartbeatTimeoutId) {
      clearTimeout(heartbeatTimeoutId);
    }
    if (reconnectTimeoutId) {
      clearTimeout(reconnectTimeoutId);
    }
    clearInterval(activityCheckerId);
    eventSource.close();
    console.log('SSE connection cleaned up');
  };
  
  return { eventSource, cleanup, reconnect };
};

// 使用普通HTTP请求作为备用方案
export const fallbackToRegularRequest = async (
  institutionA: string,
  apiBaseUrl: string,
  sessionId: string,
  processedItems: Set<string>,
  onSuccess: (results: SearchResult[], processed: number, total: number) => void,
  onError: (error: any) => void
): Promise<void> => {
  console.log('Trying to use regular HTTP request instead of SSE');
  
  try {
    // 获取已处理的项目列表
    const processedItemsArray = Array.from(processedItems).join(',');
    console.log(`Continuing with ${processedItems.size} already processed items`);
    
    // 构建API URL，添加时间戳和随机数防止缓存
    const timestamp = Date.now();
    const randomId = Math.floor(Math.random() * 1000000);
    
    // 构建API URL - 强制使用绝对URL
    let url = '';
    
    // 在开发环境中，始终使用localhost:5000
    if (import.meta.env.MODE === 'development') {
      url = `http://localhost:5000/api/deepsearch_simple?institution_A=${encodeURIComponent(institutionA)}&session_id=${sessionId}&_t=${timestamp}&_r=${randomId}`;
      console.log(`开发环境使用固定URL: ${url}`);
    } else {
      // 在生产环境中，使用apiBaseUrl
      // 确保apiBaseUrl不以斜杠结尾
      const baseUrl = apiBaseUrl.endsWith('/') ? apiBaseUrl.slice(0, -1) : apiBaseUrl;
      url = `${baseUrl}/api/deepsearch_simple?institution_A=${encodeURIComponent(institutionA)}&session_id=${sessionId}&_t=${timestamp}&_r=${randomId}`;
      console.log(`生产环境使用动态URL: ${url}`);
    }
    
    // 添加已处理的项目参数（如果有）
    if (processedItems.size > 0) {
      // 将Set转换为数组，然后转换为JSON字符串
      const processedItemsArray = JSON.stringify(Array.from(processedItems));
      url += `&processed=${encodeURIComponent(processedItemsArray)}`;
    }
    
    console.log(`Trying regular HTTP request to: ${url}`);
    
    // 发送请求，添加超时和重试逻辑
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), 30000); // 30秒超时
    
    try {
      const response = await fetch(url, {
        method: 'GET',
        headers: {
          'Accept': 'application/json',
          'X-Requested-With': 'XMLHttpRequest',
          'Origin': window.location.origin
        },
        credentials: 'omit', // 在服务器环境中使用'omit'可能更可靠
        signal: controller.signal,
        cache: 'no-cache'
      });
      
      clearTimeout(timeoutId);
      
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }
      
      const data = await response.json();
      
      // 处理结果
      if (data.results && data.results.length > 0) {
        console.log(`Adding ${data.results.length} new results from fallback request`);
        onSuccess(data.results, data.processed, data.total);
      } else {
        console.log('No new results from fallback request');
        // 即使没有新结果，也要更新进度
        if (data.processed && data.total) {
          onSuccess([], data.processed, data.total);
        }
      }
    } catch (fetchError) {
      clearTimeout(timeoutId);
      if (fetchError.name === 'AbortError') {
        console.error('Fallback request timed out');
        throw new Error('Request timed out. Server might be busy, please try again later.');
      }
      throw fetchError;
    }
  } catch (error) {
    console.error('HTTP request failed:', error);
    onError(error);
  }
};

import { useState, useRef, useEffect, useCallback } from 'react';
import { SearchResult, SSEMessage } from '../types';
import { createSSEConnection, fallbackToRegularRequest } from '../utils/sseClient';
import { TIME_UNITS } from '../constants';

// 定义批处理信息类型
interface BatchInfo {
  currentBatch: number;
  totalBatches: number;
}

// 自定义Hook - 包含DeepSearch的所有状态和业务逻辑
const useDeepSearch = () => {
  // 组件状态
  const [institutionA, setInstitutionA] = useState<string>('');
  const [isSearching, setIsSearching] = useState<boolean>(false);
  const [progress, setProgress] = useState<number>(0);
  const [totalItems, setTotalItems] = useState<number>(0);
  const [results, setResults] = useState<SearchResult[]>([]);
  const [showNoEvidence, setShowNoEvidence] = useState<boolean>(true);
  const [estimatedTimeRemaining, setEstimatedTimeRemaining] = useState<string | null>(null);
  const [sessionId, setSessionId] = useState<string>(`session_${Date.now()}`);
  const [error, setError] = useState<string>('');
  const [processingTimes, setProcessingTimes] = useState<number[]>([]);  // 存储每个项目的处理时间
  
  // 批处理信息状态
  const [batchInfo, setBatchInfo] = useState<BatchInfo>({
    currentBatch: 0,
    totalBatches: 1 // 默认为1，避免除零错误
  });
  
  // 引用
  const eventSourceRef = useRef<EventSource | null>(null);
  const processedItemsRef = useRef<Set<string>>(new Set());
  const isFallbackInProgressRef = useRef<boolean>(false);
  const searchStartTimeRef = useRef<number>(0);
  const cleanupFnRef = useRef<(() => void) | null>(null);
  const reconnectFnRef = useRef<(() => void) | null>(null);
  const reconnectCountRef = useRef<number>(0);
  const institutionARef = useRef<string>(''); // 使用ref存储目标机构名称，确保在重连过程中能够立即获取到最新的值
  const processingTimesRef = useRef<number[]>([]); // 存储每个项目的处理时间，用于估算剩余时间
  const lastProgressUpdateTimeRef = useRef<number>(Date.now()); // 上次进度更新的时间，用于计算处理速度
  
  // 调试函数，帮助跟踪重连过程中的问题
  const debugState = () => {
    console.log('=== DeepSearch 状态调试 ===');
    console.log(`institutionA (state): "${institutionA}"`);
    console.log(`institutionARef.current: "${institutionARef.current}"`);
    console.log(`sessionId: ${sessionId}`);
    console.log(`processedItemsRef.current.size: ${processedItemsRef.current.size}`);
    console.log(`isSearching: ${isSearching}`);
    console.log(`reconnectCountRef.current: ${reconnectCountRef.current}`);
    console.log(`eventSourceRef.current 是否存在: ${eventSourceRef.current !== null}`);
    console.log(`cleanupFnRef.current 是否存在: ${cleanupFnRef.current !== null}`);
    console.log(`reconnectFnRef.current 是否存在: ${reconnectFnRef.current !== null}`);
    console.log('========================');
  }
  
  // 更新剩余时间估计
  const updateTimeRemaining = useCallback((currentProgress: number, total: number) => {
    const now = Date.now();
    const elapsed = now - searchStartTimeRef.current;
    
    // 计算处理速度
    if (currentProgress > 0 && lastProgressUpdateTimeRef.current > 0) {
      const timeSinceLastUpdate = now - lastProgressUpdateTimeRef.current;
      const progressSinceLastUpdate = currentProgress - progress;
      
      if (progressSinceLastUpdate > 0 && timeSinceLastUpdate > 0) {
        // 记录每个项目的处理时间
        const timePerItem = timeSinceLastUpdate / progressSinceLastUpdate;
        processingTimesRef.current.push(timePerItem);
        
        // 限制数组大小，只保留最近10个数据点
        if (processingTimesRef.current.length > 10) {
          processingTimesRef.current = processingTimesRef.current.slice(-10);
        }
      }
    }
    
    // 更新最后进度时间
    lastProgressUpdateTimeRef.current = now;
    
    // 计算平均处理时间
    if (processingTimesRef.current.length > 0) {
      const avgTimePerItem = processingTimesRef.current.reduce((sum, time) => sum + time, 0) / processingTimesRef.current.length;
      const remainingItems = total - currentProgress;
      const estimatedMilliseconds = remainingItems * avgTimePerItem;
      
      // 选择适当的时间单位
      let timeString = '';
      if (estimatedMilliseconds < 60000) { // 小于1分钟，显示秒
        const seconds = Math.round(estimatedMilliseconds / 1000);
        timeString = `${seconds} ${seconds === 1 ? TIME_UNITS.SECOND_TEXT : TIME_UNITS.SECONDS_TEXT}`;
      } else if (estimatedMilliseconds < 3600000) { // 小于1小时，显示分钟
        const minutes = Math.round(estimatedMilliseconds / 60000);
        timeString = `${minutes} ${minutes === 1 ? TIME_UNITS.MINUTE_TEXT : TIME_UNITS.MINUTES_TEXT}`;
      } else { // 大于等于1小时，显示小时
        const hours = Math.round(estimatedMilliseconds / 3600000 * 10) / 10; // 保留一位小数
        timeString = `${hours} ${hours === 1 ? TIME_UNITS.HOUR_TEXT : TIME_UNITS.HOURS_TEXT}`;
      }
      
      // 更新状态
      setEstimatedTimeRemaining(timeString);
      console.log(`Estimated time remaining: ${timeString} (based on avg processing time of ${Math.round(avgTimePerItem/1000)} seconds per item)`);
    }
  }, [progress, TIME_UNITS.SECOND_TEXT, TIME_UNITS.SECONDS_TEXT, TIME_UNITS.MINUTE_TEXT, TIME_UNITS.MINUTES_TEXT, TIME_UNITS.HOUR_TEXT, TIME_UNITS.HOURS_TEXT]);
  
  // 显示错误并重置状态
  const showErrorAndReset = useCallback((errorMessage: string) => {
    setError(errorMessage);
    setIsSearching(false);
    if (eventSourceRef.current) {
      eventSourceRef.current.close();
      eventSourceRef.current = null;
    }
    if (cleanupFnRef.current) {
      cleanupFnRef.current();
      cleanupFnRef.current = null;
    }
  }, []);
  
  // 处理SSE消息
  const handleSSEMessage = useCallback((data: SSEMessage) => {
    // 调试收到的消息
    console.log(`[SSE Message Debug] 收到消息类型: ${data.type}`, data);
    
    // 使用类型断言来处理消息类型
    // 将消息类型转换为string类型，避免字符串字面量类型比较问题
    const messageType = data.type;
    
    // 初始化消息
    if (messageType === 'init') {
      setTotalItems(data.total || 0);
      return;
    }
    
    // 批处理信息消息
    if (messageType === 'batch_info') {
      console.log(`[Batch Info] 收到批处理信息:`, data);
      
      // 安全地访问批处理变量
      const currentBatch = data.current_batch !== undefined ? data.current_batch : 0;
      const totalBatches = data.total_batches !== undefined ? data.total_batches : 1; // 默认为1，避免除零错误
      
      console.log(`[Batch Info] 当前批次: ${currentBatch}/${totalBatches}`);
      
      // 存储批处理信息到状态中
      setBatchInfo({
        currentBatch,
        totalBatches
      });
      
      return;
    }
    
    // 重连警告消息
    if (messageType === 'reconnect_warning' as SSEMessage['type']) {
      console.log('Received reconnect warning:', data.message);
      
      // 调试当前状态
      console.log('[Reconnect Debug] 重连前状态:');
      debugState();
      
      // 检查是否需要重新创建SSE连接
      if (data.reconnect === true) {
        console.log('检测到重连标记，将创建新的SSE连接');
        
        // 增加重连计数
        reconnectCountRef.current++;
        console.log(`这是第 ${reconnectCountRef.current} 次重连`);
        
        // 先清理当前连接
        if (eventSourceRef.current) {
          eventSourceRef.current.close();
          eventSourceRef.current = null;
        }
        if (cleanupFnRef.current) {
          cleanupFnRef.current();
          cleanupFnRef.current = null;
        }
        
        // 重要改变: 不再使用从 sseClient 传递来的 processedItems
        // 而是使用我们自己维护的 processedItemsRef.current
        console.log(`重连时使用当前已处理项目列表，数量: ${processedItemsRef.current.size}`);
        
        // 检查是否有传递会话ID
        if (data.sessionId) {
          console.log(`收到会话ID: ${data.sessionId}`);
          setSessionId(data.sessionId);
        }
        
        // 检查是否有传递目标机构名称
        if (data.institutionA) {
          console.log(`收到目标机构名称: "${data.institutionA}"，当前值为: "${institutionA}"，Ref值为: "${institutionARef.current}"`);
          setInstitutionA(data.institutionA);
          institutionARef.current = data.institutionA; // 直接更新ref值
        } else if (institutionARef.current && institutionARef.current.trim() !== '') {
          // 使用ref值而不是state值
          console.log(`没有收到目标机构名称，使用Ref中的值: "${institutionARef.current}"`);
          setInstitutionA(institutionARef.current); // 同步到state
        } else if (institutionA && institutionA.trim() !== '') {
          // 如果没有传递目标机构名称，但当前值不为空，则保留当前值
          console.log(`没有收到目标机构名称，使用当前值: "${institutionA}"`);
          institutionARef.current = institutionA; // 更新ref值
        } else {
          console.warn('重连失败: 目标机构名称为空');
          return; // 如果目标机构名称为空，则不继续重连
        }

        // 创建新的SSE连接，使用我们自己维护的状态
        setTimeout(() => {
          console.log('开始创建新的SSE连接...');
          console.log(`重连前检查 - 目标机构State: "${institutionA}", Ref: "${institutionARef.current}", 会话ID: ${sessionId}, 已处理项目数: ${processedItemsRef.current.size}`);

          // 使用institutionARef而不institutionA检查目标机构是否为空
          if (!institutionARef.current || institutionARef.current.trim() === '') {
            console.log('重连失败: 目标机构名称仍然为空');
            return;
          }

          // 在重连前同步状态，确保 institutionA 不为空
          if (institutionARef.current && institutionARef.current.trim() !== '') {
            console.log(`[Reconnect Debug] 重连前同步 institutionA 状态: "${institutionARef.current}"`);
            setInstitutionA(institutionARef.current);
          }
          
          // 开始重连
          setTimeout(() => {
            console.log(`[Reconnect Debug] 延迟后再次检查状态:`);
            debugState();
            startDeepSearch(true); // 传递true表示这是重连操作
          }, 100); // 稍微延迟一下，确保旧连接已完全清理
        });
      }
      return;
    }
    
    // 心跳消息
    if (messageType === 'heartbeat' as SSEMessage['type']) {
      if (data.progress !== undefined && data.total !== undefined) {
        setProgress(data.progress);
        setTotalItems(data.total);
        
        // 如果心跳消息中包含已处理的项目列表，更新processedItemsRef
        if (data.processedItems && Array.isArray(data.processedItems) && data.processedItems.length > 0) {
          console.log(`心跳消息中收到已处理项目列表，数量: ${data.processedItems.length}`);
          // 更新已处理项目集合
          processedItemsRef.current = new Set(data.processedItems);
        } else {
          // 如果没有提供已处理的项目列表，但有进度信息，我们可以使用进度信息来更新已处理的项目数量
          // 注意：这只是一个标记，实际上我们不知道具体哪些项目已经处理过
          console.log(`心跳消息中没有已处理项目列表，但有进度信息: ${data.progress}/${data.total}`);
          
          // 将进度数存储到一个全局变量中，供重连时使用
          if (window && !window.hasOwnProperty('__deepSearchProgress')) {
            (window as any).__deepSearchProgress = {
              progress: 0,
              total: 0
            };
          }
          
          // 更新全局进度变量
          (window as any).__deepSearchProgress.progress = data.progress;
          (window as any).__deepSearchProgress.total = data.total;
          
          // 记录当前处理状态，用于日志和调试
          console.log(`Heartbeat message - Progress: ${data.progress}/${data.total}, Current processedItemsRef size: ${processedItemsRef.current.size}`);
          
          // 确保processedItemsRef的大小与进度一致
          // 使用一个更可靠的方法来同步进度
          if (processedItemsRef.current.size < data.progress) {
            // 记录当前大小
            const currentSize = processedItemsRef.current.size;
            
            // 补充虚拟项目，从当前大小开始，避免重复
            for (let i = currentSize; i < data.progress; i++) {
              const virtualItemId = `virtual_item_${i}_${Date.now()}`;
              processedItemsRef.current.add(virtualItemId);
            }
            
            console.log(`Updated processedItemsRef size: ${processedItemsRef.current.size}`);
            
            // 更新进度状态
            setProgress(data.progress);
            
            // 更新剩余时间估计
            if (data.progress > 0 && data.total > 0) {
              updateTimeRemaining(data.progress, data.total);
            }
          }
          
          // 验证更新后的状态
          if (processedItemsRef.current.size !== data.progress) {
            console.warn(`Warning: processedItemsRef size (${processedItemsRef.current.size}) does not match progress (${data.progress})`);
            
            // 检测是否是后端重新开始的情况
            if (data.progress < 5 && processedItemsRef.current.size > 20) {
              console.log(`检测到后端可能重新开始处理，保留前端进度并继续累加`);
              
              // 保留前端进度，但更新UI显示以反映实际情况
              const totalProcessed = processedItemsRef.current.size + data.progress;
              
              // 更新UI显示的进度
              setProgress(totalProcessed);
              
              // 更新全局进度变量
              if (window && window.hasOwnProperty('__deepSearchProgress')) {
                (window as any).__deepSearchProgress.progress = totalProcessed;
                (window as any).__deepSearchProgress.total = data.total;
              }
              
              // 更新剩余时间估计
              if (totalProcessed > 0 && data.total > 0) {
                updateTimeRemaining(totalProcessed, data.total);
              }
              
              console.log(`更新显示进度为: ${totalProcessed}/${data.total}`);
            }
            // 正常情况下，只在前端进度小于后端进度时才同步
            else if (processedItemsRef.current.size < data.progress) {
              // 强制同步 - 确保状态一致性
              processedItemsRef.current = new Set(Array.from({ length: data.progress }, (_, i) => `virtual_item_${i}_${Date.now()}`));
              console.log(`Forced sync of processedItemsRef, new size: ${processedItemsRef.current.size}`);
              
              // 更新UI显示的进度
              setProgress(data.progress);
            } else {
              console.log(`前端进度(${processedItemsRef.current.size})大于后端进度(${data.progress})，保留前端进度以避免回退`);
            }
          }
        }
        
        // 计算估计剩余时间
        if (data.progress > 0 && searchStartTimeRef.current > 0) {
          const elapsedTime = Date.now() - searchStartTimeRef.current;
          const avgTimePerItem = elapsedTime / data.progress;
          const remainingItems = data.total - data.progress;
          const estimatedRemainingMs = avgTimePerItem * remainingItems;
          
          // 格式化剩余时间
          let formattedTime = '';
          if (estimatedRemainingMs < TIME_UNITS.MINUTE) {
            formattedTime = `${Math.ceil(estimatedRemainingMs / TIME_UNITS.SECOND)} seconds`;
          } else if (estimatedRemainingMs < TIME_UNITS.HOUR) {
            formattedTime = `${Math.ceil(estimatedRemainingMs / TIME_UNITS.MINUTE)} minutes`;
          } else {
            formattedTime = `${(estimatedRemainingMs / TIME_UNITS.HOUR).toFixed(1)} hours`;
          }
          
          setEstimatedTimeRemaining(formattedTime);
        }
      }
      return;
    }
    
    // 结果消息
    if (messageType === 'result' as SSEMessage['type'] && data.result) {
      setResults(prev => [...prev, data.result]);
      processedItemsRef.current.add(data.result.risk_item);
      return;
    }
    
    // 完成消息
    if (messageType === 'complete' as SSEMessage['type']) {
      console.log('Search completed');
      setIsSearching(false);
      setShowNoEvidence(false); // 搜索完成后隐藏"No Evidence Found"结果
      
      // 重置重连计数
      reconnectCountRef.current = 0;
      
      // 关闭SSE连接
      if (eventSourceRef.current) {
        eventSourceRef.current.close();
        eventSourceRef.current = null;
      }
      if (cleanupFnRef.current) {
        cleanupFnRef.current();
        cleanupFnRef.current = null;
      }
      return;
    }
    
    // 错误消息
    if (messageType === 'error' as SSEMessage['type']) {
      console.error('SSE error:', data.message);
      showErrorAndReset(data.message || 'An error occurred during search');
      return;
    }
  }, [showErrorAndReset, setProgress, setTotalItems, setResults, setIsSearching, setShowNoEvidence, setBatchInfo]);

  // 处理回退到普通HTTP请求
  const handleFallbackToRegularRequest = useCallback((targetInstitution: string) => {
    if (isFallbackInProgressRef.current) return;

    console.log('正在切换到普通HTTP请求...');
    isFallbackInProgressRef.current = true;

    // 获取API基础URL
    const apiBaseUrl = getApiBaseUrl();

    // 使用普通HTTP请求作为备用方案
    fallbackToRegularRequest(
      targetInstitution,
      apiBaseUrl,
      sessionId,
      processedItemsRef.current,
      (newResults, processed, total) => {
        // 添加新结果
        setResults(prev => [...prev, ...newResults]);
        setProgress(processed);
        setTotalItems(total);

        // 更新已处理项目集合
        newResults.forEach(result => {
          processedItemsRef.current.add(result.risk_item);
        });

        setIsSearching(false);
        setShowNoEvidence(false); // 搜索完成后隐藏"No Evidence Found"结果
        isFallbackInProgressRef.current = false;
      },
      (error) => {
        console.error('Fallback request failed:', error);
        showErrorAndReset('Connection to server failed. Please try again later.');
        isFallbackInProgressRef.current = false;
      }
    );
  }, [sessionId, showErrorAndReset]);

  // 获取API基础URL
  const getApiBaseUrl = useCallback(() => {
    console.log('开始构建API基础URL...');
    
    // 1. 先尝试使用环境变量
    let envApiUrl = import.meta.env.VITE_API_BASE_URL;
    let apiBaseUrl = '';

    // 打印环境变量信息
    console.log(`环境变量VITE_API_BASE_URL: ${envApiUrl || '未设置'}`);
    console.log(`当前域名: ${window.location.origin}`);
    console.log(`当前环境: ${import.meta.env.MODE}`);

    // 2. 如果环境变量不存在，则使用相对路径（适用于生产环境）
    if (!envApiUrl) {
      // 在开发环境中，默认使用localhost:5000
      if (import.meta.env.MODE === 'development') {
        apiBaseUrl = 'http://localhost:5000';
        console.log(`开发环境使用默认后端URL: ${apiBaseUrl}`);
      } else {
        // 在生产环境中，使用当前域名
        apiBaseUrl = window.location.origin;
        console.log(`生产环境使用当前域名作为API基础URL: ${apiBaseUrl}`);
      }
    } else {
      // 3. 如果环境变量存在，则使用环境变量的值
      apiBaseUrl = envApiUrl;
      console.log(`使用环境变量的API基础URL: ${apiBaseUrl}`);
    }

    // 4. 确保apiBaseUrl是一个绝对URL
    if (apiBaseUrl && !apiBaseUrl.startsWith('http')) {
      // 如果apiBaseUrl不以http或https开头，添加协议
      if (apiBaseUrl.includes('localhost') || apiBaseUrl.includes('127.0.0.1')) {
        apiBaseUrl = `http://${apiBaseUrl}`;
      } else {
        apiBaseUrl = `https://${apiBaseUrl}`;
      }
      console.log(`添加协议后的API基础URL: ${apiBaseUrl}`);
    }

    // 5. 确保apiBaseUrl不以斜杠结尾
    if (apiBaseUrl.endsWith('/')) {
      apiBaseUrl = apiBaseUrl.slice(0, -1);
      console.log(`移除末尾斜杠后的API基础URL: ${apiBaseUrl}`);
    }

    // 6. 处理特殊情况：Railway平台的URL格式
    if (apiBaseUrl.includes('railway.app')) {
      // 如果是Railway平台，确保使用HTTPS
      if (!apiBaseUrl.startsWith('https://')) {
        apiBaseUrl = apiBaseUrl.replace(/^http:\/\//, 'https://');
        if (!apiBaseUrl.startsWith('https://')) {
          apiBaseUrl = `https://${apiBaseUrl}`;
        }
        console.log(`处理Railway平台URL后: ${apiBaseUrl}`);
      }
    }

    // 7. 处理特殊情况：Vercel平台的URL格式
    if (apiBaseUrl.includes('vercel.app')) {
      // 如果是Vercel平台，确保使用HTTPS
      if (!apiBaseUrl.startsWith('https://')) {
        apiBaseUrl = apiBaseUrl.replace(/^http:\/\//, 'https://');
        if (!apiBaseUrl.startsWith('https://')) {
          apiBaseUrl = `https://${apiBaseUrl}`;
        }
        console.log(`处理Vercel平台URL后: ${apiBaseUrl}`);
      }
    }
    
    // 8. 尝试测试API连接
    console.log(`最终使用的API基础URL: ${apiBaseUrl}`);
    console.log(`将尝试连接到: ${apiBaseUrl}/api/health`);
    
    // 返回最终的API基础URL
    return apiBaseUrl;
  }, []);

  // 开始深度搜索
  const startDeepSearch = useCallback(async (isReconnect: boolean = false) => {
    // 调试当前状态
    console.log(`[Reconnect Debug] startDeepSearch 被调用，当前目标机构: "${institutionA}", isReconnect: ${isReconnect}`);
    debugState();
    
    // 重连时优先使用 institutionARef.current 的值
    let targetInstitution = '';
    
    if (isReconnect && institutionARef.current && institutionARef.current.trim() !== '') {
      // 如果是重连操作且 institutionARef.current 有值，优先使用它
      targetInstitution = institutionARef.current;
      console.log(`[Reconnect Debug] 重连时使用 institutionARef.current = "${targetInstitution}"`);
      
      // 同步到状态，确保 UI 显示正确
      setInstitutionA(targetInstitution);
    } else if (institutionA && institutionA.trim() !== '') {
      // 如果不是重连或 institutionARef.current 为空，使用 institutionA
      targetInstitution = institutionA;
      institutionARef.current = institutionA;
      console.log(`[Reconnect Debug] 更新 institutionARef.current = "${institutionA}"`);
    } else {
      setError('Please enter a target institution name');
      return;
    }
    
    // 如果已经在搜索中且不是重连操作，不重复启动
    if (isSearching && !isReconnect) {
      console.log('搜索已经在进行中，不重复启动');
      return;
    }
    
    // 如果是重连，则不重置状态
    if (!isReconnect) {
      // 重置状态
      setError('');
      setResults([]);
      setProgress(0);
      setTotalItems(0);
      setIsSearching(true);
      // 设置显示"No Evidence Found"的结果
      setShowNoEvidence(true);
      // 记录搜索开始时间
      searchStartTimeRef.current = Date.now();
      // 生成新的会话ID
      const newSessionId = `session_${Date.now()}`;
      setSessionId(newSessionId);
      // 清空已处理项目列表
      processedItemsRef.current.clear();
      // 重置重连计数
      reconnectCountRef.current = 0;
      
      console.log(`新搜索启动，目标机构: "${targetInstitution}", 会话ID: ${newSessionId}`);
    } else {
      console.log(`重连操作，保留当前状态，目标机构: "${targetInstitution}", 会话ID: ${sessionId}, 已处理项目数: ${processedItemsRef.current.size}`);
    }
    
    try {
      // 获取API基础URL
      const apiBaseUrl = getApiBaseUrl();
      
      // 构建请求URL基础部分
      let url;
      
      // 强制使用绝对URL，避免相对路径问题
      // 在开发环境中，直接使用localhost:5000
      if (import.meta.env.MODE === 'development') {
        url = `http://localhost:5000/api/deepsearch?institution_A=${encodeURIComponent(targetInstitution)}`;
        console.log(`开发环境使用固定URL: ${url}`);
      } else {
        // 在生产环境中，使用apiBaseUrl
        // 确保apiBaseUrl不以斜杠结尾
        const baseUrl = apiBaseUrl.endsWith('/') ? apiBaseUrl.slice(0, -1) : apiBaseUrl;
        url = `${baseUrl}/api/deepsearch?institution_A=${encodeURIComponent(targetInstitution)}`;
        console.log(`生产环境使用动态URL: ${url}`);
      }
      
      // 如果是重连，先通过POST请求重新注册会话
      if (isReconnect) {
        console.log(`重连时重新注册会话，目标机构: "${targetInstitution}", 会话ID: ${sessionId}`);
        
        try {
          // 准备注册会话的数据
          const processedArray = Array.from(processedItemsRef.current);
          const sessionData = {
            institution_A: targetInstitution,
            processed: processedArray,
            session_id: sessionId
          };
          
          // 将已处理项目列表存储在localStorage中（作为备份）
          localStorage.setItem(`processed_${sessionId}`, JSON.stringify(processedArray));
          console.log(`重连时已将${processedArray.length}个已处理项目存储在本地`);
          
          // 构建注册会话URL
          let registerUrl;
          if (import.meta.env.MODE === 'development') {
            registerUrl = 'http://localhost:5000/api/register_session';
          } else {
            const baseUrl = apiBaseUrl.endsWith('/') ? apiBaseUrl.slice(0, -1) : apiBaseUrl;
            registerUrl = `${baseUrl}/api/register_session`;
          }
          
          console.log(`尝试注册会话: ${registerUrl}`);
          console.log(`注册数据: 目标机构="${targetInstitution}", 已处理项目=${processedArray.length}, 会话ID=${sessionId}`);
          
          // 发送POST请求注册会话
          const response = await fetch(registerUrl, {
            method: 'POST',
            headers: {
              'Content-Type': 'application/json'
            },
            body: JSON.stringify(sessionData)
          });
          
          if (!response.ok) {
            throw new Error(`注册会话失败: ${response.status}`);
          }
          
          const responseData = await response.json();
          console.log(`注册会话成功: ${JSON.stringify(responseData)}`);
          
          // 使用返回的会话ID（如果有）
          if (responseData.session_id && responseData.session_id !== sessionId) {
            console.log(`服务器返回了新的会话ID: ${responseData.session_id}`);
            setSessionId(responseData.session_id);
          }
          
          // 只传递进度信息，不传递已处理项目列表
          url += `&progress=${processedItemsRef.current.size}`;
          console.log(`传递进度信息: ${processedItemsRef.current.size}`);
          
        } catch (err) {
          console.warn(`重连时注册会话失败:`, err);
          
          // 如果注册失败，使用原始方式传递进度信息
          if (processedItemsRef.current.size > 0) {
            url += `&progress=${processedItemsRef.current.size}`;
            console.log(`传递进度信息: ${processedItemsRef.current.size}`);
          } else if (window && (window as any).__deepSearchProgress && (window as any).__deepSearchProgress.progress > 0) {
            url += `&progress=${(window as any).__deepSearchProgress.progress}`;
            console.log(`传递全局进度信息: ${(window as any).__deepSearchProgress.progress}/${(window as any).__deepSearchProgress.total}`);
          } else {
            url += `&progress=${progress}`;
            console.log(`传递当前进度信息: ${progress}/${totalItems}`);
          }
        }
      }
      
      // 如果有会话ID，则传递会话ID
      if (sessionId) {
        url += `&session_id=${encodeURIComponent(sessionId)}`;
        console.log(`传递会话ID: ${sessionId}`);
      }
      
      // 添加时间戳和随机数防止缓存
      const timestamp = Date.now();
      const randomId = Math.floor(Math.random() * 1000000);
      url += `&_t=${timestamp}&_r=${randomId}`;
      console.log(`[Reconnect Debug] 启动深度搜索，目标机构: "${targetInstitution}", 是否重连: ${isReconnect}, URL: ${url}`);
      console.log(`[Reconnect Debug] 当前 processedItemsRef.current 大小: ${processedItemsRef.current.size}`);
      console.log(`[Reconnect Debug] 当前 institutionARef.current: "${institutionARef.current}"`);
      console.log(`[Reconnect Debug] 当前 sessionId: ${sessionId}`);
      
      // 先检查后端健康状态
      const healthCheckUrl = `${apiBaseUrl}/api/health`;
      console.log(`[Reconnect Debug] 将尝试连接到: ${healthCheckUrl}`);
      
      try {
        // 使用await替代then链式调用
        const response = await fetch(healthCheckUrl);
        console.log(`[Reconnect Debug] 后端健康检查响应: ${response.status}`);
        
        if (!response.ok) {
          throw new Error(`后端健康检查失败: ${response.status}`);
        }
        
        console.log(`[Reconnect Debug] 后端健康检查成功，继续创建SSE连接`);
        console.log(`[Reconnect Debug] 创建SSE连接前再次检查 - processedItems: ${processedItemsRef.current.size}, targetInstitution: "${targetInstitution}"`);
        
        // 检查参数是否有效
        if (!targetInstitution || targetInstitution.trim() === '') {
          console.error(`[Reconnect Debug] 创建SSE连接失败: targetInstitution 为空`);
          setError('目标机构名称为空，无法创建SSE连接');
          setIsSearching(false);
          return;
        }
        
        // 创建SSE连接前记录状态
        console.log(`[Reconnect Debug] 即将创建SSE连接，参数检查:`);
        console.log(`[Reconnect Debug] - targetInstitution: "${targetInstitution}"`);
        console.log(`[Reconnect Debug] - processedItems.size: ${processedItemsRef.current.size}`);
        console.log(`[Reconnect Debug] - sessionId: ${sessionId}`);
        console.log(`[Reconnect Debug] - progress: ${processedItemsRef.current.size}`);
        
        // 创建SSE连接
        const connection = await createSSEConnection({
          institutionA: targetInstitution,
          apiBaseUrl,
          processedItems: processedItemsRef.current,
          sessionId,
          progress: processedItemsRef.current.size, // 传递进度信息
          onMessage: handleSSEMessage,
          onError: (error) => {
            console.error(`[Reconnect Debug] SSE错误: ${error}`);
            setError(`SSE连接错误: ${error}`);
          },
          onFallback: (fallbackInstitution) => {
            console.log(`[Reconnect Debug] SSE连接失败，尝试回退到普通HTTP请求: ${fallbackInstitution}`);
            // 当SSE连接失败时，使用普通HTTP请求作为备用方案
            handleFallbackToRegularRequest(fallbackInstitution);
          }
        });
        
        console.log(`[Reconnect Debug] SSE连接创建成功，保存引用`);
        
        // 保存引用，便于清理
        eventSourceRef.current = connection.eventSource;
        cleanupFnRef.current = connection.cleanup;
        reconnectFnRef.current = connection.reconnect;
        
        // 连接创建后再次检查状态
        console.log('[Reconnect Debug] SSE连接创建后的状态:');
        debugState();
      } catch (error) {
        console.error(`[Reconnect Debug] 健康检查或创建SSE连接时发生异常: ${error.message}`);
        setError(`创建SSE连接失败: ${error.message}`);
        setIsSearching(false);
      }
    } catch (error) {
      console.error('Error setting up SSE connection:', error);
      showErrorAndReset('Failed to start search. Please try again later.');
    }
  }, [institutionA, isSearching, sessionId, handleSSEMessage, handleFallbackToRegularRequest, getApiBaseUrl, showErrorAndReset]);
  
  // 取消搜索
  const cancelSearch = useCallback(() => {
    console.log('Search cancelled by user');
    if (eventSourceRef.current) {
      eventSourceRef.current.close();
      eventSourceRef.current = null;
    }
    if (cleanupFnRef.current) {
      cleanupFnRef.current();
      cleanupFnRef.current = null;
    }
    // 重置重连计数
    reconnectCountRef.current = 0;
    setIsSearching(false);
    // 如果有结果，归档它们
    if (results.length > 0) {
      console.log('Search completed or cancelled, archiving results...');
      setShowNoEvidence(false); // 隐藏"No Evidence Found"结果
    }
  }, [results.length]);
  
  // 组件卸载时清理资源
  useEffect(() => {
    return () => {
      if (eventSourceRef.current) {
        eventSourceRef.current.close();
      }
      if (cleanupFnRef.current) {
        cleanupFnRef.current();
      }
    };
  }, []);
  
  // 自定义setInstitutionA函数，同时更新institutionARef
  const setInstitutionAWithRef = useCallback((value: string) => {
    institutionARef.current = value; // 更新ref
    setInstitutionA(value); // 更新state
  }, []);
  
  // 在组件挂载时同步institutionA和institutionARef
  useEffect(() => {
    institutionARef.current = institutionA;
  }, [institutionA]);
  
  // 返回状态和方法
  return {
    // 状态
    institutionA,
    isSearching,
    progress,
    totalItems,
    results,
    showNoEvidence,
    estimatedTimeRemaining,
    error,
    // 批处理信息
    batchInfo,
    
    // 方法
    setInstitutionA: setInstitutionAWithRef, // 使用新的函数
    startDeepSearch,
    cancelSearch
  };
};

export default useDeepSearch;

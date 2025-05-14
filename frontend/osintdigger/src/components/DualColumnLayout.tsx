import { Separator } from "@/components/ui/separator";
import { Card } from "@/components/ui/card";
import { Label } from "@/components/ui/label";
import { Input } from "@/components/ui/input";
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs";
import { Textarea } from "@/components/ui/textarea";
import { Button } from "@/components/ui/button";
import { Alert, AlertTitle, AlertDescription } from "@/components/ui/alert";
import { ScrollArea } from "@/components/ui/scroll-area";
import { LoaderCircle } from "lucide-react";
import { useNavigate } from "react-router-dom";
import { useState } from "react";
import ResultCard from "./ResultCard";

// 导入 Source 类型，从集中的类型定义文件导入
import { Source } from "@/types";

// 导入月份选择器组件
import { MonthPicker } from "./ui/month-picker";

type InvestigationStatus = 'idle' | 'loading' | 'error' | 'success';

// 与 ResultCard 组件中的 ResultCardProps.result 类型保持一致
type RiskResult = {
  risk_item: string;
  relationship_type: string;
  finding_summary: string;
  potential_intermediary_B?: string | null;
  sources?: Source[]; // 仅使用 Source[] 类型
  // 添加 Google 搜索建议相关字段
  search_metadata?: {
    rendered_content?: string;
    search_queries?: string[];
  };
  // 兼容旧格式
  rendered_content?: string;
  search_queries?: string[];
};

const DualColumnLayout = () => {
  const navigate = useNavigate();
  const [status, setStatus] = useState<InvestigationStatus>('idle');
  const [institution, setInstitution] = useState<string>('');
  const [country, setCountry] = useState<string>('');
  const [riskList, setRiskList] = useState<string>('');
  const [results, setResults] = useState<RiskResult[]>([]);
  const [errorMessage, setErrorMessage] = useState<string>('');
  
  // 添加时间范围状态
  const [timeRangeStart, setTimeRangeStart] = useState<Date | undefined>(undefined);
  const [timeRangeEnd, setTimeRangeEnd] = useState<Date | undefined>(undefined);
  
  // 切换到DeepSearch模式
  const switchToDeepSearch = () => {
    navigate('/deepsearch');
  };

  // 处理开始调查按钮点击事件
  const handleStartInvestigation = async () => {
    // 声明变量来存储超时ID，确保在catch块中可用
    let timeoutId: NodeJS.Timeout | null = null;
    let apiBaseUrl = '';
    
    // 验证输入
    if (!institution || !riskList) {
      setErrorMessage('Please fill in Institution Name and Risk List');
      setStatus('error');
      return;
    }
    
    try {
      // 设置状态为加载中
      setStatus('loading');
      setErrorMessage('');
      
      // 将风险列表按行分割成数组
      const riskItems = riskList.split('\n')
        .map(item => item.trim())
        .filter(item => item.length > 0);
      
      // 准备请求数据
      const requestData: any = {
        institution,
        country: country.trim() || "Worldwide",  // 如果不填写location则默认为"Worldwide"
        risk_list: riskItems,
        enable_grounding: true  // 启用接地搜索功能
      };
      
      // 添加时间范围参数（如果有）
      if (timeRangeStart) {
        requestData.time_range_start = timeRangeStart.toISOString().substring(0, 7); // 格式化为 YYYY-MM
      }
      
      if (timeRangeEnd) {
        requestData.time_range_end = timeRangeEnd.toISOString().substring(0, 7); // 格式化为 YYYY-MM
      }
      
      // 获取API基础URL
      // 1. 先尝试使用环境变量
      let envApiUrl = import.meta.env.VITE_API_BASE_URL;
      
      // 2. 如果环境变量不存在，则使用相对路径（适用于生产环境）
      if (!envApiUrl) {
        // 在生产环境中，前端和后端可能部署在同一个域名下
        // 使用相对路径连接API
        apiBaseUrl = window.location.origin;
        console.log(`使用当前域名作为API基础URL: ${apiBaseUrl}`);
      } else {
        // 3. 如果环境变量存在，则使用环境变量的值
        apiBaseUrl = envApiUrl;
        console.log(`使用环境变量的API基础URL: ${apiBaseUrl}`);
      }
      
      // 4. 确保apiBaseUrl是一个绝对URL
      if (apiBaseUrl && !apiBaseUrl.startsWith('http')) {
        if (apiBaseUrl.includes('localhost') || apiBaseUrl.includes('127.0.0.1')) {
          apiBaseUrl = `http://${apiBaseUrl}`;
        } else {
          apiBaseUrl = `https://${apiBaseUrl}`;
        }
      }
      
      // 记录最终使用的URL
      console.log(`最终使用的API基础URL: ${apiBaseUrl}`);
      
      console.log(`使用API基础URL: ${apiBaseUrl}`);
      console.log('发送请求数据:', requestData);
      
      // 发送请求到后端API
      const apiUrl = `${apiBaseUrl}/api/check_risks`;
      console.log(`发送请求到: ${apiUrl}`);
      console.log('请求数据:', JSON.stringify(requestData));
      
      // Set request timeout - increased to 120 seconds as Gemini API calls may take longer
      const controller = new AbortController();
      console.log('Setting request timeout to 120 seconds');
      timeoutId = setTimeout(() => {
        console.log('Request timeout, aborting...');
        controller.abort();
      }, 120000); // 120 seconds timeout
      
      // Check API status before sending the main request
      try {
        const statusUrl = `${apiBaseUrl}/api/status`;
        console.log(`Checking API status at: ${statusUrl}`);
        const statusResponse = await fetch(statusUrl, {
          method: 'GET',
          mode: 'cors',
          cache: 'no-cache',
          // 添加更多的调试信息
          headers: {
            'X-Client-Info': 'Frontend/1.0',
            'Accept': 'application/json'
          }
        }).catch(error => {
          console.log(`API status check failed: ${error.message}`);
          return null;
        });
        
        if (statusResponse && statusResponse.ok) {
          const statusData = await statusResponse.json();
          console.log(`API status check successful: ${JSON.stringify(statusData)}`);
          console.log(`Connection to backend confirmed at: ${apiBaseUrl}`);
        } else {
          console.log(`API status check failed with status: ${statusResponse?.status || 'No response'}`);
          console.log(`This may indicate CORS or network connectivity issues`);
        }
      } catch (error) {
        console.log(`Error during API status check: ${error}`);
        // Continue with the main request even if status check fails
      }
      
      // Add more debug information
      console.log(`Sending request to: ${apiUrl}`);
      console.log(`Request data: ${JSON.stringify(requestData).substring(0, 200)}...`);
      
      // Implement request retry mechanism with improved error handling
      const fetchWithRetry = async (url: string, options: RequestInit, maxRetries = 3) => {
        let retries = 0;
        let lastError: Error | null = null;
        
        while (retries < maxRetries) {
          try {
            console.log(`Sending request (attempt ${retries + 1}/${maxRetries})`);
            const response = await fetch(url, options);
            
            // Check if the response is ok (status in the range 200-299)
            if (!response.ok) {
              // Try to get more details about the error
              try {
                const errorData = await response.text();
                console.log(`Server responded with status ${response.status}: ${errorData}`);
              } catch (e) {
                console.log(`Server responded with status ${response.status}, but could not read error details`);
              }
              
              // For 4xx errors (except 429 Too Many Requests), don't retry
              if (response.status >= 400 && response.status < 500 && response.status !== 429) {
                console.log(`Client error (${response.status}), not retrying`);
                return response; // Return the error response to be handled by the caller
              }
              
              // For other errors, retry
              throw new Error(`HTTP error: ${response.status}`);
            }
            
            return response;
          } catch (error) {
            lastError = error as Error;
            retries++;
            
            // Categorize the error
            let errorType = "Unknown error";
            if (error.name === "AbortError") {
              errorType = "Timeout error";
            } else if (error.name === "TypeError" && error.message === "Failed to fetch") {
              errorType = "Network error (CORS or connectivity issue)";
            }
            
            console.log(`Request failed, ${errorType}: ${error.message}`);
            console.log(`Retrying (${retries}/${maxRetries})...`);
            
            if (retries === maxRetries) {
              console.log('All retry attempts failed');
              throw lastError;
            }
            
            // Wait before retrying, increasing wait time with each retry
            const waitTime = 1000 * retries;
            console.log(`Waiting ${waitTime}ms before next retry...`);
            await new Promise(resolve => setTimeout(resolve, waitTime));
          }
        }
        
        // If all retries fail, throw the last error
        throw lastError;
      };
      
      // 简化请求配置
      const requestOptions = {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Accept': 'application/json',
        },
        body: JSON.stringify(requestData),
        mode: 'cors' as RequestMode,
        credentials: 'omit' as RequestCredentials,
        signal: controller.signal,
        cache: 'no-cache' as RequestCache,
      };
      
      console.log('使用简化的请求配置发送请求');
      const response = await fetchWithRetry(apiUrl, requestOptions, 3);
      
      // 清除超时计时器
      clearTimeout(timeoutId);
      timeoutId = null;
      
      console.log(`收到响应状态码: ${response.status}`);
      
      // 检查响应状态
      if (!response.ok) {
        let errorMessage = `请求失败: ${response.status} ${response.statusText}`;
        console.error(`API请求失败: ${response.status} ${response.statusText}`);
        
        // 记录响应头部信息以便调试
        const headers = {};
        response.headers.forEach((value, key) => {
          headers[key] = value;
        });
        console.error('响应头部:', headers);
        
        try {
          const errorData = await response.json();
          console.error('错误详情:', errorData);
          if (errorData && errorData.error) {
            errorMessage = errorData.error;
          }
        } catch (e) {
          // 如果无法解析JSON，尝试获取原始文本
          try {
            const textResponse = await response.text();
            console.error('原始错误响应:', textResponse);
            if (textResponse) {
              errorMessage += ` - ${textResponse.substring(0, 100)}`;
            }
          } catch (textError) {
            console.error('无法获取响应文本:', textError);
          }
        }
        throw new Error(errorMessage);
      } else {
        console.log('请求成功，正在解析响应数据...');
      }
      
      // 尝试解析响应数据
      let responseData;
      try {
        responseData = await response.json();
        console.log('API原始返回数据:', responseData);
      } catch (jsonError) {
        console.error('解析JSON响应失败:', jsonError);
        // 尝试获取原始文本
        const textResponse = await response.text();
        console.log('原始响应文本:', textResponse);
        throw new Error(`无法解析响应数据: ${jsonError.message}`);
      }
      
      // 处理API返回的数据
      const processedData: RiskResult[] = Array.isArray(responseData) ? responseData.map(item => {
        // 创建一个新的结果对象，默认包含所有必需字段
        const resultItem: RiskResult = {
          risk_item: item.risk_item || '',
          relationship_type: item.relationship_type || '',
          finding_summary: item.finding_summary || '',
          potential_intermediary_B: item.potential_intermediary_B || null
        };
        
        // 处理 Google 搜索建议相关字段
        if (item.search_metadata) {
          resultItem.search_metadata = item.search_metadata;
        } else if (item.rendered_content || item.search_queries) {
          // 兼容旧格式
          resultItem.rendered_content = item.rendered_content;
          resultItem.search_queries = item.search_queries;
        }
        
        // 处理 sources 字段
        if (item.sources && Array.isArray(item.sources)) {
          // 将每个字符串URL转换为Source对象
          resultItem.sources = item.sources.map((url: string | Source, index: number): Source => {
            // 如果已经是 Source 对象，则直接返回
            if (typeof url !== 'string') {
              return url;
            }
            // 否则，将字符串转换为 Source 对象
            return {
              url: url,
              status: 'ok',
              index: index,
              // 默认不设置 title 和 description，这些将在解析 URL 时获取
              title: undefined,
              description: undefined
            };
          });
        } else {
          // 如果没有 sources 或不是数组，设置为空数组
          resultItem.sources = [];
        }
        
        return resultItem;
      }) : [];
      
      console.log("处理后的数据:", processedData);
      
      // 更新状态和结果
      setResults(processedData);
      setStatus('success');
    } catch (err) {
      console.error('调查失败:', err);
      
      // 清除超时计时器（如果存在）
      if (timeoutId) {
        clearTimeout(timeoutId);
        timeoutId = null;
      }
      
      // 添加更详细的错误信息
      if (err instanceof TypeError && err.message.includes('Failed to fetch')) {
        setErrorMessage(`无法连接到后端服务器(${apiBaseUrl})。请确保后端服务正在运行，并检查网络连接。`);
        
        // 尝试发送一个简单的请求来测试连接
        // 先测试当前域名下的健康检查端点
        fetch(`${window.location.origin}/health`, { 
          mode: 'no-cors',
          cache: 'no-cache' 
        })
          .then(resp => {
            console.log('当前域名健康检查结果:', resp.status);
          })
          .catch(e => {
            console.error('当前域名健康检查失败:', e);
            
            // 如果当前域名下的健康检查失败，尝试直接访问配置的API URL
            fetch(`${apiBaseUrl}/health`, { 
              mode: 'no-cors',
              cache: 'no-cache' 
            })
              .then(resp => {
                console.log('配置API URL健康检查结果:', resp.status);
              })
              .catch(e2 => {
                console.error('配置API URL完全不可访问:', e2);
              });
          });
          
        // 记录当前网络状态
        console.log('当前网络状态:', navigator.onLine ? '在线' : '离线');
        console.log('当前页面URL:', window.location.href);
        console.log('当前域名:', window.location.origin);
        
      } else if (err.name === 'AbortError') {
        setErrorMessage('请求超时。请检查网络连接或稍后重试。');
      } else {
        setErrorMessage(err instanceof Error ? err.message : '未知错误');
      }
      setStatus('error');
      setResults([]);
    }
  };


  return (
    <div className="min-h-screen bg-gray-50">
      <div className="container mx-auto">
        <div className="flex flex-col md:flex-row">
          {/* Left Column */}
          <div className="w-full md:w-2/5 p-6 bg-white rounded-l-lg">
            <div className="space-y-6">
              <Card className="p-4">
                <h3 className="text-lg font-semibold text-gray-800 mb-4">Target Information</h3>
                <div className="space-y-4">
                  <div className="space-y-2">
                    <Label htmlFor="institution">Target Institution Name</Label>
                    <Input 
                      id="institution" 
                      placeholder="Enter institution name..."
                      value={institution}
                      onChange={(e) => setInstitution(e.target.value)}
                    />
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="country">Location/Country</Label>
                    <Input 
                      id="country" 
                      placeholder="Enter country or location..."
                      value={country}
                      onChange={(e) => setCountry(e.target.value)}
                    />
                  </div>
                  
                  {/* Time Range Selector */}
                  <div className="grid grid-cols-2 gap-4 pt-2">
                    <MonthPicker
                      date={timeRangeStart}
                      setDate={setTimeRangeStart}
                      label="Start Date"
                      placeholder="Select Start Month"
                    />
                    <MonthPicker
                      date={timeRangeEnd}
                      setDate={setTimeRangeEnd}
                      label="End Date"
                      placeholder="Select End Month"
                    />
                  </div>
                  
                  {/* Time Range Hint */}
                  {(timeRangeStart || timeRangeEnd) && (
                    <div className="text-xs text-muted-foreground">
                      {timeRangeStart && timeRangeEnd ? 
                        `Search Range: ${timeRangeStart.toISOString().substring(0, 7)} to ${timeRangeEnd.toISOString().substring(0, 7)}` :
                        timeRangeStart ? 
                          `Start Date: ${timeRangeStart.toISOString().substring(0, 7)}` : 
                          `End Date: ${timeRangeEnd?.toISOString().substring(0, 7)}`
                      }
                    </div>
                  )}
                </div>
              </Card>

              <Separator className="my-6" />

              <Card className="p-4">
                <h3 className="text-lg font-semibold text-gray-800 mb-4">Provide Risk List / Keywords</h3>
                <Tabs defaultValue="paste" className="w-full">
                  <TabsList className="w-full">
                    <TabsTrigger value="paste" className="flex-1">Paste Text</TabsTrigger>
                    <TabsTrigger value="upload" className="flex-1">Upload .txt File</TabsTrigger>
                  </TabsList>
                  <TabsContent value="paste" className="mt-4">
                    <div className="space-y-2">
                      <Label htmlFor="risk-list">Paste list (one item per line)</Label>
                      <Textarea 
                        id="risk-list"
                        placeholder="Paste your list here, one item per line..."
                        className="h-32 resize-none"
                        value={riskList}
                        onChange={(e) => setRiskList(e.target.value)}
                      />
                    </div>
                  </TabsContent>
                  <TabsContent value="upload" className="mt-4">
                    <div className="space-y-3">
                      <Button variant="outline" className="w-full">
                        Select .txt File
                      </Button>
                      <p className="text-sm text-muted-foreground text-center">
                        Upload a .txt file with one item per line.
                      </p>
                    </div>
                  </TabsContent>
                </Tabs>
              </Card>

              <Separator className="my-6" />

              <Card className="p-4">
                <h2 className="text-lg font-semibold text-gray-800 mb-2">Action Section</h2>
                <Button 
                  className="w-full mt-4"
                  disabled={status === 'loading' || !institution || !riskList}
                  onClick={handleStartInvestigation}
                >
                  {status === 'loading' ? 'Processing...' : 'Start Investigation'}
                </Button>
                
                <div className="mt-4 pt-4 border-t border-gray-200">
                  <h3 className="text-sm font-medium text-gray-700 mb-2">Advanced Options</h3>
                  <Button 
                    variant="outline" 
                    className="w-full"
                    onClick={switchToDeepSearch}
                  >
                    Switch to DeepSearch Mode
                  </Button>
                  <p className="text-xs text-gray-500 mt-1">分析目标机构与Named Research Organizations的关系</p>
                </div>
              </Card>
            </div>
          </div>

          {/* Right Column */}
          <div className="w-full md:flex-grow p-6 bg-white md:border-l border-gray-200 rounded-r-lg flex flex-col">
            <h3 className="text-xl font-semibold text-gray-800 mb-4">Investigation Results</h3>
            
            <ScrollArea className="flex-grow">
              <div className="h-full">
                {status === 'idle' && (
                  <p className="text-muted-foreground">
                    Enter details on the left and click 'Start Investigation' to see results.
                  </p>
                )}

                {status === 'loading' && (
                  <div className="h-full flex flex-col items-center justify-center gap-4">
                    <LoaderCircle className="h-8 w-8 animate-spin" />
                    <p className="text-muted-foreground">Investigation in progress...</p>
                  </div>
                )}

                {status === 'error' && (
                  <Alert variant="destructive">
                    <AlertTitle>Investigation Failed</AlertTitle>
                    <AlertDescription>{errorMessage}</AlertDescription>
                  </Alert>
                )}

                {status === 'success' && (
                  <div className="space-y-4">
                    {results.map((result, index) => (
                      <ResultCard 
                        key={index} 
                        result={result} 
                      />
                    ))}
                  </div>
                )}
              </div>
            </ScrollArea>
          </div>
        </div>
      </div>
    </div>
  );
};

export default DualColumnLayout;

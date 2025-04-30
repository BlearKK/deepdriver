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
import { useState } from "react";
import ResultCard from "./ResultCard";

// 导入 Source 类型，确保与 ResultCard 组件使用相同的类型定义
import { Source } from "./ResultCard";

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
  const [status, setStatus] = useState<InvestigationStatus>('idle');
  const [institution, setInstitution] = useState<string>('');
  const [country, setCountry] = useState<string>('');
  const [riskList, setRiskList] = useState<string>('');
  const [results, setResults] = useState<RiskResult[]>([]);
  const [errorMessage, setErrorMessage] = useState<string>('');

  // 处理开始调查按钮点击事件
  const handleStartInvestigation = async () => {
    // 验证输入
    if (!institution || !country || !riskList) {
      setErrorMessage('请填写所有必填字段');
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
      const requestData = {
        institution,
        country,
        risk_list: riskItems
      };
      
      // 发送请求到后端API
      const response = await fetch('http://localhost:5000/api/check_risks', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(requestData)
      });
      
      // 检查响应状态
      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.error || '请求失败');
      }
      
      // 解析响应数据
      const data = await response.json();

      // 调试日志：打印API原始返回内容及sources情况
      console.log("【API原始返回】", data);
      
      // 处理API返回的数据，将字符串数组sources转换为Source对象数组
      const processedData: RiskResult[] = Array.isArray(data) ? data.map(item => {
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
      
      console.log("【处理后的数据】", processedData);
      
      // 更新状态和结果
      setResults(processedData);
      setStatus('success');
    } catch (error) {
      console.error('调查失败:', error);
      setErrorMessage(error instanceof Error ? error.message : '未知错误');
      setStatus('error');
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
                <h3 className="text-lg font-semibold text-gray-800 mb-4">Target Institution Information</h3>
                <div className="space-y-2">
                  <Label htmlFor="institution-name">Target Institution Name</Label>
                  <Input
                    id="institution-name"
                    placeholder="Enter full institution name"
                    className="mb-4"
                    value={institution}
                    onChange={(e) => setInstitution(e.target.value)}
                  />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="country-region">Country/Region</Label>
                  <Input
                    id="country-region"
                    placeholder="Enter country or region"
                    value={country}
                    onChange={(e) => setCountry(e.target.value)}
                  />
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
                  disabled={status === 'loading' || !institution || !country || !riskList}
                  onClick={handleStartInvestigation}
                >
                  {status === 'loading' ? 'Processing...' : 'Start Investigation'}
                </Button>
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

import React, { useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '../ui/card';
import { Progress } from '../ui/progress';
import { Input } from '../ui/input';
import { Button } from '../ui/button';
import { Accordion, AccordionContent, AccordionItem, AccordionTrigger } from '../ui/accordion';
import { Badge } from '../ui/badge';
import { ScrollArea } from '../ui/scroll-area';
import { ArrowLeft } from 'lucide-react';
import { DeepSearchProps } from './types';
import useDeepSearch from './hooks/useDeepSearch';
import { RELATIONSHIP_COLORS } from './constants';

/**
 * DeepSearch组件 - 用于批量分析目标机构与Named Research Organizations的关系
 */
const DeepSearch: React.FC<DeepSearchProps> = ({ onClose }) => {
  const navigate = useNavigate();
  
  // 返回普通搜索模式
  const exitDeepSearchMode = () => {
    navigate('/');
  };
  // 使用自定义Hook获取状态和方法
  const {
    institutionA,
    isSearching,
    progress,
    totalItems,
    results,
    showNoEvidence,
    estimatedTimeRemaining,
    error,
    setInstitutionA,
    startDeepSearch,
    cancelSearch
  } = useDeepSearch();
  
  // 统计不同关系类型的数量
  const relationshipCounts = results.reduce((counts, result) => {
    const type = result.relationship_type;
    counts[type] = (counts[type] || 0) + 1;
    return counts;
  }, {} as Record<string, number>);
  
  // 计算进度百分比
  const progressPercent = totalItems > 0 ? (progress / totalItems) * 100 : 0;

  return (
    <div className="min-h-screen bg-gray-50">
      <div className="container mx-auto py-6">
        {/* 顶部导航栏 */}
        <div className="mb-4 flex items-center px-4">
          <Button 
            variant="ghost" 
            size="sm" 
            className="flex items-center gap-1 text-gray-600 hover:text-gray-900"
            onClick={exitDeepSearchMode}
          >
            <ArrowLeft className="h-4 w-4" />
            Return to Normal Search
          </Button>
          <h1 className="text-xl font-bold ml-4">DeepSearch Mode</h1>
        </div>
        
        <div className="flex flex-col md:flex-row gap-6 rounded-lg overflow-hidden shadow-sm">
          {/* 左侧面板 - 目标信息 */}
          <div className="w-full md:w-1/3 p-6 bg-white rounded-l-lg">
            <h2 className="text-lg font-semibold text-gray-800 mb-4">Target Information</h2>
            
            <div className="mb-4">
              <label className="block text-sm font-medium mb-1">Target Institution Name</label>
              <Input 
                value={institutionA}
                onChange={(e) => setInstitutionA(e.target.value)}
                placeholder="Enter target institution name"
                disabled={isSearching}
                className="w-full"
              />
            </div>
            
            {/* NRO提示卡片 */}
            <Card className="mt-4 bg-blue-50 border-blue-200">
              <CardContent className="p-3">
                <p className="text-blue-800 text-sm">
                  Currently performing batch search of Named Research Organizations (NRO). Results will be displayed in real-time on the right.
                </p>
              </CardContent>
            </Card>
            
            <div className="mt-6 space-y-2">
              <Button 
                onClick={(e) => isSearching ? cancelSearch() : startDeepSearch()}
                disabled={!institutionA.trim()}
                className="w-full"
              >
                {isSearching ? 'Searching...' : 'Start Deep Search'}
              </Button>
              
              {isSearching && (
                <Button 
                  onClick={cancelSearch}
                  variant="outline"
                  className="w-full"
                >
                  Cancel Search
                </Button>
              )}
              
              <Button 
                onClick={exitDeepSearchMode} 
                variant="outline"
                className="w-full"
              >
                Return to Normal Search
              </Button>
            </div>
          
          {/* 关系类型统计 */}
          {results.length > 0 && (
            <div className="mt-6 border-t pt-4">
              <h3 className="text-sm font-medium mb-2">Results by Relationship Type</h3>
              <div className="space-y-1 text-sm">
                {Object.keys(relationshipCounts).map(type => (
                  <div key={type} className="flex justify-between text-sm">
                    <span>{type}:</span>
                    <span>{relationshipCounts[type]}</span>
                  </div>
                ))}
              </div>
            </div>
          )}
          </div>
          
          {/* 右侧面板 - 搜索结果 */}
          <div className="w-full md:flex-grow p-6 bg-white md:border-l border-gray-200 rounded-r-lg flex flex-col">
            <h3 className="text-xl font-semibold text-gray-800 mb-4">DeepSearch Results</h3>
            
            {/* 进度条 */}
            <div className="mb-6">
              {isSearching && (
                <>
                  <div className="flex justify-between text-sm mb-1">
                    <span>Completed: {progress}/{totalItems}</span>
                    <span>{Math.round(progressPercent)}%</span>
                  </div>
                  <Progress value={progressPercent} className="h-2" />
                  {estimatedTimeRemaining && (
                    <div className="text-xs text-gray-500 mt-1">
                      Estimated time remaining: {estimatedTimeRemaining}
                    </div>
                  )}
                </>
              )}
            </div>
            
            <ScrollArea className="flex-grow">
              {/* 结果显示区域 */}
              <div className="space-y-4 min-h-[400px]">
                {/* 有关系的结果（Direct/Indirect/Significant Mention）归档显示 */}
                <Accordion type="multiple" className="space-y-2">
                  {['Direct', 'Indirect', 'Significant Mention'].map(relType => {
                    const filteredResults = results.filter(r => r.relationship_type === relType);
                    if (filteredResults.length === 0) return null;
                    
                    return (
                      <div key={relType} className="animate-fadeIn">
                        <AccordionItem value={relType} className="border rounded-md overflow-hidden">
                          <AccordionTrigger className="px-4 py-2 hover:no-underline hover:bg-gray-50">
                            <div className="flex items-center gap-2">
                              <Badge className={`${RELATIONSHIP_COLORS[relType]} px-2 py-0.5`}>
                                {relType}
                              </Badge>
                              <span className="font-medium">{filteredResults.length} Result{filteredResults.length !== 1 ? 's' : ''}</span>
                            </div>
                          </AccordionTrigger>
                          <AccordionContent>
                            <div className="p-2 space-y-3">
                              {filteredResults.map((result, index) => (
                                <div 
                                  key={index} 
                                  className="animate-fadeIn" 
                                  style={{ animationDelay: `${index * 100}ms` }}
                                >
                                  <Card className="border shadow-sm">
                                    <CardHeader className="p-3 pb-1">
                                      <CardTitle className="text-base">{result.risk_item}</CardTitle>
                                    </CardHeader>
                                    
                                    {result.finding_summary && (
                                      <CardContent className="p-3 pt-0">
                                        <Accordion type="single" collapsible>
                                          <AccordionItem value="details">
                                            <AccordionTrigger className="text-sm py-1">View Details</AccordionTrigger>
                                            <AccordionContent>
                                              <p className="text-sm whitespace-pre-line">{result.finding_summary}</p>
                                            </AccordionContent>
                                          </AccordionItem>
                                        </Accordion>
                                      </CardContent>
                                    )}
                                  </Card>
                                </div>
                              ))}
                            </div>
                          </AccordionContent>
                        </AccordionItem>
                      </div>
                    );
                  })}
                </Accordion>
                
                {/* 无关系的结果（No Evidence Found）直接显示 - 只在搜索中或showNoEvidence为true时显示 */}
                {showNoEvidence && results.filter(r => r.relationship_type === 'No Evidence Found').map((result, index) => (
                  <div
                    key={`no-evidence-${index}`}
                    className="animate-fadeIn"
                    style={{ animationDelay: `${index * 50}ms` }}
                  >
                    <Card className="border shadow-sm">
                      <CardHeader className="p-3 pb-1 flex flex-row justify-between items-center">
                        <CardTitle className="text-base">{result.risk_item}</CardTitle>
                        <Badge className={RELATIONSHIP_COLORS[result.relationship_type] || ''}>
                          {result.relationship_type}
                        </Badge>
                      </CardHeader>
                    </Card>
                  </div>
                ))}
                
                {/* 搜索中显示的内容 */}
                {isSearching && results.length === 0 && (
                  <div className="text-center py-8 text-gray-500">
                    Analyzing, please wait...
                  </div>
                )}
                
                {/* 当没有结果时显示的内容 */}
                {!isSearching && results.length === 0 && (
                  <div className="text-center py-8 text-gray-500">
                    Enter target institution name and click "Start Deep Search" to begin analysis
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

export default DeepSearch;

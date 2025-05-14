import React from 'react';
import { useNavigate } from 'react-router-dom';
import { Card, CardContent } from './ui/card';
import { Progress } from './ui/progress';
import { Input } from './ui/input';
import { Button } from './ui/button';
import { Accordion, AccordionContent, AccordionItem, AccordionTrigger } from './ui/accordion';
import { Badge } from './ui/badge';
import { ScrollArea } from './ui/scroll-area';
import { RELATIONSHIP_COLORS } from './DeepSearch/constants';
import { SearchResult, DeepSearchProps } from './DeepSearch/types';
import useDeepSearch from './DeepSearch/hooks/useDeepSearch';

/**
 * DeepSearch组件 - 用于批量分析目标机构与Named Research Organizations的关系
 * 简洁版UI，与原始截图保持一致
 */
const DeepSearch: React.FC<DeepSearchProps> = ({ onClose }) => {
  const navigate = useNavigate();
  
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

  return (
    <div className="container mx-auto p-4">
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {/* 左侧面板 - 目标信息 */}
        <div>
          <h2 className="text-lg font-semibold mb-3">Target Information</h2>
          
          <div className="mb-4">
            <label className="block text-sm font-medium mb-1">Target Institution Name</label>
            <Input 
              value={institutionA}
              onChange={(e) => setInstitutionA(e.target.value)}
              placeholder="e.g. Sharif University of Technology"
              disabled={isSearching}
              className="w-full"
            />
          </div>
          
          <div className="bg-blue-50 border border-blue-200 p-3 rounded-md mb-4 text-sm">
            Currently performing batch search of Named Research Organizations (NRO). Results will be displayed in real-time on the right.
          </div>
          
          <div className="space-y-2">
            <Button 
              onClick={(e) => isSearching ? cancelSearch() : startDeepSearch()}
              className={`w-full ${isSearching ? 'bg-red-600 hover:bg-red-700' : 'bg-blue-600 hover:bg-blue-700'}`}
            >
              {isSearching ? 'Cancel Search' : 'Start Deep Search'}
            </Button>
            
            {onClose && (
              <Button 
                onClick={onClose} 
                variant="outline" 
                className="w-full"
              >
                Return to Normal Search
              </Button>
            )}
          </div>
          
          {/* 关系类型统计 */}
          {results.length > 0 && (
            <div className="mt-6">
              <h3 className="text-sm font-medium mb-2">Results by Relationship Type</h3>
              <div className="space-y-1">
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
        <div>
          <h2 className="text-lg font-semibold mb-3">DeepSearch Results</h2>
          
          {/* 进度显示 */}
          {isSearching && (
            <div className="mb-4 space-y-2">
              <Progress value={Math.round((progress / totalItems) * 100)} className="h-2" />
              <div className="flex justify-between text-sm">
                <span>Completed: {progress} / {totalItems}</span>
                <span>{Math.round((progress / totalItems) * 100)}%</span>
              </div>
              {estimatedTimeRemaining && (
                <div className="text-xs text-gray-500 text-center">
                  Estimated time remaining: {estimatedTimeRemaining}
                </div>
              )}
            </div>
          )}
          
          {/* 结果显示区域 */}
          <div className="space-y-3">
            {/* 按关系类型分组显示结果 */}
            {Object.keys(relationshipCounts)
              .filter(type => type !== 'No Evidence Found')
              .map(relType => {
                const filteredResults = results.filter(r => r.relationship_type === relType);
                
                return filteredResults.length > 0 ? (
                  <Accordion type="single" collapsible className="w-full" key={relType}>
                    <AccordionItem value="item-1" className="border rounded-md overflow-hidden">
                      <AccordionTrigger className="px-3 py-2 hover:no-underline">
                        <div className="flex items-center gap-2">
                          <Badge className={`${RELATIONSHIP_COLORS[relType]} px-2 py-0.5`}>
                            {relType}
                          </Badge>
                          <span>{filteredResults.length} Result{filteredResults.length !== 1 ? 's' : ''}</span>
                        </div>
                      </AccordionTrigger>
                      <AccordionContent>
                        <div className="space-y-2 p-2">
                          {filteredResults.map((result, index) => (
                            <div key={`${result.risk_item}-${index}`} className="border rounded-md p-3">
                              <div className="font-medium">{result.risk_item}</div>
                              {result.finding_summary && (
                                <Accordion type="single" collapsible className="mt-2">
                                  <AccordionItem value="details">
                                    <AccordionTrigger className="text-sm py-1">View Details</AccordionTrigger>
                                    <AccordionContent>
                                      <p className="text-sm whitespace-pre-line">{result.finding_summary}</p>
                                    </AccordionContent>
                                  </AccordionItem>
                                </Accordion>
                              )}
                            </div>
                          ))}
                        </div>
                      </AccordionContent>
                    </AccordionItem>
                  </Accordion>
                ) : null;
              })}
            
            {/* 无关系的结果（No Evidence Found）- 只在搜索中或showNoEvidence为true时显示 */}
            {showNoEvidence && relationshipCounts['No Evidence Found'] > 0 && (
              <div className="border rounded-md p-3">
                <div className="flex justify-between items-center">
                  <span className="font-medium">No Evidence Found</span>
                  <span>{relationshipCounts['No Evidence Found']} results</span>
                </div>
              </div>
            )}
            
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
        </div>
      </div>
    </div>
  );
};

export default DeepSearch;

import React from 'react';
import { Accordion, AccordionContent, AccordionItem, AccordionTrigger } from '../../ui/accordion';
import { Badge } from '../../ui/badge';
import { ScrollArea } from '../../ui/scroll-area';
import { RELATIONSHIP_COLORS } from '../constants';
import { SearchResult } from '../types';
import ResultCard from './ResultCard';

interface ResultsDisplayProps {
  results: SearchResult[];
  isSearching: boolean;
  showNoEvidence: boolean;
}

const ResultsDisplay: React.FC<ResultsDisplayProps> = ({
  results,
  isSearching,
  showNoEvidence
}) => {
  // 按关系类型分组结果
  const groupedResults = results.reduce((groups, result) => {
    // 如果是"No Evidence Found"且不显示这类结果，则跳过
    if (result.relationship_type === 'No Evidence Found' && !showNoEvidence && !isSearching) {
      return groups;
    }
    
    // 将结果添加到对应的分组中
    if (!groups[result.relationship_type]) {
      groups[result.relationship_type] = [];
    }
    groups[result.relationship_type].push(result);
    return groups;
  }, {} as Record<string, SearchResult[]>);
  
  // 获取所有关系类型（除了"No Evidence Found"）
  const relationshipTypes = Object.keys(groupedResults).filter(
    type => type !== 'No Evidence Found'
  );
  
  // 获取"No Evidence Found"结果
  const noEvidenceResults = groupedResults['No Evidence Found'] || [];
  
  return (
    <ScrollArea className="h-[calc(100vh-220px)]">
      <div className="p-4 space-y-4">
        {/* 按关系类型分组显示结果 */}
        {relationshipTypes.length > 0 && (
          <Accordion type="multiple" className="space-y-2">
            {relationshipTypes.map(relType => {
              const filteredResults = groupedResults[relType] || [];
              
              return filteredResults.length > 0 ? (
                <div key={relType} className="animate-fadeIn">
                  <AccordionItem value={relType} className="border rounded-lg">
                    <AccordionTrigger className="px-4 py-2 hover:no-underline">
                      <div className="flex items-center gap-2">
                        <Badge className={RELATIONSHIP_COLORS[relType] || 'bg-gray-100 text-gray-800 border-gray-300'}>
                          {relType}
                        </Badge>
                        <span className="font-medium">{filteredResults.length} Results</span>
                      </div>
                    </AccordionTrigger>
                    <AccordionContent>
                      <div className="p-2 space-y-3">
                        {filteredResults.map((result, index) => (
                          <ResultCard 
                            key={`${result.risk_item}-${index}`} 
                            result={result} 
                            index={index}
                          />
                        ))}
                      </div>
                    </AccordionContent>
                  </AccordionItem>
                </div>
              ) : null;
            })}
          </Accordion>
        )}
        
        {/* 无关系的结果（No Evidence Found）直接显示 - 只在搜索中或showNoEvidence为true时显示 */}
        {showNoEvidence && noEvidenceResults.map((result, index) => (
          <ResultCard 
            key={`no-evidence-${index}`} 
            result={result} 
            index={index}
          />
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
  );
};

export default ResultsDisplay;

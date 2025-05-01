import { ExternalLink, RefreshCw, Info, AlertTriangle } from "lucide-react";
import { 
  Card, 
  CardContent, 
  CardHeader, 
  CardTitle,
  CardDescription,
  CardFooter
} from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import GoogleSearchSuggestion from "./GoogleSearchSuggestion";
import "./GoogleSearchSuggestion.css";
import { useState, useEffect, useMemo } from "react";
import axios from "axios";
import { Source } from '@/types';

// Import the custom hook and types
import { useSanctions, MatchLevel, MatchResult, SanctionEntity } from '@/hooks/useSanctions';
import SourceList from './SourceList';

interface ResultCardProps {
  result: {
    risk_item: string;
    relationship_type: string;
    finding_summary: string;
    potential_intermediary_B?: string | null;
    institution_a?: string; // 添加 Institution A 字段
    institution_c?: string; // 添加 Institution C 字段
    target_institution_name?: string; // 添加 Target Institution Name 字段
    sources?: Source[]; 
    // 添加 Google 搜索建议相关字段 - 新格式
    search_metadata?: {
      rendered_content?: string;
      search_queries?: string[];
    };
    // 兼容旧格式
    rendered_content?: string;
    search_queries?: string[];
  };
}

// 安全地处理文本内容，移除可能导致React渲染错误的数字引用
const sanitizeText = (text: string | null | undefined): string => {
  if (!text) return "";
  try {
    // 将[数字]或[数字1, 数字2, ...]格式替换为安全文本
    return text.replace(/\[(\d+(?:,\s*\d+)*)\]/g, '(引用$1)');
  } catch (error) {
    console.error("Error sanitizing text:", error);
    return "Error processing text";
  }
};

const ResultCard = ({ result: initialResult }: ResultCardProps) => {
  // 添加错误状态
  const [hasError, setHasError] = useState(false);
  
  // 错误处理函数
  useEffect(() => {
    const handleError = () => {
      setHasError(true);
      console.error("Error detected in ResultCard component");
    };
    
    // 尝试捕获任何渲染错误
    try {
      if (initialResult && typeof initialResult === 'object') {
        // 验证关键属性
        if (initialResult.finding_summary && 
            typeof initialResult.finding_summary === 'string' && 
            initialResult.finding_summary.includes('[')) {
          console.warn("Finding summary contains potentially problematic brackets:", 
                      initialResult.finding_summary.substring(0, 100));
        }
      }
    } catch (error) {
      handleError();
    }
  }, [initialResult]);
  
  // 如果发生错误，显示降级UI
  if (hasError) {
    return (
      <Card className="w-full">
        <CardHeader>
          <CardTitle className="text-xl">{initialResult?.risk_item || "Unknown Risk Item"}</CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-red-500">An error occurred while displaying this result. The data may contain formatting issues.</p>
          <Button 
            variant="outline" 
            onClick={() => setHasError(false)}
            className="mt-2"
          >
            Try Again
          </Button>
        </CardContent>
      </Card>
    );
  }
  // 使用内部状态管理 result，以便于更新 UI
  const [result, setResult] = useState(() => {
    try {
      // 深度复制并清理initialResult对象
      const cleanedResult = {...initialResult};
      
      // 处理finding_summary
      if (cleanedResult.finding_summary) {
        cleanedResult.finding_summary = sanitizeText(cleanedResult.finding_summary);
      }
      
      // 处理其他可能包含问题字符的字段
      if (cleanedResult.risk_item) {
        cleanedResult.risk_item = sanitizeText(cleanedResult.risk_item);
      }
      
      if (cleanedResult.relationship_type) {
        cleanedResult.relationship_type = sanitizeText(cleanedResult.relationship_type);
      }
      
      if (cleanedResult.potential_intermediary_B) {
        cleanedResult.potential_intermediary_B = sanitizeText(cleanedResult.potential_intermediary_B);
      }
      
      return cleanedResult;
    } catch (error) {
      console.error("Error initializing result state:", error);
      // 返回一个安全的默认对象
      return {
        risk_item: initialResult?.risk_item || "Unknown Risk Item",
        relationship_type: "Unknown",
        finding_summary: "Error processing data",
        sources: []
      };
    }
  });

  // Use the custom hook to get sanctions data
  const { sanctionsSet, checkEntitySanctioned, checkMultipleEntities, isDefiniteMatch, isLoading: sanctionsLoading, error: sanctionsError } = useSanctions();

  // Log loading/error status for sanctions (optional)
  useEffect(() => {
    if (sanctionsLoading) {
      console.log('Loading sanctions list...');
    } else if (sanctionsError) {
      console.error('Error loading sanctions list:', sanctionsError);
    } else {
      console.log('Sanctions list loaded successfully.');
    }
  }, [sanctionsLoading, sanctionsError]);

  // 检查所有相关实体是否被制裁（使用多实体检查）
  const riskItemSanctionResults = useMemo(() => {
    return checkMultipleEntities(result.risk_item);
  }, [checkMultipleEntities, result.risk_item]);

  const intermediarySanctionResults = useMemo(() => {
    return checkMultipleEntities(result.potential_intermediary_B);
  }, [checkMultipleEntities, result.potential_intermediary_B]);

  const institutionASanctionResults = useMemo(() => {
    return checkMultipleEntities(result.institution_a);
  }, [checkMultipleEntities, result.institution_a]);

  const institutionCSanctionResults = useMemo(() => {
    return checkMultipleEntities(result.institution_c);
  }, [checkMultipleEntities, result.institution_c]);
  
  // 检查 Target Institution Name
  const targetInstitutionSanctionResults = useMemo(() => {
    return checkMultipleEntities(result.target_institution_name);
  }, [checkMultipleEntities, result.target_institution_name]);

  // 整合所有检查结果
  const allSanctionResults = useMemo(() => {
    return [
      ...riskItemSanctionResults.map(check => ({ entity: 'Risk Item', check })),
      ...intermediarySanctionResults.map(check => ({ entity: 'Intermediary', check })),
      ...institutionASanctionResults.map(check => ({ entity: 'Institution A', check })),
      ...institutionCSanctionResults.map(check => ({ entity: 'Institution C', check })),
      ...targetInstitutionSanctionResults.map(check => ({ entity: 'Target Institution', check }))
    ];
  }, [riskItemSanctionResults, intermediarySanctionResults, institutionASanctionResults, institutionCSanctionResults, targetInstitutionSanctionResults]);

  // 分类匹配结果：确定匹配和可能匹配
  const definiteMatches = useMemo(() => {
    return allSanctionResults.filter(item => 
      isDefiniteMatch(item.check.matchLevel) && item.check.isSanctioned
    );
  }, [allSanctionResults, isDefiniteMatch]);

  const possibleMatches = useMemo(() => {
    return allSanctionResults.filter(item => 
      item.check.matchLevel === MatchLevel.PARTIAL && item.check.isSanctioned
    );
  }, [allSanctionResults]);

  // 判断是否有制裁实体（确定或可能匹配）
  const hasDefiniteMatches = definiteMatches.length > 0;
  const hasPossibleMatches = possibleMatches.length > 0;
  const isSanctioned = hasDefiniteMatches || hasPossibleMatches;
  
  // 获取匹配的制裁实体信息（用于兼容旧代码）
  const matchedSanctionEntity = hasDefiniteMatches 
    ? definiteMatches[0].check.matchedEntity 
    : (hasPossibleMatches ? possibleMatches[0].check.matchedEntity : undefined);

  // 调试日志：打印sources数量和内容
  console.log(
    `【调试 ResultCard】risk_item: ${result.risk_item}`
    // Optionally log other props/state here
  );

  // Render the card UI
  return (
    <Card className="w-full">
      <CardHeader>
        <CardTitle className="text-xl">{result.risk_item}</CardTitle>
        {/* Conditionally render the sanctioned entity tag */}
        {isSanctioned && (
          <div className="mt-1">
            <Dialog>
              <DialogTrigger asChild>
                <span className="inline-block bg-yellow-200 text-yellow-800 text-xs font-medium mr-2 px-2.5 py-0.5 rounded dark:bg-yellow-900 dark:text-yellow-300 cursor-pointer hover:bg-yellow-300 transition-colors">
                  <div className="flex items-center">
                    <AlertTriangle className="h-3 w-3 mr-1" />
                    {hasDefiniteMatches ? "Sanctioned Entity" : "Possible Sanction Match"}
                  </div>
                </span>
              </DialogTrigger>
              <DialogContent className="sm:max-w-md max-h-[80vh] overflow-y-auto">
                <DialogHeader>
                  <DialogTitle className="text-yellow-800 flex items-center">
                    <AlertTriangle className="h-5 w-5 mr-2 text-yellow-600" />
                    Sanctioned Entities Found
                  </DialogTitle>
                  <DialogDescription>
                    {hasDefiniteMatches && hasPossibleMatches
                      ? `Found ${definiteMatches.length} confirmed ${definiteMatches.length === 1 ? 'match' : 'matches'} and ${possibleMatches.length} possible ${possibleMatches.length === 1 ? 'match' : 'matches'}.`
                      : hasDefiniteMatches
                        ? `Found ${definiteMatches.length} confirmed ${definiteMatches.length === 1 ? 'match' : 'matches'} with sanctioned organizations.`
                        : `Found ${possibleMatches.length} possible ${possibleMatches.length === 1 ? 'match' : 'matches'} with sanctioned organizations.`
                    }
                  </DialogDescription>
                </DialogHeader>
                
                <div className="mt-4 space-y-6">
                  {/* 确定匹配部分 */}
                  {definiteMatches.length > 0 && (
                    <div>
                      <h3 className="text-sm font-semibold mb-2 bg-yellow-100 text-yellow-800 px-2 py-1 rounded">
                        Confirmed Matches
                      </h3>
                      <div className="space-y-3">
                        {definiteMatches.map((item, index) => (
                          <Card key={`definite-${index}`} className="border-yellow-300">
                            <CardHeader className="pb-2">
                              <CardTitle className="text-base flex items-center">
                                <span className="bg-yellow-100 text-yellow-800 text-xs font-medium mr-2 px-2 py-0.5 rounded">
                                  {item.entity}
                                </span>
                                <span className="text-sm">{item.check.entityName}</span>
                                <span className="ml-auto text-xs bg-yellow-50 text-yellow-600 px-1 py-0.5 rounded">
                                  {item.check.matchLevel === MatchLevel.EXACT ? 'Exact' : 
                                   item.check.matchLevel === MatchLevel.ALIAS ? 'Alias' : 
                                   item.check.matchLevel === MatchLevel.ACRONYM ? 'Acronym' : ''}
                                </span>
                              </CardTitle>
                            </CardHeader>
                            <CardContent className="pt-0">
                              <div className="border-t border-yellow-100 pt-2 mt-1">
                                <p className="text-sm font-medium mb-1">Matched with: {item.check.matchedEntity?.name}</p>
                                
                                {item.check.matchedEntity?.aliases && item.check.matchedEntity.aliases.length > 0 && (
                                  <div className="mt-2">
                                    <p className="text-xs font-medium text-gray-500 mb-1">Known Aliases:</p>
                                    <ul className="list-disc pl-4 space-y-0.5">
                                      {item.check.matchedEntity.aliases.map((alias, aliasIndex) => (
                                        <li key={aliasIndex} className="text-xs text-gray-700">{alias}</li>
                                      ))}
                                    </ul>
                                  </div>
                                )}
                              </div>
                            </CardContent>
                          </Card>
                        ))}
                      </div>
                    </div>
                  )}
                  
                  {/* 可能匹配部分 */}
                  {possibleMatches.length > 0 && (
                    <div>
                      <h3 className="text-sm font-semibold mb-2 bg-gray-100 text-gray-800 px-2 py-1 rounded">
                        Possible Matches
                      </h3>
                      <div className="space-y-3">
                        {possibleMatches.map((item, index) => (
                          <Card key={`possible-${index}`} className="border-gray-200">
                            <CardHeader className="pb-2">
                              <CardTitle className="text-base flex items-center">
                                <span className="bg-gray-100 text-gray-800 text-xs font-medium mr-2 px-2 py-0.5 rounded">
                                  {item.entity}
                                </span>
                                <span className="text-sm">{item.check.entityName}</span>
                              </CardTitle>
                            </CardHeader>
                            <CardContent className="pt-0">
                              <div className="border-t border-gray-100 pt-2 mt-1">
                                <p className="text-sm font-medium mb-1">Possibly related to: {item.check.matchedEntity?.name}</p>
                                
                                {item.check.matchedEntity?.aliases && item.check.matchedEntity.aliases.length > 0 && (
                                  <div className="mt-2">
                                    <p className="text-xs font-medium text-gray-500 mb-1">Known Aliases:</p>
                                    <ul className="list-disc pl-4 space-y-0.5">
                                      {item.check.matchedEntity.aliases.map((alias, aliasIndex) => (
                                        <li key={aliasIndex} className="text-xs text-gray-700">{alias}</li>
                                      ))}
                                    </ul>
                                  </div>
                                )}
                              </div>
                            </CardContent>
                          </Card>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              </DialogContent>
            </Dialog>
          </div>
        )}
      </CardHeader>
      <CardContent className="space-y-4">
        <p className="text-sm font-medium">
          Relationship Type: {result.relationship_type}
        </p>
        
        {result.potential_intermediary_B && (
          <p className="text-sm font-medium">
            Potential Intermediary: {result.potential_intermediary_B}
          </p>
        )}

        <p className="text-sm text-muted-foreground mt-4">
          {result.finding_summary ? 
            sanitizeText(result.finding_summary) : 
            "No finding summary available"
          }
        </p>
        
        {/* 根据 Google 官方文档要求，添加 Google 搜索建议组件 */}
        {/* 同时支持新旧两种数据格式 */}
        <div className="mt-4 w-full flex justify-center">
          <div className="w-full max-w-full overflow-hidden">
            <GoogleSearchSuggestion 
              renderedContent={
                (result.search_metadata && result.search_metadata.rendered_content) || 
                result.rendered_content
              } 
              searchQueries={
                (result.search_metadata && result.search_metadata.search_queries) || 
                result.search_queries
              } 
            />
          </div>
        </div>

        {/* Render the SourceList component */}
        <SourceList sources={result.sources} riskItem={result.risk_item} />
      </CardContent>
    </Card>
  );
};

export default ResultCard;

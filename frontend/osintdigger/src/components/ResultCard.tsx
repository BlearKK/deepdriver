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
import { useNROListed, MatchLevel, MatchResult, NROListedEntity } from '@/hooks/useNROListed';
import SourceList from './SourceList';

interface ResultCardProps {
  result: {
    risk_item: string;
    relationship_type: string;
    finding_summary: string;
    potential_intermediary_B?: string | string[] | null;
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
const sanitizeText = (text: string | string[] | null | undefined): string | string[] => {
  if (!text) return "";
  
  // 如果是数组，对每个元素进行处理
  if (Array.isArray(text)) {
    return text.map(item => sanitizeText(item) as string);
  }
  
  try {
    // 保留原始的【数字】格式，不再替换为"引用数字"
    // 如果需要，可以在这里添加其他文本清理逻辑
    return text;
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
        cleanedResult.finding_summary = sanitizeText(cleanedResult.finding_summary) as string;
      }
      
      // 处理其他可能包含问题字符的字段
      if (cleanedResult.risk_item) {
        cleanedResult.risk_item = sanitizeText(cleanedResult.risk_item) as string;
      }
      
      if (cleanedResult.relationship_type) {
        cleanedResult.relationship_type = sanitizeText(cleanedResult.relationship_type) as string;
      }
      
      // 处理potential_intermediary_B，可能是字符串或数组
      if (cleanedResult.potential_intermediary_B) {
        // 保持原始类型（字符串或数组）
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

  // Use the custom hook to get NRO Listed data
  const { nroSet, checkEntityNROListed, checkMultipleEntities, isDefiniteMatch, isLoading: nroListedLoading, error: nroListedError } = useNROListed();

  // Log loading/error status for NRO Listed entities (optional)
  useEffect(() => {
    if (nroListedLoading) {
      console.log('Loading NRO Listed entities...');
    } else if (nroListedError) {
      console.error('Error loading NRO Listed entities:', nroListedError);
    } else {
      console.log('NRO Listed entities loaded successfully.');
    }
  }, [nroListedLoading, nroListedError]);

  // 检查所有相关实体是否在NRO列表中（使用多实体检查）
  const riskItemNROListedResults = useMemo(() => {
    return checkMultipleEntities(result.risk_item);
  }, [checkMultipleEntities, result.risk_item]);

  const intermediaryNROListedResults = useMemo(() => {
    // 如果是数组，将其转换为逗号分隔的字符串
    const intermediary = Array.isArray(result.potential_intermediary_B) 
      ? result.potential_intermediary_B.join(', ')
      : result.potential_intermediary_B;
    return checkMultipleEntities(intermediary);
  }, [checkMultipleEntities, result.potential_intermediary_B]);

  const institutionANROListedResults = useMemo(() => {
    return checkMultipleEntities(result.institution_a);
  }, [checkMultipleEntities, result.institution_a]);

  const institutionCNROListedResults = useMemo(() => {
    return checkMultipleEntities(result.institution_c);
  }, [checkMultipleEntities, result.institution_c]);
  
  // 检查 Target Institution Name
  const targetInstitutionNROListedResults = useMemo(() => {
    return checkMultipleEntities(result.target_institution_name);
  }, [checkMultipleEntities, result.target_institution_name]);

  // 整合所有检查结果
  const allNROListedResults = useMemo(() => {
    return [
      ...riskItemNROListedResults.map(check => ({ entity: 'Risk Item', check })),
      ...intermediaryNROListedResults.map(check => ({ entity: 'Intermediary', check })),
      ...institutionANROListedResults.map(check => ({ entity: 'Institution A', check })),
      ...institutionCNROListedResults.map(check => ({ entity: 'Institution C', check })),
      ...targetInstitutionNROListedResults.map(check => ({ entity: 'Target Institution', check }))
    ];
  }, [riskItemNROListedResults, intermediaryNROListedResults, institutionANROListedResults, institutionCNROListedResults, targetInstitutionNROListedResults]);

  // 分类匹配结果：确定匹配和可能匹配
  const definiteMatches = useMemo(() => {
    return allNROListedResults.filter(item => 
      isDefiniteMatch(item.check.matchLevel) && item.check.isNROListed
    );
  }, [allNROListedResults, isDefiniteMatch]);

  const possibleMatches = useMemo(() => {
    return allNROListedResults.filter(item => 
      !isDefiniteMatch(item.check.matchLevel) && item.check.isNROListed
    );
  }, [allNROListedResults, isDefiniteMatch]);

  // 判断是否有NRO列表实体
  const hasNROListedEntities = definiteMatches.length > 0 || possibleMatches.length > 0;
  
  // 获取匹配的NRO列表实体信息（用于兼容旧代码）
  const matchedNROListedEntity = hasNROListedEntities 
    ? definiteMatches[0].check.matchedEntity 
    : (possibleMatches.length > 0 ? possibleMatches[0].check.matchedEntity : undefined);

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
        {/* Conditionally render the NRO Listed entity tag */}
        {hasNROListedEntities && (
          <div className="mt-1">
            <Dialog>
              <DialogTrigger asChild>
                <span className="inline-block bg-yellow-200 text-yellow-800 text-xs font-medium mr-2 px-2.5 py-0.5 rounded dark:bg-yellow-900 dark:text-yellow-300 cursor-pointer hover:bg-yellow-300 transition-colors">
                  <div className="flex items-center">
                    <AlertTriangle className="h-3 w-3 mr-1" />
                    {definiteMatches.length > 0 ? "NRO Listed Entity" : "Possible NRO Listed Match"}
                  </div>
                </span>
              </DialogTrigger>
              <DialogContent className="sm:max-w-md max-h-[80vh] overflow-y-auto">
                <DialogHeader>
                  <DialogTitle className="text-yellow-800 flex items-center">
                    <AlertTriangle className="h-5 w-5 mr-2 text-yellow-600" />
                    NRO Listed Entities Found
                  </DialogTitle>
                  <DialogDescription>
                    {definiteMatches.length + possibleMatches.length} NRO listed {definiteMatches.length + possibleMatches.length === 1 ? 'entity' : 'entities'} found
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
          <div className="text-sm font-medium">
            <p>Potential Intermediary:</p>
            {Array.isArray(result.potential_intermediary_B) ? (
              <ul className="list-disc pl-5 mt-1 space-y-1">
                {result.potential_intermediary_B.map((item, index) => (
                  <li key={index}>{item}</li>
                ))}
              </ul>
            ) : (
              <p className="mt-1">{result.potential_intermediary_B}</p>
            )}
          </div>
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

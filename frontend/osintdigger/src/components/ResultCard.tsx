import React, { useState, useEffect, useMemo } from "react";
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

/**
 * 安全地处理文本内容，确保所有输入都能被安全地渲染
 * 处理null、undefined、非字符串类型和数组
 */
const sanitizeText = (text: string | string[] | null | undefined): string | string[] => {
  // 处理null和undefined
  if (text === null || text === undefined) {
    return "";
  }
  
  // 处理数组 - 递归处理每个元素
  if (Array.isArray(text)) {
    // 过滤掉数组中的null和undefined值
    return text
      .filter(item => item !== null && item !== undefined)
      .map(item => sanitizeText(item) as string);
  }
  
  try {
    // 处理非字符串类型
    if (typeof text !== 'string') {
      console.log(`sanitizeText received non-string value of type ${typeof text}:`, text);
      try {
        return String(text); // 尝试转换为字符串
      } catch (e) {
        console.error("Failed to convert to string:", e);
        return "[Unparsable data]";
      }
    }
    
    // 处理空字符串
    if (text.trim() === "") {
      return "";
    }
    
    // 返回处理后的文本
    return text;
  } catch (error) {
    console.error("Error sanitizing text:", error);
    return "Error processing text";
  }
};

/**
 * ResultCard组件 - 显示搜索结果卡片
 * 包含完整的错误处理和数据验证
 */
const ResultCard = ({ result: initialResult }: ResultCardProps) => {
  // 错误状态管理
  const [hasError, setHasError] = useState<boolean>(false);
  const [errorMessage, setErrorMessage] = useState<string>("");
  
  // 使用useMemo处理初始数据，避免不必要的重复计算
  const sanitizedInitialResult = useMemo(() => {
    if (!initialResult) {
      console.error("ResultCard received null or undefined result");
      setHasError(true);
      setErrorMessage("No result data provided");
      return {
        risk_item: "Unknown Risk Item",
        relationship_type: "Unknown",
        finding_summary: "No data available",
        sources: []
      };
    }
    
    try {
      // 创建深拷贝，避免修改原始数据
      const cleanedResult = JSON.parse(JSON.stringify(initialResult));
      
      // 系统地处理所有可能的字段
      const fieldsToSanitize = [
        'risk_item', 'relationship_type', 'finding_summary', 
        'institution_a', 'institution_c', 'target_institution_name'
      ];
      
      // 处理基本字符串字段
      fieldsToSanitize.forEach(field => {
        if (field in cleanedResult) {
          cleanedResult[field] = sanitizeText(cleanedResult[field]);
        }
      });
      
      // 特殊处理potential_intermediary_B（可能是字符串或数组）
      if ('potential_intermediary_B' in cleanedResult) {
        cleanedResult.potential_intermediary_B = sanitizeText(cleanedResult.potential_intermediary_B);
      }
      
      // 处理嵌套对象 search_metadata
      if (cleanedResult.search_metadata) {
        if (cleanedResult.search_metadata.rendered_content) {
          cleanedResult.search_metadata.rendered_content = 
            sanitizeText(cleanedResult.search_metadata.rendered_content) as string;
        }
        
        if (cleanedResult.search_metadata.search_queries) {
          cleanedResult.search_metadata.search_queries = 
            sanitizeText(cleanedResult.search_metadata.search_queries) as string[];
        }
      }
      
      // 处理旧格式的字段
      if ('rendered_content' in cleanedResult) {
        cleanedResult.rendered_content = sanitizeText(cleanedResult.rendered_content) as string;
      }
      
      if ('search_queries' in cleanedResult) {
        cleanedResult.search_queries = sanitizeText(cleanedResult.search_queries) as string[];
      }
      
      return cleanedResult;
    } catch (error) {
      console.error("Error sanitizing result data:", error);
      setHasError(true);
      setErrorMessage(error instanceof Error ? error.message : "Unknown error processing data");
      
      // 返回安全的默认对象
      return {
        risk_item: initialResult?.risk_item || "Unknown Risk Item",
        relationship_type: "Unknown",
        finding_summary: "Error processing data",
        sources: []
      };
    }
  }, [initialResult]);
  
  // 使用状态管理处理后的结果
  const [result, setResult] = useState(sanitizedInitialResult);
  
  // 当sanitizedInitialResult变化时更新result
  useEffect(() => {
    setResult(sanitizedInitialResult);
  }, [sanitizedInitialResult]);
  
  // 全局错误处理
  useEffect(() => {
    const handleError = (error: Error) => {
      console.error("ResultCard error:", error);
      setHasError(true);
      setErrorMessage(error.message || "An unexpected error occurred");
    };
    
    // 设置全局错误处理器
    window.addEventListener('error', (event) => {
      if (event.error) handleError(event.error);
    });
    
    // 验证初始数据
    if (initialResult && typeof initialResult === 'object') {
      // 验证关键属性
      if (initialResult.finding_summary && 
          typeof initialResult.finding_summary === 'string' && 
          initialResult.finding_summary.includes('[')) {
        console.warn("Finding summary contains potentially problematic brackets:", 
                    initialResult.finding_summary.substring(0, 100));
      }
    }
    
    return () => {
      window.removeEventListener('error', (event) => {
        if (event.error) handleError(event.error);
      });
    };
  }, [initialResult]);
  
  // 使用NRO列表检查功能
  const { 
    checkMultipleEntities, 
    isDefiniteMatch, 
    isLoading: isNROListLoading 
  } = useNROListed();
  
  // 检查所有相关实体是否在NRO列表中
  const riskItemNROListedResults = useMemo(() => {
    return checkMultipleEntities(result.risk_item);
  }, [checkMultipleEntities, result.risk_item]);
  
  const intermediaryNROListedResults = useMemo(() => {
    // 如果是数组，将其转换为逗号分隔的字符串
    const intermediary = Array.isArray(result.potential_intermediary_B) 
      ? result.potential_intermediary_B.join(', ')
      : result.potential_intermediary_B;
    
    return intermediary ? checkMultipleEntities(intermediary) : [];
  }, [checkMultipleEntities, result.potential_intermediary_B]);
  
  // 检查 Institution A
  const institutionANROListedResults = useMemo(() => {
    return result.institution_a ? checkMultipleEntities(result.institution_a) : [];
  }, [checkMultipleEntities, result.institution_a]);
  
  // 检查 Target Institution Name
  const targetInstitutionNROListedResults = useMemo(() => {
    return result.target_institution_name ? checkMultipleEntities(result.target_institution_name) : [];
  }, [checkMultipleEntities, result.target_institution_name]);
  
  // 整合所有检查结果
  const allNROListedResults = useMemo(() => {
    return [
      ...riskItemNROListedResults.map(check => ({ entity: 'Risk Item', check })),
      ...intermediaryNROListedResults.map(check => ({ entity: 'Intermediary', check })),
      ...institutionANROListedResults.map(check => ({ entity: 'Institution A', check })),
      ...targetInstitutionNROListedResults.map(check => ({ entity: 'Target Institution', check }))
    ];
  }, [
    riskItemNROListedResults, 
    intermediaryNROListedResults, 
    institutionANROListedResults, 
    targetInstitutionNROListedResults
  ]);
  
  // 分离确定匹配和可能匹配
  const definiteMatches = useMemo(() => {
    return allNROListedResults.filter(item => isDefiniteMatch(item.check.matchLevel));
  }, [allNROListedResults, isDefiniteMatch]);
  
  const possibleMatches = useMemo(() => {
    return allNROListedResults.filter(
      item => item.check.isNROListed && !isDefiniteMatch(item.check.matchLevel)
    );
  }, [allNROListedResults, isDefiniteMatch]);
  
  // 判断是否有NRO列表实体
  const hasNROListedEntities = definiteMatches.length > 0 || possibleMatches.length > 0;
  
  // 获取匹配的NRO列表实体信息
  const matchedNROListedEntity = hasNROListedEntities 
    ? definiteMatches[0]?.check.matchedEntity 
    : (possibleMatches.length > 0 ? possibleMatches[0]?.check.matchedEntity : undefined);
  
  // 调试日志
  console.log(`【调试 ResultCard】risk_item: ${result.risk_item}`);
  
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
  
  // 渲染正常UI
  return (
    <Card className="w-full">
      <CardHeader>
        <CardTitle className="text-xl">{result.risk_item}</CardTitle>
        {/* 条件渲染NRO Listed实体标签 */}
        {hasNROListedEntities && (
          <div className="mt-1">
            <Dialog>
              <DialogTrigger asChild>
                <span className="inline-flex items-center rounded-md bg-yellow-50 px-2 py-1 text-xs font-medium text-yellow-800 ring-1 ring-inset ring-yellow-600/20 cursor-pointer hover:bg-yellow-100 transition-colors">
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
        
        {/* Google 搜索建议组件 */}
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

        {/* 渲染来源列表组件 */}
        <SourceList sources={result.sources} riskItem={result.risk_item} />
      </CardContent>
    </Card>
  );
};

export default ResultCard;

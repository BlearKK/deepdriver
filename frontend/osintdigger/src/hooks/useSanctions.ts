import { useState, useEffect, useCallback } from 'react';

// Define the expected structure of items in the JSON list
export interface SanctionEntity {
  name: string;
  aliases?: string[];
}

// 定义匹配级别枚举
export enum MatchLevel {
  EXACT = 'exact',      // 完全匹配
  ALIAS = 'alias',      // 别名匹配（也是确定匹配）
  ACRONYM = 'acronym',  // 缩写匹配（也是确定匹配）
  PARTIAL = 'partial',  // 部分匹配
  NONE = 'none'         // 无匹配
}

// 判断是否为确定匹配
export function isDefiniteMatch(matchLevel: MatchLevel): boolean {
  return matchLevel === MatchLevel.EXACT || 
         matchLevel === MatchLevel.ALIAS || 
         matchLevel === MatchLevel.ACRONYM;
}

// 定义匹配结果接口
export interface MatchResult {
  matchLevel: MatchLevel;            // 匹配级别
  isSanctioned: boolean;             // 是否被制裁
  matchedEntity?: SanctionEntity;    // 匹配的制裁实体
  entityName: string;                // 原始实体名称
}

// Define the return type of the hook
interface UseSanctionsReturn {
  // 原始制裁列表
  sanctionsList: SanctionEntity[] | null;
  // 小写名称和别名的集合，用于快速完全匹配
  sanctionsSet: Set<string> | null;
  // 检查单个实体是否被制裁的函数
  checkEntitySanctioned: (entityName: string | null | undefined) => MatchResult;
  // 检查可能包含多个实体的文本
  checkMultipleEntities: (text: string | null | undefined) => MatchResult[];
  // 判断是否为确定匹配的函数
  isDefiniteMatch: (matchLevel: MatchLevel) => boolean;
  isLoading: boolean;
  error: string | null;
}

/**
 * Custom hook to fetch and manage the set of sanctioned entities.
 * Fetches the list from '/Sanction_list/Named Research Organizations.json'.
 * Provides the set of names/aliases (lowercase), loading status, and error info.
 */
export const useSanctions = (): UseSanctionsReturn => {
  const [sanctionsList, setSanctionsList] = useState<SanctionEntity[] | null>(null);
  const [sanctionsSet, setSanctionsSet] = useState<Set<string> | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchSanctions = async () => {
      setIsLoading(true);
      setError(null);
      try {
        const response = await fetch('/Sanction_list/Named Research Organizations.json');
        if (!response.ok) {
          throw new Error(`HTTP error! status: ${response.status}`);
        }
        const loadedSanctionsList: SanctionEntity[] = await response.json();

        // 保存原始制裁列表
        setSanctionsList(loadedSanctionsList);

        // 创建小写名称和别名的集合，用于快速完全匹配
        const newSanctionsSet = new Set<string>();
        if (Array.isArray(loadedSanctionsList)) {
          loadedSanctionsList.forEach(item => {
            if (item && typeof item === 'object') {
              if (item.name && typeof item.name === 'string') {
                newSanctionsSet.add(item.name.toLowerCase());
              }
              if (item.aliases && Array.isArray(item.aliases)) {
                item.aliases.forEach(alias => {
                  if (alias && typeof alias === 'string') {
                    newSanctionsSet.add(alias.toLowerCase());
                  }
                });
              }
            }
          });
        }
        setSanctionsSet(newSanctionsSet);
      } catch (err) {
        console.error('Failed to load or process sanctions list:', err);
        setError(err instanceof Error ? err.message : 'Unknown error loading sanctions list');
        setSanctionsList(null); // Ensure list is null on error
        setSanctionsSet(null); // Ensure set is null on error
      } finally {
        setIsLoading(false);
      }
    };

    fetchSanctions();
  }, []); // Runs once on mount

  /**
   * 规范化实体名称，处理括号内的缩写和其他常见格式
   */
  const normalizeEntityName = (name: string): { normalized: string, acronym: string | null } => {
    // 去除前后空格并转为小写
    const trimmed = name.trim().toLowerCase();
    
    // 提取括号内的缩写（如果有）
    const acronymMatch = trimmed.match(/\((\w+)\)/);
    const acronym = acronymMatch ? acronymMatch[1] : null;
    
    // 移除括号及其内容
    const withoutParentheses = trimmed.replace(/\s*\([^)]*\)\s*/g, ' ').trim();
    
    // 将多个空格压缩为一个
    const normalized = withoutParentheses.replace(/\s+/g, ' ');
    
    return { normalized, acronym };
  };
  
  /**
   * 检查实体是否被制裁
   * 区分完全匹配、别名匹配、缩写匹配和部分匹配
   */
  const checkEntitySanctioned = useCallback((entityName: string | null | undefined): MatchResult => {
    // 如果实体名称为空或制裁列表未加载，返回未制裁
    if (!entityName || !sanctionsList || isLoading || error) {
      return { matchLevel: MatchLevel.NONE, isSanctioned: false, entityName: entityName || '' };
    }
    
    // 规范化实体名称，处理括号内的缩写
    const { normalized: entityNameNormalized, acronym: entityAcronym } = normalizeEntityName(entityName);
    const entityNameLower = entityNameNormalized;
    
    // 1. 先尝试完全匹配（精确匹配）
    for (const sanctionedEntity of sanctionsList) {
      const sanctionNameNormalized = normalizeEntityName(sanctionedEntity.name).normalized;
      
      // 1.1 检查规范化后的名称是否完全匹配
      if (entityNameLower === sanctionNameNormalized) {
        return { 
          matchLevel: MatchLevel.EXACT, 
          isSanctioned: true, 
          matchedEntity: sanctionedEntity,
          entityName 
        };
      }
      
      // 1.2 检查别名是否匹配
      if (sanctionedEntity.aliases?.some(alias => {
        const aliasNormalized = normalizeEntityName(alias).normalized;
        return entityNameLower === aliasNormalized;
      })) {
        return { 
          matchLevel: MatchLevel.ALIAS, 
          isSanctioned: true, 
          matchedEntity: sanctionedEntity,
          entityName 
        };
      }
      
      // 1.3 如果实体名称中有括号内的缩写，检查是否与制裁实体的缩写匹配
      if (entityAcronym && sanctionedEntity.aliases?.some(alias => alias.toLowerCase() === entityAcronym)) {
        return { 
          matchLevel: MatchLevel.ACRONYM, 
          isSanctioned: true, 
          matchedEntity: sanctionedEntity,
          entityName 
        };
      }
    }
    
    // 2. 检查缩写匹配
    for (const sanctionedEntity of sanctionsList) {
      // 2.1 检查实体名称是否是制裁实体的缩写
      // 例如："PHRC" 是 "Physics Research Center" 的缩写
      if (isAcronym(entityNameLower, sanctionedEntity.name.toLowerCase())) {
        return { 
          matchLevel: MatchLevel.ACRONYM, 
          isSanctioned: true, 
          matchedEntity: sanctionedEntity,
          entityName 
        };
      }
      
      // 2.2 检查制裁实体是否是实体名称的缩写
      if (isAcronym(sanctionedEntity.name.toLowerCase(), entityNameLower)) {
        return { 
          matchLevel: MatchLevel.ACRONYM, 
          isSanctioned: true, 
          matchedEntity: sanctionedEntity,
          entityName 
        };
      }
      
      // 2.3 检查别名中的缩写
      if (sanctionedEntity.aliases?.length) {
        for (const alias of sanctionedEntity.aliases) {
          const aliasLower = alias.toLowerCase();
          
          // 检查实体名称是否是别名的缩写
          if (isAcronym(entityNameLower, aliasLower)) {
            return { 
              matchLevel: MatchLevel.ACRONYM, 
              isSanctioned: true, 
              matchedEntity: sanctionedEntity,
              entityName 
            };
          }
          
          // 检查别名是否是实体名称的缩写
          if (isAcronym(aliasLower, entityNameLower)) {
            return { 
              matchLevel: MatchLevel.ACRONYM, 
              isSanctioned: true, 
              matchedEntity: sanctionedEntity,
              entityName 
            };
          }
        }
      }
    }
    
    // 3. 尝试部分匹配 - 只匹配完整实体名称
    for (const sanctionedEntity of sanctionsList) {
      const sanctionNameNormalized = normalizeEntityName(sanctionedEntity.name).normalized;
      
      // 3.1 检查实体名称是否与制裁名称完全匹配（忽略所有空格）
      if (entityNameLower.replace(/\s+/g, '') === sanctionNameNormalized.replace(/\s+/g, '')) {
        return { 
          matchLevel: MatchLevel.PARTIAL, 
          isSanctioned: true, 
          matchedEntity: sanctionedEntity,
          entityName 
        };
      }
      
      // 3.2 检查实体名称是否是制裁名称的子串（完整子串，不是单词匹配）
      if (sanctionNameNormalized.includes(entityNameLower) && 
          // 确保实体名称是一个完整的短语，而不是单词
          entityNameLower.length > 10 && 
          // 检查实体名称前后是否有单词边界
          (sanctionNameNormalized.indexOf(entityNameLower) === 0 || 
           sanctionNameNormalized.charAt(sanctionNameNormalized.indexOf(entityNameLower) - 1) === ' ') && 
          (sanctionNameNormalized.indexOf(entityNameLower) + entityNameLower.length === sanctionNameNormalized.length || 
           sanctionNameNormalized.charAt(sanctionNameNormalized.indexOf(entityNameLower) + entityNameLower.length) === ' ')
      ) {
        return { 
          matchLevel: MatchLevel.PARTIAL, 
          isSanctioned: true, 
          matchedEntity: sanctionedEntity,
          entityName 
        };
      }
      
      // 3.3 检查制裁名称是否是实体名称的子串
      if (entityNameLower.includes(sanctionNameNormalized) && 
          sanctionNameNormalized.length > 10 && 
          (entityNameLower.indexOf(sanctionNameNormalized) === 0 || 
           entityNameLower.charAt(entityNameLower.indexOf(sanctionNameNormalized) - 1) === ' ') && 
          (entityNameLower.indexOf(sanctionNameNormalized) + sanctionNameNormalized.length === entityNameLower.length || 
           entityNameLower.charAt(entityNameLower.indexOf(sanctionNameNormalized) + sanctionNameNormalized.length) === ' ')
      ) {
        return { 
          matchLevel: MatchLevel.PARTIAL, 
          isSanctioned: true, 
          matchedEntity: sanctionedEntity,
          entityName 
        };
      }
      
      // 3.4 检查别名匹配
      for (const alias of (sanctionedEntity.aliases || [])) {
        const aliasNormalized = normalizeEntityName(alias).normalized;
        
        // 检查实体名称是否与别名完全匹配（忽略所有空格）
        if (entityNameLower.replace(/\s+/g, '') === aliasNormalized.replace(/\s+/g, '')) {
          return { 
            matchLevel: MatchLevel.PARTIAL, 
            isSanctioned: true, 
            matchedEntity: sanctionedEntity,
            entityName 
          };
        }
        
        // 检查实体名称是否是别名的子串
        if (aliasNormalized.includes(entityNameLower) && 
            entityNameLower.length > 10 && 
            (aliasNormalized.indexOf(entityNameLower) === 0 || 
             aliasNormalized.charAt(aliasNormalized.indexOf(entityNameLower) - 1) === ' ') && 
            (aliasNormalized.indexOf(entityNameLower) + entityNameLower.length === aliasNormalized.length || 
             aliasNormalized.charAt(aliasNormalized.indexOf(entityNameLower) + entityNameLower.length) === ' ')
        ) {
          return { 
            matchLevel: MatchLevel.PARTIAL, 
            isSanctioned: true, 
            matchedEntity: sanctionedEntity,
            entityName 
          };
        }
      }
      
      // 3.2 检查别名
      if (sanctionedEntity.aliases?.length) {
        for (const alias of sanctionedEntity.aliases) {
          const aliasLower = alias.toLowerCase();
          
          // 检查实体名称是否与别名完全匹配（忽略空格和大小写）
          if (entityNameLower.replace(/\s+/g, '') === aliasLower.replace(/\s+/g, '')) {
            return { 
              matchLevel: MatchLevel.PARTIAL, 
              isSanctioned: true, 
              matchedEntity: sanctionedEntity,
              entityName 
            };
          }
          
          // 检查实体名称是否是别名的完整子串
          if (aliasLower.includes(entityNameLower) && 
              entityNameLower.length > 10 && 
              (aliasLower.indexOf(entityNameLower) === 0 || 
               aliasLower.charAt(aliasLower.indexOf(entityNameLower) - 1) === ' ') && 
              (aliasLower.indexOf(entityNameLower) + entityNameLower.length === aliasLower.length || 
               aliasLower.charAt(aliasLower.indexOf(entityNameLower) + entityNameLower.length) === ' ')
          ) {
            return { 
              matchLevel: MatchLevel.PARTIAL, 
              isSanctioned: true, 
              matchedEntity: sanctionedEntity,
              entityName 
            };
          }
        }
      }
    }
    
    // 没有找到匹配
    return { 
      matchLevel: MatchLevel.NONE, 
      isSanctioned: false,
      entityName 
    };
  }, [sanctionsList, sanctionsSet, isLoading, error]);
  
  /**
   * 判断一个字符串是否是另一个字符串的缩写
   * 例如："PHRC" 是 "Physics Research Center" 的缩写
   */
  const isAcronym = (acronym: string, fullName: string): boolean => {
    // 如果缩写比全名还长，那么肯定不是缩写
    if (acronym.length >= fullName.length) {
      return false;
    }
    
    // 如果缩写不是全部大写字母，则不考虑匹配
    // 例如："PHRC" 是缩写，而 "Fateh" 不是缩写
    if (!/^[A-Z]+$/.test(acronym)) {
      return false;
    }
    
    // 将全名分割为单词
    const words = fullName.split(/\s+/).filter(word => word.length > 0);
    
    // 如果单词数量少于2，不考虑缩写匹配
    if (words.length < 2) {
      return false;
    }
    
    // 如果缩写的长度与单词数量一致，检查每个单词的首字母
    if (acronym.length === words.length) {
      const firstLetters = words.map(word => word[0]).join('');
      return firstLetters.toUpperCase() === acronym;
    }
    
    // 获取所有单词的首字母
    const firstLetters = words.map(word => word[0]).join('').toUpperCase();
    
    // 仅当缩写完全匹配首字母组合或是首字母组合的子串时才返回匹配
    // 例如："PRC" 是 "Physics Research Center" 的缩写（匹配首字母的子串）
    // 但是 "ARI" 不应该匹配 "Fateh Aseman Sharif Company"
    return acronym === firstLetters || 
           (firstLetters.includes(acronym) && acronym.length >= 2 && acronym.length >= words.length / 2);
  };
  
  /**
   * 分割并检查可能包含多个实体的文本
   * 支持两种格式：
   * 1. 使用逗号分隔："Physics Research Center (PHRC), Aerospace Industries Organization (AIO)"
   * 2. 使用方括号："[Physics Research Center (PHRC)][Aerospace Industries Organization (AIO)]"
   */
  const checkMultipleEntities = useCallback((text: string | null | undefined): MatchResult[] => {
    if (!text || !sanctionsList) {
      return [];
    }
    
    // 先将整个文本作为一个实体进行完整匹配
    const fullTextMatch = checkEntitySanctioned(text);
    
    // 如果有确定匹配（完全匹配、别名匹配或缩写匹配），直接返回
    if (isDefiniteMatch(fullTextMatch.matchLevel)) {
      return [fullTextMatch];
    }
    
    // 检查是否使用方括号格式
    const bracketMatches = text.match(/\[(.*?)\]/g);
    let entities: string[] = [];
    
    if (bracketMatches && bracketMatches.length > 0) {
      // 使用方括号格式，提取方括号内的实体
      entities = bracketMatches
        .map(match => match.slice(1, -1).trim()) // 移除方括号并去除空格
        .filter(entity => entity.length > 0);
    } else {
      // 使用传统的逗号分隔格式
      entities = text
        .split(/[,;\n]/) 
        .map(entity => entity.trim())
        .filter(entity => entity.length > 0);
    }
    
    // 如果没有找到多个实体，则返回完整文本的匹配结果
    if (entities.length <= 1) {
      return [fullTextMatch];
    }
    
    // 检查每个实体
    const entityResults = entities.map(entity => checkEntitySanctioned(entity));
    
    // 过滤出有确定匹配的实体
    const definiteMatches = entityResults.filter(result => isDefiniteMatch(result.matchLevel));
    
    // 如果有确定匹配，只返回确定匹配的实体
    if (definiteMatches.length > 0) {
      return definiteMatches;
    }
    
    // 如果没有确定匹配，返回所有匹配结果
    return entityResults.filter(result => result.isSanctioned);
  }, [sanctionsList, checkEntitySanctioned, isDefiniteMatch]);

  return { sanctionsList, sanctionsSet, checkEntitySanctioned, checkMultipleEntities, isLoading, error, isDefiniteMatch };
};

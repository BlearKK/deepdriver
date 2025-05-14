// 定义DeepSearch组件的类型

// 搜索结果类型
export interface SearchResult {
  risk_item: string;
  institution_A: string;
  relationship_type: RelationshipType;
  finding_summary?: string;
}

// 关系类型
export type RelationshipType = 'Direct' | 'Indirect' | 'Significant Mention' | 'Unknown' | 'No Evidence Found';

// DeepSearch组件Props
export interface DeepSearchProps {
  onClose?: () => void; // 可选的关闭回调
}

// SSE消息类型
export interface SSEMessage {
  type: 'init' | 'connect' | 'heartbeat' | 'result' | 'batch_complete' | 'complete' | 'error' | 'connection_warning' | 'reconnect_warning' | 'raw' | 'batch_info';
  total?: number;
  progress?: number;
  result?: SearchResult;
  message?: string;
  timestamp?: number;
  elapsed?: number;
  batch?: string;
  reconnect?: boolean; // 标记是否需要重连
  processedItems?: string[]; // 已处理的项目列表，用于重连
  sessionId?: string; // 会话ID，用于重连
  institutionA?: string; // 目标机构名称，用于重连
  // 批处理相关字段
  current_batch?: number; // 当前批次
  total_batches?: number; // 总批次数
}

// HTTP响应类型
export interface DeepSearchResponse {
  total: number;
  processed: number;
  remaining: number;
  results: SearchResult[];
  batch_size: number;
  continuation: boolean;
  next_batch: string[];
}

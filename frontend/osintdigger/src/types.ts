// 定义共享的 TypeScript 类型

export interface Source {
  url: string;
  status: 'ok' | 'error';
  message?: string; // 错误信息，可选
  original_url?: string; // 原始 URL，解析后的 URL 会有这个字段
  time_taken?: number; // 解析耗时，秒
  isResolving?: boolean; // 是否正在解析中
  isResolved?: boolean; // 是否已经解析过
  index?: number; // URL 在数组中的索引
  title?: string; // 网页标题
  description?: string; // 网页描述
  
  // 解析结果字段
  resolved_title?: string | null; // 解析后的标题
  resolved_description?: string | null; // 解析后的描述
  resolved_status?: 'ok' | 'error' | 'warning'; // 解析状态，正常/错误/警告
  resolved_message?: string | null; // 解析过程中的错误或警告信息
}

// 可以根据需要添加其他共享类型
// export interface AnotherType {
//   ...
// }

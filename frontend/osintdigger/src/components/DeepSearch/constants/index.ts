// DeepSearch组件的常量定义

// 关系类型对应的颜色样式
export const RELATIONSHIP_COLORS = {
  'Direct': 'bg-yellow-100 text-yellow-800 border-yellow-300',
  'Indirect': 'bg-blue-100 text-blue-800 border-blue-300',
  'Significant Mention': 'bg-purple-100 text-purple-800 border-purple-300',
  'Unknown': 'bg-gray-100 text-gray-800 border-gray-300',
  'No Evidence Found': 'bg-gray-100 text-gray-500 border-gray-300'
};

// SSE连接相关常量
export const SSE_CONFIG = {
  CONNECTION_TIMEOUT: 240000, // 4分钟连接超时
  HEARTBEAT_TIMEOUT: 60000,  // 60秒心跳超时
  MAX_RECONNECT_ATTEMPTS: 5,  // 最大重连次数
  ACTIVITY_CHECK_INTERVAL: 10000, // 活动检查间隔
  MAX_CONNECTION_TIME: 270000 // 4分30秒后强制断开连接，用于测试重连机制
};

// 时间单位转换常量（用于估计剩余时间）
export const TIME_UNITS = {
  // 时间单位数值
  SECOND: 1000,
  MINUTE: 60 * 1000,
  HOUR: 60 * 60 * 1000,
  
  // 时间单位显示文本（单数）
  SECOND_TEXT: 'second',
  MINUTE_TEXT: 'minute',
  HOUR_TEXT: 'hour',
  
  // 时间单位显示文本（复数）
  SECONDS_TEXT: 'seconds',
  MINUTES_TEXT: 'minutes',
  HOURS_TEXT: 'hours'
};

import React from 'react';

interface GoogleSearchSuggestionProps {
  renderedContent?: string;
  searchQueries?: string[];
}

/**
 * GoogleSearchSuggestion 组件
 * 
 * 根据 Google 官方文档要求显示搜索建议
 * 当用户点击搜索建议时，会跳转到相应的 Google 搜索结果页面
 */
const GoogleSearchSuggestion: React.FC<GoogleSearchSuggestionProps> = ({ 
  renderedContent, 
  searchQueries 
}) => {
  // 如果有渲染内容，直接使用 Google 提供的 HTML 和 CSS
  if (renderedContent) {
    // 添加自定义样式，确保渲染内容支持横向滚动
    const customStyles = `
      .google-search-suggestion-wrapper {
        width: 100%;
        overflow: hidden;
        margin: 0 auto;
      }
      .google-search-suggestion-wrapper > div {
        overflow-x: auto !important;
        max-width: 100% !important;
        scrollbar-width: thin;
        scrollbar-color: #dfe1e5 transparent;
        padding-bottom: 8px;
      }
      .google-search-suggestion-wrapper > div::-webkit-scrollbar {
        height: 6px;
      }
      .google-search-suggestion-wrapper > div::-webkit-scrollbar-track {
        background: transparent;
      }
      .google-search-suggestion-wrapper > div::-webkit-scrollbar-thumb {
        background-color: #dfe1e5;
        border-radius: 6px;
      }
      /* 修复 Google 搜索建议卡片内容的样式 */
      .google-search-suggestion-wrapper .chip {
        white-space: nowrap !important;
        overflow: visible !important;
        display: inline-block !important;
      }
      .google-search-suggestion-wrapper .carousel {
        display: flex !important;
        overflow-x: auto !important;
        scrollbar-width: thin !important;
        scrollbar-color: #dfe1e5 transparent !important;
        padding-bottom: 8px !important;
      }
      .google-search-suggestion-wrapper .carousel::-webkit-scrollbar {
        height: 6px !important;
      }
      .google-search-suggestion-wrapper .carousel::-webkit-scrollbar-track {
        background: transparent !important;
      }
      .google-search-suggestion-wrapper .carousel::-webkit-scrollbar-thumb {
        background-color: #dfe1e5 !important;
        border-radius: 6px !important;
      }
    `;
    
    return (
      <div className="google-search-suggestion-wrapper">
        <style>{customStyles}</style>
        <div 
          className="google-search-suggestion"
          dangerouslySetInnerHTML={{ __html: renderedContent }}
        />
      </div>
    );
  }

  // 如果没有渲染内容但有搜索查询，创建基本的搜索建议
  if (searchQueries && searchQueries.length > 0) {
    // 添加自定义样式，确保搜索查询可以水平滚动
    const customStyles = `
      .custom-search-container {
        width: 100%;
        overflow: hidden;
        border: 1px solid #dfe1e5;
        border-radius: 8px;
        padding: 12px;
        background-color: #fff;
      }
      
      .custom-search-header {
        display: flex;
        align-items: center;
        margin-bottom: 8px;
      }
      
      .custom-search-text {
        color: #5f6368;
        font-size: 14px;
        margin-left: 8px;
      }
      
      .custom-search-queries {
        display: flex;
        overflow-x: auto;
        white-space: nowrap;
        padding-bottom: 8px;
        scrollbar-width: thin;
        scrollbar-color: #dfe1e5 transparent;
      }
      
      .custom-search-queries::-webkit-scrollbar {
        height: 6px;
      }
      
      .custom-search-queries::-webkit-scrollbar-track {
        background: transparent;
      }
      
      .custom-search-queries::-webkit-scrollbar-thumb {
        background-color: #dfe1e5;
        border-radius: 6px;
      }
      
      .custom-search-query-item {
        color: #1a73e8;
        text-decoration: none;
        font-size: 14px;
        padding: 8px 16px;
        margin-right: 8px;
        border: 1px solid #dfe1e5;
        border-radius: 16px;
        white-space: nowrap;
        display: inline-block;
      }
      
      .custom-search-query-item:hover {
        background-color: #f8f9fa;
        text-decoration: underline;
      }
      
      @media (prefers-color-scheme: dark) {
        .custom-search-container {
          background-color: #202124;
          border-color: #5f6368;
        }
        
        .custom-search-text {
          color: #e8eaed;
        }
        
        .custom-search-query-item {
          color: #8ab4f8;
          border-color: #5f6368;
        }
        
        .custom-search-query-item:hover {
          background-color: #303134;
        }
      }
    `;
    
    return (
      <div className="google-search-suggestion">
        <style>{customStyles}</style>
        <div className="custom-search-container">
          <div className="custom-search-header">
            <img 
              src="https://www.google.com/images/branding/googlelogo/1x/googlelogo_color_272x92dp.png" 
              alt="Google" 
              className="google-logo" 
              width="92" 
              height="30" 
            />
            <span className="custom-search-text">搜索</span>
          </div>
          <div className="custom-search-queries-wrapper">
            <div className="custom-search-queries">
              {searchQueries.map((query, index) => (
                <a 
                  key={index} 
                  href={`https://www.google.com/search?q=${encodeURIComponent(query)}`}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="custom-search-query-item"
                  title={query} // 添加标题属性，当鼠标悬停时显示完整内容
                >
                  {query}
                </a>
              ))}
            </div>
          </div>
        </div>
      </div>
    );
  }

  // 如果既没有渲染内容也没有搜索查询，不显示任何内容
  return null;
};

export default GoogleSearchSuggestion;

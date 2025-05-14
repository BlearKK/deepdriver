import React from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '../../ui/card';
import { Badge } from '../../ui/badge';
import { Accordion, AccordionContent, AccordionItem, AccordionTrigger } from '../../ui/accordion';
import { RELATIONSHIP_COLORS } from '../constants';
import { SearchResult } from '../types';

interface ResultCardProps {
  result: SearchResult;
  index: number;
  showAnimation?: boolean;
}

const ResultCard: React.FC<ResultCardProps> = ({ 
  result, 
  index, 
  showAnimation = true 
}) => {
  // 获取关系类型对应的样式
  const cardStyle = RELATIONSHIP_COLORS[result.relationship_type] || 'bg-gray-100 text-gray-800 border-gray-300';
  
  return (
    <div 
      className={showAnimation ? "animate-fadeIn" : ""} 
      style={showAnimation ? { animationDelay: `${index * 50}ms` } : undefined}
    >
      <Card className="border shadow-sm">
        <CardHeader className="p-3 pb-1 flex flex-row justify-between items-center">
          <CardTitle className="text-base">{result.risk_item}</CardTitle>
          <Badge className={cardStyle}>
            {result.relationship_type}
          </Badge>
        </CardHeader>
        
        {result.finding_summary && (
          <CardContent className="p-3 pt-0">
            <Accordion type="single" collapsible>
              <AccordionItem value="details">
                <AccordionTrigger className="text-sm py-1">View Details</AccordionTrigger>
                <AccordionContent>
                  <p className="text-sm whitespace-pre-line">{result.finding_summary}</p>
                </AccordionContent>
              </AccordionItem>
            </Accordion>
          </CardContent>
        )}
      </Card>
    </div>
  );
};

export default ResultCard;

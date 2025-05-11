import * as React from "react";
import { format, setMonth, setYear, getYear, getMonth } from "date-fns";
import { Calendar as CalendarIcon, ChevronLeft, ChevronRight } from "lucide-react";
import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import { Popover, PopoverContent, PopoverTrigger } from "@/components/ui/popover";
import { Input } from "@/components/ui/input";

interface MonthPickerProps {
  date: Date | undefined;
  setDate: (date: Date | undefined) => void;
  label?: string;
  placeholder?: string;
  className?: string;
}

// Month names
const MONTHS = [
  "Jan", "Feb", "Mar", "Apr", "May", "Jun", 
  "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"
];

export function MonthPicker({
  date,
  setDate,
  label = "Select Month",
  placeholder = "Select Month",
  className,
}: MonthPickerProps) {
  // 当前显示的日期（默认为当前日期）
  const [currentDate, setCurrentDate] = React.useState<Date>(
    date || new Date()
  );
  
  // 是否显示年份输入
  const [showYearInput, setShowYearInput] = React.useState(false);
  const [yearInput, setYearInput] = React.useState<string>(
    currentDate ? getYear(currentDate).toString() : ""
  );
  
  // 处理年份变化
  const handleYearChange = (year: number) => {
    const newDate = setYear(currentDate, year);
    setCurrentDate(newDate);
    setShowYearInput(false);
  };
  
  // 处理月份选择
  const handleMonthSelect = (month: number) => {
    const newDate = setMonth(currentDate, month);
    setDate(newDate);
  };
  
  // 处理年份输入提交
  const handleYearInputSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    const year = parseInt(yearInput);
    if (!isNaN(year) && year >= 1900 && year <= 2100) {
      handleYearChange(year);
    }
  };
  
  // 切换到上一年
  const prevYear = () => {
    const newDate = setYear(currentDate, getYear(currentDate) - 1);
    setCurrentDate(newDate);
    setYearInput(getYear(newDate).toString());
  };
  
  // 切换到下一年
  const nextYear = () => {
    const newDate = setYear(currentDate, getYear(currentDate) + 1);
    setCurrentDate(newDate);
    setYearInput(getYear(newDate).toString());
  };

  return (
    <div className={cn("grid gap-2", className)}>
      {label && <div className="text-sm font-medium">{label}</div>}
      <Popover>
        <PopoverTrigger asChild>
          <Button
            variant={"outline"}
            className={cn(
              "w-full justify-start text-left font-normal",
              !date && "text-muted-foreground"
            )}
          >
            <CalendarIcon className="mr-2 h-4 w-4" />
            {date ? format(date, "yyyy-MM") : placeholder}
          </Button>
        </PopoverTrigger>
        <PopoverContent className="w-auto p-0" align="start">
          <div className="p-3">
            {/* 年份选择器 */}
            <div className="flex items-center justify-between mb-4">
              <Button 
                variant="ghost" 
                size="icon"
                onClick={prevYear}
              >
                <ChevronLeft className="h-4 w-4" />
              </Button>
              
              {showYearInput ? (
                <form onSubmit={handleYearInputSubmit} className="flex-1 mx-2">
                  <Input
                    value={yearInput}
                    onChange={(e) => setYearInput(e.target.value)}
                    className="text-center"
                    autoFocus
                    onBlur={handleYearInputSubmit}
                  />
                </form>
              ) : (
                <Button 
                  variant="ghost" 
                  onClick={() => setShowYearInput(true)}
                  className="flex-1 font-medium"
                >
                  {getYear(currentDate)}
                </Button>
              )}
              
              <Button 
                variant="ghost" 
                size="icon"
                onClick={nextYear}
              >
                <ChevronRight className="h-4 w-4" />
              </Button>
            </div>
            
            {/* 月份网格 */}
            <div className="grid grid-cols-3 gap-2">
              {MONTHS.map((month, index) => {
                const isSelected = date && 
                  getYear(date) === getYear(currentDate) && 
                  getMonth(date) === index;
                  
                return (
                  <Button
                    key={month}
                    variant={isSelected ? "default" : "outline"}
                    className={cn(
                      "h-9",
                      isSelected && "bg-primary text-primary-foreground"
                    )}
                    onClick={() => handleMonthSelect(index)}
                  >
                    {month}
                  </Button>
                );
              })}
            </div>
          </div>
        </PopoverContent>
      </Popover>
    </div>
  );
}

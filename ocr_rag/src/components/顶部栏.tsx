import { Button } from "./ui/button";

interface 顶部栏Props {
  currentSessionTitle?: string;
}

export function 顶部栏({ currentSessionTitle }: 顶部栏Props) {
  return (
    <div className="h-12 bg-background border-b border-border flex items-center justify-center px-6">
      {/* 中间标题 */}
      <span className="text-sm font-medium text-foreground/80">
        {currentSessionTitle || "未命名会话"}
      </span>
    </div>
  );
}
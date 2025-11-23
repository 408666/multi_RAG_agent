#!/usr/bin/env python3
"""
多模态 RAG 工作台后端启动脚本
"""

import os
import sys
from pathlib import Path

# 添加当前目录到 Python 路径
current_dir = Path(__file__).parent
sys.path.insert(0, str(current_dir))

def check_environment():
    """检查环境配置"""
    print("🔍 检查环境配置...")
    
    # 检查 .env 文件
    env_file = current_dir / ".env"
    if not env_file.exists():
        print("⚠️  未找到 .env 文件，使用默认配置")
        print("💡 建议创建 .env 文件并配置 OPENAI_API_KEY")
    
    # 检查 OpenAI API Key
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("⚠️  未配置 OPENAI_API_KEY")
        print("💡 请在 .env 文件中设置: OPENAI_API_KEY=your_api_key")
    else:
        print(f"✅ OpenAI API Key 已配置 (前6位: {api_key[:6]}...)")
    
    # 检查日志目录
    logs_dir = current_dir / "logs"
    if not logs_dir.exists():
        logs_dir.mkdir(exist_ok=True)
        print(f"📁 创建日志目录: {logs_dir}")
    
    print("✅ 环境检查完成\n")

def install_dependencies():
    """检查并安装依赖"""
    print("📦 检查依赖包...")
    
    try:
        import fastapi
        import uvicorn
        import langchain
        print("✅ 主要依赖包已安装")
    except ImportError as e:
        print(f"❌ 缺少依赖包: {e}")
        print("💡 请运行: pip install -r requirements.txt")
        return False
    
    return True

def main():
    """主函数"""
    print("🚀 启动多模态 RAG 工作台后端服务")
    print("=" * 50)
    
    # 检查环境
    check_environment()
    
    # 检查依赖
    if not install_dependencies():
        sys.exit(1)
    
    # 启动服务
    print("🌟 启动 FastAPI 服务...")
    print("📍 API 文档: http://localhost:8000/docs")
    print("💬 流式聊天: http://localhost:8000/api/chat/stream")
    print("⏹️  停止服务: Ctrl+C")
    print("-" * 50)
    
    try:
        from main import app
        import uvicorn
        from config import settings
        
        uvicorn.run(
            app,
            host=settings.host,
            port=settings.port,
            log_level=settings.log_level.lower(),
            reload=settings.debug
        )
    except KeyboardInterrupt:
        print("\n👋 服务已停止")
    except Exception as e:
        print(f"❌ 启动失败: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main() 
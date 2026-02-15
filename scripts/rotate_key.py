#!/usr/bin/env python3
"""
密钥轮换脚本
用于安全地更换 Exchange 邮箱密码加密密钥

使用方法：
    # 验证模式（不实际修改）
    python scripts/rotate_key.py --dry-run --old-key "旧密钥" --new-key "新密钥"
    
    # 实际轮换
    python scripts/rotate_key.py --old-key "旧密钥" --new-key "新密钥"
    
    # 使用环境变量
    python scripts/rotate_key.py --new-key "新密钥"  # 从 EXCHANGE_ENCRYPTION_KEY 读取旧密钥

生成新密钥：
    python -c "from app.utils.crypto import generate_encryption_key; print(generate_encryption_key())"
"""
import argparse
import asyncio
import os
import sys

# 添加项目根目录到 Python 路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# 设置环境变量以启用开发模式（如果需要）
if not os.getenv("EXCHANGE_ENCRYPTION_KEY"):
    os.environ["DEV_MODE"] = "true"


async def main():
    parser = argparse.ArgumentParser(
        description="Exchange 邮箱密码加密密钥轮换工具",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )
    parser.add_argument(
        "--old-key",
        help="旧的加密密钥（默认从环境变量 EXCHANGE_ENCRYPTION_KEY 读取）"
    )
    parser.add_argument(
        "--new-key",
        required=True,
        help="新的加密密钥"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="验证模式：只检查旧密钥能否解密，不实际修改数据"
    )
    
    args = parser.parse_args()
    
    # 获取旧密钥
    old_key = args.old_key
    if not old_key:
        from app.settings import settings
        old_key = settings.EXCHANGE_ENCRYPTION_KEY
        if not old_key:
            print("❌ 错误：未指定旧密钥，且环境变量 EXCHANGE_ENCRYPTION_KEY 未设置")
            sys.exit(1)
        print(f"ℹ️  使用环境变量中的旧密钥")
    
    new_key = args.new_key
    
    # 初始化数据库
    print("🔌 连接数据库...")
    from tortoise import Tortoise
    from app.settings import settings as app_settings
    await Tortoise.init(config=app_settings.TORTOISE_ORM)
    
    try:
        # 导入轮换器
        from app.utils.key_rotator import KeyRotator
        
        rotator = KeyRotator(old_key, new_key)
        
        # 验证密钥
        print("\n🔑 验证密钥...")
        key_check = rotator.verify_keys()
        
        if not key_check["old_key_valid"]:
            print("❌ 错误：旧密钥无效")
            sys.exit(1)
        print("✅ 旧密钥验证通过")
        
        if not key_check["new_key_valid"]:
            print("❌ 错误：新密钥无效")
            sys.exit(1)
        print("✅ 新密钥验证通过")
        
        # 执行轮换
        mode = "验证" if args.dry_run else "轮换"
        print(f"\n🔄 开始{mode}...")
        
        result = await rotator.rotate_all_accounts(dry_run=args.dry_run)
        
        # 输出结果
        print(f"\n{'='*50}")
        print(f"  {mode}完成")
        print(f"{'='*50}")
        print(f"  总计: {result['total']} 个账户")
        print(f"  成功: {result['success']} 个")
        print(f"  失败: {result['failed']} 个")
        
        if result["failures"]:
            print(f"\n❌ 失败列表:")
            for f in result["failures"]:
                print(f"  - {f['email']}: {f['error']}")
        
        if args.dry_run:
            print(f"\n💡 提示: 这是验证模式，数据未被修改")
            print(f"   确认无误后，移除 --dry-run 参数执行实际轮换")
        else:
            print(f"\n✅ 密钥轮换完成！")
            print(f"   请更新配置中的 EXCHANGE_ENCRYPTION_KEY 为新密钥")
        
    finally:
        await Tortoise.close_connections()


if __name__ == "__main__":
    asyncio.run(main())

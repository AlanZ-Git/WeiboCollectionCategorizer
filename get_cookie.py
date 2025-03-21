import os
import json
import sys
import logging

# 设置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("weibo-cookie")

def print_instructions():
    """打印获取Cookie的详细指导"""
    print("\n===== 微博Cookie获取指南 =====")
    print("1. 使用Chrome或Firefox浏览器访问 https://m.weibo.cn 并登录您的账号")
    print("2. 登录成功后，按F12打开开发者工具")
    print("3. 在开发者工具中，选择'Network'（网络）选项卡")
    print("4. 在页面上刷新或点击任意微博内容，观察网络请求")
    print("5. 在网络请求列表中，找到任意一个请求（例如api/config或getIndex）")
    print("6. 点击该请求，在右侧面板中找到'Headers'（请求头）")
    print("7. 在Headers中找到'Cookie:'开头的行")
    print("8. 复制整个Cookie值（从Cookie:后面开始，到该行结束）")
    print("9. 将复制的内容粘贴到下面的输入提示中")
    print("\n注意：Cookie包含您的登录凭证，请勿分享给他人！")
    print("===========================\n")

def save_cookie(cookie):
    """保存Cookie到单独的cookie.json文件"""
    base_dir = os.path.dirname(os.path.abspath(__file__))
    cookie_path = os.path.join(base_dir, 'cookie.json')
    
    # 创建Cookie数据
    cookie_data = {"cookie": cookie}
    
    # 保存Cookie到cookie.json
    try:
        with open(cookie_path, 'w', encoding='utf-8') as f:
            json.dump(cookie_data, f, ensure_ascii=False, indent=4)
        logger.info(f"Cookie已成功保存到文件: {cookie_path}")
        return True
    except Exception as e:
        logger.error(f"保存Cookie文件失败: {e}")
        return False

def validate_cookie(cookie):
    """简单验证Cookie格式"""
    if not cookie or len(cookie) < 20:
        return False
    
    # 检查是否包含常见的Cookie键
    common_keys = ['SUB', 'SUBP', '_T_WM']
    for key in common_keys:
        if key not in cookie:
            logger.warning(f"Cookie中缺少常见键: {key}，可能不完整")
    
    return True

def main():
    print_instructions()
    
    try:
        cookie = input("请粘贴您的微博Cookie: ").strip()
        
        if not validate_cookie(cookie):
            logger.warning("输入的Cookie格式可能不正确，请确认是否完整复制")
            confirm = input("是否仍要保存此Cookie? (y/n): ").strip().lower()
            if confirm != 'y':
                logger.info("已取消保存Cookie")
                return
        
        if save_cookie(cookie):
            print("\n✅ Cookie已成功保存！")
            print("现在您可以运行startup.py脚本来爬取微博了。")
        else:
            print("\n❌ Cookie保存失败，请检查日志获取详细信息。")
    
    except KeyboardInterrupt:
        print("\n已取消操作")
    except Exception as e:
        logger.error(f"发生错误: {e}")
        print(f"\n❌ 发生错误: {e}")

if __name__ == "__main__":
    main()
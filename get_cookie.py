import os
import json
import sys
import logging

# 设置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("weibo-cookie")

def print_instructions():
    """打印获取Cookie的详细指导"""
    instructions = """

===== 微博Cookie获取指南 =====
1. 使用Chrome或Firefox浏览器访问 https://m.weibo.cn 并登录您的账号
2. 登录成功后，按F12打开开发者工具
3. 在开发者工具中，选择'Network'（网络）选项卡
4. 在页面上刷新或点击任意微博内容，观察网络请求
5. 在网络请求列表中，找到任意一个请求（例如api/config或getIndex）
6. 点击该请求，在右侧面板中找到'Headers'（请求头）
7. 在Headers中找到'Cookie:'开头的行
8. 复制整个Cookie值（从Cookie:后面开始，到该行结束）
9. 将复制的内容粘贴到下面的输入提示中

注意：Cookie包含您的登录凭证，请勿分享给他人！
===========================

"""
    print(instructions)

def save_cookie(cookie):
    """保存Cookie到单独的setting.json文件"""
    base_dir = os.path.dirname(os.path.abspath(__file__))
    cookie_path = os.path.join(base_dir, 'setting.json')
    
    # 创建Cookie数据
    cookie_data = {"cookie": cookie}
    
    # 保存Cookie到setting.json
    try:
        with open(cookie_path, 'w', encoding='utf-8') as f:
            json.dump(cookie_data, f, ensure_ascii=False, indent=4)
        logger.info(f"Cookie已成功保存到文件: {cookie_path}")
        return True
    except Exception as e:
        logger.error(f"保存Cookie文件失败: {e}")
        return False

def get_cookie_interactive():
    """交互式获取并保存Cookie"""
    print_instructions()
    
    try:
        cookie = input("请粘贴您的微博Cookie: ").strip()
        
        if save_cookie(cookie):
            print("\n✅ Cookie已成功保存！")
            return cookie
        else:
            print("\n❌ Cookie保存失败，请检查日志获取详细信息。")
            return None
    
    except KeyboardInterrupt:
        print("\n已取消操作")
        return None
    except Exception as e:
        logger.error(f"发生错误: {e}")
        print(f"\n❌ 发生错误: {e}")
        return None

def load_cookie():
    """从setting.json文件加载Cookie"""
    base_dir = os.path.dirname(os.path.abspath(__file__))
    cookie_path = os.path.join(base_dir, 'setting.json')
    
    try:
        if os.path.exists(cookie_path):
            with open(cookie_path, 'r', encoding='utf-8') as f:
                cookie_data = json.load(f)
                return cookie_data.get("cookie")
        else:
            logger.warning("Cookie文件不存在")
            return None
    except Exception as e:
        logger.error(f"加载Cookie文件失败: {e}")
        return None

# 如果直接运行此脚本，则执行交互式获取Cookie
if __name__ == "__main__":
    cookie = get_cookie_interactive()
    if cookie:
        print("现在您可以运行startup.py脚本来爬取微博了。")
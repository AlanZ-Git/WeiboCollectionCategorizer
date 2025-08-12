import os
import json

from .logger import setup_logger
logger = setup_logger()

def get_config():
    """
    获取配置信息

    Returns:
        dict: 包含配置信息的字典
    """
    # 默认配置
    return {
        "cookie_path": "setting.json"
    }

def get_cookie(config):
    """
    从配置文件中获取cookie

    Args:
        config: 配置字典

    Returns:
        str: cookie字符串，如果获取失败则返回空字符串
    """
    # 检查是否指定了cookie文件路径
    if 'cookie_path' in config and config['cookie_path']:
        cookie_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), config['cookie_path'])
        if os.path.exists(cookie_path):
            try:
                with open(cookie_path, 'r', encoding='utf-8') as f:
                    cookie_data = json.load(f)
                    if 'cookie' in cookie_data and cookie_data['cookie']:
                        return cookie_data['cookie']
            except Exception as e:
                logger.error(f"读取cookie文件出错: {e}")

    logger.warning("未找到有效的cookie配置")
    return ""
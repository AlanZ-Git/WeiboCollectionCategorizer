import re
import json
import requests
from .logger import setup_logger  # 导入日志模块

# 初始化日志
logger = setup_logger()

# 从URL中提取用户ID和微博ID
def extract_ids_from_url(url):
    pattern = r'weibo\.com/(\d+)/(\w+)'
    match = re.search(pattern, url)
    if match:
        user_id = match.group(1)
        weibo_id = match.group(2)
        return user_id, weibo_id
    return None, None

# 获取单条微博
def get_single_weibo(user_id, weibo_id, cookie):
    logger.debug("使用HTML解析方式获取微博数据")
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/86.0.4240.111 Safari/537.36",
        "Cookie": cookie,
        "X-Requested-With": "XMLHttpRequest",
        "Referer": f"https://m.weibo.cn/detail/{weibo_id}"
    }

    # 使用微博详情页API
    url = f"https://m.weibo.cn/detail/{weibo_id}"
    try:
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        html = response.text
        data_pattern = r'var \$render_data = \[(.*?)\]\[0\] \|\| \{\};'
        match = re.search(data_pattern, html, re.DOTALL)

        if match:
            json_str = match.group(1)
            try:
                render_data = json.loads(json_str)
                if 'status' in render_data:
                    logger.debug("成功从HTML中提取到微博数据")
                    return render_data['status']
            except json.JSONDecodeError:
                logger.error("无法解析详情页中的JSON数据")
        else:
            logger.warning("未找到渲染数据，尝试其他方式提取")

        logger.error("获取微博数据失败")
        return None
    except Exception as e:
        logger.error(f"获取微博数据出错: {e}")
        return None 
import os
import csv
from datetime import datetime

from .path_manager import get_download_path, create_download_directories
from .logger import setup_logger
logger = setup_logger()

def save_to_csv(weibo):
    """
    保存微博数据到CSV文件

    Args:
        weibo: 解析后的微博数据字典

    Returns:
        bool: 保存成功返回True，否则返回False
    """
    if not weibo:
        return False

    # 获取下载路径
    download_paths = create_download_directories(get_download_path())
    file_dir = download_paths['weibo']

    # 使用当天日期作为文件名
    today = datetime.now().strftime('%Y%m%d')
    file_path = os.path.join(file_dir, f"{today}.csv")

    headers = [
        'id', 'bid', 'user_id', 'screen_name', 'text', 'article_url', 'topics',
        'pics', 'videos', 'source_url', 'retweet_id', 'retweet_text',
        'retweet_screen_name', 'retweet_user_id', 'retweet_source_url'
    ]

    is_file_exist = os.path.isfile(file_path)

    with open(file_path, 'a', encoding='utf-8-sig', newline='') as f:
        writer = csv.writer(f)
        if not is_file_exist:
            writer.writerow(headers)

        row = [weibo.get(key, '') for key in headers]
        writer.writerow(row)

    logger.info(f"微博已保存到 {file_path}")
    return True 
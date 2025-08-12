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
        'id',                    # 微博ID（数字格式）
        'bid',                   # 微博BID（字符串格式，用于URL）
        'user_id',               # 用户ID（数字格式）
        'screen_name',           # 用户昵称
        'text',                  # 微博正文内容
        'article_url',           # 文章链接（如果有的话）
        'topics',                # 话题标签（用逗号分隔）
        'pics',                  # 图片本地路径（用逗号分隔）
        'videos',                # 视频本地路径（用逗号分隔）
        'source_url',            # 微博源链接
        'retweet_id',            # 转发微博ID
        'retweet_text',          # 转发微博内容
        'retweet_screen_name',   # 转发微博用户昵称
        'retweet_user_id',       # 转发微博用户ID
        'retweet_source_url'     # 转发微博源链接
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
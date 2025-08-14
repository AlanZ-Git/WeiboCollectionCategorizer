import os
import argparse
import json
from unittest import TestResult

from lib.config import get_cookie
from lib.weibo_api import extract_ids_from_url, get_single_weibo
from lib.weibo_parser import parse_weibo_data
from lib.data_storage import save_to_csv
from lib.path_manager import get_download_path, create_download_directories
from lib.logger import setup_logger


logger = setup_logger('test')


def _get_debug_dir(base_dir: str) -> str:
    debug_dir = os.path.join(base_dir, 'debug')
    os.makedirs(debug_dir, exist_ok=True)
    return debug_dir


def process_single_weibo(url: str, overwrite_pics: bool = False, overwrite_videos: bool = False) -> dict:
    """
    输入一条微博链接，保存：
    1) 原始下载数据（parse 之前）到 debug/{bid}_raw.json
    2) 整理后数据（parse 之后）到 debug/{bid}_parsed.json，并追加到当天 CSV

    Args:
        url: 微博详情页链接，如 https://weibo.com/<user_id>/<bid>
        overwrite_pics: 是否覆盖已下载的图片
        overwrite_videos: 是否覆盖已下载的视频

    Returns:
        dict: { 'raw_json_path', 'parsed_json_path', 'csv_path', 'weibo' }
    """
    # 路径准备
    download_paths = create_download_directories(get_download_path())
    base_dir = download_paths['base']
    weibo_csv_dir = download_paths['weibo']
    debug_dir = _get_debug_dir(base_dir)

    # Cookie
    cookie = get_cookie()


    # 解析URL
    user_id, weibo_id = extract_ids_from_url(url)
    if not user_id or not weibo_id:
        raise ValueError(f'无法从URL中提取用户ID和微博ID: {url}')

    # 获取原始微博数据
    weibo_data = get_single_weibo(user_id, weibo_id, cookie)
    if not weibo_data:
        raise RuntimeError('获取微博数据失败')

    bid = weibo_data.get('bid', weibo_id)

    # 保存原始数据（parse 前）
    raw_json_path = os.path.join(debug_dir, f"{bid}_raw.json")
    with open(raw_json_path, 'w', encoding='utf-8') as f:
        json.dump(weibo_data, f, ensure_ascii=False, indent=2)
    logger.info(f"原始数据已保存: {raw_json_path}")

    # 解析并保存解析后数据
    weibo = parse_weibo_data(weibo_data, user_id, overwrite_pics=overwrite_pics, overwrite_videos=overwrite_videos)
    if not weibo:
        raise RuntimeError('解析微博数据失败')

    parsed_json_path = os.path.join(debug_dir, f"{bid}_parsed.json")
    with open(parsed_json_path, 'w', encoding='utf-8') as f:
        json.dump(weibo, f, ensure_ascii=False, indent=2)
    logger.info(f"解析后数据已保存: {parsed_json_path}")

    # 追加保存到当天 CSV
    save_to_csv(weibo)
    from datetime import datetime
    today = datetime.now().strftime('%Y%m%d')
    csv_path = os.path.join(weibo_csv_dir, f"{today}.csv")

    return {
        'raw_json_path': raw_json_path,
        'parsed_json_path': parsed_json_path,
        'csv_path': csv_path,
        'weibo': weibo,
    }


if __name__ == '__main__':
    # 转发微博
    url = 'https://weibo.com/2194035935/PEFjgcwx6'
    # 原微博
    url = 'https://weibo.com/1233486457/PEBNUBoJB'

    process_single_weibo(url, overwrite_pics=True, overwrite_videos=True)


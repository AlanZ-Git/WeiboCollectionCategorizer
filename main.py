import os
import multiprocessing

# 获取CPU核心数并设置为核心数-4（最小值为1）
cpu_count = max(multiprocessing.cpu_count() - 4, 1)
os.environ["NUMEXPR_MAX_THREADS"] = str(cpu_count)

import argparse
import sys
import csv

from lib.config import get_config, get_cookie  # 从config.py导入配置函数
from lib.weibo_api import extract_ids_from_url, get_single_weibo  # 从weibo_api.py导入函数
from lib.weibo_parser import parse_weibo_data  # 从新的weibo_parser.py导入函数
from lib.data_storage import save_to_csv  # 从新的data_storage.py导入函数
from lib.task_manager import get_pending_tasks, update_task_status, create_task, add_task  # 从新的task_manager.py导入函数
from lib.get_cookie import get_cookie_interactive, load_cookie  # 导入cookie获取函数
from lib.path_manager import get_download_path, create_download_directories  # 导入路径管理函数
from lib.logger import setup_logger
logger = setup_logger('weibo')


def main(ignore_status=False, overwrite_pics=False, overwrite_videos=False):
    # 获取下载路径
    download_paths = create_download_directories(get_download_path())
    logger.info(f"下载路径设置为: {download_paths['base']}")

    # 从任务文件获取待处理任务
    tasks = get_pending_tasks(ignore_status)
    if not tasks:
        logger.info("没有待处理的任务")
        return

    logger.info(f"找到 {len(tasks)} 个待处理任务")

    # 获取配置
    config = get_config()
    cookie = get_cookie(config)

    # 检查cookie是否为空，如果为空则尝试从setting.json加载或交互式获取
    if not cookie:
        logger.warning("配置中的Cookie为空，尝试从setting.json加载")
        cookie = load_cookie()

        # 如果仍然为空，则交互式获取
        if not cookie:
            logger.info("未找到已保存的Cookie，启动交互式获取流程")
            cookie = get_cookie_interactive()

            # 如果用户取消或获取失败
            if not cookie:
                logger.error("无法获取Cookie，程序退出")
                return

    # 处理每个任务
    for task in tasks:
        url = task['url']
        logger.info(f"开始处理任务: {url}")

        # 获取用户ID和微博ID
        user_id, weibo_id = extract_ids_from_url(url)
        if not user_id or not weibo_id:
            logger.error(f"无法从URL中提取用户ID和微博ID: {url}")
            update_task_status(url, 'failed')
            continue

        # 获取微博数据
        weibo_data = get_single_weibo(user_id, weibo_id, cookie)
        if not weibo_data:
            logger.error("获取微博数据失败")
            update_task_status(url, 'failed')
            continue

        # 解析微博数据
        weibo = parse_weibo_data(weibo_data, user_id, overwrite_pics=overwrite_pics, overwrite_videos=overwrite_videos)
        if not weibo:
            logger.error("解析微博数据失败")
            update_task_status(url, 'failed')
            continue

        # 保存到CSV
        if save_to_csv(weibo):
            logger.info(f"微博爬取成功并已保存：{weibo.get('text', '')[:30]}...")
            update_task_status(url, 'completed')
        else:
            logger.error("保存微博数据失败")
            update_task_status(url, 'failed')

def fetch_favorites(max_pages=5, add_to_tasks=False):
    """获取收藏微博"""
    logger.info("开始获取收藏微博...")

    task = create_task('favorites', max_pages=max_pages)
    result = task.run()

    if result['status'] == 'success':
        logger.info(result['message'])
        logger.info(f"数据已保存到: {result['data']['filename']}")

        # 如果需要将URL添加到下载任务
        if add_to_tasks:
            # 读取保存的CSV文件
            with open(result['data']['filename'], mode='r', encoding='utf-8-sig') as file:
                reader = csv.DictReader(file)
                urls = [row['url'] for row in reader]

            # 添加到下载任务
            added_count = 0
            for url in urls:
                if add_task(url, notes='从收藏微博自动添加'):
                    added_count += 1

            logger.info(f"已将 {added_count} 个收藏微博URL添加到下载任务")
    else:
        logger.error(f"获取收藏微博失败: {result['message']}")

    return result

if __name__ == "__main__":
    # 检查命令行参数
    ignore_status = True
    overwrite_pics = True
    overwrite_videos = True

    parser = argparse.ArgumentParser(description="微博爬取工具")
    parser.add_argument('--ignore-status', action='store_true', help="忽略任务状态，将处理所有任务")
    parser.add_argument('--overwrite-pics', action='store_true', help="启用图片覆盖模式，将重新下载所有图片")
    parser.add_argument('--overwrite-videos', action='store_true', help="启用视频覆盖模式，将重新下载所有视频")
    parser.add_argument('--favorites', action='store_true', help='获取收藏微博')
    parser.add_argument('--max-pages', type=int, default=5, help='最大爬取页数')
    parser.add_argument('--add-to-tasks', action='store_true', help='将收藏微博添加到下载任务')

    args = parser.parse_args()

    if args.ignore_status:
        ignore_status = True
        logger.info("忽略任务状态，将处理所有任务")
    if args.overwrite_pics:
        overwrite_pics = True
        logger.info("启用图片覆盖模式，将重新下载所有图片")
    if args.overwrite_videos:
        overwrite_videos = True
        logger.info("启用视频覆盖模式，将重新下载所有视频")

    if args.favorites:
        fetch_favorites(max_pages=args.max_pages, add_to_tasks=args.add_to_tasks)
    else:
        main(ignore_status, overwrite_pics, overwrite_videos)
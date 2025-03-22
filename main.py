import sys
from config import get_config, get_cookie  # 从config.py导入配置函数
from logger import setup_logger  # 导入新的日志模块
from weibo_api import extract_ids_from_url, get_single_weibo  # 从weibo_api.py导入函数
from weibo_parser import parse_weibo_data  # 从新的weibo_parser.py导入函数
from data_storage import save_to_csv  # 从新的data_storage.py导入函数
from task_manager import get_pending_tasks, update_task_status  # 从新的task_manager.py导入函数
from get_cookie import get_cookie_interactive, load_cookie  # 导入cookie获取函数

# 初始化日志
logger = setup_logger()

def main(ignore_status=False, overwrite_pics=False, overwrite_videos=False):
    # 从任务文件获取待处理任务
    tasks = get_pending_tasks(ignore_status)
    if not tasks:
        logger.info("没有待处理的任务")
        return

    logger.info(f"找到 {len(tasks)} 个待处理任务")

    # 获取配置
    config = get_config()
    cookie = get_cookie(config)

    # 检查cookie是否为空，如果为空则尝试从cookie.json加载或交互式获取
    if not cookie:
        logger.warning("配置中的Cookie为空，尝试从cookie.json加载")
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

if __name__ == "__main__":
    # 检查命令行参数
    ignore_status = True
    overwrite_pics = True
    overwrite_videos = True
    
    for arg in sys.argv[1:]:
        if arg == '--ignore-status':
            ignore_status = True
            logger.info("忽略任务状态，将处理所有任务")
        elif arg == '--overwrite-pics':
            overwrite_pics = True
            logger.info("启用图片覆盖模式，将重新下载所有图片")
        elif arg == '--overwrite-videos':
            overwrite_videos = True
            logger.info("启用视频覆盖模式，将重新下载所有视频")

    main(ignore_status, overwrite_pics, overwrite_videos)
import os
import sys
import json
import re
import requests
from datetime import datetime
import csv
import logging
import logging.config

# 设置日志
if not os.path.isdir("log/"):
    os.makedirs("log/")
logging_path = os.path.split(os.path.realpath(__file__))[0] + os.sep + "logging.conf"
if os.path.exists(logging_path):
    logging.config.fileConfig(logging_path)
else:
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("weibo")


# 从URL中提取用户ID和微博ID
def extract_ids_from_url(url):
    pattern = r'weibo\.com/(\d+)/(\w+)'
    match = re.search(pattern, url)
    if match:
        user_id = match.group(1)
        weibo_id = match.group(2)
        return user_id, weibo_id
    return None, None

# 获取配置
def get_config():
    # 默认配置
    return {
        "cookie_path": "cookie.json"
    }

# 获取cookie
def get_cookie(config):
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

# 获取单条微博
def get_single_weibo(user_id, weibo_id, cookie):
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/86.0.4240.111 Safari/537.36",
        "Cookie": cookie,
        "Accept": "application/json, text/plain, */*"
    }
    
    # 尝试获取微博详情
    url = f"https://m.weibo.cn/statuses/show?id={weibo_id}"
    try:
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        
        # 添加调试日志
        logger.debug(f"API响应: {response.text[:200]}...")
        
        # 检查响应内容是否为空
        if not response.text.strip():
            logger.error("API返回空响应")
            return None
        
        # 检查响应是否为HTML而不是JSON
        if response.text.strip().startswith('<'):
            logger.warning("API返回HTML而不是JSON，可能需要验证或cookie已过期")
            return get_single_weibo_backup(user_id, weibo_id, cookie)
            
        try:
            data = response.json()
            
            if data.get('ok') == 1 and 'data' in data:
                return data['data']
            else:
                logger.error(f"获取微博失败: {data.get('msg', '未知错误')}")
                return None
        except json.JSONDecodeError as je:
            logger.error(f"JSON解析错误: {je}, 响应内容: {response.text[:100]}...")
            
            # 尝试使用备用API
            return get_single_weibo_backup(user_id, weibo_id, cookie)
    except Exception as e:
        logger.error(f"请求微博详情出错: {e}")
        # 尝试使用备用API
        return get_single_weibo_backup(user_id, weibo_id, cookie)

# 添加备用API获取微博
def get_single_weibo_backup(user_id, weibo_id, cookie):
    logger.info("尝试使用备用API获取微博")
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/86.0.4240.111 Safari/537.36",
        "Cookie": cookie,
        "X-Requested-With": "XMLHttpRequest",
        "Referer": f"https://m.weibo.cn/detail/{weibo_id}"
    }
    
    # 使用微博详情页API
    url = f"https://m.weibo.cn/detail/{weibo_id}"
    try:
        # 先获取详情页
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        
        # 从HTML中提取微博数据
        html = response.text
        data_pattern = r'var \$render_data = \[(.*?)\]\[0\] \|\| \{\};'
        match = re.search(data_pattern, html, re.DOTALL)
        
        if match:
            json_str = match.group(1)
            try:
                render_data = json.loads(json_str)
                if 'status' in render_data:
                    logger.info("成功从HTML中提取到微博数据")
                    return render_data['status']
            except json.JSONDecodeError:
                logger.error("无法解析详情页中的JSON数据")
        else:
            logger.warning("未找到渲染数据，尝试其他方式提取")
        
        # 如果上面的方法失败，尝试使用另一个API
        api_url = f"https://m.weibo.cn/api/container/getIndex?type=uid&value={user_id}&containerid=107603{user_id}"
        response = requests.get(api_url, headers=headers, timeout=10)
        response.raise_for_status()
        
        # 检查响应是否为HTML
        if response.text.strip().startswith('<'):
            logger.warning("API返回HTML而不是JSON，可能需要验证或cookie已过期")
            return None
            
        data = response.json()
        
        if data.get('ok') == 1 and 'data' in data:
            cards = data['data'].get('cards', [])
            for card in cards:
                if card.get('mblog', {}).get('id') == weibo_id or card.get('mblog', {}).get('bid') == weibo_id:
                    logger.info("成功从用户时间线中找到目标微博")
                    return card['mblog']
        
        # 尝试第三种方法：通过微博详情API
        detail_api_url = f"https://m.weibo.cn/api/container/getIndex?type=uid&value={user_id}&containerid=230283{user_id}_-_WEIBO_SECOND_PROFILE_WEIBO&page_type=03&page=1"
        response = requests.get(detail_api_url, headers=headers, timeout=10)
        response.raise_for_status()
        
        if response.text.strip().startswith('<'):
            logger.warning("第三种API方法返回HTML而不是JSON")
            return None
            
        data = response.json()
        
        if data.get('ok') == 1 and 'data' in data:
            cards = data['data'].get('cards', [])
            for card in cards:
                if 'mblog' in card and (card['mblog'].get('id') == weibo_id or card['mblog'].get('bid') == weibo_id):
                    logger.info("成功从第三种API方法中找到目标微博")
                    return card['mblog']
        
        logger.error("所有备用API方法都无法获取微博数据")
        return None
    except Exception as e:
        logger.error(f"备用API请求出错: {e}")
        return None

# 解析微博数据
def parse_weibo_data(weibo_data, user_id):
    if not weibo_data:
        return None
    
    weibo = {}
    weibo['user_id'] = user_id
    weibo['id'] = weibo_data.get('id', '')
    weibo['bid'] = weibo_data.get('bid', '')
    
    user = weibo_data.get('user', {})
    weibo['screen_name'] = user.get('screen_name', '')
    
    # 处理微博文本
    text = weibo_data.get('text', '')
    weibo['text'] = re.sub('<[^<]+?>', '', text).replace('\n', '').strip()
    
    # 获取图片
    pics = []
    if 'pics' in weibo_data and weibo_data['pics']:
        for pic in weibo_data['pics']:
            if 'large' in pic and 'url' in pic['large']:
                pics.append(pic['large']['url'])
    weibo['pics'] = ','.join(pics)
    
    # 获取视频
    weibo['video_url'] = ''
    if 'page_info' in weibo_data and weibo_data['page_info'] and weibo_data['page_info'].get('type') == 'video':
        if 'media_info' in weibo_data['page_info'] and 'stream_url' in weibo_data['page_info']['media_info']:
            weibo['video_url'] = weibo_data['page_info']['media_info']['stream_url']
    
    # 获取文章链接
    weibo['article_url'] = ''
    if 'page_info' in weibo_data and weibo_data['page_info'] and weibo_data['page_info'].get('type') == 'article':
        if 'page_url' in weibo_data['page_info']:
            weibo['article_url'] = weibo_data['page_info']['page_url']
    
    # 获取位置信息
    weibo['location'] = ''
    if 'geo' in weibo_data and weibo_data['geo']:
        if 'address' in weibo_data['geo']:
            weibo['location'] = weibo_data['geo']['address']
    
    # 获取发布时间
    created_at = weibo_data.get('created_at', '')
    try:
        created_time = datetime.strptime(created_at, '%a %b %d %H:%M:%S %z %Y')
        weibo['created_at'] = created_time.strftime('%Y-%m-%d')
        weibo['full_created_at'] = created_time.strftime('%Y-%m-%d %H:%M:%S')
    except:
        weibo['created_at'] = created_at
        weibo['full_created_at'] = created_at
    
    # 获取发布工具
    weibo['source'] = weibo_data.get('source', '')
    
    # 获取互动数据
    weibo['attitudes_count'] = weibo_data.get('attitudes_count', 0)
    weibo['comments_count'] = weibo_data.get('comments_count', 0)
    weibo['reposts_count'] = weibo_data.get('reposts_count', 0)
    
    # 获取话题和@用户
    topics = re.findall(r'#(.*?)#', text)
    weibo['topics'] = ','.join(topics)
    
    at_users = re.findall(r'@([\w-]+)', text)
    weibo['at_users'] = ','.join(at_users)
    
    # 转发微博信息
    weibo['retweet_id'] = ''
    weibo['retweet_text'] = ''
    weibo['retweet_screen_name'] = ''
    weibo['retweet_user_id'] = ''
    weibo['retweet_pics'] = ''
    weibo['retweet_video_url'] = ''
    weibo['retweet_source_url'] = ''
    
    if 'retweeted_status' in weibo_data and weibo_data['retweeted_status']:
        retweet = weibo_data['retweeted_status']
        weibo['retweet_id'] = retweet.get('id', '')
        
        # 交换字段：将当前微博文本存入retweet_text，将原微博文本存入text
        original_text = weibo['text']  # 保存当前微博文本（即转发时的评论）
        
        # 获取原微博文本并存入text
        retweet_text = retweet.get('text', '')
        weibo['text'] = re.sub('<[^<]+?>', '', retweet_text).replace('\n', '').strip()
        
        # 将当前微博文本存入retweet_text
        weibo['retweet_text'] = original_text
        
        # 获取原微博用户信息
        retweet_user = retweet.get('user', {})
        if retweet_user is not None:
            weibo['retweet_screen_name'] = retweet_user.get('screen_name', '')
            weibo['retweet_user_id'] = retweet_user.get('id', '')
        else:
            logger.warning("原微博用户信息不可见")
            weibo['retweet_screen_name'] = '已删除'
            weibo['retweet_user_id'] = ''
        
        # 获取原微博图片
        retweet_pics = []
        if 'pics' in retweet and retweet['pics']:
            for pic in retweet['pics']:
                if 'large' in pic and 'url' in pic['large']:
                    retweet_pics.append(pic['large']['url'])
        weibo['retweet_pics'] = ','.join(retweet_pics)
        
        # 获取原微博视频
        if 'page_info' in retweet and retweet['page_info'] and retweet['page_info'].get('type') == 'video':
            if 'media_info' in retweet['page_info'] and 'stream_url' in retweet['page_info']['media_info']:
                weibo['retweet_video_url'] = retweet['page_info']['media_info']['stream_url']
        
        # 添加原微博源URL
        if weibo['retweet_user_id'] and retweet.get('bid', ''):
            weibo['retweet_source_url'] = f"https://weibo.com/{weibo['retweet_user_id']}/{retweet.get('bid', '')}"
    
    # 添加源URL
    weibo['source_url'] = f"https://weibo.com/{user_id}/{weibo['bid']}"
    
    return weibo

# 保存微博到CSV
def save_to_csv(weibo):
    if not weibo:
        return False
    
    file_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'weibo')
    if not os.path.isdir(file_dir):
        os.makedirs(file_dir)
    
    # 使用当天日期作为文件名
    today = datetime.now().strftime('%Y%m%d')
    file_path = os.path.join(file_dir, f"{today}.csv")
    
    headers = [
        'id', 'bid', 'user_id', 'screen_name', 'text', 'article_url', 'topics', 
        'pics', 'video_url', 'location', 'created_at', 'full_created_at', 'source', 
        'attitudes_count', 'comments_count', 'reposts_count', 'retweet_id', 'at_users',
        'source_url', 'retweet_text', 'retweet_screen_name', 'retweet_user_id', 
        'retweet_pics', 'retweet_video_url', 'retweet_source_url'
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

def get_pending_tasks(ignore_status=False):
    """
    获取待处理的任务
    
    Args:
        ignore_status: 是否忽略状态，如果为True则返回所有任务
    
    Returns:
        任务列表
    """
    from download_tasks import get_pending_tasks
    return get_pending_tasks(ignore_status)

def main(ignore_status=False):
    # 从任务文件获取待处理任务
    from download_tasks import update_task_status
    
    tasks = get_pending_tasks(ignore_status)
    if not tasks:
        logger.info("没有待处理的任务")
        return
    
    logger.info(f"找到 {len(tasks)} 个待处理任务")
    
    # 获取配置
    config = get_config()
    cookie = get_cookie(config)
    
    # 检查cookie是否为空
    if not cookie:
        logger.error("Cookie为空，请确保配置了有效的cookie")
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
        
        logger.info(f"开始爬取用户 {user_id} 的微博 {weibo_id}")
        
        # 获取微博数据
        weibo_data = get_single_weibo(user_id, weibo_id, cookie)
        if not weibo_data:
            logger.error("获取微博数据失败")
            update_task_status(url, 'failed')
            continue
        
        # 解析微博数据
        weibo = parse_weibo_data(weibo_data, user_id)
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
    if len(sys.argv) > 1 and sys.argv[1] == '--ignore-status':
        ignore_status = True
        logger.info("忽略任务状态，将处理所有任务")
    
    main(ignore_status)
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
    logger.info("使用HTML解析方式获取微博数据")
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
            return get_single_weibo_backup(user_id, weibo_id, cookie)

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

        # 如果所有方法都失败，尝试使用备用API
        logger.info("所有主要方法都无法获取微博数据，尝试使用备用API")
        return get_single_weibo_backup(user_id, weibo_id, cookie)
    except Exception as e:
        logger.error(f"获取微博数据出错: {e}")
        # 尝试使用备用API
        logger.info("尝试使用备用API获取微博")
        return get_single_weibo_backup(user_id, weibo_id, cookie)

# 添加备用API获取微博（原来的主要API）
def get_single_weibo_backup(user_id, weibo_id, cookie):
    logger.info("尝试使用JSON API获取微博")
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
            logger.warning("备用API返回HTML而不是JSON，可能需要验证或cookie已过期")
            return None

        try:
            data = response.json()

            if data.get('ok') == 1 and 'data' in data:
                logger.info("成功从JSON API获取微博数据")
                return data['data']
            else:
                logger.error(f"获取微博失败: {data.get('msg', '未知错误')}")
                return None
        except json.JSONDecodeError as je:
            logger.error(f"JSON解析错误: {je}, 响应内容: {response.text[:100]}...")
            return None
    except Exception as e:
        logger.error(f"备用API请求出错: {e}")
        return None

# 下载图片到本地
def download_image(url, user_id, bid, index, overwrite=False):
    """
    下载图片并保存到本地
    
    Args:
        url: 图片URL
        user_id: 用户ID
        bid: 微博bid
        index: 图片序号
        overwrite: 是否覆盖已存在的文件
    
    Returns:
        保存的相对路径，如果下载失败则返回None
    """
    try:
        # 创建media目录
        media_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'media')
        if not os.path.isdir(media_dir):
            os.makedirs(media_dir)
        
        # 从URL中获取文件扩展名
        file_ext = os.path.splitext(url.split('/')[-1])[1]
        if not file_ext or len(file_ext) > 5:  # 如果没有扩展名或扩展名异常
            file_ext = '.jpg'  # 默认使用jpg
        
        # 构建文件名和路径
        filename = f"{user_id}_{bid}_{index}{file_ext}"
        file_path = os.path.join(media_dir, filename)
        relative_path = os.path.join('media', filename)
        
        # 检查文件是否已存在
        if os.path.exists(file_path) and not overwrite:
            logger.info(f"图片已存在，跳过下载: {file_path}")
            return relative_path
        
        # 设置请求头，模拟浏览器行为
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/86.0.4240.111 Safari/537.36",
            "Referer": "https://weibo.com/",
            "Accept": "image/avif,image/webp,image/apng,image/*,*/*;q=0.8"
        }
        
        # 下载图片
        response = requests.get(url, headers=headers, timeout=30, stream=True)
        response.raise_for_status()
        
        # 保存图片
        with open(file_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                if chunk:
                    f.write(chunk)
        
        logger.info(f"图片已{'覆盖' if overwrite and os.path.exists(file_path) else ''}下载到: {file_path}")
        return relative_path
    except Exception as e:
        logger.error(f"下载图片失败: {e}, URL: {url}")
        return None

# 下载视频到本地
def download_video(url, user_id, bid, index, overwrite=False, max_retries=3):
    """
    下载视频并保存到本地
    
    Args:
        url: 视频URL
        user_id: 用户ID
        bid: 微博bid
        index: 视频序号
        overwrite: 是否覆盖已存在的文件
        max_retries: 最大重试次数
    
    Returns:
        保存的相对路径，如果下载失败则返回None
    """
    try:
        # 创建media目录
        media_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'media')
        if not os.path.isdir(media_dir):
            os.makedirs(media_dir)
        
        # 从URL中获取文件扩展名
        file_ext = os.path.splitext(url.split('/')[-1].split('?')[0])[1]
        if not file_ext or len(file_ext) > 5:  # 如果没有扩展名或扩展名异常
            file_ext = '.mp4'  # 默认使用mp4
        
        # 构建文件名和路径
        filename = f"{user_id}_{bid}_{index}{file_ext}"
        file_path = os.path.join(media_dir, filename)
        relative_path = os.path.join('media', filename)
        
        # 检查文件是否已存在
        if os.path.exists(file_path) and not overwrite:
            logger.info(f"视频已存在，跳过下载: {file_path}")
            return relative_path
        
        # 设置请求头，模拟浏览器行为
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/86.0.4240.111 Safari/537.36",
            "Referer": "https://weibo.com/",
            "Accept": "*/*",
            "Range": "bytes=0-"  # 支持断点续传
        }
        
        # 实现重试机制
        retry_count = 0
        while retry_count < max_retries:
            try:
                # 下载视频
                with requests.get(url, headers=headers, timeout=60, stream=True) as response:
                    response.raise_for_status()
                    
                    # 获取文件大小
                    total_size = int(response.headers.get('content-length', 0))
                    
                    # 创建临时文件
                    temp_file_path = file_path + ".tmp"
                    
                    # 保存视频
                    with open(temp_file_path, 'wb') as f:
                        downloaded = 0
                        last_progress = 0
                        for chunk in response.iter_content(chunk_size=8192):
                            if chunk:
                                f.write(chunk)
                                downloaded += len(chunk)
                                # 打印下载进度
                                if total_size > 0:
                                    progress = int(downloaded / total_size * 100)
                                    # 每20%打印一次
                                    if progress >= last_progress + 20 or progress == 100:
                                        downloaded_mb = downloaded / 1024 / 1024
                                        total_mb = total_size / 1024 / 1024
                                        logger.info(f"视频下载进度: {progress}%, {downloaded_mb:.2f}MB/{total_mb:.2f}MB")
                                        last_progress = progress - (progress % 20)
                    
                    # 检查下载是否完整
                    if os.path.getsize(temp_file_path) == total_size or total_size == 0:
                        # 下载完成，重命名临时文件
                        if os.path.exists(file_path):
                            os.remove(file_path)
                        os.rename(temp_file_path, file_path)
                        logger.info(f"视频已{'覆盖' if overwrite and os.path.exists(file_path) else ''}下载到: {file_path}")
                        return relative_path
                    else:
                        # 下载不完整，删除临时文件，重试
                        os.remove(temp_file_path)
                        logger.warning(f"视频下载不完整，将重试 ({retry_count+1}/{max_retries})")
                        retry_count += 1
                        # 短暂延迟后重试
                        import time
                        time.sleep(2)
                        continue
                
                # 如果执行到这里，说明下载成功
                break
                
            except requests.exceptions.SSLError as ssl_err:
                logger.warning(f"SSL错误，将重试 ({retry_count+1}/{max_retries}): {ssl_err}")
                retry_count += 1
                if retry_count >= max_retries:
                    raise
                # 短暂延迟后重试
                import time
                time.sleep(2)
            
            except requests.exceptions.RequestException as req_err:
                logger.warning(f"请求错误，将重试 ({retry_count+1}/{max_retries}): {req_err}")
                retry_count += 1
                if retry_count >= max_retries:
                    raise
                # 短暂延迟后重试
                import time
                time.sleep(2)
        
        # 如果重试次数用完仍然失败
        if retry_count >= max_retries:
            logger.error(f"视频下载失败，已达到最大重试次数: {max_retries}")
            return None
            
        return relative_path
    except Exception as e:
        logger.error(f"下载视频失败: {e}, URL: {url}")
        # 清理可能存在的临时文件
        temp_file_path = file_path + ".tmp"
        if os.path.exists(temp_file_path):
            try:
                os.remove(temp_file_path)
            except:
                pass
        return None

# 获取视频并选择最高清晰度版本
def get_best_video_urls(weibo_data):
    """
    从微博数据中提取所有视频链接，并为每个不同视频选择最高清晰度版本
    
    Args:
        weibo_data: 微博数据字典
    
    Returns:
        list: 包含视频信息的字典列表，每个字典包含url和index(原始序号)
    """
    # 直接从pics数组中提取视频链接
    video_infos = []
    
    # 检查pics数组中的videoSrc字段
    if 'pics' in weibo_data and weibo_data['pics']:
        # 按照视频文件名分组
        video_groups = {}
        
        for i, pic in enumerate(weibo_data['pics']):
            if pic.get('type') == 'video' and 'videoSrc' in pic:
                url = pic['videoSrc']
                # 提取视频文件名作为唯一标识
                video_filename = url.split('/')[-1].split('?')[0]
                
                # 提取分辨率
                resolution = 0
                if 'template=' in url:
                    try:
                        res_part = url.split('template=')[1].split('&')[0]
                        if 'x' in res_part:
                            width = int(res_part.split('x')[0])
                            resolution = width
                    except:
                        pass
                
                # 如果这个文件名还没有记录，或者当前分辨率更高，则更新
                if video_filename not in video_groups or resolution > video_groups[video_filename]['resolution']:
                    video_groups[video_filename] = {
                        'url': url,
                        'resolution': resolution,
                        'index': i + 1  # 保存原始序号，从1开始
                    }
        
        # 收集每个不同视频的最高清晰度版本
        for video_info in video_groups.values():
            video_infos.append({
                'url': video_info['url'],
                'index': video_info['index']
            })
    
    # 检查page_info中的媒体数据
    if 'page_info' in weibo_data and weibo_data['page_info']:
        page_info = weibo_data['page_info']
        
        # 检查是否为视频类型
        if page_info.get('type') == 'video':
            # 尝试获取高清视频链接
            media_info = page_info.get('media_info', {})
            
            # 按优先级尝试不同的视频源
            for video_key in ['mp4_hd_url', 'mp4_720p_mp4', 'mp4_1080p_mp4', 'h265_mp4_hd', 'h265_mp4_ld']:
                if video_key in media_info and media_info[video_key]:
                    # 对于page_info中的视频，我们使用0作为特殊索引
                    # 因为它通常是主视频而不是图片列表中的视频
                    video_infos.append({
                        'url': media_info[video_key],
                        'index': 0
                    })
                    break
    
    return video_infos

# 解析微博数据
def parse_weibo_data(weibo_data, user_id, overwrite_pics=False, overwrite_videos=False):
    if not weibo_data:
        return None
        
    # 添加调试日志，将微博数据结构保存到文件中
    try:
        debug_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'debug')
        if not os.path.isdir(debug_dir):
            os.makedirs(debug_dir)
        debug_file = os.path.join(debug_dir, f"{weibo_data.get('bid', 'unknown')}_data.json")
        with open(debug_file, 'w', encoding='utf-8') as f:
            json.dump(weibo_data, f, ensure_ascii=False, indent=2)
        logger.info(f"已保存微博数据结构到: {debug_file}")
    except Exception as e:
        logger.warning(f"保存调试数据失败: {e}")
    
    # 继续原有代码
    weibo = {}
    weibo['user_id'] = user_id
    weibo['id'] = weibo_data.get('id', '')
    weibo['bid'] = weibo_data.get('bid', '')

    user = weibo_data.get('user', {})
    weibo['screen_name'] = user.get('screen_name', '')

    # 处理微博文本
    text = weibo_data.get('text', '')

    # 提取链接并转换为Markdown格式
    link_pattern = r'<a[^>]*href="([^"]*)"[^>]*>(.*?)</a>'

    def replace_link(match):
        url = match.group(1)
        link_text = match.group(2)

        # 过滤掉表情链接和话题链接
        if url.startswith('/') or 'emotion' in url or '#' in link_text:
            return link_text

        # 处理微博外链警告链接
        if 'sinaurl?u=' in url:
            # 提取真实URL
            real_url = url.split('sinaurl?u=', 1)[1]
            # 解码百分比编码
            try:
                from urllib.parse import unquote
                real_url = unquote(real_url)
            except Exception as e:
                logger.warning(f"解码URL失败: {e}")
            url = real_url

        return f"[{link_text}]({url})"

    # 替换链接为Markdown格式
    text = re.sub(link_pattern, replace_link, text)

    # 清理其他HTML标签
    weibo['text'] = re.sub('<[^<]+?>', '', text).replace('\n', '').strip()

    # 检查是否为转发微博
    is_retweet = 'retweeted_status' in weibo_data and weibo_data['retweeted_status']
    
    # 如果是转发微博，先获取原微博信息
    original_user_id = None
    original_bid = None
    
    if is_retweet:
        retweet = weibo_data['retweeted_status']
        retweet_user = retweet.get('user', {})
        if retweet_user is not None:
            original_user_id = retweet_user.get('id', '')
        else:
            original_user_id = ''
        original_bid = retweet.get('bid', '')
    
    # 获取图片
    pics = []
    local_pics = []
    
    # 如果是转发微博，只处理原微博的图片
    if is_retweet and 'pics' in weibo_data['retweeted_status'] and weibo_data['retweeted_status']['pics']:
        retweet = weibo_data['retweeted_status']
        for i, pic in enumerate(retweet['pics']):
            if 'large' in pic and 'url' in pic['large']:
                pic_url = pic['large']['url']
                pics.append(pic_url)
                
                # 下载图片并获取本地路径 - 使用原微博的user_id和bid
                local_path = download_image(pic_url, original_user_id, original_bid, i+1, overwrite=overwrite_pics)
                if local_path:
                    local_pics.append(local_path)
    # 否则处理当前微博的图片
    elif 'pics' in weibo_data and weibo_data['pics']:
        for i, pic in enumerate(weibo_data['pics']):
            if 'large' in pic and 'url' in pic['large']:
                pic_url = pic['large']['url']
                pics.append(pic_url)
                
                # 下载图片并获取本地路径
                local_path = download_image(pic_url, user_id, weibo_data.get('bid', ''), i+1, overwrite=overwrite_pics)
                if local_path:
                    local_pics.append(local_path)
    
    # 保存原始图片URL（用于调试）
    weibo['original_pics'] = ','.join(pics)
    # 保存本地图片路径
    weibo['pics'] = ','.join(local_pics)

    # 获取视频
    video_infos = []
    local_videos = []
    
    # 如果是转发微博，只处理原微博的视频
    if is_retweet:
        video_infos = get_best_video_urls(weibo_data['retweeted_status'])
        for video_info in video_infos:
            # 使用原始序号下载视频
            local_path = download_video(video_info['url'], original_user_id, original_bid, video_info['index'], overwrite=overwrite_videos)
            if local_path:
                local_videos.append(local_path)
    else:
        video_infos = get_best_video_urls(weibo_data)
        for video_info in video_infos:
            # 使用原始序号下载视频
            local_path = download_video(video_info['url'], user_id, weibo_data.get('bid', ''), video_info['index'], overwrite=overwrite_videos)
            if local_path:
                local_videos.append(local_path)
    
    # 保存原始视频URL（用于调试）
    weibo['original_videos'] = ','.join([info['url'] for info in video_infos])
    # 保存本地视频路径
    weibo['videos'] = ','.join(local_videos)

    # 获取文章链接
    weibo['article_url'] = ''
    if 'page_info' in weibo_data and weibo_data['page_info'] and weibo_data['page_info'].get('type') == 'article':
        if 'page_url' in weibo_data['page_info']:
            weibo['article_url'] = weibo_data['page_info']['page_url']

    # 获取话题
    topics = re.findall(r'#(.*?)#', text)
    weibo['topics'] = ','.join(topics)

    # 转发微博信息
    weibo['retweet_id'] = ''
    weibo['retweet_text'] = ''
    weibo['retweet_screen_name'] = ''
    weibo['retweet_user_id'] = ''
    weibo['retweet_pics'] = ''
    weibo['retweet_videos'] = ''  # 修改字段名
    weibo['retweet_source_url'] = ''

    # 添加源URL - 先在这里定义，确保后面交换时它已存在
    weibo['source_url'] = f"https://weibo.com/{user_id}/{weibo['bid']}"

    if is_retweet:
        retweet = weibo_data['retweeted_status']
        weibo['retweet_id'] = retweet.get('id', '')

        # 获取原微博文本
        retweet_text = retweet.get('text', '')

        # 替换原微博中的链接为Markdown格式
        retweet_text = re.sub(link_pattern, replace_link, retweet_text)

        # 清理其他HTML标签
        retweet_text_clean = re.sub('<[^<]+?>', '', retweet_text).replace('\n', '').strip()

        # 将当前微博文本存入retweet_text
        original_text = weibo['text']

        # 将原微博文本存入text
        weibo['text'] = retweet_text_clean

        # 获取原微博用户信息
        retweet_user = retweet.get('user', {})
        if retweet_user is not None:
            weibo['retweet_screen_name'] = retweet_user.get('screen_name', '')
            weibo['retweet_user_id'] = retweet_user.get('id', '')
        else:
            logger.warning("原微博用户信息不可见")
            weibo['retweet_screen_name'] = '已删除'
            weibo['retweet_user_id'] = ''

        # 获取原微博图片 - 这里不再重复下载图片，直接使用之前下载的图片
        # 保存本地图片路径
        weibo['retweet_pics'] = ','.join(local_pics)

        # 添加原微博源URL
        if weibo['retweet_user_id'] and retweet.get('bid', ''):
            weibo['retweet_source_url'] = f"https://weibo.com/{weibo['retweet_user_id']}/{retweet.get('bid', '')}"

        # 根据需求调整字段内容
        # 交换 user_id 和 retweet_user_id
        weibo['user_id'], weibo['retweet_user_id'] = weibo['retweet_user_id'], weibo['user_id']

        # 交换 screen_name 和 retweet_screen_name
        weibo['screen_name'], weibo['retweet_screen_name'] = weibo['retweet_screen_name'], weibo['screen_name']

        # 在retweet_text前添加当前retweet_screen_name
        if original_text:
            weibo['retweet_text'] = f"@{weibo['retweet_screen_name']}:{original_text}"
        else:
            weibo['retweet_text'] = ""

        # 交换 source_url 和 retweet_source_url
        weibo['source_url'], weibo['retweet_source_url'] = weibo['retweet_source_url'], weibo['source_url']

        # 更新bid为原微博的bid
        weibo['bid'] = retweet.get('bid', weibo['bid'])

        # 使用 retweet_pics 的值替换 pics
        weibo['pics'] = weibo['retweet_pics']

        # 保存本地视频路径 - 直接使用之前下载的视频路径
        weibo['retweet_videos'] = ','.join(local_videos)

        # 使用 retweet_videos 的值替换 videos
        weibo['videos'] = weibo['retweet_videos']

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

def main(ignore_status=False, overwrite_pics=False, overwrite_videos=False):
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
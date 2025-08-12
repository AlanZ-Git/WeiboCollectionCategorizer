import os
import re
import json

from .media_downloader import download_image, download_video
from .path_manager import get_download_path, create_download_directories
from .logger import setup_logger
logger = setup_logger()

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
            # 处理LivePhoto类型视频
            if pic.get('type') == 'livephoto' and 'videoSrc' in pic:
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
                        'index': i + 1,  # 保存原始序号，从1开始
                        'is_livephoto': True
                    }
            # 处理普通视频类型
            elif pic.get('type') == 'video' and 'videoSrc' in pic:
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
                        'index': i + 1,  # 保存原始序号，从1开始
                        'is_livephoto': False
                    }

        # 收集每个不同视频的最高清晰度版本
        for video_info in video_groups.values():
            video_infos.append({
                'url': video_info['url'],
                'index': video_info['index'],
                'is_livephoto': video_info.get('is_livephoto', False)
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
                        'index': 0,
                        'is_livephoto': False
                    })
                    break

    # 获取LivePhoto链接
    live_photo_list = get_live_photo(weibo_data)

    # 查找pics数组中对应的LivePhoto索引
    if 'pics' in weibo_data and weibo_data['pics'] and live_photo_list:
        # 创建一个映射，将LivePhoto URL映射到其在pics中的索引
        livephoto_url_to_index = {}

        # 首先遍历pics数组，建立映射关系
        for i, pic in enumerate(weibo_data['pics']):
            if pic.get('type') == 'livephoto' and 'videoSrc' in pic:
                livephoto_url_to_index[pic['videoSrc']] = i + 1

        # 处理从get_live_photo获取的LivePhoto列表
        for live_photo_url in live_photo_list:
            # 检查这个URL是否已经在video_infos中
            already_added = any(info['url'] == live_photo_url for info in video_infos)

            if not already_added:
                # 尝试找到对应的图片索引
                found_index = -1
                for i, pic in enumerate(weibo_data['pics']):
                    if pic.get('type') == 'livephoto' and pic.get('videoSrc') == live_photo_url:
                        found_index = i + 1
                        break

                # 如果找到了对应的图片索引，使用该索引
                if found_index != -1:
                    video_infos.append({
                        'url': live_photo_url,
                        'index': found_index,
                        'is_livephoto': True
                    })
                else:
                    # 如果没找到对应索引，使用连续的索引
                    next_index = len(weibo_data['pics']) + len(video_infos) + 1
                    video_infos.append({
                        'url': live_photo_url,
                        'index': next_index,
                        'is_livephoto': True
                    })
                    logger.warning(f"LivePhoto未找到对应图片，使用新索引: {next_index}")

    return video_infos

def get_live_photo(weibo_data):
    """获取live photo中的视频url列表

    Args:
        weibo_data: 微博数据字典

    Returns:
        list: LivePhoto视频URL列表
    """
    live_photo_urls = []

    # 检查pics数组中的videoSrc字段（这是最直接的方式）
    if 'pics' in weibo_data and weibo_data['pics']:
        for i, pic in enumerate(weibo_data['pics']):
            if pic.get('type') == 'livephoto' and 'videoSrc' in pic:
                live_photo_url = pic['videoSrc']
                if live_photo_url and live_photo_url not in live_photo_urls:
                    live_photo_urls.append(live_photo_url)
                    logger.debug(f"从pics[{i}].videoSrc找到LivePhoto URL: {live_photo_url}")

    # 如果上面的方法没有找到LivePhoto，尝试其他字段
    if not live_photo_urls:
        # 检查pics数组中的其他可能字段
        if 'pics' in weibo_data and weibo_data['pics']:
            for i, pic in enumerate(weibo_data['pics']):
                # 直接检查live_photo_url字段
                if pic.get('live_photo_url'):
                    live_photo_url = pic.get('live_photo_url')
                    if live_photo_url and live_photo_url not in live_photo_urls:
                        live_photo_urls.append(live_photo_url)
                        logger.info(f"从pics[{i}].live_photo_url找到LivePhoto URL: {live_photo_url}")
                # 检查pic.values字段
                elif pic.get('values') and pic['values'].get('live_photo_url'):
                    live_photo_url = pic['values'].get('live_photo_url')
                    if live_photo_url and live_photo_url not in live_photo_urls:
                        live_photo_urls.append(live_photo_url)
                        logger.info(f"从pics[{i}].values.live_photo_url找到LivePhoto URL: {live_photo_url}")
                # 检查pic.live_photo字段
                elif pic.get('live_photo'):
                    live_photo_url = pic.get('live_photo')
                    if live_photo_url and live_photo_url not in live_photo_urls:
                        live_photo_urls.append(live_photo_url)
                        logger.info(f"从pics[{i}].live_photo找到LivePhoto URL: {live_photo_url}")

    # 检查微博数据中的live_photo字段
    if 'live_photo' in weibo_data:
        if isinstance(weibo_data['live_photo'], list):
            for url in weibo_data['live_photo']:
                if url and url not in live_photo_urls:
                    live_photo_urls.append(url)
            logger.debug(f"从微博根级别live_photo数组找到LivePhoto URLs: {weibo_data['live_photo']}")
        elif isinstance(weibo_data['live_photo'], str):
            url = weibo_data['live_photo']
            if url and url not in live_photo_urls:
                live_photo_urls.append(url)
            logger.debug(f"从微博根级别live_photo字符串找到LivePhoto URL: {url}")

    return live_photo_urls

def parse_weibo_data(weibo_data, user_id, overwrite_pics=False, overwrite_videos=False):
    """
    解析微博数据，提取文本、图片、视频等内容

    Args:
        weibo_data: 微博数据字典
        user_id: 用户ID
        overwrite_pics: 是否覆盖已下载的图片
        overwrite_videos: 是否覆盖已下载的视频

    Returns:
        dict: 解析后的微博数据字典
    """
    if not weibo_data:
        return None

    # 获取下载路径
    download_paths = create_download_directories(get_download_path())
    debug_dir = os.path.join(download_paths['base'], 'debug')

    # 添加调试日志，将微博数据结构保存到文件中
    try:
        if not os.path.isdir(debug_dir):
            os.makedirs(debug_dir)
        debug_file = os.path.join(debug_dir, f"{weibo_data.get('bid', 'unknown')}_data.json")
        with open(debug_file, 'w', encoding='utf-8') as f:
            json.dump(weibo_data, f, ensure_ascii=False, indent=2)
        logger.debug(f"已保存微博数据结构到: {debug_file}")
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
            local_path = download_video(
                video_info['url'],
                original_user_id,
                original_bid,
                video_info['index'],
                overwrite=overwrite_videos
            )
            if local_path:
                local_videos.append(local_path)
    else:
        video_infos = get_best_video_urls(weibo_data)
        for video_info in video_infos:
            # 使用原始序号下载视频
            local_path = download_video(
                video_info['url'],
                user_id,
                weibo_data.get('bid', ''),
                video_info['index'],
                overwrite=overwrite_videos
            )
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
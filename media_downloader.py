import os
import requests
from logger import setup_logger
from path_manager import get_download_path, create_download_directories

# 初始化日志
logger = setup_logger()

def download_image(url, user_id, bid, index, overwrite=False):
    """下载图片并保存到本地"""
    try:
        # 获取下载路径
        download_paths = create_download_directories(get_download_path())
        media_dir = download_paths['media']
        
        file_ext = os.path.splitext(url.split('/')[-1])[1]
        if not file_ext or len(file_ext) > 5:
            file_ext = '.jpg'
        
        filename = f"{user_id}_{bid}_{index}{file_ext}"
        file_path = os.path.join(media_dir, filename)
        relative_path = os.path.join('media', filename)
        
        if os.path.exists(file_path) and not overwrite:
            logger.info(f"图片已存在，跳过下载: {file_path}")
            return relative_path
        
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/86.0.4240.111 Safari/537.36",
            "Referer": "https://weibo.com/",
            "Accept": "image/avif,image/webp,image/apng,image/*,*/*;q=0.8"
        }
        
        response = requests.get(url, headers=headers, timeout=30, stream=True)
        response.raise_for_status()
        
        with open(file_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                if chunk:
                    f.write(chunk)
        
        logger.info(f"图片{'覆盖' if overwrite and os.path.exists(file_path) else ''}下载: {file_path}")
        return relative_path
    except Exception as e:
        logger.error(f"下载图片失败: {e}, URL: {url}")
        return None

def download_video(url, user_id, bid, index, overwrite=False, max_retries=3):
    """下载视频并保存到本地"""
    try:
        # 获取下载路径
        download_paths = create_download_directories(get_download_path())
        media_dir = download_paths['media']
        
        file_ext = os.path.splitext(url.split('/')[-1].split('?')[0])[1]
        if not file_ext or len(file_ext) > 5:
            file_ext = '.mp4'
        
        filename = f"{user_id}_{bid}_{index}{file_ext}"
        file_path = os.path.join(media_dir, filename)
        relative_path = os.path.join('media', filename)
        
        if os.path.exists(file_path) and not overwrite:
            logger.info(f"视频已存在，跳过下载: {file_path}")
            return relative_path
        
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/86.0.4240.111 Safari/537.36",
            "Referer": "https://weibo.com/",
            "Accept": "*/*",
            "Range": "bytes=0-"
        }
        
        retry_count = 0
        while retry_count < max_retries:
            try:
                with requests.get(url, headers=headers, timeout=60, stream=True) as response:
                    response.raise_for_status()
                    
                    total_size = int(response.headers.get('content-length', 0))
                    temp_file_path = file_path + ".tmp"
                    
                    with open(temp_file_path, 'wb') as f:
                        downloaded = 0
                        last_progress = 0
                        for chunk in response.iter_content(chunk_size=8192):
                            if chunk:
                                f.write(chunk)
                                downloaded += len(chunk)
                                if total_size > 0:
                                    progress = int(downloaded / total_size * 100)
                                    if progress >= last_progress + 20 or progress == 100:
                                        downloaded_mb = downloaded / 1024 / 1024
                                        total_mb = total_size / 1024 / 1024
                                        logger.debug(f"视频下载进度: {progress}%, {downloaded_mb:.2f}MB/{total_mb:.2f}MB")
                                        last_progress = progress - (progress % 20)
                    
                    if os.path.getsize(temp_file_path) == total_size or total_size == 0:
                        if os.path.exists(file_path):
                            os.remove(file_path)
                        os.rename(temp_file_path, file_path)
                        logger.info(f"视频{'覆盖' if overwrite and os.path.exists(file_path) else ''}下载: {file_path}")
                        return relative_path
                    else:
                        os.remove(temp_file_path)
                        logger.warning(f"视频下载不完整，将重试 ({retry_count+1}/{max_retries})")
                        retry_count += 1
                        import time
                        time.sleep(2)
                        continue
                
                break
                
            except requests.exceptions.SSLError as ssl_err:
                logger.warning(f"SSL错误，将重试 ({retry_count+1}/{max_retries}): {ssl_err}")
                retry_count += 1
                if retry_count >= max_retries:
                    raise
                import time
                time.sleep(2)
            
            except requests.exceptions.RequestException as req_err:
                logger.warning(f"请求错误，将重试 ({retry_count+1}/{max_retries}): {req_err}")
                retry_count += 1
                if retry_count >= max_retries:
                    raise
                import time
                time.sleep(2)
        
        if retry_count >= max_retries:
            logger.error(f"视频下载失败，已达到最大重试次数: {max_retries}")
            return None
            
        return relative_path
    except Exception as e:
        logger.error(f"下载视频失败: {e}, URL: {url}")
        temp_file_path = file_path + ".tmp"
        if os.path.exists(temp_file_path):
            try:
                os.remove(temp_file_path)
            except:
                pass
        return None 
import os
import json

def get_download_path():
    """获取下载路径，如果不存在则提示用户输入"""
    saved_path = None
    try:
        with open('setting.json', 'r', encoding='utf-8') as f:
            settings = json.load(f)
            saved_path = settings.get('download_path')
            
            if saved_path:
                # 确保路径存在
                create_download_directories(saved_path)
                return saved_path
    except (FileNotFoundError, json.JSONDecodeError):
        pass
    
    # 如果没有找到设置或设置中没有下载路径，提示用户输入
    print("请输入下载路径（留空则使用已保存的路径或当前目录）：")
    download_path = input().strip()
    
    # 如果用户没有输入，优先使用已保存的路径，如果没有已保存的路径才使用当前目录
    if not download_path:
        download_path = saved_path if saved_path else os.path.abspath(os.path.curdir)
    
    # 确保路径存在
    create_download_directories(download_path)
    
    # 保存设置
    save_download_path(download_path)
    
    return download_path

def create_download_directories(base_path):
    """创建必要的下载目录"""
    # 创建基础目录
    os.makedirs(base_path, exist_ok=True)
    
    # 创建子目录
    weibo_dir = os.path.join(base_path, 'weibo')
    media_dir = os.path.join(base_path, 'media')
    
    os.makedirs(weibo_dir, exist_ok=True)
    os.makedirs(media_dir, exist_ok=True)
    
    return {
        'base': base_path,
        'weibo': weibo_dir,
        'media': media_dir
    }

def save_download_path(download_path):
    """保存下载路径到设置文件"""
    try:
        # 读取现有设置
        try:
            with open('setting.json', 'r', encoding='utf-8') as f:
                settings = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            settings = {}
        
        # 更新下载路径
        settings['download_path'] = download_path
        
        # 保存设置
        with open('setting.json', 'w', encoding='utf-8') as f:
            json.dump(settings, f, ensure_ascii=False, indent=4)
            
        return True
    except Exception as e:
        print(f"保存设置时出错：{str(e)}")
        return False 
# task_manager.py - 任务管理模块

import os
import csv
from datetime import datetime
from logger import setup_logger

# 初始化日志
logger = setup_logger()

def init_tasks_file():
    """初始化任务文件，如果不存在则创建"""
    file_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'download_tasks.csv')
    
    if not os.path.exists(file_path):
        with open(file_path, 'w', encoding='utf-8-sig', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(['url', 'status', 'notes', 'created_at', 'completed_at'])
        logger.info(f"已创建任务文件: {file_path}")
    
    return file_path

def add_task(url, notes=''):
    """
    添加新的下载任务
    
    Args:
        url: 任务URL
        notes: 任务备注
    
    Returns:
        bool: 添加是否成功
    """
    try:
        file_path = init_tasks_file()
        
        if not url:
            logger.error("URL不能为空，任务添加取消")
            return False
            
        with open(file_path, 'a', encoding='utf-8-sig', newline='') as f:
            writer = csv.writer(f)
            created_at = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            writer.writerow([url, 'pending', notes, created_at, ''])
        
        logger.info(f"已添加任务: {url}")
        return True
    except Exception as e:
        logger.error(f"添加任务失败: {str(e)}")
        return False

def add_task_interactive():
    """通过命令行交互添加新的下载任务"""
    try:
        input_str = input("请输入下载任务 (格式: URL;备注): ").strip()
        if not input_str:
            print("输入不能为空，任务添加取消")
            return False
        
        parts = input_str.split(';', 1)
        url = parts[0].strip()
        notes = parts[1].strip() if len(parts) > 1 else ''
        
        return add_task(url, notes)
    except Exception as e:
        logger.error(f"交互式添加任务失败: {str(e)}")
        return False

def update_task_status(url, status='completed'):
    """
    更新任务状态

    Args:
        url: 任务URL
        status: 新状态 ('pending', 'processing', 'completed', 'failed')
    
    Returns:
        bool: 更新是否成功
    """
    try:
        file_path = init_tasks_file()
        temp_file = file_path + '.temp'
        
        found = False
        with open(file_path, 'r', encoding='utf-8-sig', newline='') as f_in, \
             open(temp_file, 'w', encoding='utf-8-sig', newline='') as f_out:
            reader = csv.reader(f_in)
            writer = csv.writer(f_out)
            
            header = next(reader)
            writer.writerow(header)
            
            for row in reader:
                if row[0] == url:
                    found = True
                    row[1] = status
                    if status == 'completed':
                        row[4] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                writer.writerow(row)
        
        if found:
            os.replace(temp_file, file_path)
            logger.info(f"已更新任务状态: {url} -> {status}")
        else:
            os.remove(temp_file)
            logger.warning(f"未找到任务: {url}")
        
        return found
    except Exception as e:
        logger.error(f"更新任务状态失败: {str(e)}")
        return False

def get_pending_tasks(ignore_status=False):
    """
    获取待处理的任务

    Args:
        ignore_status: 是否忽略状态，如果为True则返回所有任务

    Returns:
        任务列表
    """
    try:
        file_path = init_tasks_file()
        
        tasks = []
        with open(file_path, 'r', encoding='utf-8-sig', newline='') as f:
            reader = csv.DictReader(f)
            for row in reader:
                # 如果ignore_status为True，则返回所有任务
                # 否则只返回状态为pending的任务
                if ignore_status or row.get('status', '').lower() == 'pending':
                    tasks.append(row)
        
        return tasks
    except Exception as e:
        logger.error(f"获取待处理任务失败: {str(e)}")
        return []

def get_all_tasks():
    """
    获取所有任务
    
    Returns:
        所有任务的列表
    """
    try:
        file_path = init_tasks_file()
        
        all_tasks = []
        with open(file_path, 'r', encoding='utf-8-sig', newline='') as f:
            reader = csv.DictReader(f)
            for row in reader:
                all_tasks.append(row)
        
        return all_tasks
    except Exception as e:
        logger.error(f"获取所有任务失败: {str(e)}")
        return []

if __name__ == "__main__":
    # 示例用法
    add_task_interactive()
    # tasks = get_pending_tasks()
    # print(f"待处理任务数: {len(tasks)}")
    # for task in tasks:
    #     print(f"URL: {task['url']}, 备注: {task['notes']}") 
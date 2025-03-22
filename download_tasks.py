import os
import csv
from datetime import datetime

def init_tasks_file():
    """初始化任务文件，如果不存在则创建"""
    file_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'download_tasks.csv')
    
    if not os.path.exists(file_path):
        with open(file_path, 'w', encoding='utf-8-sig', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(['url', 'status', 'notes', 'created_at', 'completed_at'])
        print(f"已创建任务文件: {file_path}")
    
    return file_path

def add_task(url, notes=''):
    """添加新的下载任务"""
    file_path = init_tasks_file()
    
    with open(file_path, 'a', encoding='utf-8-sig', newline='') as f:
        writer = csv.writer(f)
        created_at = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        writer.writerow([url, 'pending', notes, created_at, ''])
    
    print(f"已添加任务: {url}")
    return True

def update_task_status(url, status='completed'):
    """更新任务状态"""
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
        print(f"已更新任务状态: {url} -> {status}")
    else:
        os.remove(temp_file)
        print(f"未找到任务: {url}")
    
    return found

def get_pending_tasks():
    """获取所有待处理的任务"""
    file_path = init_tasks_file()
    
    pending_tasks = []
    with open(file_path, 'r', encoding='utf-8-sig', newline='') as f:
        reader = csv.reader(f)
        next(reader)  # 跳过表头
        
        for row in reader:
            if row[1] == 'pending':
                pending_tasks.append({
                    'url': row[0],
                    'notes': row[2],
                    'created_at': row[3]
                })
    
    return pending_tasks

def get_all_tasks():
    """获取所有任务"""
    file_path = init_tasks_file()
    
    all_tasks = []
    with open(file_path, 'r', encoding='utf-8-sig', newline='') as f:
        reader = csv.DictReader(f)
        for row in reader:
            all_tasks.append(row)
    
    return all_tasks

if __name__ == "__main__":
    # 示例用法
    add_task("https://weibo.com/3047892900/PjfGgqXUr", "转发微博，原微博正文有网页链接，带2张图片")
    tasks = get_pending_tasks()
    print(f"待处理任务数: {len(tasks)}")
    for task in tasks:
        print(f"URL: {task['url']}, 备注: {task['notes']}") 
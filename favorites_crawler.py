import csv
import json
import time
import requests

from datetime import datetime
import os
from pathlib import Path

class FavoritesCrawler:
    def __init__(self, cookie_path='setting.json'):
        # 加载cookie
        with open(cookie_path, 'r', encoding='utf-8') as f:
            self.cookie = json.load(f)

        # 设置请求头
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Cookie': '; '.join([f'{k}={v}' for k, v in self.cookie.items()])
        }

        # 收藏微博API
        self.favorites_url = 'https://weibo.com/ajax/favorites/all_fav'

        # 创建debug文件夹（如果不存在）
        self.debug_dir = Path('debug')
        self.debug_dir.mkdir(exist_ok=True)

    def save_debug_json(self, data, prefix='api_response'):
        """保存调试数据到JSON文件"""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = self.debug_dir / f"{prefix}_{timestamp}.json"

        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

        return filename

    def get_favorites(self, page=1, count=20):
        """获取收藏的微博列表"""
        params = {
            'page': page,
            'count': count
        }

        try:
            response = requests.get(self.favorites_url, headers=self.headers, params=params)
            if response.status_code == 200:
                data = response.json()
                # 保存API返回的数据结构到debug文件夹
                debug_file = self.save_debug_json(data)
                print(f"API返回数据已保存到: {debug_file}")
                # 检查数据结构并返回正确的数据
                if isinstance(data, dict):
                    if data.get('ok') == 1 and isinstance(data.get('data'), list):
                        return data['data']
                    elif 'data' in data and isinstance(data['data'], dict):
                        return data['data'].get('favorites', [])
                elif isinstance(data, list):
                    return data
                else:
                    print(f"未知的数据结构: {type(data)}")
                    return []
            else:
                print(f"获取收藏微博失败，状态码: {response.status_code}")
                return []
        except Exception as e:
            print(f"获取收藏微博时发生错误: {e}")
            return []

    def parse_favorites(self, favorites):
        """解析收藏微博数据，只提取URL"""
        result = []

        # 检查favorites是否为列表
        if not isinstance(favorites, list):
            print(f"收藏微博数据不是列表类型: {type(favorites)}")
            return result

        for fav in favorites:
            try:
                # 检查fav的类型
                if not isinstance(fav, dict):
                    print(f"跳过非字典类型的收藏项: {type(fav)}")
                    continue

                # 直接从fav中获取必要的字段
                user_id = fav.get('user', {}).get('id')
                mblogid = fav.get('mblogid')
                created_at = fav.get('created_at')

                if user_id and mblogid:
                    url = f"https://weibo.com/{user_id}/{mblogid}"
                    result.append({
                        'url': url,
                        'favorited_time': created_at
                    })
            except Exception as e:
                print(f"解析收藏项时出错: {e}")
                continue

        return result

    def get_all_favorites(self, max_pages=5):
        """获取所有收藏微博的URL"""
        all_favorites = []

        for page in range(1, max_pages + 1):
            print(f"正在获取第 {page} 页收藏微博...")
            favorites = self.get_favorites(page=page)

            if not favorites:
                print(f"第 {page} 页没有收藏微博数据，停止获取")
                break

            parsed_data = self.parse_favorites(favorites)
            if parsed_data:
                all_favorites.extend(parsed_data)
                print(f"成功解析第 {page} 页，获取到 {len(parsed_data)} 条收藏微博")
            else:
                print(f"第 {page} 页解析结果为空")

            # 防止请求过快
            time.sleep(2)

        print(f"总共获取到 {len(all_favorites)} 条收藏微博")
        return all_favorites

    def save_to_csv(self, data: list[str], filename=None):
        """保存收藏微博URL到CSV文件"""
        if not data:
            print("没有收藏微博数据可保存")
            return

        if filename is None:
            today = datetime.now().strftime('%Y%m%d')
            filename = f"weibo/favorites_{today}.csv"

        with open(filename, mode='w', newline='', encoding='utf-8-sig') as file:
            writer = csv.writer(file)
            # 写标题行（可选，根据数据调整）
            writer.writerow(['url', 'favorited_time'])  # 假如只存 URL，可以自行修改标题
            # 写入数据行
            for row in data:
                writer.writerow([row['url'], row['favorited_time']])

        return filename 
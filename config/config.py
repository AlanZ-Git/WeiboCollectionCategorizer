import os
import json
from typing import Optional, Dict, Any

from utils.logger import setup_logger
logger = setup_logger()


class ConfigManager:
    """微博收藏分类器配置管理类"""
    
    def __init__(self, config_filename: str = 'setting.json'):
        """
        初始化配置管理器
        
        Args:
            config_filename: 配置文件名，默认为 'setting.json'
        """
        self.base_dir = os.path.dirname(os.path.abspath(__file__))
        self.config_path = os.path.join(self.base_dir, config_filename)
        self.default_setting = {
            "download_path": "download",
            "cookie": ""
        }

    @property
    def _setting(self) -> Dict[str, Any]:
        """
        获取json文件配置, 如果文件不存在则创建

        Returns:
            Dict[str, Any]: 配置字典
        """
        default_setting = self.default_setting

        if not os.path.exists(self.config_path):
            return self._initialize_setting(default_setting)
        else:
            try:
                with open(self.config_path, 'r', encoding='utf-8') as f:
                    setting_data = json.load(f)
                    # 检查设置key是否匹配
                    if set(setting_data.keys()) != set(default_setting.keys()):
                        logger.warning("setting.json 设置key不匹配, 已使用默认配置重建。")
                        return self._initialize_setting(default_setting)

                    return setting_data
            except json.JSONDecodeError:
                # 配置损坏时回退为默认并重写
                logger.warning("检测到损坏的 setting.json，已使用默认配置重建。")
                return self._initialize_setting(default_setting)

    def _initialize_setting(self, default_setting: Dict[str, Any]) -> Dict[str, Any]:
        """
        初始化配置文件

        Args:
            default_setting: 默认配置

        Returns:
            Dict[str, Any]: 配置字典
        """
        with open(self.config_path, 'w', encoding='utf-8') as f:
            json.dump(default_setting, f, ensure_ascii=False, indent=4)
        return default_setting

    @property
    def cookie(self) -> str:
        """
        从配置中获取cookie, 如果配置不存在则交互式获取

        Returns:
            str: cookie字符串, 如果获取失败则返回空字符串
        """
        cookie = self._setting.get('cookie', '')
        if not cookie:
            return self.reload_cookie()
        else:
            return cookie

    def reload_cookie(self) -> Optional[str]:
        """
        交互式获取并保存Cookie
        
        Returns:
            Optional[str]: cookie字符串，如果获取失败则返回None
        """
        instructions = """
===== 微博Cookie获取指南 =====
1. 使用Chrome或Firefox浏览器访问 https://m.weibo.cn 并登录您的账号
2. 登录成功后，按F12打开开发者工具
3. 在开发者工具中，选择'Network'（网络）选项卡
4. 在页面上刷新或点击任意微博内容，观察网络请求
5. 在网络请求列表中，找到任意一个请求（例如api/config或getIndex）
6. 点击该请求，在右侧面板中找到'Headers'（请求头）
7. 在Headers中找到'Cookie:'开头的行
8. 复制整个Cookie值（从Cookie:后面开始，到该行结束）
9. 将复制的内容粘贴到下面的输入提示中

注意：Cookie包含您的登录凭证，请勿分享给他人！
===========================
"""
        print(instructions)

        try:
            cookie = input("请粘贴您的微博Cookie: ").strip()

            if not cookie:
                print("\n❌ 未输入任何内容，取消保存。")
                return None

            if self._save_cookie(cookie):
                print("\n✅ Cookie已成功保存！")
                return cookie
            else:
                print("\n❌ Cookie保存失败，请检查日志获取详细信息。")
                return None

        except KeyboardInterrupt:
            print("\n已取消操作")
            return None
        except Exception as e:
            logger.error(f"发生错误: {e}")
            print(f"\n❌ 发生错误: {e}")
            return None

    def _save_cookie(self, cookie: str) -> bool:
        """
        保存Cookie到setting.json文件, 保留其他设置
        
        Args:
            cookie: 要保存的cookie字符串
            
        Returns:
            bool: 保存是否成功
        """
        # 读取现有配置
        setting = self._setting

        # 更新cookie值
        if not isinstance(cookie, str) or not cookie.strip():
            logger.error("无效的 Cookie, 保存已中止")
            return False

        setting["cookie"] = cookie.strip()

        # 保存更新后的配置
        try:
            with open(self.config_path, 'w', encoding='utf-8') as f:
                json.dump(setting, f, ensure_ascii=False, indent=4)
            logger.info(f"Cookie已成功保存到文件: {self.config_path}")
            return True
        except Exception as e:
            logger.error(f"保存Cookie文件失败: {e}")
            return False

    @property
    def download_path(self) -> str:
        """
        获取下载路径，并确保路径文件夹已创建

        Returns:
            str: 下载路径
        """
        path = self._setting['download_path']
        weibo_path = os.path.join(path, 'weibo')
        media_path = os.path.join(weibo_path, 'media')

        os.makedirs(path, exist_ok=True)
        os.makedirs(weibo_path, exist_ok=True)
        os.makedirs(media_path, exist_ok=True)

        return path
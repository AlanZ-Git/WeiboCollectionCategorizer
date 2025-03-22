import os
import sys
import logging
import logging.config

# 设置日志
def setup_logger():
    if not os.path.isdir("log/"):
        os.makedirs("log/")
    logging_path = os.path.split(os.path.realpath(__file__))[0] + os.sep + "logging.conf"
    if os.path.exists(logging_path):
        logging.config.fileConfig(logging_path)
    else:
        # 修改默认日志级别为INFO，这样DEBUG级别的日志就不会显示
        logging.basicConfig(
            level=logging.INFO, 
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                # 添加文件处理器，将所有日志（包括DEBUG）写入文件
                logging.FileHandler(os.path.join("log", "weibo.log"), encoding='utf-8'),
                # 添加控制台处理器，只显示INFO及以上级别的日志
                logging.StreamHandler(sys.stdout)
            ]
        )
    logger = logging.getLogger("weibo")

    # 可以单独设置文件处理器的日志级别为DEBUG，这样DEBUG日志仍会写入文件但不会显示在终端
    for handler in logger.handlers:
        if isinstance(handler, logging.FileHandler):
            handler.setLevel(logging.DEBUG)
        elif isinstance(handler, logging.StreamHandler):
            handler.setLevel(logging.INFO)  # 控制台只显示INFO及以上级别

    return logger 
import os, sys
from pathlib import Path
import time
import random

from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.remote.webelement import WebElement

if getattr(sys, 'frozen', False):
    PARENT_DIR: Path = Path(sys.executable).parent.resolve()
else:
    PARENT_DIR: Path = Path(__file__).parent.resolve()

CHROME_DATA_DIR: Path = PARENT_DIR / 'chrome_data'
CHROME_DATA_DIR.mkdir(parents=True, exist_ok=True)

CHROME_DEFAULT_PATH = PARENT_DIR / 'chromedriver.exe'

class CrazyDriver(webdriver.Chrome):

    def __init__(self, executable_path: str = str(CHROME_DEFAULT_PATH), headless: bool = False) -> None:
        """
        Args:
            executable_path: ChromeDriver 的路径
            headless: 是否打开浏览器
        """
        service = Service(executable_path=executable_path, log_output=os.devnull)

        options = Options()
        # 禁用日志输出, 不显示
        options.add_experimental_option('excludeSwitches', ['enable-logging', 'enable-automation'])
        # 继承浏览器 Cookie
        options.add_argument(rf'--user-data-dir={CHROME_DATA_DIR}')
        if headless:
            options.add_argument('--headless')

        super().__init__(options=options, service=service)

        from ._stealth_min_js import code
        # 隐藏浏览器指纹
        self.execute_cdp_cmd('Page.addScriptToEvaluateOnNewDocument', {
            'source': code
        })

    def explicit_wait(self, by: str, value: str, seconds: int = 9999) -> WebElement:
        """
        显式等待，返回被等待的元素

        Args:
            by: 定位方式, 如 By.XPATH
            value: 定位值, 如  '//div[@id='example']'
            seconds: 等待秒数
        """
        WebDriverWait(self, seconds).until(
            EC.presence_of_element_located(
                (by, value))
        )
        element = self.find_element(by, value)
        return element
    
    def explicit_waits(self, by: str, value: str, seconds: int = 9999) -> list[WebElement]:
        """
        显式等待，返回被等待的元素列表

        Args:
            by: 定位方式, 如 By.XPATH
            value: 定位值, 如  '//div[@id='example']'
            seconds: 等待秒数
        """
        WebDriverWait(self, seconds).until(
            EC.presence_of_all_elements_located(
                (by, value))
        )
        elements = self.find_elements(by, value)
        return elements

    def update_window_handle(self) -> None:
        """更新窗口句柄为最新窗口"""
        self.switch_to.window(self.window_handles[-1])

    def save_page_source(self, path: str = str(PARENT_DIR / 'index.html'), show: bool = False) -> None:
        """
        保存当前页面的源代码到指定路径

        Args:
            path: 保存的文件路径, 默认为 'index.html'
            show: 是否在保存后打开文件
        """
        with open(path, 'w', encoding='utf-8') as f:
            f.write(self.page_source)
        if show:
            os.startfile(path)

    def scroll_to_bottom(self, scroll_delay_factor: float = 0.5) -> None: 
        """滚动到窗口底部
        Args:
            scroll_delay_factor: 滚动延迟因子, 控制滚动速度, 值越大滚动越慢, 建议取值范围 [0.1, 1.0]
        """
        # 执行这段代码，会获取到当前窗口总高度
        get_height = 'return document.body.scrollHeight'
        # 初始化现在滚动条所在高度为0
        height = 0
        # 当前窗口总高度
        new_height = self.execute_script(get_height)
        while height < new_height:
            # 将滚动条调整至页面底部
            for i in range(height, new_height, random.randint(800, 1000)):
                self.execute_script(f'window.scrollTo(0, {i})')
                time.sleep(random.random() * scroll_delay_factor)
            height = new_height
            new_height = self.execute_script(get_height)


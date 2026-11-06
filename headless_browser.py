import time
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager

class HeadlessBrowser:
    driver = None

    @classmethod
    def init_browser(cls):
        chrome_options = Options()
        
        # 1. Enable Headless Mode
        # '--headless=new' is the updated headless mode for Chrome (v109+)
        #chrome_options.add_argument("--headless=new")
        
        # 2. Window and Rendering Fixes
        chrome_options.add_argument("--window-size=1920,1080")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        
        # 3. Disabling Automation Flags (Anti-Detection)
        chrome_options.add_argument("--disable-blink-features=AutomationControlled")
        chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        chrome_options.add_experimental_option('useAutomationExtension', False)
        
        # 4. Custom Real User-Agent
        user_agent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
        chrome_options.add_argument(f"user-agent={user_agent}")

        # Initialize WebDriver
        cls.chrome_options = chrome_options
        cls.driver = webdriver.Chrome(
            service=Service(ChromeDriverManager().install()), 
            options=chrome_options
        )
        cls.driver.execute_cdp_cmd("Page.addScriptToEvaluateOnNewDocument", {
        "source": """
            Object.defineProperty(navigator, 'webdriver', {
                get: () => undefined
            });
        """
        })

    @classmethod
    def quit(cls):
        if (cls.driver is not None):
            try:
                cls.driver.quit()
            except Exception as e:
                pass
            cls.driver = None

    @classmethod
    def fetch(cls, href):
        if (cls.driver is None):
            raise RuntimeError("Driver not initialized. Please call init_browser before calling fetch.")
        cls.driver.get(href)
        return cls.driver.page_source
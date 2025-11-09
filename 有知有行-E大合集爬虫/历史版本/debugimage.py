import requests
import time

# 依然使用请求头伪装
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
                  '(KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
}

# 目标：您提供的这篇带图片的文章
TARGET_URL = "https://youzhiyouxing.cn/materials/693"

# 输出文件名
OUTPUT_FILENAME = "article_with_images_debug693.html"


print("--- 侦察兵脚本(图片版)启动 ---")

try:
    # 抓取您指定的文章页
    print(f"正在抓取 目标文章页: {TARGET_URL}")
    response_article = requests.get(TARGET_URL, headers=HEADERS, timeout=10)
    response_article.raise_for_status()
    
    # 保存为文件
    with open(OUTPUT_FILENAME, 'w', encoding='utf-8') as f:
        f.write(response_article.text)
    
    print(f"\n--- ✅ 侦察完毕 ---")
    print(f"请将 '{OUTPUT_FILENAME}' 这个文件上传给我。")

except requests.exceptions.RequestException as e:
    print(f"\n--- ❌ 侦察失败 ---")
    print(f"错误: {e}")
    print("请检查您的网络连接或网站是否可以访问。")
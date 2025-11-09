import requests
import time

# 依然使用请求头伪装
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
                  '(KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
}

# 目标1：索引页
INDEX_URL = "https://youzhiyouxing.cn/topics/ezone/nodes/2"

# 目标2：一篇具体的文章页 (来自报告)
ARTICLE_URL = "https://youzhiyouxing.cn/materials/659"

print("--- 侦察兵脚本启动 ---")

try:
    # 1. 抓取索引页
    print(f"正在抓取 索引页: {INDEX_URL}")
    response_index = requests.get(INDEX_URL, headers=HEADERS, timeout=10)
    response_index.raise_for_status()
    
    # 保存为文件
    with open('index_debug.html', 'w', encoding='utf-8') as f:
        f.write(response_index.text)
    print(" -> 成功保存 'index_debug.html'")

    time.sleep(1) # 礼貌等待

    # 2. 抓取文章页
    print(f"正在抓取 文章页: {ARTICLE_URL}")
    response_article = requests.get(ARTICLE_URL, headers=HEADERS, timeout=10)
    response_article.raise_for_status()
    
    # 保存为文件
    with open('article_debug.html', 'w', encoding='utf-8') as f:
        f.write(response_article.text)
    print(" -> 成功保存 'article_debug.html'")

    print("\n--- ✅ 侦察完毕 ---")
    print("请将 'index_debug.html' 和 'article_debug.html' 两个文件上传给我。")

except requests.exceptions.RequestException as e:
    print(f"\n--- ❌ 侦察失败 ---")
    print(f"错误: {e}")
    print("请检查您的网络连接或网站是否可以访问。")
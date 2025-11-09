import requests
import time

# 依然使用请求头伪装
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
                  '(KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
}

# 目标1：课程页
LESSONS_URL = "https://youzhiyouxing.cn/curriculum/lessons"

# 目标2：新的索引页 (Skeleton Node 28)
SKELETON_URL = "https://youzhiyouxing.cn/topics/skeleton/nodes/28"

# 输出文件名
LESSONS_OUTPUT = "lessons_debug.html"
SKELETON_OUTPUT = "skeleton_node_debug.html"


print("--- 侦察兵脚本 (新目标版) 启动 ---")

try:
    # 1. 抓取课程页
    print(f"正在抓取 课程页: {LESSONS_URL}")
    response_lessons = requests.get(LESSONS_URL, headers=HEADERS, timeout=10)
    response_lessons.raise_for_status()
    
    # 保存为文件
    with open(LESSONS_OUTPUT, 'w', encoding='utf-8') as f:
        f.write(response_lessons.text)
    print(f" -> 成功保存 '{LESSONS_OUTPUT}'")

    time.sleep(1) # 礼貌等待

    # 2. 抓取 Skeleton 索引页
    print(f"正在抓取 Skeleton索引页: {SKELETON_URL}")
    response_skeleton = requests.get(SKELETON_URL, headers=HEADERS, timeout=10)
    response_skeleton.raise_for_status()
    
    # 保存为文件
    with open(SKELETON_OUTPUT, 'w', encoding='utf-8') as f:
        f.write(response_skeleton.text)
    print(f" -> 成功保存 '{SKELETON_OUTPUT}'")

    print("\n--- ✅ 侦察完毕 ---")
    print(f"请将 '{LESSONS_OUTPUT}' 和 '{SKELETON_OUTPUT}' 这两个文件上传给我。")

except requests.exceptions.RequestException as e:
    print(f"\n--- ❌ 侦察失败 ---")
    print(f"错误: {e}")
    print("请检查您的网络连接或网站是否可以访问。")
import os
import re
import json
import time
import requests
import hashlib
from bs4 import BeautifulSoup
from urllib.parse import urljoin

# --- 1. 全局配置 (Global Configuration) ---

# 【v7.1 修正】获取脚本所在的绝对路径
# 这确保 "E大干货合集" 文件夹总是创建在 .py 文件的旁边
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

# 目标网站的根
BASE_URL = "https://youzhiyouxing.cn"

# 根目录 (v7.1 修正: 路径基于 SCRIPT_DIR)
ROOT_DIR = os.path.join(SCRIPT_DIR, "E大干货合集")

# 图片保存目录 (v7.1 修正: 路径基于 ROOT_DIR)
IMAGE_DIR = os.path.join(ROOT_DIR, "images")

# 我们要爬取的3个板块
TARGET_NODES = {
    "01-投资理念": "2",
    "02-投资策略": "14",
    "03-人生哲学": "18"
}

# 伪装成浏览器的请求头
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
                  '(KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
}

# 启动一个共享的 Session，提高网络效率
SESSION = requests.Session()
SESSION.headers.update(HEADERS)


# --- 2. 辅助工具函数 (Helper Functions) ---

def get_soup(url):
    """
    一个“有礼貌”的请求函数，负责下载网页并返回一个 'Soup' 对象。
    """
    print(f"  [网络] 正在请求: {url}")
    try:
        time.sleep(1) # 礼貌性等待
        response = SESSION.get(url, timeout=10)
        response.raise_for_status() 
        soup = BeautifulSoup(response.text, 'lxml')
        return soup
    except requests.exceptions.RequestException as e:
        print(f"  [错误] 请求失败: {e}")
        return None

def sanitize_filename(name):
    """
    一个“清洁工”函数，负责“清洗”文件名。
    """
    name = re.sub(r'[\\/*?:"<>|]', "", name)
    name = name.strip().rstrip('.')
    if not name:
        name = "Untitled"
    return name

def download_image(img_url, save_dir):
    """
    【v3.0】下载图片并返回本地文件名。
    """
    if not img_url:
        return None

    try:
        full_img_url = urljoin(BASE_URL, img_url)
        url_without_params = full_img_url.split('?')[0]
        ext_match = re.search(r'\.(jpg|jpeg|png|gif|webp)', url_without_params, re.IGNORECASE)
        ext = ext_match.group(0) if ext_match else '.jpg' # 默认 .jpg
        
        url_hash = hashlib.md5(full_img_url.encode()).hexdigest()
        local_filename = f"{url_hash}{ext}"
        save_path = os.path.join(save_dir, local_filename)

        if os.path.exists(save_path):
            print(f"    -> [图片] 已存在: {local_filename}")
            return local_filename

        print(f"    -> [图片] 正在下载: {full_img_url}")
        img_response = SESSION.get(full_img_url, stream=True, timeout=10)
        img_response.raise_for_status()

        with open(save_path, 'wb') as f:
            for chunk in img_response.iter_content(1024):
                f.write(chunk)
        
        return local_filename
        
    except requests.exceptions.RequestException as e:
        print(f"    -> [错误] 图片下载失败: {e}")
        return None
    except Exception as e:
        print(f"    -> [错误] 图片处理失败: {e}")
        return None

# --- 3. 核心爬虫模块 (Core Scraper Modules) ---

def scrape_article_page(article_url, image_dir):
    """
    【模块一：爬取文章详情页 (v7.0 逻辑)】
    返回纯 HTML 以便 Typora 渲染。
    """
    soup = get_soup(article_url)
    if not soup:
        return None, None

    # 1. 定位主标题 (仅用于打印日志)
    title_tag = soup.find('h2', class_='tw-text-22')
    if not title_tag:
        title_tag = soup.find('h2')
    
    title = title_tag.get_text(strip=True) if title_tag else "未知标题"
    
    # 2. 定位正文容器
    content_body = soup.find('div', id='zx-material-marker-root').find('body')
    if not content_body:
        content_body = soup.find('div', id='zx-material-marker-root')
        if not content_body:
            print(f"    -> [失败] 在 {article_url} 找不到正文容器 #zx-material-marker-root")
            return title, None # 返回 None

    # 3. 【外科手术 - 图片】
    all_images_in_element = content_body.find_all('img')
    for img_tag in all_images_in_element:
        img_url = img_tag.get('data-src') or img_tag.get('src')
        if img_url:
            local_filename = download_image(img_url, image_dir)
            if local_filename:
                alt_text = img_tag.get('alt') or local_filename 
                # .md 在: section/chapter/file.md
                # .img 在: images/img.png
                # 相对路径是: ../../images/img.png
                md_image_path = f"../../images/{local_filename}"
                
                # --- 修改 HTML 标签 ---
                img_tag['src'] = md_image_path
                img_tag['alt'] = alt_text
                if img_tag.has_attr('data-src'): del img_tag['data-src']
                if img_tag.has_attr('class'):
                    img_tag['class'] = [c for c in img_tag['class'] if c not in ['lazy-image', 'lazy']]
                    if not img_tag['class']: del img_tag['class']
                
                # 清理懒加载引入的多余 <span> 包装
                parent = img_tag.parent
                while parent and parent.name == 'span' and not parent.attrs:
                    grandparent = parent.parent
                    parent.unwrap() # “解开”一层 <span>
                    parent = grandparent
                        
    # 4. 【外科手术 - 超链接】
    all_links_in_element = content_body.find_all('a')
    for link_tag in all_links_in_element:
        href = link_tag.get('href')
        if href:
            # 确保原文链接是绝对路径
            link_tag['href'] = urljoin(BASE_URL, href)

    # 5. 【v7.0 最终搬运】
    html_content = "".join(str(child) for child in content_body.children)

    # 6. 【v7.0 修正】只返回标题(用于日志)和纯 HTML 内容
    return title, html_content


def scrape_index_page(section_folder_name, node_id):
    """
    【模块二：爬取索引页 (v2.0 逻辑 - 稳定)】
    """
    index_url = f"{BASE_URL}/topics/ezone/nodes/{node_id}"
    soup = get_soup(index_url)
    if not soup:
        return []

    articles_list = []
    chapter_blocks = soup.select('div.node.active.tw-my-12')
    
    if not chapter_blocks:
         print(f"  [错误] 在 {index_url} 找不到任何 'div.node.active.tw-my-12' 章节容器")
         return []

    for block in chapter_blocks:
        chapter_h2 = block.find('h2', class_='tw-text-18')
        if not chapter_h2:
            chapter_h2 = block.find('h2') 
            if not chapter_h2:
                continue 

        chapter_name = sanitize_filename(chapter_h2.get_text(strip=True))
        article_links = block.select('a[href*="/materials/"]')
        
        for link_tag in article_links:
            title_text = link_tag.get_text(strip=True)
            url = link_tag.get('href')

            number_tag = link_tag.find_previous_sibling('span', class_='tw-mr-3')
            number = number_tag.get_text(strip=True) if number_tag else ""
            
            file_title = f"{number}-{title_text}" if number else title_text
            full_url = urljoin(BASE_URL, url)
                
            article_info = {
                "section_folder": section_folder_name, 
                "chapter_folder": chapter_name,     
                "filename": sanitize_filename(file_title) + ".md",
                "original_title": title_text,
                "url": full_url
            }
            articles_list.append(article_info)

    return articles_list

# --- 4. 主程序 (Main Execution) ---

def main():
    """
    【总指挥 (v7.1)】
    """
    print(f"--- 开始爬取 E大干货合集 (v7.1 - 路径修正版) ---")
    print(f"--- 所有文件将保存在: {ROOT_DIR}/ ---")

    # 1. 创建根目录
    os.makedirs(ROOT_DIR, exist_ok=True)
    
    # 2. 【v3.0】创建图片目录
    os.makedirs(IMAGE_DIR, exist_ok=True)
    print(f"--- 图片将保存在: {IMAGE_DIR}/ ---")
    
    all_articles_data = [] # 用于保存 .json 备份
    readme_content = ["# E大干货合集 总目录\n"] # 用于生成 README.md

    # 3. 遍历我们定义的3个目标板块
    for section_name, node_id in TARGET_NODES.items():
        
        print(f"\n[板块] 正在处理: {section_name}")
        section_path = os.path.join(ROOT_DIR, section_name)
        os.makedirs(section_path, exist_ok=True)
        
        readme_content.append(f"\n## {section_name}\n")
        
        # 4. 获取该板块下的所有文章层级
        articles_to_scrape = scrape_index_page(section_name, node_id)
        
        if not articles_to_scrape:
            print(f"  [警告] 在板块 {section_name} 没有找到任何文章。")
            continue
            
        print(f"  [信息] 在 {section_name} 找到 {len(articles_to_scrape)} 篇文章。")
        
        current_readme_chapter = ""

        # 5. 遍历这个板块的每篇文章
        for article in articles_to_scrape:
            
            chapter_path = os.path.join(section_path, article['chapter_folder'])
            os.makedirs(chapter_path, exist_ok=True)
            
            if article['chapter_folder'] != current_readme_chapter:
                readme_content.append(f"\n### {article['chapter_folder']}\n")
                current_readme_chapter = article['chapter_folder']

            file_path = os.path.join(chapter_path, article['filename'])
            
            print(f"  [文章] 正在处理: {article['original_title']}")
            
            # 5.4 【调用模块一】爬取文章正文
            title, html_content = scrape_article_page(article['url'], IMAGE_DIR)
            
            if html_content:
                # 5.5 【v7.0 修正】写入 .md 文件 (内容是纯 HTML)
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(html_content)
                
                print(f"    -> [成功] 已保存到: {file_path}")
                
                # 5.6 为 README.md 添加条目
                relative_path = os.path.join(
                    section_name, 
                    article['chapter_folder'], 
                    article['filename']
                ).replace("\\", "/") 
                
                readme_content.append(f"* [{article['original_title']}]({relative_path})")
                
                # 5.7 为 .json 备份添加数据
                article['content'] = "[...HTML 内容已保存到 .md 文件...]"
                article['local_path'] = file_path
                all_articles_data.append(article)
                
            else:
                print(f"    -> [失败] 无法爬取: {article['url']}")

    # 6. 【收尾】生成 .json 备份
    json_path = os.path.join(ROOT_DIR, 'youzhiyouxing_articles.json')
    print(f"\n[收尾] 正在生成 JSON 备份: {json_path}")
    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(all_articles_data, f, indent=2, ensure_ascii=False)

    # 7. 【收尾】生成 README.md 总目录
    readme_path = os.path.join(ROOT_DIR, 'README.md')
    print(f"[收尾] 正在生成 README.md 总目录: {readme_path}")
    with open(readme_path, 'w', encoding='utf-8') as f:
        f.write("\n".join(readme_content))

    print("\n--- ✅ 所有任务已完成 ---")

# --- 5. 运行主程序 ---
if __name__ == "__main__":
    main()
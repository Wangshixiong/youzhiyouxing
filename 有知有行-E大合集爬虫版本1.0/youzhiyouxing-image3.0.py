import os
import re
import json
import time
import requests
import hashlib
from bs4 import BeautifulSoup
from urllib.parse import urljoin

# --- 1. 全局配置 (Global Configuration) ---

# 目标网站的根
BASE_URL = "https://youzhiyouxing.cn"

# 根目录，设置为脚本所在目录
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.join(SCRIPT_DIR, "E大干货合集")

# 【v3.0】图片保存目录
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
    【模块一：爬取文章详情页 (v5.0 最终版)】
    【v5.0 修正】: 恢复了“原文发表于” (p.copyright) 的抓取。
    【v4.0 修正】: 修正了 "一个 <p> 标签中包含多个 <img>" 的bug。
    【v3.1 优化】: 优化了 "alt 文本"。
    """
    soup = get_soup(article_url)
    if not soup:
        return None, None

    # 1. 定位主标题 (v2.0 逻辑)
    title_tag = soup.find('h2', class_='tw-text-22')
    if not title_tag:
        title_tag = soup.find('h2')
        if not title_tag:
            print(f"    -> [失败] 在 {article_url} 找不到主标题 <h2>")
            return None, None

    title = title_tag.get_text(strip=True)
    
    # 2. 定位正文容器 (v3.0 逻辑)
    content_body = soup.find('div', id='zx-material-marker-root').find('body')
    if not content_body:
        content_body = soup.find('div', id='zx-material-marker-root')
        if not content_body:
            print(f"    -> [失败] 在 {article_url} 找不到正文容器 #zx-material-marker-root")
            return title, f"# {title}\n\n[爬取失败：未找到正文容器]"
    
    markdown_parts = [f"# {title}\n"]

    # 3. 【v5.0 核心逻辑】
    elements = content_body.find_all(['h2', 'p', 'ul', 'ol', 'blockquote'])

    for element in elements:
        tag_name = element.name
        
        # 1. 检查停止条件
        if "想法" in element.get_text(strip=True) and tag_name == 'h2':
            break 

        # 2. 【v5.0 修正】 优先检查并抓取 "copyright" 段落
        if tag_name == 'p' and 'copyright' in element.get('class', []):
            md_line = ""
            for content in element.contents:
                if content.name == 'a':
                    md_line += f"[{content.get_text(strip=True)}]({urljoin(BASE_URL, content.get('href', '#'))})"
                elif hasattr(content, 'string'):
                    md_line += content.string or ""
            
            # 使用 Markdown 引用格式
            markdown_parts.append(f"\n> {md_line.strip()}\n")
            continue # 本段落处理完毕，跳到下一个元素

        # 3. 【v4.0】处理图片 (支持一个 <p> 中有多张图)
        all_images_in_element = element.find_all('img')
        if all_images_in_element:
            for img_tag in all_images_in_element:
                img_url = img_tag.get('data-src') or img_tag.get('src')
                if img_url:
                    local_filename = download_image(img_url, image_dir)
                    if local_filename:
                        # 【v3.1 优化】alt 文本
                        alt_text = img_tag.get('alt') or local_filename 
                        md_image_path = f"../../images/{local_filename}"
                        markdown_parts.append(f"![{alt_text}]({md_image_path})\n")
            
            if not element.get_text(strip=True):
                continue

        # 4. 【v4.0】处理标准文本元素
        if tag_name == 'h2':
            markdown_parts.append(f"\n## {element.get_text(strip=True)}\n")
        elif tag_name == 'ul':
            items = [li.get_text(strip=True) for li in element.find_all('li')]
            markdown_parts.append("\n" + "\n".join(f"* {item}" for item in items) + "\n")
        elif tag_name == 'ol':
            items = [li.get_text(strip=True) for li in element.find_all('li')]
            markdown_parts.append("\n" + "\n".join(f"1. {item}" for item in items) + "\n")
        elif tag_name == 'blockquote':
            markdown_parts.append(f"> {element.get_text(strip=True)}\n")
        elif tag_name == 'p':
            md_line = ""
            for child in element.contents:
                if not hasattr(child, 'name'): 
                    md_line += child.string or ""
                    continue
                
                if child.name == 'span' and child.find('img'):
                    continue

                child_name = child.name
                if child_name in ['i', 'em']:
                    md_line += f"*{child.get_text(strip=True)}*"
                elif child_name in ['b', 'strong']:
                    md_line += f"**{child.get_text(strip=True)}**"
                elif child_name == 'a':
                    md_line += f"[{child.get_text(strip=True)}]({urljoin(BASE_URL, child.get('href', '#'))})"
                elif child.name is None:
                    md_line += child.string or ""
                else:
                    md_line += child.get_text() 
            
            md_line_stripped = md_line.strip()
            if md_line_stripped:
                markdown_parts.append(md_line_stripped + "\n")

    # 5. 返回重建好的 Markdown 全文
    return title, "\n".join(markdown_parts)


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
    【总指挥 (v5.0)】
    """
    print(f"--- 开始爬取 E大干货合集 (v5.0) ---")
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
            title, markdown_content = scrape_article_page(article['url'], IMAGE_DIR)
            
            if markdown_content:
                # 5.5 写入 .md 文件
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(markdown_content)
                
                print(f"    -> [成功] 已保存到: {file_path}")
                
                # 5.6 为 README.md 添加条目
                relative_path = os.path.join(
                    section_name, 
                    article['chapter_folder'], 
                    article['filename']
                ).replace("\\", "/") 
                
                readme_content.append(f"* [{article['original_title']}]({relative_path})")
                
                # 5.7 为 .json 备份添加数据
                article['markdown_content'] = "[...内容已保存到 .md 文件...]"
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
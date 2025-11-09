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

# 【v7.1 升级】
# 在 "投资知识体系" 中补全所有 5 个页签
COLLECTIONS = [
    {
        "collection_name": "E大干货合集",
        "targets": [
            # "is_flat": False 表示 "01-投资理念" 会成为 "E大干货合集" 下的子目录
            {"name": "01-投资理念", "id": "2", "type": "ezone", "is_flat": False},
            {"name": "02-投资策略", "id": "14", "type": "ezone", "is_flat": False},
            {"name": "03-人生哲学", "id": "18", "type": "ezone", "is_flat": False},
        ]
    },
    {
        "collection_name": "投资知识体系",
        "targets": [
            # "is_flat": True 表示该板块的 *内容* (章节) 会被直接放入 "投资知识体系" 根目录
            {"name": "投资第一步", "id": "28", "type": "ezone", "is_flat": True},
            {"name": "长期投资", "id": "31", "type": "ezone", "is_flat": True},
            {"name": "活钱管理", "id": "29", "type": "ezone", "is_flat": True},
            {"name": "稳健理财", "id": "30", "type": "ezone", "is_flat": True},
            {"name": "保险保障", "id": "32", "type": "ezone", "is_flat": True},
        ]
    },
    {
        "collection_name": "有知有行投资第一课",
        "targets": [
            # "is_flat": True 逻辑同上
            {"name": "有知有行投资第一课", "url": "https://youzhiyouxing.cn/curriculum/lessons", "type": "lessons", "is_flat": True},
        ]
    }
]


# 伪装成浏览器的请求头


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
    print(f"    [网络] 正在请求: {url}")
    try:
        time.sleep(1) # 礼貌性等待
        response = SESSION.get(url, timeout=10)
        response.raise_for_status() 
        soup = BeautifulSoup(response.text, 'lxml')
        return soup
    except requests.exceptions.RequestException as e:
        print(f"    [错误] 请求失败: {e}")
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
            print(f"      -> [图片] 已存在: {local_filename}")
            return local_filename

        print(f"      -> [图片] 正在下载: {full_img_url}")
        img_response = SESSION.get(full_img_url, stream=True, timeout=10)
        img_response.raise_for_status()

        with open(save_path, 'wb') as f:
            for chunk in img_response.iter_content(1024):
                f.write(chunk)
        
        return local_filename
        
    except requests.exceptions.RequestException as e:
        print(f"      -> [错误] 图片下载失败: {e}")
        return None
    except Exception as e:
        print(f"      -> [错误] 图片处理失败: {e}")
        return None

# --- 3. 核心爬虫模块 (Core Scraper Modules) ---

def scrape_article_page(article_url, image_dir):
    """
    【模块一：爬取文章详情页 (v5.0 最终版 - 稳定)】
    """
    soup = get_soup(article_url)
    if not soup:
        return None, None

    # 1. 定位主标题 (v2.0 逻辑)
    title_tag = soup.find('h2', class_='tw-text-22')
    if not title_tag:
        title_tag = soup.find('h2')
        if not title_tag:
            print(f"      -> [失败] 在 {article_url} 找不到主标题 <h2>")
            return None, None

    title = title_tag.get_text(strip=True)
    
    # 2. 定位正文容器 (v3.0 逻辑)
    content_body = soup.find('div', id='zx-material-marker-root').find('body')
    if not content_body:
        content_body = soup.find('div', id='zx-material-marker-root')
        if not content_body:
            print(f"      -> [失败] 在 {article_url} 找不到正文容器 #zx-material-marker-root")
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
                        # 【v7.0 修正】图片路径现在是固定的 ../../images
                        # Case 1 (flat=F): ROOT/SECTION/CHAPTER/file.md -> ../../images -> ROOT/images
                        # Case 2 (flat=T): ROOT/CHAPTER/file.md -> ../../images -> ROOT/images (错误!)
                        #
                        # 重新计算路径:
                        # Case 1 (flat=F): ROOT/SECTION/CHAPTER/file.md -> ../../images
                        # Case 2 (flat=T): ROOT/CHAPTER/file.md -> ../images
                        #
                        # 发现问题，`scrape_article_page` 不知道自己是 flat 还是 non-flat。
                        #
                        # 统一解决方案：
                        # 在 main 函数中，根据 article['section_folder'] 是否为空来决定图片路径！
                        # 这里暂时不处理，留在 main 函数中
                        markdown_parts.append(f"![{alt_text}]({local_filename})\n") # 临时占位符
            
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


def scrape_index_page(section_folder_name, node_id, is_flat_structure=False):
    """
    【模块二：爬取 Ezone/Skeleton 索引页 (v7.0 升级)】
    - 增加 is_flat_structure 参数
    """
    index_url = f"{BASE_URL}/topics/ezone/nodes/{node_id}"
    print(f"    [Ezone] 正在扫描索引页: {index_url}")
    soup = get_soup(index_url)
    if not soup:
        return []

    articles_list = []
    chapter_blocks = soup.select('div.node.active.tw-my-12')
    
    if not chapter_blocks:
         print(f"    [错误] 在 {index_url} 找不到任何 'div.node.active.tw-my-12' 章节容器")
         return []

    # 【v7.0 升级】如果 `is_flat` 为 True, `section_folder` 设为空, 章节直接放根目录
    folder_name_to_use = "" if is_flat_structure else section_folder_name

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
                "section_folder": folder_name_to_use, # <-- 【v7.0 升级】
                "chapter_folder": chapter_name,     
                "filename": sanitize_filename(file_title) + ".md",
                "original_title": title_text,
                "url": full_url
            }
            articles_list.append(article_info)

    return articles_list

def scrape_lessons_index_page(section_folder_name, node_url, is_flat_structure=False):
    """
    【模块三：爬取课程索引页 (v7.0 升级)】
    - 增加 is_flat_structure 参数
    """
    print(f"    [课程] 正在扫描课程索引页: {node_url}")
    soup = get_soup(node_url)
    if not soup:
        return []

    articles_list = []
    chapter_blocks = soup.select('div.tw-space-y-8 div.tw-px-5')
    
    if not chapter_blocks:
        print(f"    [错误] 在 {node_url} 找不到任何 'div.tw-px-5' 章节容器")
        return []

    # 【v7.0 升级】如果 `is_flat` 为 True, `section_folder` 设为空, 章节直接放根目录
    folder_name_to_use = "" if is_flat_structure else section_folder_name

    for block in chapter_blocks:
        chapter_h2 = block.find('h2', class_='tw-text-14')
        if not chapter_h2:
            continue
        
        chapter_name = sanitize_filename(chapter_h2.get_text(strip=True))
        article_links = block.select('a[href*="/materials/"]')
        
        for link_tag in article_links:
            title_tag = link_tag.find('h3')
            if not title_tag:
                continue
            
            title_text = title_tag.get_text(strip=True)
            url = link_tag.get('href')

            number_tag = link_tag.find('label')
            number = ""
            if number_tag:
                number = number_tag.get_text(strip=True).strip()
                if not number:
                    if number_tag.find('img'):
                        number = "00"
            
            file_title = f"{number}-{title_text}" if number else title_text
            full_url = urljoin(BASE_URL, url)
                
            article_info = {
                "section_folder": folder_name_to_use, # <-- 【v7.0 升级】
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
    【总指挥 (v7.0)】
    - 遍历 COLLECTIONS 列表，为每个“合集”创建独立的根目录、图片目录、README 和 JSON。
    """
    print(f"--- 开始爬取 有知有行 全合集 (v7.0) ---")
    
    # 1. 遍历我们定义的每个“合集”
    for collection in COLLECTIONS:
        collection_name = collection['collection_name']
        
        # 2. 为每个合集设置独立的路径
        ROOT_DIR = os.path.join(SCRIPT_DIR, collection_name)
        IMAGE_DIR = os.path.join(ROOT_DIR, "images")
        
        print(f"\n--- [合集] 正在处理: {collection_name} ---")
        print(f"    [路径] 合集根目录: {ROOT_DIR}")

        os.makedirs(ROOT_DIR, exist_ok=True)
        os.makedirs(IMAGE_DIR, exist_ok=True)
        
        all_articles_data = [] # 每个合集都有自己的备份
        readme_content = [f"# {collection_name} 总目录\n"] # 每个合集都有自己的README

        # 3. 遍历该合集下的所有“目标板块”
        for target in collection['targets']:
            
            target_name = target['name']
            is_flat = target['is_flat']
            print(f"  [板块] 正在处理: {target_name}")
            
            articles_to_scrape = []
            
            # 4. 根据类型调用不同的索引爬虫
            if target['type'] == 'ezone':
                print("    [模式] Ezone/Skeleton 索引模式")
                articles_to_scrape = scrape_index_page(target_name, target['id'], is_flat_structure=is_flat)
            
            elif target['type'] == 'lessons':
                print("    [模式] Lessons 课程模式")
                articles_to_scrape = scrape_lessons_index_page(target_name, target['url'], is_flat_structure=is_flat)
            
            if not articles_to_scrape:
                print(f"    [警告] 在板块 {target_name} 没有找到任何文章。")
                continue
                
            print(f"    [信息] 在 {target_name} 找到 {len(articles_to_scrape)} 篇文章。")
            
            current_readme_chapter = ""

            # 5. 遍历这个板块的每篇文章
            for article in articles_to_scrape:
                
                # 【v7.0 核心路径逻辑】
                # `article['section_folder']` 要么是 "01-投资理念", 要么是 "" (空字符串)
                section_path = os.path.join(ROOT_DIR, article['section_folder'])
                chapter_path = os.path.join(section_path, article['chapter_folder'])
                os.makedirs(chapter_path, exist_ok=True)
                
                if article['chapter_folder'] != current_readme_chapter:
                    # 如果 section_folder 不为空，说明是 "E大合集" 模式, README 加一级
                    if article['section_folder']:
                        # 检查是否是新的 section
                        current_section_readme = f"\n## {article['section_folder']}\n"
                        if current_section_readme not in readme_content:
                             readme_content.append(current_section_readme)
                    
                    readme_content.append(f"\n### {article['chapter_folder']}\n")
                    current_readme_chapter = article['chapter_folder']

                file_path = os.path.join(chapter_path, article['filename'])
                
                print(f"    [文章] 正在处理: {article['original_title']}")
                
                # 5.4 【调用模块一】爬取文章正文
                title, markdown_content = scrape_article_page(article['url'], IMAGE_DIR)
                
                if markdown_content:
                    
                    # 【v7.0 路径修正】
                    # 确定图片相对路径 (../../images 还是 ../images)
                    if article['section_folder']: # "E大合集" 模式 (flat=False)
                        # 路径: ROOT/SECTION/CHAPTER/file.md
                        # 相对 images: ../../images/
                        img_path_prefix = "../../images/"
                    else: # "平铺" 模式 (flat=True)
                        # 路径: ROOT/CHAPTER/file.md
                        # 相对 images: ../images/
                        img_path_prefix = "../images/"
                    
                    # 替换图片路径占位符
                    markdown_content = re.sub(
                        r"!\[(.*?)]\((.*?)\)",
                        lambda match: f"![{match.group(1)}]({img_path_prefix}{match.group(2)})",
                        markdown_content
                    )

                    # 5.5 写入 .md 文件
                    with open(file_path, 'w', encoding='utf-8') as f:
                        f.write(markdown_content)
                    
                    print(f"      -> [成功] 已保存到: {file_path}")
                    
                    # 5.6 为 README.md 添加条目
                    # 构造从 ROOT_DIR 开始的相对路径
                    relative_path = os.path.relpath(file_path, ROOT_DIR).replace("\\", "/")
                    
                    readme_content.append(f"* [{article['original_title']}]({relative_path})")
                    
                    # 5.7 为 .json 备份添加数据
                    article['markdown_content'] = "[...内容已保存到 .md 文件...]"
                    article['local_path'] = file_path
                    all_articles_data.append(article)
                    
                else:
                    print(f"      -> [失败] 无法爬取: {article['url']}")

        # 6. 【收尾】为 *当前合集* 生成 .json 备份
        json_path = os.path.join(ROOT_DIR, f"{collection_name}_articles.json")
        print(f"  [收尾] 正在为 {collection_name} 生成 JSON 备份: {json_path}")
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(all_articles_data, f, indent=2, ensure_ascii=False)

        # 7. 【收尾】为 *当前合集* 生成 README.md 总目录
        readme_path = os.path.join(ROOT_DIR, 'README.md')
        print(f"  [收尾] 正在为 {collection_name} 生成 README.md 总目录: {readme_path}")
        with open(readme_path, 'w', encoding='utf-8') as f:
            f.write("\n".join(readme_content))

    print("\n--- ✅ 所有合集任务已完成 ---")

# --- 5. 运行主程序 ---
if __name__ == "__main__":
    main()
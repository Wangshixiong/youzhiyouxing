import os
import re
import json
import time
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin

# --- 1. 全局配置 (Global Configuration) ---

# 目标网站的根
BASE_URL = "https://youzhiyouxing.cn"

# 根目录，所有内容将保存在这里
ROOT_DIR = "E大干货合集"

# 我们要爬取的3个板块，以及它们对应的文件夹名
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

# --- 2. 辅助工具函数 (Helper Functions) ---

def get_soup(url):
    """
    一个“有礼貌”的请求函数，负责下载网页并返回一个 'Soup' 对象。
    它会自动处理请求头、异常并包含1秒的礼貌性延迟。
    """
    print(f"  [网络] 正在请求: {url}")
    try:
        # 1. 礼貌性等待，防止IP被封
        time.sleep(1) 
        
        response = requests.get(url, headers=HEADERS, timeout=10)
        response.raise_for_status() # 如果请求失败 (如 404, 500) 则抛出异常
        
        # 使用 'lxml' 解析器，容错性更强
        soup = BeautifulSoup(response.text, 'lxml')
        return soup
    except requests.exceptions.RequestException as e:
        print(f"  [错误] 请求失败: {e}")
        return None

def sanitize_filename(name):
    """
    一个“清洁工”函数，负责“清洗”文件名。
    它会移除在 Windows/Mac/Linux 上不允许作为文件名的字符。
    """
    # 移除 / \ : * ? " < > | 等非法字符
    name = re.sub(r'[\\/*?:"<>|]', "", name)
    # 移除开头和末尾的 . 和空格
    name = name.strip().rstrip('.')
    # 确保文件名不为空
    if not name:
        name = "Untitled"
    return name

# --- 3. 核心爬虫模块 (Core Scraper Modules) ---

def scrape_article_page(article_url):
    """
    【模块一：爬取文章详情页 (v2.0 修正版)】
    使用 `zx-material-marker-root` ID 精确制导。
    """
    soup = get_soup(article_url)
    if not soup:
        return None, None

    # 1. 定位主标题 (v1的逻辑是正确的)
    title_tag = soup.find('h2', class_='tw-text-22') # 使用更精确的 class 定位
    if not title_tag:
        title_tag = soup.find('h2') # 降级
        if not title_tag:
            print(f"    -> [失败] 在 {article_url} 找不到主标题 <h2>")
            return None, None

    title = title_tag.get_text(strip=True)
    
    # 2. 【v2.0 关键修正】
    # 不再遍历兄弟节点，而是直奔正文容器 `div#zx-material-marker-root`
    content_container = soup.find('div', id='zx-material-marker-root')
    
    if not content_container:
        print(f"    -> [失败] 在 {article_url} 找不到正文容器 #zx-material-marker-root")
        return title, f"# {title}\n\n[爬取失败：未找到正文容器]"

    
    markdown_parts = [f"# {title}\n"] # Markdown 的1级标题

    # 3. 遍历这个容器的【所有子节点】
    # 我们使用 .children 来遍历直接子节点
    for element in content_container.children:
        if not hasattr(element, 'name') or element.name is None:
            continue # 跳过空行或纯文本节点(如果有的话)

        tag_name = element.name
        text = element.get_text(strip=True)

        # 4. 智能识别并转换
        if tag_name == 'h2': # 识别为“小标题” (H2)
            markdown_parts.append(f"\n## {text}\n")
        elif tag_name == 'p': # 识别为“段落”
            # 处理段落内的 <i> <em> <strong> <b> <a> 等
            md_line = ""
            for child in element.contents:
                if child.name in ['i', 'em']:
                    md_line += f"*{child.get_text(strip=True)}*"
                elif child.name in ['b', 'strong']:
                    md_line += f"**{child.get_text(strip=True)}**"
                elif child.name == 'a':
                    md_line += f"[{child.get_text(strip=True)}]({child.get('href', '#')})"
                elif child.name is None: # 纯文本
                    md_line += child.string or ""
                else:
                    md_line += child.get_text(strip=True)
            markdown_parts.append(md_line.strip() + "\n")
        elif tag_name == 'ul': # 识别为“无序列表”
            items = [li.get_text(strip=True) for li in element.find_all('li')]
            markdown_parts.append("\n" + "\n".join(f"* {item}" for item in items) + "\n")
        elif tag_name == 'ol': # 识别为“有序列表”
            items = [li.get_text(strip=True) for li in element.find_all('li')]
            markdown_parts.append("\n" + "\n".join(f"1. {item}" for item in items) + "\n")
        elif tag_name == 'blockquote': # 识别为“引用”
            markdown_parts.append(f"> {text}\n")
        
    # 5. 返回重建好的 Markdown 全文
    return title, "\n".join(markdown_parts)

def scrape_index_page(section_folder_name, node_id):
    """
    【模块二：爬取索引页 (v2.0 修正版)】
    使用精确的 class 选择器，不再依赖脆弱的兄弟节点遍历。
    """
    index_url = f"{BASE_URL}/topics/ezone/nodes/{node_id}"
    soup = get_soup(index_url)
    if not soup:
        return []

    articles_list = []
    
    # 【v2.0 关键修正】
    # 1. 找到所有“章”的容器。根据 `index_debug.html`，
    #    它们是 <div class="node active tw-my-12 ...">
    chapter_blocks = soup.select('div.node.active.tw-my-12')
    
    if not chapter_blocks:
         print(f"  [错误] 在 {index_url} 找不到任何 'div.node.active.tw-my-12' 章节容器")
         return []

    for block in chapter_blocks:
        # 2. 在这个容器内，找到“章”标题 (h2.tw-text-18)
        chapter_h2 = block.find('h2', class_='tw-text-18')
        if not chapter_h2:
            continue # 找不到章标题，跳过这个 block

        chapter_name = sanitize_filename(chapter_h2.get_text(strip=True))

        # 3. 在这个容器内，找到【所有】的文章链接
        #    根据 `index_debug.html`，它们是 <a href="/materials/...">
        article_links = block.select('a[href*="/materials/"]')
        
        for link_tag in article_links:
            title_text = link_tag.get_text(strip=True)
            url = link_tag.get('href')

            # 抓取 "01" "02" "导" 这样的序号
            number_tag = link_tag.find_previous_sibling('span', class_='tw-mr-3')
            number = number_tag.get_text(strip=True) if number_tag else ""
            
            # 规范化文件名，如 "01-投资是一场赌博"
            file_title = f"{number}-{title_text}" if number else title_text
            
            # 规范化 URL (处理 /materials/659 这样的相对路径)
            # 使用 urljoin 确保万无一失
            full_url = urljoin(BASE_URL, url)
                
            # 按您的要求组织数据
            article_info = {
                "section_folder": section_folder_name, # "01-投资理念"
                "chapter_folder": chapter_name,     # "第一章..." 或 "开篇介绍"
                "filename": sanitize_filename(file_title) + ".md",
                "original_title": title_text,
                "url": full_url
            }
            articles_list.append(article_info)

    return articles_list

# --- 4. 主程序 (Main Execution) ---

def main():
    """
    【总指挥 (v2.0)】
    (此函数逻辑不变，因为它调用的是修正后的模块)
    """
    print(f"--- 开始爬取 E大干货合集 (v2.0) ---")
    print(f"--- 所有文件将保存在: {ROOT_DIR}/ ---")

    # 创建根目录
    os.makedirs(ROOT_DIR, exist_ok=True)
    
    all_articles_data = [] # 用于保存 .json 备份
    readme_content = ["# E大干货合集 总目录\n"] # 用于生成 README.md

    # 1. 遍历我们定义的3个目标板块
    for section_name, node_id in TARGET_NODES.items():
        
        print(f"\n[板块] 正在处理: {section_name}")
        section_path = os.path.join(ROOT_DIR, section_name)
        os.makedirs(section_path, exist_ok=True)
        
        readme_content.append(f"\n## {section_name}\n")
        
        # 2. 【调用模块二】获取该板块下的所有文章层级
        articles_to_scrape = scrape_index_page(section_name, node_id)
        
        if not articles_to_scrape:
            print(f"  [警告] 在板块 {section_name} 没有找到任何文章。")
            continue
            
        print(f"  [信息] 在 {section_name} 找到 {len(articles_to_scrape)} 篇文章。")
        
        current_readme_chapter = ""

        # 3. 遍历这个板块的每篇文章
        for article in articles_to_scrape:
            
            # 3.1 创建“章”目录 (如 "第一章...")
            chapter_path = os.path.join(section_path, article['chapter_folder'])
            os.makedirs(chapter_path, exist_ok=True)
            
            # 3.2 动态生成 README.md 的章节标题
            if article['chapter_folder'] != current_readme_chapter:
                readme_content.append(f"\n### {article['chapter_folder']}\n")
                current_readme_chapter = article['chapter_folder']

            # 3.3 准备保存文章的最终路径
            file_path = os.path.join(chapter_path, article['filename'])
            
            print(f"  [文章] 正在处理: {article['original_title']}")
            
            # 3.4 【调用模块一】爬取文章正文
            title, markdown_content = scrape_article_page(article['url'])
            
            if markdown_content:
                # 3.5 写入 .md 文件
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(markdown_content)
                
                print(f"    -> [成功] 已保存到: {file_path}")
                
                # 3.6 为 README.md 添加条目
                relative_path = os.path.join(
                    section_name, 
                    article['chapter_folder'], 
                    article['filename']
                ).replace("\\", "/") # 确保路径分隔符在README中是 /
                
                readme_content.append(f"* [{article['original_title']}]({relative_path})")
                
                # 3.7 为 .json 备份添加数据
                article['markdown_content'] = markdown_content
                article['local_path'] = file_path
                all_articles_data.append(article)
                
            else:
                print(f"    -> [失败] 无法爬取: {article['url']}")

    # 4. 【收尾】生成 .json 备份
    json_path = os.path.join(ROOT_DIR, 'youzhiyouxing_articles.json')
    print(f"\n[收尾] 正在生成 JSON 备份: {json_path}")
    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(all_articles_data, f, indent=2, ensure_ascii=False)

    # 5. 【收尾】生成 README.md 总目录
    readme_path = os.path.join(ROOT_DIR, 'README.md')
    print(f"[收尾] 正在生成 README.md 总目录: {readme_path}")
    with open(readme_path, 'w', encoding='utf-8') as f:
        f.write("\n".join(readme_content))

    print("\n--- ✅ 所有任务已完成 ---")

# --- 5. 运行主程序 ---
if __name__ == "__main__":
    main()
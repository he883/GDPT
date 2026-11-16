# -*- coding: utf-8 -*-
"""
柯南影视 - knvod.com 适配版 (完整修正)
- 分类：电影(1)、连续剧(2)、动漫(3)、综艺(4)
- 首页/分类/搜索/详情/播放 完整支持
"""
import re
import json
import time
import base64
import urllib.parse
from base.spider import Spider


class Spider(Spider):
    host = 'https://knvod.com'
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
        'Accept-Language': 'zh-CN,zh;q=0.9',
        'Referer': host + '/'
    }
    cache = {}
    cache_ttl_map = {
        'default': 800,
        'search': 300,
        'detail': 600,
        'play': 60
    }

    def init(self, extend=''):
        if extend:
            try:
                ext = json.loads(extend)
                if 'host' in ext:
                    self.host = ext['host'].rstrip('/')
                    self.headers['Referer'] = self.host + '/'
            except:
                pass

    def _request(self, url, timeout=10, cache_type='default'):
        cache_key = url
        ttl = self.cache_ttl_map.get(cache_type, 800)
        if cache_key in self.cache:
            ct, content = self.cache[cache_key]
            if time.time() - ct < ttl:
                return content

        for attempt in range(2):
            try:
                resp = self.fetch(url, headers=self.headers, timeout=timeout)
                html = resp.text if hasattr(resp, 'text') else str(resp)
                if html and ('<title>' in html or len(html) > 500):
                    self.cache[cache_key] = (time.time(), html)
                    return html
            except Exception as e:
                print(f"[Knvod] 请求失败({attempt+1}/2): {url} - {e}")
                time.sleep(0.5)
        return ''

    # ---------- 固定分类 ----------
    def homeContent(self, filter):
        return {
            'class': [
                {'type_id': '1', 'type_name': '电影'},
                {'type_id': '2', 'type_name': '连续剧'},
                {'type_id': '3', 'type_name': '动漫'},
                {'type_id': '4', 'type_name': '综艺'},
            ]
        }

    # ---------- 通用视频列表提取（首页/分类）----------
    def _extract_videos(self, html):
        videos = []
        for block in re.finditer(r'<div[^>]*class="[^"]*public-list-box[^"]*"[^>]*>(.*?)</div>\s*</div>\s*</div>', html, re.S):
            block_html = block.group(1)
            a_match = re.search(r'<a[^>]*href="([^"]*)"[^>]*>', block_html)
            if not a_match:
                continue
            href = a_match.group(1)
            vid = re.search(r'/vdetail/(\d+)\.html', href)
            if not vid:
                continue
            vod_id = vid.group(1)

            pic = ''
            img_match = re.search(r'data-src="([^"]+)"', block_html)
            if not img_match:
                img_match = re.search(r'src="([^"]+)"', block_html)
            if img_match:
                pic = img_match.group(1)

            title = ''
            title_match = re.search(r'<a[^>]*class="[^"]*time-title[^"]*"[^>]*title="([^"]+)"', block_html)
            if not title_match:
                title_match = re.search(r'<a[^>]*class="[^"]*time-title[^"]*"[^>]*>([^<]+)</a>', block_html)
            if title_match:
                title = title_match.group(1).strip()

            remarks = ''
            remarks_match = re.search(r'<span[^>]*class="[^"]*public-list-prb[^"]*"[^>]*>([^<]+)</span>', block_html)
            if remarks_match:
                remarks = remarks_match.group(1).strip()

            if title:
                videos.append({
                    'vod_id': vod_id,
                    'vod_name': title,
                    'vod_pic': pic,
                    'vod_remarks': remarks
                })

        seen = set()
        unique = []
        for v in videos:
            if v['vod_id'] not in seen:
                seen.add(v['vod_id'])
                unique.append(v)
        return unique

    # ---------- 搜索页专用视频列表提取 ----------
    def _extract_search_videos(self, html):
        """从搜索结果页提取视频卡片（结构：.public-list-box.search-box）"""
        videos = []
        for block in re.finditer(r'<div[^>]*class="[^"]*search-box[^"]*"[^>]*>(.*?)<div class="thumb-menu flex">', html, re.S):
            block_html = block.group(1)

            a_match = re.search(r'<a[^>]*href="([^"]*)"[^>]*>', block_html)
            if not a_match:
                continue
            href = a_match.group(1)
            vid = re.search(r'/vdetail/(\d+)\.html', href)
            if not vid:
                continue
            vod_id = vid.group(1)

            pic = ''
            img_match = re.search(r'data-src="([^"]+)"', block_html)
            if not img_match:
                img_match = re.search(r'src="([^"]+)"', block_html)
            if img_match:
                pic = img_match.group(1)

            title = ''
            title_match = re.search(r'<div[^>]*class="[^"]*thumb-txt[^"]*"[^>]*>.*?<a[^>]*>([^<]+)</a>', block_html, re.S)
            if title_match:
                title = title_match.group(1).strip()

            remarks = ''
            remarks_match = re.search(r'<span[^>]*class="[^"]*public-list-prb[^"]*"[^>]*>([^<]+)</span>', block_html)
            if remarks_match:
                remarks = remarks_match.group(1).strip()

            if title:
                videos.append({
                    'vod_id': vod_id,
                    'vod_name': title,
                    'vod_pic': pic,
                    'vod_remarks': remarks
                })

        seen = set()
        unique = []
        for v in videos:
            if v['vod_id'] not in seen:
                seen.add(v['vod_id'])
                unique.append(v)
        return unique

    # ---------- 首页推荐 ----------
    def homeVideoContent(self):
        html = self._request(self.host, cache_type='default')
        if not html:
            return {'list': []}
        return {'list': self._extract_videos(html)}

    # ---------- 分类列表（支持分页） ----------
    def categoryContent(self, tid, pg, filter, extend):
        if str(tid) not in ['1', '2', '3', '4']:
            return {'list': [], 'pagecount': 0, 'page': pg}

        url = f"{self.host}/vshow/{tid}--------{pg}---.html"
        html = self._request(url, cache_type='default')
        if not html:
            return {'list': [], 'pagecount': 0, 'page': pg}
        videos = self._extract_videos(html)

        pagecount = 1
        page_match = re.search(r'共\s*[\d,]+\s*条数据[,，]\s*当前\s*\d+\s*[/／]\s*(\d+)\s*页', html)
        if page_match:
            pagecount = int(page_match.group(1))
        else:
            last_match = re.search(r'<a[^>]*href="[^"]*--------(\d+)---.html"[^>]*>尾页</a>', html)
            if last_match:
                pagecount = int(last_match.group(1))

        return {'list': videos, 'pagecount': pagecount, 'page': pg}

    # ---------- 搜索 ----------
    def searchContent(self, key, quick, pg='1'):
        url = f"{self.host}/search/-------------.html?wd={urllib.parse.quote_plus(key)}"
        html = self._request(url, cache_type='search')
        if not html:
            return {'list': [], 'page': pg}

        # 优先使用搜索页专用解析
        videos = self._extract_search_videos(html)

        # 回退到通用方法
        if not videos:
            videos = self._extract_videos(html)

        # 最终兜底
        if not videos:
            for a in re.finditer(r'<a[^>]*href="(/vdetail/\d+\.html)"[^>]*>([^<]+)</a>', html):
                href = a.group(1)
                title = a.group(2).strip()
                vid = re.search(r'/vdetail/(\d+)\.html', href)
                if vid:
                    videos.append({'vod_id': vid.group(1), 'vod_name': title, 'vod_pic': '', 'vod_remarks': ''})

        return {'list': videos, 'page': pg}

    # ---------- 详情页解析 ----------
    def detailContent(self, ids):
        if not ids:
            return {'list': []}
        vod_id = ids[0]
        url = f"{self.host}/vdetail/{vod_id}.html"
        html = self._request(url, cache_type='detail')
        if not html:
            return {'list': []}
        video = self._parse_detail(html, vod_id)
        return {'list': [video]}

    def _extract_div_blocks(self, html, class_name):
        """精确提取包含特定 class 的完整 div 块（层级计数法）"""
        blocks = []
        pos = 0
        pattern = re.compile(rf'<div[^>]*class="[^"]*{class_name}[^"]*"[^>]*>')
        while True:
            m = pattern.search(html, pos)
            if not m:
                break
            start = m.start()
            depth = 1
            i = m.end()
            while i < len(html) and depth > 0:
                next_open = html.find('<div', i)
                next_close = html.find('</div>', i)
                if next_close == -1:
                    break
                if next_open != -1 and next_open < next_close:
                    depth += 1
                    i = next_open + 4
                else:
                    depth -= 1
                    if depth == 0:
                        end = next_close + 6
                        block = html[start:end]
                        blocks.append(block)
                        pos = end
                        break
                    i = next_close + 6
            else:
                if i >= len(html):
                    break
        return blocks

    def _parse_detail(self, html, vod_id):
        result = {
            'vod_id': vod_id,
            'vod_name': '',
            'vod_pic': '',
            'vod_content': '',
            'vod_actor': '',
            'vod_director': '',
            'vod_remarks': '',
            'vod_play_from': '',
            'vod_play_url': ''
        }

        # 标题
        title = re.search(r'<h3[^>]*class="[^"]*slide-info-title[^"]*"[^>]*>([^<]+)</h3>', html)
        if title:
            result['vod_name'] = title.group(1).strip()

        # 封面
        pic = re.search(r'<div[^>]*class="[^"]*detail-pic[^"]*"[^>]*>.*?<img[^>]*data-src="([^"]+)"', html, re.S)
        if not pic:
            pic = re.search(r'<img[^>]*class="[^"]*lazy[^"]*"[^>]*data-src="([^"]+)"[^>]*alt="海报图片"', html)
        if pic:
            result['vod_pic'] = pic.group(1)

        # 备注/状态
        remark = re.search(r'<strong[^>]*>备注\s*:\s*</strong>([^<]+)', html)
        if remark:
            result['vod_remarks'] = remark.group(1).strip()

        # 演员
        actor_section = re.search(r'<strong[^>]*>演员\s*:\s*</strong>(.*?)</div>', html, re.S)
        if actor_section:
            actor_html = actor_section.group(1)
            actors = re.findall(r'<a[^>]*>([^<]+)</a>', actor_html)
            if actors:
                result['vod_actor'] = ','.join([a.strip() for a in actors])

        # 导演
        director = ''
        director_section = re.search(r'<strong[^>]*>导演\s*:\s*</strong>(.*?)</div>', html, re.S)
        if director_section:
            director_html = director_section.group(1)
            directors = re.findall(r'<a[^>]*>([^<]+)</a>', director_html)
            if directors:
                director = ','.join([d.strip() for d in directors])
        if not director:
            director_match = re.search(r'<li><em[^>]*>导演：</em>\s*(.*?)\s*</li>', html, re.S)
            if director_match:
                d_html = director_match.group(1)
                d_names = re.findall(r'<a[^>]*>([^<]+)</a>', d_html)
                if d_names:
                    director = ','.join([d.strip() for d in d_names])
                else:
                    director = re.sub(r'<[^>]+>', '', d_html).strip()
        result['vod_director'] = director

        # 简介
        desc = re.search(r'<div[^>]*id="height_limit"[^>]*class="[^"]*text\s+cor3[^"]*"[^>]*>(.*?)</div>', html, re.S)
        if desc:
            result['vod_content'] = re.sub(r'<[^>]+>', '', desc.group(1)).strip()

        # ---------- 播放线路和剧集 ----------
        play_from = []
        play_url = []

        # 1. 提取线路名称
        line_names = []
        tab_match = re.search(r'<div[^>]*class="[^"]*anthology-tab[^"]*"[^>]*>(.*?)</div>', html, re.S)
        if tab_match:
            tab_html = tab_match.group(1)
            for a in re.finditer(r'<a[^>]*class="[^"]*swiper-slide[^"]*"[^>]*>(.*?)</a>', tab_html, re.S):
                inner = a.group(1).strip()
                inner = re.sub(r'<i[^>]*>.*?</i>', '', inner)
                inner = re.sub(r'<span[^>]*class="[^"]*badge[^"]*"[^>]*>.*?</span>', '', inner)
                inner = inner.replace('&nbsp;', ' ').strip()
                inner = re.sub(r'\s+', ' ', inner)
                if inner:
                    line_names.append(inner)

        # 2. 提取每个包含剧集的 block
        list_blocks = self._extract_div_blocks(html, 'anthology-list-box')

        # 3. 匹配线路与区块
        for idx, block in enumerate(list_blocks):
            if idx >= len(line_names):
                break
            episodes = self._extract_episodes_from_block(block)
            if episodes:
                play_from.append(line_names[idx])
                play_url.append('#'.join(episodes))

        # 4. 兜底
        if not play_from:
            all_episodes = []
            for a in re.finditer(r'<a[^>]*href="(/vplay/[\d\-]+\.html)"[^>]*>([^<]+)</a>', html):
                href = a.group(1)
                name = a.group(2).strip()
                vid = re.search(r'/vplay/(\d+-\d+-\d+)\.html', href)
                if vid and name:
                    all_episodes.append(f"{name}${vid.group(1)}")
            if all_episodes:
                play_from.append('默认线路')
                play_url.append('#'.join(all_episodes))

        result['vod_play_from'] = '$$$'.join(play_from)
        result['vod_play_url'] = '$$$'.join(play_url)
        return result

    def _extract_episodes_from_block(self, block_html):
        """提取剧集并反转（从小到大排序）"""
        episodes = []
        for a in re.finditer(r'<a[^>]*href="(/vplay/\d+-\d+-\d+\.html)"[^>]*>(?:<span>)?([^<]+)(?:</span>)?</a>', block_html):
            href = a.group(1)
            name = a.group(2).strip()
            vid = re.search(r'/vplay/(\d+-\d+-\d+)\.html', href)
            if vid and name:
                episodes.append(f"{name}${vid.group(1)}")
        episodes.reverse()
        return episodes

    # ---------- 播放地址提取 ----------
    def playerContent(self, flag, vid, vip_flags):
        if '$' in vid:
            _, play_id = vid.split('$', 1)
        else:
            play_id = vid
        url = f"{self.host}/vplay/{play_id}.html"
        html = self._request(url, cache_type='play')
        if not html:
            return {'jx': 0, 'parse': 0, 'url': ''}

        # player_aaaa Base64 解密
        player_match = re.search(r'var\s+player_aaaa\s*=\s*({[^;]+});', html)
        if player_match:
            try:
                data = json.loads(player_match.group(1))
                encrypted = data.get('url', '')
                if encrypted:
                    try:
                        decrypted = base64.b64decode(encrypted).decode('utf-8')
                        if decrypted.startswith('http'):
                            return {'jx': 0, 'parse': 0 if '.m3u8' in decrypted else 1, 'url': decrypted}
                    except:
                        pass
            except:
                pass

        # 备选变量
        for var_name in ['player_data', 'player_info', 'url', 'player']:
            pattern = rf'var\s+{var_name}\s*=\s*(\{{[\s\S]*?\}});'
            match = re.search(pattern, html)
            if match:
                try:
                    data = json.loads(match.group(1))
                    play_url = data.get('url', '')
                    if play_url and play_url.startswith('http'):
                        return {'jx': 0, 'parse': 0 if '.m3u8' in play_url else 1, 'url': play_url}
                except:
                    continue

        # iframe
        iframe = re.search(r'<iframe[^>]+src=["\']([^"\']+)["\']', html, re.I)
        if iframe:
            iframe_url = iframe.group(1)
            if iframe_url.startswith('http'):
                return {'jx': 0, 'parse': 1, 'url': iframe_url}

        return {'jx': 0, 'parse': 1, 'url': url}

    # ---------- 必需方法 ----------
    def getName(self):
        return "柯南影视"

    def isVideoFormat(self, url):
        return False

    def manualVideoCheck(self):
        pass

    def destroy(self):
        pass

    def localProxy(self, param):
        pass
#!/usr/bin/python
# -*- coding: utf-8 -*-
import json, re, urllib.parse
import requests
from lxml import etree
from base.spider import Spider

class Spider(Spider):
    def getName(self): return "追光影视"
    def init(self, extend=""):
        self.name = "追光影视"
        self.host = "https://www.4kmovie.top"
        self.limit = 24
        self.header = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36", "Referer": self.host + "/", "Accept-Language": "zh-CN,zh;q=0.9"}
        self.classes = [{"type_id": "20", "type_name": "电影"}, {"type_id": "37", "type_name": "连续剧"}, {"type_id": "43", "type_name": "动漫"}, {"type_id": "45", "type_name": "综艺"}, {"type_id": "47", "type_name": "B站"}]
        letters = [{"n": "全部", "v": ""}] + [{"n": x, "v": x} for x in list("ABCDEFGHIJKLMNOPQRSTUVWXYZ")] + [{"n": "0-9", "v": "0-9"}]
        self.sub_types = {"20": [("全部", "20"), ("动作片", "21"), ("喜剧片", "22"), ("爱情片", "23"), ("科幻片", "24"), ("恐怖片", "25"), ("剧情片", "26"), ("战争片", "27"), ("惊悚片", "28"), ("犯罪片", "29"), ("冒险篇", "30"), ("动画片", "31"), ("悬疑片", "32"), ("武侠片", "33"), ("奇幻片", "34"), ("纪录片", "35"), ("其他片", "36")], "37": [("全部", "37"), ("国产剧", "38"), ("港台剧", "39"), ("欧美剧", "40"), ("日韩剧", "41"), ("其他剧", "42")], "43": [("全部", "43"), ("动漫", "44")], "45": [("全部", "45"), ("综艺", "46")], "47": [("全部", "47"), ("番剧（B站）", "48"), ("国创（B站）", "49"), ("电影（B站）", "50"), ("电视剧（B站）", "51")]}
        self.filters = {}
        for c in self.classes:
            tid = c["type_id"]
            fs = []
            if tid in self.sub_types: fs.append({"key": "type", "name": "类型", "value": [{"n": n, "v": v} for n, v in self.sub_types[tid]]})
            fs += [{"key": "letter", "name": "字母", "value": letters}, {"key": "by", "name": "排序", "value": [{"n": "最新", "v": "time"}, {"n": "最热", "v": "hits"}, {"n": "评分", "v": "score"}]}]
            self.filters[tid] = fs

    def _get(self, url):
        try:
            r = requests.get(url, headers=self.header, timeout=15); r.encoding = r.apparent_encoding or "utf-8"; return r.text
        except Exception as e:
            print(f"[{self.name}] 错误: 请求失败 - {e}"); return ""

    def _fix(self, url): return "https:" + url if url and url.startswith("//") else self.host + url if url and url.startswith("/") else url or ""
    def _txt(self, arr): return re.sub(r"\s+", " ", "".join(arr).strip())

    def _vod_id(self, href):
        m = re.search(r"/vod(?:detail|play)/(\d+)(?:-|\.html)", href or "") or re.search(r"/index\.php/vod/(?:detail|play)/id/(\d+)", href or "")
        return m.group(1) if m else ""

    def _parse_list(self, text):
        html = etree.HTML(text or "")
        if html is None: return []
        items = html.xpath('//a[contains(@class,"module-poster-item") and (contains(@href,"/vodplay/") or contains(@href,"/voddetail/"))]') or html.xpath('//div[contains(@class,"module-items")]//a[(contains(@href,"/vodplay/") or contains(@href,"/voddetail/")) and .//img]') or html.xpath('//a[(contains(@href,"/vodplay/") or contains(@href,"/voddetail/")) and .//img]')
        print(f"[{self.name}] 列表选择器匹配到 {len(items)} 个视频")
        data, seen = [], set()
        for item in items:
            try:
                href = item.get("href", ""); vod_id = self._vod_id(href)
                if not vod_id or vod_id in seen: continue
                seen.add(vod_id)
                img = item.xpath('.//img')
                pic = self._fix((img[0].get("data-original") or img[0].get("data-src") or img[0].get("src") or "") if img else "")
                name = item.get("title") or self._txt(item.xpath('.//*[contains(@class,"module-poster-item-title")]/text()')) or (img[0].get("alt") if img else "") or self._txt(item.xpath('.//text()'))
                remark = self._txt(item.xpath('.//*[contains(@class,"module-item-note")]/text()'))
                data.append({"vod_id": vod_id, "vod_name": name, "vod_pic": pic, "vod_remarks": remark})
            except Exception as e:
                print(f"[{self.name}] 错误: 单条列表解析失败 - {e}"); continue
        return data

    def homeContent(self, filter):
        try: return {"class": self.classes, "filters": self.filters, "list": self._parse_list(self._get(self.host + "/"))}
        except Exception as e:
            print(f"[{self.name}] 错误: 首页内容失败 - {e}"); return {"class": self.classes, "filters": self.filters, "list": []}

    def _page_url(self, tid, pg, ext):
        tid = (ext or {}).get("type") or tid; by = (ext or {}).get("by", ""); letter = (ext or {}).get("letter", "")
        if letter: return f"{self.host}/vodshow/{tid}-----{letter}--{pg}---.html" if int(pg) > 1 else f"{self.host}/vodshow/{tid}-----{letter}------.html"
        if by: return f"{self.host}/vodshow/{tid}--{by}-----{pg}---.html" if int(pg) > 1 else f"{self.host}/vodshow/{tid}--{by}---------.html"
        return f"{self.host}/vodshow/{tid}--------{pg}---.html" if int(pg) > 1 else f"{self.host}/vodshow/{tid}-----------.html"

    def _page_count(self, text, default):
        try:
            nums = [int(x) for x in re.findall(r'/vodshow/\d+--------(\d+)---\.html', text or '')]
            return max(nums) if nums else default
        except: return default

    def categoryContent(self, tid, pg, filter, extend):
        try:
            pg = int(pg or 1); ext = extend or {}; url = self._page_url(tid, pg, ext)
            text = self._get(url); data = self._parse_list(text)
            if not data and pg == 1:
                text = self._get(f"{self.host}/vodtype/{ext.get('type') or tid}.html"); data = self._parse_list(text)
            pc = self._page_count(text, pg) if data else pg
            if pc < pg: pc = pg
            return {"list": data, "page": pg, "pagecount": pc, "limit": self.limit, "total": pc * self.limit}
        except Exception as e:
            print(f"[{self.name}] 错误: 分类爬取失败 - {e}"); return {"list": [], "page": int(pg or 1), "pagecount": int(pg or 1), "limit": self.limit, "total": 0}

    def detailContent(self, ids):
        result = {"list": []}
        for vod_id in (ids if isinstance(ids, list) else str(ids).split(","))[:1]:
            try:
                html = self._get(f"{self.host}/voddetail/{vod_id}.html") or self._get(f"{self.host}/vodplay/{vod_id}-1-1.html")
                tree = etree.HTML(html or "")
                if tree is None: continue
                name = self._txt(tree.xpath('//h1/text()'))
                pic = self._fix("".join(tree.xpath('(//img[contains(@class,"lazy") or contains(@class,"lazyload")]/@data-original | //img[contains(@class,"lazy") or contains(@class,"lazyload")]/@data-src | //*[contains(@class,"module-info-poster")]//img/@src)[1]')))
                content = self._txt(tree.xpath('//*[contains(@class,"module-info-introduction")]//text() | //*[contains(@class,"vod_content")]//text()'))
                tabs = tree.xpath('//div[contains(@class,"module-tab-item") and not(.//div[contains(@class,"module-tab-item")])]')
                lists = tree.xpath('//div[contains(@class,"module-list") and contains(@class,"tab-list")][.//a[contains(@href,"/vodplay/")]]')
                play_from, play_url = [], []
                for i, box in enumerate(lists):
                    source = (tabs[i].get("data-dropdown-value", "") if i < len(tabs) else "") or (self._txt(tabs[i].xpath('.//span/text() | ./text()')) if i < len(tabs) else "") or f"线路{i + 1}"
                    source = re.sub(r"\d+$", "", source).strip() or f"线路{i + 1}"
                    eps, seen_ep = [], set()
                    for a in box.xpath('.//a[contains(@class,"module-play-list-link") and contains(@href,"/vodplay/")]'):
                        title = self._txt(a.xpath('.//span/text() | .//text()')) or a.get("title", "") or f"第{len(eps) + 1}集"; href = self._fix(a.get("href", ""))
                        if href and href not in seen_ep:
                            seen_ep.add(href); eps.append(f"{title}${href}")
                    if eps: play_from.append(source); play_url.append("#".join(eps))
                if not play_url:
                    eps = [f"播放{idx + 1}${self._fix(a.get('href', ''))}" for idx, a in enumerate(tree.xpath('//a[contains(@class,"module-play-list-link") and contains(@href,"/vodplay/")]')) if a.get('href')]
                    if eps: play_from.append("默认线路"); play_url.append("#".join(eps))
                if not play_url:
                    play_from.append("默认线路"); play_url.append(f"播放${self.host}/vodplay/{vod_id}-1-1.html")
                print(f"[{self.name}] 详情页提取到 {len(play_from)} 个播放源")
                result["list"].append({"vod_id": vod_id, "vod_name": name, "vod_pic": pic, "vod_content": content, "vod_play_from": "$$$".join(play_from), "vod_play_url": "$$$".join(play_url)})
            except Exception as e:
                print(f"[{self.name}] 错误: 详情解析失败 - {e}"); continue
        return result

    def searchContent(self, key, quick, pg="1"):
        try:
            pg = int(pg or 1); q = urllib.parse.quote(key)
            data = self._parse_list(self._get(f"{self.host}/vodsearch/{q}----------{pg}---.html" if pg > 1 else f"{self.host}/vodsearch/{q}-------------.html"))
            print(f"[{self.name}] 搜索结果数量 {len(data)}")
            return {"list": data, "page": pg, "pagecount": pg + 1 if data else pg, "limit": self.limit, "total": 999 if data else 0}
        except Exception as e:
            print(f"[{self.name}] 错误: 搜索失败 - {e}"); return {"list": [], "page": int(pg or 1), "pagecount": 1}

    def playerContent(self, flag, id, vipFlags):
        try:
            url = self._fix(id)
            if re.search(r"\.(m3u8|mp4|flv)(\?|$)", url): return {"parse": 0, "playUrl": "", "url": url, "header": json.dumps(self.header)}
            print(f"[{self.name}] 播放解析: {flag} -> {url[:50]}...")
            return {"parse": 1, "playUrl": "", "url": url, "header": self.header}
        except Exception as e:
            print(f"[{self.name}] 错误: 播放解析失败 - {e}"); return {"parse": 1, "playUrl": "", "url": id, "header": self.header}

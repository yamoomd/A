# -*- coding: utf-8 -*-
"""
搜索处理模块
处理"其他"类别的联网搜索
"""

import requests
import json
from typing import Dict, Any, Optional
import re


class SearchHandler:
    """搜索处理器"""
    
    def __init__(self):
        self.search_engines = {
            "baidu": self.baidu_search,
            "bing": self.bing_search,
            "google": self.google_search
        }
        
        # 可以在这里配置API密钥
        self.api_keys = {
            "bing": None,  # 设置你的Bing搜索API密钥
            "google": None,  # 设置你的Google搜索API密钥
        }
    
    def handle_other_query(self, query: str) -> Dict[str, Any]:
        """处理其他类别的查询"""
        try:
            # 尝试搜索
            search_results = self.search(query)
            
            # 生成回答
            answer = self.generate_answer(query, search_results)
            
            return {
                "type": "其他",
                "query": query,
                "search_results": search_results,
                "answer": answer,
                "success": True
            }
            
        except Exception as e:
            return {
                "type": "其他", 
                "query": query,
                "error": str(e),
                "answer": "抱歉，我无法找到相关信息。",
                "success": False
            }
    
    def search(self, query: str, engine: str = "baidu") -> Dict[str, Any]:
        """执行搜索"""
        if engine in self.search_engines:
            return self.search_engines[engine](query)
        else:
            return self.baidu_search(query)
    
    def baidu_search(self, query: str) -> Dict[str, Any]:
        """百度搜索（爬虫方式）"""
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
            }
            
            # 百度搜索URL
            url = f"https://www.baidu.com/s?wd={query}"
            
            response = requests.get(url, headers=headers, timeout=10)
            response.raise_for_status()
            
            # 简单提取搜索结果（实际项目中可能需要更复杂的解析）
            results = self.parse_baidu_results(response.text)
            
            return {
                "engine": "baidu",
                "query": query,
                "results": results,
                "count": len(results)
            }
            
        except Exception as e:
            return {
                "engine": "baidu",
                "query": query,
                "error": str(e),
                "results": [],
                "count": 0
            }
    
    def bing_search(self, query: str) -> Dict[str, Any]:
        """Bing搜索API"""
        if not self.api_keys.get("bing"):
            return self.baidu_search(query)  # 降级到百度搜索
        
        try:
            subscription_key = self.api_keys["bing"]
            search_url = "https://api.bing.microsoft.com/v7.0/search"
            
            headers = {"Ocp-Apim-Subscription-Key": subscription_key}
            params = {"q": query, "textDecorations": True, "textFormat": "HTML"}
            
            response = requests.get(search_url, headers=headers, params=params, timeout=10)
            response.raise_for_status()
            
            search_results = response.json()
            
            results = []
            if "webPages" in search_results:
                for result in search_results["webPages"]["value"][:5]:
                    results.append({
                        "title": result.get("name", ""),
                        "url": result.get("url", ""),
                        "snippet": result.get("snippet", "")
                    })
            
            return {
                "engine": "bing",
                "query": query,
                "results": results,
                "count": len(results)
            }
            
        except Exception as e:
            return self.baidu_search(query)  # 降级到百度搜索
    
    def google_search(self, query: str) -> Dict[str, Any]:
        """Google搜索API"""
        if not self.api_keys.get("google"):
            return self.baidu_search(query)  # 降级到百度搜索
        
        try:
            api_key = self.api_keys["google"]
            search_engine_id = "your_search_engine_id"  # 需要配置
            
            url = f"https://www.googleapis.com/customsearch/v1"
            params = {
                "key": api_key,
                "cx": search_engine_id,
                "q": query
            }
            
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            
            search_results = response.json()
            
            results = []
            if "items" in search_results:
                for result in search_results["items"][:5]:
                    results.append({
                        "title": result.get("title", ""),
                        "url": result.get("link", ""),
                        "snippet": result.get("snippet", "")
                    })
            
            return {
                "engine": "google",
                "query": query,
                "results": results,
                "count": len(results)
            }
            
        except Exception as e:
            return self.baidu_search(query)  # 降级到百度搜索
    
    def parse_baidu_results(self, html: str) -> list:
        """解析百度搜索结果"""
        results = []
        
        # 简单的正则表达式提取（实际项目中建议使用BeautifulSoup）
        title_pattern = r'<h3[^>]*>.*?<a[^>]*href="([^"]*)"[^>]*>([^<]*)</a>.*?</h3>'
        snippet_pattern = r'<span class="content-right_[^"]*">([^<]*)</span>'
        
        titles = re.findall(title_pattern, html, re.DOTALL)
        snippets = re.findall(snippet_pattern, html)
        
        for i, (url, title) in enumerate(titles[:5]):
            snippet = snippets[i] if i < len(snippets) else ""
            results.append({
                "title": title.strip(),
                "url": url,
                "snippet": snippet.strip()
            })
        
        return results
    
    def generate_answer(self, query: str, search_results: Dict[str, Any]) -> str:
        """基于搜索结果生成回答"""
        if not search_results.get("results"):
            return "抱歉，我没有找到相关信息。"
        
        # 组合搜索结果
        snippets = []
        for result in search_results["results"][:3]:
            if result.get("snippet"):
                snippets.append(result["snippet"])
        
        if not snippets:
            return "抱歉，我没有找到详细信息。"
        
        # 简单的回答生成
        combined_text = " ".join(snippets)
        
        # 根据查询类型生成不同的回答
        if "天气" in query:
            return f"根据搜索结果：{combined_text}"
        elif "股票" in query or "行情" in query:
            return f"关于股票行情：{combined_text}"
        elif "新闻" in query or "最新" in query:
            return f"最新信息：{combined_text}"
        else:
            return f"根据搜索，{combined_text}"
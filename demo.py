# -*- coding: utf-8 -*-
"""
中文字词库系统演示程序
不依赖复杂模型的简化版本
"""

import re
import json
from typing import Dict, Any, List
from config_simple import INTENT_TYPES, SLOT_SCHEMA, STRUCTURE_TYPES, OTHER_KEYWORDS


class SimpleIntentClassifier:
    """简化的意图识别器"""
    
    def __init__(self):
        # 意图关键词映射
        self.intent_keywords = {
            "读音": ["读", "念", "拼音", "音"],
            "书写": ["写", "笔顺", "笔画", "书写"],
            "查字": ["加", "减", "笔", "左边", "右边", "上", "下", "组成", "什么字"],
            "查词": ["词", "成语", "字是什么"],
            "组词": ["组词", "造句", "搭配"],
            "释义": ["意思", "含义", "解释", "定义", "释义"],
            "分字": ["左边", "右边", "上", "下", "分解", "部件", "偏旁"]
        }
    
    def classify(self, text: str) -> Dict[str, Any]:
        """分类用户输入"""
        print(f"正在分析查询: {text}")
        
        # 检查是否包含其他类别关键词
        for keyword in OTHER_KEYWORDS:
            if keyword in text:
                return {
                    "query": text,
                    "final_intent": "其他",
                    "is_other": True,
                    "confidence": 0.9
                }
        
        # 检查字词库相关意图
        for intent, keywords in self.intent_keywords.items():
            for keyword in keywords:
                if keyword in text:
                    return {
                        "query": text,
                        "final_intent": intent,
                        "is_other": False,
                        "confidence": 0.8
                    }
        
        # 默认为查字意图
        return {
            "query": text,
            "final_intent": "查字",
            "is_other": False,
            "confidence": 0.5
        }


class SimpleSlotExtractor:
    """简化的槽位提取器"""
    
    def __init__(self):
        # 中文数字映射
        self.chinese_numbers = {
            '一': 1, '二': 2, '三': 3, '四': 4, '五': 5,
            '六': 6, '七': 7, '八': 8, '九': 9, '十': 10
        }
        
        # 方向词映射
        self.direction_mapping = {
            '左边': '左', '右边': '右', '上边': '上', '下边': '下',
            '左侧': '左', '右侧': '右', '上面': '上', '下面': '下',
            '左': '左', '右': '右', '上': '上', '下': '下'
        }
    
    def extract_slots(self, text: str, intent: str) -> Dict[str, Any]:
        """提取槽位信息"""
        if intent == "其他":
            return {"type": intent, "slot": {}}
        
        print(f"正在提取 '{intent}' 意图的槽位...")
        
        # 检查是否为复合意图
        if self.is_complex_query(text):
            return self.handle_complex_intent(text)
        
        # 根据意图类型提取槽位
        slots = self.extract_slots_by_intent(text, intent)
        
        return {
            "type": intent,
            "slot": slots
        }
    
    def is_complex_query(self, text: str) -> bool:
        """检测是否为复合查询"""
        patterns = [
            r'(.+)的(左边|右边|上|下).+(加上|和).+的(左边|右边|上|下).+是什么字',
            r'(.+)字的(左边|右边|上|下).+(加上|和).+字的(左边|右边|上|下).+什么字'
        ]
        
        for pattern in patterns:
            if re.search(pattern, text):
                return True
        return False
    
    def handle_complex_intent(self, text: str) -> Dict[str, Any]:
        """处理复合意图"""
        # 简化处理，分解查询
        queries = [
            "第一步：提取第一个字的部件",
            "第二步：提取第二个字的部件", 
            "第三步：组合部件查找新字"
        ]
        
        return {
            "type": "复合意图",
            "slot": {
                "sub_queries": queries,
                "requires_decomposition": True,
                "original_query": text
            }
        }
    
    def extract_slots_by_intent(self, text: str, intent: str) -> Dict[str, Any]:
        """根据意图类型提取槽位"""
        slots = {}
        
        # 提取汉字
        chars = re.findall(r'[\u4e00-\u9fff]', text)
        
        if intent in ["读音", "书写", "组词", "释义"]:
            slots = self.extract_single_char_slots(text, chars)
        elif intent == "查字":
            slots = self.extract_char_query_slots(text, chars)
        elif intent == "查词":
            slots = self.extract_word_query_slots(text, chars)
        elif intent == "分字":
            slots = self.extract_decomposition_slots(text, chars)
        
        return slots
    
    def extract_single_char_slots(self, text: str, chars: List[str]) -> Dict[str, Any]:
        """提取单字相关槽位"""
        slots = {}
        
        # 查找目标字符
        char_patterns = [
            r'(\w)字',
            r'(\w).*?怎么',
            r'(\w).*?什么'
        ]
        
        for pattern in char_patterns:
            match = re.search(pattern, text)
            if match:
                slots["target_char"] = [match.group(1)]
                break
        
        if not slots.get("target_char") and chars:
            slots["target_char"] = [chars[0]]
        
        return slots
    
    def extract_char_query_slots(self, text: str, chars: List[str]) -> Dict[str, Any]:
        """提取查字相关槽位"""
        slots = {}
        
        # 提取笔画数变化
        stroke_patterns = [
            r'(\w)字?.*?加(\w+)笔',
            r'(\w)字?.*?减(\w+)笔'
        ]
        
        for pattern in stroke_patterns:
            match = re.search(pattern, text)
            if match:
                char = match.group(1)
                stroke_text = match.group(2)
                
                slots["target_char"] = [char]
                
                # 转换笔画数
                stroke_num = self.convert_number(stroke_text)
                if "减" in text:
                    stroke_num = -stroke_num
                slots["strokes"] = stroke_num
                break
        
        # 提取结构和组件信息
        if "左边" in text and "右边" in text:
            # 左右结构
            left_match = re.search(r'左边.*?(\w+)', text)
            right_match = re.search(r'右边.*?(\w+)', text)
            
            if left_match and right_match:
                slots["structure_type"] = "left_right"
                slots["components"] = [left_match.group(1), right_match.group(1)]
                slots["component_count"] = 2
        
        elif "三" in text and ("组成" in text or chars):
            # 三字结构
            if chars:
                component = chars[0] if chars else "羊"
                slots["structure_type"] = "pin"
                slots["components"] = [component] * 3
                slots["component_count"] = 3
        
        return slots
    
    def extract_word_query_slots(self, text: str, chars: List[str]) -> Dict[str, Any]:
        """提取查词相关槽位"""
        slots = {}
        
        # 提取目标词组
        phrase_patterns = [
            r'([\u4e00-\u9fff]{2,}).*?是什么',
            r'([\u4e00-\u9fff]{2,}).*?的.*?是什么'
        ]
        
        for pattern in phrase_patterns:
            match = re.search(pattern, text)
            if match:
                phrase = match.group(1)
                slots["target_phrase"] = [phrase]
                break
        
        return slots
    
    def extract_decomposition_slots(self, text: str, chars: List[str]) -> Dict[str, Any]:
        """提取分字相关槽位"""
        slots = {}
        
        # 查找目标字符和位置
        patterns = [
            r'(\w)字?的(左边|右边|上|下)',
            r'(\w).*?(左边|右边|上|下)'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text)
            if match:
                char = match.group(1)
                position = match.group(2)
                
                slots["target_char"] = [char]
                slots["target_component"] = [self.direction_mapping.get(position, position)]
                break
        
        return slots
    
    def convert_number(self, text: str) -> int:
        """转换中文数字为阿拉伯数字"""
        for chinese, arabic in self.chinese_numbers.items():
            if chinese in text:
                return arabic
        
        # 尝试直接提取数字
        numbers = re.findall(r'\d+', text)
        if numbers:
            return int(numbers[0])
        
        return 1  # 默认值


class SimpleSearchHandler:
    """简化的搜索处理器"""
    
    def handle_other_query(self, query: str) -> Dict[str, Any]:
        """处理其他类别的查询"""
        print(f"正在处理搜索查询: {query}")
        
        # 模拟搜索结果
        mock_answers = {
            "天气": "抱歉，我无法获取实时天气信息。建议您查看天气预报APP或网站。",
            "股票": "抱歉，我无法获取实时股票信息。建议您查看财经网站或APP。",
            "AI": "AI技术正在快速发展，包括大语言模型、计算机视觉等领域都有重要进展。",
            "搜索": "这是一个搜索相关的查询，我会尝试为您提供相关信息。"
        }
        
        # 根据关键词生成回答
        answer = "抱歉，我无法处理这个查询。"
        for keyword, response in mock_answers.items():
            if keyword in query:
                answer = response
                break
        
        return {
            "type": "其他",
            "query": query,
            "answer": answer,
            "success": True
        }


class SimpleChineseCharacterLibrary:
    """简化的中文字词库主类"""
    
    def __init__(self):
        print("正在初始化中文字词库演示系统...")
        
        self.intent_classifier = SimpleIntentClassifier()
        self.slot_extractor = SimpleSlotExtractor()
        self.search_handler = SimpleSearchHandler()
        
        print("系统初始化完成！")
    
    def process_query(self, query: str) -> Dict[str, Any]:
        """处理用户查询"""
        print(f"\n{'='*50}")
        print(f"处理查询: {query}")
        print('='*50)
        
        # 1. 意图识别
        intent_result = self.intent_classifier.classify(query)
        print(f"✓ 意图识别: {intent_result['final_intent']} (置信度: {intent_result['confidence']})")
        
        # 2. 处理不同类型的意图
        if intent_result["is_other"]:
            # 其他类别 - 搜索
            result = self.search_handler.handle_other_query(query)
            print(f"✓ 搜索处理完成")
        else:
            # 字词库相关意图 - 抽槽处理
            slot_result = self.slot_extractor.extract_slots(
                query, 
                intent_result["final_intent"]
            )
            print(f"✓ 槽位提取完成")
            
            result = {
                "intent_info": intent_result,
                "slot_info": slot_result,
                "query": query
            }
        
        return result
    
    def format_output(self, result: Dict[str, Any]) -> str:
        """格式化输出结果"""
        if "answer" in result:
            # 其他类别的搜索结果
            return f"🔍 搜索回答: {result['answer']}"
        else:
            # 字词库相关的结构化结果
            output = f"📝 查询分析结果:\n"
            output += f"   查询: {result['query']}\n"
            output += f"   意图: {result['slot_info']['type']}\n"
            output += f"   槽位信息: {json.dumps(result['slot_info']['slot'], ensure_ascii=False, indent=6)}\n"
            
            # 根据意图类型提供相应的提示
            intent_type = result['slot_info']['type']
            if intent_type == "复合意图":
                output += "\n💡 处理建议: 这是一个复合查询，需要分步骤处理："
                for i, sub_query in enumerate(result['slot_info']['slot']['sub_queries'], 1):
                    output += f"\n     {i}. {sub_query}"
            else:
                output += f"\n💡 处理建议: 这是一个'{intent_type}'类型的查询，请根据槽位信息进行相应的字词库操作。"
            
            return output


def demo():
    """演示程序"""
    print("🎉 欢迎使用中文字词库意图识别和抽槽系统演示！")
    print("支持的意图类型：读音、书写、查字、查词、组词、释义、分字")
    print("也支持其他类别查询的搜索功能\n")
    
    # 初始化系统
    system = SimpleChineseCharacterLibrary()
    
    # 测试示例
    test_queries = [
        "焜字怎么写？",
        "毛泽东的字是什么？", 
        "艮字加三笔是什么字？",
        "良字减一笔是什么字？",
        "左边一个木，右边一个黄是什么字？",
        "三只羊组成的是什么字？",
        "伟字的左边是什么？",
        "伟字的左边加上沐的右边是什么字？",
        "合肥明天会下雨吗？",
        "帮我搜一下最新的AI进展"
    ]
    
    print(f"\n🔬 运行 {len(test_queries)} 个测试示例:")
    
    for i, query in enumerate(test_queries, 1):
        print(f"\n【示例 {i}】")
        try:
            result = system.process_query(query)
            formatted_output = system.format_output(result)
            print(formatted_output)
        except Exception as e:
            print(f"❌ 处理查询时出错: {e}")
        
        print("-" * 50)
    
    print("\n✅ 演示完成！")
    print("\n📖 说明:")
    print("   - 这是一个简化版演示，展示了系统的核心功能")
    print("   - 完整版本需要安装相应的机器学习库（FastText, Transformers等）")
    print("   - 实际部署时可以根据需要配置GPU加速和API密钥")


if __name__ == "__main__":
    demo()
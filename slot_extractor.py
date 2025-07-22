# -*- coding: utf-8 -*-
"""
抽槽模块
使用Qwen模型进行槽位提取
"""

import re
import json
from typing import Dict, List, Any, Optional
from transformers import AutoTokenizer, AutoModelForCausalLM
import torch
from config import SLOT_SCHEMA, STRUCTURE_TYPES, MODEL_CONFIG, INTENT_TYPES


class SlotExtractor:
    """槽位提取器"""
    
    def __init__(self):
        self.tokenizer = None
        self.model = None
        self.load_model()
        
        # 中文数字映射
        self.chinese_numbers = {
            '一': 1, '二': 2, '三': 3, '四': 4, '五': 5,
            '六': 6, '七': 7, '八': 8, '九': 9, '十': 10,
            '1': 1, '2': 2, '3': 3, '4': 4, '5': 5,
            '6': 6, '7': 7, '8': 8, '9': 9, '0': 0
        }
        
        # 方向词映射
        self.direction_mapping = {
            '左边': '左', '右边': '右', '上边': '上', '下边': '下',
            '左侧': '左', '右侧': '右', '上面': '上', '下面': '下',
            '左': '左', '右': '右', '上': '上', '下': '下'
        }
        
        # 偏旁部首映射
        self.radical_mapping = {
            '提手旁': '扌', '单人旁': '亻', '三点水': '氵',
            '口字旁': '口', '木字旁': '木', '火字旁': '火',
            '土字旁': '土', '草字头': '艹', '竹字头': '⺮',
            '宝盖头': '宀', '人字头': '人', '立字旁': '立'
        }
    
    def load_model(self):
        """加载Qwen模型"""
        try:
            model_name = MODEL_CONFIG["qwen_model_name"]
            self.tokenizer = AutoTokenizer.from_pretrained(model_name)
            self.model = AutoModelForCausalLM.from_pretrained(
                model_name,
                torch_dtype=torch.float16,
                device_map="auto"
            )
        except Exception as e:
            print(f"加载Qwen模型失败: {e}")
            print("将使用规则基础的抽槽方法")
    
    def extract_slots(self, text: str, intent: str) -> Dict[str, Any]:
        """提取槽位信息"""
        if intent == "其他":
            return {"type": intent, "slot": {}}
        
        # 检查是否为复合意图
        complex_queries = self.detect_complex_intent(text)
        if complex_queries:
            return self.handle_complex_intent(complex_queries)
        
        # 使用LLM进行抽槽
        if self.model and self.tokenizer:
            slots = self.llm_extract_slots(text, intent)
        else:
            slots = self.rule_based_extract_slots(text, intent)
        
        return {
            "type": intent,
            "slot": slots
        }
    
    def detect_complex_intent(self, text: str) -> List[str]:
        """检测复合意图"""
        # 检测类似 "伟字的左边加上沐的右边是什么字？" 的复合查询
        patterns = [
            r'(.+)的(左边|右边|上|下).+(加上|和).+的(左边|右边|上|下).+是什么字',
            r'(.+)字的(左边|右边|上|下).+(加上|和).+字的(左边|右边|上|下).+什么字'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text)
            if match:
                return self.decompose_complex_query(text, match)
        
        return []
    
    def decompose_complex_query(self, text: str, match) -> List[str]:
        """分解复合查询"""
        # 示例: "伟字的左边加上沐的右边是什么字？"
        # 分解为三个子查询
        
        queries = []
        
        # 从正则匹配中提取信息
        groups = match.groups()
        if len(groups) >= 4:
            char1, pos1, _, pos2 = groups[:4]
            
            # 尝试提取第二个字符
            remaining_text = text[match.start():match.end()]
            char2_match = re.search(r'(.+)的' + pos2, remaining_text)
            if char2_match:
                char2 = char2_match.group(1).replace(char1 + '的' + pos1 + '加上', '').replace('和', '')
            else:
                char2 = "未知"
            
            # 生成子查询
            queries.append(f"{char1}字的{pos1}是什么？")
            queries.append(f"{char2}字的{pos2}是什么？") 
            queries.append(f"{pos1}是component1，{pos2}是component2的是什么字？")
        
        return queries
    
    def handle_complex_intent(self, queries: List[str]) -> Dict[str, Any]:
        """处理复合意图"""
        return {
            "type": "复合意图",
            "slot": {
                "sub_queries": queries,
                "requires_decomposition": True
            }
        }
    
    def llm_extract_slots(self, text: str, intent: str) -> Dict[str, Any]:
        """使用LLM提取槽位"""
        
        # 构建提示词
        slot_examples = self.get_slot_examples_for_intent(intent)
        
        prompt = f"""
请从用户问题中提取槽位信息，返回JSON格式。

意图类别: {intent}

可用槽位:
{json.dumps(SLOT_SCHEMA, ensure_ascii=False, indent=2)}

示例:
{slot_examples}

用户问题: {text}

请提取槽位信息，只返回JSON格式的槽位数据:
"""
        
        try:
            inputs = self.tokenizer(prompt, return_tensors="pt").to(self.model.device)
            
            with torch.no_grad():
                outputs = self.model.generate(
                    **inputs,
                    max_new_tokens=200,
                    temperature=0.1,
                    do_sample=False
                )
            
            response = self.tokenizer.decode(outputs[0][inputs.input_ids.shape[1]:], skip_special_tokens=True)
            
            # 尝试解析JSON
            try:
                slots = json.loads(response.strip())
                return self.validate_and_clean_slots(slots)
            except json.JSONDecodeError:
                # 如果JSON解析失败，使用规则方法
                return self.rule_based_extract_slots(text, intent)
                
        except Exception as e:
            print(f"LLM抽槽出错: {e}")
            return self.rule_based_extract_slots(text, intent)
    
    def get_slot_examples_for_intent(self, intent: str) -> str:
        """获取意图对应的槽位示例"""
        examples = {
            "读音": """
示例1: "焜字怎么读？"
{"target_char": ["焜"]}
""",
            "书写": """
示例1: "焜字怎么写？"
{"target_char": ["焜"]}
""",
            "查字": """
示例1: "艮字加三笔是什么字？"
{"target_char": ["艮"], "strokes": 3}

示例2: "左边一个木，右边一个黄是什么字？"
{"structure_type": "left_right", "component_count": 2, "components": ["木", "黄"]}

示例3: "三只羊组成的是什么字？"
{"structure_type": "pin", "component_count": 3, "components": ["羊", "羊", "羊"]}
""",
            "查词": """
示例1: "毛泽东的字是什么？"
{"target_phrase": ["毛泽东"]}
""",
            "组词": """
示例1: "用好字组词"
{"target_char": ["好"]}
""",
            "释义": """
示例1: "好字是什么意思？"
{"target_char": ["好"]}
""",
            "分字": """
示例1: "伟字的左边是什么？"
{"target_char": ["伟"], "target_component": ["左"]}
"""
        }
        
        return examples.get(intent, "")
    
    def rule_based_extract_slots(self, text: str, intent: str) -> Dict[str, Any]:
        """基于规则的槽位提取"""
        slots = {}
        
        # 提取汉字
        chars = re.findall(r'[\u4e00-\u9fff]', text)
        
        if intent == "读音":
            slots = self.extract_reading_slots(text, chars)
        elif intent == "书写":
            slots = self.extract_writing_slots(text, chars)
        elif intent == "查字":
            slots = self.extract_char_query_slots(text, chars)
        elif intent == "查词":
            slots = self.extract_word_query_slots(text, chars)
        elif intent == "组词":
            slots = self.extract_word_formation_slots(text, chars)
        elif intent == "释义":
            slots = self.extract_meaning_slots(text, chars)
        elif intent == "分字":
            slots = self.extract_decomposition_slots(text, chars)
        
        return slots
    
    def extract_reading_slots(self, text: str, chars: List[str]) -> Dict[str, Any]:
        """提取读音相关槽位"""
        slots = {}
        
        # 查找目标字符
        char_patterns = [
            r'(\w)字.*?读',
            r'(\w).*?读音',
            r'(\w).*?怎么念',
            r'(\w).*?拼音'
        ]
        
        for pattern in char_patterns:
            match = re.search(pattern, text)
            if match:
                slots["target_char"] = [match.group(1)]
                break
        
        if not slots.get("target_char") and chars:
            slots["target_char"] = [chars[0]]
        
        return slots
    
    def extract_writing_slots(self, text: str, chars: List[str]) -> Dict[str, Any]:
        """提取书写相关槽位"""
        slots = {}
        
        # 查找目标字符
        char_patterns = [
            r'(\w)字.*?写',
            r'(\w).*?笔顺',
            r'(\w).*?书写'
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
            r'(\w)字?.*?减(\w+)笔',
            r'(\w)字?.*?加上(\w+)笔',
            r'(\w)字?.*?去掉(\w+)笔'
        ]
        
        for pattern in stroke_patterns:
            match = re.search(pattern, text)
            if match:
                char = match.group(1)
                stroke_text = match.group(2)
                
                slots["target_char"] = [char]
                
                # 转换笔画数
                stroke_num = self.convert_number(stroke_text)
                if "减" in text or "去掉" in text:
                    stroke_num = -stroke_num
                slots["strokes"] = stroke_num
                break
        
        # 提取结构和组件信息
        structure_patterns = [
            r'左边.*?(\w+).*?右边.*?(\w+)',
            r'上面.*?(\w+).*?下面.*?(\w+)',
            r'(\w+).*?(\w+).*?组成',
            r'三.*?(\w+).*?组成'
        ]
        
        for pattern in structure_patterns:
            match = re.search(pattern, text)
            if match:
                components = list(match.groups())
                
                # 判断结构类型
                if "左边" in text and "右边" in text:
                    slots["structure_type"] = "left_right"
                elif "上面" in text and "下面" in text:
                    slots["structure_type"] = "up_bottom"
                elif "三" in text and "组成" in text:
                    slots["structure_type"] = "pin"
                    # 对于三字结构，重复组件
                    if len(components) == 1:
                        components = [components[0]] * 3
                else:
                    slots["structure_type"] = "all"
                
                slots["components"] = components
                slots["component_count"] = len(components)
                break
        
        return slots
    
    def extract_word_query_slots(self, text: str, chars: List[str]) -> Dict[str, Any]:
        """提取查词相关槽位"""
        slots = {}
        
        # 提取目标词组
        phrase_patterns = [
            r'([\u4e00-\u9fff]+).*?是什么',
            r'([\u4e00-\u9fff]+).*?的.*?是什么',
            r'([\u4e00-\u9fff]{2,}).*?意思'
        ]
        
        for pattern in phrase_patterns:
            match = re.search(pattern, text)
            if match:
                phrase = match.group(1)
                if len(phrase) > 1:  # 确保是词组而不是单字
                    slots["target_phrase"] = [phrase]
                    break
        
        return slots
    
    def extract_word_formation_slots(self, text: str, chars: List[str]) -> Dict[str, Any]:
        """提取组词相关槽位"""
        slots = {}
        
        # 查找目标字符
        char_patterns = [
            r'用(\w).*?组词',
            r'(\w)字.*?组词',
            r'(\w).*?组词'
        ]
        
        for pattern in char_patterns:
            match = re.search(pattern, text)
            if match:
                slots["target_char"] = [match.group(1)]
                break
        
        if not slots.get("target_char") and chars:
            slots["target_char"] = [chars[0]]
        
        return slots
    
    def extract_meaning_slots(self, text: str, chars: List[str]) -> Dict[str, Any]:
        """提取释义相关槽位"""
        slots = {}
        
        # 查找目标字符或词组
        patterns = [
            r'([\u4e00-\u9fff]+).*?意思',
            r'([\u4e00-\u9fff]+).*?含义',
            r'([\u4e00-\u9fff]+).*?解释'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text)
            if match:
                target = match.group(1)
                if len(target) == 1:
                    slots["target_char"] = [target]
                else:
                    slots["target_phrase"] = [target]
                break
        
        return slots
    
    def extract_decomposition_slots(self, text: str, chars: List[str]) -> Dict[str, Any]:
        """提取分字相关槽位"""
        slots = {}
        
        # 查找目标字符和位置
        patterns = [
            r'(\w)字?的(左边|右边|上|下|左|右)',
            r'(\w).*?(左边|右边|上|下|左|右)',
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
    
    def validate_and_clean_slots(self, slots: Dict[str, Any]) -> Dict[str, Any]:
        """验证和清理槽位数据"""
        cleaned_slots = {}
        
        for slot_name, value in slots.items():
            if slot_name in SLOT_SCHEMA:
                slot_def = SLOT_SCHEMA[slot_name]
                
                # 类型验证和转换
                if slot_def["type"] == "list" and not isinstance(value, list):
                    if isinstance(value, str):
                        cleaned_slots[slot_name] = [value]
                    else:
                        continue
                elif slot_def["type"] == "int":
                    try:
                        cleaned_slots[slot_name] = int(value)
                    except (ValueError, TypeError):
                        continue
                elif slot_def["type"] == "str":
                    cleaned_slots[slot_name] = str(value)
                else:
                    cleaned_slots[slot_name] = value
        
        return cleaned_slots
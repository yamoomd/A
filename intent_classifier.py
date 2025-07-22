# -*- coding: utf-8 -*-
"""
意图识别模块
包含FastText快速分类和Qwen二次检验
"""

import fasttext
import jieba
import re
from typing import Dict, List, Tuple
from transformers import AutoTokenizer, AutoModelForCausalLM
import torch
import json
from config import INTENT_TYPES, OTHER_KEYWORDS, MODEL_CONFIG


class FastTextClassifier:
    """FastText快速分类器"""
    
    def __init__(self, model_path: str = None):
        self.model_path = model_path or MODEL_CONFIG["fasttext_model_path"]
        self.model = None
        self.load_model()
    
    def load_model(self):
        """加载或训练FastText模型"""
        try:
            self.model = fasttext.load_model(self.model_path)
        except:
            print("FastText模型未找到，将创建训练数据并训练模型")
            self.create_training_data()
            self.train_model()
    
    def create_training_data(self):
        """创建训练数据"""
        training_data = []
        
        # 字词库相关数据
        intent_examples = {
            "读音": [
                "焜字怎么读", "这个字的读音是什么", "帮我读一下这个字",
                "拼音是什么", "怎么念", "读音"
            ],
            "书写": [
                "焜字怎么写", "这个字怎么写", "写法",
                "笔顺", "笔画顺序", "如何书写"
            ],
            "查字": [
                "艮字加三笔是什么字", "良字减一笔是什么字", "左边木右边黄是什么字",
                "三只羊组成什么字", "查字", "什么字"
            ],
            "查词": [
                "毛泽东的字是什么", "这个词的意思", "查词",
                "词语", "成语"
            ],
            "组词": [
                "用这个字组词", "组词", "造句", "词语搭配"
            ],
            "释义": [
                "这个字什么意思", "解释", "含义", "定义", "释义"
            ],
            "分字": [
                "伟字的左边是什么", "分解这个字", "部件", "偏旁部首"
            ]
        }
        
        # 其他类别数据
        other_examples = [
            "合肥明天会下雨吗", "帮我搜一下最新的AI进展", "今天A股行情如何",
            "天气预报", "新闻资讯", "股票价格", "搜索信息",
            "政治新闻", "经济形势", "体育赛事", "娱乐八卦"
        ]
        
        # 生成训练数据
        for intent, examples in intent_examples.items():
            for example in examples:
                training_data.append(f"__label__{intent} {example}")
        
        for example in other_examples:
            training_data.append(f"__label__其他 {example}")
        
        # 保存训练数据
        with open("train_data.txt", "w", encoding="utf-8") as f:
            for line in training_data:
                f.write(line + "\n")
    
    def train_model(self):
        """训练FastText模型"""
        self.model = fasttext.train_supervised(
            input="train_data.txt",
            lr=0.1,
            epoch=100,
            wordNgrams=2,
            dim=100
        )
        # 保存模型
        import os
        os.makedirs("models", exist_ok=True)
        self.model.save_model(self.model_path)
    
    def predict(self, text: str) -> Tuple[str, float]:
        """预测意图"""
        if not self.model:
            return "其他", 0.0
        
        # 预处理文本
        text = self.preprocess_text(text)
        
        # 预测
        labels, probabilities = self.model.predict(text, k=1)
        
        # 提取结果
        label = labels[0].replace("__label__", "")
        probability = probabilities[0]
        
        return label, probability
    
    def preprocess_text(self, text: str) -> str:
        """文本预处理"""
        # 去除标点符号
        text = re.sub(r'[^\w\s]', '', text)
        # 分词
        words = jieba.cut(text)
        return " ".join(words)


class QwenVerifier:
    """Qwen二次检验器"""
    
    def __init__(self):
        self.tokenizer = None
        self.model = None
        self.load_model()
    
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
            print("将使用规则基础的检验方法")
    
    def verify_intent(self, text: str, fasttext_result: str) -> str:
        """二次检验意图"""
        # 如果FastText结果不是"其他"，先进行规则检验
        if fasttext_result != "其他":
            if self.rule_based_verify(text, fasttext_result):
                return fasttext_result
        
        # 使用Qwen模型进行检验
        if self.model and self.tokenizer:
            return self.llm_verify(text)
        else:
            return self.rule_based_verify_fallback(text)
    
    def rule_based_verify(self, text: str, predicted_intent: str) -> bool:
        """基于规则的检验"""
        intent_keywords = {
            "读音": ["读", "念", "拼音", "音"],
            "书写": ["写", "笔顺", "笔画", "书写"],
            "查字": ["加", "减", "笔", "左边", "右边", "上", "下", "组成", "什么字"],
            "查词": ["词", "成语", "字是什么"],
            "组词": ["组词", "造句", "搭配"],
            "释义": ["意思", "含义", "解释", "定义", "释义"],
            "分字": ["左边", "右边", "上", "下", "分解", "部件", "偏旁"]
        }
        
        if predicted_intent in intent_keywords:
            keywords = intent_keywords[predicted_intent]
            return any(keyword in text for keyword in keywords)
        
        return False
    
    def rule_based_verify_fallback(self, text: str) -> str:
        """规则基础的备用检验方法"""
        # 检查是否包含其他类别关键词
        for keyword in OTHER_KEYWORDS:
            if keyword in text:
                return "其他"
        
        # 检查是否包含字词库相关关键词
        char_related = ["字", "词", "读音", "写法", "意思", "组词", "笔画"]
        if any(keyword in text for keyword in char_related):
            # 进一步细分
            if any(word in text for word in ["读", "念", "拼音"]):
                return "读音"
            elif any(word in text for word in ["写", "笔顺", "书写"]):
                return "书写"
            elif any(word in text for word in ["意思", "含义", "解释"]):
                return "释义"
            elif "组词" in text:
                return "组词"
            elif any(word in text for word in ["加", "减", "笔", "什么字"]):
                return "查字"
            elif any(word in text for word in ["左边", "右边", "分解"]):
                return "分字"
            else:
                return "查词"
        
        return "其他"
    
    def llm_verify(self, text: str) -> str:
        """使用LLM进行检验"""
        prompt = f"""
请判断以下用户问题属于哪个意图类别。

意图类别: {INTENT_TYPES}

用户问题: {text}

请只返回意图类别名称，如果不属于任何字词库相关类别，返回"其他"。

意图类别:"""
        
        try:
            inputs = self.tokenizer(prompt, return_tensors="pt").to(self.model.device)
            
            with torch.no_grad():
                outputs = self.model.generate(
                    **inputs,
                    max_new_tokens=10,
                    temperature=0.1,
                    do_sample=False
                )
            
            response = self.tokenizer.decode(outputs[0][inputs.input_ids.shape[1]:], skip_special_tokens=True)
            response = response.strip()
            
            # 检查响应是否是有效的意图类别
            if response in INTENT_TYPES:
                return response
            else:
                return "其他"
                
        except Exception as e:
            print(f"LLM检验出错: {e}")
            return self.rule_based_verify_fallback(text)


class IntentClassifier:
    """意图识别主类"""
    
    def __init__(self):
        self.fasttext_classifier = FastTextClassifier()
        self.qwen_verifier = QwenVerifier()
    
    def classify(self, text: str) -> Dict:
        """分类用户输入"""
        # 1. FastText快速分类
        fasttext_intent, fasttext_confidence = self.fasttext_classifier.predict(text)
        
        # 2. Qwen二次检验
        verified_intent = self.qwen_verifier.verify_intent(text, fasttext_intent)
        
        result = {
            "query": text,
            "fasttext_result": fasttext_intent,
            "fasttext_confidence": fasttext_confidence,
            "final_intent": verified_intent,
            "is_other": verified_intent == "其他"
        }
        
        return result
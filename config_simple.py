# -*- coding: utf-8 -*-
"""
简化版配置文件 - 用于测试，不依赖torch
"""

# 意图类别定义
INTENT_TYPES = ["读音", "书写", "查字", "查词", "组词", "释义", "分字"]

# 汉字结构类型
STRUCTURE_TYPES = {
    "single": "独体字",
    "left_right": "左右结构", 
    "up_bottom": "上下结构",
    "enclosure": "包围结构",
    "pin": "品字结构",
    "complex": "镶嵌结构/复合结构",
    "all": "所有结构"
}

# 槽位定义
SLOT_SCHEMA = {
    "target_char": {
        "type": "list",
        "description": "单个目标字",
        "example": ["焜"]
    },
    "target_phrase": {
        "type": "list", 
        "description": "单个目标词",
        "example": ["毛泽东"]
    },
    "strokes": {
        "type": "int",
        "description": "查询笔画数变化",
        "example": 3
    },
    "radical": {
        "type": "str",
        "description": "偏旁/部首",
        "example": "提手旁"
    },
    "structure_type": {
        "type": "str",
        "description": "汉字结构",
        "enum": list(STRUCTURE_TYPES.keys())
    },
    "component_count": {
        "type": "int",
        "description": "部件数量"
    },
    "components": {
        "type": "list",
        "description": "具体的部件",
        "example": ["木", "黄"]
    },
    "target_component": {
        "type": "list",
        "description": "目标部件位置",
        "example": ["左", "右", "上", "下"]
    }
}

# 模型配置
MODEL_CONFIG = {
    "fasttext_model_path": "models/fasttext_intent.bin",
    "qwen_model_name": "Qwen/Qwen2.5-3B-Instruct",
    "device": "cpu"  # 默认使用CPU
}

# 其他类别的关键词
OTHER_KEYWORDS = [
    "天气", "股票", "新闻", "搜索", "查询", "AI", "科技", 
    "政治", "经济", "体育", "娱乐", "旅游", "美食"
]
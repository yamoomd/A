# -*- coding: utf-8 -*-
"""
中文字词库意图识别和抽槽系统主程序
"""

import json
import sys
from typing import Dict, Any
from intent_classifier import IntentClassifier
from slot_extractor import SlotExtractor
from search_handler import SearchHandler


class ChineseCharacterLibrary:
    """中文字词库主类"""
    
    def __init__(self):
        print("正在初始化中文字词库系统...")
        
        # 初始化各个组件
        self.intent_classifier = IntentClassifier()
        self.slot_extractor = SlotExtractor()
        self.search_handler = SearchHandler()
        
        print("系统初始化完成！")
    
    def process_query(self, query: str) -> Dict[str, Any]:
        """处理用户查询"""
        print(f"\n处理查询: {query}")
        
        # 1. 意图识别
        intent_result = self.intent_classifier.classify(query)
        print(f"意图识别结果: {intent_result}")
        
        # 2. 处理不同类型的意图
        if intent_result["is_other"]:
            # 其他类别 - 联网搜索
            result = self.search_handler.handle_other_query(query)
        else:
            # 字词库相关意图 - 抽槽处理
            slot_result = self.slot_extractor.extract_slots(
                query, 
                intent_result["final_intent"]
            )
            print(f"抽槽结果: {slot_result}")
            
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
            return f"回答: {result['answer']}"
        else:
            # 字词库相关的结构化结果
            output = f"查询: {result['query']}\n"
            output += f"意图: {result['slot_info']['type']}\n"
            output += f"槽位信息: {json.dumps(result['slot_info']['slot'], ensure_ascii=False, indent=2)}\n"
            
            # 根据意图类型提供相应的提示
            intent_type = result['slot_info']['type']
            if intent_type == "复合意图":
                output += "\n这是一个复合查询，需要分步骤处理："
                for i, sub_query in enumerate(result['slot_info']['slot']['sub_queries'], 1):
                    output += f"\n  {i}. {sub_query}"
            else:
                output += f"\n注意: 这是一个'{intent_type}'类型的查询，请根据槽位信息进行相应的字词库操作。"
            
            return output


def main():
    """主函数"""
    print("欢迎使用中文字词库意图识别和抽槽系统！")
    print("支持的意图类型：读音、书写、查字、查词、组词、释义、分字")
    print("输入 'quit' 或 'exit' 退出程序\n")
    
    # 初始化系统
    try:
        system = ChineseCharacterLibrary()
    except Exception as e:
        print(f"系统初始化失败: {e}")
        return
    
    # 交互式处理
    while True:
        try:
            # 获取用户输入
            query = input("请输入您的问题: ").strip()
            
            if not query:
                continue
            
            if query.lower() in ['quit', 'exit', '退出']:
                print("感谢使用，再见！")
                break
            
            # 处理查询
            result = system.process_query(query)
            
            # 输出结果
            formatted_output = system.format_output(result)
            print(f"\n{formatted_output}\n")
            print("-" * 50)
            
        except KeyboardInterrupt:
            print("\n\n程序被中断，再见！")
            break
        except Exception as e:
            print(f"处理查询时出错: {e}")
            continue


def test_examples():
    """测试示例"""
    print("运行测试示例...")
    
    system = ChineseCharacterLibrary()
    
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
        "帮我搜一下最新的AI进展",
        "今天A股行情如何？"
    ]
    
    for query in test_queries:
        print(f"\n{'='*60}")
        result = system.process_query(query)
        formatted_output = system.format_output(result)
        print(formatted_output)


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "test":
        test_examples()
    else:
        main()
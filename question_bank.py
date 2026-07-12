"""
题库管理模块
负责题目的存储、读取、错题标记管理
"""

import os
import json
import uuid


class QuestionBank:
    def __init__(self, data_folder):
        self.data_folder = data_folder
        self.questions_file = os.path.join(data_folder, 'questions.json')
        self.wrong_file = os.path.join(data_folder, 'wrong_questions.json')
        self._ensure_files()

    def _ensure_files(self):
        """确保数据文件存在"""
        if not os.path.exists(self.questions_file):
            self._save_json(self.questions_file, [])
        if not os.path.exists(self.wrong_file):
            self._save_json(self.wrong_file, [])

    def _save_json(self, filepath, data):
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def _load_json(self, filepath):
        with open(filepath, 'r', encoding='utf-8') as f:
            return json.load(f)

    def import_questions(self, questions):
        """导入题目到题库"""
        existing = self._load_json(self.questions_file)

        # 为每道题生成唯一ID
        for q in questions:
            if 'id' not in q or not q['id']:
                q['id'] = str(uuid.uuid4())[:8]

        existing.extend(questions)
        self._save_json(self.questions_file, existing)
        return len(questions)

    def get_all_questions(self):
        """获取所有题目"""
        return self._load_json(self.questions_file)

    def get_info(self):
        """获取题库信息"""
        questions = self._load_json(self.questions_file)
        wrong_ids = self._load_json(self.wrong_file)

        # 统计题型
        type_counts = {}
        for q in questions:
            t = q.get('type', 'single')
            type_name = {'single': '单选题', 'multiple': '多选题', 'judge': '判断题'}.get(t, t)
            type_counts[type_name] = type_counts.get(type_name, 0) + 1

        return {
            'total': len(questions),
            'wrong_count': len(wrong_ids),
            'type_counts': type_counts
        }

    def clear(self):
        """清空题库"""
        self._save_json(self.questions_file, [])
        self._save_json(self.wrong_file, [])

    def mark_wrong(self, question_id):
        """标记错题"""
        wrong_ids = self._load_json(self.wrong_file)
        if question_id not in wrong_ids:
            wrong_ids.append(question_id)
            self._save_json(self.wrong_file, wrong_ids)

    def get_wrong_question_ids(self):
        """获取错题ID列表"""
        return self._load_json(self.wrong_file)

    def clear_wrong(self):
        """清空错题标记"""
        self._save_json(self.wrong_file, [])

    def remove_wrong_mark(self, question_id):
        """移除单个错题标记"""
        wrong_ids = self._load_json(self.wrong_file)
        if question_id in wrong_ids:
            wrong_ids.remove(question_id)
            self._save_json(self.wrong_file, wrong_ids)

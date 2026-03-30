# ai_model.py
# 封裝 google.generativeai 的呼叫（固定 model: gemini-flash-latest）

import google.generativeai as genai

class AIModel:
    def __init__(self, api_key: str):
        if not api_key:
            raise ValueError('需要提供 google api key')
        genai.configure(api_key=api_key)
        self.model_name = 'gemini-2.0-flash-lite'

    def build_system_instruction(self, config: dict, user_memory: str = "") -> str:
        base = config.get('base_setting', {})
        name = base.get('name', 'AI')
        role = base.get('role', '助手')
        interests = '\n- '.join(config.get('interests', []))
        style = '\n- '.join(config.get('speaking_style', []))
        experiences = '\n- '.join(config.get('generated_experiences', []))
        
        # 讀取範例 (如果你有照著之前的教學加的話)
        examples_list = config.get('examples', [])
        examples_str = "\n".join(examples_list)

        final_instruction = f"""
        你現在扮演「{name}」，一個{role}。
        
        【基本設定】
        背景：{base.get('background','無')}
        興趣：
        - {interests}
        
        【Bot 的過往經歷】
        - {experiences}

        【關於目前的對話對象 (User)】
        這很重要，請根據以下記憶來與對方互動：
        {user_memory}
        
        【說話風格】
        - {style}

        請依照以上設定與使用者對話。
        """
        return final_instruction

    def start_chat(self, system_instruction: str, history: list = None):
        # 建立一個簡易 wrapper 物件 (同步/非同步呼叫在外面做)
        model = genai.GenerativeModel(
            model_name=self.model_name, 
            system_instruction=system_instruction
        )
        return model
    
    def list_models(self):
        print("正在查詢可用模型...")
        try:
            for m in genai.list_models():
                if 'generateContent' in m.supported_generation_methods:
                    print(f"- {m.name}")
        except Exception as e:
            print(f"查詢失敗：{e}")
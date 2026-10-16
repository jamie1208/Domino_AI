"""ExplainerSkill: evidence-aware, no invented source or causal certainty."""
class ExplainerSkill:
    def run(self,scenario,companies, findings):
        if not companies:
            return '無法產生具證據支持的數值分析：缺少可用關係、事件種子節點或經確認的事件強度。'
        top=companies[:3]
        text='；'.join(f'{c.node_id}（示範指數 {c.risk_index}）' for c in top)
        return f'在目前的示範網絡及給定情境假設下，相對暴露較高的節點包括：{text}。此分數是原型模型輸出，並非真實企業損失或發生機率。'

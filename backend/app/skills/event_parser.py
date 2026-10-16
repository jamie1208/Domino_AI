"""EventParserSkill: conservative offline parsing; never invents severity."""
import re
from app.schemas import Scenario

class EventParserSkill:
    def run(self, scenario: Scenario) -> Scenario:
        text = scenario.description
        updates = {}
        if scenario.event_type == 'unknown':
            if any(x in text for x in ['地震','颱風','earthquake','typhoon']):
                updates['event_type'] = 'natural_disaster'
            elif any(x in text for x in ['斷料','缺料','供應中斷','物流中斷','supply chain']):
                updates['event_type'] = 'supply_chain'
            elif any(x in text for x in ['關稅','出口限制','tariff','export control']):
                updates['event_type'] = 'economic_policy'
        if scenario.duration_days is None:
            match = re.search(r'(\d{1,4})\s*天', text)
            if match: updates['duration_days'] = int(match.group(1))
        return scenario.model_copy(update=updates)

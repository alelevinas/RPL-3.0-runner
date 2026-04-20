import re
import json
import os

class MistakeMatcher:
    def __init__(self, schema_path="shared/mistake_schema.json", patterns_path="shared/mistake_patterns.json"):
        self.schema_path = schema_path
        self.patterns_path = patterns_path
        self.patterns = self._load_patterns()

    def _load_patterns(self):
        if not os.path.exists(self.patterns_path):
            return []
        with open(self.patterns_path, 'r') as f:
            return json.load(f)

    def match(self, language, output, exit_code=None, custom_patterns=None):
        """
        Matches Runner output against patterns and returns a list of hints.
        """
        hints = []
        patterns_to_use = custom_patterns if custom_patterns is not None else self.patterns
        for p in patterns_to_use:
            # Handle both dictionary (JSON) and object (SQLAlchemy model) patterns
            p_lang = p['language'] if isinstance(p, dict) else p.language
            if p_lang == language:
                p_pattern = p.get('pattern') if isinstance(p, dict) else p.pattern
                p_exit_code = p.get('exit_code') if isinstance(p, dict) else p.exit_code
                p_id = p.get('id') if isinstance(p, dict) else p.id
                p_hint = p.get('hint') if isinstance(p, dict) else p.hint
                p_category = p.get('category', 'unknown') if isinstance(p, dict) else p.category

                match_regex = re.search(p_pattern, output) if p_pattern else True
                match_exit = (p_exit_code == exit_code) if p_exit_code is not None else True
                
                if match_regex and match_exit:
                    hints.append({
                        "id": p_id,
                        "hint": p_hint,
                        "category": p_category
                    })
        return hints

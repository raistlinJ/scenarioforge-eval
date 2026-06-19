import os
import json

class Reporter:
    def __init__(self, out_dir: str):
        self.out_dir = out_dir

    def log_result(self, spec_name: str, result: dict):
        log_path = os.path.join(self.out_dir, f"{spec_name}_result.json")
        with open(log_path, 'w', encoding='utf-8') as f:
            json.dump(result, f, indent=2)
            
        print(f"--- Results for {spec_name} ---")
        print(f"Success: {result['success']}")
        for stage, status in result['stages'].items():
            print(f"  {stage}: {status}")
            
        if result['error']:
            print("\nError encountered:")
            print(result['error'])
            
            # TODO: Pack the error, the plan.json, and the XML into a prompt payload for the AI
            self._generate_ai_prompt(spec_name, result)
            
    def _generate_ai_prompt(self, spec_name: str, result: dict):
        prompt_path = os.path.join(self.out_dir, f"{spec_name}_ai_prompt.md")
        with open(prompt_path, 'w', encoding='utf-8') as f:
            f.write(f"# Failure Report for {spec_name}\n\n")
            f.write("## Stack Trace\n```python\n")
            f.write(result['error'])
            f.write("\n```\n\n")
            
            plan_path = os.path.join(self.out_dir, 'plan.json')
            if os.path.exists(plan_path):
                f.write("## Generated Plan\n```json\n")
                with open(plan_path, 'r') as pf:
                    f.write(pf.read())
                f.write("\n```\n")

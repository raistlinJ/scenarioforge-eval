import os
import json

class Reporter:
    ARTIFACT_SECTIONS = (
        ('scenario_xml', 'Generated Scenario XML', 'xml'),
        ('preview_plan_json', 'Preview Plan JSON', 'json'),
        ('flag_sequencing_json', 'Flag Sequencing JSON', 'json'),
        ('topo_json', 'Topo Phase JSON', 'json'),
        ('preview_plan_log', 'Preview Plan Log', 'text'),
        ('flag_sequencing_log', 'Flag Sequencing Log', 'text'),
        ('topo_log', 'Topo Phase Log', 'text'),
        ('execute_log', 'Execute Log', 'text'),
    )

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
            
        if result.get('warnings'):
            print("\nWarnings encountered:")
            for w in result['warnings']:
                print(f"  - {w}")
            
        if result.get('error'):
            print("\nError encountered:")
            print(result['error'])
            
            # Pack the available phase artifacts into a prompt payload for follow-up debugging.
            self._generate_ai_prompt(spec_name, result)

    def _write_artifact_section(self, handle, title: str, artifact_path: str, fence: str) -> None:
        handle.write(f"## {title}\n")
        handle.write(f"Source: {artifact_path}\n\n")
        handle.write(f"```{fence}\n")
        with open(artifact_path, 'r', encoding='utf-8') as artifact_file:
            content = artifact_file.read()
        handle.write(content)
        if content and not content.endswith('\n'):
            handle.write('\n')
        handle.write("```\n\n")
            
    def _generate_ai_prompt(self, spec_name: str, result: dict):
        prompt_path = os.path.join(self.out_dir, f"{spec_name}_ai_prompt.md")
        with open(prompt_path, 'w', encoding='utf-8') as f:
            f.write(f"# Failure Report for {spec_name}\n\n")
            f.write("## Stage Summary\n```json\n")
            json.dump(result.get('stages', {}), f, indent=2)
            f.write("\n```\n\n")
            f.write("## Stack Trace\n```python\n")
            f.write(result['error'])
            f.write("\n```\n\n")

            artifacts = result.get('artifacts') or {}
            wrote_artifact = False
            for artifact_key, title, fence in self.ARTIFACT_SECTIONS:
                artifact_path = artifacts.get(artifact_key)
                if not artifact_path or not os.path.exists(artifact_path):
                    continue
                self._write_artifact_section(f, title, artifact_path, fence)
                wrote_artifact = True

            if not wrote_artifact:
                f.write("## Captured Artifacts\nNo phase artifacts were available when the run failed.\n")

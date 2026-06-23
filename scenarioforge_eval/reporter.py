import os
import json
import xml.etree.ElementTree as ET

class Reporter:
    ARTIFACT_SECTIONS = (
        ('scenario_xml', 'Generated Scenario XML', 'xml'),
        ('seed_txt', 'Iteration Seed', 'text'),
        ('preview_plan_json', 'Preview Plan JSON', 'json'),
        ('flag_sequencing_json', 'Flag Sequencing JSON', 'json'),
        ('topo_json', 'Topo Phase JSON', 'json'),
        ('preview_plan_log', 'Preview Plan Log', 'text'),
        ('flag_sequencing_log', 'Flag Sequencing Log', 'text'),
        ('topo_log', 'Topo Phase Log', 'text'),
        ('execute_log', 'Execute Log', 'text'),
        ('execute_validation_json', 'Execute Validation JSON', 'json'),
        ('execute_report', 'Scenario Report', 'markdown'),
        ('execute_summary', 'Scenario Summary', 'json'),
    )

    def __init__(self, out_dir: str):
        self.out_dir = os.path.abspath(os.path.expanduser(out_dir))

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

    @staticmethod
    def _redacted_xml_text(xml_path: str) -> str:
        try:
            tree = ET.parse(xml_path)
        except Exception as exc:
            return f"[XML redaction unavailable: failed to parse {xml_path}: {exc}]"

        for element in tree.getroot().iter('CoreConnection'):
            if 'ssh_password' in element.attrib:
                element.set('ssh_password', '[REDACTED]')
        return ET.tostring(tree.getroot(), encoding='unicode')

    def _write_artifact_section(self, handle, artifact_key: str, title: str, artifact_path: str, fence: str) -> None:
        source_label = artifact_path
        if artifact_key == 'scenario_xml':
            source_label = f"{artifact_path} (ssh_password redacted)"

        handle.write(f"## {title}\n")
        handle.write(f"Source: {source_label}\n\n")
        handle.write(f"```{fence}\n")
        if artifact_key == 'scenario_xml':
            content = self._redacted_xml_text(artifact_path)
        else:
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
                self._write_artifact_section(f, artifact_key, title, artifact_path, fence)
                wrote_artifact = True

            if not wrote_artifact:
                f.write("## Captured Artifacts\nNo phase artifacts were available when the run failed.\n")

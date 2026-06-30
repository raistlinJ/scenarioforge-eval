import csv
import json
import os
import xml.etree.ElementTree as ET

try:
    from .metrics import rounded_seconds, utc_now_iso
except ImportError:
    from metrics import rounded_seconds, utc_now_iso

class Reporter:
    RUN_METRIC_FIELDS = [
        'run_index', 'spec_name', 'spec_file', 'iteration_index', 'iteration_count',
        'target_phase', 'seed', 'success', 'failed_stage', 'failed_at',
        'started_at', 'ended_at', 'duration_s', 'router_count', 'host_count',
        'node_count', 'service_count', 'vulnerability_count', 'flow_enabled',
        'flow_chain_length', 'validation_ok', 'phase_count', 'phase_duration_s',
        'estimated_output_tokens', 'log_size_bytes', 'artifact_file_count',
        'artifact_total_size_bytes', 'cpu_user_s', 'cpu_system_s', 'cpu_total_s',
        'max_rss_bytes', 'input_blocks', 'output_blocks', 'context_switches',
    ]
    PHASE_METRIC_FIELDS = [
        'run_index', 'spec_name', 'spec_file', 'iteration_index', 'target_phase',
        'seed', 'success', 'phase', 'stage_status', 'returncode', 'timed_out',
        'started_at', 'ended_at', 'duration_s', 'stdout_bytes', 'stderr_bytes',
        'combined_bytes', 'combined_lines', 'estimated_output_tokens', 'log_path',
        'log_size_bytes', 'plan_output_size_bytes', 'cpu_user_s', 'cpu_system_s',
        'cpu_total_s', 'max_rss_bytes', 'minor_page_faults', 'major_page_faults',
        'input_blocks', 'output_blocks', 'voluntary_context_switches',
        'involuntary_context_switches', 'session_id', 'validation_ok',
    ]
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
        self.write_run_metrics(spec_name, result)
            
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
    def _nested(data: dict, *keys, default=None):
        value = data
        for key in keys:
            if not isinstance(value, dict):
                return default
            value = value.get(key)
        return default if value is None else value

    @staticmethod
    def _phase_stage_key(phase: str) -> str:
        if phase == 'topo':
            return 'topology'
        return str(phase or '').replace('-', '_')

    @classmethod
    def _first_failed_stage(cls, result: dict) -> str | None:
        stages = result.get('stages') or {}
        for stage, status in stages.items():
            if stage == 'failed_at':
                continue
            if status is False:
                return stage
            if isinstance(status, str) and status.strip().upper().startswith('FAIL'):
                return stage
        return None

    @staticmethod
    def _number_summary(values: list[float]) -> dict:
        numeric_values = []
        for value in values:
            if value in (None, ''):
                continue
            try:
                numeric_values.append(float(value))
            except (TypeError, ValueError):
                continue
        if not numeric_values:
            return {'total': 0.0, 'avg': 0.0, 'min': 0.0, 'max': 0.0}
        return {
            'total': rounded_seconds(sum(numeric_values)),
            'avg': rounded_seconds(sum(numeric_values) / len(numeric_values)),
            'min': rounded_seconds(min(numeric_values)),
            'max': rounded_seconds(max(numeric_values)),
        }

    def _run_metrics_row(self, index: int, result: dict) -> dict:
        metrics = result.get('metrics') or {}
        run = metrics.get('run') or {}
        spec = metrics.get('spec') or {}
        phases = metrics.get('phases') or {}
        phase_values = list(phases.values())
        resource_metrics = run.get('resources') or {}
        artifacts = metrics.get('artifacts') or {}
        output_dir = artifacts.get('output_dir') or {}
        execute_result = (result.get('phase_results') or {}).get('execute') or {}
        validation_summary = execute_result.get('validation_summary') or {}
        failed_stage = self._first_failed_stage(result)

        return {
            'run_index': index,
            'spec_name': self._nested(metrics, 'spec', 'name', default=result.get('metadata', {}).get('spec_name', '')),
            'spec_file': result.get('metadata', {}).get('spec_file', ''),
            'iteration_index': result.get('metadata', {}).get('iteration_index', ''),
            'iteration_count': result.get('metadata', {}).get('iteration_count', ''),
            'target_phase': self._nested(metrics, 'spec', 'target_phase', default=result.get('metadata', {}).get('target_phase', '')),
            'seed': self._nested(metrics, 'spec', 'seed', default=result.get('metadata', {}).get('seed', '')),
            'success': bool(result.get('success')),
            'failed_stage': failed_stage or '',
            'failed_at': (result.get('stages') or {}).get('failed_at', ''),
            'started_at': run.get('started_at', ''),
            'ended_at': run.get('ended_at', ''),
            'duration_s': run.get('duration_s', 0.0),
            'router_count': self._nested(spec, 'topology', 'routers', default=0),
            'host_count': self._nested(spec, 'topology', 'hosts', default=0),
            'node_count': self._nested(spec, 'topology', 'nodes', default=0),
            'service_count': self._nested(spec, 'services', 'count', default=0),
            'vulnerability_count': self._nested(spec, 'vulnerabilities', 'count', default=0),
            'flow_enabled': self._nested(spec, 'flows', 'enabled', default=False),
            'flow_chain_length': self._nested(spec, 'flows', 'chain_length', default=0),
            'validation_ok': validation_summary.get('ok', ''),
            'phase_count': len(phases),
            'phase_duration_s': rounded_seconds(sum(float(phase.get('duration_s') or 0.0) for phase in phase_values)),
            'estimated_output_tokens': sum(int(self._nested(phase, 'outputs', 'combined', 'estimated_tokens', default=0) or 0) for phase in phase_values),
            'log_size_bytes': sum(int(self._nested(phase, 'log', 'size_bytes', default=0) or 0) for phase in phase_values),
            'artifact_file_count': output_dir.get('file_count', 0),
            'artifact_total_size_bytes': output_dir.get('total_size_bytes', 0),
            'cpu_user_s': resource_metrics.get('cpu_user_s', 0.0),
            'cpu_system_s': resource_metrics.get('cpu_system_s', 0.0),
            'cpu_total_s': resource_metrics.get('cpu_total_s', 0.0),
            'max_rss_bytes': resource_metrics.get('max_rss_bytes', 0),
            'input_blocks': resource_metrics.get('input_blocks', 0),
            'output_blocks': resource_metrics.get('output_blocks', 0),
            'context_switches': int(resource_metrics.get('voluntary_context_switches', 0) or 0) + int(resource_metrics.get('involuntary_context_switches', 0) or 0),
        }

    def _phase_metrics_rows(self, index: int, result: dict) -> list[dict]:
        rows = []
        metrics = result.get('metrics') or {}
        phase_results = result.get('phase_results') or {}
        stages = result.get('stages') or {}
        spec = metrics.get('spec') or {}

        for phase, phase_result in phase_results.items():
            phase_metrics = phase_result.get('metrics') or self._nested(metrics, 'phases', phase, default={}) or {}
            outputs = phase_metrics.get('outputs') or {}
            resources = phase_metrics.get('resources') or {}
            log_metrics = phase_metrics.get('log') or {}
            plan_metrics = phase_metrics.get('plan_output') or {}
            validation_summary = phase_result.get('validation_summary') or {}
            stage_status = stages.get(self._phase_stage_key(phase), '')

            rows.append({
                'run_index': index,
                'spec_name': self._nested(metrics, 'spec', 'name', default=''),
                'spec_file': result.get('metadata', {}).get('spec_file', ''),
                'iteration_index': result.get('metadata', {}).get('iteration_index', ''),
                'target_phase': spec.get('target_phase', ''),
                'seed': spec.get('seed', ''),
                'success': bool(result.get('success')),
                'phase': phase,
                'stage_status': stage_status,
                'returncode': phase_result.get('returncode', ''),
                'timed_out': bool(phase_result.get('timed_out')),
                'started_at': phase_metrics.get('started_at', ''),
                'ended_at': phase_metrics.get('ended_at', ''),
                'duration_s': phase_metrics.get('duration_s', 0.0),
                'stdout_bytes': self._nested(outputs, 'stdout', 'bytes', default=0),
                'stderr_bytes': self._nested(outputs, 'stderr', 'bytes', default=0),
                'combined_bytes': self._nested(outputs, 'combined', 'bytes', default=0),
                'combined_lines': self._nested(outputs, 'combined', 'lines', default=0),
                'estimated_output_tokens': self._nested(outputs, 'combined', 'estimated_tokens', default=0),
                'log_path': log_metrics.get('path', ''),
                'log_size_bytes': log_metrics.get('size_bytes', 0),
                'plan_output_size_bytes': plan_metrics.get('size_bytes', 0),
                'cpu_user_s': resources.get('cpu_user_s', 0.0),
                'cpu_system_s': resources.get('cpu_system_s', 0.0),
                'cpu_total_s': resources.get('cpu_total_s', 0.0),
                'max_rss_bytes': resources.get('max_rss_bytes', 0),
                'minor_page_faults': resources.get('minor_page_faults', 0),
                'major_page_faults': resources.get('major_page_faults', 0),
                'input_blocks': resources.get('input_blocks', 0),
                'output_blocks': resources.get('output_blocks', 0),
                'voluntary_context_switches': resources.get('voluntary_context_switches', 0),
                'involuntary_context_switches': resources.get('involuntary_context_switches', 0),
                'session_id': phase_result.get('session_id') or '',
                'validation_ok': validation_summary.get('ok', ''),
            })
        return rows

    def _build_batch_metrics_summary(self, results: list[dict], run_rows: list[dict], phase_rows: list[dict]) -> dict:
        successes = sum(1 for row in run_rows if row.get('success'))
        failures = len(run_rows) - successes
        failures_by_stage: dict[str, int] = {}
        for row in run_rows:
            if row.get('success'):
                continue
            stage = str(row.get('failed_stage') or 'unknown')
            failures_by_stage[stage] = failures_by_stage.get(stage, 0) + 1

        phases: dict[str, dict] = {}
        for row in phase_rows:
            phase = str(row.get('phase') or 'unknown')
            bucket = phases.setdefault(phase, {'rows': []})
            bucket['rows'].append(row)

        phase_summary = {}
        for phase, bucket in sorted(phases.items()):
            rows = bucket['rows']
            phase_summary[phase] = {
                'count': len(rows),
                'failures': sum(
                    1
                    for row in rows
                    if row.get('timed_out') or row.get('returncode') not in ('', None, 0, '0')
                ),
                'timeouts': sum(1 for row in rows if row.get('timed_out')),
                'duration_s': self._number_summary([row.get('duration_s') for row in rows]),
                'estimated_output_tokens': {
                    'total': sum(int(row.get('estimated_output_tokens') or 0) for row in rows),
                    'avg': rounded_seconds(sum(int(row.get('estimated_output_tokens') or 0) for row in rows) / len(rows)) if rows else 0.0,
                },
                'log_size_bytes': {
                    'total': sum(int(row.get('log_size_bytes') or 0) for row in rows),
                    'avg': rounded_seconds(sum(int(row.get('log_size_bytes') or 0) for row in rows) / len(rows)) if rows else 0.0,
                },
                'cpu_total_s': self._number_summary([row.get('cpu_total_s') for row in rows]),
                'max_rss_bytes': max((int(row.get('max_rss_bytes') or 0) for row in rows), default=0),
            }

        return {
            'schema_version': 1,
            'generated_at': utc_now_iso(),
            'output_dir': self.out_dir,
            'token_estimator': 'regex_word_or_punctuation',
            'runs': {
                'total': len(results),
                'successes': successes,
                'failures': failures,
                'pass_rate': rounded_seconds(successes / len(run_rows)) if run_rows else 0.0,
                'duration_s': self._number_summary([row.get('duration_s') for row in run_rows]),
                'artifact_total_size_bytes': sum(int(row.get('artifact_total_size_bytes') or 0) for row in run_rows),
                'estimated_output_tokens': sum(int(row.get('estimated_output_tokens') or 0) for row in run_rows),
                'cpu_total_s': self._number_summary([row.get('cpu_total_s') for row in run_rows]),
                'max_rss_bytes': max((int(row.get('max_rss_bytes') or 0) for row in run_rows), default=0),
            },
            'failures': {
                'by_stage': failures_by_stage,
            },
            'phases': phase_summary,
        }

    @staticmethod
    def _write_csv(path: str, rows: list[dict], fieldnames: list[str]) -> None:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, 'w', encoding='utf-8', newline='') as handle:
            writer = csv.DictWriter(handle, fieldnames=fieldnames, extrasaction='ignore')
            writer.writeheader()
            for row in rows:
                writer.writerow(row)

    @staticmethod
    def _write_json(path: str, payload: dict | list) -> None:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, 'w', encoding='utf-8') as handle:
            json.dump(payload, handle, indent=2, sort_keys=True)

    @staticmethod
    def _safe_metric_dir_name(name: str) -> str:
        safe = ''.join(ch if ch.isalnum() or ch in ('-', '_', '.') else '_' for ch in str(name or '').strip())
        return safe.strip('._') or 'run'

    def _run_metrics_dirs(self, spec_name: str, result: dict) -> list[str]:
        dirs = []
        artifacts = result.get('artifacts') or {}
        run_output_dir = artifacts.get('output_dir')
        if isinstance(run_output_dir, str) and run_output_dir.strip():
            dirs.append(os.path.join(os.path.abspath(os.path.expanduser(run_output_dir)), 'metrics'))

        root_run_dir = os.path.join(
            self.out_dir,
            'metrics',
            'runs',
            self._safe_metric_dir_name(spec_name),
        )
        dirs.append(root_run_dir)
        return list(dict.fromkeys(dirs))

    def _write_run_metrics_markdown(self, path: str, spec_name: str, payload: dict) -> None:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        run_row = payload.get('run') or {}
        phase_rows = payload.get('phases') or []
        with open(path, 'w', encoding='utf-8') as handle:
            handle.write(f"# Run Metrics: {spec_name}\n\n")
            handle.write(f"Generated: {payload.get('generated_at', '')}\n\n")
            handle.write("## Summary\n\n")
            handle.write("| Metric | Value |\n| --- | ---: |\n")
            handle.write(f"| Success | {run_row.get('success', False)} |\n")
            handle.write(f"| Duration (s) | {run_row.get('duration_s', 0.0)} |\n")
            handle.write(f"| Phase duration (s) | {run_row.get('phase_duration_s', 0.0)} |\n")
            handle.write(f"| Estimated output tokens | {run_row.get('estimated_output_tokens', 0)} |\n")
            handle.write(f"| Log bytes | {run_row.get('log_size_bytes', 0)} |\n")
            handle.write(f"| Artifact bytes | {run_row.get('artifact_total_size_bytes', 0)} |\n")
            handle.write(f"| CPU total (s) | {run_row.get('cpu_total_s', 0.0)} |\n")
            handle.write(f"| Max RSS bytes | {run_row.get('max_rss_bytes', 0)} |\n\n")

            handle.write("## Phases\n\n")
            handle.write("| Phase | Status | Return Code | Timeout | Duration (s) | Estimated Tokens | Log Bytes |\n")
            handle.write("| --- | --- | ---: | --- | ---: | ---: | ---: |\n")
            for row in phase_rows:
                handle.write(
                    f"| {row.get('phase', '')} | {row.get('stage_status', '')} | "
                    f"{row.get('returncode', '')} | {row.get('timed_out', False)} | "
                    f"{row.get('duration_s', 0.0)} | {row.get('estimated_output_tokens', 0)} | "
                    f"{row.get('log_size_bytes', 0)} |\n"
                )

    def write_run_metrics(self, spec_name: str, result: dict, *, run_index: int | None = None) -> dict:
        index = int(run_index or result.get('metadata', {}).get('run_index') or result.get('metadata', {}).get('iteration_index') or 1)
        run_row = self._run_metrics_row(index, result)
        phase_rows = self._phase_metrics_rows(index, result)
        payload = {
            'schema_version': 1,
            'generated_at': utc_now_iso(),
            'spec_name': spec_name,
            'success': bool(result.get('success')),
            'metadata': result.get('metadata') or {},
            'stages': result.get('stages') or {},
            'warnings': result.get('warnings') or [],
            'run': run_row,
            'phases': phase_rows,
            'metrics': result.get('metrics') or {},
        }

        written = {}
        for metrics_dir in self._run_metrics_dirs(spec_name, result):
            os.makedirs(metrics_dir, exist_ok=True)
            paths = {
                'summary_json': os.path.join(metrics_dir, 'run_metrics_summary.json'),
                'raw_json': os.path.join(metrics_dir, 'run_metrics_raw.json'),
                'summary_markdown': os.path.join(metrics_dir, 'run_metrics_summary.md'),
                'run_csv': os.path.join(metrics_dir, 'run_metrics.csv'),
                'phases_csv': os.path.join(metrics_dir, 'phase_metrics.csv'),
            }
            self._write_json(paths['summary_json'], {
                'schema_version': payload['schema_version'],
                'generated_at': payload['generated_at'],
                'spec_name': spec_name,
                'success': payload['success'],
                'metadata': payload['metadata'],
                'stages': payload['stages'],
                'warnings': payload['warnings'],
                'run': run_row,
                'phases': phase_rows,
            })
            self._write_json(paths['raw_json'], payload)
            self._write_run_metrics_markdown(paths['summary_markdown'], spec_name, payload)
            self._write_csv(paths['run_csv'], [run_row], self.RUN_METRIC_FIELDS)
            self._write_csv(paths['phases_csv'], phase_rows, self.PHASE_METRIC_FIELDS)
            written[metrics_dir] = paths
        return written

    def _write_metrics_markdown(self, path: str, summary: dict, export_paths: dict) -> None:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, 'w', encoding='utf-8') as handle:
            runs = summary.get('runs') or {}
            handle.write("# ScenarioForge Eval Batch Metrics\n\n")
            handle.write(f"Generated: {summary.get('generated_at', '')}\n\n")
            handle.write("## Run Summary\n\n")
            handle.write("| Metric | Value |\n| --- | ---: |\n")
            handle.write(f"| Total runs | {runs.get('total', 0)} |\n")
            handle.write(f"| Successes | {runs.get('successes', 0)} |\n")
            handle.write(f"| Failures | {runs.get('failures', 0)} |\n")
            handle.write(f"| Pass rate | {(runs.get('pass_rate', 0.0) or 0.0) * 100:.1f}% |\n")
            handle.write(f"| Total duration (s) | {(runs.get('duration_s') or {}).get('total', 0.0)} |\n")
            handle.write(f"| Estimated output tokens | {runs.get('estimated_output_tokens', 0)} |\n")
            handle.write(f"| Artifact bytes | {runs.get('artifact_total_size_bytes', 0)} |\n\n")

            handle.write("## Phase Summary\n\n")
            handle.write("| Phase | Count | Failures | Timeouts | Avg duration (s) | Estimated tokens | Log bytes |\n")
            handle.write("| --- | ---: | ---: | ---: | ---: | ---: | ---: |\n")
            for phase, phase_summary in (summary.get('phases') or {}).items():
                handle.write(
                    f"| {phase} | {phase_summary.get('count', 0)} | "
                    f"{phase_summary.get('failures', 0)} | {phase_summary.get('timeouts', 0)} | "
                    f"{(phase_summary.get('duration_s') or {}).get('avg', 0.0)} | "
                    f"{(phase_summary.get('estimated_output_tokens') or {}).get('total', 0)} | "
                    f"{(phase_summary.get('log_size_bytes') or {}).get('total', 0)} |\n"
                )

            handle.write("\n## Raw Exports\n\n")
            for label, export_path in export_paths.items():
                handle.write(f"- {label}: `{export_path}`\n")

    def write_batch_metrics(self, results: list[dict]) -> dict:
        run_rows = [self._run_metrics_row(index, result) for index, result in enumerate(results, start=1)]
        phase_rows = []
        for index, result in enumerate(results, start=1):
            phase_rows.extend(self._phase_metrics_rows(index, result))
            spec_name = self._nested(result.get('metrics') or {}, 'spec', 'name', default='')
            if not spec_name:
                spec_name = str(result.get('metadata', {}).get('spec_name') or f'run{index}')
            self.write_run_metrics(spec_name, result, run_index=index)

        summary = self._build_batch_metrics_summary(results, run_rows, phase_rows)
        metrics_dir = os.path.join(self.out_dir, 'metrics')
        paths = {
            'summary_json': os.path.join(self.out_dir, 'batch_metrics_summary.json'),
            'summary_markdown': os.path.join(self.out_dir, 'batch_metrics_summary.md'),
            'raw_jsonl': os.path.join(self.out_dir, 'batch_metrics_raw.jsonl'),
            'runs_csv': os.path.join(self.out_dir, 'batch_metrics_runs.csv'),
            'phases_csv': os.path.join(self.out_dir, 'batch_metrics_phases.csv'),
            'metrics_summary_json': os.path.join(metrics_dir, 'batch_metrics_summary.json'),
            'metrics_summary_markdown': os.path.join(metrics_dir, 'batch_metrics_summary.md'),
            'metrics_raw_jsonl': os.path.join(metrics_dir, 'batch_metrics_raw.jsonl'),
            'metrics_runs_csv': os.path.join(metrics_dir, 'batch_metrics_runs.csv'),
            'metrics_phases_csv': os.path.join(metrics_dir, 'batch_metrics_phases.csv'),
        }
        summary['exports'] = paths

        self._write_json(paths['summary_json'], summary)
        self._write_json(paths['metrics_summary_json'], summary)
        for raw_jsonl_path in (paths['raw_jsonl'], paths['metrics_raw_jsonl']):
            os.makedirs(os.path.dirname(raw_jsonl_path), exist_ok=True)
            with open(raw_jsonl_path, 'w', encoding='utf-8') as handle:
                for result in results:
                    json.dump(result, handle, sort_keys=True)
                    handle.write('\n')

        for runs_csv_path in (paths['runs_csv'], paths['metrics_runs_csv']):
            self._write_csv(runs_csv_path, run_rows, self.RUN_METRIC_FIELDS)
        for phases_csv_path in (paths['phases_csv'], paths['metrics_phases_csv']):
            self._write_csv(phases_csv_path, phase_rows, self.PHASE_METRIC_FIELDS)
        self._write_metrics_markdown(paths['summary_markdown'], summary, paths)
        self._write_metrics_markdown(paths['metrics_summary_markdown'], summary, paths)

        print("\nBatch metrics written:")
        for label, path in paths.items():
            print(f"  - {label}: {path}")
        return paths

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

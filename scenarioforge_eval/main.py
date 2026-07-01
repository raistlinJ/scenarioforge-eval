import argparse
import datetime
import json
import os
import glob
import logging
import random
import re
import sys
import time

try:
    from .parser import SpecParser
    from .executor import Executor
    from .reporter import Reporter
except ImportError:
    from parser import SpecParser
    from executor import Executor
    from reporter import Reporter


def _format_elapsed(seconds: float) -> str:
    seconds = max(0, int(seconds))
    hours, remainder = divmod(seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    if hours:
        return f"{hours}:{minutes:02d}:{seconds:02d}"
    return f"{minutes:02d}:{seconds:02d}"


def _supports_color(stream) -> bool:
    if os.environ.get("NO_COLOR") is not None:
        return False
    if os.environ.get("FORCE_COLOR"):
        return True
    return bool(getattr(stream, "isatty", lambda: False)())


def _paint(text: str, code: str, enabled: bool) -> str:
    if not enabled:
        return text
    return f"\033[{code}m{text}\033[0m"


def _first_failed_stage(result: dict) -> str | None:
    stages = result.get('stages') or {}
    for stage, status in stages.items():
        if status is False:
            return stage
        if isinstance(status, str) and status.strip().upper().startswith('FAIL'):
            return stage
    return None


def _spec_iterations(spec: SpecParser) -> int:
    return max(0, int(spec.spec.get('iterations', 1)))


ANSI_RE = re.compile(r"\x1b\[[0-?]*[ -/]*[@-~]")
COMBINED_ERROR_FILENAMES = ("combined-latest.errors", "combined_latest.errors")
LATEST_ERROR_FILENAME = "latest.errors"
GENERATOR_SUMMARY_KEYS = (
    'generators_used',
    'used_generators',
    'selected_generators',
    'generator_validation_detail',
)
EXTRA_VALIDATION_WARNING_FIELDS = ('flow_artifact_copy_pending',)


def _clean_output(text: str) -> str:
    return ANSI_RE.sub('', text or '')


def _read_text_if_available(path: str | None) -> str:
    if not path:
        return ''
    try:
        with open(path, 'r', encoding='utf-8') as handle:
            return handle.read()
    except Exception:
        return ''


def _read_json_if_available(path: str | None):
    if not path:
        return None
    try:
        with open(path, 'r', encoding='utf-8') as handle:
            return json.load(handle)
    except Exception:
        return None


def _is_populated(value) -> bool:
    if value is None:
        return False
    if isinstance(value, str):
        return bool(value.strip())
    if isinstance(value, (list, dict, tuple, set)):
        return len(value) > 0
    if isinstance(value, (int, float)):
        return value != 0
    return bool(value)


def _render_value(value) -> str:
    try:
        return json.dumps(value, sort_keys=True, default=str)
    except TypeError:
        return str(value)


def _validation_error_fields() -> tuple[str, ...]:
    return tuple(getattr(Executor, 'VALIDATION_ERROR_FIELDS', ()))


def _validation_warning_fields() -> tuple[str, ...]:
    fields = list(getattr(Executor, 'VALIDATION_WARNING_FIELDS', ()))
    for field in EXTRA_VALIDATION_WARNING_FIELDS:
        if field not in fields:
            fields.append(field)
    return tuple(fields)


def _validation_field_lines(summary: dict, fields: tuple[str, ...]) -> list[str]:
    lines = []
    for field in fields:
        value = summary.get(field)
        if _is_populated(value):
            lines.append(f"{field}: {_render_value(value)}")
    return lines


def _validation_has_issues(summary) -> bool:
    if not isinstance(summary, dict):
        return False
    if summary.get('ok') is False:
        return True
    fields = _validation_error_fields() + _validation_warning_fields()
    return any(_is_populated(summary.get(field)) for field in fields)


def _warning_error_lines(text: str) -> list[str]:
    lines = []
    for raw_line in _clean_output(text).splitlines():
        line = raw_line.strip()
        if not line or 'VALIDATION_SUMMARY_JSON:' in line:
            continue
        lowered = line.lower()
        if re.search(r'\bwarning\b', lowered) or re.search(r'\berror\b', lowered):
            lines.append(line)
    return lines


def _generator_record_label(record) -> str | None:
    if isinstance(record, str):
        value = record.strip()
        return value or None
    if not isinstance(record, dict):
        return None

    generator_id = str(record.get('generator_id') or record.get('id') or '').strip()
    generator_name = str(record.get('generator_name') or record.get('name') or '').strip()
    generator_type = str(record.get('generator_type') or record.get('type') or '').strip()
    node_id = str(record.get('node_id') or '').strip()
    node_name = str(record.get('node_name') or record.get('container_name') or '').strip()

    if not (generator_id or generator_name or generator_type):
        return None

    parts = []
    if generator_id:
        parts.append(f"id={generator_id}")
    if generator_name and generator_name != generator_id:
        parts.append(f"name={generator_name}")
    if generator_type:
        parts.append(f"type={generator_type}")
    node_label = node_name or node_id
    if node_label:
        parts.append(f"node={node_label}")
    return ", ".join(parts)


def _collect_generator_lines(value, lines: list[str]) -> None:
    label = _generator_record_label(value)
    if label:
        lines.append(label)
        return

    if isinstance(value, list):
        for item in value:
            _collect_generator_lines(item, lines)
    elif isinstance(value, dict):
        for key in GENERATOR_SUMMARY_KEYS:
            if key in value:
                _collect_generator_lines(value.get(key), lines)


def _generators_used_lines(*payloads) -> list[str]:
    lines = []
    for payload in payloads:
        if payload is not None:
            _collect_generator_lines(payload, lines)

    deduped = []
    seen = set()
    for line in lines:
        if line in seen:
            continue
        seen.add(line)
        deduped.append(line)
    return deduped


def _build_error_report(spec_name: str, result: dict, timestamp: str | None = None) -> str:
    phase_results = result.get('phase_results') or {}
    exec_phase = phase_results.get('execute') or {}
    artifacts = result.get('artifacts') or {}
    validation_summary = exec_phase.get('validation_summary')
    execute_summary = _read_json_if_available(artifacts.get('execute_summary'))

    output_text = _read_text_if_available(exec_phase.get('log_path'))
    if not output_text:
        output_text = exec_phase.get('stderr_output') or ''
    diagnostic_lines = _warning_error_lines(output_text)
    has_validation_issues = _validation_has_issues(validation_summary)
    run_error = str(result.get('error') or '').strip()

    if not (diagnostic_lines or has_validation_issues or run_error):
        return ''

    metadata = result.get('metadata') or {}
    metrics_spec = (result.get('metrics') or {}).get('spec') or {}
    seed = metadata.get('seed') or metrics_spec.get('seed')
    generator_lines = _generators_used_lines(validation_summary, execute_summary)
    timestamp = timestamp or datetime.datetime.now().isoformat()

    sections = [
        "RUN ERROR SEPARATOR---",
        f"Timestamp: {timestamp}",
        f"Run: {spec_name}",
    ]
    if seed not in (None, ''):
        sections.append(f"Seed: {seed}")
    sections.append("")

    if generator_lines:
        sections.append("--- GENERATORS USED ---")
        sections.extend(f"- {line}" for line in generator_lines)
        sections.append("")

    if isinstance(validation_summary, dict):
        sections.append("--- VALIDATION RESULT ---")
        sections.append(f"ok: {validation_summary.get('ok')}")
        validation_errors = _validation_field_lines(
            validation_summary,
            _validation_error_fields(),
        )
        validation_warnings = _validation_field_lines(
            validation_summary,
            _validation_warning_fields(),
        )
        if validation_errors:
            sections.append("errors:")
            sections.extend(f"- {line}" for line in validation_errors)
        if validation_warnings:
            sections.append("warnings:")
            sections.extend(f"- {line}" for line in validation_warnings)
        sections.append(json.dumps(validation_summary, indent=2, sort_keys=True, default=str))
        sections.append("")

    if diagnostic_lines:
        sections.append("--- WARNING/ERROR OUTPUT ---")
        sections.extend(diagnostic_lines)
        sections.append("")

    if run_error:
        sections.append("--- RUN ERROR ---")
        sections.append(run_error)
        sections.append("")

    return "\n".join(sections).rstrip() + "\n\n"


def _clear_latest_error_files(output_root: str) -> None:
    for file_name in (*COMBINED_ERROR_FILENAMES, LATEST_ERROR_FILENAME):
        path = os.path.join(output_root, file_name)
        if not os.path.exists(path):
            continue
        try:
            os.remove(path)
        except Exception:
            pass


def _write_latest_error_files(output_root: str, report: str) -> None:
    if not report:
        return
    try:
        with open(os.path.join(output_root, LATEST_ERROR_FILENAME), "w", encoding="utf-8") as f_out:
            f_out.write(report)
        for file_name in COMBINED_ERROR_FILENAMES:
            with open(os.path.join(output_root, file_name), "a", encoding="utf-8") as f_out:
                f_out.write("\n" + report)
    except Exception:
        pass


class BatchStatusFooter:
    def __init__(
        self,
        total_iterations: int,
        target_phase: str,
        output_root: str,
        stream=None,
        use_color: bool | None = None,
    ):
        self.total_iterations = total_iterations
        self.target_phase = target_phase
        self.output_root = output_root
        self.stream = stream or sys.stdout
        self.use_color = _supports_color(self.stream) if use_color is None else use_color
        self.started_at = time.monotonic()
        self.completed = 0
        self.successes = 0
        self.failures = 0
        self.current_name: str | None = None
        self.current_seed: int | None = None
        self.last_failure: str | None = None

    def start_iteration(self, spec_name: str, seed: int) -> None:
        self.current_name = spec_name
        self.current_seed = seed
        self.render("running")

    def finish_iteration(self, spec_name: str, result: dict) -> None:
        self.completed += 1
        if result.get('success'):
            self.successes += 1
        else:
            self.failures += 1
            failed_stage = _first_failed_stage(result) or result.get('failed_at') or 'unknown stage'
            self.last_failure = f"{spec_name} ({failed_stage})"

        self.current_name = None
        self.current_seed = None
        self.render("failed" if not result.get('success') else "running")

    def stop(self) -> None:
        self.current_name = None
        self.current_seed = None
        self.render("stopped")

    def complete(self) -> None:
        self.current_name = None
        self.current_seed = None
        self.render("done" if self.failures == 0 else "stopped")

    def render(self, state: str) -> None:
        line = self._line(state)
        print(line, file=self.stream, flush=True)

    def _line(self, state: str) -> str:
        pending = max(0, self.total_iterations - self.completed)
        elapsed = _format_elapsed(time.monotonic() - self.started_at)
        pass_rate = "--" if self.completed == 0 else f"{(self.successes / self.completed) * 100:.0f}%"
        badge_color = {
            "running": "36;1",
            "failed": "31;1",
            "stopped": "33;1",
            "done": "32;1",
            "ready": "34;1",
        }.get(state, "36;1")

        parts = [
            _paint(f"[{state.upper()}]", badge_color, self.use_color),
            _paint(f"runs {self.completed}/{self.total_iterations}", "36;1", self.use_color),
            _paint(f"ok {self.successes}", "32;1", self.use_color),
            _paint(f"fail {self.failures}", "31;1" if self.failures else "2", self.use_color),
            f"pending {pending}",
            f"pass {pass_rate}",
            f"elapsed {elapsed}",
            f"phase {self.target_phase}",
        ]

        if self.current_name:
            current = f"current {self.current_name}"
            if self.current_seed is not None:
                current = f"{current} seed={self.current_seed}"
            parts.append(_paint(current, "33;1", self.use_color))
        if self.last_failure:
            parts.append(_paint(f"last failure {self.last_failure}", "31", self.use_color))

        return " | ".join(parts)


def resolve_target_phase(args: argparse.Namespace) -> str:
    if args.execute:
        return 'execute'
    if args.flag_sequencing:
        return 'flag-sequencing'
    if args.topology:
        return 'topology'
    return 'execute'

def main():
    parser = argparse.ArgumentParser(description="ScenarioForge Batch Evaluator")
    parser.add_argument('spec_path', help="Path to a specific .spec.yaml file, or a directory containing them")
    parser.add_argument('--sf-path', required=True, help="Path to the scenarioforge codebase")
    
    phase_group = parser.add_mutually_exclusive_group()
    phase_group.add_argument("--topology", action="store_true",
                             help="Run ScenarioForge's topo phase and stop after the CORE topology is built")
    phase_group.add_argument("--flag-sequencing", action="store_true",
                             help="Run preview-plan and flag-sequencing, then stop before execute")
    phase_group.add_argument("--execute", action="store_true",
                             help="Run the full evaluator pipeline: preview-plan, optional flag-sequencing, and execute")
    
    parser.add_argument('--out', default="/tmp/scenarioforge-eval-out", help="Output directory for logs and results")
    parser.add_argument('--verbose', '-v', action='store_true', help="Enable verbose debug logging")
    parser.add_argument(
        '--stop-on-error',
        action='store_true',
        help="Stop the batch execution if a single run fails"
    )
    parser.add_argument(
        '--dangerous-cleanup-between-runs',
        action='store_true',
        help=(
            "Before each runtime run, call ScenarioForge's dangerous remote Docker cleanup "
            "while holding the shared VM lock. This removes all Docker containers, images, "
            "build cache, and unused volumes/networks on the configured remote CORE host."
        ),
    )
    args = parser.parse_args()

    if args.verbose:
        logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')
        # Suppress paramiko debug logging (SSH channels, EOF, packet tracing) 
        # so it doesn't flood the console, matching WebUI behavior.
        logging.getLogger("paramiko").setLevel(logging.CRITICAL)
    else:
        logging.basicConfig(level=logging.INFO, format='%(message)s')
        # Also suppress in normal mode to prevent connection reset error logs
        logging.getLogger("paramiko").setLevel(logging.CRITICAL)

    output_root = os.path.abspath(os.path.expanduser(args.out))
    os.makedirs(output_root, exist_ok=True)
    reporter = Reporter(output_root)
    
    _clear_latest_error_files(output_root)

    if os.path.isfile(args.spec_path):
        spec_files = [args.spec_path]
    elif os.path.isdir(args.spec_path):
        spec_files = glob.glob(os.path.join(args.spec_path, '*.spec.yaml'))
    else:
        print(f"Path does not exist: {args.spec_path}")
        return

    if not spec_files:
        print(f"No .spec.yaml files found for {args.spec_path}")
        return

    target_phase = resolve_target_phase(args)
    spec_entries = [(spec_file, SpecParser(spec_file)) for spec_file in spec_files]
    total_iterations = sum(_spec_iterations(spec) for _, spec in spec_entries)
    footer = BatchStatusFooter(total_iterations, target_phase, output_root)
    footer.render("ready")
    batch_results = []

    for spec_file, spec in spec_entries:
        print(f"Evaluating {spec_file}...")
        
        iterations = _spec_iterations(spec)
        for i in range(iterations):
            spec_name = spec.get_name()
            if iterations > 1:
                spec_name = f"{spec_name}_run{i+1}"
            
            spec_out_dir = os.path.join(output_root, spec_name)
            iteration_seed = random.SystemRandom().randint(0, 2**31 - 1)
            iteration_rng = random.Random(iteration_seed)
            
            # Resolve the spec dynamically on each iteration to generate random variations
            resolved_spec = {
                'name': spec_name,
                'seed': iteration_seed,
                'topology': spec.get_topology_spec(rng=iteration_rng),
                'services': spec.get_services_spec(rng=iteration_rng),
                'vulns': spec.get_vulns_spec(rng=iteration_rng),
                'flows': spec.get_flows_spec(rng=iteration_rng),
                'segmentation': spec.get_segmentation_spec(),
                'hitl': spec.get_hitl_spec(),
                'validation': spec.get_validation_spec(),
            }
            
            footer.start_iteration(spec_name, iteration_seed)
            
            executor = Executor(
                resolved_spec,
                spec_out_dir,
                args.sf_path,
                target_phase,
                args.verbose,
                dangerous_cleanup_between_runs=args.dangerous_cleanup_between_runs,
            )
            result = executor.run()
            result.setdefault('metadata', {}).update({
                'spec_file': os.path.abspath(spec_file),
                'spec_name': spec_name,
                'iteration_index': i + 1,
                'iteration_count': iterations,
                'target_phase': target_phase,
            })
            batch_results.append(result)
            
            _write_latest_error_files(output_root, _build_error_report(spec_name, result))
            
            reporter.log_result(spec_name, result)
            footer.finish_iteration(spec_name, result)
            
            if not result['success']:
                if args.stop_on_error:
                    print(f"\n[FATAL] Evaluation failed for {spec_name}. Stopping batch execution.")
                    footer.stop()
                    reporter.write_batch_metrics(batch_results)
                    sys.exit(1)
                else:
                    print(f"\n[ERROR] Evaluation failed for {spec_name}. Continuing to next run...")

    footer.complete()
    reporter.write_batch_metrics(batch_results)

if __name__ == '__main__':
    main()

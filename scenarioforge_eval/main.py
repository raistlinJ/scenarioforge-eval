import argparse
import os
import glob
import logging
import random
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
    
    combined_errors_path = os.path.join(output_root, "combined_latest.errors")
    if os.path.exists(combined_errors_path):
        try:
            os.remove(combined_errors_path)
        except Exception:
            pass

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
            
            exec_phase = result.get('phase_results', {}).get('execute', {})
            stderr_text = exec_phase.get('stderr_output', '')
            
            validation_errors = []
            val_summary = exec_phase.get('validation_summary')
            if val_summary:
                for field in executor.VALIDATION_ERROR_FIELDS:
                    if val_summary.get(field):
                        validation_errors.append(f"{field}: {val_summary[field]}")
                        
            if stderr_text or validation_errors:
                import datetime
                try:
                    with open(combined_errors_path, "a", encoding="utf-8") as f_out:
                        f_out.write(f"\nRUN ERROR SEPARATOR---\n")
                        f_out.write(f"Timestamp: {datetime.datetime.now().isoformat()}\n")
                        f_out.write(f"Run: {spec_name}\n\n")
                        if stderr_text:
                            f_out.write("--- STDERR ---\n")
                            f_out.write(stderr_text.strip() + "\n\n")
                        if validation_errors:
                            f_out.write("--- VALIDATION ERRORS ---\n")
                            f_out.write("\n".join(validation_errors) + "\n\n")
                except Exception:
                    pass
            
            reporter.log_result(spec_name, result)
            footer.finish_iteration(spec_name, result)
            
            if not result['success']:
                if args.stop_on_error:
                    print(f"\n[FATAL] Evaluation failed for {spec_name}. Stopping batch execution.")
                    footer.stop()
                    sys.exit(1)
                else:
                    print(f"\n[ERROR] Evaluation failed for {spec_name}. Continuing to next run...")

    footer.complete()

if __name__ == '__main__':
    main()

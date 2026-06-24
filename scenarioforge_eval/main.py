import argparse
import os
import glob
import logging
import random

try:
    from .parser import SpecParser
    from .executor import Executor
    from .reporter import Reporter
except ImportError:
    from parser import SpecParser
    from executor import Executor
    from reporter import Reporter


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

    for spec_file in spec_files:
        print(f"Evaluating {spec_file}...")
        spec = SpecParser(spec_file)
        
        iterations = spec.spec.get('iterations', 1)
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
            
            target_phase = resolve_target_phase(args)
            
            executor = Executor(
                resolved_spec,
                spec_out_dir,
                args.sf_path,
                target_phase,
                args.verbose,
                dangerous_cleanup_between_runs=args.dangerous_cleanup_between_runs,
            )
            result = executor.run()
            
            reporter.log_result(spec_name, result)
            
            if not result['success']:
                print(f"\n[FATAL] Evaluation failed for {spec_name}. Stopping batch execution.")
                import sys
                sys.exit(1)

if __name__ == '__main__':
    main()

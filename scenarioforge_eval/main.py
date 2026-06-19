import argparse
import os
import glob
import logging
from parser import SpecParser
from executor import Executor
from reporter import Reporter

def main():
    parser = argparse.ArgumentParser(description="ScenarioForge Batch Evaluator")
    parser.add_argument('spec_path', help="Path to a specific .spec.yaml file, or a directory containing them")
    parser.add_argument('--sf-path', required=True, help="Path to the scenarioforge codebase")
    
    phase_group = parser.add_mutually_exclusive_group()
    phase_group.add_argument("--topology", action="store_true",
                             help="Stop after topology XML generation (local only)")
    phase_group.add_argument("--flag-sequencing", action="store_true",
                             help="Generate full preview + push artifacts to CORE VM via SSH (stops before execution)")
    phase_group.add_argument("--execute", action="store_true",
                             help="Full pipeline: topology, flag-sequencing, and execute on CORE VM")
    
    parser.add_argument('--out', default="/tmp/scenarioforge-eval-out", help="Output directory for logs and results")
    parser.add_argument('--verbose', '-v', action='store_true', help="Enable verbose debug logging")
    args = parser.parse_args()

    if args.verbose:
        logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')
        # Suppress paramiko debug logging (SSH channels, EOF, packet tracing) 
        # so it doesn't flood the console, matching WebUI behavior.
        logging.getLogger("paramiko").setLevel(logging.WARNING)
    else:
        logging.basicConfig(level=logging.INFO, format='%(message)s')

    os.makedirs(args.out, exist_ok=True)
    reporter = Reporter(args.out)

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
            
            spec_out_dir = os.path.join(args.out, spec_name)
            
            # Resolve the spec dynamically on each iteration to generate random variations
            resolved_spec = {
                'name': spec_name,
                'topology': spec.get_topology_spec(),
                'services': spec.get_services_spec(),
                'vulns': spec.get_vulns_spec(),
                'flows': spec.get_flows_spec(),
                'segmentation': spec.get_segmentation_spec(),
                'hitl': spec.get_hitl_spec(),
            }
            
            if args.execute: target_phase = 'execute'
            elif args.flag_sequencing: target_phase = 'flag-sequencing'
            elif args.topology: target_phase = 'topology'
            else: target_phase = 'flag-sequencing'
            
            executor = Executor(resolved_spec, spec_out_dir, args.sf_path, target_phase, args.verbose)
            result = executor.run()
            
            reporter.log_result(spec_name, result)
            
            if not result['success']:
                print(f"\n[FATAL] Evaluation failed for {spec_name}. Stopping batch execution.")
                import sys
                sys.exit(1)

if __name__ == '__main__':
    main()

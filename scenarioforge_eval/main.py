import argparse
import os
import glob
from parser import SpecParser
from executor import Executor
from reporter import Reporter

def main():
    parser = argparse.ArgumentParser(description="ScenarioForge Batch Evaluator")
    parser.add_argument('spec_dir', help="Directory containing .spec.yaml files")
    parser.add_argument('--out', default="/tmp/scenarioforge-eval-out", help="Output directory for logs and results")
    args = parser.parse_args()

    os.makedirs(args.out, exist_ok=True)
    reporter = Reporter(args.out)

    spec_files = glob.glob(os.path.join(args.spec_dir, '*.spec.yaml'))
    if not spec_files:
        print(f"No .spec.yaml files found in {args.spec_dir}")
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
            }
            
            executor = Executor(resolved_spec, spec_out_dir)
            result = executor.run()
            
            reporter.log_result(spec_name, result)

if __name__ == '__main__':
    main()

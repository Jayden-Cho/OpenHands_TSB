# evaluation/run_swebench_eval.py
import asyncio
from datasets import load_dataset
from adapters.swebench_adapter import SWEBenchAdapter
from core.logger import Logger
import json
import argparse
from pathlib import Path
from dotenv import load_dotenv
import os
import pytest
import subprocess
import time

# Initialize logger
logger = Logger.get_logger()

async def run_evaluation(dataset, single_test=True, instance_id=None):
    """
    Run SWE-bench evaluation
    Args:
        dataset: The loaded SWE-bench dataset
        single_test: If True, run only one test case
        instance_id: Specific instance to test (e.g., 'sympy__sympy-20590')
    """
    load_dotenv()  # Load API key before evaluation starts
    api_key = os.getenv('ANTHROPIC_API_KEY')
    if not api_key:
        raise ValueError("ANTHROPIC_API_KEY not found in environment variables")
    
    # Print first instance keys and data
    print("Available keys:", dataset[0].keys())
    print("First instance data:", json.dumps(dataset[0], indent=2))
    
    # Initialize adapter
    adapter = SWEBenchAdapter(max_iterations=30)
    
    results = []
    
    if single_test:
        # Use specified instance or first instance
        if instance_id:
            instance = next(x for x in dataset if x['instance_id'] == instance_id)
        else:
            instance = dataset[0]
            
        print(f"Testing single instance: {instance['instance_id']}")
        result = await adapter.process_swebench_instance(instance)
        results.append(result)
        
    else:
        # Run full evaluation
        print("Running full evaluation...")
        for instance in dataset:
            try:
                result = await adapter.process_swebench_instance(instance)
                results.append(result)
                print(f"Processed {instance['instance_id']}")
            except Exception as e:
                print(f"Error processing {instance['instance_id']}: {e}")
            print("Waiting 60 seconds before next iteration...")
            time.sleep(60)
    return results

def run_specific_test(test_path):
    """
    Run a specific test using pytest
    Args:
        test_path: Path in format 'path/to/test.py::test_name'
    Returns:
        bool: True if test passed, False otherwise
    """
    try:
        # Run pytest with specific test
        result = subprocess.run(['pytest', test_path], 
                              capture_output=True,
                              text=True)
        return result.returncode == 0
    except Exception as e:
        print(f"Error running test {test_path}: {e}")
        return False

def evaluate_test_results(instance_id, results, expected):
    """
    Evaluate test results for an instance
    Returns: dict with test results
    """
    # Default to False
    passing_tests_ok = False
    failing_tests_fixed = False
    
    try:
        # Get test lists
        pass_to_pass = json.loads(expected.get('PASS_TO_PASS', '[]'))
        fail_to_pass = json.loads(expected.get('FAIL_TO_PASS', '[]'))
        
        # Check if passing tests still pass
        passing_tests_results = [run_specific_test(test) for test in pass_to_pass]
        passing_tests_ok = all(passing_tests_results)
        
        # Check if failing tests now pass
        failing_tests_results = [run_specific_test(test) for test in fail_to_pass]
        failing_tests_fixed = all(failing_tests_results)
        
    except Exception as e:
        print(f"Error evaluating tests for {instance_id}: {e}")
    
    return {
        "instance_id": instance_id,
        "passing_tests_ok": passing_tests_ok,
        "failing_tests_fixed": failing_tests_fixed,
        "details": {
            "pass_to_pass_results": dict(zip(pass_to_pass, passing_tests_results)),
            "fail_to_pass_results": dict(zip(fail_to_pass, failing_tests_results))
        }
    }

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Run SWE-bench evaluation')
    parser.add_argument('--full', action='store_true', help='Run full evaluation instead of single test')
    parser.add_argument('--instance_id', type=str, help='Specific instance ID to test')
    parser.add_argument('--num_instances', type=int, default=1, 
                       help='Number of instances to test (default: 1)')
    
    args = parser.parse_args()
    
    # Load dataset once here
    dataset = load_dataset('princeton-nlp/SWE-bench', split='test')
    
    # If full evaluation, limit to specified number of instances
    if args.full:
        dataset = dataset.select(range(args.num_instances))
    
    # Clean out evaluation results directory
    output_dir = Path("evaluation_results")
    output_dir.mkdir(exist_ok=True)

    # Remove old files if they exist
    expected_file = output_dir / "expected_solutions.json"
    results_file = output_dir / "single_test.json"
    if expected_file.exists():
        expected_file.unlink()
    if results_file.exists():
        results_file.unlink()

    # Save expected solutions using the loaded dataset
    expected_solutions = [{
        "instance_id": instance["instance_id"],
        "patch": instance["patch"]
        #"test_patch": instance["test_patch"],
    } for instance in dataset]

    with open(expected_file, 'w') as f:
        json.dump(expected_solutions, f, indent=2)

    # Run evaluation with the loaded dataset
    results = asyncio.run(run_evaluation(
        dataset=dataset,
        single_test=not args.full,
        instance_id=args.instance_id
    ))
    with open(results_file, 'w') as f:
        json.dump(results, f, indent=2)
        
    print(f"\nResults saved to {results_file}")

    '''
    # In main block after saving results:
    evaluation_results = []
    total_instances = 0
    successful_instances = 0

    # Evaluate each instance
    for instance in dataset[:args.num_instances]:
        result = evaluate_test_results(
            instance["instance_id"],
            results,
            instance
        )
        evaluation_results.append(result)
        
        total_instances += 1
        if result["passing_tests_ok"] and result["failing_tests_fixed"]:
            successful_instances += 1

    # Save evaluation results
    eval_file = output_dir / "evaluation_metrics.json"
    with open(eval_file, 'w') as f:
        json.dump({
            "detailed_results": evaluation_results,
            "accuracy": successful_instances / total_instances if total_instances > 0 else 0,
            "total_instances": total_instances,
            "successful_instances": successful_instances
        }, f, indent=2)

    print(f"\nEvaluation results saved to {eval_file}")
    print(f"Accuracy: {successful_instances}/{total_instances} = {successful_instances/total_instances:.2%}")
    '''
    exit(0)
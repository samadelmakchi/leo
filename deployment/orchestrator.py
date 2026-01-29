# deployment/orchestrator.py
import logging
from pathlib import Path
from typing import Dict, List, Any, Optional
from datetime import datetime
import importlib
import sys

from deployment.config import DeploymentConfig

logger = logging.getLogger(__name__)


class TaskOrchestrator:
    """Orchestrator for managing deployment tasks"""
    
    def __init__(self, config: DeploymentConfig = None):
        """
        Initialize orchestrator
        
        Args:
            config: DeploymentConfig instance
        """
        self.config = config or DeploymentConfig()
        self.tasks_dir = Path(__file__).parent / "tasks"
        self.results = {}
        self.execution_order = []
        
    def load_task(self, task_name: str):
        """
        Load a task module
        
        Args:
            task_name: Name of the task module (e.g., "task_00_network")
            
        Returns:
            Task module
        """
        try:
            # Add tasks directory to path
            tasks_path = str(self.tasks_dir.parent)
            if tasks_path not in sys.path:
                sys.path.insert(0, tasks_path)
            
            module_name = f"deployment.tasks.{task_name}"
            return importlib.import_module(module_name)
            
        except ImportError as e:
            logger.error(f"Error loading task {task_name}: {str(e)}")
            return None
    
    def get_task_sequence(self, tags: List[str] = None) -> List[str]:
        """
        Get sequence of tasks to execute based on tags
        
        Args:
            tags: List of tags to filter tasks
            
        Returns:
            List of task module names
        """
        # Default task sequence (from your Ansible playbook)
        default_sequence = [
            "task_00_network",
            "task_01_down_state", 
            "task_02_create_dirs",
            "task_03_define_projects",
            "task_04_ensure_project_dirs",
            "task_05_ensure_gateway_docker_init",
            "task_06_update_services",
            "task_07_config_files",
            "task_08_sql_and_uploads",
            "task_09_pre_deploy_backup",
            "task_10_pre_pull_images",
            "task_11_build_customer_images",
            "task_12_deploy_containers",
            "task_13_run_migrations",
            "task_14_write_info_files",
            "task_15_copy_backup_scripts",
            "task_16_setup_cron",
            "task_20_run_tests"
        ]
        
        if not tags or 'always' in tags:
            return default_sequence
        
        # Filter tasks based on tags
        # This needs to be implemented based on how tasks are tagged
        # For now, return all tasks if tags are specified
        return default_sequence
    
    def execute_task(self, task_name: str, hostname: str = None, **kwargs) -> Dict[str, Any]:
        """
        Execute a single task
        
        Args:
            task_name: Name of the task module
            hostname: Specific host to execute on
            **kwargs: Additional arguments for the task
            
        Returns:
            Task execution results
        """
        logger.info(f"Executing task: {task_name}")
        
        task_module = self.load_task(task_name)
        if not task_module:
            return {'success': False, 'error': f'Task {task_name} not found'}
        
        try:
            # Get task config
            task_config = self.config.get_task_config(task_name, hostname)
            task_config.update(kwargs)
            
            # Execute task
            if hasattr(task_module, 'execute'):
                result = task_module.execute(task_config)
            elif hasattr(task_module, 'run'):
                result = task_module.run(task_config)
            else:
                result = {'success': False, 'error': f'No execute/run method in {task_name}'}
            
            # Store result
            self.results[task_name] = {
                'timestamp': datetime.now().isoformat(),
                'hostname': hostname,
                'result': result
            }
            
            logger.info(f"Task {task_name} completed: {result.get('success', False)}")
            return result
            
        except Exception as e:
            error_msg = f"Error executing task {task_name}: {str(e)}"
            logger.error(error_msg)
            result = {'success': False, 'error': error_msg}
            self.results[task_name] = {
                'timestamp': datetime.now().isoformat(),
                'hostname': hostname,
                'result': result
            }
            return result
    
    def execute_pipeline(self, hostname: str = None, tags: List[str] = None, 
                        start_from: str = None, stop_at: str = None) -> Dict[str, Any]:
        """
        Execute a pipeline of tasks
        
        Args:
            hostname: Specific host to execute on
            tags: Filter tasks by tags
            start_from: Start from specific task
            stop_at: Stop at specific task
            
        Returns:
            Overall execution results
        """
        logger.info(f"Starting pipeline execution for host: {hostname or 'all'}")
        
        # Get task sequence
        task_sequence = self.get_task_sequence(tags)
        
        # Apply start/stop filters
        if start_from:
            try:
                start_index = task_sequence.index(start_from)
                task_sequence = task_sequence[start_index:]
            except ValueError:
                logger.warning(f"Task {start_from} not found in sequence")
        
        if stop_at:
            try:
                stop_index = task_sequence.index(stop_at) + 1
                task_sequence = task_sequence[:stop_index]
            except ValueError:
                logger.warning(f"Task {stop_at} not found in sequence")
        
        # Execute tasks
        results = {}
        for task_name in task_sequence:
            result = self.execute_task(task_name, hostname)
            results[task_name] = result
            
            # Stop if task failed and we're not ignoring failures
            if not result.get('success', False) and not kwargs.get('ignore_failures', False):
                logger.error(f"Pipeline stopped due to failure in task: {task_name}")
                break
        
        # Summary
        success_count = sum(1 for r in results.values() if r.get('success', False))
        total_count = len(results)
        
        summary = {
            'success': success_count == total_count,
            'total_tasks': total_count,
            'successful_tasks': success_count,
            'failed_tasks': total_count - success_count,
            'results': results,
            'execution_order': task_sequence
        }
        
        logger.info(f"Pipeline completed: {success_count}/{total_count} tasks successful")
        return summary
    
    def execute_for_customer(self, customer_name: str, **kwargs) -> Dict[str, Any]:
        """
        Execute pipeline for a specific customer
        
        Args:
            customer_name: Name of the customer
            **kwargs: Additional arguments for pipeline
            
        Returns:
            Execution results
        """
        logger.info(f"Executing pipeline for customer: {customer_name}")
        
        # Get customer details from CSV
        customers = self.load_customers()
        customer = customers.get(customer_name)
        
        if not customer:
            return {'success': False, 'error': f'Customer {customer_name} not found'}
        
        # Set up environment for this customer
        hostname = customer.get('host')
        
        # Execute pipeline
        return self.execute_pipeline(hostname=hostname, **kwargs)
    
    def load_customers(self) -> Dict[str, Dict[str, Any]]:
        """
        Load customers from CSV file
        
        Returns:
            Dictionary of customers
        """
        import csv
        from pathlib import Path
        
        customers_file = Path(__file__).parent / "resources" / "customer.csv"
        customers = {}
        
        try:
            with open(customers_file, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    customer_name = row['customer_name']
                    customers[customer_name] = row
            
            logger.info(f"Loaded {len(customers)} customers from CSV")
            return customers
            
        except Exception as e:
            logger.error(f"Error loading customers CSV: {str(e)}")
            return {}
    
    def add_customer(self, customer_data: Dict[str, Any]) -> bool:
        """
        Add a new customer to CSV
        
        Args:
            customer_data: Customer data dictionary
            
        Returns:
            True if successful
        """
        import csv
        from pathlib import Path
        
        customers_file = Path(__file__).parent / "resources" / "customer.csv"
        
        try:
            # Read existing customers
            customers = self.load_customers()
            
            # Add new customer
            customer_name = customer_data.get('customer_name')
            if not customer_name:
                return False
            
            customers[customer_name] = customer_data
            
            # Write back to CSV
            fieldnames = []
            if customers_file.exists():
                with open(customers_file, 'r', encoding='utf-8') as f:
                    reader = csv.DictReader(f)
                    fieldnames = reader.fieldnames
            
            if not fieldnames:
                fieldnames = list(customer_data.keys())
            
            with open(customers_file, 'w', encoding='utf-8', newline='') as f:
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writeheader()
                for customer in customers.values():
                    writer.writerow(customer)
            
            logger.info(f"Added customer: {customer_name}")
            return True
            
        except Exception as e:
            logger.error(f"Error adding customer: {str(e)}")
            return False
    
    def get_execution_report(self) -> Dict[str, Any]:
        """
        Get detailed execution report
        
        Returns:
            Execution report
        """
        return {
            'timestamp': datetime.now().isoformat(),
            'total_executions': len(self.results),
            'results': self.results,
            'success_rate': self.calculate_success_rate()
        }
    
    def calculate_success_rate(self) -> float:
        """Calculate success rate of executions"""
        if not self.results:
            return 0.0
        
        successful = sum(1 for r in self.results.values() 
                        if r['result'].get('success', False))
        return successful / len(self.results) * 100


def main():
    """Main entry point for CLI"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Deployment Orchestrator')
    parser.add_argument('--customer', help='Customer name to deploy')
    parser.add_argument('--host', help='Hostname to deploy to')
    parser.add_argument('--task', help='Specific task to execute')
    parser.add_argument('--tags', help='Comma-separated list of tags')
    parser.add_argument('--list-tasks', action='store_true', help='List available tasks')
    parser.add_argument('--add-customer', help='Add new customer (provide JSON file)')
    
    args = parser.parse_args()
    
    # Initialize orchestrator
    orchestrator = TaskOrchestrator()
    
    if args.list_tasks:
        tasks = orchestrator.get_task_sequence()
        print("Available tasks:")
        for task in tasks:
            print(f"  - {task}")
    
    elif args.add_customer:
        import json
        with open(args.add_customer, 'r') as f:
            customer_data = json.load(f)
        success = orchestrator.add_customer(customer_data)
        print(f"Customer added: {success}")
    
    elif args.task:
        result = orchestrator.execute_task(args.task, args.host)
        print(f"Task result: {result}")
    
    elif args.customer or args.host:
        tags = args.tags.split(',') if args.tags else None
        result = orchestrator.execute_pipeline(
            hostname=args.host,
            tags=tags
        )
        print(f"Pipeline result: {result}")
    
    else:
        parser.print_help()


if __name__ == '__main__':
    main()
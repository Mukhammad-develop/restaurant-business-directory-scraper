"""Scheduler for automated scraping tasks."""

import schedule
import time
import threading
from datetime import datetime, timedelta
from typing import Dict, Any, Callable, Optional
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
import json
from pathlib import Path

from src.config import config
from src.models import SearchFilter
from src.scraper_manager import ScraperManager
from src.processors.data_processor import DataProcessor
from src.exporters.data_exporter import DataExporter
from src.utils.logger import get_logger

class TaskScheduler:
    """Manages scheduled scraping tasks."""
    
    def __init__(self):
        self.logger = get_logger(__name__)
        self.config = config
        self.scheduler = BackgroundScheduler()
        self.tasks = {}
        self.is_running = False
        
        # Create tasks directory
        self.tasks_dir = Path("data/tasks")
        self.tasks_dir.mkdir(parents=True, exist_ok=True)
        
    def start(self):
        """Start the scheduler."""
        if not self.is_running:
            self.scheduler.start()
            self.is_running = True
            self.logger.info("📅 Task scheduler started")
        
    def stop(self):
        """Stop the scheduler."""
        if self.is_running:
            self.scheduler.shutdown(wait=False)
            self.is_running = False
            self.logger.info("📅 Task scheduler stopped")
    
    def add_recurring_task(self, task_id: str, search_filter: SearchFilter, 
                          frequency: str = "daily", time: str = "02:00",
                          platforms: list = None, export_formats: list = None) -> bool:
        """Add a recurring scraping task."""
        try:
            # Default values
            platforms = platforms or ["yelp", "google_maps"]
            export_formats = export_formats or ["csv"]
            
            # Create task function
            task_func = self._create_task_function(task_id, search_filter, platforms, export_formats)
            
            # Parse frequency and time
            trigger = self._parse_schedule(frequency, time)
            
            # Add job to scheduler
            job = self.scheduler.add_job(
                task_func,
                trigger=trigger,
                id=task_id,
                name=f"Scraping Task: {task_id}",
                replace_existing=True,
                max_instances=1  # Prevent overlapping executions
            )
            
            # Store task configuration
            task_config = {
                'task_id': task_id,
                'search_filter': search_filter.to_dict(),
                'frequency': frequency,
                'time': time,
                'platforms': platforms,
                'export_formats': export_formats,
                'created_at': datetime.now().isoformat(),
                'last_run': None,
                'next_run': job.next_run_time.isoformat() if job.next_run_time else None,
                'status': 'active'
            }
            
            self.tasks[task_id] = task_config
            self._save_task_config(task_id, task_config)
            
            self.logger.info(f"✅ Recurring task added: {task_id} ({frequency} at {time})")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to add recurring task {task_id}: {str(e)}")
            return False
    
    def add_one_time_task(self, task_id: str, search_filter: SearchFilter,
                         run_time: datetime, platforms: list = None, 
                         export_formats: list = None) -> bool:
        """Add a one-time scraping task."""
        try:
            platforms = platforms or ["yelp", "google_maps"]
            export_formats = export_formats or ["csv"]
            
            # Create task function
            task_func = self._create_task_function(task_id, search_filter, platforms, export_formats)
            
            # Add job to scheduler
            job = self.scheduler.add_job(
                task_func,
                'date',
                run_date=run_time,
                id=task_id,
                name=f"One-time Task: {task_id}",
                replace_existing=True
            )
            
            # Store task configuration
            task_config = {
                'task_id': task_id,
                'search_filter': search_filter.to_dict(),
                'run_time': run_time.isoformat(),
                'platforms': platforms,
                'export_formats': export_formats,
                'created_at': datetime.now().isoformat(),
                'task_type': 'one_time',
                'status': 'scheduled'
            }
            
            self.tasks[task_id] = task_config
            self._save_task_config(task_id, task_config)
            
            self.logger.info(f"✅ One-time task scheduled: {task_id} for {run_time}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to add one-time task {task_id}: {str(e)}")
            return False
    
    def remove_task(self, task_id: str) -> bool:
        """Remove a scheduled task."""
        try:
            self.scheduler.remove_job(task_id)
            
            if task_id in self.tasks:
                self.tasks[task_id]['status'] = 'cancelled'
                self._save_task_config(task_id, self.tasks[task_id])
                del self.tasks[task_id]
            
            self.logger.info(f"✅ Task removed: {task_id}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to remove task {task_id}: {str(e)}")
            return False
    
    def get_task_status(self, task_id: str) -> Optional[Dict[str, Any]]:
        """Get status of a specific task."""
        if task_id in self.tasks:
            task_config = self.tasks[task_id].copy()
            
            # Get job info from scheduler
            try:
                job = self.scheduler.get_job(task_id)
                if job:
                    task_config['next_run'] = job.next_run_time.isoformat() if job.next_run_time else None
                    task_config['job_status'] = 'scheduled'
                else:
                    task_config['job_status'] = 'not_found'
            except:
                task_config['job_status'] = 'error'
            
            return task_config
        
        return None
    
    def list_tasks(self) -> Dict[str, Dict[str, Any]]:
        """List all tasks."""
        return self.tasks.copy()
    
    def _create_task_function(self, task_id: str, search_filter: SearchFilter, 
                             platforms: list, export_formats: list) -> Callable:
        """Create a task function for the scheduler."""
        def task_function():
            self.logger.info(f"🚀 Starting scheduled task: {task_id}")
            
            try:
                # Update task status
                if task_id in self.tasks:
                    self.tasks[task_id]['status'] = 'running'
                    self.tasks[task_id]['last_run'] = datetime.now().isoformat()
                    self._save_task_config(task_id, self.tasks[task_id])
                
                # Initialize components
                scraper_manager = ScraperManager()
                processor = DataProcessor()
                exporter = DataExporter()
                
                # Perform scraping
                self.logger.info(f"🔍 Scraping with task {task_id}")
                businesses = scraper_manager.search_all_platforms(search_filter, platforms)
                
                if not businesses:
                    self.logger.warning(f"No businesses found for task {task_id}")
                    return
                
                # Process data
                self.logger.info(f"🔧 Processing data for task {task_id}")
                processed_businesses = processor.process_businesses(businesses, search_filter)
                
                if not processed_businesses:
                    self.logger.warning(f"No valid businesses after processing for task {task_id}")
                    return
                
                # Export data
                self.logger.info(f"💾 Exporting data for task {task_id}")
                filename_prefix = f"scheduled_{task_id}"
                export_results = exporter.export_businesses(
                    processed_businesses, export_formats, filename_prefix
                )
                
                # Update task status
                if task_id in self.tasks:
                    self.tasks[task_id]['status'] = 'completed'
                    self.tasks[task_id]['last_export_results'] = export_results
                    self.tasks[task_id]['last_business_count'] = len(processed_businesses)
                    self._save_task_config(task_id, self.tasks[task_id])
                
                self.logger.info(f"✅ Scheduled task completed: {task_id}")
                
                # Log export results
                for format_type, result in export_results.items():
                    self.logger.info(f"📄 {format_type.upper()}: {result}")
                
            except Exception as e:
                self.logger.error(f"❌ Scheduled task failed: {task_id} - {str(e)}")
                
                # Update task status
                if task_id in self.tasks:
                    self.tasks[task_id]['status'] = 'failed'
                    self.tasks[task_id]['last_error'] = str(e)
                    self._save_task_config(task_id, self.tasks[task_id])
        
        return task_function
    
    def _parse_schedule(self, frequency: str, time: str) -> CronTrigger:
        """Parse frequency and time into a cron trigger."""
        hour, minute = time.split(':')
        hour = int(hour)
        minute = int(minute)
        
        if frequency == "daily":
            return CronTrigger(hour=hour, minute=minute)
        elif frequency == "weekly":
            return CronTrigger(day_of_week=0, hour=hour, minute=minute)  # Monday
        elif frequency == "monthly":
            return CronTrigger(day=1, hour=hour, minute=minute)  # First day of month
        elif frequency == "hourly":
            return CronTrigger(minute=minute)
        else:
            raise ValueError(f"Unsupported frequency: {frequency}")
    
    def _save_task_config(self, task_id: str, task_config: Dict[str, Any]):
        """Save task configuration to file."""
        try:
            config_file = self.tasks_dir / f"{task_id}.json"
            with open(config_file, 'w', encoding='utf-8') as f:
                json.dump(task_config, f, indent=2, default=str)
        except Exception as e:
            self.logger.error(f"Failed to save task config for {task_id}: {str(e)}")
    
    def load_saved_tasks(self):
        """Load saved tasks from files."""
        try:
            for config_file in self.tasks_dir.glob("*.json"):
                with open(config_file, 'r', encoding='utf-8') as f:
                    task_config = json.load(f)
                
                task_id = task_config['task_id']
                
                # Only reload active tasks
                if task_config.get('status') == 'active':
                    search_filter = SearchFilter(**task_config['search_filter'])
                    
                    if task_config.get('task_type') == 'one_time':
                        # Skip expired one-time tasks
                        run_time = datetime.fromisoformat(task_config['run_time'])
                        if run_time > datetime.now():
                            self.add_one_time_task(
                                task_id, search_filter, run_time,
                                task_config['platforms'], task_config['export_formats']
                            )
                    else:
                        # Reload recurring tasks
                        self.add_recurring_task(
                            task_id, search_filter,
                            task_config['frequency'], task_config['time'],
                            task_config['platforms'], task_config['export_formats']
                        )
                
                self.tasks[task_id] = task_config
                
            self.logger.info(f"✅ Loaded {len(self.tasks)} saved tasks")
            
        except Exception as e:
            self.logger.error(f"Failed to load saved tasks: {str(e)}")
    
    def get_scheduler_status(self) -> Dict[str, Any]:
        """Get overall scheduler status."""
        jobs = self.scheduler.get_jobs()
        
        return {
            'is_running': self.is_running,
            'total_tasks': len(self.tasks),
            'active_jobs': len(jobs),
            'next_run_time': min([job.next_run_time for job in jobs if job.next_run_time], default=None),
            'tasks': {
                'active': len([t for t in self.tasks.values() if t.get('status') == 'active']),
                'completed': len([t for t in self.tasks.values() if t.get('status') == 'completed']),
                'failed': len([t for t in self.tasks.values() if t.get('status') == 'failed']),
                'cancelled': len([t for t in self.tasks.values() if t.get('status') == 'cancelled'])
            }
        }

# Global scheduler instance
scheduler = TaskScheduler() 
#!/usr/bin/env python3
"""
CLI tool for managing scheduled scraping tasks.
"""

import argparse
import sys
import json
from datetime import datetime, timedelta
from pathlib import Path

# Add src to Python path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from src.automation.scheduler import scheduler
from src.models import SearchFilter
from src.utils.logger import get_logger

logger = get_logger(__name__)

def main():
    parser = argparse.ArgumentParser(
        description="Restaurant Directory Scraper - Task Scheduler",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    # Start scheduler command
    start_parser = subparsers.add_parser('start', help='Start the task scheduler')
    start_parser.add_argument('--daemon', action='store_true', help='Run as daemon')
    
    # Stop scheduler command
    subparsers.add_parser('stop', help='Stop the task scheduler')
    
    # Status command
    subparsers.add_parser('status', help='Show scheduler status')
    
    # Add task command
    add_parser = subparsers.add_parser('add', help='Add a new scheduled task')
    add_parser.add_argument('--id', required=True, help='Task ID')
    add_parser.add_argument('--city', required=True, help='City to search')
    add_parser.add_argument('--cuisine', help='Cuisine type')
    add_parser.add_argument('--keywords', help='Search keywords')
    add_parser.add_argument('--min-rating', type=float, help='Minimum rating')
    add_parser.add_argument('--frequency', default='daily', choices=['hourly', 'daily', 'weekly', 'monthly'], help='Task frequency')
    add_parser.add_argument('--time', default='02:00', help='Time to run (HH:MM)')
    add_parser.add_argument('--platforms', default='yelp,google_maps', help='Platforms (comma-separated)')
    add_parser.add_argument('--export', default='csv', help='Export formats (comma-separated)')
    
    # Remove task command
    remove_parser = subparsers.add_parser('remove', help='Remove a scheduled task')
    remove_parser.add_argument('--id', required=True, help='Task ID to remove')
    
    # List tasks command
    subparsers.add_parser('list', help='List all scheduled tasks')
    
    # Show task command
    show_parser = subparsers.add_parser('show', help='Show task details')
    show_parser.add_argument('--id', required=True, help='Task ID')
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    
    try:
        if args.command == 'start':
            start_scheduler(args.daemon)
        elif args.command == 'stop':
            stop_scheduler()
        elif args.command == 'status':
            show_status()
        elif args.command == 'add':
            add_task(args)
        elif args.command == 'remove':
            remove_task(args.id)
        elif args.command == 'list':
            list_tasks()
        elif args.command == 'show':
            show_task(args.id)
    
    except KeyboardInterrupt:
        logger.info("Operation cancelled by user")
    except Exception as e:
        logger.error(f"Error: {str(e)}")
        sys.exit(1)

def start_scheduler(daemon=False):
    """Start the task scheduler."""
    logger.info("🚀 Starting task scheduler...")
    
    # Load saved tasks
    scheduler.load_saved_tasks()
    
    # Start scheduler
    scheduler.start()
    
    if daemon:
        logger.info("📅 Scheduler running in daemon mode")
        try:
            # Keep the script running
            import time
            while True:
                time.sleep(60)  # Sleep for 1 minute
        except KeyboardInterrupt:
            logger.info("Stopping scheduler...")
            scheduler.stop()
    else:
        logger.info("📅 Scheduler started successfully")
        logger.info("Use 'python scheduler_cli.py stop' to stop the scheduler")

def stop_scheduler():
    """Stop the task scheduler."""
    logger.info("⏹️  Stopping task scheduler...")
    scheduler.stop()
    logger.info("✅ Scheduler stopped")

def show_status():
    """Show scheduler status."""
    status = scheduler.get_scheduler_status()
    
    print("\n📊 Scheduler Status")
    print("=" * 50)
    print(f"Running: {'✅ Yes' if status['is_running'] else '❌ No'}")
    print(f"Total Tasks: {status['total_tasks']}")
    print(f"Active Jobs: {status['active_jobs']}")
    
    if status['next_run_time']:
        next_run = datetime.fromisoformat(status['next_run_time'].replace('Z', '+00:00'))
        print(f"Next Run: {next_run.strftime('%Y-%m-%d %H:%M:%S')}")
    else:
        print("Next Run: No scheduled tasks")
    
    print(f"\nTask Status:")
    print(f"  Active: {status['tasks']['active']}")
    print(f"  Completed: {status['tasks']['completed']}")
    print(f"  Failed: {status['tasks']['failed']}")
    print(f"  Cancelled: {status['tasks']['cancelled']}")

def add_task(args):
    """Add a new scheduled task."""
    logger.info(f"Adding scheduled task: {args.id}")
    
    # Create search filter
    search_filter = SearchFilter(
        city=args.city,
        cuisine_type=args.cuisine,
        keywords=args.keywords,
        min_rating=args.min_rating
    )
    
    # Parse platforms and export formats
    platforms = [p.strip() for p in args.platforms.split(',')]
    export_formats = [f.strip() for f in args.export.split(',')]
    
    # Add recurring task
    success = scheduler.add_recurring_task(
        task_id=args.id,
        search_filter=search_filter,
        frequency=args.frequency,
        time=args.time,
        platforms=platforms,
        export_formats=export_formats
    )
    
    if success:
        logger.info(f"✅ Task '{args.id}' added successfully")
        logger.info(f"   Frequency: {args.frequency} at {args.time}")
        logger.info(f"   City: {args.city}")
        if args.cuisine:
            logger.info(f"   Cuisine: {args.cuisine}")
    else:
        logger.error(f"❌ Failed to add task '{args.id}'")

def remove_task(task_id):
    """Remove a scheduled task."""
    logger.info(f"Removing task: {task_id}")
    
    success = scheduler.remove_task(task_id)
    
    if success:
        logger.info(f"✅ Task '{task_id}' removed successfully")
    else:
        logger.error(f"❌ Failed to remove task '{task_id}'")

def list_tasks():
    """List all scheduled tasks."""
    tasks = scheduler.list_tasks()
    
    if not tasks:
        print("\n📋 No scheduled tasks found")
        return
    
    print(f"\n📋 Scheduled Tasks ({len(tasks)} total)")
    print("=" * 80)
    
    for task_id, task_config in tasks.items():
        status_emoji = {
            'active': '🟢',
            'running': '🔵',
            'completed': '✅',
            'failed': '❌',
            'cancelled': '⚪'
        }.get(task_config.get('status', 'unknown'), '❓')
        
        print(f"\n{status_emoji} {task_id}")
        print(f"   Status: {task_config.get('status', 'unknown')}")
        print(f"   City: {task_config['search_filter'].get('city', 'N/A')}")
        
        if task_config.get('frequency'):
            print(f"   Schedule: {task_config['frequency']} at {task_config.get('time', 'N/A')}")
        
        if task_config.get('last_run'):
            last_run = datetime.fromisoformat(task_config['last_run'])
            print(f"   Last Run: {last_run.strftime('%Y-%m-%d %H:%M:%S')}")
        
        if task_config.get('last_business_count'):
            print(f"   Last Result: {task_config['last_business_count']} businesses")

def show_task(task_id):
    """Show detailed task information."""
    task_config = scheduler.get_task_status(task_id)
    
    if not task_config:
        logger.error(f"Task '{task_id}' not found")
        return
    
    print(f"\n📋 Task Details: {task_id}")
    print("=" * 50)
    
    print(f"Status: {task_config.get('status', 'unknown')}")
    print(f"Created: {task_config.get('created_at', 'N/A')}")
    
    if task_config.get('frequency'):
        print(f"Frequency: {task_config['frequency']}")
        print(f"Time: {task_config.get('time', 'N/A')}")
    
    print(f"\nSearch Parameters:")
    search_filter = task_config['search_filter']
    for key, value in search_filter.items():
        if value:
            print(f"  {key}: {value}")
    
    print(f"\nPlatforms: {', '.join(task_config.get('platforms', []))}")
    print(f"Export Formats: {', '.join(task_config.get('export_formats', []))}")
    
    if task_config.get('last_run'):
        print(f"\nLast Run: {task_config['last_run']}")
    
    if task_config.get('next_run'):
        print(f"Next Run: {task_config['next_run']}")
    
    if task_config.get('last_business_count'):
        print(f"Last Result: {task_config['last_business_count']} businesses")
    
    if task_config.get('last_export_results'):
        print(f"\nLast Export Results:")
        for format_type, result in task_config['last_export_results'].items():
            print(f"  {format_type}: {result}")
    
    if task_config.get('last_error'):
        print(f"\nLast Error: {task_config['last_error']}")

if __name__ == "__main__":
    main() 
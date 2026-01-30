#!/usr/bin/env python3
"""Example: Task Engine automation with pyvergeos.

This example demonstrates the VergeOS Task Engine, which enables automated
operations triggered by specific events or scheduled times.

Task Engine Components:
    - Tasks: Define the action to perform (e.g., power off a VM)
    - Schedules: Specify when and how often a task runs
    - Events: Define conditions that trigger a task (e.g., user login)
    - Schedule Triggers: Link tasks to schedules
    - Event Triggers: Link tasks to events

Use Cases Demonstrated:
    1. Power on VMs when a user logs in
    2. Power off VMs when the user logs out
    3. Power off VMs on a schedule (e.g., Friday at 6 PM)
    4. Send notifications on sync errors

Based on VergeOS documentation:
    - product-guide/automation/task-engine.md
    - product-guide/automation/create-tasks.md
"""

from pyvergeos import VergeClient
from pyvergeos.exceptions import NotFoundError


def list_tasks() -> None:
    """List all tasks and their status."""
    print("=== List All Tasks ===")

    with VergeClient(
        host="192.168.1.100",
        username="admin",
        password="your-password",
        verify_ssl=False,
    ) as client:
        tasks = client.tasks.list(limit=10)
        print(f"Found {len(tasks)} tasks")

        for task in tasks:
            print(f"\n  Task: {task.name}")
            print(f"    Key: {task.key}")
            print(f"    Status: {task.get('status')}")
            print(f"    Enabled: {task.is_enabled}")
            print(f"    Action: {task.action_display_name}")
            print(f"    Schedule Triggers: {task.trigger_count}")
            print(f"    Event Triggers: {task.event_count}")


def list_schedules() -> None:
    """List all task schedules."""
    print("\n=== List All Schedules ===")

    with VergeClient(
        host="192.168.1.100",
        username="admin",
        password="your-password",
        verify_ssl=False,
    ) as client:
        schedules = client.task_schedules.list(limit=10)
        print(f"Found {len(schedules)} schedules")

        for schedule in schedules:
            print(f"\n  Schedule: {schedule.name}")
            print(f"    Key: {schedule.key}")
            print(f"    Enabled: {schedule.is_enabled}")
            print(f"    Repeat: {schedule.repeat_every_display}")
            print(f"    Active Days: {', '.join(schedule.active_days)}")


def create_vm_power_on_task() -> None:
    """Create a task to power on VMs.

    This demonstrates creating a task that can be triggered by events
    (e.g., user login) or schedules.
    """
    print("\n=== Create VM Power On Task ===")

    with VergeClient(
        host="192.168.1.100",
        username="admin",
        password="your-password",
        verify_ssl=False,
    ) as client:
        # First, find a VM to use as the target
        vms = client.vms.list(limit=1)
        if not vms:
            print("No VMs found. Please create a VM first.")
            return

        vm = vms[0]
        print(f"Using VM: {vm.name} (key={vm.key})")

        # Create the power on task
        task = client.tasks.create(
            name="Power On Dev VMs",
            owner=vm.key,
            action="poweron",
            description="Power on development VMs when user logs in",
            enabled=True,
        )

        print(f"Created task: {task.name} (key={task.key})")
        print(f"  Action: {task.action_type}")
        print(f"  Enabled: {task.is_enabled}")


def create_vm_power_off_task() -> None:
    """Create a task to power off VMs.

    This task can be linked to:
    - User logout events
    - A schedule (e.g., Friday at 6 PM)
    """
    print("\n=== Create VM Power Off Task ===")

    with VergeClient(
        host="192.168.1.100",
        username="admin",
        password="your-password",
        verify_ssl=False,
    ) as client:
        # Find a VM to use as the target
        vms = client.vms.list(limit=1)
        if not vms:
            print("No VMs found.")
            return

        vm = vms[0]

        # Create the power off task
        task = client.tasks.create(
            name="Power Off Dev VMs",
            owner=vm.key,
            action="poweroff",
            description="Power off development VMs on logout or end of day",
            enabled=True,
        )

        print(f"Created task: {task.name} (key={task.key})")


def create_weekly_schedule() -> None:
    """Create a schedule for Fridays at 6:00 PM.

    This schedule can be applied to multiple tasks for consistent
    end-of-week automation.
    """
    print("\n=== Create Friday 6 PM Schedule ===")

    with VergeClient(
        host="192.168.1.100",
        username="admin",
        password="your-password",
        verify_ssl=False,
    ) as client:
        # Create a schedule for Fridays at 6:00 PM
        # Time is in seconds from midnight: 18:00 = 18 * 3600 = 64800
        schedule = client.task_schedules.create(
            name="Friday End of Business",
            description="Runs every Friday at 6:00 PM",
            repeat_every="week",
            repeat_iteration=1,
            start_time_of_day=64800,  # 6:00 PM (18 * 3600 seconds)
            monday=False,
            tuesday=False,
            wednesday=False,
            thursday=False,
            friday=True,
            saturday=False,
            sunday=False,
            enabled=True,
        )

        print(f"Created schedule: {schedule.name} (key={schedule.key})")
        print(f"  Repeat: {schedule.repeat_every_display}")
        print(f"  Active Days: {', '.join(schedule.active_days)}")


def link_task_to_schedule() -> None:
    """Link a power off task to the Friday schedule.

    Schedule triggers link tasks to schedules, enabling time-based automation.
    """
    print("\n=== Link Task to Schedule ===")

    with VergeClient(
        host="192.168.1.100",
        username="admin",
        password="your-password",
        verify_ssl=False,
    ) as client:
        # Find the task and schedule
        try:
            task = client.tasks.get(name="Power Off Dev VMs")
            schedule = client.task_schedules.get(name="Friday End of Business")
        except NotFoundError as e:
            print(f"Not found: {e}")
            print("Run create_vm_power_off_task() and create_weekly_schedule() first.")
            return

        # Create the schedule trigger
        trigger = client.task_schedule_triggers.create(
            task=task.key,
            schedule=schedule.key,
        )

        print(f"Created schedule trigger (key={trigger.key})")
        print(f"  Task: {trigger.task_display}")
        print(f"  Schedule: {trigger.schedule_display}")

        # Verify the trigger shows up on the task
        print(f"\n  Task now has {task.trigger_count + 1} schedule trigger(s)")


def view_task_triggers() -> None:
    """View all triggers (schedule and event) for a task."""
    print("\n=== View Task Triggers ===")

    with VergeClient(
        host="192.168.1.100",
        username="admin",
        password="your-password",
        verify_ssl=False,
    ) as client:
        tasks = client.tasks.list(limit=5)

        for task in tasks:
            print(f"\nTask: {task.name}")

            # List schedule triggers
            triggers = task.triggers.list()
            if triggers:
                print(f"  Schedule Triggers ({len(triggers)}):")
                for t in triggers:
                    print(f"    - Schedule: {t.schedule_display}")
            else:
                print("  Schedule Triggers: None")

            # List event triggers
            events = task.events.list()
            if events:
                print(f"  Event Triggers ({len(events)}):")
                for e in events:
                    print(f"    - Event: {e.event_name_display}")
            else:
                print("  Event Triggers: None")


def execute_task_manually() -> None:
    """Execute a task immediately, bypassing its triggers.

    This is useful for testing tasks or running them on-demand.
    """
    print("\n=== Execute Task Manually ===")

    with VergeClient(
        host="192.168.1.100",
        username="admin",
        password="your-password",
        verify_ssl=False,
    ) as client:
        try:
            task = client.tasks.get(name="Power On Dev VMs")
        except NotFoundError:
            print("Task 'Power On Dev VMs' not found.")
            return

        print(f"Executing task: {task.name}")

        # Execute the task
        task = task.execute()
        print(f"  Status: {task.get('status')}")

        # Optionally wait for completion
        print("  Waiting for completion...")
        task = task.wait(timeout=60, poll_interval=2)
        print(f"  Final Status: {task.get('status')}")


def enable_disable_task() -> None:
    """Enable or disable a task.

    Disabled tasks won't run according to their triggers but can still
    be executed manually.
    """
    print("\n=== Enable/Disable Task ===")

    with VergeClient(
        host="192.168.1.100",
        username="admin",
        password="your-password",
        verify_ssl=False,
    ) as client:
        try:
            task = client.tasks.get(name="Power On Dev VMs")
        except NotFoundError:
            print("Task not found.")
            return

        print(f"Task: {task.name}")
        print(f"  Currently enabled: {task.is_enabled}")

        # Toggle the enabled state
        if task.is_enabled:
            task = task.disable()
            print("  Task disabled")
        else:
            task = task.enable()
            print("  Task enabled")

        print(f"  Now enabled: {task.is_enabled}")


def list_task_scripts() -> None:
    """List available task scripts.

    Task scripts are GCS (VergeOS scripting) code that can be executed
    as tasks. Scripts can define questions (settings) for configurability.
    """
    print("\n=== List Task Scripts ===")

    with VergeClient(
        host="192.168.1.100",
        username="admin",
        password="your-password",
        verify_ssl=False,
    ) as client:
        scripts = client.task_scripts.list(limit=10)
        print(f"Found {len(scripts)} scripts")

        for script in scripts:
            print(f"\n  Script: {script.name}")
            print(f"    Key: {script.key}")
            print(f"    Description: {script.get('description', 'N/A')}")
            print(f"    Tasks using this script: {script.task_count}")


def cleanup_example_resources() -> None:
    """Clean up tasks and schedules created by this example.

    WARNING: This deletes resources. Only run if you want to remove
    the example tasks and schedules.
    """
    print("\n=== Cleanup Example Resources ===")

    with VergeClient(
        host="192.168.1.100",
        username="admin",
        password="your-password",
        verify_ssl=False,
    ) as client:
        # Delete tasks
        for task_name in ["Power On Dev VMs", "Power Off Dev VMs"]:
            try:
                task = client.tasks.get(name=task_name)

                # Delete associated triggers first
                for trigger in task.triggers.list():
                    client.task_schedule_triggers.delete(trigger.key)
                    print(f"  Deleted trigger {trigger.key}")

                # Delete associated events
                for event in task.events.list():
                    client.task_events.delete(event.key)
                    print(f"  Deleted event {event.key}")

                # Delete the task
                client.tasks.delete(task.key)
                print(f"Deleted task: {task_name}")
            except NotFoundError:
                print(f"Task not found: {task_name}")

        # Delete schedule
        try:
            schedule = client.task_schedules.get(name="Friday End of Business")
            client.task_schedules.delete(schedule.key)
            print("Deleted schedule: Friday End of Business")
        except NotFoundError:
            print("Schedule not found: Friday End of Business")


def full_automation_workflow() -> None:
    """Complete workflow: Create task, schedule, and link them.

    This demonstrates the full workflow for setting up automated
    VM power management similar to the documentation example.
    """
    print("\n=== Full Automation Workflow ===")
    print("Setting up automated VM power management...")

    with VergeClient(
        host="192.168.1.100",
        username="admin",
        password="your-password",
        verify_ssl=False,
    ) as client:
        # 1. Find a VM to manage
        vms = client.vms.list(limit=1)
        if not vms:
            print("No VMs found. Please create a VM first.")
            return
        vm = vms[0]
        print(f"\n1. Target VM: {vm.name}")

        # 2. Create power off task
        power_off_task = client.tasks.create(
            name="Auto Power Off VM",
            owner=vm.key,
            action="poweroff",
            description="Automatically power off VM on schedule",
            enabled=True,
        )
        print(f"2. Created task: {power_off_task.name}")

        # 3. Create weekly schedule (Fridays at 6 PM)
        friday_schedule = client.task_schedules.create(
            name="Weekly Friday 6PM",
            description="Every Friday at 6:00 PM",
            repeat_every="week",
            start_time_of_day=64800,  # 6 PM
            friday=True,
            monday=False,
            tuesday=False,
            wednesday=False,
            thursday=False,
            saturday=False,
            sunday=False,
        )
        print(f"3. Created schedule: {friday_schedule.name}")

        # 4. Link task to schedule
        client.task_schedule_triggers.create(
            task=power_off_task.key,
            schedule=friday_schedule.key,
        )
        print("4. Created trigger linking task to schedule")

        # 5. Verify setup
        task = client.tasks.get(power_off_task.key)
        print("\n5. Verification:")
        print(f"   Task '{task.name}' now has {task.trigger_count} schedule trigger(s)")
        print(f"   VM '{vm.name}' will power off every Friday at 6 PM")

        print("\nAutomation setup complete!")
        print("The VM will automatically power off every Friday at 6:00 PM.")


if __name__ == "__main__":
    print("pyvergeos Task Engine Examples")
    print("=" * 50)
    print()
    print("NOTE: Update host/credentials in this file before running.")
    print()
    print("Task Engine Components:")
    print("  - Tasks: Define actions to perform")
    print("  - Schedules: Define when tasks run")
    print("  - Events: Define conditions that trigger tasks")
    print("  - Triggers: Link tasks to schedules or events")
    print()

    # Uncomment the examples you want to run:
    # list_tasks()
    # list_schedules()
    # create_vm_power_on_task()
    # create_vm_power_off_task()
    # create_weekly_schedule()
    # link_task_to_schedule()
    # view_task_triggers()
    # execute_task_manually()
    # enable_disable_task()
    # list_task_scripts()
    # full_automation_workflow()
    # cleanup_example_resources()

    print("\nSee the code for examples of:")
    print("  - Creating tasks for VM power management")
    print("  - Creating schedules (hourly, daily, weekly)")
    print("  - Linking tasks to schedules via triggers")
    print("  - Viewing task triggers and events")
    print("  - Executing tasks manually")
    print("  - Enabling/disabling tasks")
    print("  - Listing task scripts")
    print("  - Full automation workflow setup")

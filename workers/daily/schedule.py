"""Render a disabled local schedule; never installs or enables a task."""

from html import escape
from pathlib import Path


def disabled_task(python: Path, repository: Path, request: Path, root: Path) -> bytes:
    arguments = escape(f'-m workers.daily.cli dry-run --root "{root}" --request "{request}"')
    # Serialization only: no XML parser or untrusted DTD/entity processing.
    text = f"""<?xml version="1.0" encoding="UTF-16"?>
<Task version="1.4" xmlns="http://schemas.microsoft.com/windows/2004/02/mit/task">
 <RegistrationInfo><Description>Disabled research task; activation approval required</Description>
 </RegistrationInfo>
 <Triggers><CalendarTrigger><StartBoundary>2026-10-10T22:30:00+05:30</StartBoundary>
 <Enabled>false</Enabled><ScheduleByDay><DaysInterval>1</DaysInterval></ScheduleByDay>
 </CalendarTrigger></Triggers>
 <Settings><Enabled>false</Enabled><MultipleInstancesPolicy>IgnoreNew</MultipleInstancesPolicy>
 <StartWhenAvailable>true</StartWhenAvailable><ExecutionTimeLimit>PT10M</ExecutionTimeLimit>
 </Settings>
 <Actions><Exec><Command>{escape(str(python))}</Command><Arguments>{arguments}</Arguments>
 <WorkingDirectory>{escape(str(repository))}</WorkingDirectory></Exec></Actions>
</Task>
"""
    return text.encode("utf-16")

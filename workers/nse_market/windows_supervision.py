"""Candidate-only Windows containment; never selects or collects market data.

The supervisor retains the sole job handle. A hard supervisor exit closes that
handle and Windows kills its contained descendants. A process handle pins the
reviewed cmd ancestor, avoiding PID-reuse races during ancestor monitoring.
"""

from __future__ import annotations

import ctypes
import os
import threading
import time
from collections.abc import Callable, Sequence
from ctypes import wintypes
from pathlib import Path
from typing import Any

PARENT_INTERRUPTED = 125
# Windows-only ctypes attributes remain absent from other platforms' type stubs.
_NATIVE_CTYPES: Any = ctypes


class _StartupInfo(ctypes.Structure):
    _fields_ = [
        ("cb", wintypes.DWORD),
        ("lpReserved", wintypes.LPWSTR),
        ("lpDesktop", wintypes.LPWSTR),
        ("lpTitle", wintypes.LPWSTR),
        ("dwX", wintypes.DWORD),
        ("dwY", wintypes.DWORD),
        ("dwXSize", wintypes.DWORD),
        ("dwYSize", wintypes.DWORD),
        ("dwXCountChars", wintypes.DWORD),
        ("dwYCountChars", wintypes.DWORD),
        ("dwFillAttribute", wintypes.DWORD),
        ("dwFlags", wintypes.DWORD),
        ("wShowWindow", wintypes.WORD),
        ("cbReserved2", wintypes.WORD),
        ("lpReserved2", ctypes.c_void_p),
        ("hStdInput", wintypes.HANDLE),
        ("hStdOutput", wintypes.HANDLE),
        ("hStdError", wintypes.HANDLE),
    ]


class _ProcessInfo(ctypes.Structure):
    _fields_ = [
        ("hProcess", wintypes.HANDLE),
        ("hThread", wintypes.HANDLE),
        ("dwProcessId", wintypes.DWORD),
        ("dwThreadId", wintypes.DWORD),
    ]


class _StartupInfoEx(ctypes.Structure):
    _fields_ = [("StartupInfo", _StartupInfo), ("lpAttributeList", ctypes.c_void_p)]


class _ProcessEntry(ctypes.Structure):
    _fields_ = [
        ("dwSize", wintypes.DWORD),
        ("cntUsage", wintypes.DWORD),
        ("th32ProcessID", wintypes.DWORD),
        ("th32DefaultHeapID", ctypes.c_size_t),
        ("th32ModuleID", wintypes.DWORD),
        ("cntThreads", wintypes.DWORD),
        ("th32ParentProcessID", wintypes.DWORD),
        ("pcPriClassBase", wintypes.LONG),
        ("dwFlags", wintypes.DWORD),
        ("szExeFile", wintypes.WCHAR * 260),
    ]


class _BasicLimits(ctypes.Structure):
    _fields_ = [
        ("PerProcessUserTimeLimit", ctypes.c_int64),
        ("PerJobUserTimeLimit", ctypes.c_int64),
        ("LimitFlags", wintypes.DWORD),
        ("MinimumWorkingSetSize", ctypes.c_size_t),
        ("MaximumWorkingSetSize", ctypes.c_size_t),
        ("ActiveProcessLimit", wintypes.DWORD),
        ("Affinity", ctypes.c_size_t),
        ("PriorityClass", wintypes.DWORD),
        ("SchedulingClass", wintypes.DWORD),
    ]


class _IoCounters(ctypes.Structure):
    _fields_ = [
        (name, ctypes.c_uint64)
        for name in (
            "ReadOperationCount",
            "WriteOperationCount",
            "OtherOperationCount",
            "ReadTransferCount",
            "WriteTransferCount",
            "OtherTransferCount",
        )
    ]


class _ExtendedLimits(ctypes.Structure):
    _fields_ = [
        ("BasicLimitInformation", _BasicLimits),
        ("IoInfo", _IoCounters),
        ("ProcessMemoryLimit", ctypes.c_size_t),
        ("JobMemoryLimit", ctypes.c_size_t),
        ("PeakProcessMemoryUsed", ctypes.c_size_t),
        ("PeakJobMemoryUsed", ctypes.c_size_t),
    ]


class _Accounting(ctypes.Structure):
    _fields_ = [
        ("TotalUserTime", ctypes.c_int64),
        ("TotalKernelTime", ctypes.c_int64),
        ("ThisPeriodTotalUserTime", ctypes.c_int64),
        ("ThisPeriodTotalKernelTime", ctypes.c_int64),
        ("TotalPageFaultCount", wintypes.DWORD),
        ("TotalProcesses", wintypes.DWORD),
        ("ActiveProcesses", wintypes.DWORD),
        ("TotalTerminatedProcesses", wintypes.DWORD),
    ]


class _Windows:
    def __init__(self) -> None:
        if os.name != "nt":
            raise RuntimeError("WINDOWS_SUPERVISION_REQUIRED")
        self.api: Any = _NATIVE_CTYPES.WinDLL("kernel32", use_last_error=True)
        signatures = {
            "CreateJobObjectW": ([ctypes.c_void_p, wintypes.LPCWSTR], wintypes.HANDLE),
            "SetInformationJobObject": (
                [wintypes.HANDLE, ctypes.c_int, ctypes.c_void_p, wintypes.DWORD],
                wintypes.BOOL,
            ),
            "InitializeProcThreadAttributeList": (
                [ctypes.c_void_p, wintypes.DWORD, wintypes.DWORD, ctypes.POINTER(ctypes.c_size_t)],
                wintypes.BOOL,
            ),
            "UpdateProcThreadAttribute": (
                [
                    ctypes.c_void_p,
                    wintypes.DWORD,
                    ctypes.c_size_t,
                    ctypes.c_void_p,
                    ctypes.c_size_t,
                    ctypes.c_void_p,
                    ctypes.c_void_p,
                ],
                wintypes.BOOL,
            ),
            "DeleteProcThreadAttributeList": ([ctypes.c_void_p], None),
            "TerminateJobObject": ([wintypes.HANDLE, wintypes.UINT], wintypes.BOOL),
            "QueryInformationJobObject": (
                [wintypes.HANDLE, ctypes.c_int, ctypes.c_void_p, wintypes.DWORD, ctypes.c_void_p],
                wintypes.BOOL,
            ),
            "GetWindowsDirectoryW": ([wintypes.LPWSTR, wintypes.UINT], wintypes.UINT),
            "GetProcessTimes": (
                [
                    wintypes.HANDLE,
                    ctypes.POINTER(wintypes.FILETIME),
                    ctypes.POINTER(wintypes.FILETIME),
                    ctypes.POINTER(wintypes.FILETIME),
                    ctypes.POINTER(wintypes.FILETIME),
                ],
                wintypes.BOOL,
            ),
            "CreateProcessW": (
                [
                    wintypes.LPCWSTR,
                    wintypes.LPWSTR,
                    ctypes.c_void_p,
                    ctypes.c_void_p,
                    wintypes.BOOL,
                    wintypes.DWORD,
                    ctypes.c_void_p,
                    wintypes.LPCWSTR,
                    ctypes.POINTER(_StartupInfo),
                    ctypes.POINTER(_ProcessInfo),
                ],
                wintypes.BOOL,
            ),
            "GetExitCodeProcess": (
                [wintypes.HANDLE, ctypes.POINTER(wintypes.DWORD)],
                wintypes.BOOL,
            ),
            "TerminateProcess": ([wintypes.HANDLE, wintypes.UINT], wintypes.BOOL),
            "OpenProcess": ([wintypes.DWORD, wintypes.BOOL, wintypes.DWORD], wintypes.HANDLE),
            "ResumeThread": ([wintypes.HANDLE], wintypes.DWORD),
            "WaitForSingleObject": ([wintypes.HANDLE, wintypes.DWORD], wintypes.DWORD),
            "CloseHandle": ([wintypes.HANDLE], wintypes.BOOL),
            "CreateToolhelp32Snapshot": ([wintypes.DWORD, wintypes.DWORD], wintypes.HANDLE),
            "Process32FirstW": ([wintypes.HANDLE, ctypes.POINTER(_ProcessEntry)], wintypes.BOOL),
            "Process32NextW": ([wintypes.HANDLE, ctypes.POINTER(_ProcessEntry)], wintypes.BOOL),
            "QueryFullProcessImageNameW": (
                [wintypes.HANDLE, wintypes.DWORD, wintypes.LPWSTR, ctypes.POINTER(wintypes.DWORD)],
                wintypes.BOOL,
            ),
        }
        for name, (args, result) in signatures.items():
            function = getattr(self.api, name)
            function.argtypes, function.restype = args, result

    def checked(self, value: Any) -> int:
        if not value or value == ctypes.c_void_p(-1).value:
            raise OSError(_NATIVE_CTYPES.get_last_error(), "WINDOWS_SUPERVISION_API_FAILED")
        return int(value)

    def close(self, handle: int) -> None:
        self.checked(self.api.CloseHandle(handle))

    def alive(self, handle: int) -> bool:
        result = self.api.WaitForSingleObject(handle, 0)
        if result not in (0, 258):
            raise OSError("WINDOWS_SUPERVISION_WAIT_FAILED")
        return bool(result == 258)

    def processes(self) -> dict[int, tuple[int, str]]:
        handle = self.checked(self.api.CreateToolhelp32Snapshot(2, 0))
        try:
            entry = _ProcessEntry()
            entry.dwSize = ctypes.sizeof(entry)
            present = self.api.Process32FirstW(handle, ctypes.byref(entry))
            result = {}
            while present:
                result[int(entry.th32ProcessID)] = (
                    int(entry.th32ParentProcessID),
                    str(entry.szExeFile),
                )
                present = self.api.Process32NextW(handle, ctypes.byref(entry))
            return result
        finally:
            self.close(handle)

    def cmd_parent(self) -> int:
        """Accept only cmd -> optional venv redirector -> this interpreter."""
        rows = self.processes()
        parent = rows[os.getpid()][0]
        if rows[parent][1].lower() == "python.exe":
            parent = rows[parent][0]
        if rows[parent][1].lower() != "cmd.exe":
            raise RuntimeError("SCHEDULER_CMD_ANCESTOR_REQUIRED")
        handle = self.checked(self.api.OpenProcess(0x100000 | 0x1000, False, parent))
        try:
            current = self.checked(self.api.OpenProcess(0x1000, False, os.getpid()))
            try:
                if self.created(handle) > self.created(current):
                    raise RuntimeError("SCHEDULER_CMD_ANCESTOR_PID_REUSED")
            finally:
                self.close(current)
            size = wintypes.DWORD(32768)
            image = ctypes.create_unicode_buffer(size.value)
            self.checked(self.api.QueryFullProcessImageNameW(handle, 0, image, ctypes.byref(size)))
            directory = ctypes.create_unicode_buffer(32768)
            length = self.checked(self.api.GetWindowsDirectoryW(directory, len(directory)))
            if length >= len(directory):
                raise RuntimeError("WINDOWS_DIRECTORY_REJECTED")
            expected = Path(directory.value) / "System32/cmd.exe"
            if Path(image.value).resolve() != expected.resolve() or not self.alive(handle):
                raise RuntimeError("SCHEDULER_CMD_ANCESTOR_REJECTED")
            return handle
        except BaseException:
            self.close(handle)
            raise

    def created(self, handle: int) -> int:
        start, end, kernel, user = (wintypes.FILETIME() for _ in range(4))
        self.checked(
            self.api.GetProcessTimes(
                handle,
                ctypes.byref(start),
                ctypes.byref(end),
                ctypes.byref(kernel),
                ctypes.byref(user),
            )
        )
        return (int(start.dwHighDateTime) << 32) | int(start.dwLowDateTime)

    def active(self, job: int) -> int:
        accounting = _Accounting()
        self.checked(
            self.api.QueryInformationJobObject(
                job, 1, ctypes.byref(accounting), ctypes.sizeof(accounting), None
            )
        )
        return int(accounting.ActiveProcesses)

    def stop(self, job: int, code: int) -> None:
        self.checked(self.api.TerminateJobObject(job, code))
        deadline = time.monotonic() + 10
        while self.active(job):
            if time.monotonic() >= deadline:
                raise RuntimeError("CONTAINED_JOB_EXIT_TIMEOUT")
            time.sleep(0.01)


def _quote(argument: str) -> str:
    """Quote one Windows CRT argument; CreateProcess receives no command shell."""
    if "\0" in argument:
        raise ValueError("PROCESS_ARGUMENT_REJECTED")
    result = '"'
    slashes = 0
    for character in argument:
        if character == "\\":
            slashes += 1
            continue
        result += "\\" * (slashes * 2 + 1 if character == '"' else slashes)
        result += character
        slashes = 0
    return result + "\\" * (slashes * 2) + '"'


class _Child:
    def __init__(self, windows: _Windows, command: Sequence[str], job: int) -> None:
        if not command or not Path(command[0]).is_absolute():
            raise ValueError("ABSOLUTE_WORKER_EXECUTABLE_REQUIRED")
        self.windows = windows
        self.info = _ProcessInfo()
        startup = _StartupInfoEx()
        startup.StartupInfo.cb = ctypes.sizeof(startup)
        line = ctypes.create_unicode_buffer(" ".join(_quote(part) for part in command))
        size = ctypes.c_size_t()
        windows.api.InitializeProcThreadAttributeList(None, 1, 0, ctypes.byref(size))
        if not size.value:
            raise RuntimeError("WINDOWS_JOB_ATTRIBUTE_UNAVAILABLE")
        attributes = ctypes.create_string_buffer(size.value)
        startup.lpAttributeList = ctypes.cast(attributes, ctypes.c_void_p)
        windows.checked(
            windows.api.InitializeProcThreadAttributeList(
                startup.lpAttributeList, 1, 0, ctypes.byref(size)
            )
        )
        try:
            jobs = (wintypes.HANDLE * 1)(job)
            windows.checked(
                windows.api.UpdateProcThreadAttribute(
                    startup.lpAttributeList,
                    0,
                    0x2000D,
                    ctypes.byref(jobs),
                    ctypes.sizeof(jobs),
                    None,
                    None,
                )
            )  # PROC_THREAD_ATTRIBUTE_JOB_LIST, Windows 10+
            windows.checked(
                windows.api.CreateProcessW(
                    command[0],
                    line,
                    None,
                    None,
                    False,
                    0x80000 | 4,
                    None,
                    None,
                    ctypes.byref(startup.StartupInfo),
                    ctypes.byref(self.info),
                )
            )
            # EXTENDED_STARTUPINFO_PRESENT | CREATE_SUSPENDED. Job membership is
            # supplied to creation itself; no user-mode post-creation assignment gap.
        finally:
            windows.api.DeleteProcThreadAttributeList(startup.lpAttributeList)

    @property
    def handle(self) -> int:
        return int(self.info.hProcess)

    def resume(self) -> None:
        if self.windows.api.ResumeThread(self.info.hThread) != 1:
            raise RuntimeError("WORKER_RESUME_FAILED")

    def poll(self) -> int | None:
        if self.windows.alive(self.handle):
            return None
        result = wintypes.DWORD()
        self.windows.checked(self.windows.api.GetExitCodeProcess(self.handle, ctypes.byref(result)))
        return int(result.value)

    def wait(self) -> None:
        if self.windows.api.WaitForSingleObject(self.handle, 10000) != 0:
            raise RuntimeError("CONTAINED_WORKER_EXIT_TIMEOUT")

    def close(self) -> None:
        try:
            if self.poll() is None:
                stopped = self.windows.api.TerminateProcess(self.handle, PARENT_INTERRUPTED)
                if not stopped and self.windows.api.WaitForSingleObject(self.handle, 10000) != 0:
                    self.windows.checked(stopped)
            self.wait()
        finally:
            self.windows.close(int(self.info.hThread))
            self.windows.close(self.handle)


def supervise(
    command: Sequence[str],
    *,
    parent_handle: int,
    record: Callable[[str, int | None], None],
) -> int:
    """Contain the command before it can execute; own and reap its full job.

    Caller owns the pinned ancestor handle. Commands are fixed by the production
    entry point; tests supply explicitly TEST_ONLY Python subprocesses.
    """
    windows = _Windows()
    job = windows.checked(windows.api.CreateJobObjectW(None, None))
    child: _Child | None = None
    stop_watch = threading.Event()
    watch_failed = threading.Event()

    def watch_ancestor() -> None:
        # Receipt fsync can be slow. Parent loss must stop work independently of logging.
        while not stop_watch.is_set():
            result = windows.api.WaitForSingleObject(parent_handle, 50)
            if result != 258:
                if result != 0:
                    watch_failed.set()
                if not windows.api.TerminateJobObject(job, PARENT_INTERRUPTED):
                    watch_failed.set()
                return

    watchdog = threading.Thread(target=watch_ancestor, name="alphalens-ancestor-watch", daemon=True)
    watch_started = False
    try:
        limits = _ExtendedLimits()
        limits.BasicLimitInformation.LimitFlags = 0x2000  # JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE
        windows.checked(
            windows.api.SetInformationJobObject(job, 9, ctypes.byref(limits), ctypes.sizeof(limits))
        )
        watchdog.start()
        watch_started = True
        if not windows.alive(parent_handle):
            record("ANCESTOR_ALREADY_EXITED", PARENT_INTERRUPTED)
            return PARENT_INTERRUPTED
        child = _Child(windows, command, job)
        if not windows.alive(parent_handle):
            windows.stop(job, PARENT_INTERRUPTED)
            child.wait()
            record("ANCESTOR_EXITED_BEFORE_RESUME", PARENT_INTERRUPTED)
            return PARENT_INTERRUPTED
        child.resume()
        record("CONTAINED_WORKER_STARTED", None)
        while windows.alive(parent_handle):
            if watch_failed.is_set():
                raise RuntimeError("ANCESTOR_WATCH_FAILED")
            result = child.poll()
            if result is not None:
                if not windows.alive(parent_handle):
                    break
                if result != 0:
                    windows.stop(job, result)
                if result != 0 or windows.active(job) == 0:
                    child.wait()
                    record("CONTAINED_WORKER_EXIT", result)
                    if windows.alive(parent_handle):
                        return result
                    break
            time.sleep(0.05)
        windows.stop(job, PARENT_INTERRUPTED)
        child.wait()
        record("ANCESTOR_EXITED_WORKER_INTERRUPTED", PARENT_INTERRUPTED)
        return PARENT_INTERRUPTED
    except KeyboardInterrupt:
        windows.stop(job, 130)
        if child is not None:
            child.wait()
        record("SUPERVISOR_CONTROL_INTERRUPT", 130)
        return 130
    finally:
        stop_watch.set()
        if watch_started:
            watchdog.join()
        try:
            if windows.active(job):
                windows.stop(job, PARENT_INTERRUPTED)
        finally:
            try:
                # Hard supervisor death also closes this sole non-inherited handle.
                windows.close(job)
            finally:
                if child is not None:
                    child.close()

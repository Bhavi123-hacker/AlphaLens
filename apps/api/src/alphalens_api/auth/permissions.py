"""Native Windows DACL or POSIX owner-only permissions; no shell/PATH trust."""

import importlib
import os
import sys
from pathlib import Path


def restrict(root: Path) -> None:
    if sys.platform != "win32":
        root.chmod(0o700)
        return
    try:
        security = importlib.import_module("win32security")
        api = importlib.import_module("win32api")
        constants = importlib.import_module("win32con")
        access = importlib.import_module("ntsecuritycon")
        token = security.OpenProcessToken(api.GetCurrentProcess(), constants.TOKEN_QUERY)
        try:
            owner = security.GetTokenInformation(token, security.TokenUser)[0]
        finally:
            token.Close()
        system = security.CreateWellKnownSid(security.WinLocalSystemSid, None)
        dacl = security.ACL()
        flags = constants.CONTAINER_INHERIT_ACE | constants.OBJECT_INHERIT_ACE
        for sid in (owner, system):
            dacl.AddAccessAllowedAceEx(security.ACL_REVISION_DS, flags, access.FILE_ALL_ACCESS, sid)
        security.SetNamedSecurityInfo(
            str(root),
            security.SE_FILE_OBJECT,
            security.DACL_SECURITY_INFORMATION | security.PROTECTED_DACL_SECURITY_INFORMATION,
            None,
            None,
            dacl,
            None,
        )
    except Exception:
        raise ValueError("AUTH_FILESYSTEM_PERMISSION_FAILED") from None


def verify(root: Path, *, directory: bool = True) -> None:
    if sys.platform != "win32":
        if root.stat().st_mode & 0o077 or root.stat().st_uid != os.geteuid():
            raise ValueError("AUTH_FILESYSTEM_PERMISSION_FAILED")
        return
    try:
        security = importlib.import_module("win32security")
        api = importlib.import_module("win32api")
        constants = importlib.import_module("win32con")
        access = importlib.import_module("ntsecuritycon")
        token = security.OpenProcessToken(api.GetCurrentProcess(), constants.TOKEN_QUERY)
        try:
            owner = security.GetTokenInformation(token, security.TokenUser)[0]
        finally:
            token.Close()
        system = security.CreateWellKnownSid(security.WinLocalSystemSid, None)
        descriptor = security.GetNamedSecurityInfo(
            str(root), security.SE_FILE_OBJECT, security.DACL_SECURITY_INFORMATION
        )
        dacl = descriptor.GetSecurityDescriptorDacl()
        if (
            (
                directory
                and not descriptor.GetSecurityDescriptorControl()[0] & security.SE_DACL_PROTECTED
            )
            or dacl is None
            or dacl.GetAceCount() != 2
        ):
            raise ValueError
        allowed = {str(owner), str(system)}
        actual = set()
        for index in range(dacl.GetAceCount()):
            ace = dacl.GetAce(index)
            if ace[0][0] != security.ACCESS_ALLOWED_ACE_TYPE or ace[1] != access.FILE_ALL_ACCESS:
                raise ValueError
            actual.add(str(ace[2]))
        if actual != allowed:
            raise ValueError
    except Exception:
        raise ValueError("AUTH_FILESYSTEM_PERMISSION_FAILED") from None

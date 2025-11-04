from typing import Iterable, List, Optional, Set

import controlTypes
from globalPluginHandler import GlobalPlugin
from NVDAObjects import NVDAObject


# Roles where text-from-children is typically meaningful for unlabeled controls.
def _role(name: str) -> Optional[int]:
    try:
        return getattr(controlTypes.Role, name)
    except Exception:
        return None


def _build_role_set(names: Iterable[str]) -> Set[int]:
    out: Set[int] = set()
    for n in names:
        val = _role(n)
        if val is not None:
            out.add(val)
    return out


# Roles that are commonly interactive by design.
ALWAYS_CANDIDATE_ROLES: Set[int] = _build_role_set(
    [
        "BUTTON",
        "TOGGLEBUTTON",
        "LINK",
        "MENUITEM",
        "TAB",
        "TABITEM",
        "CHECKBOX",
        "RADIOBUTTON",
    ]
)

# Roles that should only be considered when tabbable/focusable.
FOCUSABLE_CANDIDATE_ROLES: Set[int] = _build_role_set(
    [
        "PANE",
        "STATIC_TEXT",
        "GROUPING",
    ]
)

# Item roles (e.g., list/tree items) that may expose class-like names
# instead of meaningful contents; we special-case these.
ITEM_ROLES: Set[int] = _build_role_set(
    [
        "LISTITEM",
        "TREEVIEWITEM",
    ]
)


def _isClassyName(name: Optional[str]) -> bool:
    """Detect names that look like type/namespace identifiers rather than user-facing labels.
    Heuristics:
    - Contains at least one dot and no spaces, e.g., 'component.sub.viewItem'.
    - Reasonable length threshold to avoid false positives.
    """
    if not isinstance(name, str):
        return False
    s = name.strip()
    if not s:
        return False
    if " " in s:
        return False
    if "." in s and len(s) >= 8:
        return True
    return False


def _getUIAFrameworkId(obj: NVDAObject) -> str:
    """Best-effort to retrieve the UIA framework ID as an uppercased string.
    Works across NVDA versions by trying multiple attribute names.
    Returns empty string on failure.
    """
    try:
        el = getattr(obj, "UIAElement", None)
        if not el:
            return ""
        # Try common attribute names used in NVDA's UIA wrappers.
        for attr in (
            "cachedFrameworkID",
            "cachedFrameworkId",
            "CurrentFrameworkId",
            "currentFrameworkId",
        ):
            fw = getattr(el, attr, None)
            if fw:
                try:
                    return str(fw).upper()
                except Exception:
                    return ""
        return ""
    except Exception:
        return ""


def _isDotNetUI(obj: NVDAObject) -> bool:
    """Heuristically determine if `obj` is part of a .NET UI.
    - UIA frameworks: WPF, XAML (UWP/WinUI/MAUI), WinForms
    - IAccessible WinForms: window class usually starts with 'WindowsForms10.'
    """
    # UIA-based frameworks
    fw = _getUIAFrameworkId(obj)
    if fw in {"WPF", "XAML", "WINFORM", "WINFORMS", "MAUI"}:
        return True

    # WinForms via IAccessible
    try:
        wcn = getattr(obj, "windowClassName", "") or ""
        if wcn.startswith("WindowsForms10."):
            return True
    except Exception:
        pass

    return False


def _gatherTextFromChildren(obj: NVDAObject, maxDepth: int = 3, maxItems: int = 10) -> List[str]:
    """Collect meaningful text from descendants up to a depth limit.
    - Prefers each child's `name`; falls back to `value` or `description`.
    - Adds items in document order; stops after `maxItems`.
    """
    out: List[str] = []

    def visit(nodes: Iterable[NVDAObject], depth: int) -> None:
        nonlocal out
        if depth < 0 or len(out) >= maxItems:
            return
        for n in nodes or []:
            if len(out) >= maxItems:
                break
            try:
                # Prefer accessible name when present
                t = getattr(n, "name", None)
                if not t:
                    t = getattr(n, "value", None) or getattr(n, "description", None)
                if isinstance(t, str) and t.strip():
                    out.append(t.strip())
                # Continue descending to capture nested text blocks
                visit(getattr(n, "children", None), depth - 1)
            except Exception:
                continue

    try:
        visit(getattr(obj, "children", None), maxDepth)
    except Exception:
        pass

    return out


class UnlabeledDotNetNameOverlay(NVDAObject):
    """Overlay that supplies a name for unlabeled .NET controls by
    concatenating meaningful text from their descendant text nodes.
    Only activates when the original name is empty.
    """

    def _get_name(self) -> Optional[str]:
        # Keep original behavior if a name already exists.
        original = super()._get_name()
        if original:
            # For item-like roles, override class-like names with child text.
            try:
                role = self.role
            except Exception:
                role = None
            if role in ITEM_ROLES and _isDotNetUI(self) and _isClassyName(original):
                pieces = _gatherTextFromChildren(self)
                if pieces:
                    return " ".join(pieces)
            return original

        # Only operate for .NET-based controls and selected roles.
        try:
            role = self.role
        except Exception:
            return original

        if not _isDotNetUI(self):
            return original

        # Determine eligibility by role and focusability.
        try:
            states = getattr(self, "states", set()) or set()
        except Exception:
            states = set()

        isFocusable = controlTypes.State.FOCUSABLE in states

        if role not in ALWAYS_CANDIDATE_ROLES and not (
            role in FOCUSABLE_CANDIDATE_ROLES and isFocusable
        ):
            return original

        pieces = _gatherTextFromChildren(self)
        if pieces:
            return " ".join(pieces)

        return original


class GlobalPlugin(GlobalPlugin):
    """Global plugin that injects the overlay class for eligible objects."""

    def chooseNVDAObjectOverlayClasses(self, obj: NVDAObject, clsList: List[type]) -> None:
        # Fast-path checks: must be .NET, eligible role, and currently unlabeled.
        if not _isDotNetUI(obj):
            return

        try:
            role = obj.role
        except Exception:
            return

        try:
            states = getattr(obj, "states", set()) or set()
        except Exception:
            states = set()

        isFocusable = controlTypes.State.FOCUSABLE in states

        eligible = False
        if role in ALWAYS_CANDIDATE_ROLES or (
            role in FOCUSABLE_CANDIDATE_ROLES and isFocusable
        ):
            eligible = True
        elif role in ITEM_ROLES:
            eligible = True
        if not eligible:
            return

        try:
            curName = getattr(obj, "name", None)
        except Exception:
            curName = None

        # Allow overlay when name is empty, or when an item role exposes a
        # class-like name that should be replaced by child contents.
        if curName and not (role in ITEM_ROLES and _isClassyName(curName)):
            return

        # Apply overlay with high precedence so its _get_name overrides UIA.
        # Use insert(0, ...) instead of append to ensure MRO order is
        # UnlabeledDotNetNameOverlay -> other overlays -> UIA -> ...
        clsList.insert(0, UnlabeledDotNetNameOverlay)


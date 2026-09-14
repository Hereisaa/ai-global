"""Optional prompt_toolkit UI; edits are staged until Enter is pressed."""

from prompt_toolkit import Application
from prompt_toolkit.application.current import get_app
from prompt_toolkit.data_structures import Point
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.layout import HSplit, Layout, Window
from prompt_toolkit.layout.controls import FormattedTextControl
from prompt_toolkit.layout.margins import ScrollbarMargin
from prompt_toolkit.styles import Style
from prompt_toolkit.utils import get_cwidth


def identity(row):
    return row["tool"], row["kind"], row["id"]


def unavailable_reason(row):
    if row["installed"] is False:
        return "尚未在使用者層安裝，請先用原生工具安裝。"
    if type(row["enabled"]) is not bool:
        return "目前開關狀態未知，請先用原生工具確認。"
    return ""


class Selection:
    def __init__(self, rows):
        self.rows = rows
        self.index = 0
        self.id_offset = 0
        self.pending = {}
        self.message = "空白鍵只預選；Enter 才會寫入設定。"

    def move(self, amount):
        if self.rows:
            self.index = max(0, min(len(self.rows) - 1, self.index + amount))
        self.id_offset = 0
        self.message = "空白鍵只預選；Enter 才會寫入設定。"

    def flip(self):
        if not self.rows:
            return
        row = self.rows[self.index]
        reason = unavailable_reason(row)
        if reason:
            self.message = reason
            return
        key = identity(row)
        wanted = not self.pending.get(key, row["enabled"])
        if wanted == row["enabled"]:
            self.pending.pop(key, None)
        else:
            self.pending[key] = wanted
        self.message = f"已預選 {len(self.pending)} 項變更；Enter 套用，Esc 取消。"


def create_app(rows, table_renderer, *, demo=False, input=None, output=None):
    state = Selection(rows)
    keys = KeyBindings()

    def clipped(text, width):
        if get_cwidth(text) <= width:
            return text
        result = ""
        for char in text:
            if get_cwidth(result + char) > width - 1:
                break
            result += char
        return result + "…"

    def table_lines():
        width = max(10, get_app().output.get_size().columns - 8)
        if width < 60:
            # Details remain below the list when the terminal is very narrow.
            return ["工具    ID", "------  " + "-" * max(2, width - 8)] + [
                f"{r['tool']:<6}  {clipped(r['id'], max(2, width - 8))}" for r in rows]
        empty_ids = [dict(r, id="") for r in rows]
        base = table_renderer(empty_ids).splitlines()[1]
        id_width = max(2, width - get_cwidth(base) + 2)
        return table_renderer([dict(r, id=clipped(r["id"], id_width)) for r in rows]).splitlines()

    @keys.add("up")
    def up(event):
        state.move(-1)

    @keys.add("down")
    def down(event):
        state.move(1)

    @keys.add("pageup")
    def pageup(event):
        state.move(-10)

    @keys.add("pagedown")
    def pagedown(event):
        state.move(10)

    @keys.add(" ")
    def space(event):
        state.flip()

    @keys.add("left")
    def left(event):
        state.id_offset = max(0, state.id_offset - 10)

    @keys.add("right")
    def right(event):
        if rows:
            state.id_offset = min(max(0, len(rows[state.index]["id"]) - 1), state.id_offset + 10)

    @keys.add("enter")
    def apply(event):
        event.app.exit(result=dict(state.pending))

    @keys.add("escape")
    @keys.add("c-c")
    def cancel(event):
        event.app.exit(result=None)

    def content():
        result = []
        table = table_lines()
        if not rows:
            return [("", "沒有符合條件的能力。Esc 離開。")]
        for i, row in enumerate(rows):
            selected = i == state.index
            key = identity(row)
            blocked = unavailable_reason(row)
            checked = "-" if blocked else "x" if state.pending.get(key, row["enabled"]) else " "
            marker = "*" if key in state.pending else " "
            prefix = f"{'>' if selected else ' '} [{checked}]{marker} "
            style = "class:selected" if selected else "class:disabled" if blocked else ""
            result.append((style, prefix + table[i + 2] + "\n"))
        return result

    control = FormattedTextControl(content, focusable=True,
                                   get_cursor_position=lambda: Point(x=0, y=state.index))

    def details():
        if not rows:
            return state.message
        row = rows[state.index]
        current = "開" if row["enabled"] is True else "關" if row["enabled"] is False else "未知"
        wanted = state.pending.get(identity(row), row["enabled"])
        wanted_label = "開" if wanted is True else "關" if wanted is False else "未知"
        origin = "專案預設" if row["origin"] == "project-default" else "本機既有"
        default = "未指定" if row["default_enabled"] is None else "開" if row["default_enabled"] else "關"
        return (f"{origin} / 專案建議：{default}\n"
                f"目前 {current} → 預定 {wanted_label} / 待套用 {len(state.pending)} 項")

    def identifier_line():
        if not rows:
            return ""
        width = max(1, get_app().output.get_size().columns - 9)
        return "ID ←→：" + clipped(rows[state.index]["id"][state.id_offset:], width)

    def reason():
        if not rows:
            return ""
        row = rows[state.index]
        return unavailable_reason(row) or row.get("note", "")

    layout = HSplit([
        Window(FormattedTextControl("AI GLOBAL  能力設定" + ("  [示範：不寫入設定]" if demo else "  [使用者全域層]")), height=1, style="class:title"),
        Window(FormattedTextControl("↑↓ 選取  空白鍵 預選開關  Enter 套用  Esc/Ctrl+C 取消  PgUp/PgDn 翻頁"), height=2, wrap_lines=True),
        Window(FormattedTextControl(lambda: "       " + table_lines()[0] + "\n       " + table_lines()[1]), height=2, wrap_lines=False),
        Window(control, wrap_lines=False, right_margins=[ScrollbarMargin(display_arrows=True)]),
        Window(height=1, char="─"),
        Window(FormattedTextControl(details), height=2, wrap_lines=True),
        Window(FormattedTextControl(identifier_line), height=1, wrap_lines=False),
        Window(FormattedTextControl(reason), height=2, wrap_lines=True),
        Window(FormattedTextControl(lambda: state.message), height=2, wrap_lines=True),
        Window(FormattedTextControl("[x] 預定啟用  [ ] 預定停用  [-] 不可切換  * 待套用；清單中的本機開關為開啟畫面時的值。"), height=2, wrap_lines=True),
    ])
    app = Application(layout=Layout(layout, focused_element=control), key_bindings=keys,
                      full_screen=True, mouse_support=False, input=input, output=output,
                      style=Style.from_dict({"title": "bold fg:ansicyan", "selected": "reverse", "disabled": "fg:ansibrightblack"}))
    return app


def demo_rows():
    return [dict(tool=tool, kind=kind, id=name, origin=origin,
                 default_enabled=True if origin == "project-default" else None,
                 installed=installed, enabled=enabled, path=None, note="示範資料，不影響任何設定。")
            for tool, kind, name, origin, installed, enabled in (
                ("claude", "skill", "demo-default-skill", "project-default", True, True),
                ("codex", "plugin", "demo-local-plugin@market", "local-existing", None, False),
                ("claude", "skill", "demo-missing-skill", "project-default", False, None),
                ("claude", "command", "demo-command", "local-existing", True, True),
            )]


def apply_changes(rows, pending, read_current, toggle):
    """Recheck the selection, then report partial progress honestly on failure."""
    if not pending:
        return 0, ["沒有變更，未寫入設定。"]
    original = {identity(row): row for row in rows}
    current = {identity(row): row for row in read_current()}
    fields = ("enabled", "installed", "path")
    for key in pending:
        if (key not in original or key not in current or
                any(original[key][field] != current[key][field] for field in fields)):
            return 1, ["清單開啟後能力狀態已改變，未套用；請重新開啟 manage。"]
    messages = []
    for key, enabled in pending.items():
        try:
            messages.append(toggle(*key, enabled))
        except Exception:
            # Config/tool exceptions can contain secrets; do not echo them.
            messages.append(f"套用失敗：{key[0]} / {key[1]} / {key[2]}。已完成 {len(messages)} 項，其餘未套用；請重新 list 核對。")
            return 1, messages
    return 0, messages or ["沒有變更，未寫入設定。"]


def manage(rows, table_renderer, read_current, toggle, *, demo=False):
    try:
        pending = create_app(rows, table_renderer, demo=demo).run()
    except (EOFError, KeyboardInterrupt):
        pending = None
    if pending is None:
        print("已取消，未寫入設定。")
        return 0
    if demo:
        print(f"示範結束：預選 {len(pending)} 項變更，未寫入任何設定。")
        return 0
    status, messages = apply_changes(rows, pending, read_current, toggle)
    for message in messages:
        print(message)
    if pending and status == 0:
        print("設定已更新；重新載入或重啟 Codex／Claude 後確認效果。")
    return status

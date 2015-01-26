from gi.repository import GObject, Gtk, Gdk, Gedit
from re import escape, finditer
from random import randint

ui_str = """<ui>
  <menubar name="MenuBar">
      <menu name="ToolsMenu" action="Tools">
            <placeholder name="ToolsOps_2">
                <menuitem name="Highlight" action="Highlight"/>
                <menuitem name="Clear highlights" action="ClearHighlight"/>
            </placeholder>
        </menu>
    </menubar>
</ui>
"""

class Highlighter:

    def __init__(self):
        self.highlight_list = list()

    def highlight_with_color(self, document, color):
        selected_text = self._get_selected_text(document)
        if selected_text != "":
            self._highlight_occurances(document, selected_text, color)

    def _get_selected_text(self, document):
        selection = ""
        if document.get_selection_bounds():
            start, end = document.get_selection_bounds()
            selection = document.get_text(start, end, False)
        return selection

    def _highlight_occurances(self, document, selection, color):
        begin = document.get_start_iter()
        end = document.get_end_iter()
        text = document.get_text(begin, end, True)
        for match in finditer(escape(selection), text):
            self._highlight(document, match, color)

    def _highlight(self, document, match, color):
        tag_name = self._next_name()
        tag = document.create_tag(tag_name, foreground="#ffffffffffff", background=color.to_string())
        begin = document.get_iter_at_offset(match.start())
        end = document.get_iter_at_offset(match.end())
        document.apply_tag_by_name(tag_name, begin, end)
        self.highlight_list.append(tag_name)

    def _next_name(self):
        num = len(self.highlight_list)
        return "highlight" + str(num)

    def clear(self, document):
        start, end = document.get_bounds()
        for tag_name in self.highlight_list:
            document.remove_tag_by_name(tag_name, start, end)
        del self.highlight_list[:]


class HighlightPlugin(GObject.Object, Gedit.WindowActivatable):
    __gtype_name__ = "HighlightPlugin"

    window = GObject.property(type=Gedit.Window)

    def __init__(self):
        GObject.Object.__init__(self)

    def do_activate(self):
        self._insert_menu()
        self._connect()
        self._plugins = dict()

    def _insert_menu(self):
        self._action_group = Gtk.ActionGroup("HighlightPluginActions")
        self._action_group.add_actions([("Highlight", None, _("Highlight"), "<control>1", _("Highlights selection"), self.highlight)])
        self._action_group.add_actions([("ClearHighlight", None, _("Clear Highlights"), None, _("Clears the highlights"), self.clear)])
        manager = self.window.get_ui_manager()
        manager.insert_action_group(self._action_group, -1)
        self._ui_id = manager.add_ui_from_string(ui_str)

    def highlight(self, action):
        color = self._fetch_color()
        if color:
            document = self.window.get_active_document()
            plugin = self._get_plugin(document)
            plugin.highlight_with_color(document, color)

    def _fetch_color(self):
        color_selector = Gtk.ColorSelectionDialog("Select Color")
        color_selector.get_color_selection().set_has_palette(True)
        random_color = self._random_color()
        color_selector.get_color_selection().set_current_color(random_color)
        response = color_selector.run()
        color = None
        if response == Gtk.ResponseType.OK:
            color = color_selector.get_color_selection().get_current_rgba()
        color_selector.destroy()
        return color

    def _random_color(self):
        r = lambda: randint(0, 255)
        color_string = "#%02X%02X%02X" % (r(), r(), r())
        return Gdk.color_parse(color_string)

    def _get_plugin(self, document):
        if document not in self._plugins:
            self._plugins[document] = Highlighter()
        return self._plugins[document]

    def clear(self, action):
        document = self.window.get_active_document()
        plugin = self._get_plugin(document)
        plugin.clear(document)

    def _connect(self):
        self._signal_handlers = [
            self.window.connect("tab_removed", self.tab_removed)
        ]

    def tab_removed(self, window, tab, data=None):
        document = tab.get_document()
        if document in self._plugins:
            plugin = self._plugins[document]
            plugin.clear(document)
            del self._plugins[document]

    def do_deactivate(self):
        self._disconnect()
        self._remove_menu()
        self._clear_all()
        self._plugins.clear()

    def _clear_all(self):
        for document in self._plugins.keys():
            plugin = self._plugins[document]
            plugin.clear(document)

    def _disconnect(self):
        for handler_id in self._signal_handlers:
            self.window.disconnect(handler_id)
        self._signal_handlers = []

    def _remove_menu(self):
        manager = self.window.get_ui_manager()
        manager.remove_ui(self._ui_id)
        manager.remove_action_group(self._action_group)
        manager.ensure_update()
        self._action_group = None

    def do_update_state(self):
        self._action_group.set_sensitive(self.window.get_active_document() != None)

import sys
import os
import subprocess
import shutil
import string
import re
import enum
import json
import xml
import xml.dom.minidom
import sublime
import sublime_plugin
from . import sbot_common as sc


# Syntax defs.
SYNTAX_C = 'Packages/C++/C.sublime-syntax'
SYNTAX_CPP = 'Packages/C++/C++.sublime-syntax'
SYNTAX_CS = 'Packages/C#/C#.sublime-syntax'
SYNTAX_XML = 'Packages/XML/XML.sublime-syntax'
SYNTAX_LUA = 'Packages/Lua/Lua.sublime-syntax'
SYNTAX_JSON = 'Packages/JSON/JSON.sublime-syntax'


#-----------------------------------------------------------------------------------
def plugin_loaded():
    '''Called per plugin instance.'''
    pass


#-----------------------------------------------------------------------------------
def plugin_unloaded():
    '''Ditto.'''
    pass


#-----------------------------------------------------------------------------------
class SbotEvent(sublime_plugin.EventListener):
    ''' Listener for window events of global interest. '''

    def on_init(self, views):
        ''' First thing that happens when plugin/window created. Initialize everything. '''
        del views

    def on_selection_modified(self, view):
        ''' Show the abs position in the status bar. '''
        caret = sc.get_single_caret(view)
        view.set_status("position", '???' if caret is None else f'Pos {caret}')


#-----------------------------------------------------------------------------------
class SbotSplitViewCommand(sublime_plugin.TextCommand):
    ''' Toggles between split file views. '''

    def run(self, edit):
        del edit
        win = self.view.window()
        caret = sc.get_single_caret(self.view)

        if win is not None:
            if len(win.layout()['rows']) > 2:  # pyright: ignore
                # Remove split.
                win.run_command("focus_group", {"group": 1})
                win.run_command("close_file")
                win.run_command("set_layout", {"cols": [0.0, 1.0], "rows": [0.0, 1.0], "cells": [[0, 0, 1, 1]]})
            elif caret is not None:
                # Add split.
                sel_row, _ = self.view.rowcol(caret)  # current sel
                win.run_command("set_layout", {"cols": [0.0, 1.0], "rows": [0.0, 0.5, 1.0], "cells": [[0, 0, 1, 1], [0, 1, 1, 2]]})
                win.run_command("focus_group", {"group": 0})
                win.run_command("clone_file")
                win.run_command("move_to_group", {"group": 1})
                self.view.run_command("goto_line", {"line": sel_row})


#-----------------------------------------------------------------------------------
class SbotOpenContextPathCommand(sublime_plugin.TextCommand):
    '''
    Borrowed from open_context_url.py. Note - that file is now
    disabled and the function apparently implemented internally.
    '''

    def run(self, edit, event):
        del edit
        path = self.find_path(event)
        sc.open_path(path)

    def is_visible(self, event):
        syn = self.view.syntax()
        path = self.find_path(event)
        return syn is not None and syn.name != 'Notr' and path is not None

    def find_path(self, event):
        ret = None

        # Get the text.
        pt = self.view.window_to_text((event["x"], event["y"]))
        line = self.view.line(pt) # Region
        text = self.view.substr(line)

        # Test all matches on the line against the one where the cursor is.
        rex = re.compile(r'\[(.*)\]\(([^\)]*)\)')
        it = rex.finditer(text)
        for match in it:
            if match.start() <= (pt - line.a) and match.end() >= (pt - line.a):
                path = match.group(2)
                if os.path.exists(path):
                    ret = path
        return ret

    def description(self, event):
        # For menu.
        path = self.find_path(event)
        return f'Open Path {path}'

    def want_event(self):
        return True


#-----------------------------------------------------------------------------------
class SbotTreeCommand(sublime_plugin.WindowCommand):
    ''' Run tree command to a new view. '''

    def run(self, paths=None):
        dir, _, _ = sc.get_path_parts(self.window, paths)

        try:
            # Try treex first.
            cmd = f'treex -c "{dir}"' if shutil.which("treex") else f'tree "{dir}" /a /f'
            cp = subprocess.run(cmd, universal_newlines=True, capture_output=True, shell=True, check=True)
            sc.create_new_view(self.window, cp.stdout)
        except Exception as e:
            sc.create_new_view(self.window, f'Well, that did not go well: {e} {e.__traceback__}')

    def is_visible(self, paths=None):
        dir, _, _ = sc.get_path_parts(self.window, paths)
        return dir is not None


#-----------------------------------------------------------------------------------
class SbotRunCommand(sublime_plugin.WindowCommand):
    '''
    If the clicked file is a script, it is executed and the output presented in a new view.
    Otherwise acts as if you had double-clicked the file in the UI, honors your file associations.
    Supports context and sidebar menus.
    Doesn't support entering user args currently.
    '''

    def run(self, paths=None):
        dir, fn, path = sc.get_path_parts(self.window, paths)

        if fn is not None: # Plain file
            _, ext = os.path.splitext(fn)
            try:
                cmd_list = []
                if ext == '.py':
                    cmd_list.append('python')
                    cmd_list.append(f'\"{path}\"')
                elif ext == '.lua':
                    cmd_list.append('lua')
                    cmd_list.append(f'\"{path}\"')
                elif ext in ['.cmd', '.bat', '.sh']:
                    cmd_list.append(f'\"{path}\"')
                else:
                    # Simple file click.
                    sc.open_path(path)
                    return

                cmd = ' '.join(cmd_list)
                cp = subprocess.run(cmd, cwd=dir, universal_newlines=True, capture_output=True, shell=True)
                output = cp.stdout
                errors = cp.stderr
                if len(errors) > 0:
                    output = output + '============ stderr =============\n' + errors
                sc.create_new_view(self.window, output)
            except Exception as e:
                sc.error(f"Run failed: {e}", e.__traceback__)
        elif dir is not None: # Plain directory
            pass # or??
        elif path.startswith('http'): # Special case.
            sc.open_path(path)
        else:
            sc.error(f"Invalid path: {path}")

    def is_visible(self, paths=None):
        dir, fn, path = sc.get_path_parts(self.window, paths)
        if fn is not None or (path is not None and path.startswith('http')): # Special case.
            return True
        return False


#-----------------------------------------------------------------------------------
class SbotTerminalCommand(sublime_plugin.WindowCommand):
    '''
    Open term in this directory.
    Supports context and sidebar menus.
    '''
    def run(self, paths=None):
        dir, _, _ = sc.get_path_parts(self.window, paths)
        if dir is not None:
            sc.open_terminal(dir)

    def is_visible(self, paths=None):
        dir, _, _ = sc.get_path_parts(self.window, paths)
        return dir is not None



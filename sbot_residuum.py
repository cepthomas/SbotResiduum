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
class SbotSniffBinCommand(sublime_plugin.TextCommand):
    ''' Reports non-ascii characters in the view.'''

    def run(self, edit):
        # This only works on text/view regions so is string-centric.

        # TODO args/settings.
        op = 'xlat' # or 'inst'
        limit = 100

        # Expected binary chars.
        exp = { '\0':'<<NUL>>', '\n':'<<LF>>', '\r':'<<CR>>', '\t':'<<TAB>>', '\033':'<<ESC>>' }

        pos = 0
        regnum = 0
        buff = []

        # Iterate user selections.
        for region in sc.get_sel_regions(self.view):
            if op == 'xlat':
                buff = [f'===== Translation Region {regnum} =====\n']
            else:
                buff = [f'===== Instances Region {regnum} =====\n']

            # Iterate lines in selection.
            line_num = 1
            for line_reg in self.view.split_by_newlines(region):
                col_num = 1

                # Examine each line.
                text = self.view.substr(line_reg)
                for ch in text:
                    if op == 'xlat':
                        if ch >= ' ' and ch <= '~': # ascii printable
                            buff.append(ch)
                        elif ch in exp:
                            buff.append(exp[ch])
                        else: # Everything else is binary.
                            buff.append(f'<<0x{ord(ch):04x}>>')
                            limit -= 1

                    else:
                        if ch >= ' ' and ch <= '~': # ascii printable
                            pass
                        elif ch in exp:
                            pass
                        else: # Everything else is binary.
                            buff.append(f'line:{line_num} col:{col_num} val:0x{ord(ch):04x}\n')
                            limit -= 1

                    col_num += 1
                    pos += 1

                line_num += 1

                if op == 'xlat':
                    buff.append('\n')

                if limit <= 0:
                    break

        sc.create_new_view(self.view.window(), "".join(buff))


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


#-----------------------------------------------------------------------------------
class SbotCopyNameCommand(sublime_plugin.WindowCommand):
    '''
    Get file or directory name to clipboard.
    Supports context and sidebar menus.
    '''
    def run(self, paths=None):
        _, _, path = sc.get_path_parts(self.window, paths)
        if path is not None:
            sublime.set_clipboard(os.path.split(path)[-1])

    def is_visible(self, paths=None):
        _, _, path = sc.get_path_parts(self.window, paths)
        return path is not None


#-----------------------------------------------------------------------------------
class SbotCopyPathCommand(sublime_plugin.WindowCommand):
    '''
    Get file or directory path to clipboard.
    Supports context and sidebar menus.
    '''
    def run(self, paths=None):
        _, _, path = sc.get_path_parts(self.window, paths)
        if path is not None:
            sublime.set_clipboard(path)

    def is_visible(self, paths=None):
        _, _, path = sc.get_path_parts(self.window, paths)
        return path is not None


#-----------------------------------------------------------------------------------
class SbotCopyFileCommand(sublime_plugin.WindowCommand):
    '''
    Copy selected file to the same dir.
    Supports context and sidebar menus.
    '''
    def run(self, paths=None):
        _, fn, path = sc.get_path_parts(self.window, paths)
        if fn is not None and path is not None:
            # Find a valid file name.
            ok = False
            root, ext = os.path.splitext(path)
            for i in range(1, 9):
                newfn = f'{root}_{i}{ext}'
                if not os.path.isfile(newfn):
                    shutil.copyfile(path, newfn)
                    ok = True
                    break

            if not ok:
                sublime.status_message("Couldn't copy file")

    def is_visible(self, paths=None):
        _, fn, _ = sc.get_path_parts(self.window, paths)
        return fn is not None


#-----------------------------------------------------------------------------------
class SbotDeleteFileCommand(sublime_plugin.WindowCommand):
    '''
    Delete the file in the current view.
    Supports context and tab menus.
    '''
    def run(self):  # , paths=None):
        _, fn, path = sc.get_path_parts(self.window, None)
        if fn is not None:
            self.window.run_command("delete_file", {"files": [path], "prompt": False})

    def is_visible(self):  #, paths=None):
        _, fn, _ = sc.get_path_parts(self.window, None)
        return fn is not None


#-----------------------------------------------------------------------------------
class SbotTrimCommand(sublime_plugin.TextCommand):
    '''sbot_trim how=leading|trailing|both'''

    def run(self, edit, how):
        if how == 'leading':
            reo = re.compile('^[ \t]+', re.MULTILINE)
            sub = ''
        elif how == 'trailing':
            reo = re.compile('[\t ]+$', re.MULTILINE)
            sub = ''
        else:  # both
            reo = re.compile('^[ \t]+|[\t ]+$', re.MULTILINE)
            sub = ''
        _do_sub(self.view, edit, reo, sub)


#-----------------------------------------------------------------------------------
class SbotRemoveEmptyLinesCommand(sublime_plugin.TextCommand):
    '''sbot_remove_empty_lines  how=remove_all|normalize'''

    def run(self, edit, how):
        if how == 'normalize':
            reo = re.compile(r'(?:\s*)(\r?\n)(?:\s*)(?:\r?\n+)', re.MULTILINE)
            sub = r'\1\1'
        else:  # remove_all
            reo = re.compile('^[ \t]*$\r?\n', re.MULTILINE)
            sub = ''
        _do_sub(self.view, edit, reo, sub)


#-----------------------------------------------------------------------------------
class SbotRemoveWsCommand(sublime_plugin.TextCommand):
    '''sbot_remove_ws  how=remove_all|keep_eol|normalize'''

    def run(self, edit, how):
        if how == 'normalize':
            # Note: doesn't trim trailing.
            reo = re.compile('([ ])[ ]+')
            sub = r'\1'
        elif how == 'keep_eol':
            reo = re.compile(r'[ \t\v\f]')
            sub = ''
        else:  # remove_all
            reo = re.compile(r'[ \t\r\n\v\f]')
            sub = ''
        _do_sub(self.view, edit, reo, sub)


#-----------------------------------------------------------------------------------
class SbotInsertLineIndexesCommand(sublime_plugin.TextCommand):
    ''' Insert sequential numbers in first column. Default is to start at 1. '''

    def run(self, edit):
        # Iterate lines.
        line_count = self.view.rowcol(self.view.size())[0]
        width = len(str(line_count))
        offset = 0

        for region in sc.get_sel_regions(self.view):
            line_num = 1
            offset = 0
            for line_region in self.view.split_by_newlines(region):
                s = f'{line_num:0{width}} '
                self.view.insert(edit, line_region.a + offset, s)
                line_num += 1
                # Adjust for inserts.
                offset += width + 1


#-----------------------------------------------------------------------------------
class SbotFormatXmlCommand(sublime_plugin.TextCommand):
    ''' Simple formatter for xml. '''

    def is_visible(self):
        # return self.view.settings().get('syntax') == SYNTAX_XML
        # Allow apply to any file type.
        return True

    def run(self, edit):
        del edit
        err = False

        settings = sublime.load_settings(sc.get_settings_fn())
        reg = sc.get_sel_regions(self.view)[0]
        s = self.view.substr(reg)
        tab_size = settings.get('tab_size')

        def clean(node):
            for n in node.childNodes:
                if n.nodeType == xml.dom.minidom.Node.TEXT_NODE:
                    if n.nodeValue:
                        n.nodeValue = n.nodeValue.strip()
                elif n.nodeType == xml.dom.minidom.Node.ELEMENT_NODE:
                    clean(n)

        try:
            top = xml.dom.minidom.parseString(s)
            clean(top)
            top.normalize()
            sindent = ' ' * int(tab_size)  # pyright: ignore
            s = top.toprettyxml(indent=sindent)
        except Exception as e:
            s = f"Error: {e}"
            err = True

        vnew = sc.create_new_view(self.view.window(), s)
        if not err:
            vnew.set_syntax_file(SYNTAX_XML)


#-----------------------------------------------------------------------------------
class SbotFormatCxCommand(sublime_plugin.TextCommand):
    ''' Simple formatter for C/C++/C# family. '''

    def is_visible(self):
        syntax = self.view.settings().get('syntax')
        return syntax in [SYNTAX_C, SYNTAX_CPP, SYNTAX_CS]

    def run(self, edit):
        del edit

        # Current syntax.
        syntax = str(self.view.settings().get('syntax'))
        settings = sublime.load_settings(sc.get_settings_fn())
        reg = sc.get_sel_regions(self.view)[0]
        s = self.view.substr(reg)
        tab_size = settings.get('tab_size')

        # Build the command. Uses --style=allman --indent=spaces=4 --indent-col1-comments --errors-to-stdout
        sindent = f"-s{tab_size}"
        p = ['astyle', '-A1', sindent, '-Y', '-X']
        if syntax == 'C#': # else default of C
            p.append('--mode=cs')

        try:
            cp = subprocess.run(p, input=s, text=True, universal_newlines=True, capture_output=True, shell=True, check=True)
            sout = cp.stdout
        except Exception:
            sout = "Format Cx failed. Is astyle installed and in your path?"

        vnew = sc.create_new_view(self.view.window(), sout)
        vnew.set_syntax_file(syntax)


#-----------------------------------------------------------------------------------
class SbotFormatJsonCommand(sublime_plugin.TextCommand):
    ''' Simple formatter for json. '''

    def is_visible(self):
        # return self.view.settings().get('syntax') == SYNTAX_JSON
        # Allow apply to any file type.
        return True

    def run(self, edit):
        del edit
        err = False

        reg = sc.get_sel_regions(self.view)[0]
        s = self.view.substr(reg)

        class ScanState(enum.IntFlag):
            DEFAULT = enum.auto()   # Idle
            STRING = enum.auto()    # Process a quoted string
            LCOMMENT = enum.auto()  # Processing a single line comment
            BCOMMENT = enum.auto()  # Processing a block/multiline comment
            DONE = enum.auto()      # Finito

        settings = sublime.load_settings(sc.get_settings_fn())
        tab_size = settings.get('tab_size')
        comment_count = 0
        sreg = []
        state = ScanState.DEFAULT
        current_comment = []
        current_char = -1
        next_char = -1
        escaped = False

        # Index is in cleaned version, value is in original.
        pos_map = []

        # Iterate the string.
        try:
            slen = len(s)
            i = 0
            while i < slen:
                current_char = s[i]
                next_char = s[i + 1] if i < slen - 1 else -1

                # Remove whitespace and transform comments into legal json.
                if state == ScanState.STRING:
                    sreg.append(current_char)
                    pos_map.append(i)
                    # Handle escaped chars.
                    if current_char == '\\':
                        escaped = True
                    elif current_char == '\"':
                        if not escaped:
                            state = ScanState.DEFAULT
                        escaped = False
                    else:
                        escaped = False

                elif state == ScanState.LCOMMENT:
                    # Handle line comments.
                    if current_char == '\n':
                        # End of comment.
                        scom = ''.join(current_comment)
                        stag = f'\"//{comment_count}\":\"{scom}\",'
                        comment_count += 1
                        sreg.append(stag)
                        pos_map.append(i)
                        state = ScanState.DEFAULT
                        current_comment.clear()
                    elif current_char == '\r':
                        # ignore
                        pass
                    else:
                        # Maybe escape.
                        if current_char == '\"' or current_char == '\\':
                            current_comment.append('\\')
                        current_comment.append(current_char)

                elif state == ScanState.BCOMMENT:
                    # Handle block comments.
                    if current_char == '*' and next_char == '/':
                        # End of comment.
                        scom = ''.join(current_comment)
                        stag = f'\"//{comment_count}\":\"{scom}\",'
                        comment_count += 1
                        sreg.append(stag)
                        pos_map.append(i)
                        state = ScanState.DEFAULT
                        current_comment.clear()
                        i += 1  # Skip next char.
                    elif current_char == '\n' or current_char == '\r':
                        # ignore
                        pass
                    else:
                        # Maybe escape.
                        if current_char == '\"' or current_char == '\\':
                            current_comment.append('\\')
                        current_comment.append(current_char)

                elif state == ScanState.DEFAULT:
                    # Check for start of a line comment.
                    if current_char == '/' and next_char == '/':
                        state = ScanState.LCOMMENT
                        current_comment.clear()
                        i += 1  # Skip next char.
                    # Check for start of a block comment.
                    elif current_char == '/' and next_char == '*':
                        state = ScanState.BCOMMENT
                        current_comment.clear()
                        i += 1  # Skip next char.
                    elif current_char == '\"':
                        sreg.append(current_char)
                        pos_map.append(i)
                        state = ScanState.STRING
                    # Skip ws.
                    elif current_char not in string.whitespace:
                        sreg.append(current_char)
                        pos_map.append(i)

                else:  # state == ScanState.DONE:
                    pass
                i += 1  # next

            # Prep for formatting.
            sout = ''.join(sreg)

            # Remove any trailing commas.
            sout = re.sub(',}', '}', sout)
            sout = re.sub(',]', ']', sout)

            # Run it through the formatter.
            sout = json.loads(sout)
            sout = json.dumps(sout, indent=int(tab_size))  # pyright: ignore

        except json.JSONDecodeError as je:
            # Get some context from the original string.
            context = []
            original_pos = pos_map[je.pos]
            start_pos = max(0, original_pos - 40)
            end_pos = min(len(s) - 1, original_pos + 40)
            context.append(f'Json Error: {je.msg} pos: {original_pos}')
            context.append(s[start_pos:original_pos])
            context.append('---------here----------')
            context.append(s[original_pos:end_pos])
            sout = '\n'.join(context)
            err = True

        vnew = sc.create_new_view(self.view.window(), sout)
        if not err:
            vnew.set_syntax_file(SYNTAX_JSON)


#-----------------------------------------------------------------------------------
def _do_sub(view, edit, reo, sub):
    # Generic substitution function.
    for region in sc.get_sel_regions(view):
        orig = view.substr(region)
        new = reo.sub(sub, orig)
        view.replace(edit, region, new)

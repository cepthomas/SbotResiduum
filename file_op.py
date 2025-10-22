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


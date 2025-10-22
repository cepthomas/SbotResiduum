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



# These are what appear in ST: https://www.vertex42.com/ExcelTips/unicode-symbols.html
#   also:  https://www.fileformat.info/info/unicode/category/So/list.htm
# B/W versions of above (in my font i.e Word):  https://symbl.cc/en/unicode-table/
# My font:  Cascadia Code  https://fonts.google.com/specimen/Cascadia+Code
# py code with all symbols by name:  https://github.com/mvoidex/UnicodeMath
# picker:  https://packages.sublimetext.io/packages/Unicode%20Character%20Insert/
#   also: https://github.com/randy3k/UnicodeCompletion


# Supported menu type is C</b>ontext, <b>S</b>idebar, <b>T</b>ab.

# Tools on views:
#   ops:
#       'translate' to new view (doesn't help with line ends) [bin -> translate] C (view) or S (file) :: colorize unicode/bin
#       'instances' to new view (ditto) [bin -> instances] C (view) or S (file)
#       'hex' to new view (ditto) [bin -> hex] C (view) or S (file) :: colorize unicode/bin
#   find/replace - just use native ST in View [NA]
#   insert/edit unicode from numerical/clipboard/region (dec/hex) [bin -> insert?] C (view)
#   insert/edit unicode from glyph picker [bin -> insert?] C (view)
#
# Tools on files:
#   find/replace unicodes value(s) -> value(s) [or just open view and do there]
#   fix/show/analyze line ends? [bin -> line_ends] S (file)  like C# SniffBin?
#
# optargs: how???
#   start/end addr
#   output to terminal w/more etc,
# 
# settings:
#   limit for instances etc = 100
#   limit other? = 100000
#   delims = ["<<", ">>"]
#   colors = { "0": "markup.user_hl3", "27": "reddish" } // NUL  ESC


#-----------------------------------------------------------------------------------
def plugin_loaded():
    '''Called per plugin instance.'''
    pass


#-----------------------------------------------------------------------------------
def plugin_unloaded():
    '''Ditto.'''
    pass





#-----------------------------------------------------------------------------------
class BinXxxWindowCommand(sublime_plugin.WindowCommand):
    '''
    Open term in this directory.
    Supports context and sidebar menus.
    '''
    def run(self, paths=None):
        dir, fn, path = sc.get_path_parts(self.window, paths)
        if dir is not None:
            sc.open_terminal(dir)

    def is_visible(self, paths=None):
        dir, fn, path = sc.get_path_parts(self.window, paths)
        return dir is not None







#-----------------------------------------------------------------------------------
class BinXxxCommand(sublime_plugin.TextCommand):

    def run(self, edit): #, arg...
        # This only works on text/view regions so is string-centric.

        # TODO args/settings.
        op = 'xlat' # or 'inst'
        limit = 100


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
class BinDevCommand(sublime_plugin.TextCommand):
    '''Converts all selections to unicode characters, if applicable.'''
    # https://forum.sublimetext.com/t/options-for-typing-unicode-characters/29818/6

    def run(self, edit):

        # from https://www.vertex42.com/ExcelTips/unicode-symbols.html
        ##  <<0x 0001F30B >>  <<0x 0001F44E >>
        ##  << 127755 >>  << 128078 >>

        buff = []
        # for i in range(0x0001F30B, 0x0001F40B):
        for i in range(0, 10):
            buff.append(chr(0x0001F300 + i))
        sc.create_new_view(self.view.window(), "".join(buff))



        # for region in self.view.sel():
        #     candidate = self.view.substr(region)

        #     try:
        #         number = int(candidate, 16) # assumes hex
        #     except Exception as e:
        #         sublime.error_message(f'Failed to convert "{candidate}" into a decimal number.')
        #         continue

        #     try:
        #         character = chr(number)
        #     except ValueError as e:
        #         sublime.error_message(f'Failed to convert {number} (0X{candidate}). Probably not a valid unicode code point.')
        #         continue

        #     except OverflowError as e:
        #         sublime.error_message(f'{candidate} is too big of a number...')
        #         continue

        #     # Everything went okay. Let's replace the selection by the unicode character.
        #     # self.view.replace(edit, region, character)
        #     sc.create_new_view(self.view.window(), character)



    def run_not(self, edit):

        ##  <<0x 0001F30B >>  <<0x 0001F44E >>
        ##  << 127755 >>  << 128078 >>

        # buff = []
        # buff.append(33) #'|')
        # # buff.append(0x0001f30b)
        # buff.append(0x0bf30100)
        # buff.append(33) #'|')
        # buff.append(0x0001f44e)
        # buff.append(33) #'|')


        # https://docs.python.org/3/library/stdtypes.html#bytes-objects
        # >>> list_of_values = [0x55, 0x33, 0x22]
        # >>> bytes_of_values = bytes(list_of_values)
        # >>> bytes_of_values == b'\x55\x33\x22'
        # True
        # >>> bytes_of_values
        # b'U3"'

        # buff = bytes([0x55, 0x33, 0x22])
        buff = bytearray([48, 0x33, 57])

        # https://docs.python.org/3/library/stdtypes.html#bytearray-objects


        sc.create_new_view(self.view.window(), buff)


#-----------------------------------------------------------------------------------
def _do_sub(view, edit, reo, sub):
    # Generic substitution function.
    for region in sc.get_sel_regions(view):
        orig = view.substr(region)
        new = reo.sub(sub, orig)
        view.replace(edit, region, new)

import sys
import os
import subprocess
import shutil
import string
import re
import enum
import sublime
import sublime_plugin
from . import sbot_common as sc



# These are what appear in ST: https://www.vertex42.com/ExcelTips/unicode-symbols.html
#     https://www.fileformat.info/info/unicode/category/So/list.htm
# B/W versions of above (in my font i.e Word):  https://symbl.cc/en/unicode-table/

# py code with all symbols by name:  https://github.com/mvoidex/UnicodeMath
# unicode picker:  https://packages.sublimetext.io/packages/Unicode%20Character%20Insert/
#               :  https://github.com/randy3k/UnicodeCompletion

# https://en.wikipedia.org/wiki/UTF-8
# Convert codepoint to memory bytes
# UTF-8 encodes code points in one to four bytes, depending on the value of the code point. In the following table,
# the characters u to z are replaced by the bits of the code point, from the positions U+uvwxyz:
# First CP  Last CP   Byte 1    Byte 2    Byte 3    Byte 4
# U+0000    U+007F    0yyyzzzz
# U+0080    U+07FF    110xxxyy  10yyzzzz
# U+0800    U+FFFF    1110wwww  10xxxxyy  10yyzzzz
# U+010000  U+10FFFF  11110uvv  10vvwwww  10xxxxyy  10yyzzzz
#
# The first 128 code points (ASCII) need 1 byte. The next 1,920 code points need two bytes to encode, which covers
# the remainder of almost all Latin-script alphabets, and also IPA extensions, Greek, Cyrillic, Coptic, Armenian,
# Hebrew, Arabic, Syriac, Thaana and N'Ko alphabets, as well as Combining Diacritical Marks.
# Three bytes are needed for the remaining 61,440 codepoints of the Basic Multilingual Plane (BMP), including most
# Chinese, Japanese and Korean characters. Four bytes are needed for the 1,048,576 non-BMP code points, which
# include emoji, less common CJK characters, and other useful characters.[15]

# codepoint U+1F308 -> mem F0 9F 8C 8B
# Translate: 01 F3 0B -- 00000001 11110011 00001011
# Misc Symbols and Pictographs (U+1F300 to U+1F5FF)


# Tools on views C (view):
#   op:'translate' to new view (doesn't help with line ends) [bin -> translate] :: colorize unicode/bin
#   op:'instance' to new view (ditto) [bin -> instance]
#   op:'hex' to new view (ditto) [bin -> hex] :: colorize unicode/bin
#   ? find/replace - just use native ST in View [NA]
#   insert/edit unicode from numerical/clipboard/region (dec/hex) [bin -> insert?]
#   insert/edit unicode from glyph picker [bin -> insert?]
#
# Tools on files S (file):
#   dump hex
#   ? find/replace unicodes value(s) -> value(s) [or just open view and do there]
#   ? fix/show/analyze line ends? [bin -> line_ends]  like C# SniffBin?
#
# optargs: how?
#   ? start/end addr
#   ? output to terminal w/more etc instead of view - setting?

# Expected/common binary chars.
expect_bin = { '\0':'NUL', '\n':'LF', '\r':'CR', '\t':'TAB', '\033':'ESC' }


# { "caption": "Bin Translate", "command": "binstr_translate" },
# { "caption": "Bin Instance", "command": "binstr_instance" },
# { "caption": "Bin Dump", "command": "binstr_dump" },


#       'translate' to new view (doesn't help with line ends) [bin -> translate] C (view) or S (file) :: colorize unicode/bin
#       'instance' to new view (ditto) [bin -> instance] C (view) or S (file)
#       'hex' to new view (ditto) [bin -> hex] C (view) or S (file) :: colorize unicode/bin



#-----------------------------------------------------------------------------------
class BinstrTranslateCommand(sublime_plugin.TextCommand):

    def run(self, edit):
        del edit
        # err = False

        start_offset = 0 # in view
        # len = 0 # 0 = all

        settings = sublime.load_settings(sc.get_settings_fn())
        instance_limit = int(settings.get('instance_limit'))   # pyright: ignore
        translate_delims = settings.get('translate_delims')
        bin_color = str(settings.get('bin_color'))
        unicode_color = str(settings.get('unicode_color'))
        left_delim = translate_delims[0] or ''   # pyright: ignore
        right_delim = translate_delims[1] or ''   # pyright: ignore

        in_pos = 0 # input text
        out_pos = 0
        regnum = 0
        buff = []
        # junk = [111]
        region = sc.get_sel_regions(self.view)[0] # TODO handle multiple regions?

        # print('***', region)

        # buff_index : "color"
        # colors = {}
        bin_regions = []
        unicode_regions = []

        # buff = [f'===== Translation Region {regnum} =====\n']
        # Iterate lines in selection.
        line_num = 1
        for region_line in self.view.split_by_newlines(region):
            col_num = 1
            text = self.view.substr(region_line)
            for codepoint in text:
                if codepoint >= ' ' and codepoint <= '~': # ascii printable
                    buff.append(codepoint)
                    out_pos += 1
                elif codepoint in expect_bin:
                    # colors[len(buff)] = bin_color
                    # buff.append(expect_bin[codepoint])
                    start_pos = out_pos
                    sout = expect_bin[codepoint]
                    buff.append(sout)
                    out_pos += len(sout)
                    bin_regions.append(sublime.Region(start_pos, out_pos)) # color range

                else: # Everything else is binary. codepoint is the codepoint
                    start_pos = out_pos
                    sout = f'{left_delim}CP{ord(codepoint):04X}{right_delim}'
                    buff.append(sout)
                    out_pos += len(sout)
                    if codepoint < ' ':
                        bin_regions.append(sublime.Region(start_pos, out_pos))
                    else:
                        unicode_regions.append(sublime.Region(start_pos, out_pos))
                    # limit -= 1

                col_num += 1
                in_pos += 1

            line_num += 1
            buff.append('\n')
            out_pos += 1 # for LF

        new_view = sc.create_new_view(self.view.window(), "".join(buff))

        new_view.add_regions(key='bin_regions', regions=bin_regions, scope=bin_color)
        new_view.add_regions(key='unicode_regions', regions=unicode_regions, scope=unicode_color)


# >>> chr(97)
# 'a'
# >>> ord('a')
# 97




#-----------------------------------------------------------------------------------
class BinstrInstanceCommand(sublime_plugin.TextCommand):

    def run(self, edit):
        del edit
        # err = False

        start_offset = 0 # in view
        # len = 0 # 0 = all

        settings = sublime.load_settings(sc.get_settings_fn())
        instance_limit = int(settings.get('instance_limit'))   # pyright: ignore
        translate_delims = settings.get('translate_delims')
        bin_color = str(settings.get('bin_color'))
        unicode_color = str(settings.get('unicode_color'))
        left_delim = translate_delims[0] or ''   # pyright: ignore
        right_delim = translate_delims[1] or ''   # pyright: ignore

        in_pos = 0 # input text
        out_pos = 0
        regnum = 0
        buff = []
        # junk = [111]
        region = sc.get_sel_regions(self.view)[0] # TODO handle multiple regions?

        # print('***', region)

        # buff_index : "color"
        # colors = {}
        bin_regions = []
        unicode_regions = []



        # buff = [f'===== Instances Region {regnum} =====\n']
        # Iterate lines in selection.
        line_num = 1
        for region_line in self.view.split_by_newlines(region):
            col_num = 1

            # Examine each line.
            text = self.view.substr(region_line)
            for codepoint in text:
                if codepoint >= ' ' and codepoint <= '~': # ascii printable
                    pass
                elif codepoint in expect_bin:
                    # sout = expect_bin[codepoint]
                    # buff.append(sout)
                    buff.append(f'line:{line_num} col:{col_num} val:{expect_bin[codepoint]}\n')
                else: # Everything else is binary of interest.
                    buff.append(f'line:{line_num} col:{col_num} val:0x{ord(codepoint):04X}\n')
                    instance_limit -= 1

                col_num += 1
                in_pos += 1

            line_num += 1
            if instance_limit <= 0:
                break


        new_view = sc.create_new_view(self.view.window(), "".join(buff))

        new_view.add_regions(key='bin_regions', regions=bin_regions, scope=bin_color)
        new_view.add_regions(key='unicode_regions', regions=unicode_regions, scope=unicode_color)

# >>> chr(97)
# 'a'
# >>> ord('a')
# 97


#-----------------------------------------------------------------------------------
class BinstrDumpCommand(sublime_plugin.WindowCommand): #TODO1
    '''
    Get file or directory name to clipboard.
    Supports context and sidebar menus.
    '''
    def run(self, paths=None):
        # _, _, path = sc.get_path_parts(self.window, paths)
        # if path is not None:
        #     sublime.set_clipboard(os.path.split(path)[-1])
        
    # def run(self, paths=None):
    #     _, _, path = sc.get_path_parts(self.window, paths)
    #     if path is not None:
    #         sublime.set_clipboard(path)

    # def is_visible(self, paths=None):
    #     _, _, path = sc.get_path_parts(self.window, paths)
    #     return path is not None

        start_offset = 0 # in view
        # len = 0 # 0 = all

        settings = sublime.load_settings(sc.get_settings_fn())
        instance_limit = int(settings.get('instance_limit'))   # pyright: ignore
        translate_delims = settings.get('translate_delims')
        bin_color = str(settings.get('bin_color'))
        unicode_color = str(settings.get('unicode_color'))
        left_delim = translate_delims[0] or ''   # pyright: ignore
        right_delim = translate_delims[1] or ''   # pyright: ignore



        # in_pos = 0 # input text
        # out_pos = 0
        # regnum = 0
        # buff = []
        # # junk = [111]
        # region = sc.get_sel_regions(self.view)[0] # TODO handle multiple regions?

        # # print('***', region)

        # # buff_index : "color"
        # # colors = {}
        # bin_regions = []
        # unicode_regions = []


        # # buff = [f'===== Hex Region {regnum} =====\n']

        # text = self.view.substr(region)

        # if len(text) == 0:
        #     sc.error("No text")
        #     return

        # pad = 16 - len(text) % 16
        # for p in range(0, pad):
        #     text += ''

        # num_rows = len(text) // 16

        # for r in range(0, num_rows):
        #     row_addr = r * 16
        #     trow = [f'0x{row_addr:04x}']

        #     for c in range(0, 16):
        #         v = ord(text[r * 16 + c])
        #         trow.append(f' {v:02x}')

        #     trow.append('\n')
        #     buff.append("".join(trow))


        # 0x00c0 20 50 4c 20 4e 6f 20 20 20 20 20 20 20 20 20 59
        # 0x00d0 65 73 0a 0a 0a 47 6f 20 67 6f 20 67 6f 3a 20 23
        # 0x00e0 23 1f30b 23 23 1f44e 23 23 1f30d 23 23 0a 54 72 61 6e 73
        # 0x00f0 6c 61 74 65 3a 20 23 23 3c 3c 30 78 31 66 33 30
        # 0x0100 62 3e 3e 23 23 3c 3c 30 78 31 66 34 34 65 3e 3e
        # 0x0110 23 23 3c 3c 30 78 31 66 33 30 64 3e 3e 23 23 0a
        # 0x0120 0a 2d 2d 2d 2d 3e 1f3be 20 2d 2d 2d 3e 1f680 0a 0a 43
        # 0x0130 3a 5c 50 72 6f 00 67 72 61 6d 20 46 69 6c 65 73
        # 0x0140 5c 53 75 62 6c 69 6d 65 20 1f4dd 20 54 65 78 74 20
        # 0x0150 33 3e 64 69 72 0a 30 78 30 32 3a 20 02 0a 30 78
        # 0x0160 30 31 3a 20 01 0a 44 69 72 65 63 74 6f 72 79 20
        # 0x0170 6f 202d 66 20 43 3a 5c 50 72 6f 7c 3f 7c 67 72 61
        # 0x0180 6d 20 46 69 6c 65 73 5c 53 75 62 6c 69 6d 65 20
        # 0x0190 54 65 78 74 20 33 0a 7c 3b7 7c 2297 7c 2261 7c 0a 0a
        # 0x01a0 48 65 72 65 27 73 20 73 6f 6d 65 20 65 6d 62 65
        # 0x01b0 64 64 65 64 20 61 6e 73 69 20 63 6f 6c 6f 72 20
        # 0x01c0 63 6f 64 65 73 21 20 1b 5b 33 38 3b 32 3b 32 30

        # new_view = sc.create_new_view(self.view.window(), "".join(buff))

        # new_view.add_regions(key='bin_regions', regions=bin_regions, scope=bin_color)
        # new_view.add_regions(key='unicode_regions', regions=unicode_regions, scope=unicode_color)

    def is_visible(self, paths=None):
        _, _, path = sc.get_path_parts(self.window, paths)
        return path is not None






#------------------------ messing around -----------------------------------------------
class BinstrDevCommand(sublime_plugin.TextCommand):
    '''Converts all selections to unicode characters, if applicable.'''
    # https://forum.sublimetext.com/t/options-for-typing-unicode-characters/29818/6

    def run(self, edit):
        # del edit

        # from https://www.vertex42.com/ExcelTips/unicode-symbols.html
        ##  <<0x 0001F30B >>  <<0x 0001F44E >>
        ##  << 127755 >>  << 128078 >>

        buff = []
        # for i in range(0x0001F30B, 0x0001F40B):
        for i in range(0, 10):
            buff.append(chr(0x0001F300 + i))
        sc.create_new_view(self.view.window(), "".join(buff))


        # Example that reads selected text/number:
        #
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


#----------------------------- original attempt -------------------------------------
class SniffBinCommand(sublime_plugin.TextCommand):
    ''' Reports non-ascii characters in the view.'''

    def run(self, edit, op_type):
        del edit
        err = False

        op = 'aaa'

        # Expected binary chars.
        exp = { '\0':'<<NUL>>', '\n':'<<LF>>', '\r':'<<CR>>', '\t':'<<TAB>>', '\033':'<<ESC>>' }

        pos = 0
        regnum = 0
        buff = []
        limit = 100


        # Iterate user selections.
        for region in sc.get_sel_regions(self.view):
            if op == 'xlat':
                buff = [f'===== Translation Region {regnum} =====\n']
            else:
                buff = [f'===== Instances Region {regnum} =====\n']

            # Iterate lines in selection.
            line_num = 1
            for region_line in self.view.split_by_newlines(region):
                col_num = 1

                # Examine each line.
                text = self.view.substr(region_line)
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


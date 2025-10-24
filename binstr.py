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


# Expected/common binary chars.
expect_bin = { '\0':'NUL', '\n':'LF', '\r':'CR', '\t':'TAB', '\033':'ESC' }


#-----------------------------------------------------------------------------------
class SbotBinTranslateCommand(sublime_plugin.TextCommand):

    def run(self, edit):
        del edit

        settings = sublime.load_settings(sc.get_settings_fn())
        translate_delims = settings.get('translate_delims')
        color_ascii = str(settings.get('color_ascii'))
        color_unicode = str(settings.get('color_unicode'))
        left_delim = translate_delims[0] or ''   # pyright: ignore
        right_delim = translate_delims[1] or ''   # pyright: ignore

        in_pos = 0 # input text
        out_pos = 0

        buff = []
        regions_ascii = []
        regions_unicode = []

        region = sc.get_sel_regions(self.view)[0] # TODO handle multiple regions?

        # Iterate lines in selection.
        line_num = 1
        for region_line in self.view.split_by_newlines(region):
            col_num = 1
            text = self.view.substr(region_line)
            for ch in text:
                if ch >= ' ' and ch <= '~': # ascii printable
                    buff.append(ch)
                    out_pos += 1

                elif ch in expect_bin:
                    start_pos = out_pos
                    sout = expect_bin[ch]
                    buff.append(sout)
                    out_pos += len(sout)
                    regions_ascii.append(sublime.Region(start_pos, out_pos)) # color range

                else: # Everything else is binary.
                    start_pos = out_pos

                    if ch < ' ':
                        sout = f'{left_delim}0x{ord(ch):02X}{right_delim}'
                        buff.append(sout)
                        out_pos += len(sout)
                        regions_ascii.append(sublime.Region(start_pos, out_pos))
                    else:
                        sout = f'{left_delim}U+{ord(ch):04X}{right_delim}'
                        buff.append(sout)
                        out_pos += len(sout)
                        regions_unicode.append(sublime.Region(start_pos, out_pos))

                col_num += 1
                in_pos += 1

            line_num += 1
            buff.append('\n')
            out_pos += 1 # for LF

        new_view = sc.create_new_view(self.view.window(), ''.join(buff))
        new_view.add_regions(key='regions_ascii', regions=regions_ascii, scope=color_ascii)
        new_view.add_regions(key='regions_unicode', regions=regions_unicode, scope=color_unicode)


#-----------------------------------------------------------------------------------
class SbotBinInstanceCommand(sublime_plugin.TextCommand):

    def run(self, edit):
        del edit

        settings = sublime.load_settings(sc.get_settings_fn())
        instance_limit = int(settings.get('instance_limit'))   # pyright: ignore
        translate_delims = settings.get('translate_delims')
        color_ascii = str(settings.get('color_ascii'))
        color_unicode = str(settings.get('color_unicode'))

        in_pos = 0 # input text

        buff = []
        regions_ascii = []
        regions_unicode = []

        region = sc.get_sel_regions(self.view)[0] # TODO handle multiple regions?

        # Iterate lines in selection.
        line_num = 1
        for region_line in self.view.split_by_newlines(region):
            col_num = 1

            # Examine each line.
            text = self.view.substr(region_line)
            for ch in text:
                if ch >= ' ' and ch <= '~': # ascii printable
                    pass

                elif ch in expect_bin:
                    buff.append(f'line:{line_num} col:{col_num} val:{expect_bin[ch]}\n')

                else: # Everything else is binary of interest.

                    if ch < ' ':
                        buff.append(f'line:{line_num} col:{col_num} val:0x{ord(ch):02X}\n')
                    else:
                        buff.append(f'line:{line_num} col:{col_num} val:U+{ord(ch):02X}\n')

                    instance_limit -= 1

                col_num += 1
                in_pos += 1

            line_num += 1
            if instance_limit <= 0:
                break

        new_view = sc.create_new_view(self.view.window(), ''.join(buff))
        new_view.add_regions(key='regions_ascii', regions=regions_ascii, scope=color_ascii)
        new_view.add_regions(key='regions_unicode', regions=regions_unicode, scope=color_unicode)


#-----------------------------------------------------------------------------------
class SbotBinDumpCommand(sublime_plugin.WindowCommand):
    ''' zzz.'''
    def run(self, paths=None):
        ''' zzz.'''
        _, _, path = sc.get_path_parts(self.window, paths)

        buff = []
        regions_ascii = []
        regions_unicode = []

        settings = sublime.load_settings(sc.get_settings_fn())
        color_ascii = str(settings.get('color_ascii'))
        color_unicode = str(settings.get('color_unicode'))

        ROW_SIZE = 16
        READ_ROWS = 256 # per block
        BLOCK_SIZE = READ_ROWS * ROW_SIZE

        file_row = 0 # offset in file

        with open(str(path), 'rb') as f:
            done = False
            multibyte = False
            color_region_start = 0

            while not done:
                bytes_read = f.read(BLOCK_SIZE)
                blen = len(bytes_read)

                # Process new array.
                num_rows = blen // ROW_SIZE
                residual = 0

                # Check for last block.
                if blen < BLOCK_SIZE:
                    done = True
                    residual = blen % ROW_SIZE

                for row in range(0, num_rows):
                    row_addr = file_row * ROW_SIZE
                    trow = [f'0s{row_addr:04X}']

                    for b in range(0, ROW_SIZE):
                        v = bytes_read[row * ROW_SIZE + b]
                        trow.append(f' {v:02X}')

                    trow.append('\n')
                    buff.append(''.join(trow))
                    file_row += 1

                if residual:
                    row_addr = file_row * ROW_SIZE
                    trow = [f'0x{row_addr:04X}']

                    # for b in bytes_read[-residual:]:
                    #     trow.append(f' {b:02X}')


                    for b in range(0, ROW_SIZE):
                        v = bytes_read[row * ROW_SIZE + b]
                        trow.append(f' {v:02X}')


                    trow.append('\n')
                    buff.append(''.join(trow))
                    file_row += 1

        new_view = sc.create_new_view(self.window, ''.join(buff))
        new_view.add_regions(key='regions_ascii', regions=regions_ascii, scope=color_ascii)
        new_view.add_regions(key='regions_unicode', regions=regions_unicode, scope=color_unicode)

    def is_visible(self, paths=None):
        _, _, path = sc.get_path_parts(self.window, paths)
        return path is not None


#------------------------ messing around -----------------------------------------------
class SbotBinDevCommand(sublime_plugin.TextCommand):
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
        sc.create_new_view(self.view.window(), ''.join(buff))


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

        sc.create_new_view(self.view.window(), ''.join(buff))


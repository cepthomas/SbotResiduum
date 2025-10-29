import sys
import sublime
import sublime_plugin
from . import sbot_common as sc


# TODO Insert/edit unicode from numerical/clipboard/region or from glyph picker.


# Expected/common binary chars.
com_bin = { '\0':'NUL', '\n':'LF', '\r':'CR', '\t':'TAB', '\033':'ESC' }


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

        buff = []
        regions_ascii = []
        regions_unicode = []
        out_pos = 0 # in output view

        region = sc.get_sel_regions(self.view)[0] 

        # Iterate lines in selection.
        for region_line in self.view.split_by_newlines(region):
            text = self.view.substr(region_line)
            for ch in text:
                if ch >= ' ' and ch <= '~': # ascii printable
                    buff.append(ch)
                    out_pos += 1

                elif ch in com_bin:
                    start_pos = out_pos
                    sout = com_bin[ch]
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
        output_limit = int(settings.get('output_limit'))   # pyright: ignore
        color_ascii = str(settings.get('color_ascii'))
        color_unicode = str(settings.get('color_unicode'))

        in_pos = 0 # input text

        buff = []
        regions_ascii = []
        regions_unicode = []

        region = sc.get_sel_regions(self.view)[0] 

        # Iterate lines in selection.
        line_num = 1
        for region_line in self.view.split_by_newlines(region):
            col_num = 1

            # Examine each line.
            text = self.view.substr(region_line)
            for ch in text:
                if ch >= ' ' and ch <= '~': # ascii printable
                    pass
                elif ch in com_bin:
                    buff.append(f'line:{line_num} col:{col_num} val:{com_bin[ch]}\n')
                else: # Everything else is binary of interest.
                    if ch < ' ':
                        buff.append(f'line:{line_num} col:{col_num} val:0x{ord(ch):02X}\n')
                    else:
                        buff.append(f'line:{line_num} col:{col_num} val:U+{ord(ch):02X}\n')
                    output_limit -= 1

                col_num += 1
                in_pos += 1

            line_num += 1
            if output_limit <= 0:
                buff.append(f'===== Truncated =====\n')
                break

        new_view = sc.create_new_view(self.view.window(), ''.join(buff))
        new_view.add_regions(key='regions_ascii', regions=regions_ascii, scope=color_ascii)
        new_view.add_regions(key='regions_unicode', regions=regions_unicode, scope=color_unicode)


#-----------------------------------------------------------------------------------
class SbotBinDumpCommand(sublime_plugin.WindowCommand):

    start_addr = 0 # -1 = invalid
    rows_to_read = 0 # num to read or 0 for all
    out_pos = 0 # byte position for capturing regions
    lsrow = [] # current row parts
    last_input = ''
    fn = '' # source

    def run(self, paths, sel_addr_range):

        # Reset.
        self.start_addr = 0
        self.rows_to_read = 0
        self.out_pos = 0
        _, _, self.fn = sc.get_path_parts(self.window, paths)

        # User options?
        if sel_addr_range:
            self.window.show_input_panel('Enter: address [length]', self.last_input, self.on_user_entry, None, None)
        else:
            self.do_work()

    def on_user_entry(self, text):
        # Reset.
        self.start_addr = 0
        self.rows_to_read = 0
        self.out_pos = 0
        # print('--!', text)

        # Process the user input. Address can be hex or decimal.
        parts = text.upper().split(' ')
        if len(parts) >= 1:
            try:
                if 'X' in parts[0]:
                    self.start_addr = int(parts[0].replace('X', ''), 16)
                else:
                    self.start_addr = int(parts[0], 10)
                if len(parts) == 2:
                    self.rows_to_read = int(parts[1], 10)
            except:
                # print('--!', e)
                self.start_addr = -1

        if self.start_addr == -1:
            sc.error(f'Invalid address/rows')
            return

        self.last_input = text # save
        self.do_work() # go

    def do_work(self):
        ROW_SIZE = 16
        buff = []
        regions_ascii = []
        regions_unicode = []

        settings = sublime.load_settings(sc.get_settings_fn())
        color_ascii = str(settings.get('color_ascii'))
        color_unicode = str(settings.get('color_unicode'))
        output_limit = int(settings.get('output_limit'))   # pyright: ignore

        # Helper func.
        def append_row_element(s):
            self.lsrow.append(s)
            self.out_pos += len(s)

        with open(str(self.fn), 'rb') as f:
            eof = False
            done = False
            row_count = 0
            f.seek(self.start_addr)

            # Read rows.
            while not done:
                if (self.rows_to_read > 0 and row_count >= self.rows_to_read) or eof:
                    done = True
                    continue

                self.lsrow.clear()
                row_addr = f.tell() # cache
                bytes = f.read(ROW_SIZE)
                row_len = len(bytes)
                eof = row_len < ROW_SIZE

                ### Process row.
                readable = ['    ']

                # Address.
                append_row_element(f'0x{row_addr:04X}')

                # Byte values.
                for i in range(0, row_len):
                    start_pos = self.out_pos + 1
                    v = bytes[i]
                    append_row_element(f' {v:02X}')

                    if v >= 32 and v <= 126: # ascii printable
                        readable.append(chr(v))
                    elif v < 32 or v == 127: # ascii control
                        regions_ascii.append(sublime.Region(start_pos, self.out_pos)) # color range
                        readable.append(' ')
                    else: # Unicode byte.
                        regions_unicode.append(sublime.Region(start_pos, self.out_pos)) # color range
                        readable.append(' ')

                # Maybe pad last row.
                for i in range(row_len, ROW_SIZE):
                    append_row_element(f' ..')

                # Tack on readable.
                append_row_element(''.join(readable))

                # Row done.
                append_row_element('\n')
                buff.append(''.join(self.lsrow))

                row_count += 1
                output_limit -= 1

                if output_limit <= 0:
                    buff.append(f'====================== Truncated =====================\n')
                    done = True
                    break

        # Show result.
        new_view = sc.create_new_view(self.window, ''.join(buff))
        new_view.add_regions(key='regions_ascii', regions=regions_ascii, scope=color_ascii)
        new_view.add_regions(key='regions_unicode', regions=regions_unicode, scope=color_unicode)

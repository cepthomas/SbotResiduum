import sys
import sublime
import sublime_plugin
from . import sbot_common as sc


# TODO Insert/edit unicode from numerical/clipboard/region or from glyph picker.
# TODO Option: addr, length.


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

        in_pos = 0 # input text
        out_pos = 0

        buff = []
        regions_ascii = []
        regions_unicode = []

        region = sc.get_sel_regions(self.view)[0] 

        # Iterate lines in selection.
        line_num = 1
        for region_line in self.view.split_by_newlines(region):
            col_num = 1
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

    start_addr = 0 # -1 = invalid
    read_rows = 0 # num to read or 0 for all
    last_input = ''

    def run(self, paths, sel_addr_range):

        def on_done(input_string):
            self.last_input = input_string

            # Check user entry.
            if self.start_addr < 0:
                sc.error("Invalid start address")
                return

            ROW_SIZE = 16
            ROWS_PER_BLOCK = 256 # per block
            BLOCK_SIZE = ROWS_PER_BLOCK * ROW_SIZE

            _, _, path = sc.get_path_parts(self.window, paths)

            buff = []
            regions_ascii = []
            regions_unicode = []
            out_pos = 0
            file_row = 0 # offset in file

            settings = sublime.load_settings(sc.get_settings_fn())
            color_ascii = str(settings.get('color_ascii'))
            color_unicode = str(settings.get('color_unicode'))

            with open(str(path), 'rb') as f:
                eof = False
                f.seek(self.start_addr)

                while not eof:
                    bytes_read = f.read(BLOCK_SIZE)
                    blen = len(bytes_read)
                    eof = blen < BLOCK_SIZE

                    # Process new array.
                    num_rows = blen // ROW_SIZE + 1 if eof else 0
                    last_row_len = blen % ROW_SIZE

                    # Process block rows.
                    for row_num in range(0, num_rows):
                        row_len = last_row_len if eof and row_num == num_rows-1 else ROW_SIZE
                        if row_len == 0: continue

                        row_addr = file_row * ROW_SIZE + self.start_addr
                        srow = [f'0x{row_addr:04X}']
                        out_pos += 7
                        info = ['    ']

                        for i in range(0, row_len):
                            st_pos = out_pos
                            v = bytes_read[row_num * ROW_SIZE + i]
                            srow.append(f' {v:02X}')
                            out_pos += 3

                            if v >= 32 and v <= 126: # ascii printable
                                info.append(chr(v))

                            elif v < 32 or v == 127: # ascii control
                                regions_ascii.append(sublime.Region(st_pos, out_pos-1)) # color range
                                info.append(' ')

                            else: # Unicode byte.
                                regions_unicode.append(sublime.Region(st_pos, out_pos-1)) # color range
                                info.append(' ')

                        # Maybe pad last.
                        for i in range(row_len, ROW_SIZE):
                            srow.append(f' ..')
                            out_pos += 3

                        # Row done.
                        sinfo = (''.join(info))
                        srow.append(sinfo)
                        out_pos += len(sinfo)
                        srow.append('\n')
                        buff.append(''.join(srow))
                        file_row += 1

            new_view = sc.create_new_view(self.window, ''.join(buff))
            new_view.add_regions(key='regions_ascii', regions=regions_ascii, scope=color_ascii)
            new_view.add_regions(key='regions_unicode', regions=regions_unicode, scope=color_unicode)

        def on_cancel():
            print("User cancelled the input")

        # Start here...
        # User options?
        start_addr = 0
        read_rows = 0
        if sel_addr_range:
            self.window.show_input_panel('Enter address [length]', self.last_input, on_done, None, on_cancel)


#-----------------------------------------------------------------------------------
'''
class SbotBinDumpCommand_o(sublime_plugin.WindowCommand):

    start_addr = 0 # -1 = invalid
    read_rows = 0 # num to read or 0 for all
    last_input = ''

    def run(self, paths, sel_addr_range):
        _, _, path = sc.get_path_parts(self.window, paths)

        buff = []
        regions_ascii = []
        regions_unicode = []
        out_pos = 0
        file_row = 0 # offset in file

        settings = sublime.load_settings(sc.get_settings_fn())
        color_ascii = str(settings.get('color_ascii'))
        color_unicode = str(settings.get('color_unicode'))

        ROW_SIZE = 16
        READ_ROWS = 256 # per block
        BLOCK_SIZE = READ_ROWS * ROW_SIZE

        # User options?
        start_addr = 0
        read_rows = 0
        if sel_addr_range:
            self.window.show_input_panel('Enter address [length]', self.last_input, self.on_done_enter_address, None, None)
        if self.start_addr < 0:
            sc.error("Invalid start address")
            return

        with open(str(path), 'rb') as f:
            eof = False
            f.seek(self.start_addr)

            while not eof:
                bytes_read = f.read(BLOCK_SIZE)
                blen = len(bytes_read)
                eof = blen < BLOCK_SIZE

                # Process new array.
                num_rows = blen // ROW_SIZE + 1 if eof else 0
                last_row_len = blen % ROW_SIZE

                # Process block rows.
                for row_num in range(0, num_rows):
                    row_len = last_row_len if eof and row_num == num_rows-1 else ROW_SIZE
                    if row_len == 0: continue

                    row_addr = file_row * ROW_SIZE + self.start_addr
                    srow = [f'0x{row_addr:04X}']
                    out_pos += 7
                    info = ['    ']

                    for i in range(0, row_len):
                        st_pos = out_pos
                        v = bytes_read[row_num * ROW_SIZE + i]
                        srow.append(f' {v:02X}')
                        out_pos += 3

                        if v >= 32 and v <= 126: # ascii printable
                            info.append(chr(v))

                        elif v < 32 or v == 127: # ascii control
                            regions_ascii.append(sublime.Region(st_pos, out_pos-1)) # color range
                            info.append(' ')

                        else: # Unicode byte.
                            regions_unicode.append(sublime.Region(st_pos, out_pos-1)) # color range
                            info.append(' ')

                    # Maybe pad last.
                    for i in range(row_len, ROW_SIZE):
                        srow.append(f' ..')
                        out_pos += 3

                    # Row done.
                    sinfo = (''.join(info))
                    srow.append(sinfo)
                    out_pos += len(sinfo)
                    srow.append('\n')
                    buff.append(''.join(srow))
                    file_row += 1

        new_view = sc.create_new_view(self.window, ''.join(buff))
        new_view.add_regions(key='regions_ascii', regions=regions_ascii, scope=color_ascii)
        new_view.add_regions(key='regions_unicode', regions=regions_unicode, scope=color_unicode)

    def on_done_enter_address(self, text):
        # Process the input. Address can be hex or decimal.
        self.start_addr = -1
        self.read_rows = 0

        parts = text.split(' ')
        if len(parts) >= 1:
            try:
                if 'X' in parts[0].toupper():
                    self.start_addr = int(parts[0], 16)
                else:
                    self.start_addr = int(parts[0], 10)

                if len(parts) == 2:
                    self.read_rows = int(parts[1], 10)
            except:
                self.start_addr = -1

    def is_visible(self, paths=None):
        _, _, path = sc.get_path_parts(self.window, paths)
        return path is not None
'''
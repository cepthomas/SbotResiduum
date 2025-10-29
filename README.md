# Residuum

Sublime Text plugin with all the little stuff that doesn't fit anywhere else.
It will probably never be published to Package Control.

Built for ST4 on Windows. Linux and OSX should be ok but are not tested - PRs welcome.


# Commands

`sbot_residuum.py` is a sandard ST plugin with a variety of commands that process text, simplify ST internals,
interact with the OS, process binary/unicode content, etc. Displays absolute text position in status bar next to row/col.

Supported menu type is <b>C</b>ontext, <b>S</b>idebar, <b>T</b>ab.

| Command                 | Menu | Description                                                | Args          |
| :--------               | :--- | :------------                                              | :-------      |
| sbot_split_view         | C S  | Toggle simple split view like VS, Word etc.                |               |
| sbot_copy_name          | S T  | Copy file/dir name to clipboard.                           | S: paths:[]   |
| sbot_copy_path          | S T  | Copy full file/dir path to clipboard.                      | S: paths:[]   |
| sbot_copy_file          | S T  | Copy selected file to a new file in the same directory.    | S: paths:[]   |
| sbot_delete_file        | C T  | Moves the file in current view to recycle/trash bin.       |               |
| sbot_run                | C S  | Runs executable or opens other types.                      |               |
| sbot_terminal           | C S  | Open a terminal here.                                      | S: paths:[]   |
| sbot_tree               | C S  | Run tree cmd to new view.                                  | S: paths:[]   |
| sbot_open_context_path  | C    | Open path under cursor like `[opt tag](C:\my\file.txt)`    |               |
| sbot_insert_line_indexes| C    | Insert line numbers at beginning of line                   |               |
| sbot_trim               | C    | Remove ws from Line ends.                                  | how: leading OR trailing OR both |
| sbot_remove_empty_lines | C    | Like it says.                                              | how: remove_all OR normalize ( to one) |
| sbot_remove_ws          | C    | Like it says.                                              | how: remove_all OR keep_eol OR normalize (to one) |
| sbot_format_json        | C    | Simple json formatter. Converts comments to json elements. |               |
| sbot_format_xml         | C    | Simple xml formatter.                                      |               |
| sbot_format_cx_src      | C    | Simple C/C++/C# formatter. Uses AStyle.                    |               |
| sbot_bin_translate      | C    | Current view/selection with all binary/unicode expanded.   |               |
| sbot_bin_instance       | C    | List of all binary/unicode in current view.                |               |
| sbot_bin_dump           | S    | Hex dump of selected file with colored binary.             | S: paths:[] sel_addr_range:T/F   |



There are no default `.sublime-menu` files in this plugin.
Add the ones you like to your own menu files. Typical entries are:
``` json
{ "caption": "Copy Name", "command": "sbot_copy_name"},
{ "caption": "Copy Path", "command": "sbot_copy_path"},
{ "caption": "Copy File", "command": "sbot_copy_file"},
{ "caption": "Delete File", "command": "sbot_delete_file" },
{ "caption": "Split View 2 Pane", "command": "sbot_split_view" },
{ "caption": "Run", "command": "sbot_run" },
{ "caption": "Terminal Here", "command": "sbot_terminal" },
{ "caption": "Tree", "command": "sbot_tree" },
{ "caption": "Trim Leading WS", "command": "sbot_trim", "args" : {"how" : "leading"}  },
{ "caption": "Trim Trailing WS", "command": "sbot_trim", "args" : {"how" : "trailing"}  },
{ "caption": "Trim WS", "command": "sbot_trim", "args" : {"how" : "both"}  },
{ "caption": "Remove Empty Lines", "command": "sbot_remove_empty_lines", "args" : { "how" : "remove_all" } },
{ "caption": "Collapse Empty Lines", "command": "sbot_remove_empty_lines", "args" : { "how" : "normalize" } },
{ "caption": "Remove WS", "command": "sbot_remove_ws", "args" : { "how" : "remove_all" } },
{ "caption": "Remove WS Except EOL", "command": "sbot_remove_ws", "args" : { "how" : "keep_eol" } },
{ "caption": "Collapse WS", "command": "sbot_remove_ws", "args" : { "how" : "normalize" } },
{ "caption": "Insert Line Indexes", "command": "sbot_insert_line_indexes" },
{ "caption": "Format C/C++/C#", "command": "sbot_format_cx_src" },
{ "caption": "Format json", "command": "sbot_format_json" },
{ "caption": "Format xml", "command": "sbot_format_xml" },
{ "caption": "Bin Translate", "command": "sbot_bin_translate" },
{ "caption": "Bin Instance", "command": "sbot_bin_instance" },
{ "caption": "Bin Dump", "command": "sbot_bin_dump", "args": {"paths": []} },
```

# Settings

| Setting            | Description                  | Options                     |
| :--------          | :-------                     | :------                     |
| format_tab_size    | Spaces per tab.              | Default = 4                 |
| output_limit       | Limit output results.        | Default = 500  0 = none     |
| translate_delims   | Marks for binaries.          | Default = ["<<", ">>"]      |
| color_ascii        | One byte values.             | Default = scope "comment"   |
| color_unicode      | Multi byte values.           | Default = scope "variable"  |


Right click stuff works best with this global setting:
```
"preview_on_click": "only_left",
```

## Notes

- `sbot_common.py` contains miscellaneous common components primarily for internal use by the sbot family.
  This includes a very simple logger primarily for user-facing information, syntax errors and the like.
  Log file is in `<ST_PACKAGES_DIR>\User\Residuum\Residuum.log`.
- `tests` dir doesn't contain actual unit tests, just a bunch of files to use as targets manually.

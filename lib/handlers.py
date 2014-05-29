import sublime, sublime_plugin, json
from SublimeTogether.diff_match_patch import diff_match_patch

SELECTION_KEY   = 'SublimeTogether-Selection-{}'
SELECTION_SCOPE = 'SublimeTogether.Selection.{}'
SELECTION_ICON  = 'dot'
SELECTION_STYLE = sublime.DRAW_EMPTY

def error_handler(arg):
    print('[SublimeTogether Error]: Unknow command %s' % hex(arg['data']))

def message_handler(arg):
    sublime.active_window().active_view().run_command('sublime_together_chat_insert', {'text': '%s\n' % arg['data']})

def change_selection_handler(arg):
    data = arg['data']
    if data['path'] in arg['path_views']:
        client = data['client']
        view = arg['path_views'][data['path']]
        sels = data['selections']
        regions = []
        for sel in sels:
            regions.append(sublime.Region(sel['a'], sel['b']))
        view.add_regions(SELECTION_KEY.format(client), regions,
            SELECTION_SCOPE.format(client), SELECTION_ICON, SELECTION_STYLE)

def edit_file_handler(arg):
    data = arg['data']
    print('edit_file_handler', data['path'] in arg['path_views'])
    if data['path'] in arg['path_views']:
        client = data['client']
        view = arg['path_views'][data['path']]
        patches_text = data['patch']
        view.run_command('sublime_together_edit_file', {
            'client': client,
            'patches_text': patches_text
            })

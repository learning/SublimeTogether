import sublime, sublime_plugin, threading, socket, struct, os, pickle
from SublimeTogether.lib import in_cmd, out_cmd, handlers
from SublimeTogether.diff_match_patch import diff_match_patch

# SublimeTogether's socket connection
thread = None
chat = None
project = None

CHAT_TITLE = 'SublimeTogether Chat'

def load_settings():
    '''Load Settings'''
    # default settings
    defaultPort = 5800
    defaultHost = 'localhost'
    defaultUser = ''
    defaultPass = ''

    # load SublimeTogether settings
    s = sublime.load_settings('SublimeTogether.sublime-settings')
    # if setting file not exists, set to default
    if not s.has('port'):
        s.set('port', defaultPort)
    if not s.has('host'):
        s.set('host', defaultHost)
    if not s.has('user'):
        s.set('user', defaultUser)
    if not s.has('pass'):
        s.set('pass', defaultPass)
    sublime.save_settings('SublimeTogether.sublime-settings')
    return s

def get_project():
    '''Get SublimeTogether project folder'''
    for w in sublime.windows():
        for f in w.folders():
            if os.path.isfile(f + os.sep + '.stproject'):
                return f
    return None

def is_in_project(view):
    return project and view.file_name() and view.file_name().startswith(project)

def get_file_path(view):
    return view.file_name()[len(project) + 1 :].replace(os.sep, '/')

class SublimeTogetherThread(threading.Thread):
    socket = None
    enable = True
    views = {}
    paths = {}
    path_views = {}
    path_clients = {}
    user_name = None
    # last_sels = {}
    # Packet's head
    head = [0xd0, 0x02, 0x0f]

    def __init__(self):
        super(SublimeTogetherThread, self).__init__()
        self.setName(self.__class__.__name__)

    def run(self):
        global project
        settings = load_settings()
        self.socket = socket.socket()
        try:
            self.socket.connect((settings.get('host'), settings.get('port')))
            self.send('login', {
                'user': settings.get('user'),
                'pass': settings.get('pass')
                })
            self.user_name = settings.get('user')
            project = get_project()
            while self.enable:
                self.read_command()
        except ConnectionError as err:
            sublime.message_dialog('SublimeTogether: %s' % err)
        finally:
            self.socket.close()
            print('SublimeTogether: socket closed.')

    def send(self, cmd, data):
        if self.socket is None:
            return
        data = pickle.dumps(data)
        # send header
        header = b'\xa9\x5f\xca'
        # send command
        command = out_cmd[cmd].to_bytes(1, 'big')
        # send data-length
        length = len(data).to_bytes(4, 'little')
        # send all data
        all_data = header + command + length + data
        # print('send_all:', all_data)
        self.socket.sendall(all_data)

    def read_command(self, offset = 0):
        if self.socket is None:
            return
        try:
            byte = self.socket.recv(1)[0]
        except IndexError:
            raise ConnectionError("Disconnected from server.")
        if byte == self.head[offset]:
            if offset is 2:
                tmp = self.socket.recv(5)
                # convert 4 bytes data to unsigned integer (I), offset 1
                length = struct.unpack_from('I', tmp, 1)[0]
                data = self.socket.recv(length)
                data = pickle.loads(data)
                key = tmp[0]
                # print(tmp, data)
                if key in in_cmd:
                    cmd = in_cmd[tmp[0]]
                else:
                    cmd = 'error'
                    data = key
                handlers.__dict__['%s_handler' % cmd]({
                    'thread': self,
                    'data': data,
                    'views': self.views,
                    'paths': self.paths,
                    'path_views': self.path_views
                    })
            else:
                self.read_command(offset + 1)
        else:
            print('byte error:')
            print(byte)

    def open_file(self, key, view):
        # print('open_file')
        path = get_file_path(view)
        self.views[key] = view
        self.paths[key] = path
        self.path_views[path] = view
        self.send('open_file', path)

    def close_file(self, key):
        # print('close_file')
        if key in self.paths:
            path = self.paths[key]
            self.send('close_file', path)
            del(self.views[key])
            del(self.path_views[path])
            del(self.paths[key])
        else:
            print('key: %s' % key)
            print(self.paths)

    def change_selection(self, key, sels):
        path = self.paths[key]
        self.send('change_selection', {
            'path'      : path,
            'selections': sels
            })

    def edit_file(self, key, patch, region_dict):
        path = self.paths[key]
        self.send('edit_file', {
            'path' : path,
            'patch': patch,
            'region_dict': region_dict
            })

    def stop(self):
        self.enable = False

class SublimeTogetherChatInsertCommand(sublime_plugin.TextCommand):
    def run(self, edit, text):
        global chat
        if chat is None:
            chat = self.create_chat()
        chat.set_read_only(False)
        chat.insert(edit, 0, text)
        chat.set_read_only(True)

    def create_chat(self):
        view = None
        for w in sublime.windows():
            for v in w.views():
                if v.name() == CHAT_TITLE:
                    view = v
                    w.focus_view(v)
        if view is None:
            view = sublime.active_window().new_file()
            view.set_name(CHAT_TITLE)
        view.set_read_only(True)
        return view

class SublimeTogetherChatSendCommand(sublime_plugin.TextCommand):
    def run(self, edit):
        global thread
        contents = []
        for region in self.view.sel():
            # no selection, send whole line, and erase it
            if region.empty():
                line = self.view.full_line(region)
                content = self.view.substr(line)
                self.view.erase(edit, line)
                contents.append(content.strip())
            # has selections, send selected words, without erase
            else:
                word = self.view.word(region)
                content = self.view.substr(word)
                contents.append(content)
        thread.send('message', str.join('\n', contents))
    def is_enabled(self):
        global thread
        return thread is not None and thread.is_alive()


class SublimeTogetherConnectCommand(sublime_plugin.ApplicationCommand):
    def run(self):
        global thread
        settings = load_settings()
        if settings.get('user') == '':
            sublime.active_window().run_command('open_file', {"file": "${packages}/User/SublimeTogether.sublime-settings"})
            return sublime.message_dialog('Please set up you username and password first!')
        if thread is not None and thread.is_alive():
            return sublime.message_dialog('SublimeTogether is alread started!')
        thread = SublimeTogetherThread()
        thread.start()
    def is_enabled(self):
        global thread
        return not (thread is not None and thread.is_alive())

class SublimeTogetherDisconnectCommand(sublime_plugin.ApplicationCommand):
    def run(self):
        global thread
        if thread is not None and thread.is_alive():
            thread.stop()
            # no need to join, just set thread to None
            thread = None
    def is_enabled(self):
        global thread
        return thread is not None and thread.is_alive()

class SublimeTogetherFileListener(sublime_plugin.EventListener):
    differ = diff_match_patch()
    file_buffers = {}
    def on_load(self, view):
        global project, thread
        if is_in_project(view):
            if thread and thread.is_alive():
                self.file_buffers[view.id()] = view.substr(sublime.Region(0, view.size()))
                thread.open_file(view.id(), view)

    def on_close(self, view):
        global project, thread
        if is_in_project(view):
            if thread and thread.is_alive():
                if view.id() in self.file_buffers:
                    del(self.file_buffers[view.id()])
                thread.close_file(view.id())

    def on_modified(self, view):
        global project, thread
        if is_in_project(view):
            if thread and thread.is_alive():
                last_text = self.file_buffers[view.id()]
                this_text = view.substr(sublime.Region(0, view.size()))
                # check if is not SublimeTogether's command
                # if you ignore this, it will go into a infinite loop
                if view.command_history(0, True)[0] != 'sublime_together_edit_file':
                    patches = self.differ.patch_make(last_text, this_text)
                    patches_text = self.differ.patch_toText(patches)
                    path = thread.paths[view.id()]
                    client_list = thread.path_clients[path]
                    region_dict = {}
                    for client in client_list:
                        # get all regions
                        print(handlers.SELECTION_KEY.format(client))
                        regions = view.get_regions(handlers.SELECTION_KEY.format(client))
                        sels = []
                        for region in regions:
                            sels.append({'a': region.a, 'b': region.b})
                        region_dict[client] = sels
                    print(region_dict)
                    thread.edit_file(view.id(), patches_text, region_dict)
                self.file_buffers[view.id()] = this_text

    def on_selection_modified(self, view):
        global project, thread
        if is_in_project(view):
            if thread and thread.is_alive():
                sels = []
                for region in view.sel():
                    sels.append({'a': region.a, 'b': region.b})
                thread.change_selection(view.id(), sels)

class SublimeTogetherEditFileCommand(sublime_plugin.TextCommand):
    differ = diff_match_patch()

    def run(self, edit, client, patches_text, region_dict):
        global thread
        region = sublime.Region(0, self.view.size())
        patches = self.differ.patch_fromText(patches_text)
        result = self.differ.patch_apply(patches, self.view.substr(region))
        new_text = result[0]
        # print(result[1])
        self.view.replace(edit, region, new_text)
        # relocate selections and regions
        region_dict = pickle.loads(region_dict)
        for client in region_dict:
            regions = []
            for sel in region_dict[client]:
                regions.append(sublime.Region(sel['a'], sel['b']))
            if client == thread.user_name:
                view.sel().add_all(regions)
            else:
                view.add_regions(SELECTION_KEY.format(client), regions,
                    SELECTION_SCOPE.format(client), SELECTION_ICON,
                    SELECTION_STYLE)

project = get_project()
load_settings()
# check if last SublimeTogetherThread exists
threads = threading.enumerate()
for t in threads:
    if t.__class__.__name__ is SublimeTogetherThread.__name__:
        thread = t
        break

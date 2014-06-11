# commands from server
in_cmd = {
    0xa0: 'initialize',
    0xa1: 'message',
    0xa2: 'disconnect',
    0xa3: 'update_client_list',
    0xa4: 'change_selection',
    0xa5: 'edit_file'
}

# commands for send
out_cmd = {
    'login'           : 0xd0,
    'message'         : 0xd1,
    'open_file'       : 0xd2,
    'close_file'      : 0xd3,
    'change_selection': 0xd4,
    'edit_file'       : 0xd5
}
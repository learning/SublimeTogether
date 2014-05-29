# commands from server
in_cmd = {
    0xa0: 'initialize',
    0xa1: 'message',
    0xa4: 'change_selection',
    0xa5: 'edit_file'
}

# commands for send
out_cmd = {
    'message'         : 0xd1,
    'open_file'       : 0xd2,
    'close_file'      : 0xd3,
    'change_selection': 0xd4,
    'edit_file'       : 0xd5
}
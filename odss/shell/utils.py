BUNDLE_STATE = {
    "1": "UNINSTALLED",
    "2": "INSTALLED",
    "4": "RESOLVED",
    "8": "STARTING",
    "16": "STOPPING",
    "32": "ACTIVE"
}

def bundle_state_name(state):
    return BUNDLE_STATE[str(state)]

def make_ascii_table(headers, records):
    sizes = [len(head) for head in headers]

    for row, record in enumerate(records):
        if len(headers) != len(record):
            raise ValueError(f'Diffrent size of headers and records (row={row})')
        for column, value in enumerate(record):
            svalue = str(value)
            size = len(svalue)
            if sizes[column] < size:
                sizes[column] = size

    sformat = "|"
    for size in sizes:
        sformat += f" {{:^{size}}} |"

    buff = []
    sheader = sformat.format(*headers)
    buff.append("-" * len(sheader))
    buff.append(sheader)
    buff.append("-" * len(sheader))

    sformat = "|"
    for size in sizes:
        sformat += f" {{:<{size}}} |"

    for record in records:
        buff.append(sformat.format(*record))
    buff.append("-" * len(sheader))

    return "\n".join(buff)
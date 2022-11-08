def _sep_top(sizes):
    line = "┬".join(["─" * (size + 2) for size in sizes])
    return f"┌{line}┐"


def _sep_mid(sizes):
    line = "┼".join(["─" * (size + 2) for size in sizes])
    return f"├{line}┤"


def _sep_bottom(sizes):
    line = "┴".join(["─" * (size + 2) for size in sizes])
    return f"└{line}┘"


def make_ascii_table(title, headers, records):
    sizes = [len(head) for head in headers]
    for row, record in enumerate(records):
        if len(headers) != len(record):
            raise ValueError(f"Diffrent size of headers and records (row={row})")
        for column, value in enumerate(record):
            svalue = str(value)
            size = len(svalue)
            if sizes[column] < size:
                sizes[column] = size

    sformat = "│"
    for size in sizes:
        sformat += f" {{:<{size}}} │"

    sheader = sformat.format(*headers)
    buff = [title]
    buff.append(_sep_top(sizes))

    buff.append(sheader)
    buff.append(_sep_mid(sizes))

    for record in records:
        buff.append(sformat.format(*record))
    buff.append(_sep_bottom(sizes))

    return "\n".join(buff)

from difflib import SequenceMatcher
import aiofiles


async def process(data_left, data_right, meta):
    buff_size = meta["buff_size"]
    lookup_distance = meta["lookup_distance"]
    similar_threshold = meta["similar_threshold"]
    output_separator = meta["output_separator"]

    async def fill_buffer(reader, size):
        lines = []
        while range(size):
            chunk = await reader.readline()
            if not chunk:
                break
            lines.append(chunk.decode().replace("\n", ""))
        return lines

    def compare(what, where):
        right = right_lines[where]
        similarity = SequenceMatcher(None, what, right).ratio()
        is_similar = similarity > similar_threshold
        is_the_same = similarity == 1.0
        output_str = None
        if is_similar:
            left_used.add(where)
            output_str = f"{what}" if is_the_same else f"{what}{output_separator}{right}"
        return is_similar, output_bytes(output_str)

    def output_bytes(s):
        return f"{s}\n".encode()

    right_tail = []
    file_name = f"{data_left['file_name']}_{data_right['file_name']}_{meta['session_id']}"
    file_url = f"/static/output/{file_name}"
    file_name = meta["output_path"] / file_name

    async with aiofiles.open(file_name, mode="wb") as f:
        while True:
            stop = False
            left_lines = await fill_buffer(data_left["reader"], buff_size)
            if len(left_lines) == 0:
                stop = True
            right_lines = (
                await fill_buffer(data_right["reader"], buff_size + lookup_distance - len(right_tail))
                + right_tail
            )

            right_tail = []
            if len(left_lines) == 0:
                stop = True
            if stop:
                for line in left_lines:
                    await f.write(output_bytes(f"{line}{output_separator}"))
                for line in right_lines:
                    await f.write(output_bytes(f"{output_separator}{line}"))
                break

            right_len = len(right_lines)
            left_used = set()
            for idx, left in enumerate(left_lines):
                found = False
                for distance in range(lookup_distance):
                    near_idx = idx - distance
                    if distance > 0 and near_idx < right_len and near_idx not in left_used:
                        found, output_string = compare(left, near_idx)
                        await f.write(output_string)
                        if found:
                            break
                    near_idx = idx + distance
                    if near_idx < right_len and near_idx not in left_used and compare(left, near_idx):
                        found, output_string = compare(left, near_idx)
                        await f.write(output_string)
                        if found:
                            break
                if not found:
                    await f.write(output_bytes(f"{left}{output_separator}"))
            for idx, line in enumerate(right_lines):
                if idx >= buff_size:
                    right_tail.append(line)
                if idx not in left_used:
                    await f.write(output_bytes(f"{output_separator}{line}"))

    meta["waiter"].set()
    return file_url

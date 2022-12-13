from construct import *
import os
import sys

Entry = Struct(
    'tag' / Hex(Int32ub),
    'data' / Bytes(124),
)

ENTRY_EMPTY_TAG = 0x20
EntryEmpty = Struct(
    'tag' / Const(ENTRY_EMPTY_TAG, Int32ub),
    Const(b'\x00' * 124)
)

ENTRY_GENRE_TAG = 0x23
EntryGenre = Struct(
    'tag' / Const(ENTRY_GENRE_TAG, Int32ub),
    'name' / PaddedString(0x30, 'ascii'),
    'unknown0' / Hex(Int8ub),
    'unknown1' / Hex(Int8ub),
    Const(b'\x00' * 74),
)

ENTRY_TRACK_TAG = 0x24
EntryTrack = Struct(
    'tag' / Const(ENTRY_TRACK_TAG, Int32ub),
    'size' / Hex(Int32ub),
    'sector_length' / Hex(Int32ub),
    'sector_start' / Hex(Int32ub),
    'unknown3' / Hex(Int32ub),
    'unknown4' / Hex(Int32ub),
    'genre' / Hex(Int16ub),
    'unknown5' / Hex(Int16ub),
    'unknown6' / Hex(Int32ub),
    'album' / PaddedString(0x30, 'ascii'),
    'track' / PaddedString(0x30, 'ascii'),
)

ENTRY_ALBUM_TAG = 0x25
EntryAlbum = Struct(
    'tag' / Const(ENTRY_ALBUM_TAG, Int32ub),
    'track_list' / Hex(Int16ub),
    'genre' / Hex(Int16ub),
    'unknown0' / Hex(Int32ub),
    'str1' / PaddedString(0x30, 'ascii'),
    'str2' / PaddedString(0x30, 'ascii'),
    'unknown1' / Hex(Int32ub),
    'unknown2' / Hex(Int32ub),
    'unknown3' / Hex(Int32ub),
    'unknown4' / Hex(Int32ub),
    'unknown5' / Hex(Int32ub),
)

ENTRY_TRACK_LIST_TAG = 0x26
EntryTrackList = Struct(
    'tag' / Const(ENTRY_TRACK_LIST_TAG, Int32ub),
    'unknown0' / Hex(Int16ub),
    'track_count' / Hex(Int16ub),
    'unknown1' / Hex(Int32ub),
    'tracks' / Array(10, Int16ub),
)

ENTRY_BASE = 0x400000
ALLOCATION_TABLE_BASE = 0x480000
SECTOR_SIZE = 0x20000


def read_entries(f):
    entries = []

    f.seek(ENTRY_BASE, os.SEEK_SET)
    for _ in range(4096):
        data = f.read(128)
        entry = Entry.parse(data)

        if entry.tag == ENTRY_EMPTY_TAG:
            entry = EntryEmpty.parse(data)
        elif entry.tag == ENTRY_GENRE_TAG:
            entry = EntryGenre.parse(data)
        elif entry.tag == ENTRY_TRACK_TAG:
            entry = EntryTrack.parse(data)
        elif entry.tag == ENTRY_ALBUM_TAG:
            entry = EntryAlbum.parse(data)
        elif entry.tag == ENTRY_TRACK_LIST_TAG:
            entry = EntryTrackList.parse(data)

        entries.append(entry)

    return entries

def read_allocation_table(f):
    allocation_table = []

    f.seek(ALLOCATION_TABLE_BASE, os.SEEK_SET)
    for _ in range(4096):
        entry = f.read(4)
        entry = int.from_bytes(entry, byteorder='big')
        allocation_table.append(entry)

    return allocation_table

def read_sector(f, sector):
    f.seek(sector * SECTOR_SIZE, os.SEEK_SET)
    return f.read(SECTOR_SIZE)


def dump_entries(entries, full):
    for i, entry in enumerate(entries):
        if entry.tag == ENTRY_EMPTY_TAG:
            continue

        offset = ENTRY_BASE + 128 * i
        print(f'{i:#05x} (@ {offset:#07x}) ', end='')

        if entry.tag == ENTRY_GENRE_TAG:
            print(f'genre      => {entry.name}')
        elif entry.tag == ENTRY_TRACK_TAG:
            print(f'track      => {entry.album} - {entry.track}')
        elif entry.tag == ENTRY_ALBUM_TAG:
            print(f'album      => {entry.str1} - {entry.str2}')
        elif entry.tag == ENTRY_TRACK_LIST_TAG:
            tracks = ', '.join(f'{v:#05x}' for v in entry.tracks[:entry.track_count])
            print(f'track list => length={entry.track_count:d} tracks={tracks}')
        else:
            print('unknown')

        if full:
            print(entry)
            print('=' * 20)

def dump_allocation_table(allocation_table):
    t = 0
    print('digraph at {')
    for i in range(4096):
        ii = allocation_table[i]
        if ii == 0xffffffff:
            continue
        if ii != 0x00000000:
            print(f'    n{i:#05x} -> n{ii:#05x};')
        else:
            print(f'    terminal{t} [label="", shape=circle, style=filled, fillcolor=black];')
            print(f'    n{i:#05x} -> terminal{t};')
            t += 1
    print('}')

def dump_tracks(entries, allocation_table):
    for entry in entries:
        if entry.tag != ENTRY_TRACK_TAG:
            continue

        os.makedirs('tracks', exist_ok=True)
        with open(f'tracks/{entry.album} - {entry.track}.mp3', 'wb') as mp3:
            bytes_remaining = entry.size
            sector = entry.sector_start
            while sector != 0:
                next_sector = allocation_table[sector]
                if bytes_remaining < SECTOR_SIZE:
                    assert next_sector == 0

                bytes_from_sector = min(bytes_remaining, SECTOR_SIZE)
                bytes_remaining -= bytes_from_sector

                data = read_sector(f, sector)
                mp3.write(data[:bytes_from_sector])

                sector = next_sector


assert len(sys.argv) == 2, 'expected image as first command line argument'
with open(sys.argv[1], 'rb') as f:
    entries = read_entries(f)
    allocation_table = read_allocation_table(f)

    # uncomment to print a list of the tracks/albums/stuff. set full=True
    # to see fields i'm not sure about (dump the construct structs)
    #dump_entries(entries, full=False)

    # uncomment to print a dot graph to stdout of the allocation table chains
    #dump_allocation_table(allocation_table)

    # uncomment to create a bunch of mp3 files in a directory called tracks/
    dump_tracks(entries, allocation_table)

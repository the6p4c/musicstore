# musicstore
lazy notes about the musicstore hdd format

## code
the firmware is stored on the hard drive (weird huh). "`.text`" starts at `0x0`
and continues until `0x75090` (exclusive). the next `0x2588` bytes (from
`0x75090` to `0x77618`, exclusive) are the "`.data`" section of the firmware
image.

both `.text` and `.data` sections are loaded one after another at address 0.
there's a `.bss` section which is at addresses `0x77618` to `0x81dbc`
(exclusive). the firmware is classic ARM (we all know the chip is probably yet
another ARM926EJ-S deal), big endian.

the initialisation of `.data` and `.bss` are in a function at 0x00033614 -
beware of the fact that `.data` is copied from where it was loaded straight back
to where it's already loaded. i think that's just a silly linker script heckup.

### fw
it's a bit of a c++ nightmare with vtables everywhere. good luck.

seems like it runs something resembling an rtos. there are what look like tasks
being started in a function at `0x00005980`.

be really careful with the tail calls - there are a lot which are just `b` to a
tail call'd function and ghidra is Not good at picking up on them.

### mmio
there's some registers in a region starting at `0x01ff0000`. ones near
`0x01ffb004`/`0x01ffb005` seem to be gpio used to drive the LCD (yeah, just a
mega standard hitachi deal). there's some kind of ata controller at
`0x03fd0000`, where the command block registers are mapped `0x03fd0040 +
DA2..DA0 * 4`. they maintain the same read/write semantics as the ata spec says
they should.

## data
the filesystem is FAT like. there's a table of file-ish things (i called them
"entries", naming is hard) beginning at `0x400000`. each is 128 bytes long and
begins with a 4-byte BE tag value. there's 4096 entries, and a tag of 0x20 is
given to unused entries.

there's a cluster chain esque system which begins at `0x480000`. there are 4096
4-byte BE values which are the next sector in the chain (i.e. there's a big
array of dwords at `0x480000` which you index into with your current sector
value and you get back the next sector value). if the next sector is 0, the
thing you're reading is finished. if it's `0xffffffff`, the sector is
unallocated.

each sector from the file system's perspective is `0x20000` long - 256x 512-byte
sectors.

the sectors in the cluster chain are all relative to the start of the disk -
they don't have any offsets to ignore the code. this is also probably why the
first cluster chain exists - it's just one which covers all the data from `0x0`
to `0x400000`. if you look at the cluster chains themselves there are a few odd
ones which don't have mp3 data in them. no clue what they do.

**you can use the `fs.py` file to poke at some of this**. run it with the `.img`
file as the first command line argument and uncomment the functions at the
bottom of the file to do different things (dump entries, dump cluster chains,
dump mp3s). you'll need the `construct` library but that's it.

## mp3s
no idea. they have the right structure, i think - that is, they start with the
right header with sync word and sensible looking data (44.1khz, etc), but
software freaks out reading them. the size of the files seem to make sense for
their lengths, considering the bitrate + sample rate.

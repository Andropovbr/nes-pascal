local frames = 0
local function fail(message, code)
    emu.log("Background update validation failed: " .. message)
    emu.stop(code)
end

local function validateBackgroundUpdates()
    frames = frames + 1
    if frames < 9 then
        return
    end

    if emu.read(0x05DF, emu.memType.nesDebug) ~= 1 then
        fail("The fifth tile write did not report overflow.", 2)
        return
    end
    if emu.read(0x05E0, emu.memType.nesDebug) ~= 1 then
        fail("Cancelling pending writes unexpectedly cleared overflow.", 31)
        return
    end
    if emu.read(0x05E1, emu.memType.nesDebug) ~= 0 then
        fail("Explicit overflow clearing did not update its query.", 34)
        return
    end
    if emu.read(0x05E2, emu.memType.nesDebug) ~= 1 then
        fail("Attribute queue overflow was not reported.", 32)
        return
    end
    if emu.read(0x05D4, emu.memType.nesDebug) ~= 0 then
        fail("The sticky overflow flag was not explicitly cleared.", 33)
        return
    end
    for slot = 0, 3 do
        if emu.read(0x05C4 + slot, emu.memType.nesDebug) ~= 0 then
            fail("A consumed queue slot remained published.", 4)
            return
        end
    end
    for x = 0, 3 do
        local actual = emu.read(0x2000 + x, emu.memType.nesPpuDebug)
        if actual ~= x + 1 then
            fail("One of the first four tile writes was not uploaded.", 5)
            return
        end
    end
    if emu.read(0x2004, emu.memType.nesPpuDebug) ~= 0x30 then
        fail("The fifth same-frame tile write was not dropped.", 6)
        return
    end
    if emu.read(0x0208, emu.memType.nesDebug) ~= 0x30
        or emu.read(0x05DB, emu.memType.nesDebug) ~= 0x30 then
        fail("A rejected tile write changed the confirmed shadow.", 7)
        return
    end
    if emu.read(0x05DC, emu.memType.nesDebug) ~= 0x01 then
        fail("get_tile did not observe a tile confirmed by NMI.", 8)
        return
    end
    if emu.read(0x2005, emu.memType.nesPpuDebug) ~= 0x07
        or emu.read(0x0209, emu.memType.nesDebug) ~= 0x07
        or emu.read(0x05DD, emu.memType.nesDebug) ~= 0x07 then
        fail("Repeated writes did not confirm their final value in order.", 9)
        return
    end
    if emu.read(0x2006, emu.memType.nesPpuDebug) ~= 0x30
        or emu.read(0x020A, emu.memType.nesDebug) ~= 0x30
        or emu.read(0x05DE, emu.memType.nesDebug) ~= 0x30 then
        fail("Cancelling a pending tile write changed confirmed state.", 10)
        return
    end
    if emu.read(0x23C0, emu.memType.nesPpuDebug) ~= 0xE4 then
        fail("Attribute overflow replaced an accepted attribute write.", 11)
        return
    end
    for x = 7, 9 do
        local expected = x + 2
        if emu.read(0x2000 + x, emu.memType.nesPpuDebug) ~= expected
            or emu.read(0x0204 + x, emu.memType.nesDebug) ~= expected then
            fail("An accepted post-overflow tile did not reach PPU and shadow.", 12)
            return
        end
    end
    if emu.read(0x0200, emu.memType.nesDebug) ~= 0x80
        or emu.read(0x0201, emu.memType.nesDebug) ~= 0x1E
        or emu.read(0x0202, emu.memType.nesDebug) ~= 0x00
        or emu.read(0x0203, emu.memType.nesDebug) ~= 0x00 then
        fail("The background uploader did not preserve PPU state shadows.", 13)
        return
    end

    emu.log("Confirmed shadow, bounded overflow, cancellation, and attribute validation passed.")
    emu.stop(0)
end

emu.addEventCallback(validateBackgroundUpdates, emu.eventType.endFrame)

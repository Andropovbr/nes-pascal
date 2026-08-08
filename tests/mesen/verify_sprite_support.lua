local frames = 0

local function fail(message, code)
    emu.log("Sprite support validation failed: " .. message)
    emu.stop(code)
end

local function validateSpriteSupport()
    frames = frames + 1
    if frames < 10 then
        return
    end

    if emu.read(0x0000, emu.memType.nesDebug) < 2 then
        fail("NMI frame bookkeeping did not advance.", 6)
        return
    end

    local y = emu.read(0x0200, emu.memType.nesDebug)
    local tile = emu.read(0x0201, emu.memType.nesDebug)
    local attributes = emu.read(0x0202, emu.memType.nesDebug)
    local x = emu.read(0x0203, emu.memType.nesDebug)
    if y ~= 0x70 or tile ~= 0x01 or attributes ~= 0x42 or x ~= 0x78 then
        fail("Sprite 0 fields do not match the Pascal setters.", 2)
        return
    end
    if emu.read(0x00, emu.memType.nesSpriteRam) ~= y
        or emu.read(0x01, emu.memType.nesSpriteRam) ~= tile
        or emu.read(0x02, emu.memType.nesSpriteRam) ~= attributes
        or emu.read(0x03, emu.memType.nesSpriteRam) ~= x then
        fail("PPU OAM does not contain the shadow copied by DMA.", 4)
        return
    end

    for sprite = 1, 63 do
        local spriteY = emu.read(0x0200 + sprite * 4, emu.memType.nesDebug)
        if spriteY ~= 0xFF then
            fail("An unused sprite was not hidden during initialization.", 3)
            return
        end
        if emu.read(sprite * 4, emu.memType.nesSpriteRam) ~= 0xFF then
            fail("DMA did not copy an unused hidden sprite to PPU OAM.", 5)
            return
        end
    end

    emu.log("Basic sprite shadow, initialization, attributes, and DMA passed.")
    emu.stop(0)
end

emu.addEventCallback(
    validateSpriteSupport,
    emu.eventType.startFrame
)

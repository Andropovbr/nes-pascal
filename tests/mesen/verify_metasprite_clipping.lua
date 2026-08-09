local totalFrames = 0

local function fail(message, stage)
    emu.log("Metasprite clipping validation failed: " .. message)
    emu.stop(60 + stage)
end

local function sprite(index)
    local address = 0x0200 + index * 4
    return {
        y = emu.read(address, emu.memType.nesDebug),
        tile = emu.read(address + 1, emu.memType.nesDebug),
        attributes = emu.read(address + 2, emu.memType.nesDebug),
        x = emu.read(address + 3, emu.memType.nesDebug),
    }
end

local function visibleCount()
    local count = 0
    for index = 0, 6 do
        if sprite(index).y ~= 0xFF then
            count = count + 1
        end
    end
    return count
end

local function allHidden()
    return visibleCount() == 0
end

local function expectSprite(index, y, tile, attributes, x, stage, context)
    local actual = sprite(index)
    if actual.y ~= y or actual.tile ~= tile
        or actual.attributes ~= attributes or actual.x ~= x then
        fail(context .. " has incorrect OAM geometry or attributes.", stage)
        return false
    end
    return true
end

local function validateMetaspriteClipping()
    totalFrames = totalFrames + 1
    local stage = emu.read(0x0081, emu.memType.nesDebug)
    local count = visibleCount()

    if stage == 1 then
        if count ~= 7
            or not expectSprite(0, 0x5B, 0x00, 0x00, 0x6C, stage, "centered baseline")
            or not expectSprite(4, 0x6B, 0x03, 0x00, 0x64, stage, "centered baseline") then
            return
        end
    elseif stage == 2 then
        if count ~= 3 or sprite(1).x ~= 0x04 or sprite(3).x ~= 0x04
            or sprite(6).x ~= 0x04 then
            fail("left-edge clipping wrapped or retained the wrong components.", stage)
            return
        end
    elseif stage == 3 then
        if count ~= 1 or sprite(4).x ~= 0xF3 then
            fail("right-edge clipping wrapped or retained the wrong components.", stage)
            return
        end
    elseif stage == 4 then
        if count ~= 3 or sprite(4).y ~= 0x03 or sprite(5).y ~= 0x03
            or sprite(6).y ~= 0x03 then
            fail("top-edge clipping or logical Y conversion is incorrect.", stage)
            return
        end
    elseif stage == 5 then
        if count ~= 2 or sprite(0).y ~= 0xE7 or sprite(1).y ~= 0xE7 then
            fail("bottom-edge clipping retained the wrong components.", stage)
            return
        end
    elseif stage == 6 then
        if count ~= 1 or sprite(4).x ~= 0x04 or sprite(4).attributes ~= 0x40 then
            fail("horizontal flip near the left edge wrapped or XORed incorrectly.", stage)
            return
        end
    elseif stage == 7 then
        if count ~= 3 or sprite(1).x ~= 0xF3 or sprite(1).attributes ~= 0x00
            or sprite(3).x ~= 0xF3 or sprite(3).attributes ~= 0x40
            or sprite(6).x ~= 0xF3 or sprite(6).attributes ~= 0x40 then
            fail("horizontal flip near the right edge wrapped or XORed incorrectly.", stage)
            return
        end
    elseif stage == 8 then
        if count ~= 2 or sprite(0).y ~= 0x03 or sprite(0).attributes ~= 0x80
            or sprite(1).y ~= 0x03 or sprite(1).attributes ~= 0xC0 then
            fail("vertical flip near the top edge wrapped or XORed incorrectly.", stage)
            return
        end
    elseif stage == 9 then
        if count ~= 3 or sprite(4).y ~= 0xE7 or sprite(5).y ~= 0xE7
            or sprite(6).y ~= 0xE7 then
            fail("vertical flip near the bottom edge wrapped a component.", stage)
            return
        end
    elseif stage == 10 then
        if count ~= 7
            or not expectSprite(0, 0x6B, 0x00, 0xC0, 0x6C, stage, "combined flip")
            or not expectSprite(1, 0x6B, 0x00, 0x80, 0x64, stage, "combined flip")
            or not expectSprite(4, 0x5B, 0x03, 0xC0, 0x74, stage, "combined flip") then
            return
        end
    elseif stage == 11 or stage == 12 then
        if not allHidden() then
            fail("hidden movement or frame switching exposed an owned component.", stage)
            return
        end
    elseif stage == 13 then
        if count ~= 7
            or not expectSprite(0, 0x63, 0x06, 0x40, 0x74, stage, "flipped frame switch")
            or not expectSprite(1, 0x63, 0x06, 0x00, 0x6C, stage, "flipped frame switch") then
            return
        end
        emu.log("Metasprite pivot geometry, flip XOR, clipping, hidden movement, and flipped frame switching passed.")
        emu.stop(0)
        return
    end

    if totalFrames > 60 then
        fail("timed out before all deterministic stages completed.", stage)
    end
end

emu.addEventCallback(validateMetaspriteClipping, emu.eventType.endFrame)

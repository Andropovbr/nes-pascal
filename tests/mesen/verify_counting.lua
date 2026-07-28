local frameCount = 0

local function fail(message)
    emu.log("Counting example validation failed: " .. message)
    emu.stop(1)
end

local function expectByte(address, expected, name)
    local actual = emu.read(address, emu.memType.nesDebug)
    if actual ~= expected then
        fail(
            string.format(
                "%s was $%02X instead of $%02X.",
                name,
                actual,
                expected
            )
        )
        return false
    end
    return true
end

local function validateCountingResult()
    frameCount = frameCount + 1
    if frameCount < 3 then
        return
    end

    if not expectByte(0x0310, 0xFD, "Counter") then
        return
    elseif not expectByte(0x0311, 0x10, "Sum") then
        return
    elseif not expectByte(0x0312, 0x03, "Index") then
        return
    elseif not expectByte(0x0313, 0x00, "Reverse") then
        return
    elseif not expectByte(0x0314, 0x00, "Edge") then
        return
    elseif not expectByte(0x0315, 0x01, "Outer") then
        return
    elseif not expectByte(0x0316, 0x01, "Inner") then
        return
    elseif not expectByte(0x0317, 0x21, "BackgroundColor") then
        return
    end

    local paletteColor = emu.read(0x3F00, emu.memType.nesPpuDebug)
    if paletteColor ~= 0x21 then
        fail(
            string.format(
                "PPU palette entry $3F00 was $%02X instead of $21.",
                paletteColor
            )
        )
    else
        emu.log("Counting example validation passed.")
        emu.stop(0)
    end
end

emu.addEventCallback(validateCountingResult, emu.eventType.endFrame)

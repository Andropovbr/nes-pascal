local frameCount = 0

local function fail(message)
    emu.log("Zero Page validation failed: " .. message)
    emu.stop(1)
end

local function expectByte(address, expected, name)
    local actual = emu.read(address, emu.memType.nesDebug)
    if actual ~= expected then
        fail(
            string.format(
                "%s at $%04X was $%02X instead of $%02X.",
                name,
                address,
                actual,
                expected
            )
        )
        return false
    end
    return true
end

local function validateZeroPage()
    frameCount = frameCount + 1
    if frameCount < 3 then
        return
    end

    if not expectByte(0x0080, 0x01, "Counter") then
        return
    elseif not expectByte(0x0081, 0x21, "BackgroundColor") then
        return
    elseif not expectByte(0x0204, 0x01, "Matches") then
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
        emu.log("Zero Page validation passed.")
        emu.stop(0)
    end
end

emu.addEventCallback(
    validateZeroPage,
    emu.eventType.endFrame
)

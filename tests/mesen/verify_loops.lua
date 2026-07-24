local frameCount = 0

local function fail(message)
    emu.log("Loop example validation failed: " .. message)
    emu.stop(1)
end

local function validateLoopResult()
    frameCount = frameCount + 1
    if frameCount < 3 then
        return
    end

    local counter = emu.read(0x0300, emu.memType.nesDebug)
    local innerCounter = emu.read(0x0301, emu.memType.nesDebug)
    local backgroundColor = emu.read(0x0302, emu.memType.nesDebug)
    local paletteColor = emu.read(0x3F00, emu.memType.nesPpuDebug)

    if counter ~= 0x05 then
        fail(string.format("Counter was $%02X instead of $05.", counter))
    elseif innerCounter ~= 0x00 then
        fail(
            string.format(
                "InnerCounter was $%02X instead of $00.",
                innerCounter
            )
        )
    elseif backgroundColor ~= 0x21 then
        fail(
            string.format(
                "BackgroundColor was $%02X instead of $21.",
                backgroundColor
            )
        )
    elseif paletteColor ~= 0x21 then
        fail(
            string.format(
                "PPU palette entry $3F00 was $%02X instead of $21.",
                paletteColor
            )
        )
    else
        emu.log("Loop example validation passed.")
        emu.stop(0)
    end
end

emu.addEventCallback(validateLoopResult, emu.eventType.endFrame)

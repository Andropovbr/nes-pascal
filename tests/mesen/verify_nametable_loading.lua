local frames = 0

local function fail(message, code)
    emu.log("Nametable loading validation failed: " .. message)
    emu.stop(code)
end

local function validateNametable()
    frames = frames + 1
    if frames < 4 then
        return
    end

    for index = 0, 1023 do
        local expected = 0x30
        if index % 32 == 31 then
            expected = 0x0A
        end
        local actual = emu.read(0x2000 + index, emu.memType.nesPpuDebug)
        if actual ~= expected then
            fail(
                string.format(
                    "PPU byte $%04X was $%02X instead of $%02X.",
                    0x2000 + index,
                    actual,
                    expected
                ),
                2
            )
            return
        end
    end

    emu.log("Complete nametable and attribute-table upload validation passed.")
    emu.stop(0)
end

emu.addEventCallback(validateNametable, emu.eventType.endFrame)

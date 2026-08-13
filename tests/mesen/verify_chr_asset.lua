local frames = 0

local function fail(message, code)
    emu.log("CHR-ROM validation failed: " .. message)
    emu.stop(code)
end

local function validateChrRom()
    frames = frames + 1
    if frames < 4 then
        return
    end

    for index = 0, 8191 do
        local expected
        if index == 8191 then
            expected = 0x0A
        else
            local mod = index % 16
            if mod < 10 then
                expected = 0x30 + mod
            else
                expected = 0x41 + (mod - 10)
            end
        end

        local actual = emu.read(index, emu.memType.nesPpuDebug)
        if actual ~= expected then
            fail(
                string.format(
                    "PPU pattern table byte $%04X was $%02X instead of $%02X.",
                    index,
                    actual,
                    expected
                ),
                2
            )
            return
        end
    end

    emu.log("CHR-ROM pattern table embedding validation passed.")
    emu.stop(0)
end

emu.addEventCallback(validateChrRom, emu.eventType.endFrame)

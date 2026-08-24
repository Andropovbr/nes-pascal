local checked = false

local function fail(message, code)
    emu.log("Random-number validation failed: " .. message)
    emu.stop(code)
end

local function expectByte(address, expected, label, code)
    local actual = emu.read(address, emu.memType.nesDebug)
    if actual ~= expected then
        fail(label .. " expected $" .. string.format("%02X", expected)
            .. " but found $" .. string.format("%02X", actual), code)
        return false
    end
    return true
end

local function validateRandomNumbers()
    if checked then
        return
    end
    if emu.read(0x0000, emu.memType.nesDebug) == 0
        or emu.read(0x020A, emu.memType.nesDebug) == 0 then
        return
    end
    checked = true

    local sequence = {
        0x15, 0x8A, 0x45, 0xA2, 0xD1, 0xE8, 0x74, 0xBA,
        0x5D, 0x2E, 0x97, 0x4B, 0xA5, 0xD2, 0x69, 0x34
    }
    for index = 0, 15 do
        if not expectByte(0x020A + index, sequence[index + 1],
            "known seeded sequence byte " .. index, 10 + index) then
            return
        end
    end

    if not expectByte(0x021B, 0x02, "three-value range", 30) then return end
    if not expectByte(0x021C, 0x5C, "hundred-value range", 31) then return end
    if not expectByte(0x021D, 0x15, "full-byte range", 32) then return end
    if not expectByte(0x021E, 0x33, "singleton range", 33) then return end
    if not expectByte(0x021F, 0x15, "state after singleton", 34) then return end
    if not expectByte(0x0222, 0x20, "dynamic invalid range", 35) then return end
    if not expectByte(0x0223, 0x15, "state after invalid range", 36) then return end
    if not expectByte(0x0224, 0x70, "zero-seed normalization", 37) then return end
    if not expectByte(0x0225, 0x75, "right-first complex arithmetic", 38) then return end
    if not expectByte(0x0226, 0x8B, "left-to-right function arguments", 39) then return end
    if not expectByte(0x0227, 0x15, "function RNG return", 40) then return end
    if not expectByte(0x0080, 0x00, "short-circuit and condition", 41) then return end
    if not expectByte(0x0081, 0x01, "short-circuit or condition", 42) then return end
    if not expectByte(0x0228, 0x15, "state after short-circuit and", 43) then return end
    if not expectByte(0x0229, 0x15, "state after short-circuit or", 44) then return end
    if not expectByte(0x022A, 0x8F, "nested Function/TemporaryPool integration", 45) then return end

    if not expectByte(0x0204, 0x8A, "final LFSR low state", 46) then return end
    if not expectByte(0x0205, 0xBE, "final LFSR high state", 47) then return end

    emu.log("Random-number validation passed.")
    emu.stop(0)
end

emu.addEventCallback(validateRandomNumbers, emu.eventType.endFrame)

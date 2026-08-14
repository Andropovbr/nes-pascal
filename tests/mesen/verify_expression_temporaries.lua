local frameCount = 0

local function fail(message, code)
    emu.log("Expression temporary validation failed: " .. message)
    emu.stop(code)
end

local function expectByte(address, expected, name, failureCode)
    local actual = emu.read(address, emu.memType.nesDebug)
    if actual ~= expected then
        fail(
            string.format("%s was $%02X instead of $%02X.", name, actual, expected),
            failureCode
        )
    end
end

local function validateExpressionTemporaries()
    frameCount = frameCount + 1
    if frameCount < 3 then
        return
    end

    -- Addresses are asserted against the compiler's deterministic memory map.
    expectByte(0x0217, 0x10, "one-temporary wraparound", 11)
    expectByte(0x0218, 0x15, "two-temporary arithmetic", 12)
    expectByte(0x0219, 0x17, "three-temporary arithmetic", 13)
    expectByte(0x021A, 0x17, "sequential slot reuse", 14)
    expectByte(0x021B, 0x02, "nested array index", 15)
    expectByte(0x021C, 0x91, "record-array expression", 16)
    expectByte(0x021D, 0x15, "first procedure argument", 17)
    expectByte(0x021E, 0x10, "second procedure argument", 18)
    expectByte(0x021F, 0x01, "nested comparison", 21)
    expectByte(0x020A, 0x15, "indexed array assignment", 19)
    expectByte(0x0215, 0x15, "indexed record assignment", 20)

    emu.log("Expression temporary validation passed.")
    emu.stop(0)
end

emu.addEventCallback(validateExpressionTemporaries, emu.eventType.endFrame)

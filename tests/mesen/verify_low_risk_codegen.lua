local frameCount = 0

local function fail(message, code)
    emu.log("Low-risk codegen validation failed: " .. message)
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

local function validateOptimizedControlFlow()
    frameCount = frameCount + 1
    if frameCount < 3 then
        return
    end

    expectByte(0x0080, 0x03, "Left", 11)
    expectByte(0x0081, 0x03, "Right", 12)
    expectByte(0x0082, 0x03, "BranchScore", 13)
    expectByte(0x0083, 0x02, "LoopCount", 14)
    expectByte(0x0084, 0x02, "RepeatCount", 15)
    expectByte(0x0204, 0x01, "StoredTrue", 16)
    expectByte(0x0085, 0x00, "StoredFalse", 17)

    emu.log("Low-risk codegen validation passed.")
    emu.stop(0)
end

emu.addEventCallback(validateOptimizedControlFlow, emu.eventType.endFrame)

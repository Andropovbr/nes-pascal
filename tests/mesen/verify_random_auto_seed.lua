local frames = 0
local strobeCount = 0
local latched = 0
local readIndex = 0
local seedFrame = nil

local function xorByte(left, right)
    local result = 0
    local place = 1
    for _ = 0, 7 do
        local leftBit = left % 2
        local rightBit = right % 2
        if leftBit ~= rightBit then
            result = result + place
        end
        left = math.floor(left / 2)
        right = math.floor(right / 2)
        place = place * 2
    end
    return result
end

local function expectedFirstByte(frame, controller)
    local mixed = xorByte(frame, controller)
    local low = xorByte(mixed, 0xE1)
    local high = xorByte(mixed, 0xAC)
    local oldLowBit = low % 2
    low = math.floor(low / 2) + (high % 2) * 128
    high = math.floor(high / 2)
    if oldLowBit == 1 then
        high = xorByte(high, 0xB4)
    end
    return low, high
end

local function onStrobeWrite(address, value)
    if value == 1 then
        strobeCount = strobeCount + 1
        latched = (strobeCount == 6 or strobeCount == 7) and 0x08 or 0x00
        if strobeCount == 6 then
            seedFrame = emu.read(0x0000, emu.memType.nesDebug)
        end
        readIndex = 0
    end
end

local function onControllerRead(address, value)
    local bit = math.floor(latched / (2 ^ readIndex)) % 2
    readIndex = readIndex + 1
    return bit
end

local function validateAutoSeed()
    frames = frames + 1
    local captured = emu.read(0x0080, emu.memType.nesDebug)
    if captured == 1 then
        local frame = seedFrame
        local controller = emu.read(0x0003, emu.memType.nesDebug)
        local actual = emu.read(0x0206, emu.memType.nesDebug)
        local expectedLow, expectedHigh = expectedFirstByte(frame, controller)
        local actualHigh = emu.read(0x0205, emu.memType.nesDebug)
        local earlyLow = expectedFirstByte(1, 0)
        if frame == nil or frame < 5 then
            emu.log("Automatic seed validation failed: RNG activated before delayed input.")
            emu.stop(20)
        elseif controller ~= 0x08 then
            emu.log("Automatic seed validation failed: Start state was not mixed.")
            emu.stop(21)
        elseif actual ~= expectedLow or actualHigh ~= expectedHigh then
            emu.log("Automatic seed validation failed: timing/input mix did not match contract.")
            emu.stop(22)
        elseif actual == earlyLow then
            emu.log("Automatic seed validation failed: delayed timing matched early baseline.")
            emu.stop(23)
        else
            emu.log("Automatic seed timing/controller validation passed.")
            emu.stop(0)
        end
    elseif frames > 30 then
        emu.log("Automatic seed validation failed: timed out waiting for delayed Start.")
        emu.stop(24)
    end
end

emu.addMemoryCallback(onStrobeWrite, emu.callbackType.write, 0x4016)
emu.addMemoryCallback(onControllerRead, emu.callbackType.read, 0x4016)
emu.addEventCallback(validateAutoSeed, emu.eventType.endFrame)

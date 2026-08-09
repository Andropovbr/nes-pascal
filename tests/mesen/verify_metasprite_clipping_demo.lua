local seen = {}
local totalFrames = 0

local function read(address)
    return emu.read(address, emu.memType.nesDebug)
end

local function visibleCount()
    local count = 0
    for slot = 0, 6 do
        if read(0x0200 + slot * 4) ~= 0xFF then
            count = count + 1
        end
    end
    return count
end

local function fail(message, stage)
    emu.log("Visual clipping demo validation failed: " .. message)
    emu.stop(80 + stage)
end

local function validateTarget(stage, expectedX, expectedY, expectedVisible)
    if read(0x0082) ~= expectedX then
        fail("stage transition did not stop at its expected X target.", stage)
        return false
    end
    if read(0x0083) ~= expectedY then
        fail("stage transition did not stop at its expected Y target.", stage)
        return false
    end
    if visibleCount() ~= expectedVisible then
        fail("partial target clipped the wrong number of components.", stage)
        return false
    end
    if read(0x0303) ~= 1 then
        fail("a clipping stage inherited flip or hidden state.", stage)
        return false
    end
    for slot = 0, 6 do
        local address = 0x0200 + slot * 4
        local y = read(address)
        if y ~= 0xFF then
            local x = read(address + 3)
            if x > 248 or y > 231 then
                fail("a visible component wrapped outside representable coordinates.", stage)
                return false
            end
        end
    end
    return true
end

local function validateClippingDemo()
    totalFrames = totalFrames + 1
    local stage = read(0x0081)
    if stage >= 1 and stage <= 7 and not seen[stage] then
        local expected = {
            [1] = { 0x08, 0x68, 6 },
            [2] = { 0x70, 0x68, 7 },
            [3] = { 0xF8, 0x68, 4 },
            [4] = { 0x70, 0x68, 7 },
            [5] = { 0x70, 0x08, 5 },
            [6] = { 0x70, 0x68, 7 },
            [7] = { 0x70, 0xEC, 4 },
        }
        local target = expected[stage]
        if not validateTarget(stage, target[1], target[2], target[3]) then return end
        seen[stage] = true
    elseif stage == 7 and seen[7] and read(0x0083) == 0x68 then
        if not validateTarget(0, 0x70, 0x68, 7) then return end
        emu.log("Human-facing partial clipping demo completed one clear edge cycle.")
        emu.stop(0)
    end

    if totalFrames > 1200 then
        fail("timed out before the complete visual edge cycle.", stage)
    end
end

emu.addEventCallback(validateClippingDemo, emu.eventType.endFrame)

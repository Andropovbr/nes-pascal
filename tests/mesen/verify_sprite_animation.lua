local previousStep = 0

local function read(address)
    return emu.read(address, emu.memType.nesDebug)
end

local function fail(message)
    emu.log("Sprite animation validation failed: " .. message)
    emu.stop(1)
end

local function expectedCycle(elapsed)
    local phase = elapsed % 6
    if phase == 0 then return 0, 2 end
    if phase == 1 then return 0, 1 end
    if phase == 2 then return 1, 3 end
    if phase == 3 then return 1, 2 end
    if phase == 4 then return 1, 1 end
    return 2, 1
end

local function assertState(instance, animation, frameIndex, timer, flags, frameId)
    local animationValue = read(0x0308 + instance)
    local frameIndexValue = read(0x030A + instance)
    local timerValue = read(0x030C + instance)
    local flagsValue = read(0x030E + instance)
    local frameValue = read(0x0304 + instance)
    if animationValue ~= animation or frameIndexValue ~= frameIndex
        or timerValue ~= timer or flagsValue ~= flags or frameValue ~= frameId then
        fail(
            "instance " .. instance .. " state was "
            .. animationValue .. "/" .. frameIndexValue .. "/" .. timerValue
            .. "/" .. flagsValue .. "/" .. frameValue .. ", expected "
            .. animation .. "/" .. frameIndex .. "/" .. timer
            .. "/" .. flags .. "/" .. frameId
        )
        return false
    end
    return true
end

local function slotVisible(slot)
    return read(0x0200 + slot * 4) ~= 0xFF
end

local function validateFirst(step)
    local expectedVisualFlags = step >= 8 and 7 or 1
    if read(0x0306) ~= expectedVisualFlags then
        fail("animation switching or restart changed visibility/flip state.")
        return false
    end
    if step <= 15 then
        local frameIndex, timer = expectedCycle(step)
        return assertState(0, 0, frameIndex, timer, 0x80, frameIndex)
    elseif step == 16 then
        return assertState(0, 1, 0, 1, 0x80, 3)
    elseif step == 17 then
        return assertState(0, 1, 1, 2, 0x80, 4)
    elseif step == 18 then
        return assertState(0, 1, 1, 1, 0x80, 4)
    elseif step >= 19 and step <= 22 then
        return assertState(0, 1, 1, 0, 0x81, 4)
    elseif step == 23 then
        return assertState(0, 1, 0, 1, 0x80, 3)
    elseif step == 24 then
        return assertState(0, 1, 1, 2, 0x80, 4)
    elseif step == 25 then
        return assertState(0, 1, 1, 1, 0x80, 4)
    end
    return assertState(0, 1, 1, 0, 0x81, 4)
end

local function validateSecond(step)
    if step < 3 then
        return assertState(1, 0, 0, 0, 0, 0)
    elseif step >= 32 then
        return assertState(1, 0, 0, 0, 0, 0)
    end
    local frameIndex, timer = expectedCycle(step - 3)
    return assertState(1, 0, frameIndex, timer, 0x80, frameIndex)
end

local function validateOam(step)
    if not slotVisible(0) then
        fail("the first instance unexpectedly became hidden.")
        return false
    end
    if step >= 25 and step < 29 then
        if slotVisible(2) or slotVisible(3) then
            fail("hidden playback published an OAM component.")
            return false
        end
    elseif step >= 3 then
        if not slotVisible(2) then
            fail("the second instance did not become visible again.")
            return false
        end
        local frameIndex = read(0x030A + 1)
        local expectedSecondSlot = step < 32 and frameIndex == 1
        if slotVisible(3) ~= expectedSecondSlot then
            fail("a frame component-count change left an incorrect OAM slot.")
            return false
        end
    end
    return true
end

local function validateSpriteAnimation()
    local step = read(0x0082)
    if step == previousStep then return end
    if step ~= previousStep + 1 then
        fail("the update callback skipped a logical game frame.")
        return
    end
    previousStep = step

    if not validateFirst(step) or not validateSecond(step) or not validateOam(step) then
        return
    end

    local finished = read(0x031C)
    local expectedFinished = (step >= 19 and step <= 23) or step >= 26
    if finished ~= (expectedFinished and 1 or 0) then
        fail("the one-shot completion query returned the wrong value.")
        return
    end

    if step == 32 then
        if read(0x0307) ~= 1 then
            fail("manual frame selection changed visibility.")
            return
        end
        emu.log("Sprite animation validation passed.")
        emu.stop(0)
    end
end

emu.addEventCallback(
    validateSpriteAnimation,
    emu.eventType.endFrame
)

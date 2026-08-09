local phase = 0
local phaseFrames = 0
local previousProcessed = nil
local latchedController1 = 0
local controllerReadIndex = 0
local baselineX = 0
local baselineY = 0
local baselineAnimationFrame = 0
local sawAnimationAdvance = false

local phaseInputs = {
    [0] = 0x00,
    [1] = 0x40,
    [2] = 0x00,
    [3] = 0x10,
    [4] = 0x00,
    [5] = 0x80,
    [6] = 0x00,
}

local function read(address)
    return emu.read(address, emu.memType.nesDebug)
end

local function fail(message)
    emu.log("Animated player validation failed: " .. message)
    emu.stop(20 + phase)
end

local function serialBit(value, index)
    return math.floor(value / (2 ^ index)) % 2
end

local function onStrobeWrite(address, value)
    if value == 1 then
        latchedController1 = phaseInputs[phase]
        controllerReadIndex = 0
    end
end

local function onController1Read(address, value)
    local bit = serialBit(latchedController1, controllerReadIndex)
    controllerReadIndex = controllerReadIndex + 1
    return bit
end

local function onController2Read(address, value)
    return 0
end

local function horizontalBounds()
    local minimum = 0xFF
    local maximumExclusive = 0
    for slot = 0, 6 do
        local address = 0x0200 + slot * 4
        if read(address) ~= 0xFF then
            local x = read(address + 3)
            if x < minimum then minimum = x end
            if x + 8 > maximumExclusive then maximumExclusive = x + 8 end
        end
    end
    return minimum, maximumExclusive
end

local function validateGeometry(playerX, horizontalFlip)
    local minimum, maximumExclusive = horizontalBounds()
    if minimum ~= playerX - 12 or maximumExclusive ~= playerX + 12 then
        fail("horizontal flip moved the centered visible bounding range.")
        return false
    end

    local firstX = read(0x0203)
    local firstAttributes = read(0x0202)
    local secondX = read(0x0207)
    local secondAttributes = read(0x0206)
    if horizontalFlip then
        if firstX ~= playerX - 4 or firstAttributes ~= 0x40
            or secondX ~= playerX - 12 or secondAttributes ~= 0 then
            fail("whole flip did not mirror placement and XOR source attributes.")
            return false
        end
    else
        if firstX ~= playerX - 4 or firstAttributes ~= 0
            or secondX ~= playerX + 4 or secondAttributes ~= 0x40 then
            fail("unflipped centered geometry or source attributes changed.")
            return false
        end
    end
    if read(0x021C) ~= 0xFF then
        fail("animation changed the static seven-slot OAM reservation.")
        return false
    end
    return true
end

local function beginObservation(playerX, playerY, animationFrame)
    phaseFrames = 1
    baselineX = playerX
    baselineY = playerY
    baselineAnimationFrame = animationFrame
    sawAnimationAdvance = false
end

local function observeAdvance(animationFrame)
    phaseFrames = phaseFrames + 1
    if animationFrame ~= baselineAnimationFrame then
        sawAnimationAdvance = true
    end
end

local function requireAnimation(expectedAnimation, animationFrame, selectedFrame)
    if read(0x0304) ~= expectedAnimation then
        fail("the selected animation identity is incorrect.")
        return false
    end
    local expectedFrame = expectedAnimation == 0 and animationFrame or 6 + animationFrame
    if selectedFrame ~= expectedFrame then
        fail("animation state did not select its shared immutable frame ID.")
        return false
    end
    if read(0x0307) ~= 0x80 then
        fail("looping animation active/completion flags are incorrect.")
        return false
    end
    return true
end

local function advancePhase()
    phase = phase + 1
    phaseFrames = 0
    sawAnimationAdvance = false
end

local function validateAnimatedPlayer()
    local processed = read(0x0002)
    if previousProcessed == processed then return end
    previousProcessed = processed

    if read(0x0303) % 2 == 0 or read(0x0307) ~= 0x80 then return end

    local expectedInput = phaseInputs[phase]
    local controller = read(0x0003)
    if controller ~= expectedInput then return end

    local playerX = read(0x0081)
    local playerY = read(0x0082)
    local moving = read(0x0084)
    local visualFlags = read(0x0303)
    local animationFrame = read(0x0305)
    local selectedFrame = read(0x0302)
    local horizontalFlip = math.floor(visualFlags / 2) % 2 == 1

    local expectedAnimation = (phase == 1 or phase == 3 or phase == 5) and 1 or 0
    local expectedMoving = expectedAnimation == 1 and 1 or 0
    if moving ~= expectedMoving then
        fail("Moving did not match stationary/movement input state.")
        return
    end
    if not requireAnimation(expectedAnimation, animationFrame, selectedFrame) then return end
    if not validateGeometry(playerX, horizontalFlip) then return end
    if read(0x0311) ~= 0x1E then
        fail("the complete left-edge PPUMASK state regressed.")
        return
    end

    if phaseFrames == 0 then
        beginObservation(playerX, playerY, animationFrame)
    else
        observeAdvance(animationFrame)
    end

    if phase == 0 then
        if horizontalFlip then
            fail("initial idle unexpectedly changed facing.")
            return
        end
    elseif phase == 1 then
        if not horizontalFlip or playerY ~= baselineY then
            fail("left movement did not set facing or changed the wrong axis.")
            return
        end
        if phaseFrames > 1 and playerX >= baselineX then
            fail("left movement did not advance while animation continued.")
            return
        end
    elseif phase == 2 then
        if not horizontalFlip or playerX ~= baselineX or playerY ~= baselineY then
            fail("left-facing idle did not preserve facing and position.")
            return
        end
    elseif phase == 3 then
        if not horizontalFlip or playerX ~= baselineX then
            fail("vertical movement reset horizontal facing or changed X.")
            return
        end
        if phaseFrames > 1 and playerY >= baselineY then
            fail("up movement did not advance while animation continued.")
            return
        end
    elseif phase == 4 then
        if not horizontalFlip or playerX ~= baselineX or playerY ~= baselineY then
            fail("idle after vertical movement lost left-facing state.")
            return
        end
    elseif phase == 5 then
        if horizontalFlip or playerY ~= baselineY then
            fail("right movement did not clear facing or changed the wrong axis.")
            return
        end
        if phaseFrames > 1 and playerX <= baselineX then
            fail("right movement did not advance while animation continued.")
            return
        end
    elseif phase == 6 then
        if horizontalFlip or playerX ~= baselineX or playerY ~= baselineY then
            fail("right-facing idle did not preserve facing and position.")
            return
        end
    end

    if phaseFrames >= 8 then
        if not sawAnimationAdvance then
            fail("repeated set_animation restarted or froze the active sequence.")
            return
        end
        if phase == 6 then
            emu.log("Animated player idle/movement/facing validation passed.")
            emu.stop(0)
        else
            advancePhase()
        end
    end
end

emu.addMemoryCallback(onStrobeWrite, emu.callbackType.write, 0x4016)
emu.addMemoryCallback(onController1Read, emu.callbackType.read, 0x4016)
emu.addMemoryCallback(onController2Read, emu.callbackType.read, 0x4017)
emu.addEventCallback(validateAnimatedPlayer, emu.eventType.endFrame)

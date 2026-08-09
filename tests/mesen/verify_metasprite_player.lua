local phase = 0
local phaseFrames = 0
local totalFrames = 0
local inputSeen = false
local boundaryReached = false
local baselineX = 0
local baselineY = 0
local latchedController1 = 0
local controllerReadIndex = 0
local leftEdgeBaseline = {}

local directions = {
    { mask = 0x40, dx = -1, dy = 0, name = "left" },
    { mask = 0x80, dx = 1, dy = 0, name = "right" },
    { mask = 0x10, dx = 0, dy = -1, name = "up" },
    { mask = 0x20, dx = 0, dy = 1, name = "down" },
    { mask = 0x50, dx = -1, dy = -1, name = "up-left" },
    { mask = 0x90, dx = 1, dy = -1, name = "up-right" },
    { mask = 0xA0, dx = 1, dy = 1, name = "down-right" },
    { mask = 0x60, dx = -1, dy = 1, name = "down-left" },
}

local boundaryPhases = {
    [9] = { mask = 0x10, axis = "y", value = 0x0D, name = "top" },
    [10] = { mask = 0x20, axis = "y", value = 0xE4, name = "bottom" },
    [11] = { mask = 0x80, axis = "x", value = 0xF4, name = "right" },
    [12] = { mask = 0x40, axis = "x", value = 0x0C, name = "left" },
}

local function fail(message)
    emu.log("Metasprite player validation failed: " .. message)
    emu.stop(30 + phase)
end

local function phaseInput()
    if phase >= 1 and phase <= 8 then
        return directions[phase].mask
    elseif phase >= 9 and phase <= 12 then
        return boundaryPhases[phase].mask
    elseif phase == 13 then
        return 0x01
    elseif phase == 15 or phase == 18 then
        return 0x04
    elseif phase == 16 then
        return 0x90
    end
    return 0
end

local function serialBit(value, index)
    return math.floor(value / (2 ^ index)) % 2
end

local function advance(nextPhase)
    phase = nextPhase
    phaseFrames = 0
    inputSeen = false
    boundaryReached = false
end

local function onStrobeWrite(address, value)
    if value == 1 then
        latchedController1 = phaseInput()
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

local function allOwnedSlotsHidden()
    for sprite = 0, 6 do
        if emu.read(0x0200 + sprite * 4, emu.memType.nesDebug) ~= 0xFF then
            return false
        end
    end
    return true
end

local function allOwnedSlotsVisible()
    for sprite = 0, 6 do
        if emu.read(0x0200 + sprite * 4, emu.memType.nesDebug) == 0xFF then
            return false
        end
    end
    return true
end

local function validateVisibleFrame(expectedTile, horizontalFlip)
    local playerX = emu.read(0x0081, emu.memType.nesDebug)
    local playerY = emu.read(0x0082, emu.memType.nesDebug)
    local y = emu.read(0x0200, emu.memType.nesDebug)
    local tile = emu.read(0x0201, emu.memType.nesDebug)
    local attributes = emu.read(0x0202, emu.memType.nesDebug)
    local x = emu.read(0x0203, emu.memType.nesDebug)
    local expectedAttributes = horizontalFlip and 0x40 or 0x00
    return y == playerY - 13 and tile == expectedTile
        and attributes == expectedAttributes and x == playerX - 4
end

local function horizontalBounds()
    local minimum = 0xFF
    local maximumExclusive = 0
    for sprite = 0, 6 do
        local address = 0x0200 + sprite * 4
        if emu.read(address, emu.memType.nesDebug) ~= 0xFF then
            local x = emu.read(address + 3, emu.memType.nesDebug)
            if x < minimum then minimum = x end
            if x + 8 > maximumExclusive then maximumExclusive = x + 8 end
        end
    end
    return minimum, maximumExclusive
end

local function verticalBounds()
    local minimum = 0xFF
    local maximumExclusive = 0
    for sprite = 0, 6 do
        local y = emu.read(0x0200 + sprite * 4, emu.memType.nesDebug)
        if y ~= 0xFF then
            local logicalTop = y + 1
            if logicalTop < minimum then minimum = logicalTop end
            if logicalTop + 8 > maximumExclusive then
                maximumExclusive = logicalTop + 8
            end
        end
    end
    return minimum, maximumExclusive
end

local function validateGameplayBoundary(currentPhase)
    if not allOwnedSlotsVisible() then
        fail(boundaryPhases[currentPhase].name .. " gameplay limit clipped a component.")
        return false
    end
    if currentPhase == 9 or currentPhase == 10 then
        local minimumY, maximumY = verticalBounds()
        local expectedMinimum = currentPhase == 9 and 1 or 216
        local expectedMaximum = currentPhase == 9 and 25 or 240
        if minimumY ~= expectedMinimum or maximumY ~= expectedMaximum then
            fail(boundaryPhases[currentPhase].name .. " gameplay limit left an incorrect vertical range.")
            return false
        end
    else
        local minimumX, maximumX = horizontalBounds()
        local expectedMinimum = currentPhase == 12 and 0 or 232
        local expectedMaximum = currentPhase == 12 and 24 or 256
        if minimumX ~= expectedMinimum or maximumX ~= expectedMaximum then
            fail(boundaryPhases[currentPhase].name .. " gameplay limit moved or clipped the horizontal bounds.")
            return false
        end
        if currentPhase == 12 then
            if not validateVisibleFrame(0, true) then
                fail("left gameplay limit did not preserve the flipped frame geometry.")
                return false
            end
            local renderedDifference = false
            local index = 1
            for y = 216, 239 do
                for x = 0, 7 do
                    if emu.getPixel(x, y) ~= leftEdgeBaseline[index] then
                        renderedDifference = true
                    end
                    index = index + 1
                end
            end
            if not renderedDifference then
                fail("leftmost metasprite component was masked from the rendered frame.")
                return false
            end
        end
    end
    return true
end

local function validateMetaspritePlayer()
    totalFrames = totalFrames + 1
    phaseFrames = phaseFrames + 1
    local controller = emu.read(0x0003, emu.memType.nesDebug)
    local previous = emu.read(0x0004, emu.memType.nesDebug)
    local playerX = emu.read(0x0081, emu.memType.nesDebug)
    local playerY = emu.read(0x0082, emu.memType.nesDebug)
    local frame = emu.read(0x0302, emu.memType.nesDebug)
    local flags = emu.read(0x0303, emu.memType.nesDebug)

    if phase == 0 then
        if emu.read(0x0000, emu.memType.nesDebug) > 2 and flags == 1 then
            if not validateVisibleFrame(0, false) then
                fail("initial frame geometry or logical Y conversion is incorrect.")
                return
            end
            local index = 1
            for y = 216, 239 do
                for x = 0, 7 do
                    leftEdgeBaseline[index] = emu.getPixel(x, y)
                    index = index + 1
                end
            end
            if emu.read(0x030D, emu.memType.nesDebug) ~= 0x1E then
                fail("normal rendering did not preserve the complete $1E PPUMASK state.")
                return
            end
            advance(1)
        end
    elseif phase >= 1 and phase <= 8 then
        local direction = directions[phase]
        if controller == direction.mask then
            if not inputSeen then
                inputSeen = true
                baselineX = playerX
                baselineY = playerY
            else
                local dx = playerX - baselineX
                local dy = playerY - baselineY
                if dx == direction.dx and dy == direction.dy then
                    local horizontalFlip = math.floor(flags / 2) % 2
                    if direction.dx < 0 and horizontalFlip ~= 1 then
                        fail(direction.name .. " did not enable whole horizontal flip.")
                        return
                    elseif direction.dx > 0 and horizontalFlip ~= 0 then
                        fail(direction.name .. " did not clear whole horizontal flip.")
                        return
                    end
                    if phase == 1 then
                        local firstX = emu.read(0x0203, emu.memType.nesDebug)
                        local firstAttributes = emu.read(0x0202, emu.memType.nesDebug)
                        local secondX = emu.read(0x0207, emu.memType.nesDebug)
                        local secondAttributes = emu.read(0x0206, emu.memType.nesDebug)
                        local minimumX, maximumX = horizontalBounds()
                        if firstX ~= playerX - 4 or firstAttributes ~= 0x40
                            or secondX ~= playerX - 12 or secondAttributes ~= 0
                            or minimumX ~= playerX - 12 or maximumX ~= playerX + 12 then
                            fail("centered whole flip moved the bounds or XORed source flips incorrectly.")
                            return
                        end
                    end
                    advance(phase + 1)
                elseif dx ~= 0 or dy ~= 0 then
                    fail(direction.name .. " changed the wrong axes.")
                    return
                end
            end
        end
    elseif phase >= 9 and phase <= 12 then
        local boundary = boundaryPhases[phase]
        if controller == boundary.mask then
            local coordinate = boundary.axis == "x" and playerX or playerY
            if coordinate == boundary.value then
                if not boundaryReached then
                    boundaryReached = true
                    baselineX = playerX
                    baselineY = playerY
                else
                    if playerX ~= baselineX or playerY ~= baselineY then
                        fail(boundary.name .. " gameplay limit allowed movement beyond its bound.")
                        return
                    end
                    if not validateGameplayBoundary(phase) then return end
                    advance(phase + 1)
                end
            end
        end
    elseif phase == 13 then
        if controller == 0x01 and previous % 2 == 0 and frame == 2 then
            if math.floor(flags / 2) % 2 ~= 1
                or not validateVisibleFrame(6, true) then
                fail("frame switching did not preserve centered horizontal flip geometry.")
                return
            end
            advance(14)
        end
    elseif phase == 14 then
        if controller == 0 and previous == 0x01 then
            advance(15)
        end
    elseif phase == 15 then
        if controller == 0x04 and previous == 0 and flags % 2 == 0 then
            if not allOwnedSlotsHidden() then
                fail("hide did not affect every reserved component slot.")
                return
            end
            advance(16)
        end
    elseif phase == 16 then
        if controller == 0x90 then
            if not inputSeen then
                inputSeen = true
                baselineX = playerX
                baselineY = playerY
            elseif playerX == baselineX + 1 and playerY == baselineY - 1 then
                if flags % 2 ~= 0 or not allOwnedSlotsHidden() then
                    fail("moving while hidden made a component visible.")
                    return
                end
                advance(17)
            elseif playerX ~= baselineX or playerY ~= baselineY then
                fail("hidden diagonal movement changed the wrong axes.")
                return
            end
        end
    elseif phase == 17 then
        if controller == 0 and previous == 0x90 then
            advance(18)
        end
    elseif phase == 18 then
        if controller == 0x04 and previous == 0 and flags % 2 == 1 then
            if frame ~= 2 or not validateVisibleFrame(6, false) then
                fail("show did not restore the selected frame at the moved position.")
                return
            end
            advance(19)
        end
    elseif phase == 19 then
        local shadowY = emu.read(0x0200, emu.memType.nesDebug)
        local ppuY = emu.read(0x00, emu.memType.nesSpriteRam)
        if shadowY == ppuY then
            emu.log("Metasprite movement, all four gameplay bounds, frame selection, flip, hide/show, and DMA passed.")
            emu.stop(0)
            return
        end
    end

    if phaseFrames > 300 or totalFrames > 1200 then
        fail("timed out in phase " .. phase .. ".")
    end
end

emu.addMemoryCallback(onStrobeWrite, emu.callbackType.write, 0x4016)
emu.addMemoryCallback(onController1Read, emu.callbackType.read, 0x4016)
emu.addMemoryCallback(onController2Read, emu.callbackType.read, 0x4017)
emu.addEventCallback(validateMetaspritePlayer, emu.eventType.endFrame)

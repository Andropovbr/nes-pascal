local runtimeFrames = 0
local updateFrames = 0
local previousRuntime = nil
local previousUpdate = nil
local previousVBlank = nil
local sawRuntimeWrap = false

local function fail(message)
    emu.log("Frame callback validation failed: " .. message)
    emu.stop(1)
end

local function byteDelta(current, previous)
    return (current - previous) % 256
end

local function validateFrameCallbacks()
    local runtimeCounter = emu.read(0x0000, emu.memType.nesDebug)
    local updateCounter = emu.read(0x0204, emu.memType.nesDebug)
    local vblankCounter = emu.read(0x0205, emu.memType.nesDebug)

    if previousRuntime ~= nil then
        local runtimeDelta = byteDelta(runtimeCounter, previousRuntime)
        local updateDelta = byteDelta(updateCounter, previousUpdate)
        local vblankDelta = byteDelta(vblankCounter, previousVBlank)

        if runtimeDelta > 1 then
            fail("The runtime counter advanced more than once in one frame.")
            return
        elseif updateDelta > 1 then
            fail("The update callback ran more than once in one frame.")
            return
        elseif vblankDelta > 1 then
            fail("The VBlank callback ran more than once in one frame.")
            return
        end

        if runtimeDelta == 1 then
            runtimeFrames = runtimeFrames + 1
        end
        if updateDelta == 1 then
            updateFrames = updateFrames + 1
        end
        if runtimeFrames > 1 and updateDelta ~= runtimeDelta then
            fail("The update callback did not run once for the observed frame.")
            return
        end
        if previousRuntime > runtimeCounter then
            sawRuntimeWrap = true
        end

        if runtimeCounter ~= vblankCounter then
            fail("The VBlank callback did not run exactly once with its NMI.")
            return
        end

        local updateLag = byteDelta(runtimeCounter, updateCounter)
        if updateLag > 1 then
            fail("The main-thread update callback fell more than one frame behind.")
            return
        end
    end

    previousRuntime = runtimeCounter
    previousUpdate = updateCounter
    previousVBlank = vblankCounter

    if runtimeFrames < 260 then
        return
    end
    if not sawRuntimeWrap then
        fail("The runtime counter did not wrap during validation.")
        return
    elseif updateFrames < runtimeFrames - 1 then
        fail("The update callback did not advance once per observed frame.")
        return
    end

    local paletteColor = emu.read(0x3F00, emu.memType.nesPpuDebug)
    if paletteColor ~= 0x21 then
        fail("The universal background color changed unexpectedly.")
        return
    end

    emu.log("Frame callback validation passed across counter wraparound.")
    emu.stop(0)
end

emu.addEventCallback(
    validateFrameCallbacks,
    emu.eventType.endFrame
)

-- Debug camera for fitting armour: circles the player in four fixed stops,
-- front, side, back, other side, one every PERIOD seconds, so F12 screenshots
-- taken on a timer see the suit from every side. Never shipped: it is loaded
-- only by passing tools/viewer as a data directory and
-- zenar_viewer.omwscripts as content on the command line.
local camera = require('openmw.camera')
local self = require('openmw.self')
local util = require('openmw.util')

local DIST, HEIGHT, PITCH, PERIOD, SETTLE = 190, 80, 0.12, 6, 3
local STOPS = { 0, math.pi / 2, math.pi, -math.pi / 2 }
local t = 0

return {
    engineHandlers = {
        onUpdate = function(dt)
            t = t + dt
            if t < SETTLE then return end
            local k = math.floor((t - SETTLE) / PERIOD) % #STOPS + 1
            local yaw = self.rotation:getYaw() + STOPS[k]
            local out = util.vector3(math.sin(yaw), math.cos(yaw), 0)
            camera.setMode(camera.MODE.Static)
            camera.setStaticPosition(self.position + out * DIST + util.vector3(0, 0, HEIGHT))
            camera.setYaw(yaw + math.pi)
            camera.setPitch(PITCH)
        end,
    },
}

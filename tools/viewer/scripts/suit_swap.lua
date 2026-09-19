-- Debug camera plus suit swap, for the two-copies rule (CLAUDE.md, testing a
-- mesh, method 3): the real suit and its diagnostic copy photographed in one
-- run. zenar_viewer.lua's circle - front, side, back, other side, PERIOD
-- seconds each after SETTLE - with the suit changed on the same clock at the
-- start of every circle, so each stop is seen in both suits and no stop
-- straddles a change. A second round of circles is run with the character
-- running, sword drawn (CarriedRight is part of each suit). Used instead of zenar_viewer.omwscripts, never beside it.
-- Every item must be in the inventory already (AddItem in the --script-run card).
local camera = require('openmw.camera')
local I = require('openmw.interfaces')
local self = require('openmw.self')
local types = require('openmw.types')
local util = require('openmw.util')

local DIST, HEIGHT, PITCH, PERIOD, SETTLE = 190, 80, 0.12, 6, 3
local STOPS = { 0, math.pi / 2, math.pi, -math.pi / 2 }
local S = types.Actor.EQUIPMENT_SLOT
local function suit(prefix, cuirass, greaves, boots, arms)
    return { [S.Cuirass] = cuirass, [S.Greaves] = greaves, [S.Boots] = boots,
             [S.LeftPauldron] = prefix .. '_pauldron_left',
             [S.RightPauldron] = prefix .. '_pauldron_right',
             [S.LeftGauntlet] = prefix .. arms .. '_left',
             [S.RightGauntlet] = prefix .. arms .. '_right',
             [S.CarriedRight] = 'daedric longsword' }
end
-- Real suit, then its grid copy: Zenar on Daedric with its grid on glass,
-- Wolf on Dwemer with its grid on ebony. Only the suits whose cuirass the
-- --script-run card put in the inventory take part.
local ALL = {
    suit('daedric', 'daedric_cuirass', 'daedric_greaves', 'daedric_boots', '_gauntlet'),
    suit('glass', 'glass_cuirass', 'glass_greaves', 'glass_boots', '_bracer'),
    suit('dwemer', 'dwemer_cuirass', 'dwemer_greaves', 'dwemer_boots', '_bracer'),
    suit('ebony', 'ebony_cuirass', 'ebony_greaves', 'ebony_boots', '_bracer'),
}
local SUITS = nil

local t, worn, wornAt = 0, 0, 0

local function wear(k)
    -- setEquipment replaces the whole table: start from what is worn. Items
    -- go in as the inventory's own objects where there is one.
    local eq = types.Actor.getEquipment(self)
    local inv = types.Actor.inventory(self)
    for slot, id in pairs(SUITS[k]) do eq[slot] = inv:find(id) or id end
    types.Actor.setEquipment(self, eq)
    -- put the weapon away; onUpdate draws it again with the sword in hand.
    -- A stance set before the sword arrived stays hand-to-hand: fists, no
    -- blade, even with the sword listed as held (seen 2026-09-20).
    types.Actor.setStance(self, types.Actor.STANCE.Nothing)
    worn, wornAt = k, t
    local held = types.Actor.getEquipment(self)[S.CarriedRight]
    print('[suit_swap] suit ' .. k .. ', right hand: ' ..
          tostring(held and held.recordId) .. ', sword in inventory: ' ..
          tostring(inv:find('daedric longsword') ~= nil))
end

return {
    engineHandlers = {
        onUpdate = function(dt)
            t = t + dt
            if t < SETTLE then return end
            if not SUITS then
                local inv = types.Actor.inventory(self)
                SUITS = {}
                for _, st in ipairs(ALL) do
                    if inv:find(st[S.Cuirass]) then SUITS[#SUITS + 1] = st end
                end
                if #SUITS == 0 then SUITS = { ALL[1] } end
            end
            local step = math.floor((t - SETTLE) / PERIOD)
            local circle = math.floor(step / #STOPS)
            local suit = circle % #SUITS + 1
            if suit ~= worn then wear(suit) end
            -- every suit circled standing, then circled running backwards
            -- (ToddTest starts facing a wall; against the far one the run
            -- animation keeps playing), where rigid pieces used to part
            local running = math.floor(circle / #SUITS) % 2 == 1
            -- the built-in playercontrols.lua rewrites movement every frame
            -- from the keyboard unless told another script drives it
            I.Controls.overrideMovementControls(true)
            -- back and forth, 1.5 s each way: a straight run left ToddTest
            -- and the character died outside (2026-09-20)
            local way = math.floor(t / 1.5) % 2 == 0 and -1 or 1
            self.controls.movement = running and way or 0
            self.controls.run = running
            -- weapon out when one is carried: bent elbows and a closed grip,
            -- where Faig saw the elbow cylinders and the sword through the palm
            -- only after the new equipment has settled: drawn in the same
            -- frame the stance came up hand-to-hand, fists and no blade
            if t - wornAt > 1.5 and types.Actor.getEquipment(self)[S.CarriedRight]
                    and types.Actor.getStance(self) ~= types.Actor.STANCE.Weapon then
                types.Actor.setStance(self, types.Actor.STANCE.Weapon)
            end
            local yaw = self.rotation:getYaw() + STOPS[step % #STOPS + 1]
            local out = util.vector3(math.sin(yaw), math.cos(yaw), 0)
            camera.setMode(camera.MODE.Static)
            camera.setStaticPosition(self.position + out * DIST + util.vector3(0, 0, HEIGHT))
            camera.setYaw(yaw + math.pi)
            camera.setPitch(PITCH)
        end,
    },
}

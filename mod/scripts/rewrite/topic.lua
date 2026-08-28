-- Sci-fi conversion: make the word Zenar clickable.
--
-- Morrowind highlights a topic inside a line of dialogue only if the player
-- already knows it. Our rules put "Zenar" into 187 replies; without this the
-- word sits there as plain text and the reader has nowhere to go with it.
--
-- The topic itself and the answers under it are added by the plugin. Only
-- actors who know have a reply, so the topic appears in the list for them and
-- for nobody else - the dialogue system doing characterisation that would
-- otherwise need prose.
--
-- API verified in the shipped 0.51 stubs before use:
--   resources/lua_api/openmw/types.lua
--     "Adds a topic to the list of ones known by the player, so that it can be
--      used in dialogue with actors who can talk about that topic."
--     @function [parent=#PLAYER] addTopic, usage self.type.addTopic(self, "...")
-- This is why no script body is touched: vanilla adds topics with AddTopic
-- inside result scripts, which the rules freeze.

local self = require('openmw.self')

local TAG = '[REWRITE]'
local TOPIC = 'Zenar'

local done = false

local function runOnce()
    if done then return end
    done = true
    local ok, err = pcall(function()
        self.type.addTopic(self, TOPIC)
    end)
    if ok then
        print(TAG .. ' topic "' .. TOPIC .. '" added to the player')
    else
        print(TAG .. ' FAILED to add topic "' .. TOPIC .. '": ' .. tostring(err))
    end
end

return {
    engineHandlers = {
        onInit = function() pcall(runOnce) end,
        onLoad = function() pcall(runOnce) end,
        onUpdate = function() pcall(runOnce) end,
    },
}

-- Work Order 0 -- load context writability spike (Layer 2).
--
-- Reads the same four values back from a GLOBAL script -- a context with no
-- relationship to the load context that wrote them. This is the check that
-- matters: a write can be accepted locally and never reach the game data.
--
-- Read surfaces verified in resources/lua_api/openmw/types.lua and core.lua:
--   types.Armor.records[id].name        (types.lua: list<ArmorRecord> records)
--   types.Creature.records[id].name     (types.lua: list<CreatureRecord> records)
--   types.Book.records[id].text         (types.lua: list<BookRecord> records)
--   core.dialogue.topic.records[t].infos[i].text
--
-- This script stores nothing and implements no onSave handler, so it adds no
-- data to save games.

local types = require('openmw.types')
local core = require('openmw.core')

local TAG = '[WO0]'

local function log(...)
    local parts = {}
    for i = 1, select('#', ...) do
        parts[i] = tostring((select(i, ...)))
    end
    print(TAG .. ' ' .. table.concat(parts, ' '))
end

local function brief(v, n)
    if v == nil then return '<nil>' end
    local s = tostring(v)
    s = string.gsub(s, '[\r\n]', ' ')
    n = n or 70
    if #s > n then s = string.sub(s, 1, n) .. ' ...(' .. #s .. ' chars)' end
    return s
end

local function try(fn)
    local ok, res = pcall(fn)
    if ok then return true, res end
    return false, res
end

-- Try the literal id then its lowercase form, matching the load script.
local function readRecordField(store, id, field)
    local variants = { id, string.lower(id) }
    for _, variant in ipairs(variants) do
        local ok, val = try(function()
            local rec = store[variant]
            if rec == nil then return nil end
            return rec[field]
        end)
        if ok and val ~= nil then return true, val, variant end
    end
    return false, nil, nil
end

local function checkRecord(label, store, id, field, sentinel)
    log('')
    log('--- READBACK ' .. label .. ' ---')
    log('  record id :', id)
    log('  field     :', field)

    if store == nil then
        log('  RESULT    : NO_READ_SURFACE (store is nil)')
        return
    end

    local ok, value, usedId = readRecordField(store, id, field)
    if not ok then
        log('  RESULT    : READ_FAILED (record or field not readable)')
        return
    end
    log('  matched id:', usedId)
    log('  value     :', brief(value))
    if value == sentinel then
        log('  RESULT    : SENTINEL_PRESENT  readback_ok=true')
    else
        log('  RESULT    : ORIGINAL_VALUE    readback_ok=false')
    end
end

local INFO_TOPIC = 'little advice'
local INFO_ACTOR = 'arrille'

local function checkInfo(sentinel)
    log('')
    log('--- READBACK 4/4 INFO response text ---')
    log('  topic        :', INFO_TOPIC)
    log('  filterActorId:', INFO_ACTOR)

    local okTopic, topic = try(function()
        return core.dialogue.topic.records[INFO_TOPIC]
    end)
    if not okTopic or topic == nil then
        log('  RESULT    : NO_READ_SURFACE (topic not readable)')
        return
    end

    local okScan, found = try(function()
        for idx, info in ipairs(topic.infos) do
            if info.filterActorId ~= nil and
               string.lower(tostring(info.filterActorId)) == INFO_ACTOR then
                return { idx = idx, id = tostring(info.id), text = info.text }
            end
        end
        return nil
    end)
    if not okScan or found == nil then
        log('  RESULT    : READ_FAILED (no info filtered to ' .. INFO_ACTOR .. ')')
        return
    end

    log('  info index:', found.idx)
    log('  info id   :', found.id)
    log('  value     :', brief(found.text))
    if found.text == sentinel then
        log('  RESULT    : SENTINEL_PRESENT  readback_ok=true')
    else
        log('  RESULT    : ORIGINAL_VALUE    readback_ok=false')
    end
end

local done = false

local function runOnce()
    if done then return end
    done = true

    log('')
    log('##################################################')
    log('# WORK ORDER 0 -- Layer 2 readback               #')
    log('# Context: GLOBAL (not the load context)         #')
    log('##################################################')

    checkRecord('1/4 ARMO name', types.Armor and types.Armor.records,
                'newtscale_cuirass', 'name', 'SPIKE_ARMO_OK')
    checkRecord('2/4 CREA name', types.Creature and types.Creature.records,
                'mudcrab', 'name', 'SPIKE_CREA_OK')
    checkRecord('3/4 BOOK text', types.Book and types.Book.records,
                'bk_BriefHistoryEmpire1', 'text', 'SPIKE_BOOK_OK')
    checkInfo('SPIKE_INFO_OK')

    log('')
    log('=== Layer 2 complete. Compare against Layer 1 results above. ===')
end

return {
    engineHandlers = {
        -- onInit fires on a new game, onLoad on a loaded save; onUpdate is
        -- the backstop so the readback runs exactly once either way.
        onInit = function() pcall(runOnce) end,
        onLoad = function() pcall(runOnce) end,
        onUpdate = function() pcall(runOnce) end,
    },
}

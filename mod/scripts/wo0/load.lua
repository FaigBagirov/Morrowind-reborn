-- Work Order 0 -- load context writability spike (Layer 1).
--
-- Question this answers: which record fields are writable from the
-- OpenMW 0.51 Lua "load" context?
--
-- Every API call below was checked against, in order:
--   resources/lua_api/openmw/content.lua            (0.51 API stubs, shipped)
--   resources/vfs-mw/scripts/omw/esmfallbacks.lua   (engine's own LOAD script)
--   https://openmw.readthedocs.io/en/openmw-0.51.0/
-- Nothing here is invented. Every lookup is probed for existence before
-- use, and every access is wrapped in pcall, so a missing API surface is
-- reported as a result rather than throwing and aborting the other tests.

local content = require('openmw.content')

local TAG = '[WO0]'

local function log(...)
    local parts = {}
    for i = 1, select('#', ...) do
        parts[i] = tostring((select(i, ...)))
    end
    print(TAG .. ' ' .. table.concat(parts, ' '))
end

-- Collapse newlines and clip, so a whole book does not land in the log.
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

----------------------------------------------------------------------------
-- Enumeration: what does content actually expose at runtime?
-- This is the definitive answer, independent of docs and shipped stubs.
----------------------------------------------------------------------------

local function enumerate()
    log('')
    log('=== ENUMERATION: content sub-packages present at runtime ===')
    local ok, res = try(function()
        local keys = {}
        for k in pairs(content) do keys[#keys + 1] = tostring(k) end
        table.sort(keys)
        return keys
    end)
    if not ok then
        log('  pairs(content) failed:', tostring(res))
        return
    end
    log('  count:', #res)
    for _, k in ipairs(res) do
        local okr, recs = try(function() return content[k].records end)
        log('   -', k, (okr and recs ~= nil) and '(has .records)' or '(no .records)')
    end
end

----------------------------------------------------------------------------
-- Probing helpers
----------------------------------------------------------------------------

-- Find the first candidate sub-package name that exists and has .records.
local function findSub(candidates)
    for _, name in ipairs(candidates) do
        local ok, sub = try(function() return content[name] end)
        if ok and sub ~= nil then
            local ok2, recs = try(function() return sub.records end)
            if ok2 and recs ~= nil then return sub, name end
        end
    end
    return nil, nil
end

-- Record ids differ in case between the ESM and the engine store, so try
-- the literal id and its lowercase form before giving up.
local function findRecord(recs, id)
    local variants = { id, string.lower(id) }
    for _, variant in ipairs(variants) do
        local ok, rec = try(function() return recs[variant] end)
        if ok and rec ~= nil then return rec, variant end
    end
    return nil, nil
end

----------------------------------------------------------------------------
-- A single write attempt, fully reported.
----------------------------------------------------------------------------

local function attempt(label, candidates, recordId, field, sentinel)
    log('')
    log('=== ATTEMPT ' .. label .. ' ===')
    log('  record id :', recordId)
    log('  field     :', field)
    log('  sentinel  :', sentinel)

    local sub, subName = findSub(candidates)
    if sub == nil then
        log('  RESULT    : NO_API_SURFACE')
        log('  detail    : no content sub-package with .records among {' ..
            table.concat(candidates, ', ') .. '}')
        log('  write_ok=false readback_load=n/a')
        return
    end
    log('  surface   : content.' .. subName .. '.records')

    local rec, usedId = findRecord(sub.records, recordId)
    if rec == nil then
        log('  RESULT    : RECORD_NOT_FOUND')
        log('  write_ok=false readback_load=n/a')
        return
    end
    log('  matched id:', usedId)

    local okOld, oldValue = try(function() return rec[field] end)
    if okOld then
        log('  old value :', brief(oldValue))
    else
        log('  old value : <read failed: ' .. tostring(oldValue) .. '>')
    end

    local okWrite, werr = try(function() rec[field] = sentinel end)
    if not okWrite then
        log('  RESULT    : WRITE_THREW')
        log('  detail    :', tostring(werr))
        log('  write_ok=false readback_load=n/a')
        return
    end
    log('  write call: returned with no error')

    -- Re-fetch the record rather than reusing the handle, so a write that
    -- only mutated a local copy shows up as a mismatch here.
    local okBack, newValue = try(function()
        local r2 = findRecord(sub.records, recordId)
        if r2 == nil then return nil end
        return r2[field]
    end)

    if not okBack then
        log('  RESULT    : WRITE_OK_READBACK_THREW')
        log('  detail    :', tostring(newValue))
        log('  write_ok=true readback_load=false')
    elseif newValue == sentinel then
        log('  RESULT    : WRITE_OK')
        log('  write_ok=true readback_load=true')
    else
        log('  RESULT    : WRITE_SILENTLY_REVERTED')
        log('  now reads :', brief(newValue))
        log('  write_ok=true readback_load=false')
    end
end

----------------------------------------------------------------------------
-- Attempt 4 is special: 0.51 exposes no content sub-package for dialogue,
-- so the only surface that exists at all is openmw.core.dialogue, which the
-- docs describe as read-only. Attempting it is the point -- a documented
-- read-only surface that silently accepts writes would be the worst case.
----------------------------------------------------------------------------

local INFO_TOPIC = 'little advice'
local INFO_ACTOR = 'arrille'

local function attemptInfo(sentinel)
    log('')
    log('=== ATTEMPT 4/4 INFO response text ===')
    log('  topic        :', INFO_TOPIC)
    log('  filterActorId:', INFO_ACTOR)
    log('  sentinel     :', sentinel)

    local sub, subName = findSub({ 'dialogue', 'dialogues', 'topics', 'infos',
                                   'dialogueTopics', 'dialogs' })
    if sub ~= nil then
        log('  surface   : content.' .. subName .. ' (unexpected -- investigate)')
    else
        log('  surface   : no content sub-package for dialogue in this build')
    end

    local okCore, core = try(function() return require('openmw.core') end)
    if not okCore or core == nil then
        log('  RESULT    : NO_API_SURFACE (openmw.core unavailable in load context)')
        log('  write_ok=false readback_load=n/a')
        return
    end

    local okTopic, topic = try(function()
        return core.dialogue.topic.records[INFO_TOPIC]
    end)
    if not okTopic or topic == nil then
        log('  RESULT    : NO_API_SURFACE (core.dialogue.topic unreadable here)')
        log('  detail    :', tostring(topic))
        log('  write_ok=false readback_load=n/a')
        return
    end
    log('  surface   : core.dialogue.topic.records["' .. INFO_TOPIC .. '"].infos')

    -- Locate by actor filter rather than by info id, so a difference in id
    -- formatting between esmtool and the engine cannot cause a false miss.
    local okScan, found = try(function()
        for idx, info in ipairs(topic.infos) do
            if info.filterActorId ~= nil and
               string.lower(tostring(info.filterActorId)) == INFO_ACTOR then
                return { idx = idx, id = tostring(info.id), info = info }
            end
        end
        return nil
    end)
    if not okScan then
        log('  RESULT    : SCAN_THREW')
        log('  detail    :', tostring(found))
        log('  write_ok=false readback_load=n/a')
        return
    end
    if found == nil then
        log('  RESULT    : RECORD_NOT_FOUND (no info filtered to ' .. INFO_ACTOR .. ')')
        log('  write_ok=false readback_load=n/a')
        return
    end

    log('  info index:', found.idx)
    log('  info id   :', found.id)
    log('  old value :', brief(found.info.text))

    local okWrite, werr = try(function() found.info.text = sentinel end)
    if not okWrite then
        log('  RESULT    : WRITE_THREW  (expected: core.dialogue is read-only)')
        log('  detail    :', tostring(werr))
        log('  write_ok=false readback_load=n/a')
        return
    end
    log('  write call: returned with no error')

    local okBack, newValue = try(function()
        return core.dialogue.topic.records[INFO_TOPIC].infos[found.idx].text
    end)
    if not okBack then
        log('  RESULT    : WRITE_OK_READBACK_THREW')
        log('  detail    :', tostring(newValue))
        log('  write_ok=true readback_load=false')
    elseif newValue == sentinel then
        log('  RESULT    : WRITE_OK')
        log('  write_ok=true readback_load=true')
    else
        log('  RESULT    : WRITE_SILENTLY_REVERTED')
        log('  now reads :', brief(newValue))
        log('  write_ok=true readback_load=false')
    end
end

----------------------------------------------------------------------------

local function run()
    log('')
    log('##################################################')
    log('# WORK ORDER 0 -- load context writability spike #')
    log('# Layer 1: write attempts from the LOAD context  #')
    log('##################################################')

    enumerate()

    -- 1. ARMO name (FNAM). Target sits in Seyda Neen, Arrille's Tradehouse.
    attempt('1/4 ARMO name (FNAM)',
            { 'armors', 'armor', 'armours', 'armo' },
            'newtscale_cuirass', 'name', 'SPIKE_ARMO_OK')

    -- 2. CREA name (FNAM). Mudcrab is the only creature in the Seyda Neen
    --    exterior cell, so it is the most reachable creature target there.
    attempt('2/4 CREA name (FNAM)',
            { 'creatures', 'creature', 'crea' },
            'mudcrab', 'name', 'SPIKE_CREA_OK')

    -- 3. BOOK text. Target sits in Seyda Neen, Census and Excise Office --
    --    the room the game starts in.
    attempt('3/4 BOOK text',
            { 'books', 'book' },
            'bk_BriefHistoryEmpire1', 'text', 'SPIKE_BOOK_OK')

    -- 4. INFO response text, on a record filtered to a specific actor id.
    attemptInfo('SPIKE_INFO_OK')

    log('')
    log('=== Layer 1 complete. Layer 2 readback runs when a game starts. ===')
end

return {
    engineHandlers = {
        onContentFilesLoaded = function()
            local ok, err = pcall(run)
            if not ok then
                log('FATAL: spike aborted:', tostring(err))
            end
        end,
    },
}

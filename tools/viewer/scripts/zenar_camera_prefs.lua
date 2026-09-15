-- One-off: turn on the third-person camera options Faig uses in his play
-- profile, in whatever profile loads this. They live in the engine camera
-- script's own settings section and persist in the profile's player storage,
-- so one launch with this content file is enough.
local storage = require('openmw.storage')
local done = false

return {
    engineHandlers = {
        onUpdate = function()
            if done then return end
            done = true
            local section = storage.playerSection('SettingsOMWCameraThirdPerson')
            section:set('previewIfStandStill', true)
            section:set('deferredPreviewRotation', true)
            print('[zenar] camera: previewIfStandStill and deferredPreviewRotation on')
        end,
    },
}

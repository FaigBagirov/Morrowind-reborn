# UI Hook Reconnaissance Report

**Answer:** No.

## What was checked
There is no display-time hook, string intercept, or override for item names or tooltips exposed to Lua in OpenMW 0.51. The engine's built-in UI rendering for the crosshair, tooltips, and inventory is still handled entirely in C++ (MyGUI) and does not pass those strings through Lua before rendering.

I explicitly checked the following surfaces in `resources/lua_api` and `resources/vfs`:

1. **`openmw.ui` and `openmw.interfaces`**
   - The `openmw.ui` API provides primitives for building new custom widgets (`ui.create`, layers, `ui.showMessage`, text, flex, etc.), but exposes zero hooks for modifying existing engine UI windows (no `setTooltipFormatter`, no `onItemDisplay`).
   - `openmw.interfaces.MWUI` (`vfs/scripts/omw/mwui/`) provides layout templates (padding, borders, text, colors) used by the engine for building custom windows, but no interceptors for vanilla item names.

2. **Crosshair Targeting (`openmw/camera.lua` & `vfs/scripts/omw/camera`)**
   - Searched for any crosshair-related functions. `camera.showCrosshair(bool)` exists to toggle visibility (used in 3rd person and 360 movement), but there is no mechanism to read or override the target's name string shown over the crosshair.

3. **Inventory & Item Handlers (`openmw/core.lua`, `openmw/types.lua`, `vfs/scripts/omw/usehandlers.lua`)**
   - The `Inventory` type allows querying (`findAll`), counting, and moving items (`moveInto`), but it does not dictate how items are displayed.
   - `I.ItemUsage` handlers allow intercepting the *action* of using an item (equipping, consuming), but not the UI rendering of the item in the list.

The OpenMW 0.51 Lua API is simply not wired into the UI rendering pipeline deeply enough to rewrite entity strings on the fly. You cannot intercept the string; it must be modified at the record level.

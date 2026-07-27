# 1. OBJECTIVE

Implement Phase 2 of the StoryForge frontend roadmap: **Character Enhancement**. This phase adds three key features to the editor:

1. **Character Reference Image Upload** - Allow users to upload reference images to characters via the CharacterSheet panel
2. **Character Reference Regeneration** - Add a "Regenerate References" button that triggers AI regeneration of character visuals
3. **Character Assignment to Scenes** - Allow users to assign characters to scenes in the SceneStage editor

# 2. CONTEXT SUMMARY

### Current State
- **CharacterSheet.jsx**: Basic CRUD for characters (name, role, description, appearance, personality) with a simple reference image thumbnail display
- **SceneStage.jsx**: Scene editing with visual prompt, script, narration, mood, location - but no character assignment UI
- **dysentryClient.js**: Missing API functions for character ref regeneration and scene character updates

### Backend APIs Available
- `POST /pipeline/uploads/image` - Upload reference images (returns URL)
- `PUT /pipeline/characters/{id}` - Update character (accepts `ref_image_urls`)
- `POST /pipeline/characters/{id}/regenerate-refs` - Trigger character ref regeneration (returns job)
- `PUT /pipeline/scenes/{id}` - Update scene (accepts `character_ids`, `primary_character_ids`)

### Files to Modify
- `web/src/api/dysentryClient.js` - Add missing API functions
- `web/src/components/dysentry/editor/CharacterSheet.jsx` - Add upload UI and regenerate button
- `web/src/components/dysentry/editor/SceneStage.jsx` - Add character assignment panel
- `web/src/components/dysentry/editor/Editor.jsx` - Wire up new callbacks if needed

# 3. APPROACH OVERVIEW

**Step 1: API Client Functions**
Add two new functions to dysentryClient.js:
- `regenerateCharacterRefs(characterId)` - Calls the regeneration endpoint
- `updateSceneCharacters(sceneId, characterIds, primaryCharacterIds)` - Updates scene character associations

**Step 2: Character Reference Upload UI**
Enhance CharacterSheet to:
- Add an "Add Reference Image" button in edit mode
- Show upload progress and preview thumbnails
- Allow removing individual reference images
- Display reference images in a gallery grid in view mode

**Step 3: Regenerate References Button**
Add to CharacterSheet:
- "Regenerate References" button (shown when character has ref images)
- Loading state while regeneration is in progress
- Refresh character data after regeneration completes

**Step 4: Scene Character Assignment**
Enhance SceneStage to:
- Add a "Characters" section in the editing panel
- Display current characters with avatar thumbnails
- Add a character picker (checkboxes) to assign/unassign characters
- Visual indication of primary character

# 4. IMPLEMENTATION STEPS

### Step 1: Add API Functions
**Goal:** Enable frontend to call backend character regeneration and scene character update endpoints

**Method:** Add two new export functions to `web/src/api/dysentryClient.js`:
- `regenerateCharacterRefs(characterId)` - POST to `/pipeline/characters/{id}/regenerate-refs`
- `updateSceneCharacters(sceneId, characterIds, primaryCharacterIds)` - PUT to `/pipeline/scenes/{id}` with character fields

**Reference:** dysentryClient.js (end of file after line 490)

---

### Step 2: Upload UI in CharacterSheet
**Goal:** Allow users to upload and manage reference images for characters

**Method:** Modify `CharacterSheet.jsx`:
1. Add upload button with file input in edit mode
2. Handle file selection, POST to `/pipeline/uploads/image`
3. Add uploaded URL to `ref_image_urls` array
4. Save updated character via `onUpdateCharacter`
5. Show upload progress indicator
6. Add "remove" button on each reference thumbnail in edit mode
7. Display reference images as expandable gallery in view mode

**Reference:** CharacterSheet.jsx - inside edit form (around line 176) and character view (around line 252)

---

### Step 3: Regenerate References Button
**Goal:** Allow users to trigger AI regeneration of character reference images

**Method:** Modify `CharacterSheet.jsx`:
1. Add "Regenerate" button next to reference image section
2. On click, call `regenerateCharacterRefs(characterId)`
3. Show loading spinner while job is pending
4. Poll job status or refresh character data after completion
5. Update character in parent state with new `ref_image_urls`

**Reference:** CharacterSheet.jsx - add new state: `regeneratingRefs`

---

### Step 4: Character Assignment in SceneStage
**Goal:** Allow users to assign characters to scenes for continuity

**Method:** Modify `SceneStage.jsx`:
1. Add `characters` prop to component
2. Add "Characters" section after the type tabs
3. Show character avatars/chips for assigned characters
4. Add expand button to show character picker
5. Character picker: checkbox list of all story characters
6. Click to toggle character assignment
7. Mark first selected as "primary" character
8. Call `onUpdateCharacters(sceneId, characterIds, primaryCharacterIds)` callback
9. Pass new callback from Editor.jsx

**Reference:** SceneStage.jsx - new section after line 267 (after type tabs)

---

### Step 5: Wire Up Editor Callbacks
**Goal:** Connect SceneStage character assignment to the data layer

**Method:** Modify `Editor.jsx`:
1. Add `onUpdateSceneCharacters` handler that calls API
2. Pass `characters` array and handler down to SceneStage
3. Refresh scene data after character assignment update

**Reference:** Editor.jsx - pass new props to SceneStage

# 5. TESTING AND VALIDATION

### Manual Testing Checklist
1. **Character Upload**
   - [ ] Open CharacterSheet, click edit on a character
   - [ ] Click "Add Reference Image" button
   - [ ] Select an image file, verify upload progress shows
   - [ ] Verify image appears as thumbnail after upload
   - [ ] Add multiple images, verify gallery displays correctly
   - [ ] Click remove on an image, verify it disappears after save

2. **Character Regeneration**
   - [ ] Click "Regenerate References" on a character with existing refs
   - [ ] Verify button shows loading state
   - [ ] After completion, verify new images appear (or job status updates)

3. **Character Assignment**
   - [ ] Select a scene in the editor
   - [ ] Find "Characters" section, click to expand
   - [ ] Check/uncheck characters, verify scene updates
   - [ ] Reload page, verify character assignments persist
   - [ ] Set one character as primary, verify it appears first

### Success Criteria
- Upload completes within 10 seconds for standard images
- Regeneration job triggers correctly and updates UI on completion
- Character assignments persist across page reloads
- No console errors during any Phase 2 operations
- UI remains responsive during async operations (loading states shown)

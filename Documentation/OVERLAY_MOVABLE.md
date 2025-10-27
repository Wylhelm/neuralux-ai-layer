# Movable Overlay Window ✅

## What's New

The overlay window can now be **dragged and repositioned** anywhere on your screen!

## How to Use

### Move the Window

1. **Hover over the title bar** at the top of the overlay
   - You'll see: `≡ Neuralux ≡`
   - Cursor changes to a "grab" hand

2. **Click and drag** the title bar
   - Click and hold left mouse button
   - Move mouse to reposition window
   - Release to drop in new location

3. **Position anywhere**
   - Move to any corner
   - Keep visible while working
   - Reposition as needed

## Visual Changes

```
┌─────────────────────────────────────────────────────────┐
│           ≡ Neuralux ≡  ← Drag here to move             │
├─────────────────────────────────────────────────────────┤
│  [🎤] [🔇] [🆕] [🕘] [🔲] [↻] [🎨]                      │
│  ┌─────────────────────────────────────────────────┐   │
│  │ Type a command or question...                   │   │
│  └─────────────────────────────────────────────────┘   │
│                                                         │
│  [Results Area]                                         │
│                                                         │
│  Status: Ready                                          │
└─────────────────────────────────────────────────────────┘
```

## Features

✅ **Drag Handle** - Clear visual indicator at top  
✅ **Cursor Feedback** - Changes to grab cursor on hover  
✅ **Smooth Movement** - Follows mouse precisely  
✅ **X11 Compatible** - Works on X11 window systems  
✅ **No Accidental Moves** - Only drags from title bar  
✅ **Position Memory** - Stays where you put it  

## Use Cases

### 1. Multi-Monitor Setup
```
Move overlay to:
- Secondary monitor
- Corner of main screen
- Between applications
```

### 2. Screen Recording
```
Position overlay:
- Out of recording area
- In corner for demos
- Beside content being shown
```

### 3. Split Screen Work
```
Place overlay:
- Side by side with browser
- Next to code editor
- Beside terminal
```

### 4. Gaming/Streaming
```
Move overlay to:
- Edge of screen
- Secondary monitor
- Between game and chat
```

## Technical Details

### Implementation
- **Drag Gesture**: GTK4 GestureDrag controller
- **Window Movement**: X11 window configuration
- **Cursor Change**: Motion controller for hover feedback
- **Title Bar**: 30px drag handle at top

### X11 Support
- Uses Xlib for direct window positioning
- Captures window geometry on drag start
- Applies offset during drag motion
- Flushes X11 display for immediate feedback

### Future Support
- Wayland support (via layer-shell positioning)
- Remember last position between sessions
- Snap to edges/corners
- Multi-monitor awareness

## Keyboard Alternative

While dragging is the primary method, you can also:
- Close and reopen overlay (centers automatically)
- Use hotkey (`Alt+Space`) to show/hide

## Tips

1. **Drag from title bar only** - Dragging from other areas won't work
2. **Cursor indicates draggable area** - Look for grab cursor
3. **Smooth movements** - X11 provides fluid repositioning
4. **No decorations** - Title bar is custom, not OS-provided

## Styling

The drag handle has custom styling:
- **Color**: Light blue (`#89b4fa`)
- **Opacity**: 70% (subtle but visible)
- **Font**: 14px
- **Symbol**: ≡ (hamburger menu icon)
- **Hover**: Cursor changes to "grab"

## Troubleshooting

### Window won't move
- Ensure you're dragging from the `≡ Neuralux ≡` area
- Check you're on X11 (not Wayland)
- Try closing and reopening overlay

### Jerky movement
- This is normal on some X11 configurations
- Movement is still functional
- Consider lighter desktop effects

### Can't find window
- Press `Alt+Space` to reopen centered
- Window always appears in center when opened

## Related Features

Works seamlessly with:
- ✅ Image generation
- ✅ Voice input
- ✅ OCR capture
- ✅ Settings dialog
- ✅ All overlay functions

## Summary

**Before**: Overlay appeared in fixed position  
**After**: Drag anywhere you want!

**To move**: 
1. Hover over `≡ Neuralux ≡`
2. Click and drag
3. Release to position

Enjoy your freely positionable AI assistant! 🎯


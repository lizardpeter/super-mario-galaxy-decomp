# Branding

- `star.png`: the program's icon picture (white background).
- `star.ico`: the icon the Windows build embeds (file, window and taskbar), made from it:
  `python3 tools/icon/make_icon.py branding/star.png branding/star.ico --white-to-alpha`. Make it again when the
  picture changes.
- Discord: the status shows under the application `1575795687273013248` (Super Mario Galaxy), over the Discord app's
  local pipe (`port/runtime/src/discord_presence.cpp`); no SDK, nothing over the network from the game.

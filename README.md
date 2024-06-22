> [!NOTE]
>
> WinToucher is still under development. The current version is a prototype and may contain bugs.

<img src="assets/WinToucher.svg" width="150" align="right">

# WinToucher
Powered by Win32 API and tkinter, WinToucher is a Python application that allows you to simulate touch events on Windows through keyboard input. It is useful for testing touch-based applications on Windows without a physical touch screen.

![](./assets/Preview.png)

## Features
- 📝 Mark touch points on the screen (when the overlay is shown)
  - **Click blank space** to create a new touch point
  - **Double click touch point** to check its detail
  - **Drag touch point** to move it
  - **Right click touch point** to unset its key binding or delete it (if it is not bound to any key)
- 👇 Support actions of pressing and flicking
  - **Press**: Tap the touch point once
  - **Flick**: Drag the touch point to a certain direction and distance
- 📃 Save and load touch points (dots) in JSON format
- 👂 Global, togglable keyboard listener
- 👻 Hide window to the system tray

## Usage
This tool is managed using [Poetry](https://python-poetry.org/).

To install the dependencies, run:
```bash
poetry install
```

After that, you can run the application with:
```bash
poetry run wintoucher
```

## To-do
- [x] Further modularize the code and decouple current `__main__.py`
- [x] Fix bugs with touch simulation when calling `InjectTouchInput` in some certain cases
- [ ] Improve overlay GUI
- [ ] Try to build with `nuitka`

## License
[MIT](./LICENSE)
# Second Life XUI Designer

> ⚠️ **Note:** This project is currently in active development. Features, UI, and functionality are subject to change.

**Second Life XUI Designer** is a desktop visual layout editor and WYSIWYG Integrated Development Environment (IDE) built with Python and PySide6. It is engineered specifically for creating, inspecting, modifying, and previewing Second Life XML User Interface (XUI) layout files. 

By bridging the gap between raw XML coding and in-viewer testing, the designer renders authentic viewer skins using 9-slice texture scaling and implements an algebraic layout solver to accurately handle Second Life's relative coordinate system.

---

![XUIDesigner](screenshots/screenshot0.png)

---

## ⚙️ Prerequisites & Setup

**Crucial Note on Textures:** To render the UI correctly, this application relies on the actual graphic assets used by the Second Life viewer. Because these textures are not bundled with this repository, **you must have a local copy of the Second Life viewer source code**.

1. Download or clone the Second Life viewer source code from Linden Lab.
2. Locate the default skin textures directory (typically found at `indra/newview/skins/default/textures`).
3. Set your texture path in the application (via the `File -> Set Viewer Texture Folder...` menu or by updating the default path in `textures.py`) so the designer can load the necessary `.png`, `.tga`, and `.j2c` files.

---

## 🌟 Key Features

### 🎨 WYSIWYG Interactive Canvas
* **10px Snapping Grid & Rulers:** The visual canvas features a background grid that automatically snaps widget positions to 10-pixel increments. Built-in top and left rulers display coordinate tick marks and pixel measurements for precise alignment.
* **Direct Manipulation:** Supports interactive on-canvas drag-and-drop widget placement, moving, and resizing. Selected elements display visual bounding outlines, directional resize handles, and an instant-delete handle.
* **Smart Drop Redirection:** Dragging new child widgets onto a `tab_container` automatically routes and embeds them directly into the active tab panel. If no tab panel exists, the engine automatically generates a default panel to hold the dropped widget.

### 🖥️ Three-Pane Workspace
* **Left Pane (Widget Palette):** A categorized drag-and-drop tree palette featuring standard Second Life elements. Categories include **Containers & Windows** (`floater`, `panel`, `tab_container`, `accordion`), **Buttons & Toggles**, **Text & Editors** (`line_editor`, `search_editor`), **Selection Controls** (`slider`, `spinner`, `combo_box`), and **Display Indicators** (`progress_bar`, `icon`).
* **Center Pane (Canvas & Live XML Source):** A split workspace combining the visual canvas with a real-time Second Life XML source code editor. The XML code view generates standalone, pretty-printed XUI XML that updates instantaneously as you manipulate graphical elements.
* **Right Pane (DOM Hierarchy & Property Inspector):** Contains a synchronized DOM tree that allows bidirectional selection and drag-and-drop parent-child reordering. Below it, a dynamic Property Inspector automatically generates form controls tailored to the selected widget's schema.

### 🖼️ Authentic Viewer Skin Rendering
* **Local Viewer Texture Integration:** Includes a texture manager that loads original Second Life viewer assets (supporting PNG, TGA, and J2C formats via Pillow) directly from your local viewer skin folder.
* **Scale-9 Grid (9-Slice) Scaling:** Implements custom 9-slice texture drawing to ensure that rounded corners, window borders, button bevels, and tab headers scale cleanly without pixel distortion.
* **Visual State Rendering:** Accurately renders specialized UI states, such as active versus inactive tab headers, checked versus unchecked boxes, and styled floating headers (`LLFloater`).

### 🧮 Robust XML Import & Algebraic Solving
* **Opposing Anchor Math:** Features an XML importer that resolves Second Life's relative layout geometry. It evaluates simultaneous opposing anchors (such as defining both `left` and `right` or `top` and `bottom` coordinates) to dynamically deduce true element widths, heights, and negative container offsets.
* **Sibling Delta Calculation:** Supports sequential layout offsets including `left_delta`, `top_delta`, `left_pad`, and `top_pad` relative to preceding sibling elements.
* **Clean Compilation:** The compiler cleans out empty attributes and formats output with standardized 2-space indentation and UTF-8 encoding.

### 📋 Comprehensive SL Schema Registry
* **C++ Class Mapping:** Built upon an underlying parameter registry that maps visual controls directly to their Second Life C++ UI counterparts (e.g., `LLView`, `LLUICtrl`, `LLFloater`, `LLButton`, `LLTabContainer`, `LLPanel`).
* **Grouped Attribute Editing:** The inspector organizes properties into logical collapsible sections based on class inheritance.
* **Deep Parameter Support:** Allows editing of universal layout behaviors (`follows`, `layout`), data bindings (`value`, `control_name`, `enabled_controls`), typography (`font`, `halign`), and viewer event callbacks (`commit_callback`, `mouseenter_callback`).

---

## 🛠️ Technology Stack

| Component | Technology / Library | Usage in Codebase |
| :--- | :--- | :--- |
| **Core Language** | Python 3 | Application logic and algebraic coordinate solvers. |
| **GUI Framework** | PySide6 (Qt for Python) | Window management, custom `QGraphicsView` canvas, tree widgets, and Fusion UI styling. |
| **Image Processing** | Pillow (PIL) | Reading and converting viewer texture files (TGA, J2C, PNG) into Qt pixmaps. |
| **XML Parsing & DOM** | `xml.etree.ElementTree` & `minidom` | Parsing incoming layout files and generating clean, formatted XML output. |
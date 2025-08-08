# PrintImage
![PrintImage](https://i.imgur.com/tIKRSAx.png)

PrintImage is a desktop application developed using PySide6 (the official Qt for Python bindings). It is designed to simplify and enhance the process of printing images, providing users with a convenient graphical interface and flexible options for customizing print layouts.

## Features

- **Load Multiple Images from the Command Line:**  
  Users can specify several image files to be loaded when starting the application via the command line. This is useful for batch printing or quickly accessing a selection of photos.

- **Flexible Print Layouts:**  
  PrintImage offers various preset print layouts, such as full-page printing, 13x18 cm, and 20x25 cm formats. This allows users to choose the layout that best fits their needs, whether for standard photo sizes or custom arrangements.

- **Image Preview Before Printing:**  
  Before sending images to the printer, users can preview how each image will look with the selected layout and settings. This helps prevent mistakes and ensures that the output matches expectations.

- **Specify Number of Copies:**  
  For each image, users can indicate how many copies they wish to print, streamlining the process for events, photo distributions, or multiple prints.

- **Fit to Frame or Maintain Aspect Ratio:**  
  PrintImage gives users the option either to scale images to fit the selected print frame or to preserve their original aspect ratio, depending on their preference for cropping or scaling.

- **Direct Printing Capability:**  
  Once all settings are chosen, users can print images directly from the application without needing to export or use other software.

## Technical Requirements

- Python 3.x
- PySide6
- A compatible printer

## Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/Merdekasoft/printimg.git
   cd printimg
   ```
2. Ensure Python 3.x and PySide6 are installed on your system.
3. Run the application according to usage instructions provided in the repository.

## Purpose and Benefit

PrintImage is particularly useful for photographers, event organizers, and anyone who regularly needs to print images in various formats. The use of PySide6 ensures cross-platform compatibility and a modern, responsive user interface. The application combines batch processing, layout flexibility, and direct hardware interaction, streamlining the photo printing workflow.

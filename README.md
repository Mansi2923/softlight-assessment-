# Figma to HTML/CSS Converter

A Python-based tool that converts Figma design files into static HTML/CSS representations using the Figma REST API.

## Overview

This converter takes a Figma file as input and generates a standalone HTML file with embedded CSS that visually replicates the Figma design. It handles layout, typography, colors, borders, gradients, and positioning to create a pixel-accurate representation.

## Features

- Complete layout conversion (absolute positioning and flexbox)
- Accurate typography (fonts, sizes, weights, spacing)
- Color accuracy (RGBA conversion)
- Gradient support (linear gradients)
- Border styling (colors, weights, corner radii)
- Auto-layout frame support
- Opacity handling
- Google Fonts integration
- Image export and embedding

## Setup

### Prerequisites

- Python 3.7+
- Figma account with API access
- Access to the target Figma file

### Installation

1. Clone this repository
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Create a `.env` file:
   ```env
   FIGMA_TOKEN=your_figma_api_token
   FIGMA_KEY=your_figma_file_key
   ```

### Getting Credentials

1. **Figma API Token**: 
   - Go to Figma → Settings → Account
   - Scroll to "Personal access tokens"
   - Generate a new token

2. **File Key**:
   - Open your Figma file
   - Extract from the URL: `https://www.figma.com/file/[FILE_KEY]/...`
   - Or use the format: Copy the file to your workspace and get the key from the URL

## Usage

```bash
python main.py
```

The generated HTML file will be saved to `output/index.html`.

## Output

The converter generates:
- `output/index.html` - Standalone HTML file with embedded CSS
- `output/assets/` - Directory containing exported images (if any)

## How It Works

1. **Fetch**: Retrieves Figma file data via REST API
2. **Parse**: Traverses the node tree structure
3. **Convert**: Transforms Figma properties to CSS:
   - Colors → rgba()
   - Typography → font properties
   - Layout → absolute/flexbox positioning
   - Effects → box-shadow, borders
4. **Generate**: Creates semantic HTML with embedded styles

## Known Limitations

### Layout
- Complex nested auto-layout with varying child sizes may not render perfectly
- Constraints and responsive behavior are not fully translated
- Overlapping elements may have z-index issues

### Visual
- Blur effects are approximated, not exactly replicated
- Some advanced effects (glows, layer blurs) may not render
- Vector shapes are exported as images, not SVG paths
- Image fills require API access and network calls

### Typography
- Text with complex character formatting may simplify
- Text auto-resize behavior may differ slightly
- Nested text styles with overrides may not render identically

### Technical
- Requires active Figma API connection
- May need multiple API calls for complex files
- Generated class names are sanitized and may not be semantic
- Output HTML is not minified

### Components
- Component instances are rendered but not interactive
- Variant properties are not fully resolved
- Component overrides may not translate perfectly

## File Structure

```
.
├── main.py              # Main converter logic
├── requirements.txt      # Python dependencies
├── .env                 # Environment variables (not in repo)
├── README.md            # This file
└── output/              # Generated files
    ├── index.html       # Output HTML/CSS
    └── assets/          # Exported images
```

## Example

Converting the provided Figma file results in a mobile sign-in screen with:
- Rounded container (32px radius)
- Styled input fields
- Gradient buttons
- Proper typography and spacing
- Dark background with centered content

## Testing

1. Ensure `.env` file is configured
2. Run `python main.py`
3. Open `output/index.html` in a browser
4. Compare with the original Figma design

## Dependencies

- `requests` - HTTP client for Figma API
- `python-dotenv` - Environment variable management

## License

MIT License

## Submission

This project was created as part of the Softlight Engineering Take-Home Assignment.

<small>yes this README was created using AI for better time management.</small>

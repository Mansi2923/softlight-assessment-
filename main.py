import requests
import json
import os
import re
import math
from typing import Dict, List, Tuple
from dotenv import load_dotenv

load_dotenv()


class FigmaConverter:
    def __init__(self, api_key: str, file_key: str):
        self.api_key = api_key
        self.file_key = file_key
        self.base_url = "https://api.figma.com/v1"
        self.headers = {"X-Figma-Token": api_key}
        self.images = {}
        self.fonts_used = set()
        self.root_frame = None
        
    def fetch_file(self) -> Dict:
        url = f"{self.base_url}/files/{self.file_key}"
        response = requests.get(url, headers=self.headers)
        response.raise_for_status()
        return response.json()
    
    def fetch_images(self, node_ids: List[str]) -> Dict:
        if not node_ids:
            return {}
        
        ids_str = ",".join(node_ids)
        url = f"{self.base_url}/images/{self.file_key}?ids={ids_str}&format=png&scale=2"
        response = requests.get(url, headers=self.headers)
        response.raise_for_status()
        return response.json().get("images", {})
    
    def download_image(self, url: str, filename: str, output_dir: str):
        response = requests.get(url)
        response.raise_for_status()
        
        os.makedirs(output_dir, exist_ok=True)
        filepath = os.path.join(output_dir, filename)
        
        with open(filepath, 'wb') as f:
            f.write(response.content)
        
        return filename
    
    def color_to_css(self, color: Dict) -> str:
        if not color or not isinstance(color, dict):
            return 'transparent'
        
        r = max(0, min(255, int(color.get('r', 0) * 255)))
        g = max(0, min(255, int(color.get('g', 0) * 255)))
        b = max(0, min(255, int(color.get('b', 0) * 255)))
        a = max(0, min(1, color.get('a', 1)))
        
        return f"rgba({r}, {g}, {b}, {a})"
    
    def get_fills(self, node: Dict) -> str:
        fills = node.get('fills', [])
        if not fills or not fills[0].get('visible', True):
            return 'transparent'
        
        fill = fills[0]
        if fill['type'] == 'SOLID':
            return self.color_to_css(fill['color'])
        
        if fill['type'] == 'GRADIENT_LINEAR':
            stops = fill.get('gradientStops', [])
            if len(stops) < 2:
                return 'transparent'
            
            handles = fill.get('gradientHandlePositions', [])
            if len(handles) >= 2:
                x1, y1 = handles[0]['x'], handles[0]['y']
                x2, y2 = handles[1]['x'], handles[1]['y']
                angle_rad = math.atan2(y2 - y1, x2 - x1)
                css_angle = (90 - math.degrees(angle_rad)) % 360
            else:
                css_angle = 180
            
            gradient_stops = ', '.join([
                f"{self.color_to_css(stop['color'])} {stop['position']*100}%"
                for stop in stops
            ])
            return f"linear-gradient({css_angle}deg, {gradient_stops})"
        
        return 'transparent'
    
    def get_strokes(self, node: Dict) -> Tuple:
        strokes = node.get('strokes', [])
        if not strokes or not strokes[0].get('visible', True):
            return None, 0
        
        color = self.color_to_css(strokes[0]['color'])
        weight = node.get('strokeWeight', 1)
        return color, weight
    
    def get_effects(self, node: Dict) -> List[str]:
        effects = node.get('effects', [])
        css_effects = []
        
        for effect in effects:
            if not effect.get('visible', True):
                continue
                
            if effect['type'] == 'DROP_SHADOW':
                offset = effect.get('offset', {'x': 0, 'y': 0})
                radius = effect.get('radius', 0)
                spread = effect.get('spread', 0)
                color = self.color_to_css(effect.get('color', {'r': 0, 'g': 0, 'b': 0, 'a': 0.25}))
                css_effects.append(f"{offset['x']}px {offset['y']}px {radius}px {spread}px {color}")
            elif effect['type'] == 'INNER_SHADOW':
                offset = effect.get('offset', {'x': 0, 'y': 0})
                radius = effect.get('radius', 0)
                color = self.color_to_css(effect.get('color', {'r': 0, 'g': 0, 'b': 0, 'a': 0.25}))
                css_effects.append(f"inset {offset['x']}px {offset['y']}px {radius}px {color}")
        
        return css_effects
    
    def get_typography(self, node: Dict) -> Dict[str, str]:
        style = node.get('style', {})
        css = {}
        
        if 'fontFamily' in style:
            font = style['fontFamily']
            self.fonts_used.add(font)
            css['font-family'] = f"'{font}', sans-serif"
        
        if 'fontSize' in style:
            css['font-size'] = f"{style['fontSize']}px"
        
        if 'fontWeight' in style:
            css['font-weight'] = str(style['fontWeight'])
        
        if 'lineHeightPx' in style:
            css['line-height'] = f"{style['lineHeightPx']}px"
        elif 'lineHeightPercentFontSize' in style:
            css['line-height'] = f"{style['lineHeightPercentFontSize']}%"
        
        if 'letterSpacing' in style:
            css['letter-spacing'] = f"{style['letterSpacing']}px"
        
        if 'textAlignHorizontal' in style:
            align_map = {'LEFT': 'left', 'CENTER': 'center', 'RIGHT': 'right', 'JUSTIFIED': 'justify'}
            css['text-align'] = align_map.get(style['textAlignHorizontal'], 'left')
        
        if 'textDecoration' in style and style['textDecoration'] == 'UNDERLINE':
            css['text-decoration'] = 'underline'
        
        return css
    
    def sanitize_class_name(self, name: str, node_id: str = '') -> str:
        if not name:
            name = 'unnamed'
        
        name = re.sub(r'[^a-zA-Z0-9_-]', '-', name)
        name = re.sub(r'-+', '-', name).lower().strip('-')
        
        if name and not name[0].isalpha():
            name = 'n-' + name
        
        if node_id:
            sanitized_id = re.sub(r'[^a-zA-Z0-9_-]', '', node_id[:6])
            name = f"{name}-{sanitized_id}"
        
        return name if name else 'unnamed'
    
    def node_to_css(self, node: Dict, class_name: str, is_root: bool = False, 
                    parent_has_layout: bool = False) -> Dict[str, str]:
        css = {}
        bounds = node.get('absoluteBoundingBox', {})
        layout_mode = node.get('layoutMode')
        
        if is_root:
            if 'width' in bounds:
                css['width'] = f"{bounds['width']}px"
            if 'height' in bounds:
                css['height'] = f"{bounds['height']}px"
            css['position'] = 'relative'
            css['margin'] = '0 auto'
            self.root_frame = bounds
        else:
            if not parent_has_layout and self.root_frame and 'x' in bounds and 'y' in bounds:
                rel_x = bounds['x'] - self.root_frame['x']
                rel_y = bounds['y'] - self.root_frame['y']
                css['position'] = 'absolute'
                css['left'] = f"{rel_x}px"
                css['top'] = f"{rel_y}px"
            
            if layout_mode:
                css['display'] = 'flex'
                css['flex-direction'] = 'row' if layout_mode == 'HORIZONTAL' else 'column'
                
                if node.get('counterAxisAlignItems') == 'CENTER':
                    css['align-items'] = 'center'
                if node.get('primaryAxisAlignItems') == 'CENTER':
                    css['justify-content'] = 'center'
                
                padding_props = ['paddingLeft', 'paddingRight', 'paddingTop', 'paddingBottom']
                for prop in padding_props:
                    if prop in node:
                        css_prop = prop[:7].lower() + '-' + prop[7:].lower()
                        css[css_prop] = f"{node[prop]}px"
                
                if 'itemSpacing' in node and node['itemSpacing'] > 0:
                    css['gap'] = f"{node['itemSpacing']}px"
            
            if 'width' in bounds:
                css['width'] = f"{bounds['width']}px"
            if 'height' in bounds:
                css['height'] = f"{bounds['height']}px"
        
        if 'rotation' in node and node['rotation'] != 0:
            css['transform'] = f"rotate({math.degrees(node['rotation'])}deg)"
        
        if node.get('type') != 'TEXT':
            background = self.get_fills(node)
            if background != 'transparent':
                css['background'] = background
        
        stroke_color, stroke_weight = self.get_strokes(node)
        if stroke_color:
            css['border'] = f"{stroke_weight}px solid {stroke_color}"
        
        if 'cornerRadius' in node:
            css['border-radius'] = f"{node['cornerRadius']}px"
        elif 'rectangleCornerRadii' in node:
            radii = node['rectangleCornerRadii']
            css['border-radius'] = f"{radii[0]}px {radii[1]}px {radii[2]}px {radii[3]}px"
        
        effects = self.get_effects(node)
        if effects:
            css['box-shadow'] = ', '.join(effects)
        
        if 'opacity' in node and node['opacity'] < 1:
            css['opacity'] = str(node['opacity'])
        
        if node.get('clipsContent'):
            css['overflow'] = 'hidden'
        
        return css
    
    def traverse_node(self, node: Dict, depth: int = 0, is_root: bool = False, 
                     parent_has_layout: bool = False) -> Tuple[str, Dict]:
        node_type = node.get('type')
        node_name = node.get('name', 'unnamed')
        node_id = node.get('id', 'no-id')
        class_name = self.sanitize_class_name(node_name, node_id)
        
        if not node.get('visible', True):
            return '', {}
        
        html_parts = []
        css_rules = {}
        current_has_layout = bool(node.get('layoutMode'))
        
        if node_type == 'TEXT':
            content = node.get('characters', '').replace('<', '&lt;').replace('>', '&gt;')
            css = self.node_to_css(node, class_name, is_root, parent_has_layout)
            css.update(self.get_typography(node))
            
            fills = node.get('fills', [])
            if fills and fills[0].get('visible', True):
                css['color'] = self.color_to_css(fills[0]['color'])
                if 'opacity' in fills[0]:
                    css['opacity'] = str(fills[0]['opacity'])
            
            if 'background' in css and css['background'] == css.get('color'):
                del css['background']
            
            html_parts.append(f'<div class="{class_name}">{content}</div>')
            css_rules[class_name] = css
        
        elif node_type in ['RECTANGLE', 'ELLIPSE', 'FRAME', 'GROUP', 'COMPONENT', 'INSTANCE']:
            css = self.node_to_css(node, class_name, is_root, parent_has_layout)
            
            if node_type == 'ELLIPSE':
                css['border-radius'] = '50%'
            
            fills = node.get('fills', [])
            has_image = any(f.get('type') == 'IMAGE' for f in fills if f.get('visible', True))
            
            if has_image:
                self.images[node['id']] = class_name
                css['background-size'] = 'cover'
                css['background-position'] = 'center'
            
            children = node.get('children', [])
            bounds = node.get('absoluteBoundingBox', {})
            is_leaf = not children and bounds.get('height', 0) < 50
            
            if is_leaf:
                html_parts.append(f'<div class="{class_name}"></div>')
                css_rules[class_name] = css
            else:
                children_html = []
                for child in children:
                    child_html, child_css = self.traverse_node(
                        child, depth + 1, False, current_has_layout
                    )
                    if child_html:
                        children_html.append(child_html)
                    css_rules.update(child_css)
                
                inner_html = '\n    '.join(children_html) if children_html else ''
                html_parts.append(f'<div class="{class_name}">\n    {inner_html}\n  </div>')
                css_rules[class_name] = css
        
        elif node_type == 'VECTOR':
            css = self.node_to_css(node, class_name, is_root, parent_has_layout)
            self.images[node['id']] = class_name
            css['background-size'] = 'contain'
            css['background-repeat'] = 'no-repeat'
            css['background-position'] = 'center'
            
            html_parts.append(f'<div class="{class_name}"></div>')
            css_rules[class_name] = css
        
        elif node_type == 'CANVAS':
            for child in node.get('children', []):
                if child.get('type') == 'FRAME' and child.get('visible', True):
                    return self.traverse_node(child, depth, True, False)
        
        elif node_type == 'DOCUMENT':
            for child in node.get('children', []):
                child_html, child_css = self.traverse_node(child, depth, False, False)
                if child_html:
                    html_parts.append(child_html)
                css_rules.update(child_css)
        
        return '\n  '.join(html_parts), css_rules
    
    def generate_css(self, css_rules: Dict, canvas_bg: str = None) -> str:
        bg_color = canvas_bg if canvas_bg else '#1E1E1E'
        primary_font = 'Inter, sans-serif' if 'Inter' in self.fonts_used else 'system-ui, sans-serif'
        
        css_output = [
            '* { box-sizing: border-box; margin: 0; padding: 0; }',
            'body {',
            '  margin: 0;',
            '  padding: 20px;',
            f'  background: {bg_color};',
            f'  font-family: {primary_font};',
            '  display: flex;',
            '  justify-content: center;',
            '  align-items: center;',
            '  min-height: 100vh;',
            '}'
        ]
        
        for class_name, properties in css_rules.items():
            if not properties or not class_name:
                continue
            
            valid_props = {k: v for k, v in properties.items() if v and k}
            if valid_props:
                props = ';\n  '.join(f"{k}: {v}" for k, v in valid_props.items())
                css_output.append(f"\n.{class_name} {{\n  {props};\n}}")
        
        return '\n'.join(css_output)
    
    def generate_google_fonts_link(self) -> str:
        if not self.fonts_used:
            return ""
        
        weights = "300,400,500,600,700"
        fonts_param = "&".join(
            f"family={f.replace(' ', '+')}:wght@{weights}" for f in self.fonts_used
        )
        return f'<link href="https://fonts.googleapis.com/css2?{fonts_param}&display=swap" rel="stylesheet">'
    
    def convert(self, output_dir: str = "output"):
        try:
            print("Fetching Figma file...")
            figma_data = self.fetch_file()
            
            print("Parsing nodes...")
            document = figma_data['document']
            
            canvas_bg = None
            if 'children' in document and document['children']:
                canvas = document['children'][0]
                if 'backgroundColor' in canvas:
                    canvas_bg = self.color_to_css(canvas['backgroundColor'])
            
            html_body, css_rules = self.traverse_node(document)
            
            if self.images:
                print(f"Downloading {len(self.images)} images...")
                image_urls = self.fetch_images(list(self.images.keys()))
                images_dir = os.path.join(output_dir, 'assets')
                
                for node_id, class_name in self.images.items():
                    if node_id in image_urls and image_urls[node_id]:
                        try:
                            url = image_urls[node_id]
                            filename = f"{class_name}.png"
                            self.download_image(url, filename, images_dir)
                            
                            if class_name in css_rules:
                                css_rules[class_name]['background-image'] = f"url('assets/{filename}')"
                        except Exception as e:
                            print(f"Warning: Failed to download {class_name}: {e}")
            
            css_content = self.generate_css(css_rules, canvas_bg)
            fonts_link = self.generate_google_fonts_link()
            
            html_template = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{figma_data.get('name', 'Figma Design')}</title>
    {fonts_link}
    <style>
{css_content}
    </style>
</head>
<body>
  {html_body}
</body>
</html>"""
            
            os.makedirs(output_dir, exist_ok=True)
            with open(os.path.join(output_dir, 'index.html'), 'w', encoding='utf-8') as f:
                f.write(html_template)
            
            print(f"\n✓ Conversion complete")
            print(f"✓ Output: {output_dir}/index.html")
            
        except requests.exceptions.HTTPError as e:
            print(f"Error: HTTP {e.response.status_code}")
            if e.response.status_code == 403:
                print("Check API key and file permissions")
            elif e.response.status_code == 404:
                print("File not found")
            raise
        except Exception as e:
            print(f"Error: {e}")
            raise


def main():
    api_key = os.getenv('FIGMA_TOKEN') or os.getenv('FIGMA_API_KEY')
    file_key = os.getenv('FIGMA_KEY') or os.getenv('FIGMA_FILE_KEY')
    
    if not api_key or not file_key:
        print("Error: Missing FIGMA_TOKEN and FIGMA_KEY in environment")
        return 1
    
    converter = FigmaConverter(api_key, file_key)
    converter.convert()
    return 0


if __name__ == "__main__":
    exit(main())
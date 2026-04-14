import os
import re

icon_dir = "assets/icons"

def whitify_svg(content):
    # 1. Replace stroke="currentColor" with stroke="white"
    content = re.sub(r'stroke="currentColor"', 'stroke="white"', content)
    
    # 2. If it has no fill or stroke at the SVG level or path level, add a default fill
    # This is a bit coarse but works for these MD icons
    if 'fill=' not in content and 'stroke=' not in content:
        content = re.sub(r'<svg ', '<svg fill="white" ', content)
    
    # 3. Specifically if it has fill="none" (usually used with stroke), leave it alone, 
    # but ensure stroke is white
    if 'fill="none"' in content:
        content = re.sub(r'stroke="[^"]*"', 'stroke="white"', content)
    elif 'fill=' not in content:
        # If there's no fill defined anywhere, add it to paths or SVG
        content = re.sub(r'<path ', '<path fill="white" ', content)
        
    return content

def main():
    if not os.path.exists(icon_dir):
        print(f"Error: {icon_dir} not found")
        return

    for filename in os.listdir(icon_dir):
        if filename.endswith(".svg"):
            path = os.path.join(icon_dir, filename)
            with open(path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            new_content = whitify_svg(content)
            
            with open(path, 'w', encoding='utf-8') as f:
                f.write(new_content)
            print(f"Updated {filename}")

if __name__ == "__main__":
    main()

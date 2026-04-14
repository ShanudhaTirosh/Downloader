from PIL import Image, ImageDraw, ImageFont
import os

os.makedirs('assets', exist_ok=True)

def create_icon():
    # Create a 256x256 image with a gradient
    size = (256, 256)
    img = Image.new('RGBA', size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    
    # Draw a rounded rect background
    draw.rounded_rectangle([10, 10, 246, 246], radius=40, fill=(20, 20, 30, 255), outline=(0, 212, 255, 255), width=8)
    
    # Add some "SF" text (ShanuFx)
    try:
        # Try to use a system font
        font = ImageFont.truetype("arial.ttf", 120)
    except:
        font = ImageFont.load_default()
    
    # Draw SF
    draw.text((128, 128), "SF", fill=(0, 212, 255, 255), font=font, anchor="mm")
    
    # Save as ICO
    img.save('assets/icon.ico', format='ICO', sizes=[(256, 256), (128, 128), (64, 64), (32, 32), (16, 16)])
    print("Created assets/icon.ico")

if __name__ == "__main__":
    create_icon()

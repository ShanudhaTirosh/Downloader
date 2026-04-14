import urllib.request
import os

os.makedirs('assets/icons', exist_ok=True)
icons = {
    'download': 'https://raw.githubusercontent.com/Templarian/MaterialDesign/master/svg/download.svg',
    'play': 'https://raw.githubusercontent.com/Templarian/MaterialDesign/master/svg/play.svg',
    'bolt': 'https://raw.githubusercontent.com/Templarian/MaterialDesign/master/svg/lightning-bolt.svg',
    'clock': 'https://raw.githubusercontent.com/Templarian/MaterialDesign/master/svg/clock-outline.svg',
    'settings': 'https://raw.githubusercontent.com/Templarian/MaterialDesign/master/svg/cog.svg',
    'add': 'https://raw.githubusercontent.com/Templarian/MaterialDesign/master/svg/plus.svg',
    'search': 'https://raw.githubusercontent.com/Templarian/MaterialDesign/master/svg/magnify.svg',
    'trash': 'https://raw.githubusercontent.com/Templarian/MaterialDesign/master/svg/trash-can.svg',
    'refresh': 'https://raw.githubusercontent.com/Templarian/MaterialDesign/master/svg/refresh.svg',
    'pause': 'https://raw.githubusercontent.com/Templarian/MaterialDesign/master/svg/pause.svg',
    'close': 'https://raw.githubusercontent.com/Templarian/MaterialDesign/master/svg/close.svg',
    'folder': 'https://raw.githubusercontent.com/Templarian/MaterialDesign/master/svg/folder.svg',
    'link': 'https://raw.githubusercontent.com/Templarian/MaterialDesign/master/svg/link.svg',
    'globe': 'https://raw.githubusercontent.com/Templarian/MaterialDesign/master/svg/web.svg',
    'success': 'https://raw.githubusercontent.com/Templarian/MaterialDesign/master/svg/check-circle.svg',
    'error': 'https://raw.githubusercontent.com/Templarian/MaterialDesign/master/svg/alert-circle.svg',
    'chart': 'https://raw.githubusercontent.com/Templarian/MaterialDesign/master/svg/chart-bar.svg',
    'more': 'https://raw.githubusercontent.com/Templarian/MaterialDesign/master/svg/dots-horizontal.svg',
    'arrow_down': 'https://raw.githubusercontent.com/Templarian/MaterialDesign/master/svg/arrow-down.svg',
    'arrow_up': 'https://raw.githubusercontent.com/Templarian/MaterialDesign/master/svg/arrow-up.svg',
    'queue': 'https://raw.githubusercontent.com/Templarian/MaterialDesign/master/svg/format-list-bulleted.svg'
}

for name, url in icons.items():
    print(f'Downloading {name}.svg...')
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req) as response:
            content = response.read().decode('utf-8')
            new_content = content.replace('\"#000000\"', '\"currentColor\"').replace('fill=\"none\"', '')
            with open(f'assets/icons/{name}.svg', 'w') as f:
                f.write(new_content)
    except Exception as e:
        print(f'Failed {name}: {e}')

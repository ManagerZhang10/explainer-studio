#!/usr/bin/env python3
"""新建口播专题骨架：studio avatar init <目录>。
生成 topic.json、script/script.json、scenes.js（照模板改）和一张示意图。
录像、克隆声音、示意图的默认值取本机 config.toml 的 [me] 段，没配就留空让你填。"""
import json, shutil, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
from studio.common import config  # noqa: E402

PIPE = Path(__file__).resolve().parent.parent
if len(sys.argv) < 2:
    sys.exit('用法：studio avatar init <专题目录>')
d = Path(sys.argv[1]).expanduser().resolve()
if (d / 'topic.json').exists():
    sys.exit(f'{d} 已经是专题目录')
for p in ['script', 'assets', 'work', 'out']:
    (d / p).mkdir(parents=True, exist_ok=True)
me = config.load().get('me', {})
topic = {'out_name': d.name, 'theme': 'light', 'camera_open': 'card', 'camera_open_until': 'hook', 'tail': 1.8,
         'camera': {'video': me.get('camera_video', ''), 'mic': me.get('camera_mic', ''), 'start': me.get('camera_start', 0),
                    'grade': me.get('camera_grade', 'null')},
         'voice': {'speed': me.get('voice_speed', 1.12), 'sample_start': me.get('voice_sample_start', 0), 'sample_len': 90,
                   'clone_result': me.get('voice_clone_result', 'work/voice/clone_result.json'),
                   # 各家克隆好的声音：config [me] 里 voice_clone_result_<家>（bailian / qwen / cosyvoice）
                   **{k.replace('voice_', '', 1): me[k] for k in me if k.startswith('voice_clone_result_')}},
         'bgm': {'style': 'bright'}}
json.dump(topic, open(d / 'topic.json', 'w'), ensure_ascii=False, indent=1)
json.dump({'title': '', 'source': '', 'lines': [
    {'id': 'hook', 'show': '开场一句结论。', 'say': '开场一句结论。'},
    {'id': 'p01', 'show': '第一个要点。', 'say': '第一个要点。'},
    {'id': 'outro', 'show': '想看哪个，评论区说。', 'say': '想看哪个，评论区说。'}]}, open(d / 'script/script.json', 'w'), ensure_ascii=False, indent=1)
shutil.copy(PIPE / 'engine/scenes.template.js', d / 'scenes.js')
demo = config.path('me', 'demo_image')
if demo and demo.exists():
    shutil.copy(demo, d / 'assets/demo.png')
else:  # 没配示意图就画一张渐变占位图
    from PIL import Image
    im = Image.new('RGB', (360, 320))
    im.putdata([(80 + x // 3, 120 + y // 4, 200 - x // 4) for y in range(320) for x in range(360)])
    im.save(d / 'assets/demo.png')
print('created', d)
missing = [k for k in ('camera_video', 'camera_mic') if not me.get(k)]
if missing:
    print('topic.json 里还要手填：', '、'.join(missing), '（或写进 config.toml 的 [me] 段，以后新建自动带上）')

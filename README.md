# 캐릭터 쇼츠 채널

캐릭터 쇼츠 채널의 분야, 캐릭터, 말투와 시리즈를 정하고 이후 에피소드마다 같은 프로필을 쓰는 스킬입니다. 직접 녹음과 코드 카드만으로 시작할 수 있고, 선택에 따라 AI 내레이션이나 장면 그림을 더할 수 있습니다.

## 사용 예시

- “심리 쇼츠 캐릭터 채널 만들어 줘”
- “다음 편 만들어 줘”
- “이 주제로 한 편: 알람을 자꾸 미루는 이유”

첫 작업에서는 인기 쇼츠 경향을 살펴보고 캐릭터 콘셉트, 시리즈 주제 20개, 채널 이름 후보 5개를 제안합니다. 말투별 음성 샘플과 캐릭터 그림 후보를 확인해 선택하면 스타일과 제작 방식을 `channel/profile.json`과 `channel/STYLE.md`에 저장합니다.

이후에는 같은 작업 폴더에서 새 주제나 “다음 편”을 요청하세요. 선택한 방식으로 대본, 음성과 장면을 준비한 뒤, 대본 자막이 들어간 세로 MP4와 장면 시트, 검수 보고서, 제목 3안이 포함된 업로드 키트를 만듭니다. 편이 준비되면 프로필의 주제 상태를 갱신합니다. [전체 흐름](SKILL.md)

## 설치

Claude Code에서는 저장소의 상위 디렉터리에서 실행하세요. [Claude Code 스킬 문서](https://code.claude.com/docs/en/skills)

```bash
mkdir -p ~/.claude/skills/character-shorts-channel
cp -R character-shorts-channel/SKILL.md character-shorts-channel/README.md \
  character-shorts-channel/references character-shorts-channel/scripts \
  character-shorts-channel/templates character-shorts-channel/examples \
  ~/.claude/skills/character-shorts-channel/
```

claude.ai에서는 코드 실행과 파일 생성을 사용 설정하고 **Customize → Skills**에서 스킬 폴더를 담은 ZIP을 업로드합니다. 저장소 루트에서 ZIP을 만들 수 있습니다. [Claude 맞춤 스킬 도움말](https://support.claude.com/en/articles/12512180-use-skills-in-claude)

```bash
git archive --format=zip --prefix=character-shorts-channel/ \
  --output=../character-shorts-channel.zip HEAD
```

Higgsfield에서 음성이나 장면을 만들려면 Claude Code의 `/mcp` 또는 claude.ai의 **Customize → Connectors**에서 인증합니다. 커넥터 주소는 `https://mcp.higgsfield.ai/mcp`입니다. [Higgsfield MCP 안내](https://higgsfield.ai/mcp)

```bash
claude mcp add --transport http --scope user higgsfield https://mcp.higgsfield.ai/mcp
```

## 제작 방식과 비용

아래는 한 편의 실측 기준입니다. 생성 단계마다 실제 견적을 먼저 확인합니다. 채널 설정용 캐릭터 후보, 표정 시트, 감정 기준 그림, 음성 샘플과 재생성은 별도로 계산합니다.

| 방식 | 프로필 값 | 70초 내레이션 기준 크레딧 |
|---|---|---:|
| ① 직접 녹음 + 코드 카드 | `recorded_card` | 0 |
| ② AI 음성 + 코드 카드 | `ai_voice_card` | 약 2.76 |
| ③ AI 음성 + 생성 그림 | `ai_voice_image` | 약 2.76 + 기본 화질 그림 장당 0.75 |

## 로컬 렌더

Python 3.10 이상, 한국어 글꼴, H.264 인코더 `libx264`와 AAC 인코더가 포함된 FFmpeg 및 `ffprobe`가 필요합니다. 아래 명령은 스킬 폴더에서 실행합니다.

```bash
python3 -m venv .venv
. .venv/bin/activate
python3 -m pip install -r scripts/requirements.txt
python3 scripts/render.py --scenes work/scenes.json --audio work/narration.mp3 \
  --language ko --out work/out
```

- `scenes.json`은 재생 순서의 배열입니다. 각 장면에는 고유한 `key`와 녹음 내용과 같은 `dialogue`가 필요합니다.
- 그림 장면은 `type`을 생략하거나 `"type": "image"`를 지정합니다. `image`는 JSON 파일 기준 상대 경로입니다. `screen_text`로 화면 문구를 추가할 수 있습니다.
- 카드 장면은 `"type": "card"`와 `screen_text` 문자열 배열을 사용합니다. 첫 줄은 제목, 둘째와 셋째 줄은 선택 설명입니다. 선택 항목인 `number`는 `"1개"` 같은 짧은 문자열입니다. 생략하면 기본 도형이 들어갑니다. 그림과 카드는 한 편에서 함께 사용할 수 있습니다.
- `--audio`에는 MP3, WAV 등 FFmpeg가 읽는 녹음 파일을 쓸 수 있습니다. `--words`로 원본 음성 기준의 초 단위 타이밍 `[{"w":"알람을","s":0.05,"e":0.46}]`을 전달할 수 있습니다. 생략하면 faster-whisper가 단어 시각을 추정합니다.
- 시스템에서 한글 글꼴을 찾지 못하면 `--font /path/to/NotoSansKR.ttf`를 지정하세요.
- 출력은 `short.mp4`, `sheet_scenes.jpg`, `REPORT.md`입니다. 장면 시트와 보고서를 본 뒤 MP4를 재생해 컷, 발화, 자막을 대조합니다. claude.ai에서 렌더 의존성을 사용할 수 없으면 입력 파일을 내려받아 로컬에서 실행하세요.

### 15초 카드 예시

[카드 전용 장면](examples/card_only/scenes.json)과 단어 타이밍이 들어 있습니다. 내레이션 파일은 [예시 안내](examples/card_only/README.md)대로 먼저 만드세요. `--words`를 사용하면 이 예시를 렌더할 때 Pillow와 FFmpeg만 필요합니다.

```bash
python3 scripts/render.py --scenes examples/card_only/scenes.json \
  --audio examples/card_only/narration.mp3 --words examples/card_only/words.json \
  --out ../test_out/card_only
```

[가사리 프로필 예시](examples/gasari/profile.example.json)는 가상의 채널 정보로 채웠습니다. [전체 대본](examples/gasari/script.md)과 [첫 네 컷](examples/gasari/scenes.json)이 들어 있으며 그림 예시를 렌더할 음성은 별도로 준비합니다.

## English summary

Set up a recurring character-led Shorts channel, choose its voice and look, and save the style and topic queue in a reusable channel profile. Each episode can use your own recording and code-drawn cards, AI narration and cards, or AI narration and generated art. The renderer produces a vertical MP4 with script-based captions, a scene sheet, and an audio QA report. The upload kit includes three title options, a description, hashtags, a pinned comment, and the upload checks. Try the bundled 15-second card example with Python, Pillow, and FFmpeg.
